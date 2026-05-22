import { useEffect, useMemo, useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import {
  GameShell,
  PressButton,
  ResultTier,
  EmptyGuard,
} from "./_practiceShared";
import s from "./Assembly.module.css";

// ---------------------------------------------------------------------------
// Assembly — Practice Arc game (gb_assembly).
//
// The student arranges a shuffled set of pieces into the correct sequence
// (a proof chain, lab protocol, or process steps). The expected order lives
// ONLY on the server (expected_order is in ANSWER_BEARING_KEYS and is redacted
// at hydration). Client-side comparison against expected_order is forbidden.
//
// Phase: "assembly". POST { item_id, order:[orderedPieceIds] } to
// /api/ai/check-answer → { correct, complete?, feedback }. On correct or
// "complete", show ResultTier + advance. On incorrect, show feedback + allow
// retry (pieces keep the student's current arrangement).
//
// EmptyGuard → onComplete() immediately when gb_assembly is absent/empty.
// ---------------------------------------------------------------------------

// ---- Content shapes (client-visible only; expected_order is stripped) ----
interface AssemblyPiece {
  id: string;
  label: string;
}

interface AssemblyItem {
  id: string;
  instructions?: string;
  pieces: AssemblyPiece[];
  // expected_order is intentionally absent — it is redacted server-side
}

// ---- Server response shape ----
interface AssemblyResult {
  correct: boolean;
  complete?: boolean;
  feedback?: string | null;
  result_tier?: string | null;
}

// ---- Fisher-Yates shuffle ----
function shuffle<T>(arr: T[]): T[] {
  const out = arr.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// ---- Move a piece up or down in the list ----
function moveItem<T>(arr: T[], from: number, to: number): T[] {
  if (to < 0 || to >= arr.length) return arr;
  const next = arr.slice();
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

export default function Assembly({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const rawItems = (payload?.content_json?.gb_assembly ?? []) as AssemblyItem[];

  // Current item index through the list
  const [idx, setIdx] = useState(0);

  // The current item
  const item = rawItems[idx] as AssemblyItem | undefined;

  // Shuffled piece-id order — re-seeded per item (keyed on item.id + idx)
  const initialOrder = useMemo(
    () => shuffle((item?.pieces ?? []).map((p) => p.id)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [item?.id, idx],
  );

  const [order, setOrder] = useState<string[]>(initialOrder);
  const [busy, setBusy] = useState(false);
  const [verdict, setVerdict] = useState<AssemblyResult | null>(null);
  const [submitted, setSubmitted] = useState(false);

  // Sync order when the item changes (keyed on item id + idx so each new puzzle
  // gets a freshly shuffled starting order without calling setState during render).
  useEffect(() => {
    setOrder(initialOrder);
    setVerdict(null);
    setSubmitted(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.id, idx]);

  // ---- Guard: empty content ----
  if (rawItems.length === 0) {
    return (
      <EmptyGuard
        title="Assembly"
        message="No assembly puzzles authored for this homework."
        onSkip={onComplete}
        testid="assembly-empty"
      />
    );
  }

  // ---- Guard: past the end ----
  if (!item) {
    onComplete();
    return null;
  }

  // ---- Piece lookup map ----
  const pieceMap = new Map(item.pieces.map((p) => [p.id, p]));

  // ---- Move handler ----
  function handleMove(from: number, to: number) {
    if (busy || submitted) return;
    setOrder((prev) => moveItem(prev, from, to));
  }

  // ---- Submit to server ----
  async function handleSubmit() {
    if (busy || submitted) return;
    if (!hwId || !sessionId) {
      // No active session — soft-pass so the arc stays walkable.
      setVerdict({ correct: true, complete: true, feedback: null });
      setSubmitted(true);
      return;
    }
    setBusy(true);
    try {
      const res = await submitGameAnswer<AssemblyResult>(
        hwId,
        sessionId,
        "assembly",
        { item_id: item!.id, order },
      );
      setVerdict(res);
      setSubmitted(res.correct === true || res.complete === true);
    } catch {
      // Surface a generic error message without blocking the arc
      setVerdict({
        correct: false,
        feedback: "Could not reach the server — check your connection and try again.",
      });
    } finally {
      setBusy(false);
    }
  }

  // ---- Retry: reset verdict, keep student's current arrangement ----
  function handleRetry() {
    setVerdict(null);
    setSubmitted(false);
  }

  // ---- Advance to next item or finish arc ----
  function handleAdvance() {
    if (idx + 1 < rawItems.length) {
      setIdx(idx + 1);
      setVerdict(null);
      setSubmitted(false);
      // order will be reseeded by the useMemo key change
      setOrder(shuffle((rawItems[idx + 1].pieces ?? []).map((p) => p.id)));
    } else {
      onComplete();
    }
  }

  const isCorrect = submitted && verdict?.correct === true;
  const isWrong = verdict !== null && verdict.correct === false;

  return (
    <GameShell
      title="Assembly"
      eyebrow="Practice · Sequence"
      counter={`${idx + 1} / ${rawItems.length}`}
      testid="game-assembly"
    >
      {/* Instructions */}
      <p className={s.instructions}>
        {item.instructions ?? "Arrange the pieces in the correct sequence."}
      </p>

      {/* Ordered draggable rows */}
      {!isCorrect && (
        <ol className={s.list} aria-label="Assembly pieces — use arrows to reorder">
          {order.map((pid, i) => {
            const piece = pieceMap.get(pid);
            const label = piece?.label ?? pid;
            return (
              <li
                key={pid}
                className={s.row}
                data-testid="assembly-piece"
                aria-label={`Step ${i + 1}: ${label}`}
              >
                <span className={s.seq} aria-hidden="true">{i + 1}</span>
                <span className={s.pieceLabel}>{label}</span>
                <span className={s.controls}>
                  <button
                    type="button"
                    className={s.arrowBtn}
                    onClick={() => handleMove(i, i - 1)}
                    disabled={busy || i === 0}
                    aria-label={`Move "${label}" up`}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className={s.arrowBtn}
                    onClick={() => handleMove(i, i + 1)}
                    disabled={busy || i === order.length - 1}
                    aria-label={`Move "${label}" down`}
                  >
                    ↓
                  </button>
                </span>
              </li>
            );
          })}
        </ol>
      )}

      {/* Server feedback */}
      {verdict?.feedback && (
        <p
          className={isCorrect ? s.feedbackCorrect : s.feedbackWrong}
          role="status"
          aria-live="polite"
        >
          {verdict.feedback}
        </p>
      )}

      {/* Result tier on success */}
      {isCorrect && (
        <div className={s.result} data-testid="assembly-complete">
          <ResultTier tier={verdict.result_tier ?? "Well ordered"} />
        </div>
      )}

      {/* Action footer */}
      <div className={s.foot}>
        {isCorrect ? (
          <PressButton onClick={handleAdvance}>
            {idx + 1 < rawItems.length ? "Next →" : "Finish"}
          </PressButton>
        ) : isWrong ? (
          <>
            <PressButton variant="ghost" onClick={handleRetry}>
              Try again
            </PressButton>
            {/* Allow advancing even on wrong to keep arc walkable */}
            <PressButton onClick={handleAdvance}>
              {idx + 1 < rawItems.length ? "Skip item →" : "Finish"}
            </PressButton>
          </>
        ) : (
          <PressButton
            onClick={handleSubmit}
            disabled={busy || order.length === 0}
            data-testid="assembly-submit"
          >
            {busy ? "Checking…" : "Submit order"}
          </PressButton>
        )}
      </div>
    </GameShell>
  );
}
