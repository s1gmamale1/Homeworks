import { useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import {
  GameShell,
  EmptyGuard,
  PressChoice,
  PressButton,
  DPEBox,
  ResultTier,
} from "./_practiceShared";
import type { ResultTierName, DPEResult } from "./_practiceShared";
import s from "./ErrorDetection.module.css";

// ---------------------------------------------------------------------------
// Error Detection — Practice Arc game (gb_error_detection).
//
// Flow per item:
//   SPOT   → student taps a work block → POST {item_id, stage:"spot", block_id}
//            correct → advance to CORRECTION
//            wrong   → mark the tapped block wrong, show penalty, allow retry
//            (after 3 wrong taps: auto-reveal hint if present)
//   CORRECTION → student types the fix → POST {item_id, stage:"correction", correction}
//            correct → if why_prompt exists, advance to WHY; else advance to DONE
//   WHY    → DPEBox → POST {item_id, stage:"why", reasoning_text}
//            resolves pending_ai seam → advance to DONE
//   DONE   → shows ResultTier for the item, then Next / Done
//
// After all items: overall ResultTier from server score or client spot+correction
// accuracy, then calls onComplete().
//
// Server is authoritative (is_broken / correction_answer_spec are redacted).
// ---------------------------------------------------------------------------

interface ErrorDetectionBlock {
  id: string;
  text?: string;
}

interface ErrorDetectionItem {
  id?: string;
  instructions?: string;
  pattern?: string;
  work_blocks?: ErrorDetectionBlock[];
  hint?: string;
  why_prompt?: string;
}

interface SpotResult {
  correct: boolean;
  feedback?: string | null;
  complete?: boolean;
  result_tier?: string | null;
  score?: number | null;
}

interface CorrectionResult {
  correct: boolean;
  feedback?: string | null;
  complete?: boolean;
  result_tier?: string | null;
  score?: number | null;
}

interface WhyResult {
  pending_ai?: boolean;
  feedback?: string | null;
}

type ItemStage = "spot" | "correction" | "why" | "done";

// Derive the ResultTier label from a 0–100 score.
function scoreTier(score: number): ResultTierName {
  if (score >= 85) return "Sharp Eye";
  if (score >= 65) return "Good Detective";
  if (score >= 40) return "Half-Found";
  return "Hali emas";
}

// Client-side tier from per-item performance when the server doesn't return one.
// spotCorrect=true, correctionCorrect=true → 100 (Sharp Eye territory)
// spotWrongs tracks penalty taps; each costs a bit.
function deriveItemTier(
  spotCorrect: boolean,
  correctionCorrect: boolean,
  wrongTaps: number
): ResultTierName {
  if (!spotCorrect || !correctionCorrect) return "Hali emas";
  const penalty = Math.min(wrongTaps * 15, 45);
  const score = 100 - penalty;
  return scoreTier(score);
}

const MAX_WRONG_BEFORE_HINT = 3;

export default function ErrorDetection({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);
  const items = (payload?.content_json?.gb_error_detection ??
    []) as ErrorDetectionItem[];

  // ── per-item state ────────────────────────────────────────────────────────
  const [idx, setIdx] = useState(0);
  const [stage, setStage] = useState<ItemStage>("spot");

  // SPOT stage
  const [pickedBlock, setPickedBlock] = useState<string | null>(null);
  const [wrongBlocks, setWrongBlocks] = useState<Set<string>>(new Set());
  const [wrongCount, setWrongCount] = useState(0);
  const [spotFeedback, setSpotFeedback] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);

  // CORRECTION stage
  const [correction, setCorrection] = useState("");
  const [correctionFeedback, setCorrectionFeedback] = useState<string | null>(null);
  const [correctionCorrect, setCorrectionCorrect] = useState(false);

  // tier tracking across items
  const [itemTierName, setItemTierName] = useState<ResultTierName | null>(null);
  const [overallScore, setOverallScore] = useState<number | null>(null);

  // submission guard
  const [submitting, setSubmitting] = useState(false);
  // track spot correctness for client-side tier fallback
  const [spotCorrectFlag, setSpotCorrectFlag] = useState(false);
  const [wrongCountAtCorrect, setWrongCountAtCorrect] = useState(0);

  // ── empty guard ───────────────────────────────────────────────────────────
  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Error Detection"
        onSkip={onComplete}
        testid="error_detection-empty"
      />
    );
  }

  const item = items[idx];
  if (!item) {
    onComplete();
    return null;
  }

  // ── helpers ───────────────────────────────────────────────────────────────
  function resetForNext() {
    setStage("spot");
    setPickedBlock(null);
    setWrongBlocks(new Set());
    setWrongCount(0);
    setSpotFeedback(null);
    setShowHint(false);
    setCorrection("");
    setCorrectionFeedback(null);
    setCorrectionCorrect(false);
    setItemTierName(null);
    setSpotCorrectFlag(false);
    setWrongCountAtCorrect(0);
  }

  function advanceItem() {
    if (idx + 1 < items.length) {
      setIdx((i) => i + 1);
      resetForNext();
    } else {
      onComplete();
    }
  }

  // ── SPOT stage submission ─────────────────────────────────────────────────
  async function handleSpotTap(blockId: string) {
    if (stage !== "spot" || submitting || pickedBlock === blockId) return;
    if (!hwId || !sessionId) return;
    setSubmitting(true);
    setSpotFeedback(null);
    try {
      const res = await submitGameAnswer<SpotResult>(
        hwId,
        sessionId,
        "error-detection",
        { item_id: item.id ?? String(idx), stage: "spot", block_id: blockId }
      );
      if (res.correct) {
        setPickedBlock(blockId);
        setSpotCorrectFlag(true);
        setWrongCountAtCorrect(wrongCount);
        setSpotFeedback(res.feedback ?? "Correct block found — now write the fix.");
        setStage("correction");
      } else {
        // Wrong tap: mark block, increment penalty, allow retry
        setWrongBlocks((prev) => {
          const next = new Set(prev);
          next.add(blockId);
          return next;
        });
        const newCount = wrongCount + 1;
        setWrongCount(newCount);
        setSpotFeedback(
          res.feedback ?? "That part is correct — look again."
        );
        if (newCount >= MAX_WRONG_BEFORE_HINT && item.hint) {
          setShowHint(true);
        }
      }
    } catch {
      // Optimistic fallback: treat as correct spot so arc stays walkable.
      setPickedBlock(blockId);
      setSpotCorrectFlag(true);
      setWrongCountAtCorrect(wrongCount);
      setStage("correction");
    } finally {
      setSubmitting(false);
    }
  }

  // ── CORRECTION stage submission ───────────────────────────────────────────
  async function handleCorrection() {
    if (submitting || !correction.trim() || !hwId || !sessionId) return;
    setSubmitting(true);
    setCorrectionFeedback(null);
    try {
      const res = await submitGameAnswer<CorrectionResult>(
        hwId,
        sessionId,
        "error-detection",
        {
          item_id: item.id ?? String(idx),
          stage: "correction",
          block_id: pickedBlock,
          correction: correction.trim(),
        }
      );
      setCorrectionFeedback(res.feedback ?? null);
      if (res.correct) {
        setCorrectionCorrect(true);
        // Resolve tier from server score or client derivation
        const tier: ResultTierName = res.result_tier
          ? (res.result_tier as ResultTierName)
          : deriveItemTier(spotCorrectFlag, true, wrongCountAtCorrect);
        setItemTierName(tier);
        if (res.score != null) setOverallScore(res.score);
        // Advance to WHY if prompt exists, else DONE
        if (item.why_prompt) {
          setStage("why");
        } else {
          setStage("done");
        }
      }
      // If wrong: leave in correction stage with feedback, student retries
    } catch {
      setCorrectionCorrect(true);
      setItemTierName(deriveItemTier(spotCorrectFlag, true, wrongCountAtCorrect));
      if (item.why_prompt) {
        setStage("why");
      } else {
        setStage("done");
      }
    } finally {
      setSubmitting(false);
    }
  }

  // ── WHY stage submission (DPEBox handler) ─────────────────────────────────
  async function handleWhySubmit(text: string): Promise<DPEResult> {
    if (!hwId || !sessionId) return { pending_ai: true };
    try {
      const res = await submitGameAnswer<WhyResult>(
        hwId,
        sessionId,
        "error-detection",
        {
          item_id: item.id ?? String(idx),
          stage: "why",
          reasoning_text: text,
        }
      );
      return {
        pending_ai: res.pending_ai ?? true,
        feedback:
          res.feedback ??
          "Javobingiz AI tomonidan baholanadi — natija tez orada.",
      };
    } catch {
      return {
        pending_ai: true,
        feedback: "Javobingiz AI tomonidan baholanadi — natija tez orada.",
      };
    }
  }

  // ── block chip state ──────────────────────────────────────────────────────
  function blockChoiceState(
    blockId: string
  ): React.ComponentProps<typeof PressChoice>["state"] {
    if (stage === "spot") {
      if (wrongBlocks.has(blockId)) return "wrong";
      return "idle";
    }
    // correction / why / done: show the picked block as correct
    if (blockId === pickedBlock) return "correct";
    return "idle";
  }

  // ── render ────────────────────────────────────────────────────────────────
  const blocks = item.work_blocks ?? [];
  const isLastItem = idx + 1 >= items.length;

  // Final overall tier (for last item done screen)
  const finalTierName: ResultTierName =
    overallScore != null
      ? scoreTier(overallScore)
      : itemTierName ?? "Good Detective";

  return (
    <GameShell
      title="Error Detection"
      eyebrow={`Item ${idx + 1} of ${items.length}`}
      counter={item.pattern ? `${item.pattern}` : undefined}
      testid="game-error_detection"
      className={s.shell}
    >
      {/* ── Instructions ── */}
      <p className={s.instructions}>
        {item.instructions ??
          "Find the one broken block, then write the correct version."}
      </p>

      {/* ── Hint ribbon (revealed after MAX_WRONG_BEFORE_HINT wrong taps) ── */}
      {showHint && item.hint && (
        <div className={s.hintBanner} role="note" aria-label="Hint">
          <span className={s.hintIcon} aria-hidden="true">💡</span>
          <span>{item.hint}</span>
        </div>
      )}

      {/* ── Work blocks ── */}
      <div className={s.blocks} role="group" aria-label="Work blocks">
        {blocks.map((b) => {
          const bState = blockChoiceState(b.id);
          const isDisabled =
            stage !== "spot" || submitting;
          return (
            <PressChoice
              key={b.id}
              state={bState}
              className={s.block}
              disabled={isDisabled}
              onClick={() => handleSpotTap(b.id)}
              aria-pressed={b.id === pickedBlock}
              data-testid="error_detection-block"
            >
              {b.text}
            </PressChoice>
          );
        })}
      </div>

      {/* ── Wrong-spot feedback + penalty counter ── */}
      {stage === "spot" && spotFeedback && (
        <div className={s.spotFeedback} role="status" aria-live="polite">
          <span className={s.spotFeedbackText}>{spotFeedback}</span>
          {wrongCount > 0 && (
            <span className={s.penaltyPill} aria-label={`${wrongCount} wrong tap${wrongCount === 1 ? "" : "s"}`}>
              {wrongCount} {wrongCount === 1 ? "miss" : "misses"}
            </span>
          )}
        </div>
      )}

      {/* ── CORRECTION stage ── */}
      {stage === "correction" && (
        <div
          className={s.correctionWrap}
          data-testid="error_detection-correction"
        >
          {spotFeedback && (
            <p className={s.spotSuccessBanner}>{spotFeedback}</p>
          )}
          <label className={s.correctionLabel} htmlFor="ed-correction">
            Write the corrected version
          </label>
          <input
            id="ed-correction"
            type="text"
            className={s.correctionInput}
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && !submitting && handleCorrection()
            }
            placeholder="Type the corrected text here"
            disabled={submitting}
            aria-label="Your correction"
          />
          {correctionFeedback && !correctionCorrect && (
            <p
              className={s.correctionFeedbackWrong}
              role="status"
              aria-live="polite"
            >
              {correctionFeedback}
            </p>
          )}
          <div className={s.foot}>
            <PressButton
              onClick={handleCorrection}
              disabled={!correction.trim() || submitting}
            >
              {submitting ? "Checking…" : "Submit correction"}
            </PressButton>
          </div>
        </div>
      )}

      {/* ── WHY stage (optional DPEBox) ── */}
      {stage === "why" && item.why_prompt && (
        <div
          className={s.whyWrap}
          data-testid="error_detection-why"
        >
          {correctionFeedback && (
            <p className={s.correctionFeedbackCorrect}>{correctionFeedback}</p>
          )}
          <DPEBox
            prompt={item.why_prompt}
            onSubmit={handleWhySubmit}
            onContinue={() => setStage("done")}
            placeholder="Explain why this was the error and what the correct rule is."
            testidPrefix="error_detection"
          />
        </div>
      )}

      {/* ── DONE screen for this item ── */}
      {stage === "done" && (
        <div
          className={s.doneWrap}
          data-testid="error_detection-complete"
        >
          {correctionFeedback && correctionCorrect && (
            <p className={s.correctionFeedbackCorrect}>{correctionFeedback}</p>
          )}

          <div className={s.tierRow}>
            <ResultTier
              tier={isLastItem ? finalTierName : itemTierName ?? undefined}
              testid="error_detection-tier"
            />
            <span className={s.tierLabel}>
              {isLastItem ? "Session complete" : "Item complete"}
            </span>
          </div>

          {isLastItem && (
            <div className={s.tierMeta}>
              <span className={s.tierMetaLine}>
                {finalTierName === "Sharp Eye" &&
                  "Outstanding — you caught it on the first scan."}
                {finalTierName === "Good Detective" &&
                  "Solid work — you found the error and fixed it cleanly."}
                {finalTierName === "Half-Found" &&
                  "You got there — a few extra taps, but the correction landed."}
                {finalTierName === "Hali emas" &&
                  "Keep sharpening the eye — review the pattern and try again."}
              </span>
            </div>
          )}

          <div className={s.foot}>
            <PressButton onClick={advanceItem}>
              {isLastItem ? "Finish" : "Next item →"}
            </PressButton>
          </div>
        </div>
      )}
    </GameShell>
  );
}
