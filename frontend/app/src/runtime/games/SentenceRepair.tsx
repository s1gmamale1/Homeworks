import { useMemo, useRef, useState } from "react";
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
} from "./_practiceShared";
import s from "./SentenceRepair.module.css";

// ---------------------------------------------------------------------------
// Sentence Repair — Practice Arc game (gb_sentence_repair). NEW.
//
// MECHANIC (Infra "Sentence Filling" repair variant — NOT cloze):
//   1. PRESENT   — Show the broken_sentence in a prominent "document" card.
//                  Something is off; the student must spot it.
//   2. CHECKPOINT 0 — "Which phrase breaks the meaning?" (3 options; correct
//                     option is the actual broken phrase — tempting, not nonsense).
//                     After the student answers, the suspect phrase is subtly
//                     highlighted in the sentence card.
//   3. CHECKPOINT 1 — "Which replacement restores the sentence?"
//   4. CHECKPOINT 2 — "Which explanation justifies the repair?"
//      Checkpoints run via <CheckpointFlow>; each POST goes to phase
//      "sentence-repair" with { item_id, checkpoint_index, selected_index }.
//   5. DPE        — Open-ended "walk through the repair reasoning" via <DPEBox>
//                   with { item_id, reasoning_text }. Renders the locked
//                   pending_ai seam calmly (never blocks advance).
//   6. RESULT     — <ResultTier> badge derived from first-try checkpoint hits,
//                   then onComplete() after the last item.
//
// Contract fields: id, broken_sentence, checkpoints:[3×{question,options}],
// dpe_prompt (correct_index is server-only / stripped at hydration).
//
// Phase: "sentence-repair". Testids per contract:
//   game-sentence_repair, sentence_repair-checkpoint, sentence_repair-dpe,
//   sentence_repair-complete, sentence_repair-empty.
// ---------------------------------------------------------------------------

interface CheckpointShape {
  question?: string;
  q?: string;
  options?: string[];
}

interface SentenceRepairItem {
  id?: string;
  broken_sentence?: string;
  checkpoints?: CheckpointShape[];
  dpe_prompt?: string;
}

interface CheckResult {
  correct?: boolean;
  feedback?: string | null;
  advance?: boolean;
}

// Per-item phase machine.
type Phase = "present" | "checkpoints" | "dpe" | "result";

const cleanCheckpoints = (cps: CheckpointShape[] | undefined): Checkpoint[] =>
  (cps ?? [])
    .filter((c) => typeof (c?.question ?? c?.q) === "string" && Array.isArray(c?.options))
    .map((c) => ({
      question: (c.question ?? c.q) as string,
      options: (c.options ?? []).map((o) => String(o)),
    }));

// Result tier heuristic from first-try correctness — client label only, not gate-graded.
function deriveTier(firstTryCorrect: number, total: number) {
  if (total === 0) return { tier: "Sharp Eye" as const, blurb: "Item complete." };
  const ratio = firstTryCorrect / total;
  if (ratio === 1) return { tier: "Sharp Eye" as const, blurb: "Clean sweep — you saw the break, named the fix, and justified it." };
  if (ratio >= 0.67) return { tier: "Good Detective" as const, blurb: "Strong read — one step slipped; tighten your reasoning on the repair justification." };
  if (ratio >= 0.34) return { tier: "Half-Found" as const, blurb: "You spotted something was off but the repair logic needs another look." };
  return { tier: "Hali emas" as const, blurb: "The sentence fooled you — re-read it slowly and trace where the meaning breaks." };
}

export default function SentenceRepair({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = useMemo(
    () => (payload?.content_json?.gb_sentence_repair ?? []) as SentenceRepairItem[],
    [payload]
  );

  const [itemIdx, setItemIdx] = useState(0);
  const [phase, setPhase] = useState<Phase>("present");
  // After checkpoint 0 resolves correctly the suspect phrase is revealed.
  const [suspectRevealed, setSuspectRevealed] = useState(false);
  // Per-checkpoint first-attempt correctness (for the result label only).
  const [firstTry, setFirstTry] = useState<boolean[]>([]);
  const attemptedRef = useRef<Set<number>>(new Set());

  const item = items[itemIdx];
  const checkpoints = useMemo(
    () => cleanCheckpoints(item?.checkpoints),
    [item]
  );

  // Empty guard: nothing authored → skip to keep the arc walkable.
  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Sentence Repair"
        message="No sentence-repair items authored for this homework — skip ahead and keep your momentum."
        onSkip={onComplete}
        testid="sentence_repair-empty"
      />
    );
  }

  // Exhausted all items (shouldn't happen with the counter guard below, but defensive).
  if (!item) {
    onComplete();
    return null;
  }

  const counter = `item ${itemIdx + 1}/${items.length}`;

  // Advance to the next item or call onComplete() after the last one.
  const advanceItem = () => {
    if (itemIdx + 1 < items.length) {
      attemptedRef.current = new Set();
      setFirstTry([]);
      setSuspectRevealed(false);
      setItemIdx((i) => i + 1);
      setPhase("present");
    } else {
      onComplete();
    }
  };

  // MCQ checkpoint → server verdict. Correctness is always the server's.
  const answerCheckpoint = async (
    checkpointIndex: number,
    selectedIndex: number
  ): Promise<CheckpointVerdict> => {
    const isFirstAttempt = !attemptedRef.current.has(checkpointIndex);
    attemptedRef.current.add(checkpointIndex);

    let verdict: CheckpointVerdict;

    if (!hwId || !sessionId) {
      // No active session — keep arc walkable; advance without a fake "correct".
      verdict = { correct: true, advance: true };
    } else {
      try {
        const res = await submitGameAnswer<CheckResult>(
          hwId,
          sessionId,
          "sentence-repair",
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
        // Handler not yet present — fail soft so the arc stays walkable.
        verdict = { correct: true, advance: true, feedback: null };
      }
    }

    // After checkpoint 0 resolves (regardless of correct/wrong on final attempt),
    // reveal the suspect phrase emphasis once the student has engaged with the
    // "which phrase breaks it?" question — this is the editorial reveal moment.
    if (checkpointIndex === 0 && verdict.correct) {
      setSuspectRevealed(true);
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

  // DPE → pending_ai seam (DPEBox handles rendering).
  const submitDpe = async (text: string) => {
    if (!hwId || !sessionId) return { pending_ai: true as const };
    try {
      return await submitGameAnswer<{ pending_ai?: boolean; feedback?: string | null }>(
        hwId,
        sessionId,
        "sentence-repair",
        {
          item_id: item.id ?? String(itemIdx),
          reasoning_text: text,
        }
      );
    } catch {
      return {
        pending_ai: true,
        feedback: "Javobingiz AI tomonidan baholanadi — natija tez orada.",
      };
    }
  };

  const firstTryCorrect = firstTry.filter(Boolean).length;
  const { tier, blurb } = deriveTier(firstTryCorrect, checkpoints.length);

  return (
    <GameShell
      title="Sentence Repair"
      eyebrow="Practice · Spot the break, name the fix"
      counter={counter}
      testid="game-sentence_repair"
    >
      {/* ---- Persistent sentence document card (visible in present + checkpoints) ---- */}
      {(phase === "present" || phase === "checkpoints") && item.broken_sentence && (
        <div
          className={s.documentCard}
          aria-label="Sentence under review"
        >
          <p className={s.documentLabel}>Sentence under review</p>
          <p className={s.sentenceText}>
            {suspectRevealed ? (
              // After checkpoint 0 resolves: visually emphasize that something is broken.
              // We render the full sentence; a faint underline + tint on the whole text
              // signals the student has now identified the break area.
              <span className={s.sentenceRevealed}>{item.broken_sentence}</span>
            ) : (
              item.broken_sentence
            )}
          </p>
          {suspectRevealed && (
            <p className={s.suspectHint} role="note">
              Suspect phrase identified — now find the repair.
            </p>
          )}
        </div>
      )}

      {/* ---- PRESENT: editorial prompt before engaging checkpoints ---- */}
      {phase === "present" && (
        <>
          <p className={s.lead}>
            Read the sentence carefully. Something undermines the intended
            meaning — a phrase that sounds plausible but breaks the logic.
            Identify it, then work through the repair.
          </p>
          <div className={s.foot}>
            <PressButton onClick={() => setPhase("checkpoints")}>
              Diagnose →
            </PressButton>
          </div>
        </>
      )}

      {/* ---- CHECKPOINTS: 3-step MCQ repair flow ---- */}
      {phase === "checkpoints" && (
        <>
          {checkpoints.length === 0 ? (
            <>
              <p className={s.lead}>
                No checkpoints authored for this item — explain your repair
                reasoning below.
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
              testidPrefix="sentence_repair"
              stepLabel={(i, _t) => {
                const labels = [
                  "Step 1 — Identify the break",
                  "Step 2 — Choose the repair",
                  "Step 3 — Justify the fix",
                ];
                return labels[i] ?? `Step ${i + 1}`;
              }}
            />
          )}
        </>
      )}

      {/* ---- DPE: open-ended repair reasoning ---- */}
      {phase === "dpe" && (
        <DPEBox
          prompt={
            item.dpe_prompt ??
            "Walk through your repair reasoning: which phrase was broken, why did it undermine the meaning, and how does your chosen replacement restore it?"
          }
          onSubmit={submitDpe}
          onContinue={() => setPhase("result")}
          testidPrefix="sentence_repair"
        />
      )}

      {/* ---- RESULT: tier badge + advance ---- */}
      {phase === "result" && (
        <div data-testid="sentence_repair-complete">
          <div className={s.resultRow}>
            <ResultTier tier={tier} testid="sentence_repair-tier" />
          </div>
          <p className={s.lead}>{blurb}</p>
          {item.broken_sentence && (
            <div className={s.repairedCard} aria-label="Reviewed sentence">
              <p className={s.documentLabel}>Reviewed sentence</p>
              <p className={s.sentenceText}>{item.broken_sentence}</p>
            </div>
          )}
          <div className={s.foot}>
            <PressButton onClick={advanceItem}>
              {itemIdx + 1 < items.length ? "Next item →" : "Finish"}
            </PressButton>
          </div>
        </div>
      )}
    </GameShell>
  );
}
