import type {
  AdaptiveQuizEditorProps,
  AuthoredAnswerSpec,
  DraftAdaptiveQuizItem,
} from "./types";
import { optionIndexSpec } from "./draft";
import {
  EditorCard,
  Field,
  TextInput,
  TextArea,
  Select,
  OptionEditor,
  SmallButton,
} from "./fields";
import s from "./AdaptiveQuizEditor.module.css";

// gb_adaptive_quiz authoring — a list of Practice Arc questions. Each item
// carries the SAME answer_spec grading contract as boss questions
// (server/schemas/content.py AdaptiveQuizItem ~236). The runtime
// (runtime/games/AdaptiveQuiz.tsx) renders `options` as choice buttons when the
// item is multiple-choice, else a free-text input — so the answer-type selector
// here drives BOTH the grading spec AND whether `options` are authored:
//
//   - option_index : MC. {type:"option_index", expected:<idx>, option_count:<n>}
//                    Author edits the options + taps the correct one (shared
//                    OptionEditor). Mirrors MemoryCheckEditor's MC items.
//   - text_fuzzy   : free recall. {type:"text_fuzzy", expected:"<text>"}.
//                    Author types the expected answer (kept in sync with ans[0],
//                    exactly like BossEditor). No options are persisted.
//
// This deliberately reuses the EXACT answer_spec UX from MemoryCheckEditor /
// BossEditor (Select type switch + OptionEditor for option_index + a single
// expected TextInput for text_fuzzy) so the builder reads consistently.

type AnswerType = AuthoredAnswerSpec["type"];

const ANSWER_TYPES: { value: AnswerType; label: string }[] = [
  { value: "option_index", label: "Multiple choice (tap correct)" },
  { value: "text_fuzzy", label: "Typed answer (fuzzy match)" },
];

const TIERS: { value: string; label: string }[] = [
  { value: "", label: "— (unset)" },
  { value: "EASY", label: "Easy" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HARD", label: "Hard" },
];

/** A fresh multiple-choice item (the common case). */
function emptyAdaptiveQuizItem(): DraftAdaptiveQuizItem {
  const options = ["", "", "", ""];
  return {
    q: "",
    options,
    ans: [""],
    answer_spec: optionIndexSpec(0, options.length),
  };
}

export function AdaptiveQuizEditor({ value, onChange }: AdaptiveQuizEditorProps) {
  const patchItem = (i: number, p: Partial<DraftAdaptiveQuizItem>) =>
    onChange(value.map((it, idx) => (idx === i ? { ...it, ...p } : it)));

  const replaceItem = (i: number, next: DraftAdaptiveQuizItem) =>
    onChange(value.map((it, idx) => (idx === i ? next : it)));

  const removeItem = (i: number) =>
    onChange(value.filter((_, idx) => idx !== i));

  const addItem = () => onChange([...value, emptyAdaptiveQuizItem()]);

  // Switching answer type rebuilds the spec (and options) from a clean template
  // of that type so options/answer_spec stay coherent — same approach as
  // MemoryCheckEditor.changeItemType (text_fuzzy drops options).
  const changeAnswerType = (i: number, type: AnswerType) => {
    const cur = value[i];
    if (type === "text_fuzzy") {
      replaceItem(i, {
        ...cur,
        options: undefined,
        ans: cur.ans.length ? cur.ans : [""],
        answer_spec: {
          type: "text_fuzzy",
          expected: cur.ans[0] ?? "",
          allow_ai_fallback: true,
        },
      });
      return;
    }
    const options =
      cur.options && cur.options.length >= 2 ? cur.options : ["", "", "", ""];
    replaceItem(i, {
      ...cur,
      options,
      answer_spec: optionIndexSpec(0, options.length),
    });
  };

  return (
    <div className={s.editor}>
      <EditorCard
        title="Adaptive Quiz"
        actions={
          <SmallButton tone="primary" onClick={addItem}>
            + Add question
          </SmallButton>
        }
      >
        <p className={s.help}>
          Practice Arc questions, asked in order. Choose multiple-choice (tap the
          correct option) or a typed answer (graded fuzzily — near matches
          accepted). Answers are stripped server-side before they reach the
          student.
        </p>

        {value.length === 0 && (
          <p className={s.empty}>No quiz questions yet. Add the first one.</p>
        )}

        {value.map((item, i) => {
          const spec = item.answer_spec;
          const isMc = spec.type === "option_index";
          const options = item.options ?? [];
          const correctIndex = isMc ? spec.expected : 0;

          return (
            <div key={i} className={s.subItem}>
              <div className={s.subItemHead}>
                <span className={s.subItemLabel}>Question {i + 1}</span>
                <SmallButton tone="danger" onClick={() => removeItem(i)}>
                  Remove
                </SmallButton>
              </div>

              <Field label="Question">
                <TextArea
                  value={item.q}
                  rows={2}
                  placeholder="What do you want to ask?"
                  onChange={(q) => patchItem(i, { q })}
                />
              </Field>

              <Field label="Answer type">
                <Select<AnswerType>
                  value={spec.type}
                  options={ANSWER_TYPES}
                  onChange={(type) => changeAnswerType(i, type)}
                />
              </Field>

              {isMc ? (
                <OptionEditor
                  options={options}
                  correctIndex={correctIndex}
                  onOptionChange={(oi, v) =>
                    patchItem(i, {
                      options: options.map((o, idx) => (idx === oi ? v : o)),
                    })
                  }
                  onCorrectChange={(oi) =>
                    patchItem(i, {
                      answer_spec: optionIndexSpec(oi, options.length),
                    })
                  }
                  onAddOption={() =>
                    patchItem(i, { options: [...options, ""] })
                  }
                  onRemoveOption={(oi) => {
                    const nextOptions = options.filter((_, idx) => idx !== oi);
                    const expected = Math.max(
                      0,
                      Math.min(correctIndex, nextOptions.length - 1)
                    );
                    patchItem(i, {
                      options: nextOptions,
                      answer_spec: optionIndexSpec(expected, nextOptions.length),
                    });
                  }}
                />
              ) : (
                <Field
                  label="Expected answer"
                  hint="Graded fuzzily; the primary accepted answer"
                >
                  <TextInput
                    value={spec.type === "text_fuzzy" ? spec.expected : ""}
                    placeholder="e.g. photosynthesis"
                    onChange={(expected) =>
                      patchItem(i, {
                        // Keep ans[0] in lockstep with the expected value (the
                        // BossEditor convention) so the authored accepted-answers
                        // list always leads with the canonical answer.
                        ans: [expected, ...item.ans.slice(1)],
                        answer_spec: {
                          type: "text_fuzzy",
                          expected,
                          allow_ai_fallback: true,
                        },
                      })
                    }
                  />
                </Field>
              )}

              {/* Extra accepted answers — author-visible alternates beyond the
                  canonical one. Applies to BOTH types (the runtime grades
                  server-side against the full ans list). */}
              <AcceptedAnswersField
                ans={item.ans}
                primaryLocked={!isMc}
                onChange={(ans) => patchItem(i, { ans })}
              />

              <Field label="Difficulty tier" hint="optional">
                <Select<string>
                  value={item.tier ?? ""}
                  options={TIERS}
                  onChange={(tier) =>
                    patchItem(i, { tier: tier === "" ? undefined : tier })
                  }
                />
              </Field>

              <Field label="Tags" hint="optional · comma-separated">
                <TextInput
                  value={item.tags ?? ""}
                  placeholder="e.g. cells, energy"
                  onChange={(tags) =>
                    patchItem(i, { tags: tags === "" ? undefined : tags })
                  }
                />
              </Field>
            </div>
          );
        })}
      </EditorCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Accepted-answers sub-editor. The canonical answer is `ans[0]`; for text_fuzzy
// it mirrors answer_spec.expected (edited above, so the first row is read-only
// here to avoid two sources of truth). Additional rows are free alternates.
// ---------------------------------------------------------------------------
function AcceptedAnswersField({
  ans,
  primaryLocked,
  onChange,
}: {
  ans: string[];
  primaryLocked: boolean;
  onChange: (next: string[]) => void;
}) {
  // Rows shown for editing alternates: everything after the canonical ans[0].
  const alternates = ans.slice(1);

  const setAlternate = (i: number, v: string) =>
    onChange([ans[0] ?? "", ...alternates.map((a, idx) => (idx === i ? v : a))]);

  const addAlternate = () => onChange([ans[0] ?? "", ...alternates, ""]);

  const removeAlternate = (i: number) =>
    onChange([ans[0] ?? "", ...alternates.filter((_, idx) => idx !== i)]);

  return (
    <div className={s.acceptedGroup}>
      <span className={s.acceptedLabel}>
        Also accept
        <span className={s.acceptedHint}>
          {primaryLocked
            ? "alternate spellings / phrasings (the expected answer above is row 1)"
            : "optional alternate answers beyond the marked option"}
        </span>
      </span>
      {alternates.map((alt, i) => (
        <div key={i} className={s.acceptedRow}>
          <input
            className={s.acceptedInput}
            value={alt}
            placeholder={`Alternate ${i + 1}`}
            onChange={(e) => setAlternate(i, e.target.value)}
          />
          <SmallButton tone="danger" onClick={() => removeAlternate(i)}>
            ✕
          </SmallButton>
        </div>
      ))}
      <SmallButton onClick={addAlternate}>+ Add alternate</SmallButton>
    </div>
  );
}
