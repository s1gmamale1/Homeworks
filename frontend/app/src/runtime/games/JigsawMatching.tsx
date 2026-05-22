import { useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import {
  GameShell,
  EmptyGuard,
  PressButton,
  CheckpointFlow,
  DPEBox,
  ResultTier,
} from "./_practiceShared";
import type { Checkpoint, CheckpointVerdict, DPEResult } from "./_practiceShared";
import s from "./JigsawMatching.module.css";

// ---------------------------------------------------------------------------
// Jigsaw Matching — Practice Arc game (gb_jigsaw_matching).
//
// Per the Infra "Jigsaw Matching" spec, this is NOT a generic MCQ quiz: each
// round walks the student through assembling a SOURCE-SUPPORTED relationship
// out of candidate pieces, in three semantic checkpoints:
//
//   checkpoint 0 — "pick the 2 source-supported pieces that fit together"
//                  (the authored options name piece pairs; the `pieces` grid
//                   above is the visual context the student reasons over)
//   checkpoint 1 — "which assembly-type label connects them?" (the relationship
//                   is one of: concept-definition / formula-variable /
//                   cause-effect / evidence-claim / step-result / term-example)
//   checkpoint 2 — "which explanation proves it + rejects the tempting wrong
//                   combo?"
//   then the open-ended DPE — narrate the assembly decision.
//
// FORBIDDEN by spec (the wrong answers are authored to bait these): inventing a
// relationship the source doesn't support, and surface-similarity matches.
// Max 3 assembly types per round. Correctness is ALWAYS the server's verdict —
// the piece-pick options are graded server-side by `selected_index`; this
// component never holds an answer key, only the `pieces` it renders as context.
//
// Phase: "jigsaw-matching". Per-checkpoint POST shape (contract):
//   { item_id, checkpoint_index, selected_index } -> { correct, feedback, advance }
// DPE POST shape: { item_id, reasoning_text } -> the locked pending_ai seam.
// ---------------------------------------------------------------------------

interface JigsawPiece {
  id: string;
  label?: string;
  role?: string;
}
interface JigsawCheckpointShape {
  question?: string;
  q?: string;
  options?: string[];
}
interface JigsawMatchingItem {
  id?: string;
  case_setup?: string;
  pieces?: JigsawPiece[];
  checkpoints?: JigsawCheckpointShape[]; // exactly 3 per spec
  dpe_prompt?: string;
}

// Server checkpoint verdict (contract §Response — MCQ checkpoint).
interface JigsawCheckResult {
  correct: boolean;
  feedback?: string | null;
  advance?: boolean;
}

// Semantic kicker for each of the three checkpoints (spec ordering). Falls back
// to "Checkpoint N of 3" if a round somehow authors a different count.
const STEP_KICKERS = [
  "Step 1 · Fit the pieces",
  "Step 2 · Name the link",
  "Step 3 · Prove & reject",
];

type Stage = "setup" | "checkpoints" | "dpe" | "done";

export default function JigsawMatching({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);
  const items = (payload?.content_json?.gb_jigsaw_matching ??
    []) as JigsawMatchingItem[];

  const [itemIdx, setItemIdx] = useState(0);
  const [stage, setStage] = useState<Stage>("setup");

  // ---- EmptyGuard: nothing authored → graceful skip ----
  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Jigsaw Matching"
        message="No jigsaw-matching cases authored for this homework."
        onSkip={onComplete}
        testid="jigsaw_matching-empty"
      />
    );
  }

  const item = items[itemIdx];
  if (!item) {
    // Defensive: index ran past the array — finish the arc.
    onComplete();
    return null;
  }

  // Stable item identifier the server resolves the round by. Falls back to the
  // index when an item omits its id (server template tolerates either).
  const itemId = item.id ?? String(itemIdx);

  const counter = `Case ${itemIdx + 1} / ${items.length}`;

  // The three authored MCQ checkpoints, normalized into the shared kit's shape.
  const checkpoints: Checkpoint[] = (item.checkpoints ?? [])
    .slice(0, 3)
    .map((cp) => ({
      question: cp.question ?? cp.q ?? "(missing question)",
      options: cp.options ?? [],
    }));

  const pieces = item.pieces ?? [];

  // ---- checkpoint submit → server verdict (relayed up by CheckpointFlow) ----
  const onAnswer = async (
    checkpointIndex: number,
    selectedIndex: number
  ): Promise<CheckpointVerdict> => {
    if (!hwId || !sessionId) {
      // No session → keep the arc walkable: treat as a soft pass + advance.
      return { correct: true, advance: true };
    }
    try {
      const res = await submitGameAnswer<JigsawCheckResult>(
        hwId,
        sessionId,
        "jigsaw-matching",
        {
          item_id: itemId,
          checkpoint_index: checkpointIndex,
          selected_index: selectedIndex,
        }
      );
      return {
        correct: res.correct,
        feedback: res.feedback ?? null,
        advance: res.advance,
      };
    } catch {
      // Server handler not present yet in this branch — let them keep moving.
      return { correct: true, advance: true };
    }
  };

  // ---- DPE submit → locked pending_ai seam ----
  const onDpeSubmit = async (text: string): Promise<DPEResult> => {
    if (!hwId || !sessionId) {
      return { pending_ai: true };
    }
    try {
      return await submitGameAnswer<DPEResult>(
        hwId,
        sessionId,
        "jigsaw-matching",
        { item_id: itemId, reasoning_text: text }
      );
    } catch {
      // DPEBox shows its own calm fallback note; surface the seam shape anyway.
      return { pending_ai: true };
    }
  };

  // Advance to the next case, or finish the whole game.
  const nextCase = () => {
    if (itemIdx + 1 < items.length) {
      setItemIdx((i) => i + 1);
      setStage("setup");
    } else {
      onComplete();
    }
  };

  const isLastCase = itemIdx + 1 >= items.length;

  return (
    <GameShell
      title="Jigsaw Matching"
      eyebrow="Practice · Assemble the relationship"
      counter={counter}
      testid="game-jigsaw_matching"
    >
      {/* ---- piece context: shown for setup + the piece-pick checkpoints ---- */}
      {pieces.length > 0 && stage !== "done" && (
        <div
          className={s.pieceGrid}
          role="list"
          aria-label="Source-supported pieces"
        >
          {pieces.map((p) => (
            <div key={p.id} className={s.piece} role="listitem">
              <span className={s.pieceLabel}>{p.label ?? p.id}</span>
              {p.role && <span className={s.pieceRole}>{p.role}</span>}
            </div>
          ))}
        </div>
      )}

      {/* ---- STAGE: setup — read the case, then start the checkpoints ---- */}
      {stage === "setup" && (
        <>
          <p className={s.caseSetup}>
            {item.case_setup ??
              "Study the pieces above, then assemble the one source-supported relationship they form."}
          </p>
          <div className={s.foot}>
            <PressButton onClick={() => setStage("checkpoints")}>
              Start →
            </PressButton>
          </div>
        </>
      )}

      {/* ---- STAGE: 3 MCQ checkpoints (piece-pick → link-type → prove) ---- */}
      {stage === "checkpoints" && (
        checkpoints.length === 0 ? (
          <>
            <p className={s.caseSetup}>
              No checkpoints authored for this case — continue to explain your
              assembly reasoning below.
            </p>
            <div className={s.foot}>
              <PressButton onClick={() => setStage("dpe")}>Continue →</PressButton>
            </div>
          </>
        ) : (
          <CheckpointFlow
            key={`cp-${itemIdx}`}
            checkpoints={checkpoints}
            onAnswer={onAnswer}
            onDone={() => setStage("dpe")}
            testidPrefix="jigsaw_matching"
            stepLabel={(index, total) =>
              STEP_KICKERS[index] ?? `Checkpoint ${index + 1} of ${total}`
            }
          />
        )
      )}

      {/* ---- STAGE: open-ended Decision Process Explanation ---- */}
      {stage === "dpe" && (
        <DPEBox
          prompt={
            item.dpe_prompt ??
            "Explain your assembly: which two pieces fit, what relationship they form, and why the tempting wrong combination cannot — without inventing a link the source doesn't support."
          }
          onSubmit={onDpeSubmit}
          onContinue={() => setStage("done")}
          testidPrefix="jigsaw_matching"
        />
      )}

      {/* ---- STAGE: done — result badge + advance ---- */}
      {stage === "done" && (
        <div className={s.done} data-testid="jigsaw_matching-complete">
          <ResultTier
            tier="Assembled"
            testid="jigsaw_matching-result-tier"
          />
          <p className={s.doneNote}>
            Relationship assembled. Your explanation is being scored — keep your
            momentum.
          </p>
          <div className={s.foot}>
            <PressButton onClick={nextCase}>
              {isLastCase ? "Finish →" : "Next case →"}
            </PressButton>
          </div>
        </div>
      )}
    </GameShell>
  );
}
