import type { DraftBossMeta, DraftBossQuestion } from "./types";
import { emptyBossQuestion } from "./draft";
import {
  EditorCard,
  Field,
  TextInput,
  TextArea,
  NumberInput,
  SmallButton,
} from "./fields";
import s from "./editors.module.css";

// Authors boss_meta (name, HP) + boss_questions (q, accepted answers, dmg,
// text_fuzzy answer_spec). The Practice Arc game ORDERING moved to the Practice
// Arc section (PracticeArcOrder in BuilderApp) — the Boss is the implicit final
// node and is not orderable here.
export function BossEditor({
  bossMeta,
  bossQuestions,
  onBossMetaChange,
  onBossQuestionsChange,
}: {
  bossMeta: DraftBossMeta;
  bossQuestions: DraftBossQuestion[];
  onBossMetaChange: (next: DraftBossMeta) => void;
  onBossQuestionsChange: (next: DraftBossQuestion[]) => void;
}) {
  const patchQuestion = (i: number, p: Partial<DraftBossQuestion>) =>
    onBossQuestionsChange(
      bossQuestions.map((q, idx) => (idx === i ? { ...q, ...p } : q))
    );

  return (
    <div className={s.editor}>
      <EditorCard title="Boss">
        <Field label="Boss name">
          <TextInput
            value={bossMeta.name}
            placeholder="e.g. The Equation Wraith"
            onChange={(name) => onBossMetaChange({ ...bossMeta, name })}
          />
        </Field>
        <Field label="Max HP" hint="Total damage to defeat the boss">
          <NumberInput
            value={bossMeta.starting_hp_override}
            min={10}
            step={10}
            onChange={(starting_hp_override) =>
              onBossMetaChange({ ...bossMeta, starting_hp_override })
            }
          />
        </Field>
      </EditorCard>

      <EditorCard
        title="Boss questions"
        actions={
          <SmallButton
            tone="primary"
            onClick={() =>
              onBossQuestionsChange([...bossQuestions, emptyBossQuestion()])
            }
          >
            + Add question
          </SmallButton>
        }
      >
        {bossQuestions.length === 0 && (
          <p className={s.empty}>No boss questions yet.</p>
        )}
        {bossQuestions.map((q, i) => (
          <div key={i} className={s.subItem}>
            <div className={s.subItemHead}>
              <span className={s.subItemLabel}>Question {i + 1}</span>
              <SmallButton
                tone="danger"
                onClick={() =>
                  onBossQuestionsChange(
                    bossQuestions.filter((_, idx) => idx !== i)
                  )
                }
              >
                Remove
              </SmallButton>
            </div>
            <Field label="Question">
              <TextArea
                value={q.q}
                rows={2}
                onChange={(text) => patchQuestion(i, { q: text })}
              />
            </Field>
            <Field
              label="Expected answer"
              hint="Graded fuzzily; the primary accepted answer"
            >
              <TextInput
                value={q.answer_spec.expected}
                onChange={(expected) => {
                  const ans = [expected, ...q.ans.slice(1)];
                  patchQuestion(i, {
                    answer_spec: { ...q.answer_spec, expected },
                    ans,
                  });
                }}
              />
            </Field>
            <Field label="Damage" hint="HP drained on a correct answer">
              <NumberInput
                value={q.dmg}
                min={1}
                step={5}
                onChange={(dmg) => patchQuestion(i, { dmg })}
              />
            </Field>
          </div>
        ))}
      </EditorCard>
    </div>
  );
}
