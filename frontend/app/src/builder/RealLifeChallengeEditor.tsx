import { useState } from "react";
import type {
  RealLifeChallengeEditorProps,
  DraftRealLifeChallenge,
  DraftRLCStep,
  DraftRLCDecisionOption,
  DraftRLCConceptChip,
  RLCExpertRole,
  RLCStepKind,
} from "./types";
import {
  EditorCard,
  Field,
  TextInput,
  TextArea,
  NumberInput,
  Select,
  SmallButton,
} from "./fields";
import s from "./RealLifeChallengeEditor.module.css";

// ---------------------------------------------------------------------------
// Real-Life Challenge editor — owns content_json.real_life_challenge
// (DraftRealLifeChallenge | null). The MOST nested authoring slice:
//
//   case
//    ├─ case-level fields (id / expert_role / title / intro / pisa / tier / …)
//    └─ steps[5]  (FIXED order + FIXED kind per slot, per the server validator)
//         ├─ decision        → options[] (≥2, exactly 1 correct, consequence)
//         ├─ info_request     → options[] (≥2, exactly 1 correct, consequence)
//         ├─ final_decision   → options[] (≥2, exactly 1 correct, consequence)
//         ├─ concept_select   → concept_chips[] (≥3, exactly 1 correct)
//         └─ reasoning        → placeholder / min_chars / acceptable_keywords
//
// server/schemas/content.py RealLifeChallengeCase (~507) enforces:
//   - len(steps) == 5
//   - step kinds match the fixed order exactly
//   - decision-kind steps have ≥2 options + exactly 1 is_correct
//   - concept_select has ≥3 chips + exactly 1 is_correct
//   - reasoning min_chars ∈ [20, 1000] (defaults 80)
//
// Because the order + per-slot kind are part of the contract, the editor does
// NOT offer "reorder" or "change kind" (that would produce a non-savable case).
// Instead it seeds the canonical 5-slot skeleton on case creation and lets the
// author edit each step in place (collapsible cards). is_correct / consequence
// / acceptable_keywords are author-set here and stripped server-side before
// delivery (the runtime never holds answers).
// ---------------------------------------------------------------------------

const EXPERT_ROLE_OPTIONS: { value: RLCExpertRole; label: string }[] = [
  { value: "general", label: "General" },
  { value: "fire_inspector", label: "Fire Inspector" },
  { value: "structural_engineer", label: "Structural Engineer" },
  { value: "business_consultant", label: "Business Consultant" },
  { value: "medical_diagnostician", label: "Medical Diagnostician" },
  { value: "agronomist", label: "Agronomist" },
  { value: "teacher", label: "Teacher" },
  { value: "lawyer", label: "Lawyer" },
  { value: "city_planner", label: "City Planner" },
  { value: "epidemiologist", label: "Epidemiologist" },
  { value: "ethicist", label: "Ethicist" },
  { value: "historian", label: "Historian" },
];

const PISA_OPTIONS: { value: string; label: string }[] = [
  { value: "L1", label: "L1" },
  { value: "L2", label: "L2" },
  { value: "L3", label: "L3" },
  { value: "L4", label: "L4" },
  { value: "L5", label: "L5" },
  { value: "L6", label: "L6" },
];

const TIER_OPTIONS: { value: "basic" | "premium"; label: string }[] = [
  { value: "basic", label: "Basic" },
  { value: "premium", label: "Premium" },
];

const GRADE_BAND_OPTIONS: {
  value: "g1_3" | "g4_6" | "g7_9" | "g10_11";
  label: string;
}[] = [
  { value: "g1_3", label: "Grades 1–3" },
  { value: "g4_6", label: "Grades 4–6" },
  { value: "g7_9", label: "Grades 7–9" },
  { value: "g10_11", label: "Grades 10–11" },
];

const VARIANT_OPTIONS: {
  value: "standard" | "creative_thinking";
  label: string;
}[] = [
  { value: "standard", label: "Standard" },
  { value: "creative_thinking", label: "Creative thinking (premium)" },
];

// The 5 fixed slots in spec order, with human labels + per-kind authoring help.
const STEP_SLOTS: {
  kind: RLCStepKind;
  badge: string;
  label: string;
  defaultTitle: string;
  help: string;
}[] = [
  {
    kind: "decision",
    badge: "1",
    label: "Decision",
    defaultTitle: "Step 1 · Size up the situation",
    help: "The opening call. Give ≥2 options and mark exactly one correct.",
  },
  {
    kind: "info_request",
    badge: "2",
    label: "Info request",
    defaultTitle: "Step 2 · Gather information",
    help: "What does the expert ask for first? ≥2 options, exactly one correct.",
  },
  {
    kind: "final_decision",
    badge: "3",
    label: "Final decision",
    defaultTitle: "Step 3 · Commit to a course of action",
    help: "The decisive move. ≥2 options, exactly one correct.",
  },
  {
    kind: "concept_select",
    badge: "4",
    label: "Concept select",
    defaultTitle: "Step 4 · Name the underlying concept",
    help: "≥3 concept chips; mark exactly one as the correct concept.",
  },
  {
    kind: "reasoning",
    badge: "5",
    label: "Reasoning",
    defaultTitle: "Step 5 · Justify your reasoning",
    help: "Free-text. Set the minimum length and the grading keyword anchors.",
  },
];

const KIND_TO_SLOT = Object.fromEntries(
  STEP_SLOTS.map((slot) => [slot.kind, slot])
) as Record<RLCStepKind, (typeof STEP_SLOTS)[number]>;

// option ids are stable per-slot letters "a"/"b"/"c"…; chip ids are "c1"/"c2"…
function optionLetter(i: number): string {
  return String.fromCharCode(97 + i); // 0 -> "a"
}

function makeOption(i: number, isCorrect = false): DraftRLCDecisionOption {
  return { id: optionLetter(i), label: "", ...(isCorrect ? { is_correct: true } : {}) };
}

function makeChip(i: number, isCorrect = false): DraftRLCConceptChip {
  return { id: `c${i + 1}`, label: "", ...(isCorrect ? { is_correct: true } : {}) };
}

// Build a fresh, schema-valid 5-step skeleton (2 options/chips, 1st marked
// correct; reasoning defaults min_chars 80) so a new case saves immediately.
function makeStep(slotIndex: number): DraftRLCStep {
  const slot = STEP_SLOTS[slotIndex];
  const base: DraftRLCStep = {
    id: `step${slotIndex + 1}`,
    kind: slot.kind,
    title: slot.defaultTitle,
    prompt: "",
  };
  if (slot.kind === "concept_select") {
    base.concept_chips = [makeChip(0, true), makeChip(1), makeChip(2)];
  } else if (slot.kind === "reasoning") {
    base.placeholder = "";
    base.min_chars = 80;
    base.acceptable_keywords = [];
  } else {
    base.options = [makeOption(0, true), makeOption(1)];
  }
  return base;
}

function makeCase(): DraftRealLifeChallenge {
  return {
    id: "rlc_001",
    expert_role: "general",
    title: "",
    intro: "",
    pisa_level: "L4",
    tier: "basic",
    grade_band: "g7_9",
    variant: "standard",
    steps: STEP_SLOTS.map((_, i) => makeStep(i)),
  };
}

// --- decision/info/final option sub-editor -------------------------------- //
function OptionsBlock({
  options,
  onChange,
}: {
  options: DraftRLCDecisionOption[];
  onChange: (next: DraftRLCDecisionOption[]) => void;
}) {
  const setCorrect = (idx: number) =>
    onChange(
      options.map((o, i) =>
        i === idx ? { ...o, is_correct: true } : { ...o, is_correct: false }
      )
    );

  const patch = (idx: number, partial: Partial<DraftRLCDecisionOption>) =>
    onChange(options.map((o, i) => (i === idx ? { ...o, ...partial } : o)));

  const add = () => onChange([...options, makeOption(options.length)]);

  const remove = (idx: number) => {
    // Re-letter remaining ids so they stay "a","b","c"… and keep a correct one.
    const filtered = options.filter((_, i) => i !== idx);
    const hadCorrect = filtered.some((o) => o.is_correct);
    onChange(
      filtered.map((o, i) => ({
        ...o,
        id: optionLetter(i),
        is_correct: hadCorrect ? o.is_correct : i === 0,
      }))
    );
  };

  return (
    <div className={s.choiceGroup}>
      <span className={s.choiceGroupLabel}>
        Options
        <span className={s.choiceGroupHint}>
          Tap the circle to mark the one correct answer — exactly one required
        </span>
      </span>
      {options.map((opt, i) => (
        <div key={opt.id} className={s.optionRow}>
          <div className={s.optionRowTop}>
            <button
              type="button"
              className={`${s.correctRadio} ${opt.is_correct ? s.correctRadioOn : ""}`}
              aria-label={`Mark option ${opt.id.toUpperCase()} correct`}
              aria-pressed={!!opt.is_correct}
              onClick={() => setCorrect(i)}
            >
              {opt.is_correct ? "✓" : ""}
            </button>
            <span className={s.optionTag}>{opt.id.toUpperCase()}</span>
            <input
              className={s.optionInput}
              value={opt.label}
              placeholder={`Option ${opt.id.toUpperCase()}`}
              onChange={(e) => patch(i, { label: e.target.value })}
            />
            {options.length > 2 && (
              <SmallButton tone="danger" onClick={() => remove(i)}>
                ✕
              </SmallButton>
            )}
          </div>
          <input
            className={s.consequenceInput}
            value={opt.consequence ?? ""}
            placeholder="Consequence — shown after the student picks (optional)"
            onChange={(e) =>
              patch(i, { consequence: e.target.value || undefined })
            }
          />
        </div>
      ))}
      <SmallButton onClick={add}>+ Add option</SmallButton>
    </div>
  );
}

// --- concept_select chip sub-editor --------------------------------------- //
function ChipsBlock({
  chips,
  onChange,
}: {
  chips: DraftRLCConceptChip[];
  onChange: (next: DraftRLCConceptChip[]) => void;
}) {
  const setCorrect = (idx: number) =>
    onChange(
      chips.map((c, i) =>
        i === idx ? { ...c, is_correct: true } : { ...c, is_correct: false }
      )
    );

  const patch = (idx: number, partial: Partial<DraftRLCConceptChip>) =>
    onChange(chips.map((c, i) => (i === idx ? { ...c, ...partial } : c)));

  const add = () => onChange([...chips, makeChip(chips.length)]);

  const remove = (idx: number) => {
    const filtered = chips.filter((_, i) => i !== idx);
    const hadCorrect = filtered.some((c) => c.is_correct);
    onChange(
      filtered.map((c, i) => ({
        ...c,
        id: `c${i + 1}`,
        is_correct: hadCorrect ? c.is_correct : i === 0,
      }))
    );
  };

  return (
    <div className={s.choiceGroup}>
      <span className={s.choiceGroupLabel}>
        Concept chips
        <span className={s.choiceGroupHint}>
          At least 3 — tap the circle to mark the one correct concept
        </span>
      </span>
      {chips.map((chip, i) => (
        <div key={chip.id} className={s.optionRowTop}>
          <button
            type="button"
            className={`${s.correctRadio} ${chip.is_correct ? s.correctRadioOn : ""}`}
            aria-label={`Mark concept ${i + 1} correct`}
            aria-pressed={!!chip.is_correct}
            onClick={() => setCorrect(i)}
          >
            {chip.is_correct ? "✓" : ""}
          </button>
          <input
            className={s.optionInput}
            value={chip.label}
            placeholder={`Concept ${i + 1}`}
            onChange={(e) => patch(i, { label: e.target.value })}
          />
          {chips.length > 3 && (
            <SmallButton tone="danger" onClick={() => remove(i)}>
              ✕
            </SmallButton>
          )}
        </div>
      ))}
      <SmallButton onClick={add}>+ Add concept</SmallButton>
    </div>
  );
}

// --- reasoning sub-editor (keywords as a comma list) ---------------------- //
function ReasoningBlock({
  step,
  onPatch,
}: {
  step: DraftRLCStep;
  onPatch: (partial: Partial<DraftRLCStep>) => void;
}) {
  const keywords = step.acceptable_keywords ?? [];
  return (
    <>
      <Field label="Input placeholder" hint="The grey hint inside the textarea">
        <TextInput
          value={step.placeholder ?? ""}
          onChange={(v) => onPatch({ placeholder: v || undefined })}
          placeholder="e.g. Explain why you'd vent the chamber…"
        />
      </Field>
      <Field
        label="Minimum characters"
        hint="Between 20 and 1000 (defaults to 80)"
      >
        <NumberInput
          value={step.min_chars ?? 80}
          min={20}
          max={1000}
          step={10}
          onChange={(v) => onPatch({ min_chars: v })}
        />
      </Field>
      <Field
        label="Grading keywords"
        hint="Author-only anchors for AI grading — comma separated, stripped server-side"
      >
        <TextArea
          value={keywords.join(", ")}
          rows={2}
          onChange={(v) =>
            onPatch({
              acceptable_keywords: v
                .split(",")
                .map((k) => k.trim())
                .filter(Boolean),
            })
          }
          placeholder="pressure, safety margin, evacuation, …"
        />
      </Field>
    </>
  );
}

// --- one collapsible step card -------------------------------------------- //
function StepCard({
  step,
  index,
  open,
  onToggle,
  onPatch,
}: {
  step: DraftRLCStep;
  index: number;
  open: boolean;
  onToggle: () => void;
  onPatch: (partial: Partial<DraftRLCStep>) => void;
}) {
  const slot = KIND_TO_SLOT[step.kind] ?? STEP_SLOTS[index];
  const isDecisionKind =
    step.kind === "decision" ||
    step.kind === "info_request" ||
    step.kind === "final_decision";
  const isConcept = step.kind === "concept_select";
  const isReasoning = step.kind === "reasoning";

  // A compact validity hint for the collapsed header.
  let summary = "";
  if (isDecisionKind) {
    const n = step.options?.length ?? 0;
    const correct = step.options?.filter((o) => o.is_correct).length ?? 0;
    summary = `${n} option${n === 1 ? "" : "s"} · ${correct} correct`;
  } else if (isConcept) {
    const n = step.concept_chips?.length ?? 0;
    const correct = step.concept_chips?.filter((c) => c.is_correct).length ?? 0;
    summary = `${n} chip${n === 1 ? "" : "s"} · ${correct} correct`;
  } else if (isReasoning) {
    summary = `≥ ${step.min_chars ?? 80} chars`;
  }

  return (
    <section className={`${s.stepCard} ${open ? s.stepCardOpen : ""}`}>
      <button
        type="button"
        className={s.stepHead}
        onClick={onToggle}
        aria-expanded={open}
      >
        <span className={s.stepBadge}>{slot.badge}</span>
        <span className={s.stepHeadText}>
          <span className={s.stepKind}>{slot.label}</span>
          <span className={s.stepTitlePreview}>
            {step.title || slot.defaultTitle}
          </span>
        </span>
        <span className={s.stepSummary}>{summary}</span>
        <span className={`${s.chevron} ${open ? s.chevronOpen : ""}`} aria-hidden="true">
          ⌄
        </span>
      </button>

      {open && (
        <div className={s.stepBody}>
          <p className={s.stepHelp}>{slot.help}</p>

          <Field label="Step title">
            <TextInput
              value={step.title}
              onChange={(v) => onPatch({ title: v })}
              placeholder={slot.defaultTitle}
            />
          </Field>

          <Field label="Prompt" hint="What the student reads on this step">
            <TextArea
              value={step.prompt}
              rows={3}
              onChange={(v) => onPatch({ prompt: v })}
              placeholder="Describe the situation + the question…"
            />
          </Field>

          {isDecisionKind && (
            <OptionsBlock
              options={step.options ?? []}
              onChange={(options) => onPatch({ options })}
            />
          )}

          {isConcept && (
            <ChipsBlock
              chips={step.concept_chips ?? []}
              onChange={(concept_chips) => onPatch({ concept_chips })}
            />
          )}

          {isReasoning && <ReasoningBlock step={step} onPatch={onPatch} />}
        </div>
      )}
    </section>
  );
}

// --------------------------------------------------------------------------- //
// Main editor
// --------------------------------------------------------------------------- //
export function RealLifeChallengeEditor({
  value,
  onChange,
}: RealLifeChallengeEditorProps) {
  // Which step cards are expanded (default: step 1 open).
  const [openSteps, setOpenSteps] = useState<Record<number, boolean>>({ 0: true });

  // --- empty state: no case yet --- //
  if (!value) {
    return (
      <div className={s.editor}>
        <div className={s.emptyState}>
          <div className={s.emptyIcon} aria-hidden="true">
            <svg
              width="34"
              height="34"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <p className={s.emptyLabel}>No Real-Life Challenge</p>
          <p className={s.emptyBody}>
            A 5-step expert role-play case: the student makes a decision, requests
            information, commits to a final call, names the underlying concept, and
            justifies their reasoning. Add a case to author all five steps.
          </p>
          <SmallButton tone="primary" onClick={() => onChange(makeCase())}>
            + Add Real-Life Challenge
          </SmallButton>
        </div>
      </div>
    );
  }

  const patch = (partial: Partial<DraftRealLifeChallenge>) =>
    onChange({ ...value, ...partial });

  const patchStep = (idx: number, partial: Partial<DraftRLCStep>) =>
    patch({
      steps: value.steps.map((st, i) => (i === idx ? { ...st, ...partial } : st)),
    });

  const toggleStep = (idx: number) =>
    setOpenSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));

  const isPremium = value.tier === "premium";

  return (
    <div className={s.editor}>
      {/* Case-level fields */}
      <EditorCard
        title="Real-Life Challenge"
        actions={
          <SmallButton tone="danger" onClick={() => onChange(null)}>
            Remove case
          </SmallButton>
        }
      >
        <div className={s.metaGrid}>
          <Field label="Case ID" hint="Stable id, e.g. rlc_001">
            <TextInput
              value={value.id}
              onChange={(v) => patch({ id: v })}
              placeholder="rlc_001"
            />
          </Field>
          <Field label="Expert role">
            <Select<RLCExpertRole>
              value={value.expert_role}
              options={EXPERT_ROLE_OPTIONS}
              onChange={(expert_role) => patch({ expert_role })}
            />
          </Field>
        </div>

        <Field label="Case title">
          <TextInput
            value={value.title}
            onChange={(v) => patch({ title: v })}
            placeholder="e.g. The Bazaar Fire Risk"
          />
        </Field>

        <Field label="Intro" hint="1–3 sentence scenario hook the student reads first">
          <TextArea
            value={value.intro}
            rows={3}
            onChange={(v) => patch({ intro: v })}
            placeholder="Set the scene — who the student is and what just happened…"
          />
        </Field>

        <div className={s.metaGrid}>
          <Field label="PISA level">
            <Select<string>
              value={value.pisa_level ?? "L4"}
              options={PISA_OPTIONS}
              onChange={(pisa_level) => patch({ pisa_level })}
            />
          </Field>
          <Field label="Tier">
            <Select<"basic" | "premium">
              value={value.tier ?? "basic"}
              options={TIER_OPTIONS}
              onChange={(tier) =>
                patch({
                  tier,
                  // creative_thinking is premium-only; downgrade if leaving premium.
                  ...(tier === "basic" && value.variant === "creative_thinking"
                    ? { variant: "standard" }
                    : {}),
                })
              }
            />
          </Field>
          <Field label="Grade band">
            <Select<"g1_3" | "g4_6" | "g7_9" | "g10_11">
              value={value.grade_band ?? "g7_9"}
              options={GRADE_BAND_OPTIONS}
              onChange={(grade_band) => patch({ grade_band })}
            />
          </Field>
          <Field
            label="Variant"
            hint={isPremium ? undefined : "Creative thinking needs the Premium tier"}
          >
            <Select<"standard" | "creative_thinking">
              value={value.variant ?? "standard"}
              options={
                isPremium
                  ? VARIANT_OPTIONS
                  : VARIANT_OPTIONS.filter((o) => o.value === "standard")
              }
              onChange={(variant) => patch({ variant })}
            />
          </Field>
        </div>
      </EditorCard>

      {/* Fixed-order steps */}
      <p className={s.stepsNote}>
        The five steps run in a fixed order — decision, info request, final
        decision, concept select, then reasoning. Edit each in place; the order
        and step kinds are part of the contract and can't be changed.
      </p>

      <div className={s.steps}>
        {value.steps.map((step, i) => (
          <StepCard
            key={step.id || i}
            step={step}
            index={i}
            open={!!openSteps[i]}
            onToggle={() => toggleStep(i)}
            onPatch={(partial) => patchStep(i, partial)}
          />
        ))}
      </div>
    </div>
  );
}
