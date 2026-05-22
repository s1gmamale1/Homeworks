import type { MetadataEditorProps } from "./types";
import { ALWAYS_HARD, SUBJECT_LABELS } from "./builderApi";
import { EditorCard, Field, TextInput, Select } from "./fields";
import s from "./MetadataEditor.module.css";

// CEFR levels — A1 through C2, in ascending order.
const CEFR_OPTIONS = [
  { value: "", label: "Not set" },
  { value: "A1", label: "A1 — Beginner" },
  { value: "A2", label: "A2 — Elementary" },
  { value: "B1", label: "B1 — Intermediate" },
  { value: "B2", label: "B2 — Upper-Intermediate" },
  { value: "C1", label: "C1 — Advanced" },
  { value: "C2", label: "C2 — Mastery" },
];

// Derive the subject key from subject_display if it matches a known label.
// Used only for the ALWAYS_HARD guard.
function subjectKeyFromDisplay(display: string | undefined): string {
  if (!display) return "";
  const lower = display.toLowerCase();
  return (
    Object.entries(SUBJECT_LABELS).find(
      ([, label]) => label.toLowerCase() === lower
    )?.[0] ?? lower
  );
}

// Authors content_json.meta (DraftMeta): title, subject_display, section,
// topic, cefr_level, and the difficulty/mode selector.
// `mode` here is the top-level field that controls easy/hard delivery.
export function MetadataEditor({ value, onChange }: MetadataEditorProps) {
  const patch = (p: Partial<typeof value>) => onChange({ ...value, ...p });

  const subjectKey = subjectKeyFromDisplay(value.subject_display);
  const isAlwaysHard = ALWAYS_HARD.has(subjectKey);

  // The current mode coerced to the two canonical values.
  const currentMode: "easy" | "hard" =
    value.mode === "easy" && !isAlwaysHard ? "easy" : "hard";

  return (
    <div className={s.editor}>
      {/* ---- Identity ---- */}
      <EditorCard title="Homework identity">
        <Field
          label="Title"
          hint="Shown in the student header and share links"
        >
          <TextInput
            value={value.title ?? ""}
            onChange={(v) => patch({ title: v })}
            placeholder="e.g. Algebra — Quadratic Equations"
          />
        </Field>

        <Field
          label="Subject"
          hint="Display name shown to the student (e.g. Algebra)"
        >
          <TextInput
            value={value.subject_display ?? ""}
            onChange={(v) => patch({ subject_display: v })}
            placeholder="e.g. Algebra"
          />
        </Field>

        <div className={s.grid2}>
          <Field label="Section" hint="Optional curriculum section">
            <TextInput
              value={value.section ?? ""}
              onChange={(v) => patch({ section: v })}
              placeholder="e.g. Chapter 3"
            />
          </Field>

          <Field label="Topic" hint="Narrow topic within the section">
            <TextInput
              value={value.topic ?? ""}
              onChange={(v) => patch({ topic: v })}
              placeholder="e.g. Factoring"
            />
          </Field>
        </div>
      </EditorCard>

      {/* ---- Language level ---- */}
      <EditorCard title="Language level">
        <Field
          label="CEFR level"
          hint="Common European Framework of Reference — reading difficulty"
        >
          <Select<string>
            value={value.cefr_level ?? ""}
            onChange={(v) => patch({ cefr_level: v || undefined })}
            options={CEFR_OPTIONS}
          />
        </Field>
      </EditorCard>

      {/* ---- Difficulty / mode ---- */}
      <EditorCard title="Difficulty">
        {isAlwaysHard ? (
          <p className={s.alwaysHardNote}>
            This subject ({value.subject_display ?? subjectKey}) is
            always-hard mode. The server enforces hard delivery regardless of
            this setting.
          </p>
        ) : (
          <Field
            label="Mode"
            hint="Controls adaptive difficulty thresholds and Boss HP"
          >
            <div className={s.modeGroup} role="group" aria-label="Mode">
              <button
                type="button"
                className={`${s.modeBtn} ${currentMode === "easy" ? s.modeBtnActive : ""}`}
                aria-pressed={currentMode === "easy"}
                onClick={() => patch({ mode: "easy" })}
              >
                <span className={s.modeBtnIcon}>&#9711;</span>
                Easy
              </button>
              <button
                type="button"
                className={`${s.modeBtn} ${currentMode === "hard" ? s.modeBtnActive : ""}`}
                aria-pressed={currentMode === "hard"}
                onClick={() => patch({ mode: "hard" })}
              >
                <span className={s.modeBtnIcon}>&#11088;</span>
                Hard
              </button>
            </div>
          </Field>
        )}
      </EditorCard>
    </div>
  );
}
