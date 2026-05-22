import { useState } from "react";
import type { ReactNode, ButtonHTMLAttributes, MouseEvent } from "react";
import s from "./_practiceShared.module.css";
import { play } from "../sfx";

// ---------------------------------------------------------------------------
// _practiceShared — the reusable building-block kit for the 8 Division-3
// practice games (see _DIV3_CONTRACT.md). Every game mounts its UI through
// <GameShell> and composes <CheckpointFlow> / <DPEBox> / <ResultTier> /
// <StateMeters> + the 3D-press buttons, so all 8 surfaces read as one
// serious, premium Apple-glass family with the --grad-game purple accent.
//
// These primitives carry NO answer state: an MCQ checkpoint reports the
// selected_index up to its game, which POSTs to the server; correct/incorrect
// feedback is ALWAYS the server's verdict, fed back down as a prop. The kit
// never decides correctness on its own (contract: "Correctness is ALWAYS the
// server's").
// ---------------------------------------------------------------------------

const cx = (...c: (string | false | undefined | null)[]) =>
  c.filter(Boolean).join(" ");

// ===========================================================================
// GameShell — the card frame (gradient top bar, glow, mount animation).
// ===========================================================================
export interface GameShellProps {
  /** Game title, e.g. "Sentence Repair". */
  title: ReactNode;
  /** Small uppercase kicker above the title, e.g. "Practice · 2 of 5". */
  eyebrow?: ReactNode;
  /** Right-aligned progress counter, e.g. "item 1/4". */
  counter?: ReactNode;
  /** data-testid on the root, e.g. "game-sentence_repair". */
  testid?: string;
  className?: string;
  children?: ReactNode;
}

export function GameShell({
  title,
  eyebrow,
  counter,
  testid,
  className,
  children,
}: GameShellProps) {
  return (
    <div className={cx(s.shell, className)} data-testid={testid}>
      <div className={s.head}>
        <div>
          {eyebrow && <p className={s.eyebrow}>{eyebrow}</p>}
          <h2 className={s.title}>{title}</h2>
        </div>
        {counter != null && <span className={s.counter}>{counter}</span>}
      </div>
      <div className={s.body}>{children}</div>
    </div>
  );
}

// ===========================================================================
// PressChoice / PressButton — 3D-press buttons (dual box-shadow lip).
// ===========================================================================
type PressBtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** "solid" = filled gradient (primary); "ghost" = white outline. */
  variant?: "solid" | "ghost";
};

/** Primary action button — the gradient 3D-press CTA used for Continue/Submit. */
export function PressButton({
  variant = "solid",
  className,
  children,
  onClick,
  ...rest
}: PressBtnProps) {
  const handleClick = (e: MouseEvent<HTMLButtonElement>) => { play("tick"); onClick?.(e); };
  return (
    <button
      type="button"
      className={cx(s.pressBtn, variant === "ghost" && s.pressBtnGhost, className)}
      onClick={handleClick}
      {...rest}
    >
      {children}
    </button>
  );
}

type PressChoiceProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** Visual state for MCQ option feedback (server-driven). */
  state?: "idle" | "selected" | "correct" | "wrong";
};

/** A single 3D-press selectable option (MCQ option, ttt cell, etc.). */
export function PressChoice({
  state = "idle",
  className,
  children,
  onClick,
  ...rest
}: PressChoiceProps) {
  const stateClass = {
    idle: "",
    selected: s.choiceSelected,
    correct: s.choiceCorrect,
    wrong: s.choiceWrong,
  }[state];
  const handleClick = (e: MouseEvent<HTMLButtonElement>) => { play("tick"); onClick?.(e); };
  return (
    <button type="button" className={cx(s.choice, stateClass, className)} onClick={handleClick} {...rest}>
      {children}
    </button>
  );
}

// ===========================================================================
// CheckpointFlow — renders a sequence of {question, options} MCQs.
//
// For each checkpoint the student taps an option; onAnswer(checkpointIndex,
// selectedIndex) is called and MUST resolve to the server verdict
// { correct, feedback?, advance? }. The flow shows correct/incorrect feedback,
// then advances to the next checkpoint. When the last checkpoint resolves it
// calls onDone(). The flow holds NO answer key — it only relays the index.
// ===========================================================================
export interface Checkpoint {
  question: string;
  options: string[];
}

export interface CheckpointVerdict {
  correct: boolean;
  feedback?: string | null;
  /** When false, stay on this checkpoint (let the student retry). Default true. */
  advance?: boolean;
}

export interface CheckpointFlowProps {
  checkpoints: Checkpoint[];
  /** Resolve with the SERVER verdict for the chosen option. */
  onAnswer: (
    checkpointIndex: number,
    selectedIndex: number
  ) => Promise<CheckpointVerdict> | CheckpointVerdict;
  /** Fired after the final checkpoint resolves (advance!==false). */
  onDone: () => void;
  /** data-testid prefix, e.g. "sentence_repair" → "sentence_repair-checkpoint". */
  testidPrefix?: string;
  /** Override the "Checkpoint N of M" kicker label. */
  stepLabel?: (index: number, total: number) => string;
}

export function CheckpointFlow({
  checkpoints,
  onAnswer,
  onDone,
  testidPrefix,
  stepLabel,
}: CheckpointFlowProps) {
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [verdict, setVerdict] = useState<CheckpointVerdict | null>(null);
  const [busy, setBusy] = useState(false);

  const total = checkpoints.length;
  const cp = checkpoints[index];
  if (!cp) return null;

  const label =
    stepLabel?.(index, total) ?? `Checkpoint ${index + 1} of ${total}`;

  async function choose(optionIndex: number) {
    if (busy || verdict?.correct) return;
    setBusy(true);
    setSelected(optionIndex);
    try {
      const v = await onAnswer(index, optionIndex);
      setVerdict(v);
      // CheckpointFlow owns its own sequence: a CORRECT answer always steps to
      // the next checkpoint (or onDone after the last). We do NOT gate on the
      // server's `advance` flag here — backend MCQ graders legitimately return
      // advance=false to mean "more checkpoints remain", which is the opposite
      // of "stay and retry". Retry is driven purely by `!correct`.
      if (v.correct) {
        play("correct");
        // brief pause so the student sees the correct flash, then advance
        window.setTimeout(() => {
          if (index + 1 < total) {
            play("advance");
            setIndex((i) => i + 1);
            setSelected(null);
            setVerdict(null);
          } else {
            play("complete");
            onDone();
          }
        }, 720);
      } else {
        play("wrong");
        // wrong → let them retry this checkpoint
        setSelected(null);
      }
    } finally {
      setBusy(false);
    }
  }

  const optState = (i: number): PressChoiceProps["state"] => {
    if (selected !== i) return "idle";
    if (verdict?.correct) return "correct";
    if (verdict && !verdict.correct) return "wrong";
    return "selected";
  };

  return (
    <div data-testid={testidPrefix ? `${testidPrefix}-checkpoint` : undefined}>
      <p className={s.cpStep}>{label}</p>
      <p className={s.cpQuestion}>{cp.question}</p>
      <div className={s.cpOptions} role="group" aria-label={label}>
        {cp.options.map((opt, i) => (
          <PressChoice
            key={i}
            state={optState(i)}
            disabled={busy || verdict?.correct === true}
            onClick={() => choose(i)}
            data-testid={
              testidPrefix ? `${testidPrefix}-option-${i}` : undefined
            }
          >
            {opt}
          </PressChoice>
        ))}
      </div>
      {verdict?.feedback && (
        <p
          className={cx(
            s.feedback,
            verdict.correct ? s.feedbackCorrect : s.feedbackWrong
          )}
          role="status"
          aria-live="polite"
        >
          {verdict.feedback}
        </p>
      )}
    </div>
  );
}

// ===========================================================================
// DPEBox — open-ended "Decision Process Explanation" textarea.
//
// On submit it calls onSubmit(text) which resolves to the LOCKED pending_ai
// seam ({ pending_ai:true, feedback:"…AI tomonidan baholanadi…" }). We render
// that feedback CALMLY (not as an error) and enable Continue. Per contract:
// "render the pending_ai feedback as a calm 'AI will grade soon' provisional
// note, then allow advance."
// ===========================================================================
export interface DPEResult {
  pending_ai?: boolean;
  feedback?: string | null;
}

export interface DPEBoxProps {
  prompt: ReactNode;
  /** POST the reasoning text; resolve with the server's provisional response. */
  onSubmit: (text: string) => Promise<DPEResult> | DPEResult;
  /** Fired when the student taps Continue after the provisional note shows. */
  onContinue: () => void;
  placeholder?: string;
  testidPrefix?: string;
}

export function DPEBox({
  prompt,
  onSubmit,
  onContinue,
  placeholder = "2–4 sentences — walk through your reasoning.",
  testidPrefix,
}: DPEBoxProps) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<DPEResult | null>(null);

  async function submit() {
    if (busy || result || !text.trim()) return;
    setBusy(true);
    try {
      const r = await onSubmit(text.trim());
      play("submit");
      setResult(r ?? { pending_ai: true });
    } catch {
      // Even on a transient error keep the arc walkable with the calm note.
      setResult({
        pending_ai: true,
        feedback: "Javobingiz AI tomonidan baholanadi — natija tez orada.",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div data-testid={testidPrefix ? `${testidPrefix}-dpe` : undefined}>
      <p className={s.dpePrompt}>{prompt}</p>
      <textarea
        className={s.dpeArea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        rows={4}
        disabled={busy || result !== null}
        aria-label="Your explanation"
      />
      {result ? (
        <>
          <div className={s.dpePending} role="status" aria-live="polite">
            <span className={s.dpePendingDot} aria-hidden="true" />
            <span>
              {result.feedback ??
                "Javobingiz AI tomonidan baholanadi — natija tez orada."}
            </span>
          </div>
          <div className={s.foot}>
            <PressButton onClick={onContinue} data-testid={testidPrefix ? `${testidPrefix}-dpe-continue` : undefined}>
              Continue →
            </PressButton>
          </div>
        </>
      ) : (
        <div className={s.foot}>
          <PressButton onClick={submit} disabled={!text.trim() || busy}>
            {busy ? "Submitting…" : "Submit"}
          </PressButton>
        </div>
      )}
    </div>
  );
}

// ===========================================================================
// ResultTier — the completion badge.
//
// Error Detection tiers per contract: "Sharp Eye" | "Good Detective" |
// "Half-Found" | "Hali emas". Any other string renders as a generic done
// badge, so games without tiers can pass tier="Done" or omit it.
// ===========================================================================
export type ResultTierName =
  | "Sharp Eye"
  | "Good Detective"
  | "Half-Found"
  | "Hali emas"
  | string;

const TIER_META: Record<string, { cls: string; icon: string }> = {
  "Sharp Eye": { cls: s.tierSharp, icon: "🦅" },
  "Good Detective": { cls: s.tierGood, icon: "🔍" },
  "Half-Found": { cls: s.tierHalf, icon: "◑" },
  "Hali emas": { cls: s.tierNot, icon: "↻" },
};

export interface ResultTierProps {
  tier?: ResultTierName | null;
  testid?: string;
}

export function ResultTier({ tier, testid }: ResultTierProps) {
  const label = tier ?? "Complete";
  const meta: { cls: string; icon: string } =
    (tier ? TIER_META[tier] : undefined) ?? { cls: "", icon: "✓" };
  return (
    <span className={cx(s.tier, meta.cls)} data-testid={testid}>
      <span className={s.tierIcon} aria-hidden="true">
        {meta.icon}
      </span>
      {label}
    </span>
  );
}

// ===========================================================================
// StateMeters — labeled bars for ttt_grid meters.
//
// The 7 canonical ttt_grid meters (contract): Accuracy, Evidence, Risk,
// Safety, Clarity, Balance, Efficiency. Pass `meters` as a name→value (0–100)
// map and optional `deltas` (name→signed change) to show the last move's
// effect. meter_deltas themselves are server-only (redacted); the game derives
// the displayed value from the server response, never from raw deltas.
// ===========================================================================
export interface StateMetersProps {
  /** name → current value (0–100). */
  meters: Record<string, number>;
  /** name → signed delta for the most recent move (optional). */
  deltas?: Record<string, number> | null;
  /** Explicit ordering; defaults to the contract's 7 ttt_grid meters. */
  order?: string[];
  testid?: string;
}

const TTT_METER_ORDER = [
  "Accuracy",
  "Evidence",
  "Risk",
  "Safety",
  "Clarity",
  "Balance",
  "Efficiency",
];

export function StateMeters({
  meters,
  deltas,
  order,
  testid,
}: StateMetersProps) {
  const names =
    order ??
    TTT_METER_ORDER.filter((n) => n in meters).concat(
      Object.keys(meters).filter((n) => !TTT_METER_ORDER.includes(n))
    );
  return (
    <div className={s.meters} data-testid={testid}>
      {names.map((name) => {
        const value = Math.max(0, Math.min(100, meters[name] ?? 0));
        const delta = deltas?.[name];
        return (
          <div className={s.meterRow} key={name}>
            <span className={s.meterLabel}>{name}</span>
            <span className={s.meterTrack}>
              <span className={s.meterFill} style={{ width: `${value}%` }} />
            </span>
            <span className={s.meterValue}>
              {Math.round(value)}
              {typeof delta === "number" && delta !== 0 && (
                <span
                  className={cx(
                    s.meterDelta,
                    delta > 0 ? s.meterDeltaUp : s.meterDeltaDown
                  )}
                >
                  {delta > 0 ? `+${delta}` : delta}
                </span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ===========================================================================
// EmptyGuard — the shared "no content → skip" card every game opens with.
// Keeps the arc walkable when a gb_* array is missing/empty.
// ===========================================================================
export interface EmptyGuardProps {
  title: ReactNode;
  message?: ReactNode;
  onSkip: () => void;
  testid?: string;
}

export function EmptyGuard({
  title,
  message = "Nothing authored for this homework — skip ahead and keep your momentum.",
  onSkip,
  testid,
}: EmptyGuardProps) {
  return (
    <GameShell title={title} eyebrow="Practice" testid={testid}>
      <p className={s.lead}>{message}</p>
      <div className={s.foot}>
        <PressButton variant="ghost" onClick={onSkip}>
          Skip for now →
        </PressButton>
      </div>
    </GameShell>
  );
}
