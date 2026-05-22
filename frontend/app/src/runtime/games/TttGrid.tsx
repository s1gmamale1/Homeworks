import { useMemo, useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import {
  GameShell,
  EmptyGuard,
  PressButton,
  PressChoice,
  CheckpointFlow,
  DPEBox,
  ResultTier,
  StateMeters,
} from "./_practiceShared";
import type { Checkpoint, CheckpointVerdict, DPEResult } from "./_practiceShared";
import s from "./TttGrid.module.css";

// ---------------------------------------------------------------------------
// TTT Grid — "Tic-Tac-Toe Decision Grid" (gb_ttt_grid). NEW.
//
// A SERIOUS decision game, NOT a tic-tac-toe match. Each item walks the student
// through one decision situation as four gates:
//
//   1. concept_checkpoint MCQ — "what concept controls this situation?"
//      → submitGameAnswer(..., "ttt-grid", {item_id, checkpoint_index:0,
//        selected_index}) → {correct, feedback, advance}
//   2. the decision board — cells:[{id,label,type}] laid out in `grid_size`
//      (3x3 or 2x2). The student picks the strongest ACTION cell:
//      → submitGameAnswer(..., "ttt-grid", {item_id, cell_id}) →
//        {correct, feedback, advance}. The server compares cell_id to the
//        server-only best_cell_id; meter_deltas are server-only. The grading
//        RESPONSE drives the <StateMeters> animation (correct cell improves the
//        meters). If the response carries no deltas we show a neutral confirm
//        rather than fabricating movement (forbidden: decorative animation as
//        learning evidence).
//   3. justify_checkpoint MCQ — justify the action / reject the tempting weak
//      strategy → checkpoint_index:1.
//   4. open-ended DPE → {item_id, reasoning_text} (LOCKED pending_ai seam).
//
// Correctness is ALWAYS the server's verdict; this component never holds the
// best cell or any meter delta as authored content (all ⛔ fields are redacted
// at hydration). The board is not solvable by general intuition — the concept
// + justify gates force the reasoning, and the meters reflect SERVER deltas.
//
// Phase: "ttt-grid". Testids: game-ttt_grid, ttt_grid-checkpoint, ttt_grid-cell,
// ttt_grid-dpe, ttt_grid-complete, ttt_grid-empty.
// ---------------------------------------------------------------------------

interface TttCell {
  id: string;
  label?: string;
  type?: string;
}

interface TttMcq {
  question?: string;
  q?: string;
  options?: string[];
}

interface TttGridItem {
  id?: string;
  grid_size?: "3x3" | "2x2";
  concept_checkpoint?: TttMcq;
  cells?: TttCell[];
  justify_checkpoint?: TttMcq;
  dpe_prompt?: string;
  meters?: string[];
}

// Server grading response shapes. Checkpoint + cell pick share the verdict
// envelope; the cell-pick response MAY additionally carry meter deltas / values
// (these are the SERVER's verdict, not redacted authored content). We read them
// defensively under several plausible key names and never invent movement.
interface VerdictRes {
  correct?: boolean;
  feedback?: string | null;
  advance?: boolean;
}

interface CellRes extends VerdictRes {
  /** name → signed delta for the PICKED cell (server-computed, post-decision). */
  meters_delta?: Record<string, number> | null;
  /** name → absolute value (0–100) after THIS move (server-computed). */
  meters?: Record<string, number> | null;
  meter_state?: Record<string, number> | null;
}

const DEFAULT_METERS = [
  "Accuracy",
  "Evidence",
  "Risk",
  "Safety",
  "Clarity",
  "Balance",
  "Efficiency",
];

// Where every meter starts before the student's first decision moves it. A
// mid-rail baseline so improvement (and the rare regression) both read clearly.
const BASELINE_VALUE = 50;

const clamp = (n: number) => Math.max(0, Math.min(100, n));

type Step = "concept" | "board" | "justify" | "dpe";

export default function TttGrid({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_ttt_grid ?? []) as TttGridItem[];

  if (items.length === 0) {
    return (
      <EmptyGuard
        title="Decision Grid"
        message="No decision-grid items authored for this homework."
        onSkip={onComplete}
        testid="game-ttt_grid-empty"
      />
    );
  }

  return (
    <TttGridInner
      hwId={hwId}
      sessionId={sessionId}
      items={items}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// Inner — stateful body (guard above stays a clean early return).
// ---------------------------------------------------------------------------
function TttGridInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: TttGridItem[];
  onComplete: () => void;
}) {
  const [itemIdx, setItemIdx] = useState(0);
  const [step, setStep] = useState<Step>("concept");
  const [done, setDone] = useState(false);

  const item = items[itemIdx];
  const total = items.length;
  const itemId = item.id ?? String(itemIdx);

  const meterNames = item.meters?.length ? item.meters : DEFAULT_METERS;

  // Live meter values for THIS item, seeded at the neutral baseline. The board
  // mutates them from the server's grading response only.
  const [meters, setMeters] = useState<Record<string, number>>(() =>
    Object.fromEntries(meterNames.map((n) => [n, BASELINE_VALUE]))
  );
  // The last move's signed deltas, surfaced as +N / −N chips beside each bar.
  const [deltas, setDeltas] = useState<Record<string, number> | null>(null);

  // Reset per-item state whenever we advance to a new grid.
  function startItem(nextIdx: number) {
    const next = items[nextIdx];
    const names = next.meters?.length ? next.meters : DEFAULT_METERS;
    setItemIdx(nextIdx);
    setStep("concept");
    setMeters(Object.fromEntries(names.map((n) => [n, BASELINE_VALUE])));
    setDeltas(null);
  }

  // ---- Concept + Justify share CheckpointFlow (one MCQ each). ----
  const conceptCp: Checkpoint[] = useMemo(
    () => {
      const q = item.concept_checkpoint?.question ?? item.concept_checkpoint?.q;
      return q
        ? [
            {
              question: q,
              options: item.concept_checkpoint?.options ?? [],
            },
          ]
        : [];
    },
    [item]
  );
  const justifyCp: Checkpoint[] = useMemo(
    () => {
      const q = item.justify_checkpoint?.question ?? item.justify_checkpoint?.q;
      return q
        ? [
            {
              question: q,
              options: item.justify_checkpoint?.options ?? [],
            },
          ]
        : [];
    },
    [item]
  );

  async function submitMcq(
    checkpointIndex: 0 | 1,
    selectedIndex: number
  ): Promise<CheckpointVerdict> {
    try {
      const res = await submitGameAnswer<VerdictRes>(hwId, sessionId, "ttt-grid", {
        item_id: itemId,
        checkpoint_index: checkpointIndex,
        selected_index: selectedIndex,
      });
      return {
        correct: res.correct === true,
        feedback: res.feedback ?? null,
        advance: res.advance,
      };
    } catch {
      // Keep the arc walkable on a transient error: don't claim correct, let
      // the student retry with a calm note.
      return {
        correct: false,
        feedback: "Could not check that — try again.",
        advance: false,
      };
    }
  }

  // Step transitions. A checkpoint with no authored question is skipped via the
  // same handlers, so a sparsely-authored item still walks cleanly.
  function onConceptDone() {
    setStep("board");
  }
  // After the board resolves, go to justify (or straight to DPE if unauthored).
  function onBoardDone() {
    setStep(justifyCp.length ? "justify" : "dpe");
  }
  function onJustifyDone() {
    setStep("dpe");
  }

  function onItemFinished() {
    if (itemIdx + 1 < total) {
      startItem(itemIdx + 1);
    } else {
      setDone(true);
    }
  }

  // ---- Completion screen ----
  if (done) {
    return (
      <GameShell
        title="Decision Grid"
        eyebrow="Practice"
        counter={`${total} grid${total !== 1 ? "s" : ""}`}
        testid="game-ttt_grid"
      >
        <div className={s.complete} data-testid="ttt_grid-complete">
          <ResultTier tier="Done" testid="ttt_grid-tier" />
          <p className={s.completeNote}>
            Every decision graded against the concept it tests — not a guess that
            happened to land. Nice reasoning.
          </p>
          <StateMeters
            meters={meters}
            deltas={deltas}
            order={meterNames}
            testid="ttt_grid-meters"
          />
          <div className={s.foot}>
            <PressButton onClick={onComplete}>Continue →</PressButton>
          </div>
        </div>
      </GameShell>
    );
  }

  const stepLabel = step === "concept" ? "Concept" : step === "board" ? "Decision" : step === "justify" ? "Justify" : "Explain";

  return (
    <GameShell
      title="Decision Grid"
      eyebrow="Practice"
      counter={`Grid ${itemIdx + 1} of ${total} · ${stepLabel}`}
      testid="game-ttt_grid"
    >
      {/* The meters panel is persistent context — the strategy/analytics
          readout the whole decision is measured against. */}
      <section className={s.metersPanel} aria-label="Decision state meters">
        <p className={s.metersHead}>State meters</p>
        <StateMeters
          meters={meters}
          deltas={step === "board" ? deltas : null}
          order={meterNames}
          testid="ttt_grid-meters"
        />
      </section>

      {step === "concept" &&
        (conceptCp.length ? (
          <CheckpointFlow
            checkpoints={conceptCp}
            onAnswer={(_i, sel) => submitMcq(0, sel)}
            onDone={onConceptDone}
            testidPrefix="ttt_grid"
            stepLabel={() => "Which concept controls this situation?"}
          />
        ) : (
          <SkipNote
            label="What concept is being tested"
            onContinue={onConceptDone}
          />
        ))}

      {step === "board" && (
        <BoardStep
          item={item}
          itemId={itemId}
          hwId={hwId}
          sessionId={sessionId}
          meterNames={meterNames}
          onMeters={(nextMeters, nextDeltas) => {
            setMeters(nextMeters);
            setDeltas(nextDeltas);
          }}
          onResolved={onBoardDone}
        />
      )}

      {step === "justify" &&
        (justifyCp.length ? (
          <CheckpointFlow
            checkpoints={justifyCp}
            onAnswer={(_i, sel) => submitMcq(1, sel)}
            onDone={onJustifyDone}
            testidPrefix="ttt_grid"
            stepLabel={() =>
              "Justify the action — and reject the tempting weak play."
            }
          />
        ) : (
          <SkipNote
            label="Justify the action"
            onContinue={onJustifyDone}
          />
        ))}

      {step === "dpe" && (
        <DPEBox
          prompt={
            item.dpe_prompt ??
            "Walk through your decision: what made the strongest cell the right move here?"
          }
          onSubmit={(text): Promise<DPEResult> =>
            submitGameAnswer<DPEResult>(hwId, sessionId, "ttt-grid", {
              item_id: itemId,
              reasoning_text: text,
            })
          }
          onContinue={onItemFinished}
          testidPrefix="ttt_grid"
        />
      )}
    </GameShell>
  );
}

// ---------------------------------------------------------------------------
// BoardStep — the decision grid itself. Renders cells as Apple-glass tiles in
// a 3x3 / 2x2 layout; on pick it POSTs {item_id, cell_id}, then animates the
// meters from the SERVER response (deltas/values), or shows a neutral confirm
// if the response carries no meter movement.
// ---------------------------------------------------------------------------
function BoardStep({
  item,
  itemId,
  hwId,
  sessionId,
  meterNames,
  onMeters,
  onResolved,
}: {
  item: TttGridItem;
  itemId: string;
  hwId: string;
  sessionId: string;
  meterNames: string[];
  onMeters: (
    meters: Record<string, number>,
    deltas: Record<string, number> | null
  ) => void;
  onResolved: () => void;
}) {
  const cells = item.cells ?? [];
  const [picked, setPicked] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<CellRes | null>(null);
  const [busy, setBusy] = useState(false);

  // An item with no cells can't be played — skip it cleanly.
  if (cells.length === 0) {
    return <SkipNote label="No board authored for this grid" onContinue={onResolved} />;
  }

  const cols = item.grid_size === "2x2" ? 2 : 3;

  async function pick(cellId: string) {
    if (busy || verdict?.correct) return;
    setBusy(true);
    setPicked(cellId);
    try {
      const res = await submitGameAnswer<CellRes>(hwId, sessionId, "ttt-grid", {
        item_id: itemId,
        cell_id: cellId,
      });
      setVerdict(res);
      applyMeters(res);
      if (res.correct === true && res.advance !== false) {
        window.setTimeout(onResolved, 820);
      } else if (res.correct !== true) {
        // wrong cell → let them reconsider (meters reflect the server's read)
        setPicked(null);
      }
    } catch {
      setVerdict({
        correct: false,
        feedback: "Could not check that — try another cell.",
        advance: false,
      });
      setPicked(null);
    } finally {
      setBusy(false);
    }
  }

  // Derive the displayed meters from the SERVER response only. Priority:
  //   1. absolute values (meters / meter_state) → use verbatim
  //   2. signed deltas (meter_deltas) → apply to the current baseline
  //   3. neither → neutral confirm (no fabricated movement)
  function applyMeters(res: CellRes) {
    const absolute = res.meters ?? res.meter_state ?? null;
    const d = res.meters_delta ?? null;

    if (absolute && Object.keys(absolute).length) {
      const next: Record<string, number> = {};
      for (const n of meterNames) next[n] = clamp(absolute[n] ?? BASELINE_VALUE);
      // If deltas weren't sent, derive them from baseline → absolute for chips.
      const derived: Record<string, number> = {};
      for (const n of meterNames) derived[n] = next[n] - BASELINE_VALUE;
      onMeters(next, d ?? derived);
      return;
    }

    if (d && Object.keys(d).length) {
      const next: Record<string, number> = {};
      for (const n of meterNames) next[n] = clamp(BASELINE_VALUE + (d[n] ?? 0));
      onMeters(next, d);
      return;
    }

    // Neutral confirm — the response drives the verdict via feedback text; we
    // do NOT invent meter movement (decorative animation ≠ learning evidence).
    onMeters(
      Object.fromEntries(meterNames.map((n) => [n, BASELINE_VALUE])),
      null
    );
  }

  const cellState = (id: string): "idle" | "selected" | "correct" | "wrong" => {
    if (picked !== id) return "idle";
    if (verdict?.correct === true) return "correct";
    // After the early return above, a present verdict here is a wrong pick.
    if (verdict) return "wrong";
    return "selected";
  };

  const locked = busy || verdict?.correct === true;

  return (
    <div data-testid="ttt_grid-board">
      <p className={s.boardPrompt}>
        Read the board. Pick the cell that makes the strongest play — the one the
        controlling concept actually rewards.
      </p>
      <div
        className={s.board}
        data-cols={cols}
        style={{ "--ttt-cols": cols } as React.CSSProperties}
        role="group"
        aria-label="Decision cells"
      >
        {cells.map((cell) => {
          const st = cellState(cell.id);
          const stClass =
            st === "correct"
              ? s.cellCorrect
              : st === "wrong"
              ? s.cellWrong
              : st === "selected"
              ? s.cellSelected
              : "";
          return (
            <PressChoice
              key={cell.id}
              disabled={locked}
              onClick={() => pick(cell.id)}
              className={[s.cell, stClass].filter(Boolean).join(" ")}
              data-testid="ttt_grid-cell"
              data-cell-id={cell.id}
            >
              {cell.type && <span className={s.cellType}>{cell.type}</span>}
              <span className={s.cellLabel}>{cell.label ?? cell.id}</span>
            </PressChoice>
          );
        })}
      </div>

      {verdict?.feedback && (
        <p
          className={[
            s.cellFeedback,
            verdict.correct ? s.cellFeedbackCorrect : s.cellFeedbackWrong,
          ].join(" ")}
          role="status"
          aria-live="polite"
        >
          {verdict.feedback}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SkipNote — graceful inline advance when a checkpoint/board isn't authored,
// keeping a sparsely-authored item walkable without crashing the arc.
// ---------------------------------------------------------------------------
function SkipNote({
  label,
  onContinue,
}: {
  label: string;
  onContinue: () => void;
}) {
  return (
    <div className={s.skipNote}>
      <p className={s.note}>{label} — not authored for this grid. Continue.</p>
      <div className={s.foot}>
        <PressButton variant="ghost" onClick={onContinue}>
          Continue →
        </PressButton>
      </div>
    </div>
  );
}
