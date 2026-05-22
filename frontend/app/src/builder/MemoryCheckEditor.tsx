import type {
  DraftFlashcard,
  DraftMemoryCheck,
  DraftMemoryCheckItem,
  MemoryCheckItemType,
} from "./types";
import { emptyFlashcard, emptyMemoryItem, optionIndexSpec } from "./draft";
import {
  EditorCard,
  Field,
  TextInput,
  TextArea,
  NumberInput,
  Select,
  OptionEditor,
  SmallButton,
} from "./fields";
import s from "./editors.module.css";

const ITEM_TYPES: { value: MemoryCheckItemType; label: string }[] = [
  { value: "mcq", label: "Multiple choice" },
  { value: "true_false", label: "True / False" },
  { value: "choose_explanation", label: "Choose the explanation" },
  { value: "fill_blank", label: "Fill in the blank" },
];

// Authors the flashcard deck + the graded Memory Check. Option types use the
// option-index picker → {type:"option_index", expected:<idx>, option_count:<n>};
// fill_blank uses {type:"text_fuzzy", expected:"<text>"}.
export function MemoryCheckEditor({
  flashcards,
  memoryCheck,
  onFlashcardsChange,
  onMemoryCheckChange,
}: {
  flashcards: DraftFlashcard[];
  memoryCheck: DraftMemoryCheck;
  onFlashcardsChange: (next: DraftFlashcard[]) => void;
  onMemoryCheckChange: (next: DraftMemoryCheck) => void;
}) {
  const patchCard = (i: number, p: Partial<DraftFlashcard>) =>
    onFlashcardsChange(
      flashcards.map((c, idx) => (idx === i ? { ...c, ...p } : c))
    );

  const patchItem = (i: number, p: Partial<DraftMemoryCheckItem>) =>
    onMemoryCheckChange({
      ...memoryCheck,
      items: memoryCheck.items.map((it, idx) =>
        idx === i ? ({ ...it, ...p } as DraftMemoryCheckItem) : it
      ),
    });

  // Switching item type rebuilds the item from a clean template of that type so
  // options/answer_spec stay coherent (e.g. fill_blank drops options).
  const changeItemType = (i: number, type: MemoryCheckItemType) => {
    const fresh = emptyMemoryItem(type);
    fresh.prompt = memoryCheck.items[i].prompt;
    onMemoryCheckChange({
      ...memoryCheck,
      items: memoryCheck.items.map((it, idx) => (idx === i ? fresh : it)),
    });
  };

  return (
    <div className={s.editor}>
      <EditorCard
        title="Flashcards"
        actions={
          <SmallButton
            tone="primary"
            onClick={() => onFlashcardsChange([...flashcards, emptyFlashcard()])}
          >
            + Add card
          </SmallButton>
        }
      >
        {flashcards.length === 0 && (
          <p className={s.empty}>No cards yet. Add the study deck.</p>
        )}
        {flashcards.map((card, i) => (
          <div key={i} className={s.subItem}>
            <div className={s.subItemHead}>
              <span className={s.subItemLabel}>Card {i + 1}</span>
              <SmallButton
                tone="danger"
                onClick={() =>
                  onFlashcardsChange(flashcards.filter((_, idx) => idx !== i))
                }
              >
                Remove
              </SmallButton>
            </div>
            <Field label="Term (front)">
              <TextInput
                value={card.term}
                onChange={(term) => patchCard(i, { term })}
              />
            </Field>
            <Field label="Definition (back)">
              <TextArea
                value={card.def}
                rows={2}
                onChange={(def) => patchCard(i, { def })}
              />
            </Field>
            <Field label="Hint" hint="optional">
              <TextInput
                value={card.hint ?? ""}
                onChange={(hint) => patchCard(i, { hint })}
              />
            </Field>
            <Field label="Example" hint="optional">
              <TextInput
                value={card.example ?? ""}
                onChange={(example) => patchCard(i, { example })}
              />
            </Field>
          </div>
        ))}
      </EditorCard>

      <EditorCard
        title="Memory Check"
        actions={
          <SmallButton
            tone="primary"
            onClick={() =>
              onMemoryCheckChange({
                ...memoryCheck,
                items: [...memoryCheck.items, emptyMemoryItem("mcq")],
              })
            }
          >
            + Add item
          </SmallButton>
        }
      >
        <Field
          label="Pass threshold (%)"
          hint="Minimum recall score to unlock the Practice Arc"
        >
          <NumberInput
            value={memoryCheck.pass_threshold_pct}
            min={0}
            max={100}
            step={5}
            onChange={(pass_threshold_pct) =>
              onMemoryCheckChange({ ...memoryCheck, pass_threshold_pct })
            }
          />
        </Field>

        {memoryCheck.items.length === 0 && (
          <p className={s.empty}>No graded items yet.</p>
        )}
        {memoryCheck.items.map((item, i) => (
          <div key={i} className={s.subItem}>
            <div className={s.subItemHead}>
              <span className={s.subItemLabel}>Item {i + 1}</span>
              <SmallButton
                tone="danger"
                onClick={() =>
                  onMemoryCheckChange({
                    ...memoryCheck,
                    items: memoryCheck.items.filter((_, idx) => idx !== i),
                  })
                }
              >
                Remove
              </SmallButton>
            </div>
            <Field label="Type">
              <Select<MemoryCheckItemType>
                value={item.type}
                options={ITEM_TYPES}
                onChange={(type) => changeItemType(i, type)}
              />
            </Field>
            <Field label="Prompt">
              <TextArea
                value={item.prompt}
                rows={2}
                onChange={(prompt) => patchItem(i, { prompt })}
              />
            </Field>

            {item.type === "fill_blank" ? (
              <Field
                label="Expected answer"
                hint="Graded fuzzily; near-matches accepted"
              >
                <TextInput
                  value={item.answer_spec.type === "text_fuzzy" ? item.answer_spec.expected : ""}
                  onChange={(expected) =>
                    patchItem(i, {
                      answer_spec: {
                        type: "text_fuzzy",
                        expected,
                        allow_ai_fallback: true,
                      },
                    })
                  }
                />
              </Field>
            ) : (
              <OptionEditor
                options={item.options}
                correctIndex={
                  item.answer_spec.type === "option_index"
                    ? item.answer_spec.expected
                    : 0
                }
                fixedOptions={item.type === "true_false"}
                onOptionChange={(oi, v) =>
                  patchItem(i, {
                    options: item.options.map((o, idx) => (idx === oi ? v : o)),
                  })
                }
                onCorrectChange={(oi) =>
                  patchItem(i, {
                    answer_spec: optionIndexSpec(oi, item.options.length),
                  })
                }
                onAddOption={
                  item.type === "true_false"
                    ? undefined
                    : () => patchItem(i, { options: [...item.options, ""] })
                }
                onRemoveOption={
                  item.type === "true_false"
                    ? undefined
                    : (oi) => {
                        const options = item.options.filter((_, idx) => idx !== oi);
                        const cur =
                          item.answer_spec.type === "option_index"
                            ? item.answer_spec.expected
                            : 0;
                        const expected = Math.max(
                          0,
                          Math.min(cur, options.length - 1)
                        );
                        patchItem(i, {
                          options,
                          answer_spec: optionIndexSpec(expected, options.length),
                        });
                      }
                }
              />
            )}
          </div>
        ))}
      </EditorCard>
    </div>
  );
}
