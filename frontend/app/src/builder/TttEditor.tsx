import type { ChangeEvent } from "react";
import type { DraftTttItem, DraftTttConfig, TttEditorProps } from "./types";
import { EditorCard, Field, TextInput, TextArea, SmallButton } from "./fields";
import s from "./TttEditor.module.css";
import e from "./editors.module.css";

// ---------------------------------------------------------------------------
// Tic-Tac-Toe Quiz editor — owns content_json.gb_ttt (DraftTttItem[]) +
// gb_ttt_config (DraftTttConfig).
//
// Per server/schemas/content.py TttItem (~280): each item is
// {id?, q, correct, distractors[]} with EXACTLY 3 distractors. The runtime
// (runtime/games/Ttt.tsx) shuffles correct + the 3 distractors into 4 options
// per cell; the injector strips `correct` + `distractors` before the wire
// format (answer-leak prevention) — the author writes them here.
//
// TttConfig (~294) carries optional XP / session overrides; every field is
// optional and the injector applies spec defaults when absent.
// ---------------------------------------------------------------------------

// The 3-distractor rule, enforced at the editor boundary. Items are always
// presented (and mutated) with exactly 3 distractor slots: a load that carried
// fewer/more is padded/truncated to 3 here, and there is no add/remove for
// distractor rows — so the persisted shape can never drift off the contract.
const DISTRACTOR_COUNT = 3;
const DISTRACTOR_LABELS = ["First wrong option", "Second wrong option", "Third wrong option"];

/** Coerce any distractor list to exactly 3 slots (pad with "", truncate). */
function normalizeDistractors(raw: string[] | undefined): string[] {
  const next = [...(raw ?? [])].slice(0, DISTRACTOR_COUNT);
  while (next.length < DISTRACTOR_COUNT) next.push("");
  return next;
}

/** A fresh, valid item: blank Q + correct, 3 empty distractor slots, stable id. */
function emptyTttItem(id: string): DraftTttItem {
  return { id, q: "", correct: "", distractors: ["", "", ""] };
}

/** Next stable "ttt-N" id that doesn't collide with an existing one. */
function nextItemId(items: DraftTttItem[]): string {
  let max = 0;
  for (const it of items) {
    const m = /^ttt-(\d+)$/.exec(it.id ?? "");
    if (m) max = Math.max(max, Number(m[1]));
  }
  return `ttt-${Math.max(max, items.length) + 1}`;
}

// ---- config field descriptors (label / hint / default the injector applies) --
const CONFIG_FIELDS: {
  key: keyof DraftTttConfig;
  label: string;
  hint: string;
  step?: number;
}[] = [
  { key: "session_games", label: "Games per session", hint: "Rounds before the tally — default 3" },
  { key: "xp_correct", label: "XP · correct answer", hint: "Per claimed cell — default 50" },
  { key: "xp_win", label: "XP · win a round", hint: "3-in-a-row — default 300" },
  { key: "xp_draw", label: "XP · draw a round", hint: "Full board, no winner — default 200" },
  { key: "xp_strong_session", label: "XP · strong session", hint: "Bonus for a strong run — default 100" },
  { key: "xp_mercy", label: "XP · mercy bounce", hint: "Lucky-bounce claim — default 10" },
  { key: "mercy_chance", label: "Mercy chance", hint: "0–1 probability — default 0.002", step: 0.001 },
];

export function TttEditor({ value, config, onChange, onConfigChange }: TttEditorProps) {
  // ---- item mutations -----------------------------------------------------
  const patchItem = (i: number, p: Partial<DraftTttItem>) => {
    onChange(value.map((it, idx) => (idx === i ? { ...it, ...p } : it)));
  };

  const patchDistractor = (i: number, di: number, v: string) => {
    const distractors = normalizeDistractors(value[i].distractors).map((d, idx) =>
      idx === di ? v : d
    );
    patchItem(i, { distractors });
  };

  const addItem = () => {
    onChange([...value, emptyTttItem(nextItemId(value))]);
  };

  const removeItem = (i: number) => {
    onChange(value.filter((_, idx) => idx !== i));
  };

  // ---- config mutations ---------------------------------------------------
  // A blank field CLEARS the override so the injector default applies again —
  // distinct from an explicit 0. (The shared NumberInput coerces blank→0, which
  // would silently zero a default, so config uses a raw number input instead.)
  const patchConfig = (key: keyof DraftTttConfig, raw: string) => {
    if (raw.trim() === "") {
      const next = { ...config };
      delete next[key];
      onConfigChange(next);
      return;
    }
    const n = Number(raw);
    if (!Number.isFinite(n)) return; // ignore non-numeric noise
    onConfigChange({ ...config, [key]: n });
  };

  return (
    <div className={e.editor}>
      {/* ---------------- Section 1 · Questions ---------------- */}
      <EditorCard
        title="Tic-Tac-Toe questions"
        actions={
          <SmallButton tone="primary" onClick={addItem}>
            + Add question
          </SmallButton>
        }
      >
        <p className={e.help}>
          Each question needs its <strong>correct answer</strong> plus exactly{" "}
          <strong>3 wrong options</strong>. The game shuffles all four into the cell
          a student taps — the wrong options keep the round honest. Answers are
          stored here and stripped before they ever reach the student.
        </p>

        {value.length === 0 && (
          <p className={e.empty}>No questions yet. Add one to start the board.</p>
        )}

        {value.map((item, i) => {
          const distractors = normalizeDistractors(item.distractors);
          const blankDistractors = distractors.filter((d) => d.trim() === "").length;
          const missingCorrect = (item.correct ?? "").trim() === "";
          const incomplete = missingCorrect || blankDistractors > 0;

          return (
            <div key={item.id ?? i} className={e.subItem}>
              <div className={e.subItemHead}>
                <span className={e.subItemLabel}>
                  Question {i + 1}
                  <span className={s.idTag}>{item.id ?? nextItemId(value)}</span>
                </span>
                <SmallButton tone="danger" onClick={() => removeItem(i)}>
                  Remove
                </SmallButton>
              </div>

              <Field label="Question">
                <TextArea
                  value={item.q}
                  rows={2}
                  onChange={(q) => patchItem(i, { q })}
                  placeholder="e.g. What is 7 × 8?"
                />
              </Field>

              <Field label="Correct answer" hint="The one right option">
                <TextInput
                  value={item.correct}
                  onChange={(correct) => patchItem(i, { correct })}
                  placeholder="e.g. 56"
                />
              </Field>

              <div className={s.distractorGroup}>
                <span className={s.distractorHeading}>
                  Wrong options
                  <span className={s.distractorHint}>Exactly 3 — all required</span>
                </span>
                {distractors.map((d, di) => (
                  <Field key={di} label={DISTRACTOR_LABELS[di]}>
                    <TextInput
                      value={d}
                      onChange={(v) => patchDistractor(i, di, v)}
                      placeholder={`Plausible-but-wrong answer ${di + 1}`}
                    />
                  </Field>
                ))}
              </div>

              {incomplete && (
                <p className={s.itemWarn} role="status">
                  {missingCorrect && "Add the correct answer. "}
                  {blankDistractors > 0 &&
                    `Fill ${blankDistractors} more wrong option${
                      blankDistractors === 1 ? "" : "s"
                    } (3 required).`}
                </p>
              )}
            </div>
          );
        })}
      </EditorCard>

      {/* ---------------- Section 2 · Config ---------------- */}
      <EditorCard title="Game settings">
        <p className={e.help}>
          Optional overrides. Leave a field blank to use the built-in default.
        </p>
        <div className={s.configGrid}>
          {CONFIG_FIELDS.map(({ key, label, hint, step }) => (
            <Field key={key} label={label} hint={hint}>
              <input
                className={s.numInput}
                type="number"
                min={0}
                step={step}
                value={config[key] ?? ""}
                placeholder="default"
                onChange={(ev: ChangeEvent<HTMLInputElement>) =>
                  patchConfig(key, ev.target.value)
                }
              />
            </Field>
          ))}
        </div>
      </EditorCard>
    </div>
  );
}
