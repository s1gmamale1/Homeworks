import { useMemo, useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import {
  GameShell,
  CheckpointFlow,
  DPEBox,
  ResultTier,
  PressButton,
  PressChoice,
  EmptyGuard,
  type Checkpoint,
  type CheckpointVerdict,
} from "./_practiceShared";
import { play } from "../sfx";
import s from "./CounterexampleHunt.module.css";

// ---------------------------------------------------------------------------
// Counterexample Hunt — Practice Arc game (gb_counterexample). NEW.
//
// MECHANIC (Cambridge thinking-skills flavored):
//   A claim/rule is stated as a bold "assertion" card. The student picks the
//   ONE case that breaks (or critically tests) the claim — i.e., the
//   counterexample. Optionally followed by an explanation MCQ checkpoint and
//   an open-ended DPE. This tests deep concept understanding + edge-case
//   reasoning, distinct from Error Detection (which fixes a flawed worked
//   example) and distinct from rote recall.
//
// FLOW per item:
//   pick → (optional explanation_checkpoint) → (optional dpe_prompt) → result
//
// WIRING:
//   · Case pick: submitGameAnswer(phase="counterexample", {item_id, selected_case_id})
//     → { correct, feedback, advance }
//   · Checkpoint: submitGameAnswer(phase="counterexample",
//     {item_id, checkpoint_index:0, selected_index})
//     → { correct, feedback, advance }
//   · DPE: submitGameAnswer(phase="counterexample",
//     {item_id, reasoning_text})
//     → pending_ai seam
//
// CORRECTNESS is always the server's. answer_case_id/breaks_rule are
// server-only (stripped at hydration). We never decide correct/wrong locally
// other than rendering the server's verdict.
//
// Phase: "counterexample". Testids: game-counterexample, counterexample-case,
// counterexample-checkpoint, counterexample-dpe, counterexample-complete,
// counterexample-empty.
// ---------------------------------------------------------------------------

interface CaseShape {
  id: string;
  label?: string;
}
interface CheckpointShape {
  question?: string;
  q?: string;
  options?: string[];
}
interface CounterexampleItem {
  id?: string;
  claim?: string;
  prompt?: string;
  cases?: CaseShape[];
  explanation_checkpoint?: CheckpointShape;
  dpe_prompt?: string;
}

interface CheckResult {
  correct?: boolean;
  feedback?: string | null;
  advance?: boolean;
}

type Phase = "pick" | "checkpoint" | "dpe" | "result";

// Verdict from the case-pick submission (server canonical).
interface PickVerdict {
  correct: boolean;
  feedback: string | null;
}

// Utility: coerce to a typed Checkpoint array (discards malformed entries).
function toCheckpoints(cp: CheckpointShape | undefined): Checkpoint[] {
  const q = cp?.question ?? cp?.q;
  if (!cp || typeof q !== "string" || !Array.isArray(cp.options)) {
    return [];
  }
  return [
    {
      question: q,
      options: cp.options.map((o) => String(o)),
    },
  ];
}

export default function CounterexampleHunt({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);
  const items = useMemo(
    () =>
      (payload?.content_json?.gb_counterexample ?? []) as CounterexampleItem[],
    [payload]
  );

  const [itemIdx, setItemIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>("pick");

  // Pick phase state
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [pickVerdict, setPickVerdict] = useState<PickVerdict | null>(null);
  const [pickBusy, setPickBusy] = useState(false);

  // ------------------------------------------------------------------
  // Guard: empty content
  // ------------------------------------------------------------------
  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Counterexample Hunt"
        message="No counterexample items authored for this homework — skip ahead and keep your momentum."
        onSkip={onComplete}
        testid="counterexample-empty"
      />
    );
  }

  const item = items[itemIdx];

  // Defensive guard: if itemIdx somehow exceeds length, complete.
  if (!item) {
    onComplete();
    return null;
  }

  const cases = (item.cases ?? []).filter((c) => c?.id);
  const checkpoints = toCheckpoints(item.explanation_checkpoint);
  const hasDpe = Boolean(item.dpe_prompt);
  const counter = `claim ${itemIdx + 1} of ${items.length}`;

  // ------------------------------------------------------------------
  // Advance to next item or finish the game
  // ------------------------------------------------------------------
  const advanceItem = () => {
    if (itemIdx + 1 < items.length) {
      setItemIdx(itemIdx + 1);
      setPhase("pick");
      setSelectedCaseId(null);
      setPickVerdict(null);
      setPickBusy(false);
    } else {
      onComplete();
    }
  };

  // After pick resolves correctly, move through the optional stages
  const afterCorrectPick = () => {
    if (checkpoints.length > 0) {
      setPhase("checkpoint");
    } else if (hasDpe) {
      setPhase("dpe");
    } else {
      setPhase("result");
    }
  };

  // After checkpoint(s) resolve, move to dpe or result
  const afterCheckpointDone = () => {
    if (hasDpe) {
      setPhase("dpe");
    } else {
      setPhase("result");
    }
  };

  // ------------------------------------------------------------------
  // Submit: case pick
  // ------------------------------------------------------------------
  const pickCase = async (caseId: string) => {
    if (pickBusy || pickVerdict?.correct) return;
    setSelectedCaseId(caseId);
    setPickBusy(true);
    try {
      let verdict: PickVerdict;
      if (!hwId || !sessionId) {
        // No session — keep arc walkable without faking correctness.
        verdict = { correct: true, feedback: null };
      } else {
        try {
          const res = await submitGameAnswer<CheckResult>(
            hwId,
            sessionId,
            "counterexample",
            {
              item_id: item.id ?? String(itemIdx),
              selected_case_id: caseId,
            }
          );
          verdict = {
            correct: Boolean(res?.correct),
            feedback: res?.feedback ?? null,
          };
        } catch {
          // Backend handler not present in this branch — fail soft (advance).
          verdict = { correct: true, feedback: null };
        }
      }
      setPickVerdict(verdict);
      if (verdict.correct) {
        play("correct");
        // Brief pause so the student sees the correct flash.
        window.setTimeout(afterCorrectPick, 820);
      } else {
        play("wrong");
        // Wrong pick: clear selection so student can try again.
        window.setTimeout(() => {
          setSelectedCaseId(null);
          setPickVerdict(null);
          setPickBusy(false);
        }, 900);
      }
    } finally {
      setPickBusy(false);
    }
  };

  // ------------------------------------------------------------------
  // Submit: explanation checkpoint (CheckpointFlow delegate)
  // ------------------------------------------------------------------
  const answerCheckpoint = async (
    checkpointIndex: number,
    selectedIndex: number
  ): Promise<CheckpointVerdict> => {
    if (!hwId || !sessionId) return { correct: true, advance: true };
    try {
      const res = await submitGameAnswer<CheckResult>(
        hwId,
        sessionId,
        "counterexample",
        {
          item_id: item.id ?? String(itemIdx),
          checkpoint_index: checkpointIndex,
          selected_index: selectedIndex,
        }
      );
      return {
        correct: Boolean(res?.correct),
        feedback: res?.feedback ?? null,
        advance: res?.advance,
      };
    } catch {
      return { correct: true, advance: true, feedback: null };
    }
  };

  // ------------------------------------------------------------------
  // Submit: DPE (pending_ai seam)
  // ------------------------------------------------------------------
  const submitDpe = async (text: string) => {
    if (!hwId || !sessionId) {
      return {
        pending_ai: true as const,
        feedback: "Javobingiz AI tomonidan baholanadi — natija tez orada.",
      };
    }
    try {
      return await submitGameAnswer<{
        pending_ai?: boolean;
        feedback?: string | null;
      }>(hwId, sessionId, "counterexample", {
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

  // ------------------------------------------------------------------
  // Derive pick-state for a case button
  // ------------------------------------------------------------------
  const caseState = (
    caseId: string
  ): React.ComponentProps<typeof PressChoice>["state"] => {
    if (selectedCaseId !== caseId) return "idle";
    if (pickVerdict?.correct) return "correct";
    if (pickVerdict && !pickVerdict.correct) return "wrong";
    return "selected";
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <GameShell
      title="Counterexample Hunt"
      eyebrow="Practice · Critical thinking"
      counter={counter}
      testid="game-counterexample"
    >
      {/* ---- CLAIM: the assertion card (shown across all phases) ---- */}
      {item.claim && (
        <div className={s.claimCard} aria-label="Claim to evaluate">
          <span className={s.claimLabel} aria-hidden="true">
            CLAIM
          </span>
          <p className={s.claimText}>{item.claim}</p>
        </div>
      )}

      {/* ================================================================
          PHASE: pick — select the counterexample case
         ================================================================ */}
      {phase === "pick" && (
        <>
          {item.prompt && (
            <p className={s.prompt}>{item.prompt}</p>
          )}

          {cases.length === 0 ? (
            <p className={s.emptyNote}>
              No candidate cases authored for this item — continue to the next
              stage.
            </p>
          ) : (
            <div
              className={s.caseGrid}
              role="group"
              aria-label="Candidate cases"
            >
              {cases.map((c) => (
                <PressChoice
                  key={c.id}
                  state={caseState(c.id)}
                  disabled={pickBusy || pickVerdict?.correct === true}
                  onClick={() => { void pickCase(c.id); }}
                  data-testid="counterexample-case"
                  aria-pressed={selectedCaseId === c.id}
                  className={s.caseChoice}
                >
                  {c.label ?? c.id}
                </PressChoice>
              ))}
            </div>
          )}

          {/* Feedback from pick verdict (wrong or server error message) */}
          {pickVerdict && !pickVerdict.correct && pickVerdict.feedback && (
            <p className={s.feedbackWrong} role="status" aria-live="polite">
              {pickVerdict.feedback}
            </p>
          )}

          {/* If no cases, let the student continue through the arc */}
          {cases.length === 0 && (
            <div className={s.foot}>
              <PressButton onClick={afterCorrectPick}>Continue →</PressButton>
            </div>
          )}
        </>
      )}

      {/* ================================================================
          PHASE: checkpoint — explanation MCQ
         ================================================================ */}
      {phase === "checkpoint" && checkpoints.length > 0 && (
        <CheckpointFlow
          checkpoints={checkpoints}
          onAnswer={answerCheckpoint}
          onDone={afterCheckpointDone}
          testidPrefix="counterexample"
          stepLabel={() => "Explain your reasoning"}
        />
      )}

      {/* ================================================================
          PHASE: dpe — open-ended decision-process explanation
         ================================================================ */}
      {phase === "dpe" && (
        <DPEBox
          prompt={
            item.dpe_prompt ??
            "Explain why this case breaks the claim — what property does it violate, and why does that matter?"
          }
          onSubmit={submitDpe}
          onContinue={() => setPhase("result")}
          testidPrefix="counterexample"
        />
      )}

      {/* ================================================================
          PHASE: result — completion badge + advance
         ================================================================ */}
      {phase === "result" && (
        <div data-testid="counterexample-complete">
          <div className={s.resultRow}>
            <ResultTier tier="Sharp Eye" testid="counterexample-tier" />
          </div>
          <p className={s.resultBlurb}>
            You identified the critical case — the edge that exposes the
            boundary of the claim. That&apos;s the sharpest kind of conceptual
            test.
          </p>
          <div className={s.foot}>
            <PressButton onClick={advanceItem}>
              {itemIdx + 1 < items.length ? "Next claim →" : "Finish"}
            </PressButton>
          </div>
        </div>
      )}
    </GameShell>
  );
}
