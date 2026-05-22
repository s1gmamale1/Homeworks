import { useEffect, useState, useRef } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer, acknowledgeNudge } from "../../shared/api";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Pill, Button } from "../../shared/ui/primitives";
import { useAnswerTelemetry } from "../hooks/useAnswerTelemetry";
import IntegrityNudge from "../IntegrityNudge";
import s from "./SentenceFill.module.css";
import type { ClipboardEventHandler } from "react";

// ---------------------------------------------------------------------------
// Sentence Fill — cloze passage game (Practice Arc).
//
// Each item has a `passage` with "___" markers and an optional `word_bank`.
// mode=="word_bank": student taps a chip to fill each blank (chips can be
//   reused until locked; server grades by exact normalized match).
// mode=="free_recall": student types into each blank (semantic AI grader).
//
// Answers are NEVER in the client payload (stripped server-side by
// _serialize_sentence_fill). Each blank is submitted independently via
// phase="sentence-fill" with {item_id, blank_idx, student_value, attempt_number}.
// After 2 attempts OR a correct hit the blank locks. When all blanks in all
// items are locked, onComplete() fires.
// ---------------------------------------------------------------------------

// --- Inline type (do NOT import from shared/types.ts) ---
interface SentenceFillItem {
  id: string;
  mode: "word_bank" | "free_recall";
  passage: string;
  word_bank?: string[] | null;
  tags?: string | null;
  pisa_level?: string | null;
  difficulty?: string | null;
  subject_hint?: string | null;
  color_hints?: Record<string, string> | null;
  blank_icons?: (string | null)[] | null;
  tier?: "basic" | "premium";
}

interface SfResponse {
  correct: boolean;
  lock: boolean;
  correct_answer?: string | null;
  explanation?: string | null;
  xp?: { base: number; first_attempt_bonus: number; total: number };
  // Optional advisory anti-cheat nudge — never answer-bearing.
  integrity_nudge?: { type: string; message: string } | null;
}

// Per-blank runtime state
interface BlankState {
  value: string;           // current input value
  attempts: number;        // how many times submitted
  locked: boolean;         // server said lock=true
  correct: boolean | null; // null = not yet judged
  revealedAnswer?: string; // shown when locked+wrong
  explanation?: string;
  submitting: boolean;
  flash: "correct" | "wrong" | null; // brief visual flash
}

function makeBlankStates(count: number): BlankState[] {
  return Array.from({ length: count }, () => ({
    value: "",
    attempts: 0,
    locked: false,
    correct: null,
    submitting: false,
    flash: null,
  }));
}

function countBlanks(passage: string): number {
  return (passage.match(/___/g) ?? []).length;
}

// Split passage on "___" → segments; blanks sit between them.
function splitPassage(passage: string): string[] {
  return passage.split("___");
}

export default function SentenceFill({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  const items = (payload?.content_json?.gb_sentence_fill ?? []) as SentenceFillItem[];

  // ---- Empty guard (mirrors TileMatch totalPairs===0) ----
  if (items.length === 0) {
    return (
      <div className={s.wrap} data-testid="sentence-fill-empty">
        <Lead>No sentence-fill passages on this homework.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete}>
            Skip →
          </Button>
        </div>
      </div>
    );
  }

  return (
    <SentenceFillInner
      hwId={hwId}
      sessionId={sessionId}
      items={items}
      onComplete={onComplete}
    />
  );
}

// ---------------------------------------------------------------------------
// Inner — stateful game body (separated so the guard above is a clean return).
// ---------------------------------------------------------------------------
function SentenceFillInner({
  hwId,
  sessionId,
  items,
  onComplete,
}: {
  hwId: string;
  sessionId: string;
  items: SentenceFillItem[];
  onComplete: () => void;
}) {
  const [itemIdx, setItemIdx] = useState(0);
  const [blanks, setBlanks] = useState<BlankState[]>(() =>
    makeBlankStates(countBlanks(items[0].passage))
  );
  // word_bank chip selection: which chip is staged for the focused blank
  const [focusedBlank, setFocusedBlank] = useState<number | null>(null);
  const [complete, setComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // flash timer refs
  const flashTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  // Advisory anti-cheat: re-baseline timing/paste per blank (item + focused
  // blank); the advisory nudge from the server, if any.
  const tele = useAnswerTelemetry(`${itemIdx}:${focusedBlank ?? "none"}`);
  const [nudge, setNudge] = useState<{ type: string; message: string } | null>(null);

  const item = items[itemIdx];
  const totalItems = items.length;
  const segments = splitPassage(item.passage);
  const numBlanks = blanks.length;

  // Locked blanks count for progress display
  const lockedCount = blanks.filter((b) => b.locked).length;
  // "All blanks done in this item?" triggers advance to next item or complete
  const allLocked = lockedCount === numBlanks;

  // Advance to next item or finish when all blanks locked
  useEffect(() => {
    if (!allLocked || numBlanks === 0) return;
    const t = setTimeout(() => {
      if (itemIdx + 1 < totalItems) {
        setItemIdx((i) => i + 1);
        setBlanks(makeBlankStates(countBlanks(items[itemIdx + 1].passage)));
        setFocusedBlank(null);
        setError(null);
        setNudge(null);
      } else {
        setComplete(true);
      }
    }, 900); // brief pause so student sees the last correct flash
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allLocked]);

  // Cleanup flash timers on unmount
  useEffect(() => {
    return () => {
      flashTimers.current.forEach(clearTimeout);
    };
  }, []);

  // ---- Submission ----
  async function submitBlank(blankIdx: number, value: string) {
    if (blanks[blankIdx].locked || blanks[blankIdx].submitting) return;
    const trimmed = value.trim();
    if (!trimmed) return;

    setError(null);
    setBlanks((prev) => {
      const next = [...prev];
      next[blankIdx] = { ...next[blankIdx], submitting: true };
      return next;
    });

    try {
      const res = await submitGameAnswer<SfResponse>(hwId, sessionId, "sentence-fill", {
        item_id: item.id,
        blank_idx: blankIdx,
        student_value: trimmed,
        attempt_number: blanks[blankIdx].attempts + 1,
        ...tele.read(),
      });
      setNudge(res.integrity_nudge ?? null);

      const flash: "correct" | "wrong" = res.correct ? "correct" : "wrong";

      setBlanks((prev) => {
        const next = [...prev];
        next[blankIdx] = {
          ...next[blankIdx],
          attempts: prev[blankIdx].attempts + 1,
          locked: res.lock,
          correct: res.correct,
          revealedAnswer: res.correct_answer ?? undefined,
          explanation: res.explanation ?? undefined,
          submitting: false,
          flash,
          // If locked+wrong, keep the student's value so they see it; if
          // locked+correct, keep it too. If still unlocked+wrong, reset to ""
          // so they can try again.
          value: res.lock ? trimmed : "",
        };
        return next;
      });

      // Clear flash after animation completes
      const t = setTimeout(() => {
        setBlanks((prev) => {
          const next = [...prev];
          next[blankIdx] = { ...next[blankIdx], flash: null };
          return next;
        });
      }, 560);
      flashTimers.current.push(t);

      // Deselect focused blank when locked
      if (res.lock && focusedBlank === blankIdx) {
        setFocusedBlank(null);
      }
    } catch (err) {
      setError((err as Error).message || "Could not check that answer.");
      setBlanks((prev) => {
        const next = [...prev];
        next[blankIdx] = { ...next[blankIdx], submitting: false };
        return next;
      });
    }
  }

  // ---- Word bank chip tap ----
  function onChipTap(word: string) {
    if (focusedBlank === null) return;
    const target = focusedBlank;
    if (blanks[target].locked) return;
    // Immediately submit
    setBlanks((prev) => {
      const next = [...prev];
      next[target] = { ...next[target], value: word };
      return next;
    });
    submitBlank(target, word);
  }

  // ---- Free recall: on Enter or blur submit ----
  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>, blankIdx: number) {
    if (e.key === "Enter") {
      e.preventDefault();
      submitBlank(blankIdx, blanks[blankIdx].value);
    }
  }

  function onInputBlur(blankIdx: number) {
    // Auto-submit on blur only if has content and not already locked
    if (blanks[blankIdx].value.trim() && !blanks[blankIdx].locked) {
      submitBlank(blankIdx, blanks[blankIdx].value);
    }
  }

  // ---- Complete screen ----
  if (complete) {
    return (
      <div className={s.wrap} data-testid="sentence-fill-complete">
        <div className={s.done}>
          <Pill tone="good">All filled</Pill>
          <Title size="section">Passage complete.</Title>
          <Lead>
            You filled all {totalItems} passage{totalItems !== 1 ? "s" : ""}. Keep it up.
          </Lead>
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete} data-testid="sf-continue">
              Continue →
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ---- Word bank chips available (for word_bank mode only) ----
  const wordBank = item.mode === "word_bank" ? (item.word_bank ?? []) : [];
  // Chips already used in locked+correct blanks are visually "used"
  const usedWords = new Set(
    blanks
      .filter((b) => b.locked && b.correct)
      .map((b) => b.value)
  );

  return (
    <div className={s.wrap} data-testid="sentence-fill">
      {/* Header */}
      <div className={s.head}>
        <Eyebrow>Sentence Fill</Eyebrow>
        <span className={s.counter} data-testid="sf-progress">
          {lockedCount}/{numBlanks} filled · item {itemIdx + 1}/{totalItems}
        </span>
      </div>

      <Title size="section">Fill in the blanks.</Title>
      <Lead className={s.sub}>
        {item.mode === "word_bank"
          ? "Tap the blank first, then pick a word from the bank below."
          : "Type your answer in each blank and press Enter (or click Submit)."}
      </Lead>

      {/* Difficulty badge */}
      {item.difficulty && (
        <div className={s.badges}>
          <Pill tone={item.difficulty === "easy" ? "good" : item.difficulty === "hard" ? "warn" : "default"}>
            {item.difficulty}
          </Pill>
          {item.pisa_level && <Pill tone="default">{item.pisa_level}</Pill>}
        </div>
      )}

      {/* Cloze passage */}
      <div className={s.passage} data-testid="sf-passage">
        {segments.map((seg, i) => (
          <span key={i}>
            <span dangerouslySetInnerHTML={{ __html: seg.replace(/\n/g, "<br>") }} />
            {i < numBlanks && (
              <BlankWidget
                idx={i}
                state={blanks[i]}
                mode={item.mode}
                isFocused={focusedBlank === i}
                onFocus={() => !blanks[i].locked && setFocusedBlank(i)}
                onChange={(val) => {
                  setBlanks((prev) => {
                    const next = [...prev];
                    next[i] = { ...next[i], value: val };
                    return next;
                  });
                }}
                onKeyDown={(e) => onInputKeyDown(e, i)}
                onBlur={() => item.mode === "free_recall" && onInputBlur(i)}
                onSubmit={() => submitBlank(i, blanks[i].value)}
                onPaste={tele.onPaste}
              />
            )}
          </span>
        ))}
      </div>

      {/* Word bank (word_bank mode only) */}
      {item.mode === "word_bank" && wordBank.length > 0 && (
        <div className={s.bankWrap} role="group" aria-label="Word bank">
          <span className={s.bankLabel}>Word bank</span>
          <div className={s.chips}>
            {wordBank.map((word) => {
              const isUsed = usedWords.has(word);
              const isActive = focusedBlank !== null && !blanks[focusedBlank]?.locked;
              return (
                <button
                  key={word}
                  type="button"
                  className={[
                    s.chip,
                    isUsed && s.chipUsed,
                    isActive && !isUsed && s.chipAvailable,
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  disabled={isUsed || focusedBlank === null || blanks[focusedBlank]?.locked}
                  onClick={() => onChipTap(word)}
                  data-testid={`sf-chip-${word}`}
                >
                  {word}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Explanation panel — shown when any blank is locked+wrong */}
      {blanks.some((b) => b.locked && !b.correct && b.explanation) && (
        <div className={s.explanations}>
          {blanks.map((b, i) =>
            b.locked && !b.correct && b.explanation ? (
              <div key={i} className={s.explanationRow}>
                <Pill tone="warn">Blank {i + 1}</Pill>
                <span className={s.explanationText}>{b.explanation}</span>
              </div>
            ) : null
          )}
        </div>
      )}

      {/* Advisory anti-cheat nudge — beside the passage/feedback, never gates
          blank progress or advance. */}
      <IntegrityNudge
        nudge={nudge}
        onDismiss={() => setNudge(null)}
        onRespond={(choice) =>
          acknowledgeNudge(hwId, sessionId, "sentence-fill", choice)
        }
      />

      {error && (
        <p className={s.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// BlankWidget — renders one inline blank (input or locked chip).
// ---------------------------------------------------------------------------
interface BlankWidgetProps {
  idx: number;
  state: BlankState;
  mode: "word_bank" | "free_recall";
  isFocused: boolean;
  onFocus: () => void;
  onChange: (val: string) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  onBlur: () => void;
  onSubmit: () => void;
  // Advisory anti-cheat — observe paste on the free-recall input.
  onPaste?: ClipboardEventHandler;
}

function BlankWidget({
  idx,
  state,
  mode,
  isFocused,
  onFocus,
  onChange,
  onKeyDown,
  onBlur,
  onSubmit,
  onPaste,
}: BlankWidgetProps) {
  const { locked, correct, value, submitting, flash, revealedAnswer } = state;

  // Locked state: show the answer as a pill
  if (locked) {
    const displayVal = correct ? value : (revealedAnswer ?? value);
    return (
      <span
        className={[
          s.blankLocked,
          correct ? s.blankCorrect : s.blankWrong,
        ].join(" ")}
        data-testid={`sf-blank-locked-${idx}`}
        aria-label={`Blank ${idx + 1}: ${displayVal}`}
      >
        {displayVal}
      </span>
    );
  }

  // Word-bank mode: render a tap target
  if (mode === "word_bank") {
    return (
      <button
        type="button"
        className={[
          s.blankTarget,
          isFocused && s.blankTargetFocused,
          flash === "wrong" && s.blankFlashWrong,
          flash === "correct" && s.blankFlashCorrect,
          submitting && s.blankSubmitting,
        ]
          .filter(Boolean)
          .join(" ")}
        onClick={onFocus}
        aria-label={`Blank ${idx + 1}${value ? `: ${value}` : " (tap to select)"}`}
        data-testid={`sf-blank-wb-${idx}`}
        disabled={submitting}
      >
        {value || <span className={s.blankPlaceholder}>tap</span>}
      </button>
    );
  }

  // Free recall mode: text input
  return (
    <span className={s.inputWrap}>
      <input
        type="text"
        className={[
          s.blankInput,
          flash === "wrong" && s.blankFlashWrong,
          flash === "correct" && s.blankFlashCorrect,
          submitting && s.blankSubmitting,
        ]
          .filter(Boolean)
          .join(" ")}
        value={value}
        placeholder="…"
        onChange={(e) => onChange(e.target.value)}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
        onPaste={onPaste}
        disabled={submitting}
        aria-label={`Blank ${idx + 1}`}
        data-testid={`sf-blank-input-${idx}`}
      />
      {value.trim() && !submitting && (
        <button
          type="button"
          className={s.submitMini}
          onClick={onSubmit}
          tabIndex={-1}
          aria-label="Submit this blank"
        >
          ↵
        </button>
      )}
    </span>
  );
}
