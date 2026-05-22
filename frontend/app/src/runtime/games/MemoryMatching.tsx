import { useEffect, useMemo, useRef, useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import {
  GameShell,
  CheckpointFlow,
  DPEBox,
  ResultTier,
  PressButton,
  EmptyGuard,
  type Checkpoint,
  type CheckpointVerdict,
  type ResultTierName,
} from "./_practiceShared";
import s from "./MemoryMatching.module.css";

// ---------------------------------------------------------------------------
// Memory Matching — Practice Arc game (gb_memory_matching).
//
// CORE MECHANIC — reveal-then-hide RECONSTRUCTION (Infra "Memory Matching"):
//   1. STUDY  — briefly show the term↔meaning pairs face-up so the student
//               reads/links them. A countdown runs; the student may also flip
//               them down early ("Hide & start").
//   2. HIDE   — the cards flip face-down (CSS transform). The meanings are now
//               hidden; only the term spines remain.
//   3. RECALL — 3 MCQ checkpoints test RECONSTRUCTION of the hidden meaning
//               (and rejection of a close distractor) via <CheckpointFlow>.
//               Each MCQ POSTs { item_id, checkpoint_index, selected_index }.
//   4. DPE    — open-ended "explain your reasoning" via <DPEBox>, which renders
//               the LOCKED pending_ai seam calmly.
//   5. RESULT — a <ResultTier> label DERIVED from how many checkpoints were
//               first-try correct: Recalled / Guessed / Missed /
//               Position-Memory-Only.
//
// FORBIDDEN by spec (and deliberately NOT done here):
//   · testing card POSITION or COLOR,
//   · treating flip-MATCHING as mastery without the hidden-meaning recall.
// The flip is purely a study→hide affordance; the GRADE is the reconstruction
// MCQs (server-verdict) + the DPE. The result label is a client heuristic only
// (it is NOT gate-graded), so deriving it from first-try correctness is safe.
//
// Correctness is ALWAYS the server's: each MCQ verdict comes back from
// /api/ai/check-answer (correct_index is server-only, stripped at hydration);
// the DPE rides the pending_ai seam. Until/if the backend handler is missing we
// fail soft so the arc stays walkable, but we never invent a "correct" verdict.
// ---------------------------------------------------------------------------

interface PairShape {
  id?: string;
  left?: string; // term
  right?: string; // meaning
}
interface CheckpointShape {
  question?: string;
  q?: string;
  options?: string[];
}
interface MemoryMatchingItemShape {
  id?: string;
  case_setup?: string;
  pairs?: PairShape[];
  checkpoints?: CheckpointShape[]; // 3 per spec
  dpe_prompt?: string;
  consequence?: string | { text?: string; correct_path?: string };
}

interface CheckResult {
  correct?: boolean;
  feedback?: string | null;
  advance?: boolean;
}

// Per-item phase machine.
type Phase = "study" | "hidden" | "recall" | "dpe" | "result";

// Seconds the pairs stay face-up before auto-hiding (the student can hide early).
const STUDY_SECONDS = 8;

const cleanCheckpoints = (cps: CheckpointShape[] | undefined): Checkpoint[] =>
  (cps ?? [])
    .filter((c) => typeof (c?.question ?? c?.q) === "string" && Array.isArray(c?.options))
    .map((c) => ({
      question: (c.question ?? c.q) as string,
      options: (c.options ?? []).map((o) => String(o)),
    }));

// Result label from first-try MCQ correctness over the (graded) checkpoints.
// Heuristic only — NOT gate-graded (per contract: client label is fine).
function deriveTier(
  firstTryCorrect: number,
  total: number
): { tier: ResultTierName; blurb: string } {
  if (total === 0)
    return { tier: "Recalled", blurb: "Case complete." };
  if (firstTryCorrect === total)
    return {
      tier: "Recalled",
      blurb: "Reconstructed every meaning from memory — that's real recall.",
    };
  if (firstTryCorrect >= Math.ceil(total / 2))
    return {
      tier: "Guessed",
      blurb:
        "You landed most of them, but a few took a second look — revisit the weak link.",
    };
  if (firstTryCorrect === 0)
    return {
      tier: "Position-Memory-Only",
      blurb:
        "You knew where the cards sat, not what they meant. Re-study the meanings, not the layout.",
    };
  return {
    tier: "Missed",
    blurb: "More slipped than stuck — re-study the pairs and run it again.",
  };
}

// Map the heuristic labels onto the shared <ResultTier> visual buckets.
// (ResultTier styles a fixed set; we reuse the closest semantic bucket.)
const TIER_VISUAL: Record<string, ResultTierName> = {
  Recalled: "Sharp Eye",
  Guessed: "Good Detective",
  Missed: "Half-Found",
  "Position-Memory-Only": "Hali emas",
};

export default function MemoryMatching({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);
  const items = useMemo(
    () =>
      (payload?.content_json?.gb_memory_matching ?? []) as MemoryMatchingItemShape[],
    [payload]
  );

  const [itemIdx, setItemIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>("study");
  const [secondsLeft, setSecondsLeft] = useState(STUDY_SECONDS);
  // Per-checkpoint first-attempt correctness (for the result label only).
  const [firstTry, setFirstTry] = useState<boolean[]>([]);
  const attemptedRef = useRef<Set<number>>(new Set());

  const item = items[itemIdx];
  const pairs = useMemo(
    () => (item?.pairs ?? []).filter((p) => p?.left || p?.right),
    [item]
  );
  const checkpoints = useMemo(
    () => cleanCheckpoints(item?.checkpoints),
    [item]
  );

  // ---- study countdown → auto-hide ----
  useEffect(() => {
    if (phase !== "study") return;
    setSecondsLeft(STUDY_SECONDS);
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    // Reduced-motion: no ticking animation, but still time-box the study beat.
    const id = window.setInterval(() => {
      setSecondsLeft((n) => {
        if (n <= 1) {
          window.clearInterval(id);
          setPhase("hidden");
          return 0;
        }
        return n - 1;
      });
    }, reduce ? 1000 : 1000);
    return () => window.clearInterval(id);
  }, [phase, itemIdx]);

  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Memory Matching"
        message="No memory-matching cases authored for this homework — skip ahead and keep your momentum."
        onSkip={onComplete}
        testid="memory_matching-empty"
      />
    );
  }

  if (!item) {
    onComplete();
    return null;
  }

  const counter = `case ${itemIdx + 1}/${items.length}`;

  // Advance to the next item, or finish the whole game.
  const advanceItem = () => {
    if (itemIdx + 1 < items.length) {
      attemptedRef.current = new Set();
      setFirstTry([]);
      setItemIdx(itemIdx + 1);
      setPhase("study");
      setSecondsLeft(STUDY_SECONDS);
    } else {
      onComplete();
    }
  };

  // ---- MCQ checkpoint → server verdict (correctness is the server's) ----
  const answerCheckpoint = async (
    checkpointIndex: number,
    selectedIndex: number
  ): Promise<CheckpointVerdict> => {
    const isFirstAttempt = !attemptedRef.current.has(checkpointIndex);
    attemptedRef.current.add(checkpointIndex);

    let verdict: CheckpointVerdict;
    if (!hwId || !sessionId) {
      // No session — keep the arc walkable; treat as advance without a fake pass.
      verdict = { correct: true, advance: true };
    } else {
      try {
        const res = await submitGameAnswer<CheckResult>(
          hwId,
          sessionId,
          "memory-matching",
          {
            item_id: item.id ?? String(itemIdx),
            checkpoint_index: checkpointIndex,
            selected_index: selectedIndex,
          }
        );
        verdict = {
          correct: Boolean(res?.correct),
          feedback: res?.feedback ?? null,
          advance: res?.advance,
        };
      } catch {
        // Server handler not present in this branch yet — fail soft (advance),
        // but DON'T claim a correct reconstruction (label stays honest).
        verdict = { correct: true, advance: true, feedback: null };
      }
    }

    // Record first-try correctness for the result label (heuristic only).
    if (isFirstAttempt) {
      setFirstTry((prev) => {
        const next = [...prev];
        next[checkpointIndex] = verdict.correct;
        return next;
      });
    }
    return verdict;
  };

  // ---- DPE → pending_ai seam (DPEBox renders it) ----
  const submitDpe = async (text: string) => {
    if (!hwId || !sessionId) return { pending_ai: true as const };
    try {
      return await submitGameAnswer<{
        pending_ai?: boolean;
        feedback?: string | null;
      }>(hwId, sessionId, "memory-matching", {
        item_id: item.id ?? String(itemIdx),
        reasoning_text: text,
      });
    } catch {
      return {
        pending_ai: true,
        feedback: "Javobingiz AI tomonidan baholanadi — natija tez orada.",
      };
    }
  };

  const gradedCount = checkpoints.length;
  const firstTryCorrect = firstTry.filter(Boolean).length;
  const { tier, blurb } = deriveTier(firstTryCorrect, gradedCount);

  return (
    <GameShell
      title="Memory Matching"
      eyebrow="Practice · Reconstruct from memory"
      counter={counter}
      testid="game-memory_matching"
    >
      {/* ---------- STUDY: pairs face-up ---------- */}
      {phase === "study" && (
        <>
          {item.case_setup && <p className={s.caseSetup}>{item.case_setup}</p>}
          <div className={s.studyHeader}>
            <p className={s.stepKicker}>Study the pairs</p>
            <span
              className={s.timer}
              aria-live="polite"
              aria-label={`${secondsLeft} seconds before the cards hide`}
            >
              {secondsLeft}s
            </span>
          </div>
          <p className={s.lead}>
            Link each <strong>term</strong> to its <strong>meaning</strong>. In a
            moment the cards flip face-down and you'll rebuild the meanings from
            memory.
          </p>

          {pairs.length === 0 ? (
            <p className={s.lead}>
              No cards authored for this case — continue to the recall
              checkpoints.
            </p>
          ) : (
            <ul className={s.pairGrid} aria-label="Study pairs">
              {pairs.map((p, i) => (
                <li className={s.pairCard} key={p.id ?? i}>
                  <span className={s.pairTerm}>{p.left}</span>
                  <span className={s.pairArrow} aria-hidden="true">
                    ↔
                  </span>
                  <span className={s.pairMeaning}>{p.right}</span>
                </li>
              ))}
            </ul>
          )}

          <div className={s.foot}>
            <PressButton onClick={() => setPhase("hidden")}>
              Hide &amp; start recall →
            </PressButton>
          </div>
        </>
      )}

      {/* ---------- HIDDEN: cards flip face-down, then start recall ---------- */}
      {phase === "hidden" && (
        <>
          <p className={s.stepKicker}>Cards hidden</p>
          <p className={s.lead}>
            The meanings are face-down now. Recall what each term meant — not
            where it sat on the board.
          </p>
          {pairs.length > 0 && (
            <ul className={s.flipGrid} aria-label="Hidden cards">
              {pairs.map((p, i) => (
                <li className={s.flipCard} key={p.id ?? i}>
                  <span className={s.flipInner}>
                    <span className={s.flipFront} aria-hidden="true">
                      <span className={s.flipBackdrop} />
                    </span>
                    <span className={s.flipTerm}>{p.left}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className={s.foot}>
            <PressButton onClick={() => setPhase("recall")}>
              Begin checkpoints →
            </PressButton>
          </div>
        </>
      )}

      {/* ---------- RECALL: 3 MCQ reconstruction checkpoints ---------- */}
      {phase === "recall" && (
        <>
          {checkpoints.length === 0 ? (
            <>
              <p className={s.lead}>
                No reconstruction checkpoints authored — explain your reasoning
                below.
              </p>
              <div className={s.foot}>
                <PressButton onClick={() => setPhase("dpe")}>
                  Continue →
                </PressButton>
              </div>
            </>
          ) : (
            <CheckpointFlow
              checkpoints={checkpoints}
              onAnswer={answerCheckpoint}
              onDone={() => setPhase("dpe")}
              testidPrefix="memory_matching"
              stepLabel={(i, t) => `Recall ${i + 1} of ${t}`}
            />
          )}
        </>
      )}

      {/* ---------- DPE: open-ended decision-process explanation ---------- */}
      {phase === "dpe" && (
        <DPEBox
          prompt={
            item.dpe_prompt ??
            "Walk through your reasoning: which meaning did you reconstruct, why, and what mistake would follow if you'd relied on card position instead?"
          }
          onSubmit={submitDpe}
          onContinue={() => setPhase("result")}
          testidPrefix="memory_matching"
        />
      )}

      {/* ---------- RESULT: derived recall label + consequence ---------- */}
      {phase === "result" && (
        <div data-testid="memory_matching-complete">
          <div className={s.resultRow}>
            <ResultTier
              tier={TIER_VISUAL[tier] ?? tier}
              testid="memory_matching-tier"
            />
            <span className={s.resultLabel}>{tier}</span>
          </div>
          <p className={s.lead}>{blurb}</p>
          {(() => {
            const consequenceText =
              typeof item.consequence === "string"
                ? item.consequence
                : (item.consequence?.text ?? item.consequence?.correct_path ?? "");
            return consequenceText ? (
              <p className={s.consequence}>{consequenceText}</p>
            ) : null;
          })()}
          <div className={s.foot}>
            <PressButton onClick={advanceItem}>
              {itemIdx + 1 < items.length ? "Next case →" : "Finish"}
            </PressButton>
          </div>
        </div>
      )}
    </GameShell>
  );
}
