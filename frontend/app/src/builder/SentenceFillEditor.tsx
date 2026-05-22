import type {
  DraftSentenceFillItem,
  SentenceFillEditorProps,
  SentenceFillMode,
} from "./types";
import {
  EditorCard,
  Field,
  TextInput,
  TextArea,
  Select,
  SmallButton,
} from "./fields";
import f from "./fields.module.css";
import e from "./editors.module.css";
import s from "./SentenceFillEditor.module.css";

// ---------------------------------------------------------------------------
// Sentence Fill editor — authors content_json.gb_sentence_fill, a list of
// cloze-passage items. Mirrors server/schemas/content.py SentenceFillItem (~357)
// and the runtime renderer (runtime/games/SentenceFill.tsx).
//
// Blank convention: a blank is the literal marker "___" (three underscores) in
// the passage — same token the runtime splits on (splitPassage) and the server
// counts (passage.count("___")). The schema requires:
//   - 1–6 blanks per passage,
//   - answers.length === blank count (one accepted answer per blank, in order),
//   - word_bank mode: word_bank must be a SUPERSET of answers + carry ≥1
//     distractor (a word that isn't an answer).
//
// To make the blank↔answer relationship impossible to get wrong, this editor
// derives the blank count from the live passage and keeps `answers` (and the
// optional `explanations`) length-synced to it automatically. The author never
// hand-manages the answers-array length; they just type the passage and fill
// the numbered answer rows that appear.
// ---------------------------------------------------------------------------

const BLANK = "___";
const MAX_BLANKS = 6;

const MODE_OPTIONS: { value: SentenceFillMode; label: string }[] = [
  { value: "word_bank", label: "Word bank (tap a chip)" },
  { value: "free_recall", label: "Free recall (type the answer)" },
];

function countBlanks(passage: string): number {
  return (passage.match(/___/g) ?? []).length;
}

// Split the passage on the blank marker → text segments; a blank sits between
// each adjacent pair (mirrors the runtime's splitPassage).
function splitPassage(passage: string): string[] {
  return passage.split(BLANK);
}

// Resize `arr` to exactly `len` entries: grow by appending `fill`, shrink by
// truncating. Keeps answers/explanations in lock-step with the blank count.
function resize<T>(arr: T[], len: number, fill: T): T[] {
  if (arr.length === len) return arr;
  if (arr.length > len) return arr.slice(0, len);
  return [...arr, ...Array.from({ length: len - arr.length }, () => fill)];
}

// A blank, monospace-ish so it stands out in the passage box.
function newItem(n: number): DraftSentenceFillItem {
  return {
    id: `sf_${n}`,
    mode: "word_bank",
    passage: "",
    answers: [],
    word_bank: [],
  };
}

// Parse a free-form word-bank textarea (comma- or newline-separated) into a
// trimmed, de-duped, order-preserving list.
function parseBank(raw: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const tok of raw.split(/[\n,]/)) {
    const w = tok.trim();
    if (!w || seen.has(w)) continue;
    seen.add(w);
    out.push(w);
  }
  return out;
}

export function SentenceFillEditor({ value, onChange }: SentenceFillEditorProps) {
  const patchItem = (i: number, p: Partial<DraftSentenceFillItem>) =>
    onChange(value.map((it, idx) => (idx === i ? { ...it, ...p } : it)));

  const addItem = () =>
    onChange([...value, newItem(value.length + 1)]);

  const removeItem = (i: number) =>
    onChange(value.filter((_, idx) => idx !== i));

  // Editing the passage re-derives the blank count and re-syncs the per-blank
  // arrays so answers/explanations always match the markers in the text.
  const onPassageChange = (i: number, passage: string) => {
    const item = value[i];
    const blanks = countBlanks(passage);
    const answers = resize(item.answers, blanks, "");
    const explanations =
      item.explanations !== undefined
        ? resize<string | null>(item.explanations, blanks, null)
        : undefined;
    patchItem(i, { passage, answers, ...(explanations ? { explanations } : {}) });
  };

  return (
    <div className={s.editor}>
      <p className={e.help}>
        Each passage is a fill-in-the-blank sentence. Mark a blank by typing
        three underscores (<code className={s.code}>{BLANK}</code>) where the
        word should go — 1–{MAX_BLANKS} blanks per passage. An answer row appears
        for each blank, in order.
      </p>

      <EditorCard
        title="Passages"
        actions={
          <SmallButton tone="primary" onClick={addItem}>
            + Add passage
          </SmallButton>
        }
      >
        {value.length === 0 && (
          <p className={e.empty}>No passages yet. Add one to get started.</p>
        )}

        {value.map((item, i) => (
          <PassageItem
            key={item.id || i}
            index={i}
            item={item}
            onPassageChange={(passage) => onPassageChange(i, passage)}
            onPatch={(p) => patchItem(i, p)}
            onRemove={() => removeItem(i)}
          />
        ))}
      </EditorCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PassageItem — one cloze item: passage + per-blank answers + (optional) word
// bank. Surfaces live validation so an invalid item is visible before save.
// ---------------------------------------------------------------------------
function PassageItem({
  index,
  item,
  onPassageChange,
  onPatch,
  onRemove,
}: {
  index: number;
  item: DraftSentenceFillItem;
  onPassageChange: (passage: string) => void;
  onPatch: (p: Partial<DraftSentenceFillItem>) => void;
  onRemove: () => void;
}) {
  const blanks = countBlanks(item.passage);
  const segments = splitPassage(item.passage);
  const bank = item.word_bank ?? [];

  // ---- per-blank answer + explanation ----
  const setAnswer = (bi: number, v: string) => {
    const answers = item.answers.map((a, idx) => (idx === bi ? v : a));
    onPatch({ answers });
  };
  const setExplanation = (bi: number, v: string) => {
    // Lazily materialize the explanations array, sized to the blank count.
    const base =
      item.explanations !== undefined
        ? resize<string | null>(item.explanations, blanks, null)
        : Array.from({ length: blanks }, () => null as string | null);
    const explanations = base.map((x, idx) => (idx === bi ? (v ? v : null) : x));
    // If every explanation is empty, drop the array entirely (it's optional).
    const allEmpty = explanations.every((x) => !x);
    onPatch({ explanations: allEmpty ? undefined : explanations });
  };

  // ---- word bank ----
  const setBank = (raw: string) => onPatch({ word_bank: parseBank(raw) });
  const addAnswersToBank = () => {
    const merged = parseBank([...bank, ...item.answers].join("\n"));
    onPatch({ word_bank: merged });
  };

  // ---- validation (mirrors SentenceFillItem._validate) ----
  const issues: string[] = [];
  if (blanks === 0) {
    issues.push(`Add at least one "${BLANK}" blank to the passage.`);
  } else if (blanks > MAX_BLANKS) {
    issues.push(`Too many blanks (${blanks}). The maximum is ${MAX_BLANKS}.`);
  }
  if (blanks > 0 && item.answers.some((a) => !a.trim())) {
    issues.push("Every blank needs an answer.");
  }
  if (item.mode === "word_bank" && blanks > 0) {
    const answerSet = item.answers.map((a) => a.trim()).filter(Boolean);
    const missing = answerSet.filter((a) => !bank.includes(a));
    if (bank.length === 0) {
      issues.push("Word-bank mode needs a word bank.");
    } else {
      if (missing.length > 0) {
        issues.push(`Word bank is missing: ${missing.join(", ")}.`);
      }
      if (bank.length <= answerSet.length && missing.length === 0) {
        issues.push("Add at least one distractor (a word that isn't an answer).");
      }
    }
  }

  const badgeTone = issues.length === 0 ? s.badgeOk : s.badgeWarn;

  return (
    <div className={e.subItem}>
      <div className={e.subItemHead}>
        <span className={e.subItemLabel}>
          Passage {index + 1}
          <span className={`${s.badge} ${badgeTone}`}>
            {blanks} blank{blanks === 1 ? "" : "s"}
            {issues.length === 0 ? " · ready" : ` · ${issues.length} to fix`}
          </span>
        </span>
        <SmallButton tone="danger" onClick={onRemove}>
          Remove
        </SmallButton>
      </div>

      <Field label="Mode" hint="How the student fills each blank">
        <Select<SentenceFillMode>
          value={item.mode}
          options={MODE_OPTIONS}
          onChange={(mode) => onPatch({ mode })}
        />
      </Field>

      <Field
        label="Passage"
        hint={`Use "${BLANK}" for each blank · ${blanks}/${MAX_BLANKS} used`}
      >
        <TextArea
          value={item.passage}
          rows={3}
          placeholder={`The capital of France is ${BLANK}, on the river ${BLANK}.`}
          onChange={onPassageChange}
        />
      </Field>

      {/* Live blank map: shows where each numbered blank sits in the passage */}
      {blanks > 0 && (
        <div className={s.preview} aria-label="Passage preview">
          <span className={s.previewLabel}>Preview</span>
          <p className={s.previewBody}>
            {segments.map((seg, si) => (
              <span key={si}>
                <span className={s.previewText}>{seg}</span>
                {si < blanks && <span className={s.blankChip}>{si + 1}</span>}
              </span>
            ))}
          </p>
        </div>
      )}

      {/* Per-blank answers — one row per blank, numbered to match the chips */}
      {blanks > 0 && (
        <div className={s.answers}>
          <span className={f.label}>
            Answers
            <span className={f.hint}>One accepted answer per blank, in order</span>
          </span>
          {item.answers.map((ans, bi) => (
            <div key={bi} className={s.answerRow}>
              <span className={s.answerNum} aria-hidden>
                {bi + 1}
              </span>
              <div className={s.answerFields}>
                <input
                  className={f.input}
                  value={ans}
                  placeholder={`Answer for blank ${bi + 1}`}
                  aria-label={`Answer for blank ${bi + 1}`}
                  onChange={(ev) => setAnswer(bi, ev.target.value)}
                />
                <input
                  className={`${f.input} ${s.explInput}`}
                  value={item.explanations?.[bi] ?? ""}
                  placeholder="Why (optional — shown if they miss it)"
                  aria-label={`Explanation for blank ${bi + 1}`}
                  onChange={(ev) => setExplanation(bi, ev.target.value)}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Word bank — required only in word_bank mode */}
      {item.mode === "word_bank" && (
        <Field
          label="Word bank"
          hint="Comma- or line-separated · must include every answer + ≥1 distractor"
        >
          <TextArea
            value={bank.join("\n")}
            rows={2}
            placeholder={"Paris\nSeine\nLyon\nRhône"}
            onChange={setBank}
          />
          {blanks > 0 && (
            <div className={s.bankActions}>
              <SmallButton onClick={addAnswersToBank}>
                + Add all answers to bank
              </SmallButton>
              <span className={s.bankCount}>
                {bank.length} word{bank.length === 1 ? "" : "s"}
              </span>
            </div>
          )}
        </Field>
      )}

      {/* Optional metadata */}
      <div className={s.metaGrid}>
        <Field label="Difficulty">
          <Select<"" | "easy" | "medium" | "hard">
            value={item.difficulty ?? ""}
            options={[
              { value: "", label: "—" },
              { value: "easy", label: "Easy" },
              { value: "medium", label: "Medium" },
              { value: "hard", label: "Hard" },
            ]}
            onChange={(d) => onPatch({ difficulty: d === "" ? undefined : d })}
          />
        </Field>
        <Field label="Tags" hint="Optional, comma-separated">
          <TextInput
            value={item.tags ?? ""}
            placeholder="geography, capitals"
            onChange={(tags) => onPatch({ tags: tags || undefined })}
          />
        </Field>
      </div>

      {/* Validation summary */}
      {issues.length > 0 && (
        <ul className={s.issues} role="status">
          {issues.map((msg, mi) => (
            <li key={mi}>{msg}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
