import { useEffect, useRef, useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer, acknowledgeNudge } from "../../shared/api";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Pill, Button } from "../../shared/ui/primitives";
import { useAnswerTelemetry } from "../hooks/useAnswerTelemetry";
import IntegrityNudge from "../IntegrityNudge";
import s from "./PuzzleLock.module.css";

// ---------------------------------------------------------------------------
// Puzzle Lock — Practice Arc game (gb_puzzle_lock).
//
// Each item in gb_puzzle_lock is a {content?|text?, q?|question?} tuple.
// The lock renders one tumbler per item. The current tumbler shows the
// content/text clue + q/question prompt; student types an answer and submits.
// Correct → tumbler clicks open, advance to next; wrong → shake + retry.
// When ALL tumblers are open, the lock pops open → onComplete().
//
// Answers (a/answer) are stripped server-side before hydration — they are
// NEVER present on the client. Correctness is ALWAYS the server's call.
//
// Submit shape:
//   submitGameAnswer(hwId, sessionId, "puzzle-lock", {
//     item_index: <0-based int>,
//     student_answer: <string>,
//   })
//   → { correct: boolean, feedback: string }
// ---------------------------------------------------------------------------

// --- Inline type (do NOT import from shared/types.ts) ---
interface PuzzleLockItem {
  content?: string;
  text?: string;
  q?: string;
  question?: string;
}

interface PuzzleLockResponse {
  correct: boolean;
  feedback: string;
  // Optional advisory anti-cheat nudge — never answer-bearing.
  integrity_nudge?: { type: string; message: string } | null;
}

type TumblerState = "locked" | "open" | "wrong";

export default function PuzzleLock({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_puzzle_lock ?? []) as PuzzleLockItem[];

  // Empty guard — graceful skip card mirrors TileMatch / SentenceFill pattern
  if (items.length === 0) {
    return (
      <div className={s.wrap} data-testid="puzzle-lock-empty">
        <Lead>No puzzle-lock items on this homework.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete}>
            Skip →
          </Button>
        </div>
      </div>
    );
  }

  return (
    <PuzzleLockInner
      hwId={hwId}
      sessionId={sessionId}
      items={items}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// Inner — separated so the guard above is a clean early return.
// ---------------------------------------------------------------------------
function PuzzleLockInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: PuzzleLockItem[];
  onComplete: () => void;
}) {
  const total = items.length;

  // Which tumbler the student is currently on (0-based)
  const [currentIdx, setCurrentIdx] = useState(0);

  // Per-tumbler state: "locked" | "open" | "wrong"
  const [tumblerStates, setTumblerStates] = useState<TumblerState[]>(
    () => Array(total).fill("locked") as TumblerState[]
  );

  const [inputValue, setInputValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [allOpen, setAllOpen] = useState(false);
  // Advisory anti-cheat: timing + paste per tumbler; advisory nudge from server.
  const tele = useAnswerTelemetry(currentIdx);
  const [nudge, setNudge] = useState<{ type: string; message: string } | null>(null);

  // Track whether the current tumbler is shaking (wrong answer)
  const [shaking, setShaking] = useState(false);
  const shakeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input when tumbler changes
  useEffect(() => {
    if (!allOpen) {
      inputRef.current?.focus();
    }
  }, [currentIdx, allOpen]);

  // Cleanup shake timer on unmount
  useEffect(() => {
    return () => {
      if (shakeTimer.current) clearTimeout(shakeTimer.current);
    };
  }, []);

  const item = items[currentIdx];
  const clue = item.content ?? item.text ?? "";
  const question = item.q ?? item.question ?? "";
  const openedCount = tumblerStates.filter((t) => t === "open").length;

  async function handleSubmit() {
    const trimmed = inputValue.trim();
    if (!trimmed || submitting || allOpen) return;

    setSubmitting(true);
    setFeedback(null);
    setError(null);

    try {
      const res = await submitGameAnswer<PuzzleLockResponse>(
        hwId,
        sessionId,
        "puzzle-lock",
        { item_index: currentIdx, student_answer: trimmed, ...tele.read() }
      );
      setNudge(res.integrity_nudge ?? null);

      if (res.correct) {
        // Tumbler clicks open
        const next = [...tumblerStates] as TumblerState[];
        next[currentIdx] = "open";
        setTumblerStates(next);
        setInputValue("");
        setFeedback(null);

        const newOpenCount = next.filter((t) => t === "open").length;
        if (newOpenCount >= total) {
          // All tumblers open — lock pops open
          setAllOpen(true);
        } else {
          // Advance to next locked tumbler
          const nextIdx = next.findIndex((t, i) => i > currentIdx && t === "locked");
          setCurrentIdx(nextIdx >= 0 ? nextIdx : currentIdx + 1);
        }
      } else {
        // Wrong — shake + show feedback, allow retry
        setFeedback(res.feedback || "Not quite — try again.");

        const next = [...tumblerStates] as TumblerState[];
        next[currentIdx] = "wrong";
        setTumblerStates(next);
        setShaking(true);

        if (shakeTimer.current) clearTimeout(shakeTimer.current);
        shakeTimer.current = setTimeout(() => {
          setShaking(false);
          // Restore "locked" so the input stays active for retry
          setTumblerStates((prev) => {
            const r = [...prev] as TumblerState[];
            r[currentIdx] = "locked";
            return r;
          });
        }, 520);

        setInputValue("");
        inputRef.current?.focus();
      }
    } catch (err) {
      setError((err as Error).message || "Could not check that answer.");
    } finally {
      setSubmitting(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  }

  // ---- All-open celebration screen ----
  if (allOpen) {
    return (
      <div className={s.wrap} data-testid="puzzle-lock-complete">
        {/* Ambient glow layer */}
        <div className={s.ambient} aria-hidden="true">
          <div className={s.auraBlue} />
          <div className={s.auraFuchsia} />
          <div className={s.auraEmerald} />
        </div>
        <div className={s.content}>
          <div className={s.done}>
            <div className={s.lockOpenWrap} aria-hidden="true">
              <LockOpenIcon />
            </div>
            <Pill tone="good">Unlocked</Pill>
            <Title size="section">Lock cracked.</Title>
            <Lead>
              You opened all {total} tumbler{total !== 1 ? "s" : ""}. Clean work.
            </Lead>
            <div className={s.actions}>
              <Button variant="blue" onClick={onComplete} data-testid="pl-continue">
                Continue →
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={s.wrap} data-testid="puzzle-lock">
      {/* Ambient glow layer — blue/fuchsia/emerald radial blobs */}
      <div className={s.ambient} aria-hidden="true">
        <div className={s.auraBlue} />
        <div className={s.auraFuchsia} />
        <div className={s.auraEmerald} />
      </div>

      <div className={s.content}>
        {/* Header */}
        <div className={s.head}>
          <Eyebrow>Puzzle Lock</Eyebrow>
          <span className={s.counter} data-testid="pl-progress">
            {openedCount}/{total} open
          </span>
        </div>

        <Title size="section">Crack the combination.</Title>
        <Lead className={s.sub}>Answer each question to open the next tumbler.</Lead>

        {/* Lock body — tumbler strip */}
        <div className={s.lockBody} aria-label="Combination lock" role="group">
          <div className={s.tumblerStrip}>
            {items.map((_, i) => {
              const state = tumblerStates[i];
              const isCurrent = i === currentIdx;
              return (
                <div
                  key={i}
                  className={[
                    s.tumbler,
                    state === "open" && s.tumblerOpen,
                    state === "wrong" && s.tumblerWrong,
                    isCurrent && state !== "open" && s.tumblerActive,
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  aria-label={`Tumbler ${i + 1}: ${state}`}
                  data-testid={`pl-tumbler-${i}`}
                >
                  {state === "open" ? (
                    <span className={s.tumblerCheckmark} aria-hidden="true">
                      ✓
                    </span>
                  ) : (
                    <span className={s.tumblerDot} aria-hidden="true" />
                  )}
                </div>
              );
            })}
          </div>

          {/* Lock shackle — visual */}
          <div className={[s.shackle, openedCount >= total && s.shackleOpen].filter(Boolean).join(" ")} aria-hidden="true" />
        </div>

        {/* Active question card */}
        <div
          className={[s.questionCard, shaking && s.questionCardShake].filter(Boolean).join(" ")}
          data-testid="pl-question-card"
        >
          {clue && (
            <div className={s.clue} data-testid="pl-clue">
              {clue}
            </div>
          )}
          {question && (
            <p className={s.question} data-testid="pl-question">
              {question}
            </p>
          )}

          <div className={s.inputRow}>
            <input
              ref={inputRef}
              type="text"
              className={s.answerInput}
              value={inputValue}
              placeholder="Your answer…"
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={onKeyDown}
              onPaste={tele.onPaste}
              disabled={submitting}
              aria-label={`Answer for tumbler ${currentIdx + 1}`}
              data-testid="pl-answer-input"
              autoComplete="off"
            />
            <button
              type="button"
              className={s.submitBtn}
              onClick={handleSubmit}
              disabled={submitting || !inputValue.trim()}
              aria-label="Submit answer"
              data-testid="pl-submit"
            >
              {submitting ? "…" : "→"}
            </button>
          </div>
        </div>

        {/* Feedback (wrong answer) */}
        {feedback && (
          <div className={s.feedbackBand} role="status" data-testid="pl-feedback">
            <Pill tone="warn">Try again</Pill>
            <span className={s.feedbackText}>{feedback}</span>
          </div>
        )}

        {/* Advisory anti-cheat nudge — beside feedback, never gates retry. */}
        <IntegrityNudge
          nudge={nudge}
          onDismiss={() => setNudge(null)}
          onRespond={(choice) =>
            acknowledgeNudge(hwId, sessionId, "puzzle-lock", choice)
          }
        />

        {error && (
          <p className={s.error} role="alert" data-testid="pl-error">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lock-open SVG — shown on the completion screen.
// ---------------------------------------------------------------------------
function LockOpenIcon() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={s.lockOpenSvg}
      aria-hidden="true"
    >
      {/* Shackle open (swung left) */}
      <path d="M8 11V6a4 4 0 0 1 7.93-.93" />
      {/* Lock body */}
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      {/* Keyhole */}
      <circle cx="12" cy="16" r="1" fill="currentColor" />
    </svg>
  );
}
