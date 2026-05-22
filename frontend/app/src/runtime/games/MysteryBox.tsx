import { useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Pill, Button } from "../../shared/ui/primitives";
import { useAnswerTelemetry } from "../hooks/useAnswerTelemetry";
import IntegrityNudge from "../IntegrityNudge";
import s from "./MysteryBox.module.css";

// ---------------------------------------------------------------------------
// Mystery Box — Practice Arc game (gb_mystery_box).
//
// Content: array of {category?, q?} — the answer field `a` is stripped
// server-side before hydration; correctness is ALWAYS the server's.
//
// UX flow:
//   1. A row/grid of sealed mystery boxes, one per item.
//   2. Student clicks a box → it "opens" to reveal category + question.
//   3. Student types their answer → hits Submit (or Enter).
//   4. Server grades and returns {correct, feedback}.
//   5. Box is marked solved (green) or missed (red); student sees feedback.
//   6. After all boxes are answered, onComplete() fires.
// ---------------------------------------------------------------------------

// --- Inline type (do NOT import from shared/types.ts) ---
interface MysteryBoxItem {
  category?: string | null;
  q?: string | null;
}

interface MysteryBoxResponse {
  correct: boolean;
  feedback: string;
  // Optional advisory anti-cheat nudge — never answer-bearing.
  integrity_nudge?: { type: string; message: string } | null;
}

type BoxStatus = "sealed" | "open" | "solved" | "missed";

interface BoxState {
  status: BoxStatus;
  answer: string;
  submitting: boolean;
  feedback: string | null;
  correct: boolean | null;
}

function makeBoxStates(count: number): BoxState[] {
  return Array.from({ length: count }, () => ({
    status: "sealed" as BoxStatus,
    answer: "",
    submitting: false,
    feedback: null,
    correct: null,
  }));
}

// Emoji-style icon for each sealed box, cycling through a small palette.
const BOX_ICONS = ["📦", "🎁", "❓", "🔮", "🗃️", "💼", "🎀", "🧧"];

export default function MysteryBox({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_mystery_box ?? []) as MysteryBoxItem[];

  // Empty / missing array → graceful skip card.
  if (items.length === 0) {
    return (
      <div className={s.wrap} data-testid="mystery-box-empty">
        <Lead>No mystery boxes on this homework.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete}>
            Skip →
          </Button>
        </div>
      </div>
    );
  }

  return (
    <MysteryBoxInner
      hwId={hwId}
      sessionId={sessionId}
      items={items}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// Inner — separated so the empty-guard above is a clean early return.
// ---------------------------------------------------------------------------
function MysteryBoxInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: MysteryBoxItem[];
  onComplete: () => void;
}) {
  const [boxes, setBoxes] = useState<BoxState[]>(() => makeBoxStates(items.length));
  // Which box is currently expanded in the answer panel (null = none).
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);
  // Advisory anti-cheat: re-baseline timing/paste each time a box opens.
  const tele = useAnswerTelemetry(activeIdx);
  const [nudge, setNudge] = useState<{ type: string; message: string } | null>(null);

  const totalBoxes = items.length;
  const answeredCount = boxes.filter(
    (b) => b.status === "solved" || b.status === "missed"
  ).length;

  // Open a sealed box (any already-opened/answered box can be re-focused for
  // review, but you can't re-submit).
  function openBox(idx: number) {
    const box = boxes[idx];
    if (box.status === "sealed") {
      setBoxes((prev) => {
        const next = [...prev];
        next[idx] = { ...next[idx], status: "open" };
        return next;
      });
    }
    setActiveIdx(idx);
    setError(null);
    setNudge(null);
  }

  async function submitAnswer(idx: number) {
    const box = boxes[idx];
    if (box.status === "solved" || box.status === "missed") return;
    if (box.submitting) return;
    const trimmed = box.answer.trim();
    if (!trimmed) return;

    setError(null);
    setBoxes((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], submitting: true };
      return next;
    });

    try {
      const res = await submitGameAnswer<MysteryBoxResponse>(
        hwId,
        sessionId,
        "mystery-box",
        {
          item_index: idx,
          student_answer: trimmed,
          ...tele.read(),
        }
      );
      setNudge(res.integrity_nudge ?? null);

      const newStatus: BoxStatus = res.correct ? "solved" : "missed";

      setBoxes((prev) => {
        const next = [...prev];
        next[idx] = {
          ...next[idx],
          status: newStatus,
          submitting: false,
          feedback: res.feedback,
          correct: res.correct,
          answer: trimmed,
        };

        // Check if all boxes are now answered.
        const allDone = next.every(
          (b) => b.status === "solved" || b.status === "missed"
        );
        if (allDone) {
          // Delay slightly so student sees the last verdict.
          setTimeout(() => setComplete(true), 900);
        }
        return next;
      });
    } catch (err) {
      setError((err as Error).message || "Could not check that answer.");
      setBoxes((prev) => {
        const next = [...prev];
        next[idx] = { ...next[idx], submitting: false };
        return next;
      });
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>, idx: number) {
    if (e.key === "Enter") {
      e.preventDefault();
      submitAnswer(idx);
    }
  }

  // Complete screen.
  if (complete) {
    const solvedCount = boxes.filter((b) => b.status === "solved").length;
    return (
      <div className={s.wrap} data-testid="mystery-box-complete">
        <div className={s.done}>
          <Pill tone="good">All opened</Pill>
          <Title size="section">Mystery solved.</Title>
          <Lead>
            You opened all {totalBoxes} box{totalBoxes !== 1 ? "es" : ""} and answered{" "}
            {solvedCount} correctly.
          </Lead>
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete} data-testid="mb-continue">
              Continue →
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const activeBox = activeIdx !== null ? boxes[activeIdx] : null;
  const activeItem = activeIdx !== null ? items[activeIdx] : null;
  const isAnswered =
    activeBox?.status === "solved" || activeBox?.status === "missed";

  return (
    <div className={s.wrap} data-testid="mystery-box">
      {/* Header */}
      <div className={s.head}>
        <Eyebrow>Mystery Box</Eyebrow>
        <span className={s.counter} data-testid="mb-progress">
          {answeredCount}/{totalBoxes} answered
        </span>
      </div>

      <Title size="section">Open a mystery box.</Title>
      <Lead className={s.sub}>
        {activeIdx === null
          ? "Pick any box to reveal its question."
          : "Read the question and type your answer below."}
      </Lead>

      {/* Box grid */}
      <div
        className={s.grid}
        role="group"
        aria-label="Mystery boxes"
        style={{ "--box-count": totalBoxes } as React.CSSProperties}
      >
        {items.map((_, idx) => {
          const box = boxes[idx];
          const isActive = activeIdx === idx;
          const icon = BOX_ICONS[idx % BOX_ICONS.length];
          return (
            <button
              key={idx}
              type="button"
              className={[
                s.box,
                box.status === "open" && s.boxOpen,
                box.status === "solved" && s.boxSolved,
                box.status === "missed" && s.boxMissed,
                isActive && s.boxActive,
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => openBox(idx)}
              aria-label={`Box ${idx + 1}${box.status !== "sealed" ? `, ${box.status}` : ""}`}
              aria-pressed={isActive}
              data-testid={`mb-box-${idx}`}
            >
              <span className={s.boxIcon} aria-hidden="true">
                {box.status === "solved"
                  ? "✓"
                  : box.status === "missed"
                  ? "✗"
                  : icon}
              </span>
              <span className={s.boxLabel}>
                {box.status === "sealed" ? `Box ${idx + 1}` : `#${idx + 1}`}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active box panel */}
      {activeIdx !== null && activeItem && activeBox && (
        <div
          className={[
            s.panel,
            activeBox.status === "solved" && s.panelSolved,
            activeBox.status === "missed" && s.panelMissed,
          ]
            .filter(Boolean)
            .join(" ")}
          data-testid={`mb-panel-${activeIdx}`}
        >
          {/* Category badge */}
          {activeItem.category && (
            <div className={s.categoryRow}>
              <Pill tone="accent">{activeItem.category}</Pill>
            </div>
          )}

          {/* Question text */}
          <p className={s.question} data-testid="mb-question">
            {activeItem.q ?? "What is the answer?"}
          </p>

          {/* Answer area */}
          {!isAnswered ? (
            <div className={s.answerRow}>
              <input
                type="text"
                className={[s.answerInput, activeBox.submitting && s.inputSubmitting]
                  .filter(Boolean)
                  .join(" ")}
                value={activeBox.answer}
                placeholder="Type your answer…"
                onChange={(e) => {
                  const val = e.target.value;
                  setBoxes((prev) => {
                    const next = [...prev];
                    next[activeIdx] = { ...next[activeIdx], answer: val };
                    return next;
                  });
                }}
                onKeyDown={(e) => onKeyDown(e, activeIdx)}
                onPaste={tele.onPaste}
                disabled={activeBox.submitting}
                aria-label={`Answer for box ${activeIdx + 1}`}
                data-testid="mb-answer-input"
                // eslint-disable-next-line jsx-a11y/no-autofocus
                autoFocus
              />
              <Button
                variant="blue"
                onClick={() => submitAnswer(activeIdx)}
                disabled={!activeBox.answer.trim() || activeBox.submitting}
                data-testid="mb-submit"
              >
                {activeBox.submitting ? "Checking…" : "Submit"}
              </Button>
            </div>
          ) : (
            /* Feedback row (answered state) */
            <div className={s.feedbackRow} data-testid="mb-feedback">
              <Pill tone={activeBox.correct ? "good" : "warn"}>
                {activeBox.correct ? "Correct" : "Incorrect"}
              </Pill>
              {activeBox.feedback && (
                <span className={s.feedbackText}>{activeBox.feedback}</span>
              )}
            </div>
          )}

          {/* Advisory anti-cheat nudge — beside feedback, never gates flow. */}
          <IntegrityNudge nudge={nudge} onDismiss={() => setNudge(null)} />
        </div>
      )}

      {error && (
        <p className={s.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
