import type {
  CheckpointKind,
  DraftCaseBasedPreview,
  DraftCbpBlock,
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

const CHECKPOINT_KINDS: CheckpointKind[] = ["identify", "decide", "justify"];

function newCheckpoint(kind: CheckpointKind): DraftCheckpoint {
  return {
    kind,
    question: "",
    options: ["", "", "", ""],
    answer_spec: optionIndexSpec(0, 4),
    learning_block: "",
  };
}

// Seed an ordered `blocks[]` overlay for a legacy draft that only has
// case_setup + checkpoints[]: the story becomes the first TEXT page, then one
// CHECKPOINT block per existing checkpoint in index order. This runs once, the
// first time the author touches the editor on an old homework, so older
// homeworks open cleanly while still emitting case_setup + checkpoints for
// runtime back-compat.
function seedBlocks(value: DraftCaseBasedPreview): DraftCbpBlock[] {
  const blocks: DraftCbpBlock[] = [];
  const story = value.case_setup.story;
  if (story && story.trim() !== "") {
    blocks.push({ type: "text", title: "Story", body: story });
  }
  value.checkpoints.forEach((_ck, i) => {
    blocks.push({ type: "checkpoint", ref: i });
  });
  return blocks;
}

// Authors the Case-Based Preview as an ORDERED, reorderable list of blocks —
// TEXT PAGES + CHECKPOINTS in any order/count. Each checkpoint block edits
// checkpoints[ref] inline (the ref indirection is hidden from the author);
// checkpoints[] STAYS the canonical grading source. Plus the unchanged
// final_simulation + feedback_summary cards. case_setup + checkpoints are still
// emitted (via toContentJson) for runtime back-compat.
export function CbpEditor({
  value,
  onChange,
}: {
  value: DraftCaseBasedPreview;
  onChange: (next: DraftCaseBasedPreview) => void;
}) {
  const patch = (p: Partial<DraftCaseBasedPreview>) => onChange({ ...value, ...p });

  // Back-compat: a loaded draft may have NO `blocks`. Seed them lazily so the
  // ordered list always has something to render. We never mutate `value` here —
  // we just compute the working list; the first edit persists it via patch().
  const blocks: DraftCbpBlock[] = value.blocks ?? seedBlocks(value);

  const setBlocks = (next: DraftCbpBlock[]) => patch({ blocks: next });

  const patchCheckpoint = (ref: number, p: Partial<DraftCheckpoint>) => {
    const checkpoints = value.checkpoints.map((ck, idx) =>
      idx === ref ? { ...ck, ...p } : ck
    );
    // Persist seeded blocks alongside the checkpoint edit so the overlay sticks.
    onChange({ ...value, checkpoints, blocks });
  };

  // ---- block-level mutations (operate on blocks[]; keep refs valid) ----

  const addTextPage = () => {
    setBlocks([...blocks, { type: "text", title: "", body: "" }]);
  };

  const addCheckpoint = () => {
    // Append a new checkpoint; its index is the canonical ref. Cycle the
    // suggested kind (identify → decide → justify → identify …) by count.
    const newRef = value.checkpoints.length;
    const kind = CHECKPOINT_KINDS[newRef % CHECKPOINT_KINDS.length];
    onChange({
      ...value,
      checkpoints: [...value.checkpoints, newCheckpoint(kind)],
      blocks: [...blocks, { type: "checkpoint", ref: newRef }],
    });
  };

  const moveBlock = (i: number, delta: number) => {
    const j = i + delta;
    if (j < 0 || j >= blocks.length) return;
    const next = [...blocks];
    [next[i], next[j]] = [next[j], next[i]];
    // Reorder ONLY changes presentation order; refs point into checkpoints[] by
    // index, so they remain valid + untouched.
    setBlocks(next);
  };

  const removeBlock = (i: number) => {
    const block = blocks[i];
    if (block.type !== "checkpoint") {
      // Text page: just drop it.
      setBlocks(blocks.filter((_, idx) => idx !== i));
      return;
    }
    // Checkpoint block: drop its checkpoints[] entry, drop the block, and FIX UP
    // every remaining checkpoint block whose ref was past the removed one so all
    // refs stay valid + contiguous against the shrunken checkpoints[] array.
    const removedRef = block.ref;
    const checkpoints = value.checkpoints.filter((_, idx) => idx !== removedRef);
    const nextBlocks = blocks
      .filter((_, idx) => idx !== i)
      .map((b) =>
        b.type === "checkpoint" && b.ref > removedRef
          ? { ...b, ref: b.ref - 1 }
          : b
      );
    onChange({ ...value, checkpoints, blocks: nextBlocks });
  };

  // Stable, per-render keys so React doesn't lose focus on edit/reorder. We use
  // the array index — order changes are explicit (move buttons re-render).
  let checkpointCount = 0;

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

      <p className={s.help}>
        Build the case as an ordered sequence of text pages and checkpoints. The
        student reads each block in this order; reorder with the arrows.
      </p>

      {blocks.map((block, i) => {
        const rowControls = (
          <span className={s.cardActions}>
            <SmallButton onClick={() => moveBlock(i, -1)} disabled={i === 0}>
              ↑
            </SmallButton>
            <SmallButton
              onClick={() => moveBlock(i, 1)}
              disabled={i === blocks.length - 1}
            >
              ↓
            </SmallButton>
            <SmallButton tone="danger" onClick={() => removeBlock(i)}>
              Remove
            </SmallButton>
          </span>
        );

        if (block.type === "text") {
          return (
            <EditorCard
              key={`block-${i}`}
              title="Text page"
              actions={rowControls}
            >
              <Field label="Page title" hint="Optional heading">
                <TextInput
                  value={block.title ?? ""}
                  onChange={(v) =>
                    setBlocks(
                      blocks.map((b, idx) =>
                        idx === i && b.type === "text"
                          ? { ...b, title: v }
                          : b
                      )
                    )
                  }
                  placeholder="e.g. The Setup"
                />
              </Field>
              <Field label="Body" hint="Story or teaching text the student reads">
                <TextArea
                  value={block.body ?? ""}
                  rows={4}
                  onChange={(v) =>
                    setBlocks(
                      blocks.map((b, idx) =>
                        idx === i && b.type === "text"
                          ? { ...b, body: v }
                          : b
                      )
                    )
                  }
                  placeholder="Set the scene…"
                />
              </Field>
            </EditorCard>
          );
        }

        // checkpoint block — edit checkpoints[ref] inline. Guard against a
        // dangling ref (shouldn't happen given the bookkeeping, but stay total).
        const ref = block.ref;
        const ck = value.checkpoints[ref];
        if (!ck) {
          return (
            <EditorCard
              key={`block-${i}`}
              title="Checkpoint (missing)"
              actions={rowControls}
            >
              <p className={s.empty}>
                This checkpoint lost its data. Remove it and add a fresh one.
              </p>
            </EditorCard>
          );
        }
        checkpointCount += 1;
        const cpNumber = checkpointCount;
        return (
          <EditorCard
            key={`block-${i}`}
            title={`Checkpoint ${cpNumber}`}
            actions={rowControls}
          >
            <Field label="Kind">
              <Select<CheckpointKind>
                value={ck.kind}
                options={KIND_OPTIONS}
                onChange={(kind) => patchCheckpoint(ref, { kind })}
              />
            </Field>
            <Field label="Question">
              <TextArea
                value={ck.question}
                onChange={(question) => patchCheckpoint(ref, { question })}
                placeholder="What does the student decide here?"
              />
            </Field>
            <OptionEditor
              options={ck.options}
              correctIndex={ck.answer_spec.expected}
              onOptionChange={(oi, v) => {
                const options = ck.options.map((o, idx) => (idx === oi ? v : o));
                patchCheckpoint(ref, { options });
              }}
              onCorrectChange={(oi) =>
                patchCheckpoint(ref, {
                  answer_spec: optionIndexSpec(oi, ck.options.length),
                })
              }
              onAddOption={() =>
                patchCheckpoint(ref, { options: [...ck.options, ""] })
              }
              onRemoveOption={(oi) => {
                const options = ck.options.filter((_, idx) => idx !== oi);
                const expected = Math.min(
                  ck.answer_spec.expected,
                  options.length - 1
                );
                patchCheckpoint(ref, {
                  options,
                  answer_spec: optionIndexSpec(
                    Math.max(0, expected),
                    options.length
                  ),
                });
              }}
            />
            <Field label="Learning block" hint="Taught after they answer">
              <TextArea
                value={ck.learning_block}
                onChange={(learning_block) =>
                  patchCheckpoint(ref, { learning_block })
                }
                placeholder="The teaching beat the student reads next…"
              />
            </Field>
          </EditorCard>
        );
      })}

      <div className={s.gamePicker}>
        <SmallButton onClick={addTextPage}>+ Add text page</SmallButton>
        <SmallButton tone="primary" onClick={addCheckpoint}>
          + Add checkpoint
        </SmallButton>
      </div>

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
    </div>
  );
}
