import { useCallback } from "react";
import type { MysteryBoxEditorProps } from "./types";
import type { DraftMysteryBoxItem } from "./types";
import { EditorCard, Field, TextInput, TextArea, SmallButton } from "./fields";
import s from "./MysteryBoxEditor.module.css";

// ---------------------------------------------------------------------------
// Mystery Box editor — owns content_json.gb_mystery_box (DraftMysteryBoxItem[]).
// Each item: {category?, q, a}. `a` is the authored answer — stripped
// server-side before student delivery (server/schemas/content.py MysteryBoxItem).
//
// UX:
//   - Header card: item count badge + "Add box" button.
//   - Items rendered as a flat list; category is shown as an optional label chip
//     above each item card (purely visual — no grouping tree, no drag-to-sort).
//   - Per item: category (optional), question q, answer a, remove button.
//   - Empty state: friendly prompt to add the first item.
// ---------------------------------------------------------------------------

function makeItem(): DraftMysteryBoxItem {
  return { category: "", q: "", a: "" };
}

export function MysteryBoxEditor({ value, onChange }: MysteryBoxEditorProps) {
  const add = useCallback(() => {
    onChange([...value, makeItem()]);
  }, [value, onChange]);

  const remove = useCallback(
    (idx: number) => {
      onChange(value.filter((_, i) => i !== idx));
    },
    [value, onChange]
  );

  const patch = useCallback(
    (idx: number, partial: Partial<DraftMysteryBoxItem>) => {
      onChange(
        value.map((item, i) => (i === idx ? { ...item, ...partial } : item))
      );
    },
    [value, onChange]
  );

  return (
    <div className={s.editor}>
      {/* Header */}
      <EditorCard
        title="Mystery Box"
        actions={
          <SmallButton tone="primary" onClick={add}>
            + Add box
          </SmallButton>
        }
      >
        <p className={s.meta}>
          {value.length === 0 ? (
            <span className={s.emptyHint}>
              No boxes yet — each box hides a question; the student opens it and
              types their answer.
            </span>
          ) : (
            <>
              <span className={s.countBadge}>
                {value.length} box{value.length === 1 ? "" : "es"}
              </span>
              <span className={s.metaHint}>
                The answer field is stripped server-side before delivery.
              </span>
            </>
          )}
        </p>
      </EditorCard>

      {/* Item list */}
      {value.length === 0 ? (
        <div className={s.emptyState}>
          <div className={s.emptyIcon} aria-hidden="true">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M20 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2Z" />
              <path d="M16 3 8 3 6 7h12l-2-4Z" />
              <path d="M12 12v4" />
              <path d="M10 14h4" />
            </svg>
          </div>
          <p className={s.emptyLabel}>No mystery boxes</p>
          <p className={s.emptyBody}>
            Add a box to get started. Each box hides one question — students
            click to open and type their answer.
          </p>
          <SmallButton tone="primary" onClick={add}>
            + Add first box
          </SmallButton>
        </div>
      ) : (
        <ol className={s.list} aria-label="Mystery box items">
          {value.map((item, idx) => (
            <li key={idx} className={s.item}>
              {/* Item header row */}
              <div className={s.itemHead}>
                <span className={s.itemIndex} aria-hidden="true">
                  {idx + 1}
                </span>
                {item.category ? (
                  <span className={s.categoryChip}>{item.category}</span>
                ) : (
                  <span className={s.categoryChipEmpty}>No category</span>
                )}
                <SmallButton
                  tone="danger"
                  onClick={() => remove(idx)}
                >
                  Remove
                </SmallButton>
              </div>

              {/* Fields */}
              <div className={s.itemFields}>
                <Field label="Category" hint="Optional — groups boxes visually for the student">
                  <TextInput
                    value={item.category ?? ""}
                    onChange={(v) => patch(idx, { category: v })}
                    placeholder="e.g. Photosynthesis, Laws of Motion…"
                  />
                </Field>

                <Field label="Question">
                  <TextArea
                    value={item.q}
                    rows={2}
                    onChange={(v) => patch(idx, { q: v })}
                    placeholder="What does the student need to answer?"
                  />
                </Field>

                <Field
                  label="Answer"
                  hint="Author-only — stripped before student delivery"
                >
                  <TextInput
                    value={item.a}
                    onChange={(v) => patch(idx, { a: v })}
                    placeholder="The correct answer…"
                  />
                </Field>
              </div>
            </li>
          ))}
        </ol>
      )}

      {/* Footer add button when list is non-empty */}
      {value.length > 0 && (
        <div className={s.footer}>
          <SmallButton onClick={add}>+ Add another box</SmallButton>
        </div>
      )}
    </div>
  );
}
