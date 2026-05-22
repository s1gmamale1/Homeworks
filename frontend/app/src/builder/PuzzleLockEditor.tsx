import type { PuzzleLockEditorProps, DraftPuzzleLockItem } from "./types";
import { EditorCard, Field, TextInput, TextArea, SmallButton } from "./fields";
import s from "./PuzzleLockEditor.module.css";

// Wave-1 implementation. Owns content_json.gb_puzzle_lock (DraftPuzzleLockItem[]).
// Canonical shape: {content?, q, a} — see server/schemas/content.py PuzzleLockItem (~259).
// Legacy {text, question, answer} aliases are coerced on load (draft.ts ~629).
// The builder authors the canonical triple; `content` is optional (the tile clue shown
// above the question prompt in the runtime).

function emptyItem(): DraftPuzzleLockItem {
  return { content: "", q: "", a: "" };
}

export function PuzzleLockEditor({ value, onChange }: PuzzleLockEditorProps) {
  function addItem() {
    onChange([...value, emptyItem()]);
  }

  function removeItem(idx: number) {
    onChange(value.filter((_, i) => i !== idx));
  }

  function patchItem(idx: number, patch: Partial<DraftPuzzleLockItem>) {
    onChange(value.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  }

  return (
    <div className={s.editor}>
      <EditorCard
        title="Puzzle Lock"
        actions={
          <SmallButton tone="primary" onClick={addItem}>
            + Add tumbler
          </SmallButton>
        }
      >
        {value.length === 0 ? (
          <p className={s.empty}>
            No tumblers yet. Each tumbler has a clue, a question, and an answer.
            Add one to get started.
          </p>
        ) : (
          <ol className={s.list}>
            {value.map((item, idx) => (
              <li key={idx} className={s.tumbler}>
                <div className={s.tumblerHead}>
                  <span className={s.tumblerIndex}>{idx + 1}</span>
                  <SmallButton
                    tone="danger"
                    onClick={() => removeItem(idx)}
                  >
                    Remove
                  </SmallButton>
                </div>

                <Field label="Clue" hint="Tile text shown above the question — optional">
                  <TextInput
                    value={item.content ?? ""}
                    onChange={(v) => patchItem(idx, { content: v })}
                    placeholder="e.g. A force that opposes motion"
                  />
                </Field>

                <Field label="Question">
                  <TextArea
                    value={item.q}
                    rows={2}
                    onChange={(v) => patchItem(idx, { q: v })}
                    placeholder="e.g. What is the name of this force?"
                  />
                </Field>

                <Field label="Answer" hint="Stripped before student delivery">
                  <TextInput
                    value={item.a}
                    onChange={(v) => patchItem(idx, { a: v })}
                    placeholder="e.g. Friction"
                  />
                </Field>
              </li>
            ))}
          </ol>
        )}
      </EditorCard>

      <p className={s.footer}>
        <span className={s.count}>
          {value.length} tumbler{value.length === 1 ? "" : "s"}
        </span>
        The runtime shows one tumbler at a time. Correct answer opens it; all
        open = lock cracked.
      </p>
    </div>
  );
}
