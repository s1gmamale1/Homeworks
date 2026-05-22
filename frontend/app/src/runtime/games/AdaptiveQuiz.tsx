import { useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer, acknowledgeNudge } from "../../shared/api";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Pill, Button } from "../../shared/ui/primitives";
import { useAnswerTelemetry } from "../hooks/useAnswerTelemetry";
import IntegrityNudge from "../IntegrityNudge";
import { play } from "../sfx";
import s from "./AdaptiveQuiz.module.css";

// ---------------------------------------------------------------------------
// Adaptive Quiz — Practice Arc game (gb_adaptive_quiz).
//
// Renders a sequence of question items in order. Each item has `q` or
// `prompt` for display text and an optional `options` array. If options are
// present, the student taps a choice button; otherwise a text input is shown.
// Every answer is submitted SERVER-SIDE via phase="adaptive-quiz" with
// { item_index, student_answer }. The server returns { correct, feedback }.
// Correctness is ALWAYS the server's — never compared client-side.
// After the last item is answered, onComplete() fires.
//
// Empty/missing array → graceful skip card → onComplete.
// ---------------------------------------------------------------------------

// Inline item type (do NOT import from shared/types.ts)
interface AdaptiveQuizItem {
  q?: string;
  prompt?: string;
  options?: string[] | null;
  // Answer fields (answer_spec / ans / correct) are stripped server-side.
  // Do not reference them here.
}

interface QuizResponse {
  correct: boolean;
  feedback: string;
  // Optional advisory anti-cheat nudge (server-set on a strong flag only).
  // Never answer-bearing; never decides correctness.
  integrity_nudge?: { type: string; message: string } | null;
}

// Per-item submission result stored for display until the student advances.
interface ItemResult {
  correct: boolean;
  feedback: string;
}

export default function AdaptiveQuiz({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_adaptive_quiz ?? []) as AdaptiveQuizItem[];

  // Graceful skip on empty array
  if (items.length === 0) {
    return (
      <div className={s.wrap} data-testid="adaptive-quiz-empty">
        <div className={s.ambient} aria-hidden="true" />
        <div className={s.stage}>
          <Lead>No adaptive-quiz questions on this homework.</Lead>
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete}>
              Skip →
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <AdaptiveQuizInner
      hwId={hwId}
      sessionId={sessionId}
      items={items}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// Inner — stateful game body (separated so the empty guard above is clean).
// ---------------------------------------------------------------------------
function AdaptiveQuizInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: AdaptiveQuizItem[];
  onComplete: () => void;
}) {
  const totalItems = items.length;
  const [itemIdx, setItemIdx] = useState(0);
  const [inputValue, setInputValue] = useState("");
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [result, setResult] = useState<ItemResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);
  // Advisory anti-cheat: per-item timing + paste; advisory nudge from server.
  const tele = useAnswerTelemetry(itemIdx);
  const [nudge, setNudge] = useState<{ type: string; message: string } | null>(null);

  const item = items[itemIdx];
  const questionText = item.q ?? item.prompt ?? "";
  const options = item.options && item.options.length > 0 ? item.options : null;

  // ---- Submission ----
  async function handleSubmit(answer: string) {
    const trimmed = answer.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const res = await submitGameAnswer<QuizResponse>(hwId, sessionId, "adaptive-quiz", {
        item_index: itemIdx,
        student_answer: trimmed,
        ...tele.read(),
      });
      setResult({ correct: res.correct, feedback: res.feedback });
      setNudge(res.integrity_nudge ?? null);
      if (res.correct) {
        play("correct");
      } else {
        play("wrong");
      }
    } catch (err) {
      setError((err as Error).message || "Could not check that answer.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleOptionSelect(opt: string) {
    if (result || submitting) return;
    setSelectedOption(opt);
    handleSubmit(opt);
  }

  function handleTextSubmit() {
    handleSubmit(inputValue);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit(inputValue);
    }
  }

  // Advance to next item (or finish)
  function handleAdvance() {
    if (itemIdx + 1 < totalItems) {
      setItemIdx((i) => i + 1);
      setInputValue("");
      setSelectedOption(null);
      setResult(null);
      setError(null);
      setNudge(null);
    } else {
      setComplete(true);
    }
  }

  // ---- Complete screen ----
  if (complete) {
    return (
      <div className={s.wrap} data-testid="adaptive-quiz-complete">
        <div className={s.ambient} aria-hidden="true" />
        <div className={s.stage}>
          <div className={s.done}>
            <Pill tone="good">All answered</Pill>
            <Title size="section">Quiz complete.</Title>
            <Lead>
              You answered all {totalItems} question{totalItems !== 1 ? "s" : ""}. Keep going.
            </Lead>
            <div className={s.actions}>
              <Button variant="blue" onClick={onComplete} data-testid="aq-continue">
                Continue →
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={s.wrap} data-testid="adaptive-quiz">
      {/* Ambient multi-hue glow — presentational only */}
      <div className={s.ambient} aria-hidden="true" />

      <div className={s.stage}>
        {/* Header */}
        <div className={s.head}>
          <Eyebrow>Adaptive Quiz</Eyebrow>
          <span className={s.counter} data-testid="aq-progress">
            {itemIdx + 1} / {totalItems}
          </span>
        </div>

        {/* Progress dots */}
        <div className={s.progressDots} aria-hidden="true">
          {items.map((_, i) => (
            <span
              key={i}
              className={[
                s.dot,
                i === itemIdx && s.dotActive,
                i < itemIdx && s.dotDone,
              ]
                .filter(Boolean)
                .join(" ")}
            />
          ))}
        </div>

        <Title size="section">Answer the question.</Title>

        {/* Question card — frosted-glass slab with interior glow */}
        <div className={s.questionCard} data-testid="aq-question">
          <div className={s.questionGlow} aria-hidden="true" />
          <div className={s.questionBody}>
            <p className={s.questionText}>{questionText}</p>
          </div>
        </div>

        {/* Answer area — options OR text input */}
        {options ? (
          <div className={s.optionsList} role="group" aria-label="Answer choices">
            {options.map((opt, i) => {
              const isSelected = selectedOption === opt;
              const isAnswered = result !== null;
              return (
                <button
                  key={i}
                  type="button"
                  className={[
                    s.optionBtn,
                    isSelected && !isAnswered && s.optionSelected,
                    isSelected && isAnswered && result.correct && s.optionCorrect,
                    isSelected && isAnswered && !result.correct && s.optionWrong,
                    !isSelected && isAnswered && s.optionDimmed,
                    submitting && isSelected && s.optionSubmitting,
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  disabled={isAnswered || submitting}
                  onClick={() => { play("tick"); handleOptionSelect(opt); }}
                  data-testid={`aq-option-${i}`}
                  aria-pressed={isSelected}
                >
                  <span className={s.optionIndex}>{String.fromCharCode(65 + i)}</span>
                  <span className={s.optionText}>{opt}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <div className={s.textInputWrap}>
            <input
              type="text"
              className={[
                s.textInput,
                result && result.correct && s.textInputCorrect,
                result && !result.correct && s.textInputWrong,
              ]
                .filter(Boolean)
                .join(" ")}
              value={inputValue}
              placeholder="Type your answer…"
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={tele.onPaste}
              disabled={result !== null || submitting}
              aria-label="Your answer"
              data-testid="aq-text-input"
            />
            {!result && (
              <Button
                variant="blue"
                onClick={handleTextSubmit}
                disabled={!inputValue.trim() || submitting}
                data-testid="aq-submit"
              >
                {submitting ? "Checking…" : "Submit"}
              </Button>
            )}
          </div>
        )}

        {/* Feedback panel — shown after server responds */}
        {result && (
          <div
            className={[s.feedback, result.correct ? s.feedbackCorrect : s.feedbackWrong].join(" ")}
            role="status"
            data-testid="aq-feedback"
          >
            <Pill tone={result.correct ? "good" : "warn"}>
              {result.correct ? "Correct" : "Not quite"}
            </Pill>
            <p className={s.feedbackText}>{result.feedback}</p>
            <div className={s.actions}>
              <Button
                variant={itemIdx + 1 < totalItems ? "blue" : "blue"}
                onClick={handleAdvance}
                data-testid="aq-next"
              >
                {itemIdx + 1 < totalItems ? "Next question →" : "Finish →"}
              </Button>
            </div>
          </div>
        )}

        {/* Advisory anti-cheat nudge — mounts BESIDE feedback, never gates the
            Next/Finish button above. */}
        <IntegrityNudge
          nudge={nudge}
          onDismiss={() => setNudge(null)}
          onRespond={(choice) =>
            acknowledgeNudge(hwId, sessionId, "adaptive-quiz", choice)
          }
        />

        {error && (
          <p className={s.error} role="alert" data-testid="aq-error">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
