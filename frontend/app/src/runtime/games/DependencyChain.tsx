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
import s from "./DependencyChain.module.css";

// ---------------------------------------------------------------------------
// Dependency Chain — Practice Arc game (gb_dependency_chain). NEW.
//
// MECHANIC (AP/IB/Cambridge TRANSFER flavored):
//   A scenario frames a multi-step problem. The student SOLVES a sequence of
//   linked sub-questions where each answer FEEDS the next: Q1 is solved → its
//   result (a `carry`, e.g. "x = 5 →") carries into Q2's prompt → … → final
//   step. This tests genuine transfer / multi-step application — the student
//   must carry an intermediate result forward and apply it again.
//
//   DISTINCT FROM problem_trace: problem_trace reveals a GIVEN worked solution
//   one line at a time (the student predicts the author's next move). HERE the
//   student actually computes each linked step, and a wrong step blocks the
//   chain until corrected (a chain is only as strong as its weakest link).
//
// FLOW per item:
//   render scenario + chain progress → for each step show its MCQ prompt
//   (prefixed by the prior step's carry once unlocked) → on CORRECT the server
//   returns `carry`, which we surface as the link feeding the next step → after
//   the final step a ResultTier with the cumulative score.
//
// WIRING (contract §dependency-chain): per step POST
//   submitGameAnswer(hwId, sessionId, "dependency-chain",
//     { item_id, step_index, selected_index }) → { correct, feedback, advance, carry? }
//   `correct_index` + `carry_label` are server-only (redacted at hydration);
//   the carry is delivered ONLY in the response of a correct answer. The chain
//   is the server's truth — we never decide correctness locally.
//
// Phase: "dependency-chain". Testids: game-dependency_chain,
// dependency_chain-step, dependency_chain-option-<i>, dependency_chain-carry,
// dependency_chain-complete, dependency_chain-empty.
// ---------------------------------------------------------------------------

interface ChainStep {
  id?: string;
  prompt?: string;
  options?: string[];
  carry_label?: string; // server-only — never present at hydration; ignored if leaked.
}

interface DependencyChainItem {
  id?: string;
  scenario?: string;
  steps?: ChainStep[];
}

interface StepResponse {
  correct: boolean;
  feedback?: string | null;
  advance?: boolean;
  carry?: string | null;
}

export default function DependencyChain({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_dependency_chain ??
    []) as DependencyChainItem[];

  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Dependency Chain"
        message="No dependency-chain items authored for this homework — skip ahead and keep your momentum."
        onSkip={onComplete}
        testid="game-dependency_chain-empty"
      />
    );
  }

  return (
    <DependencyChainInner
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
function DependencyChainInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: DependencyChainItem[];
  onComplete: () => void;
}) {
  const [itemIdx, setItemIdx] = useState(0);
  // Which link in the chain the student is currently solving.
  const [stepIdx, setStepIdx] = useState(0);
  // Tapped option for the current step (drives correct/wrong highlight).
  const [selected, setSelected] = useState<number | null>(null);
  // Server verdict for the current step.
  const [verdict, setVerdict] = useState<StepResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Carries surfaced by the server on each CORRECT step, index-aligned to steps.
  // carries[i] = the result that step i produced (feeds step i+1's prompt).
  const [carries, setCarries] = useState<Record<number, string>>({});
  // Correct FIRST-TRY steps across THIS item (the cumulative score).
  const [score, setScore] = useState(0);
  // True once the student has wrongly answered the current step at least once.
  const [stumbled, setStumbled] = useState(false);
  // End-of-item summary screen.
  const [itemDone, setItemDone] = useState(false);

  const item = items[itemIdx];
  const steps = item.steps ?? [];
  const totalItems = items.length;
  const totalSteps = steps.length;
  const step = steps[stepIdx];
  const options = step?.options ?? [];
  const isLastStep = stepIdx >= totalSteps - 1;

  // An item with no steps is nothing to solve — treat it as instantly done so
  // the arc stays walkable rather than stranding the student.
  const itemHasNoSteps = totalSteps === 0;

  function resetStepState() {
    setSelected(null);
    setVerdict(null);
    setError(null);
    setStumbled(false);
  }

  function gotoItem(nextIdx: number) {
    setItemIdx(nextIdx);
    setStepIdx(0);
    setCarries({});
    setScore(0);
    setItemDone(false);
    resetStepState();
  }

  // ---- Submit the answer for the current link in the chain ----
  async function solveStep(optionIndex: number) {
    if (busy || verdict?.correct || !step) return;
    setBusy(true);
    setSelected(optionIndex);
    setError(null);
    try {
      let res: StepResponse;
      if (!hwId || !sessionId) {
        // No session — keep the arc walkable without faking the carry.
        res = { correct: true, feedback: null, advance: isLastStep };
      } else {
        res = await submitGameAnswer<StepResponse>(
          hwId,
          sessionId,
          "dependency-chain",
          {
            item_id: item.id ?? String(itemIdx),
            step_index: stepIdx,
            selected_index: optionIndex,
          }
        );
      }
      setVerdict(res);
      if (res.correct) {
        // First-try correct (never stumbled on this step) scores a point.
        if (!stumbled) setScore((sc) => sc + 1);
        // The server surfaces the carried result ONLY on a correct answer.
        if (typeof res.carry === "string" && res.carry) {
          const carry = res.carry;
          setCarries((prev) => ({ ...prev, [stepIdx]: carry }));
        }
        // Pause so the student sees the correct flash + the new link forming,
        // then advance to the next step (or the item summary).
        window.setTimeout(() => {
          if (isLastStep) {
            setItemDone(true);
          } else {
            setStepIdx((i) => i + 1);
            resetStepState();
          }
        }, 820);
      } else {
        // Wrong link: the chain holds here. Mark stumbled (so a later correct
        // answer no longer scores first-try) and let the student retry.
        setStumbled(true);
        window.setTimeout(() => {
          setSelected(null);
          setVerdict(null);
        }, 900);
      }
    } catch (err) {
      setError((err as Error).message || "Couldn't check that step.");
      setSelected(null);
    } finally {
      setBusy(false);
    }
  }

  function finishItem() {
    if (itemIdx + 1 < totalItems) {
      gotoItem(itemIdx + 1);
    } else {
      onComplete();
    }
  }

  const counter = `chain ${itemIdx + 1}/${totalItems}`;

  // Visual state for an MCQ option (server-driven correctness).
  const optState = (i: number) => {
    if (selected !== i) return "idle";
    if (verdict?.correct) return "correct";
    if (verdict && !verdict.correct) return "wrong";
    return "selected";
  };

  // The carry produced by the immediately-preceding step (feeds this prompt).
  const incomingCarry = stepIdx > 0 ? carries[stepIdx - 1] : undefined;

  // -------------------------------------------------------------------------
  // End-of-item summary (or an item that authored no steps).
  // -------------------------------------------------------------------------
  if (itemDone || itemHasNoSteps) {
    const last = itemIdx + 1 >= totalItems;
    const tier = !itemHasNoSteps && score === totalSteps ? "Sharp Eye" : "Complete";
    return (
      <GameShell
        title="Dependency Chain"
        eyebrow="Practice · Multi-step transfer"
        counter={counter}
        testid="game-dependency_chain"
      >
        {item.scenario && <p className={s.scenario}>{item.scenario}</p>}

        {!itemHasNoSteps && (
          // The completed chain — every solved link with its carried result.
          <ol className={s.chain} aria-label="Completed dependency chain">
            {steps.map((st2, i) => (
              <li key={st2.id ?? i} className={s.link}>
                <span className={s.linkIndex} aria-hidden="true">
                  {i + 1}
                </span>
                <span className={s.linkBody}>
                  <span className={s.linkPrompt}>{st2.prompt}</span>
                  {carries[i] && (
                    <span className={s.carryDone}>{carries[i]}</span>
                  )}
                </span>
              </li>
            ))}
          </ol>
        )}

        <div className={s.summary} data-testid="dependency_chain-complete">
          <ResultTier tier={tier} testid="dependency_chain-tier" />
          {!itemHasNoSteps && (
            <p className={s.scoreLine}>
              You solved{" "}
              <strong>
                {score}/{totalSteps}
              </strong>{" "}
              link{totalSteps !== 1 ? "s" : ""} on the first try — carrying each
              result forward through the chain.
            </p>
          )}
        </div>

        <div className={s.foot}>
          <PressButton onClick={finishItem} data-testid="dependency_chain-continue">
            {last ? "Finish →" : "Next chain →"}
          </PressButton>
        </div>
      </GameShell>
    );
  }

  // -------------------------------------------------------------------------
  // Active chain — scenario + progress + already-forged links + current step.
  // -------------------------------------------------------------------------
  return (
    <GameShell
      title="Dependency Chain"
      eyebrow="Practice · Multi-step transfer"
      counter={counter}
      testid="game-dependency_chain"
    >
      {item.scenario && (
        <p className={s.scenario} data-testid="dependency_chain-scenario">
          {item.scenario}
        </p>
      )}

      {/* Chain progress rail — one node per link, filled as the chain forges. */}
      {totalSteps > 1 && (
        <div className={s.rail} role="img" aria-label={`Step ${stepIdx + 1} of ${totalSteps}`}>
          {steps.map((_, i) => (
            <span
              key={i}
              className={`${s.node}${
                i < stepIdx ? ` ${s.nodeDone}` : i === stepIdx ? ` ${s.nodeActive}` : ""
              }`}
            >
              {i < totalSteps - 1 && <span className={s.connector} aria-hidden="true" />}
            </span>
          ))}
        </div>
      )}

      <p className={s.progress}>
        Link {stepIdx + 1} of {totalSteps}
      </p>

      {/* The current link's MCQ — prefixed by the prior step's carried result. */}
      <div className={s.stepCard} data-testid="dependency_chain-step">
        {incomingCarry && (
          <p className={s.carryIn} data-testid="dependency_chain-carry">
            <span className={s.carryChip}>{incomingCarry}</span>
            <span className={s.carryNote}>carry this forward</span>
          </p>
        )}
        {step?.prompt && <p className={s.stepPrompt}>{step.prompt}</p>}
        <div className={s.options} role="group" aria-label="Solve this step">
          {options.map((opt, i) => (
            <PressChoice
              key={i}
              state={optState(i)}
              disabled={busy || verdict?.correct === true}
              onClick={() => solveStep(i)}
              data-testid={`dependency_chain-option-${i}`}
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

        {/* The link forming the moment a step resolves correctly. */}
        {verdict?.correct && carries[stepIdx] && (
          <p className={s.carryOut} role="status" aria-live="polite">
            <span className={s.carryChip}>{carries[stepIdx]}</span>
            <span className={s.carryNote}>feeds the next link</span>
          </p>
        )}

        {error && (
          <p className={s.error} role="alert">
            {error}
          </p>
        )}
      </div>
    </GameShell>
  );
}
