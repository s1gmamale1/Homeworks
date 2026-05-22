import { useCallback } from "react";
import type { ReflectionEditorProps } from "./types";
import { EditorCard, Field, TextArea, SmallButton } from "./fields";
import s from "./ReflectionEditor.module.css";

// ---------------------------------------------------------------------------
// Reflection editor — owns content_json.reflection (DraftReflection).
//
// Two cards:
//   1. Closing copy — the four optional free-text fields the author writes to
//      frame the debrief screen: summary, question, spaced_rep, closing.
//      These are stored on the ReflectionPhase and available to the runtime
//      surface / AI debrief prompt as author context.
//   2. Reflection prompts — an optional override of the two Flow-v2 default
//      prompts ("What was the hardest part…" / "Why did you make your main
//      decision…"). When the author adds prompts here they REPLACE the defaults
//      (store.ts: `authored.length > 0 ? authored.slice(0,2) : defaults`).
//      Capped at 2. Empty = defaults run at runtime.
//
// server/schemas/content.py ReflectionPhase (~403):
//   summary, question, spaced_rep, closing — all Optional[str]
// types.ts DraftReflection:
//   same four + prompts?: string[]
// ---------------------------------------------------------------------------

const DEFAULT_PROMPTS = [
  "What was the hardest part, and why?",
  "Why did you make your main decision the way you did?",
] as const;

const MAX_PROMPTS = 2;

export function ReflectionEditor({ value, onChange }: ReflectionEditorProps) {
  // Patch a top-level key of the draft reflection slice.
  const patch = useCallback(
    (partial: Partial<typeof value>) => onChange({ ...value, ...partial }),
    [value, onChange]
  );

  // ---- Prompts helpers ----
  const prompts = value.prompts ?? [];
  const canAdd = prompts.length < MAX_PROMPTS;

  const addPrompt = useCallback(() => {
    patch({ prompts: [...prompts, ""] });
  }, [patch, prompts]);

  const removePrompt = useCallback(
    (idx: number) => {
      const next = prompts.filter((_, i) => i !== idx);
      // When all custom prompts are removed, drop the key entirely so the store
      // falls through to the Flow-v2 defaults at runtime.
      patch({ prompts: next.length > 0 ? next : undefined });
    },
    [patch, prompts]
  );

  const updatePrompt = useCallback(
    (idx: number, text: string) => {
      patch({ prompts: prompts.map((p, i) => (i === idx ? text : p)) });
    },
    [patch, prompts]
  );

  const usingDefaults = prompts.length === 0;

  return (
    <div className={s.editor}>
      {/* ---- Card 1: Closing copy ---- */}
      <EditorCard title="Closing copy">
        <p className={s.sectionHint}>
          Optional author text that frames the debrief. Leave any field blank to
          use the runtime defaults.
        </p>

        <Field
          label="Summary"
          hint="What this homework covered — shown as a brief recap"
        >
          <TextArea
            value={value.summary ?? ""}
            rows={2}
            onChange={(v) => patch({ summary: v || undefined })}
            placeholder="e.g. In this homework we explored Newton's three laws through real-world scenarios."
          />
        </Field>

        <Field
          label="Key question"
          hint="The central idea the student should carry away"
        >
          <TextArea
            value={value.question ?? ""}
            rows={2}
            onChange={(v) => patch({ question: v || undefined })}
            placeholder="e.g. How does inertia explain why passengers lurch forward when a bus brakes?"
          />
        </Field>

        <Field
          label="Spaced-rep hook"
          hint="A prompt or reminder to revisit this topic later"
        >
          <TextArea
            value={value.spaced_rep ?? ""}
            rows={2}
            onChange={(v) => patch({ spaced_rep: v || undefined })}
            placeholder="e.g. In 3 days, sketch Newton's 2nd law from memory."
          />
        </Field>

        <Field
          label="Closing note"
          hint="Final words shown at the bottom of the debrief — keep it warm"
        >
          <TextArea
            value={value.closing ?? ""}
            rows={2}
            onChange={(v) => patch({ closing: v || undefined })}
            placeholder="e.g. Great work. You cleared the Boss — that's the bar."
          />
        </Field>
      </EditorCard>

      {/* ---- Card 2: Reflection prompts ---- */}
      <EditorCard
        title="Reflection prompts"
        actions={
          canAdd ? (
            <SmallButton tone="primary" onClick={addPrompt}>
              + Add prompt
            </SmallButton>
          ) : undefined
        }
      >
        <p className={s.sectionHint}>
          1–2 free-text prompts the student answers before the AI debrief.
          Leave empty to use the Flow-v2 defaults.
        </p>

        {/* Default prompts preview when no overrides are set */}
        {usingDefaults ? (
          <div className={s.defaultsBox}>
            <span className={s.defaultsLabel}>Using defaults</span>
            <ol className={s.defaultsList}>
              {DEFAULT_PROMPTS.map((p, i) => (
                <li key={i} className={s.defaultsItem}>
                  {p}
                </li>
              ))}
            </ol>
            <SmallButton onClick={addPrompt}>Override prompts</SmallButton>
          </div>
        ) : (
          <>
            <ol className={s.promptList} aria-label="Custom reflection prompts">
              {prompts.map((prompt, idx) => (
                <li key={idx} className={s.promptItem}>
                  <div className={s.promptItemHead}>
                    <span className={s.promptIndex} aria-hidden="true">
                      {idx + 1}
                    </span>
                    <span className={s.promptItemLabel}>Prompt {idx + 1}</span>
                    <SmallButton
                      tone="danger"
                      onClick={() => removePrompt(idx)}
                    >
                      Remove
                    </SmallButton>
                  </div>
                  <div className={s.promptItemBody}>
                    <TextArea
                      value={prompt}
                      rows={2}
                      onChange={(v) => updatePrompt(idx, v)}
                      placeholder="e.g. What was the hardest part, and why?"
                    />
                  </div>
                </li>
              ))}
            </ol>

            {/* Footer: cap notice or add-another */}
            <div className={s.promptFooter}>
              {canAdd ? (
                <SmallButton onClick={addPrompt}>+ Add another prompt</SmallButton>
              ) : (
                <p className={s.capNote}>
                  Maximum 2 prompts — the runtime shows at most 2.
                </p>
              )}
            </div>
          </>
        )}
      </EditorCard>
    </div>
  );
}
