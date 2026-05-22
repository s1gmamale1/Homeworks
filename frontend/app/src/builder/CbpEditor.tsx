import type {
  CheckpointKind,
  DraftCaseBasedPreview,
  DraftCheckpoint,
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
import s from "./editors.module.css";

const KIND_OPTIONS: { value: CheckpointKind; label: string }[] = [
  { value: "identify", label: "Identify" },
  { value: "decide", label: "Decide" },
  { value: "justify", label: "Justify" },
];

// Authors the Case-Based Preview: title, case_setup, EXACTLY 3 checkpoints
// (each with an option-index answer picker + learning_block), final_simulation,
// feedback_summary. The option-index picker writes
// {type:"option_index", expected:<idx>, option_count:<n>}.
export function CbpEditor({
  value,
  onChange,
}: {
  value: DraftCaseBasedPreview;
  onChange: (next: DraftCaseBasedPreview) => void;
}) {
  const patch = (p: Partial<DraftCaseBasedPreview>) => onChange({ ...value, ...p });

  const patchCheckpoint = (i: number, p: Partial<DraftCheckpoint>) => {
    const checkpoints = value.checkpoints.map((ck, idx) =>
      idx === i ? { ...ck, ...p } : ck
    );
    patch({ checkpoints });
  };

  return (
    <div className={s.editor}>
      <EditorCard title="Case overview">
        <Field label="Case title">
          <TextInput
            value={value.title}
            onChange={(v) => patch({ title: v })}
            placeholder="e.g. The Reactor Pressure Crisis"
          />
        </Field>
        <Field label="Story" hint="The dramatic setup the student reads first">
          <TextArea
            value={value.case_setup.story}
            rows={4}
            onChange={(v) =>
              patch({ case_setup: { ...value.case_setup, story: v } })
            }
            placeholder="Set the scene…"
          />
        </Field>
        <Field label="Your role">
          <TextInput
            value={value.case_setup.role}
            onChange={(v) =>
              patch({ case_setup: { ...value.case_setup, role: v } })
            }
            placeholder="e.g. Lead engineer on call"
          />
        </Field>
        <Field label="Your task">
          <TextInput
            value={value.case_setup.task}
            onChange={(v) =>
              patch({ case_setup: { ...value.case_setup, task: v } })
            }
            placeholder="e.g. Decide whether to vent the chamber"
          />
        </Field>
      </EditorCard>

      {value.checkpoints.map((ck, i) => (
        <EditorCard key={i} title={`Checkpoint ${i + 1}`}>
          <Field label="Kind">
            <Select<CheckpointKind>
              value={ck.kind}
              options={KIND_OPTIONS}
              onChange={(kind) => patchCheckpoint(i, { kind })}
            />
          </Field>
          <Field label="Question">
            <TextArea
              value={ck.question}
              onChange={(question) => patchCheckpoint(i, { question })}
              placeholder="What does the student decide here?"
            />
          </Field>
          <OptionEditor
            options={ck.options}
            correctIndex={ck.answer_spec.expected}
            onOptionChange={(oi, v) => {
              const options = ck.options.map((o, idx) => (idx === oi ? v : o));
              patchCheckpoint(i, { options });
            }}
            onCorrectChange={(oi) =>
              patchCheckpoint(i, {
                answer_spec: optionIndexSpec(oi, ck.options.length),
              })
            }
            onAddOption={() =>
              patchCheckpoint(i, { options: [...ck.options, ""] })
            }
            onRemoveOption={(oi) => {
              const options = ck.options.filter((_, idx) => idx !== oi);
              const expected = Math.min(
                ck.answer_spec.expected,
                options.length - 1
              );
              patchCheckpoint(i, {
                options,
                answer_spec: optionIndexSpec(Math.max(0, expected), options.length),
              });
            }}
          />
          <Field label="Learning block" hint="Taught after they answer">
            <TextArea
              value={ck.learning_block}
              onChange={(learning_block) => patchCheckpoint(i, { learning_block })}
              placeholder="The teaching beat the student reads next…"
            />
          </Field>
        </EditorCard>
      ))}

      <EditorCard title="Final simulation">
        <Field
          label="Correct path"
          hint="Redacted from students — surfaced via grading feedback"
        >
          <TextArea
            value={value.final_simulation.correct_path}
            onChange={(v) =>
              patch({
                final_simulation: { ...value.final_simulation, correct_path: v },
              })
            }
            placeholder="How the case resolves when they reason well…"
          />
        </Field>
        <Field label="Wrong path">
          <TextArea
            value={value.final_simulation.wrong_path}
            onChange={(v) =>
              patch({
                final_simulation: { ...value.final_simulation, wrong_path: v },
              })
            }
            placeholder="What goes wrong if they slip…"
          />
        </Field>
      </EditorCard>

      <EditorCard title="Feedback summary">
        <Field label="What the student understood">
          <TextArea
            value={value.feedback_summary.student_understood}
            onChange={(v) =>
              patch({
                feedback_summary: {
                  ...value.feedback_summary,
                  student_understood: v,
                },
              })
            }
          />
        </Field>
        <Field label="Where mistakes appeared">
          <TextArea
            value={value.feedback_summary.mistake_appeared}
            onChange={(v) =>
              patch({
                feedback_summary: {
                  ...value.feedback_summary,
                  mistake_appeared: v,
                },
              })
            }
          />
        </Field>
        <Field label="What to review">
          <TextArea
            value={value.feedback_summary.what_to_review}
            onChange={(v) =>
              patch({
                feedback_summary: {
                  ...value.feedback_summary,
                  what_to_review: v,
                },
              })
            }
          />
        </Field>
      </EditorCard>

      <p className={s.note}>
        <SmallButton onClick={() => undefined} disabled>
          3 checkpoints fixed
        </SmallButton>
        The Case-Based Preview always runs exactly 3 checkpoints — identify,
        decide, justify.
      </p>
    </div>
  );
}
