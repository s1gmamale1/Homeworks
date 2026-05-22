import { useReducer, useRef, useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Pill, Button, FeatureCard } from "../../shared/ui/primitives";
import { play } from "../sfx";
import s from "./Ttt.module.css";

// ---------------------------------------------------------------------------
// Tic-Tac-Toe Quiz — gb_ttt Practice Arc game.
//
// Wire format (injector-redacted, server-authoritative):
//   gb_ttt: Array<{ id: string; q: string; options: string[] }>
//   gb_ttt_config: { session_games?: number; ... }
//
// The client NEVER holds correct answers. To claim a cell the student picks
// one of the four shuffled `options`; we POST { item_id, picked } to
// phase="ttt". The server returns { is_correct, mercy, xp_delta, correct_value }.
//
//   Correct → student (X) claims the cell.
//   Wrong + mercy → student still claims the cell ("lucky bounce").
//   Wrong (no mercy) → opponent (O) claims the cell.
//
// One round ends when someone wins (3-in-a-row) or the board is full (draw).
// After `session_games` rounds the ttt-session tally is posted and onComplete
// fires.
// ---------------------------------------------------------------------------

// ---- inline types (do NOT touch shared/types.ts) -------------------------

interface TttWireItem {
  id: string;
  q: string;
  options: string[]; // 4 options, shuffled server-side; correct unknown client-side
}

interface TttPickResult {
  is_correct: boolean;
  mercy: boolean;
  xp_delta: number;
  correct_value: string;
}

interface TttSessionResult {
  session_xp: number;
  strong_session_bonus: number;
  mastery_tier: string;
  duolingo_remediation: boolean;
  wins: number;
  draws: number;
  losses: number;
}

type CellState = "empty" | "X" | "O";
type GameOutcome = "win" | "draw" | "loss";

// ---- win-line detection (pure, client is only used for UI feedback) --------

const WIN_LINES = [
  [0, 1, 2],
  [3, 4, 5],
  [6, 7, 8],
  [0, 3, 6],
  [1, 4, 7],
  [2, 5, 8],
  [0, 4, 8],
  [2, 4, 6],
] as const;

function detectWinner(board: CellState[]): { winner: CellState | null; line: number[] | null } {
  for (const line of WIN_LINES) {
    const [a, b, c] = line;
    if (board[a] !== "empty" && board[a] === board[b] && board[b] === board[c]) {
      return { winner: board[a], line: [...line] };
    }
  }
  return { winner: null, line: null };
}

function isBoardFull(board: CellState[]): boolean {
  return board.every((c) => c !== "empty");
}

// ---- assign questions to cells deterministically --------------------------
// Items are shuffled server-side; we assign them round-robin to cells 0-8.
// If fewer than 9 items: wrap (modulo index).

function assignItemsToBoard(items: TttWireItem[]): TttWireItem[] {
  if (items.length === 0) return [];
  return Array.from({ length: 9 }, (_, i) => items[i % items.length]);
}

// ---- game-round reducer ---------------------------------------------------

interface RoundState {
  board: CellState[];
  outcome: GameOutcome | null; // null while game in progress
  winLine: number[] | null;
}

const freshRound = (): RoundState => ({
  board: Array(9).fill("empty") as CellState[],
  outcome: null,
  winLine: null,
});

type RoundAction =
  | { type: "CLAIM"; cell: number; marker: "X" | "O" }
  | { type: "RESET" };

function roundReducer(state: RoundState, action: RoundAction): RoundState {
  if (action.type === "RESET") return freshRound();
  if (action.type === "CLAIM") {
    const next = [...state.board] as CellState[];
    next[action.cell] = action.marker;
    const { winner, line } = detectWinner(next);
    let outcome: GameOutcome | null = null;
    if (winner === "X") outcome = "win";
    else if (winner === "O") outcome = "loss";
    else if (isBoardFull(next)) outcome = "draw";
    return { board: next, outcome, winLine: line };
  }
  return state;
}

// ---- main component -------------------------------------------------------

export default function Ttt({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rawItems: TttWireItem[] = (payload?.content_json as any)?.gb_ttt ?? [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const config = (payload?.content_json as any)?.gb_ttt_config ?? {};
  const sessionGames: number = config.session_games ?? 3;

  const cellItems = assignItemsToBoard(rawItems);

  // session-level state
  const [gameIndex, setGameIndex] = useState(0); // 0-based round counter
  const [outcomes, setOutcomes] = useState<GameOutcome[]>([]);
  const [sessionDone, setSessionDone] = useState(false);
  const [sessionResult, setSessionResult] = useState<TttSessionResult | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  // round state (reducer)
  const [round, dispatch] = useReducer(roundReducer, undefined, freshRound);

  // question modal state
  const [openCell, setOpenCell] = useState<number | null>(null);
  const [pickedOption, setPickedOption] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [verdict, setVerdict] = useState<TttPickResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ref to track latest outcomes for post-round async callback
  const outcomesRef = useRef<GameOutcome[]>([]);
  outcomesRef.current = outcomes;

  // Empty content guard — graceful skip
  if (rawItems.length === 0) {
    return (
      <FeatureCard>
        <div className={s.wrap} data-testid="ttt-empty">
          <Eyebrow>Tic-Tac-Toe</Eyebrow>
          <Title size="section">No questions here.</Title>
          <Lead>This homework has no Tic-Tac-Toe questions.</Lead>
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete} data-testid="ttt-skip">
              Skip →
            </Button>
          </div>
        </div>
      </FeatureCard>
    );
  }

  // ---- cell click handler -------------------------------------------------

  const onCellClick = (cellIndex: number) => {
    if (round.outcome !== null) return; // round already over
    if (round.board[cellIndex] !== "empty") return; // already claimed
    if (submitting || openCell !== null) return;
    setOpenCell(cellIndex);
    setPickedOption(null);
    setVerdict(null);
    setSubmitError(null);
  };

  // ---- submit answer to server --------------------------------------------

  const onSubmitPick = async () => {
    if (openCell === null || pickedOption === null) return;
    const item = cellItems[openCell];
    if (!item) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await submitGameAnswer<TttPickResult>(hwId, sessionId, "ttt", {
        item_id: item.id,
        picked: pickedOption,
      });
      setVerdict(res);
    } catch (err) {
      setSubmitError((err as Error).message || "Could not check that answer.");
    } finally {
      setSubmitting(false);
    }
  };

  // ---- confirm verdict and update board ------------------------------------

  const onConfirmVerdict = () => {
    if (!verdict || openCell === null) return;

    const marker: "X" | "O" = verdict.is_correct || verdict.mercy ? "X" : "O";
    if (verdict.is_correct || verdict.mercy) {
      play("correct");
    } else {
      play("wrong");
    }
    dispatch({ type: "CLAIM", cell: openCell, marker });

    // peek at what the board will look like after this claim for outcome detection
    const nextBoard = [...round.board] as CellState[];
    nextBoard[openCell] = marker;
    const { winner } = detectWinner(nextBoard);
    const full = nextBoard.every((c) => c !== "empty");

    let roundOutcome: GameOutcome | null = null;
    if (winner === "X") roundOutcome = "win";
    else if (winner === "O") roundOutcome = "loss";
    else if (!winner && full) roundOutcome = "draw";

    // close modal
    setOpenCell(null);
    setPickedOption(null);
    setVerdict(null);
    setSubmitError(null);

    if (roundOutcome !== null) {
      if (roundOutcome === "win") play("complete");
      // round just ended — record and advance
      const nextOutcomes = [...outcomesRef.current, roundOutcome];
      setOutcomes(nextOutcomes);
      if (nextOutcomes.length >= sessionGames) {
        // session complete — post tally
        postSessionTally(nextOutcomes);
      }
      // The round reducer will update the board with CLAIM + set outcome
      // via the next render; we trigger a visual "next round" after a pause.
    }
  };

  const startNextRound = () => {
    dispatch({ type: "RESET" });
    setGameIndex((i) => i + 1);
    setOpenCell(null);
    setPickedOption(null);
    setVerdict(null);
    setSubmitError(null);
  };

  // ---- post session tally -------------------------------------------------

  const postSessionTally = async (finalOutcomes: GameOutcome[]) => {
    try {
      const res = await submitGameAnswer<TttSessionResult>(hwId, sessionId, "ttt-session", {
        results: finalOutcomes.map((outcome) => ({ outcome })),
      });
      setSessionResult(res);
    } catch (err) {
      setSessionError((err as Error).message || "Could not save session results.");
    } finally {
      setSessionDone(true);
    }
  };

  // ---- session complete screen --------------------------------------------

  if (sessionDone) {
    const tier = sessionResult?.mastery_tier ?? "—";
    const wins = sessionResult?.wins ?? outcomes.filter((o) => o === "win").length;
    const draws = sessionResult?.draws ?? outcomes.filter((o) => o === "draw").length;
    const xp = sessionResult?.session_xp ?? 0;

    return (
      <div className={s.wrap} data-testid="ttt-session-done">
        <div className={s.doneCard}>
          <Pill tone="good">Session Complete</Pill>
          <Title size="section">You finished {sessionGames} games.</Title>
          <div className={s.stats}>
            <div className={s.statRow}>
              <span className={s.statLabel}>Mastery tier</span>
              <span className={s.statVal}>{tier}</span>
            </div>
            <div className={s.statRow}>
              <span className={s.statLabel}>Wins</span>
              <span className={s.statVal}>{wins}</span>
            </div>
            <div className={s.statRow}>
              <span className={s.statLabel}>Draws</span>
              <span className={s.statVal}>{draws}</span>
            </div>
            <div className={s.statRow}>
              <span className={s.statLabel}>XP earned</span>
              <span className={s.statVal}>{xp}</span>
            </div>
          </div>
          {sessionError && (
            <p className={s.error} role="alert">
              {sessionError}
            </p>
          )}
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete} data-testid="ttt-continue">
              Continue →
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ---- round-over overlay -------------------------------------------------

  const roundOver = round.outcome !== null;

  // ---- render active game --------------------------------------------------

  const currentOutcome = round.outcome;

  return (
    <div className={s.wrap} data-testid="ttt">
      {/* Header */}
      <div className={s.head}>
        <Eyebrow>Tic-Tac-Toe</Eyebrow>
        <span className={s.progress} data-testid="ttt-progress">
          Game {Math.min(gameIndex + 1, sessionGames)} of {sessionGames}
        </span>
      </div>

      <Lead className={s.instruction}>
        {roundOver ? "" : "Tap a cell to answer a question and claim it. First to 3-in-a-row wins."}
      </Lead>

      {/* 3x3 Board — frosted glass slab wrapper */}
      <div className={s.boardWrap}>
      <div
        className={s.board}
        role="grid"
        aria-label="Tic-Tac-Toe board"
        data-testid="ttt-board"
      >
        {round.board.map((cell, idx) => {
          const inWinLine = round.winLine?.includes(idx) ?? false;
          const isEmpty = cell === "empty";
          return (
            <button
              key={idx}
              type="button"
              role="gridcell"
              className={[
                s.cell,
                cell === "X" && s.cellX,
                cell === "O" && s.cellO,
                inWinLine && s.cellWin,
                isEmpty && !roundOver && s.cellEmpty,
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => { play("tick"); onCellClick(idx); }}
              disabled={!isEmpty || roundOver || submitting || openCell !== null}
              aria-label={
                isEmpty
                  ? `Cell ${idx + 1}, empty`
                  : `Cell ${idx + 1}, ${cell === "X" ? "yours" : "opponent"}`
              }
              data-testid={`ttt-cell-${idx}`}
            >
              {cell === "X" && <span className={s.markerX} aria-hidden="true">✕</span>}
              {cell === "O" && <span className={s.markerO} aria-hidden="true">○</span>}
            </button>
          );
        })}
      </div>
      </div>{/* /boardWrap */}

      {/* Round result banner */}
      {roundOver && (
        <div className={s.roundBanner} role="status" data-testid="ttt-round-result">
          {currentOutcome === "win" && <Pill tone="good">You won this round!</Pill>}
          {currentOutcome === "draw" && <Pill tone="default">Draw!</Pill>}
          {currentOutcome === "loss" && <Pill tone="warn">Opponent won this round.</Pill>}
          <div className={s.actions}>
            {outcomes.length < sessionGames ? (
              <Button
                variant="blue"
                onClick={startNextRound}
                data-testid="ttt-next-round"
              >
                Next game →
              </Button>
            ) : null}
          </div>
        </div>
      )}

      {/* Question modal */}
      {openCell !== null && (
        <QuestionModal
          item={cellItems[openCell]}
          pickedOption={pickedOption}
          onPick={setPickedOption}
          onSubmit={onSubmitPick}
          onConfirm={onConfirmVerdict}
          verdict={verdict}
          submitting={submitting}
          error={submitError}
          onClose={() => {
            if (!verdict && !submitting) {
              setOpenCell(null);
              setPickedOption(null);
            }
          }}
        />
      )}
    </div>
  );
}

// ---- QuestionModal --------------------------------------------------------

interface QuestionModalProps {
  item: TttWireItem | undefined;
  pickedOption: string | null;
  onPick: (opt: string) => void;
  onSubmit: () => void;
  onConfirm: () => void;
  verdict: TttPickResult | null;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
}

function QuestionModal({
  item,
  pickedOption,
  onPick,
  onSubmit,
  onConfirm,
  verdict,
  submitting,
  error,
  onClose,
}: QuestionModalProps) {
  if (!item) return null;

  const hasPicked = pickedOption !== null;
  const showVerdict = verdict !== null;

  // Determine result messaging
  const wasCorrect = verdict?.is_correct;
  const wasMercy = verdict?.mercy;
  const youClaim = wasCorrect || wasMercy;

  return (
    <div
      className={s.modalBackdrop}
      role="dialog"
      aria-modal="true"
      aria-label="Answer the question to claim this cell"
      data-testid="ttt-modal"
    >
      <div className={s.modal}>
        <div className={s.modalHead}>
          <Eyebrow>Claim this cell</Eyebrow>
          {!showVerdict && (
            <button
              type="button"
              className={s.closeBtn}
              onClick={() => { play("tick"); onClose(); }}
              aria-label="Cancel"
              data-testid="ttt-modal-close"
            >
              ✕
            </button>
          )}
        </div>

        <p className={s.question} data-testid="ttt-question">
          {item.q}
        </p>

        {!showVerdict && (
          <>
            <div className={s.options} role="group" aria-label="Answer options">
              {item.options.map((opt, i) => (
                <button
                  key={i}
                  type="button"
                  className={[s.option, pickedOption === opt && s.optionSelected]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={() => { play("tick"); onPick(opt); }}
                  disabled={submitting}
                  aria-pressed={pickedOption === opt}
                  data-testid={`ttt-option-${i}`}
                >
                  {opt}
                </button>
              ))}
            </div>

            {error && (
              <p className={s.error} role="alert">
                {error}
              </p>
            )}

            <div className={s.modalActions}>
              <Button
                variant="blue"
                onClick={onSubmit}
                disabled={!hasPicked || submitting}
                data-testid="ttt-submit"
              >
                {submitting ? "Checking…" : "Submit"}
              </Button>
            </div>
          </>
        )}

        {showVerdict && (
          <div className={s.verdictWrap} data-testid="ttt-verdict">
            {youClaim ? (
              <>
                <Pill tone="good">
                  {wasMercy && !wasCorrect ? "Lucky bounce — you still get it!" : "Correct!"}
                </Pill>
                <p className={s.verdictText}>You claim this cell.</p>
              </>
            ) : (
              <>
                <Pill tone="warn">Wrong</Pill>
                <p className={s.verdictText}>
                  Correct answer: <strong>{verdict!.correct_value}</strong>. Opponent takes this cell.
                </p>
              </>
            )}
            <div className={s.modalActions}>
              <Button
                variant={youClaim ? "blue" : "outline"}
                onClick={onConfirm}
                data-testid="ttt-verdict-confirm"
              >
                OK
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
