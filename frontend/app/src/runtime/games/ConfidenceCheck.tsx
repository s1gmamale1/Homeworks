import { useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import {
  GameShell,
  EmptyGuard,
  PressChoice,
  PressButton,
  ResultTier,
} from "./_practiceShared";
import { play } from "../sfx";
import s from "./ConfidenceCheck.module.css";

// ---------------------------------------------------------------------------
// Confidence Check — Practice Arc game (gb_confidence_check). NEW.
//
// MECHANIC (metacognition / calibration — an IB/Cambridge study-skills staple):
//   For each item the student answers a uniform MCQ AND rates how confident
//   they are: Sure / Maybe / Guess. The server grades correctness; the CLIENT
//   then derives a CALIBRATION VERDICT from {correct, confidence}:
//
//     Sure  + Correct → Mastered            (calibrated, high confidence)
//     Sure  + Wrong   → Misconception flag  (DANGER: confidently wrong)
//     Maybe + Correct → Solid               (sound, build confidence)
//     Maybe + Wrong   → Close — review
//     Guess + Correct → Lucky — not mastery (revisit; don't bank it)
//     Guess + Wrong   → Known gap           (honest; study this)
//
//   The point is teaching students to KNOW WHAT THEY KNOW — calibration is a
//   higher-order skill than raw accuracy. "Confidently wrong" is the most
//   dangerous quadrant and we surface it loudest.
//
// FLOW per item: pick an option → pick a confidence → submit → calibration
//   verdict + the next/finish CTA.
//
// WIRING (contract §confidence-check): POST
//   submitGameAnswer(hwId, sessionId, "confidence-check",
//     { item_id, selected_index, confidence }) → { correct, feedback, advance }
//   `correct_index` is server-only (redacted at hydration). The calibration
//   label is derived ENTIRELY on the client from {correct, confidence}; the
//   server only returns the boolean correctness.
//
// Phase: "confidence-check". Testids: game-confidence_check,
// confidence_check-option-<i>, confidence_check-conf-<level>,
// confidence_check-verdict, confidence_check-complete, confidence_check-empty.
// ---------------------------------------------------------------------------

interface ConfidenceItem {
  id?: string;
  question?: string;
  options?: string[];
}

interface CheckResponse {
  correct: boolean;
  feedback?: string | null;
  advance?: boolean;
}

type Confidence = "sure" | "maybe" | "guess";

interface Calibration {
  label: string;
  blurb: string;
  /** "mastered" | "danger" | "solid" | "review" | "lucky" | "gap" — drives styling. */
  tone: "mastered" | "danger" | "solid" | "review" | "lucky" | "gap";
}

const CONFIDENCE_LEVELS: { level: Confidence; label: string; hint: string }[] = [
  { level: "sure", label: "Sure", hint: "I know this" },
  { level: "maybe", label: "Maybe", hint: "Fairly confident" },
  { level: "guess", label: "Guess", hint: "Not certain" },
];

// The calibration matrix — CLIENT-derived from {correct, confidence}.
function calibrate(correct: boolean, confidence: Confidence): Calibration {
  if (confidence === "sure") {
    return correct
      ? {
          label: "Mastered",
          tone: "mastered",
          blurb:
            "Correct and confident — this is calibrated mastery. You knew it, and you were right.",
        }
      : {
          label: "Misconception",
          tone: "danger",
          blurb:
            "Confidently wrong — the riskiest gap. You believed it, so you'd never think to check. Review this carefully.",
        };
  }
  if (confidence === "maybe") {
    return correct
      ? {
          label: "Solid",
          tone: "solid",
          blurb:
            "Right, but you weren't fully sure. The knowledge is sound — one more pass and you'll own it.",
        }
      : {
          label: "Close — review",
          tone: "review",
          blurb:
            "Wrong, but you sensed the uncertainty. Honest signal — go back over the reasoning.",
        };
  }
  // guess
  return correct
    ? {
        label: "Lucky — not mastery",
        tone: "lucky",
        blurb:
          "Right by guess, not by knowing. Don't bank this one — revisit it as if you'd missed it.",
      }
    : {
        label: "Known gap",
        tone: "gap",
        blurb:
          "Wrong, and you knew you weren't sure. That self-awareness is exactly what tells you where to study.",
      };
}

export default function ConfidenceCheck({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_confidence_check ??
    []) as ConfidenceItem[];

  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Confidence Check"
        message="No confidence-check items authored for this homework — skip ahead and keep your momentum."
        onSkip={onComplete}
        testid="game-confidence_check-empty"
      />
    );
  }

  return (
    <ConfidenceCheckInner
      hwId={hwId}
      sessionId={sessionId}
      items={items}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// Inner — stateful body (the empty guard above stays a clean early return).
// ---------------------------------------------------------------------------
function ConfidenceCheckInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: ConfidenceItem[];
  onComplete: () => void;
}) {
  const [itemIdx, setItemIdx] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [confidence, setConfidence] = useState<Confidence | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Server correctness + client-derived calibration for the resolved item.
  const [verdict, setVerdict] = useState<{
    correct: boolean;
    calibration: Calibration;
  } | null>(null);
  // Running count of MASTERED (sure+correct) items across the game.
  const [mastered, setMastered] = useState(0);

  const item = items[itemIdx];
  const totalItems = items.length;
  const options = item.options ?? [];
  const isLast = itemIdx + 1 >= totalItems;

  function gotoNext() {
    if (isLast) {
      onComplete();
      return;
    }
    setItemIdx((i) => i + 1);
    setSelected(null);
    setConfidence(null);
    setVerdict(null);
    setError(null);
  }

  // ---- Submit the answer + confidence; derive the calibration locally ----
  async function submit() {
    if (busy || verdict || selected === null || !confidence) return;
    setBusy(true);
    setError(null);
    try {
      let correct: boolean;
      if (!hwId || !sessionId) {
        // No session — keep the arc walkable. Without a server verdict we can't
        // know correctness, so treat the submission as correct (the calibration
        // still teaches the metacognitive frame).
        correct = true;
      } else {
        const res = await submitGameAnswer<CheckResponse>(
          hwId,
          sessionId,
          "confidence-check",
          {
            item_id: item.id ?? String(itemIdx),
            selected_index: selected,
            confidence,
          }
        );
        correct = Boolean(res?.correct);
      }
      const calibration = calibrate(correct, confidence);
      setVerdict({ correct, calibration });
      if (calibration.tone === "mastered") {
        play("correct");
        setMastered((m) => m + 1);
      } else if (calibration.tone === "solid") {
        // solid = Maybe+Correct — encouraging
        play("correct");
      } else {
        // danger (Sure+Wrong = overconfident), review, lucky (underconfident), gap
        play("wrong");
      }
    } catch (err) {
      setError((err as Error).message || "Couldn't check that answer.");
    } finally {
      setBusy(false);
    }
  }

  const counter = `item ${itemIdx + 1}/${totalItems}`;

  // Visual state for an MCQ option. Pre-submit: only the picked one is selected.
  // Post-submit: the picked one reflects the server's correctness.
  const optState = (i: number) => {
    if (selected !== i) return "idle";
    if (!verdict) return "selected";
    return verdict.correct ? "correct" : "wrong";
  };

  const locked = verdict !== null;

  return (
    <GameShell
      title="Confidence Check"
      eyebrow="Practice · Metacognition"
      counter={counter}
      testid="game-confidence_check"
    >
      {item.question && (
        <p className={s.question} data-testid="confidence_check-question">
          {item.question}
        </p>
      )}

      {/* ---- MCQ options ---- */}
      <div className={s.options} role="group" aria-label="Choose your answer">
        {options.map((opt, i) => (
          <PressChoice
            key={i}
            state={optState(i)}
            disabled={busy || locked}
            onClick={() => setSelected(i)}
            aria-pressed={selected === i}
            data-testid={`confidence_check-option-${i}`}
          >
            {opt}
          </PressChoice>
        ))}
      </div>

      {/* ---- confidence rating (the metacognitive layer) ---- */}
      <div className={s.confBlock}>
        <p className={s.confKicker}>How confident are you?</p>
        <div className={s.confRow} role="group" aria-label="Rate your confidence">
          {CONFIDENCE_LEVELS.map(({ level, label, hint }) => (
            <button
              key={level}
              type="button"
              className={`${s.conf}${confidence === level ? ` ${s.confActive}` : ""}`}
              disabled={busy || locked}
              aria-pressed={confidence === level}
              onClick={() => { play("tick"); setConfidence(level); }}
              data-testid={`confidence_check-conf-${level}`}
            >
              <span className={s.confLabel}>{label}</span>
              <span className={s.confHint}>{hint}</span>
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className={s.error} role="alert">
          {error}
        </p>
      )}

      {/* ---- submit OR the calibration verdict ---- */}
      {!verdict ? (
        <div className={s.foot}>
          <PressButton
            onClick={submit}
            disabled={selected === null || !confidence || busy}
            data-testid="confidence_check-submit"
          >
            {busy ? "Checking…" : "Lock it in"}
          </PressButton>
        </div>
      ) : (
        <>
          <div
            className={`${s.verdict} ${s[`tone_${verdict.calibration.tone}`]}`}
            role="status"
            aria-live="polite"
            data-testid="confidence_check-verdict"
          >
            <span className={s.verdictLabel}>{verdict.calibration.label}</span>
            <span className={s.verdictBlurb}>{verdict.calibration.blurb}</span>
          </div>
          <div className={s.foot} data-testid="confidence_check-complete">
            {isLast && <ResultTier tier="Complete" testid="confidence_check-tier" />}
            <PressButton onClick={gotoNext} data-testid="confidence_check-continue">
              {isLast ? "Finish →" : "Next →"}
            </PressButton>
          </div>
          {isLast && (
            <p className={s.scoreLine}>
              You reached calibrated mastery on{" "}
              <strong>
                {mastered}/{totalItems}
              </strong>{" "}
              item{totalItems !== 1 ? "s" : ""} — sure and right.
            </p>
          )}
        </>
      )}
    </GameShell>
  );
}
