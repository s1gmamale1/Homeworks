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
import s from "./ProblemTrace.module.css";

// ---------------------------------------------------------------------------
// Problem Trace — Practice Arc game (gb_problem_trace). NEW.
//
// A worked solution is revealed ONE STEP AT A TIME. Before each reveal the
// student must PREDICT the next move (an MCQ from steps[i].predict.options).
// On answer the server returns {correct, feedback, advance} and we then reveal
// the ACTUAL steps[i].reveal_text — correct or not, the derivation always grows
// (this is a worked solution, not a quiz that traps you on a wrong answer). The
// revealed steps stack like a clean derivation; the prediction sits in a
// focused MCQ card below the trace-so-far. Score = correct FIRST-TRY
// predictions. This catches exactly where a student's procedure diverges.
//
// Wiring (contract §problem-trace): per step POST
//   submitGameAnswer(hwId, sessionId, "problem-trace",
//     { item_id, step_index, selected_index }) → { correct, feedback, advance }
// predict.correct_index is server-only (redacted at hydration). After the last
// step we show <ResultTier> + a Continue that advances to the next item, then
// onComplete().
//
// Phase: "problem-trace". Testids: game-problem_trace, problem_trace-step,
// problem_trace-predict, problem_trace-complete, problem_trace-empty.
// ---------------------------------------------------------------------------

interface PredictMCQ {
  question?: string;
  q?: string;
  options?: string[];
}

interface TraceStep {
  id?: string;
  reveal_text?: string;
  predict?: PredictMCQ;
}

interface ProblemTraceItem {
  id?: string;
  problem?: string;
  steps?: TraceStep[];
}

interface TraceResponse {
  correct: boolean;
  feedback?: string | null;
  advance?: boolean;
}

// Per-step UI phase: "predict" = MCQ open; "revealed" = reveal_text shown,
// student reads it then taps Reveal-next / See result.
type StepPhase = "predict" | "revealed";

export default function ProblemTrace({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_problem_trace ??
    []) as ProblemTraceItem[];

  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Problem Trace"
        message="No problem-trace items authored for this homework."
        onSkip={onComplete}
        testid="game-problem_trace-empty"
      />
    );
  }

  return (
    <ProblemTraceInner
      hwId={hwId}
      sessionId={sessionId}
      items={items}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// Inner — stateful body (separated so the empty guard above is a clean return).
// ---------------------------------------------------------------------------
function ProblemTraceInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: ProblemTraceItem[];
  onComplete: () => void;
}) {
  const [itemIdx, setItemIdx] = useState(0);
  // Which step we're tracing within the current item.
  const [stepIdx, setStepIdx] = useState(0);
  const [phase, setPhase] = useState<StepPhase>("predict");
  // Tapped option for the current step (drives correct/wrong highlight).
  const [selected, setSelected] = useState<number | null>(null);
  // Server verdict for the current step's prediction.
  const [verdict, setVerdict] = useState<TraceResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Correct FIRST-TRY predictions across THIS item (the score).
  const [score, setScore] = useState(0);
  // End-of-item summary screen.
  const [itemDone, setItemDone] = useState(false);

  const item = items[itemIdx];
  const steps = item.steps ?? [];
  const totalItems = items.length;
  const totalSteps = steps.length;
  const step = steps[stepIdx];
  const predict = step?.predict;
  const options = predict?.options ?? [];
  const isLastStep = stepIdx >= totalSteps - 1;

  // An item with no steps is nothing to trace — treat it as instantly done so
  // the arc stays walkable rather than stranding the student on an empty card.
  const itemHasNoSteps = totalSteps === 0;

  // Reset per-step transient state when moving to a fresh step.
  function resetStepState() {
    setPhase("predict");
    setSelected(null);
    setVerdict(null);
    setError(null);
  }

  // Reset per-item state when moving to a fresh item.
  function gotoItem(nextIdx: number) {
    setItemIdx(nextIdx);
    setStepIdx(0);
    setScore(0);
    setItemDone(false);
    resetStepState();
  }

  // ---- Submit the prediction for the current step ----
  async function predictStep(optionIndex: number) {
    if (busy || phase !== "predict" || !step) return;
    setBusy(true);
    setSelected(optionIndex);
    setError(null);
    try {
      const res = await submitGameAnswer<TraceResponse>(
        hwId,
        sessionId,
        "problem-trace",
        {
          item_id: item.id ?? String(itemIdx),
          step_index: stepIdx,
          selected_index: optionIndex,
        }
      );
      setVerdict(res);
      if (res.correct) setScore((sc) => sc + 1);
      // The reveal ALWAYS happens — a worked solution shows its next line
      // whether or not the prediction was right. (advance is informational
      // here; we never trap the student on a wrong prediction.)
      setPhase("revealed");
    } catch (err) {
      // Failed POST: don't strand the student — clear the selection so they can
      // retry the prediction.
      setError((err as Error).message || "Couldn't check that prediction.");
      setSelected(null);
    } finally {
      setBusy(false);
    }
  }

  // ---- Advance from a revealed step to the next step / item summary ----
  function advanceStep() {
    if (isLastStep) {
      setItemDone(true);
      return;
    }
    setStepIdx((i) => i + 1);
    resetStepState();
  }

  // ---- Finish this item → next item or whole-game complete ----
  function finishItem() {
    if (itemIdx + 1 < totalItems) {
      gotoItem(itemIdx + 1);
    } else {
      onComplete();
    }
  }

  const counter = `problem ${itemIdx + 1}/${totalItems}`;

  // Visual state for an MCQ option (server-driven correctness).
  const optState = (i: number) => {
    if (phase === "predict") return selected === i ? "selected" : "idle";
    // revealed: highlight the student's pick correct/wrong.
    if (selected === i) return verdict?.correct ? "correct" : "wrong";
    return "idle";
  };

  // -------------------------------------------------------------------------
  // End-of-item summary (or an item that authored no steps).
  // -------------------------------------------------------------------------
  if (itemDone || itemHasNoSteps) {
    const last = itemIdx + 1 >= totalItems;
    return (
      <GameShell
        title="Problem Trace"
        eyebrow="Practice"
        counter={counter}
        testid="game-problem_trace"
      >
        {item.problem && <p className={s.problem}>{item.problem}</p>}

        {!itemHasNoSteps && (
          // The full derivation, now complete — every line on screen.
          <ol className={s.trace} aria-label="Completed solution trace">
            {steps.map((st2, i) => (
              <li key={st2.id ?? i} className={s.traceStep}>
                <span className={s.traceIndex} aria-hidden="true">
                  {i + 1}
                </span>
                <span className={s.traceText}>{st2.reveal_text}</span>
              </li>
            ))}
          </ol>
        )}

        <div className={s.summary} data-testid="problem_trace-complete">
          <ResultTier tier="Complete" testid="problem_trace-tier" />
          {!itemHasNoSteps && (
            <p className={s.scoreLine}>
              You predicted{" "}
              <strong>
                {score}/{totalSteps}
              </strong>{" "}
              step{totalSteps !== 1 ? "s" : ""} correctly on the first try.
            </p>
          )}
        </div>

        <div className={s.foot}>
          <PressButton onClick={finishItem} data-testid="problem_trace-continue">
            {last ? "Finish →" : "Next problem →"}
          </PressButton>
        </div>
      </GameShell>
    );
  }

  // -------------------------------------------------------------------------
  // Active trace — problem + revealed-so-far derivation + the predict MCQ.
  // -------------------------------------------------------------------------
  return (
    <GameShell
      title="Problem Trace"
      eyebrow="Practice"
      counter={counter}
      testid="game-problem_trace"
    >
      {item.problem && (
        <p className={s.problem} data-testid="problem_trace-problem">
          {item.problem}
        </p>
      )}

      <p className={s.progress}>
        Step {stepIdx + 1} of {totalSteps}
      </p>

      {/* The derivation so far — already-revealed steps stack like a clean,
          math/logic worked solution. The current step appears here only once
          its reveal_text is shown. */}
      {(stepIdx > 0 || phase === "revealed") && (
        <ol
          className={s.trace}
          aria-label="Solution trace so far"
          data-testid="problem_trace-step"
        >
          {steps.slice(0, phase === "revealed" ? stepIdx + 1 : stepIdx).map(
            (st2, i) => {
              const isCurrent = i === stepIdx && phase === "revealed";
              return (
                <li
                  key={st2.id ?? i}
                  className={`${s.traceStep}${isCurrent ? ` ${s.traceStepNew}` : ""}`}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  <span className={s.traceIndex} aria-hidden="true">
                    {i + 1}
                  </span>
                  <span className={s.traceText}>{st2.reveal_text}</span>
                </li>
              );
            }
          )}
        </ol>
      )}

      {/* The prediction card — focused MCQ for the NEXT move. */}
      <div className={s.predictCard} data-testid="problem_trace-predict">
        <p className={s.predictKicker}>
          {phase === "predict" ? "Predict the next step" : "Your prediction"}
        </p>
        {(predict?.question ?? predict?.q) && (
          <p className={s.predictQuestion}>{predict?.question ?? predict?.q}</p>
        )}
        <div className={s.options} role="group" aria-label="Predict the next step">
          {options.map((opt, i) => (
            <PressChoice
              key={i}
              state={optState(i)}
              disabled={busy || phase === "revealed"}
              onClick={() => predictStep(i)}
              data-testid={`problem_trace-option-${i}`}
            >
              {opt}
            </PressChoice>
          ))}
        </div>

        {verdict?.feedback && (
          <p
            className={`${s.feedback}${
              verdict.correct ? ` ${s.feedbackCorrect}` : ` ${s.feedbackWrong}`
            }`}
            role="status"
            aria-live="polite"
          >
            {verdict.feedback}
          </p>
        )}

        {error && (
          <p className={s.error} role="alert">
            {error}
          </p>
        )}
      </div>

      {phase === "revealed" && (
        <div className={s.foot}>
          <PressButton onClick={advanceStep} data-testid="problem_trace-advance">
            {isLastStep ? "See result →" : "Reveal next step →"}
          </PressButton>
        </div>
      )}
    </GameShell>
  );
}
