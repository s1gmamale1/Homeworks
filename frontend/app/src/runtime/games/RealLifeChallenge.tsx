import { useState } from "react";
import { useRuntimeStore } from "../store";
import { submitGameAnswer } from "../../shared/api";
import type { GameProps } from "../GameHost";
import { Eyebrow, Title, Lead, Pill, Button, FeatureCard } from "../../shared/ui/primitives";
import { useAnswerTelemetry } from "../hooks/useAnswerTelemetry";
import IntegrityNudge from "../IntegrityNudge";
import s from "./RealLifeChallenge.module.css";
import type { ClipboardEventHandler } from "react";

// ---------------------------------------------------------------------------
// Real-Life Challenge — 5-step expert role-play decision game.
//
// Content lives at content_json.real_life_challenge (a RealLifeChallengeCase).
// The injector strips: options[].is_correct, options[].consequence,
// concept_chips[].is_correct, steps[].acceptable_keywords.
// So the client NEVER holds answers — grading is always the server's call.
//
// Step kinds (always exactly this order per schema validator):
//   1. decision          → pick one option  → submit selected_option_id
//   2. info_request      → pick one option  → submit selected_option_id
//   3. final_decision    → pick one option  → submit selected_option_id
//   4. concept_select    → pick one chip    → submit selected_chip_id
//   5. reasoning         → free-text        → submit reasoning_text
//
// Server response shape (all steps):
//   { step_id, kind, correct, consequence, correct_option_label,
//     reasoning_score, reasoning_feedback, xp, step_index, total_steps,
//     complete, outcome, completion_bonus_xp, total_xp, rubric_breakdown }
//
// When the reasoning step responds with complete=true we call onComplete().
// Empty content_json.real_life_challenge → graceful skip card.
// ---------------------------------------------------------------------------

// Inline local types — do NOT import from shared/types.ts (contract: new fields
// only; never rename existing ones). These mirror the REDACTED wire shape.

interface RLCOption {
  id: string;
  label: string;
  // is_correct and consequence are stripped by the injector; absent on client
}

interface RLCChip {
  id: string;
  label: string;
  // is_correct stripped by injector
}

type RLCStepKind =
  | "decision"
  | "info_request"
  | "final_decision"
  | "concept_select"
  | "reasoning";

interface RLCStep {
  id: string;
  kind: RLCStepKind;
  title: string;
  prompt: string;
  options?: RLCOption[];
  concept_chips?: RLCChip[];
  placeholder?: string;
  min_chars?: number;
}

interface RLCCase {
  id: string;
  expert_role: string;
  title: string;
  intro: string;
  pisa_level?: string;
  steps: RLCStep[];
}

// Server response — only the fields we read on the client.
interface RLCStepResult {
  step_id: string;
  kind: string;
  correct: boolean;
  consequence: string | null;
  correct_option_label: string | null;
  reasoning_score: number | null;
  reasoning_feedback: string | null;
  complete: boolean;
  outcome: string | null;
  total_xp: number | null;
  rubric_breakdown: Record<string, number> | null;
  // Optional advisory anti-cheat nudge — never answer-bearing.
  integrity_nudge?: { type: string; message: string } | null;
}

// Decision step: pick one option from a list.
function DecisionStep({
  step,
  onPick,
  submitting,
  pickedId,
  result,
}: {
  step: RLCStep;
  onPick: (optionId: string) => void;
  submitting: boolean;
  pickedId: string | null;
  result: RLCStepResult | null;
}) {
  const options = step.options ?? [];
  return (
    <div className={s.optionList} role="group" aria-label="Options">
      {options.map((opt) => {
        const isPicked = pickedId === opt.id;
        const isCorrect = result && isPicked && result.correct;
        const isWrong = result && isPicked && !result.correct;
        return (
          <button
            key={opt.id}
            type="button"
            className={[
              s.option,
              isPicked && s.optionPicked,
              isCorrect && s.optionCorrect,
              isWrong && s.optionWrong,
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onPick(opt.id)}
            disabled={submitting || result !== null}
            aria-pressed={isPicked}
            data-testid={`rlc-option-${opt.id}`}
          >
            <span className={s.optionBullet} aria-hidden="true" />
            <span className={s.optionLabel}>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// Concept-select step: pick one chip from a set.
function ConceptSelectStep({
  step,
  onPick,
  submitting,
  pickedId,
  result,
}: {
  step: RLCStep;
  onPick: (chipId: string) => void;
  submitting: boolean;
  pickedId: string | null;
  result: RLCStepResult | null;
}) {
  const chips = step.concept_chips ?? [];
  return (
    <div className={s.chipGrid} role="group" aria-label="Concepts">
      {chips.map((chip) => {
        const isPicked = pickedId === chip.id;
        const isCorrect = result && isPicked && result.correct;
        const isWrong = result && isPicked && !result.correct;
        return (
          <button
            key={chip.id}
            type="button"
            className={[
              s.chip,
              isPicked && s.chipPicked,
              isCorrect && s.chipCorrect,
              isWrong && s.chipWrong,
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onPick(chip.id)}
            disabled={submitting || result !== null}
            aria-pressed={isPicked}
            data-testid={`rlc-chip-${chip.id}`}
          >
            {chip.label}
          </button>
        );
      })}
    </div>
  );
}

// Reasoning step: free-text textarea.
function ReasoningStep({
  step,
  value,
  onChange,
  submitting,
  result,
  onPaste,
}: {
  step: RLCStep;
  value: string;
  onChange: (v: string) => void;
  submitting: boolean;
  result: RLCStepResult | null;
  // Advisory anti-cheat — observe paste on the reasoning textarea only.
  onPaste?: ClipboardEventHandler;
}) {
  const minChars = step.min_chars ?? 80;
  const tooShort = value.trim().length < minChars;
  return (
    <div className={s.reasoningWrap}>
      <textarea
        className={s.reasoningBox}
        placeholder={step.placeholder ?? "Write your reasoning here…"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onPaste={onPaste}
        disabled={submitting || result !== null}
        rows={5}
        aria-label="Reasoning answer"
        data-testid="rlc-reasoning-input"
      />
      <p className={[s.charHint, tooShort && s.charHintWarn].filter(Boolean).join(" ")}>
        {value.trim().length}/{minChars} characters minimum
      </p>
    </div>
  );
}

// Post-submit feedback panel shown after each step (before advancing).
function FeedbackPanel({
  result,
  onNext,
  isLast,
}: {
  result: RLCStepResult;
  onNext: () => void;
  isLast: boolean;
}) {
  return (
    <div className={s.feedback} role="status" data-testid="rlc-feedback">
      <div className={s.feedbackRow}>
        {result.correct ? (
          <Pill tone="good">Correct</Pill>
        ) : (
          <Pill tone="warn">Not quite</Pill>
        )}
        {result.reasoning_score !== null && (
          <span className={s.scoreLabel}>Score: {result.reasoning_score}/100</span>
        )}
      </div>

      {result.consequence && (
        <p className={s.consequenceText}>{result.consequence}</p>
      )}

      {result.correct_option_label && (
        <p className={s.hintText}>
          The best choice was: <strong>{result.correct_option_label}</strong>
        </p>
      )}

      {result.reasoning_feedback && (
        <p className={s.reasoningFeedbackText}>{result.reasoning_feedback}</p>
      )}

      <div className={s.feedbackActions}>
        <Button
          variant="blue"
          onClick={onNext}
          data-testid={isLast ? "rlc-finish" : "rlc-next-step"}
        >
          {isLast ? "See results →" : "Next step →"}
        </Button>
      </div>
    </div>
  );
}

// Completion screen after all 5 steps.
function CompletionScreen({
  result,
  onComplete,
}: {
  result: RLCStepResult;
  onComplete: () => void;
}) {
  const outcome = result.outcome ?? "completed";
  const totalXp = result.total_xp ?? 0;
  const rb = result.rubric_breakdown;

  return (
    <div className={s.done} data-testid="rlc-complete">
      <Pill tone="good">Case Closed</Pill>
      <Title size="section">
        {outcome === "expert"
          ? "Expert-level decision making."
          : outcome === "apprentice"
          ? "Good thinking — you're learning."
          : "Case complete."}
      </Title>
      <Lead>
        You worked through all 5 steps of the scenario.
        {totalXp > 0 && ` You earned ${totalXp} XP.`}
      </Lead>

      {rb && (
        <FeatureCard className={s.rubricCard}>
          <p className={s.rubricRow}>
            <span>Decision quality</span>
            <strong>{rb.decision_quality ?? 0}</strong>
          </p>
          <p className={s.rubricRow}>
            <span>Concept identification</span>
            <strong>{rb.concept_id ?? 0}</strong>
          </p>
          <p className={s.rubricRow}>
            <span>Reasoning quality</span>
            <strong>{rb.reasoning_quality ?? 0}</strong>
          </p>
          {rb.bonus > 0 && (
            <p className={s.rubricRow}>
              <span>Completion bonus</span>
              <strong>+{rb.bonus}</strong>
            </p>
          )}
        </FeatureCard>
      )}

      <div className={s.actions}>
        <Button variant="blue" onClick={onComplete} data-testid="rlc-continue">
          Continue →
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function RealLifeChallenge({ onComplete }: GameProps) {
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const payload = useRuntimeStore((st) => st.payload);

  // Read the case from the store. Type inline — don't modify shared/types.ts.
  const rlcCase = (payload?.content_json as { real_life_challenge?: RLCCase } | null)
    ?.real_life_challenge ?? null;

  const steps: RLCStep[] = rlcCase?.steps ?? [];

  // Per-step UI state.
  const [stepIndex, setStepIndex] = useState(0);
  // pickedId is either an option id (decision/info/final) or a chip id (concept_select).
  const [pickedId, setPickedId] = useState<string | null>(null);
  const [reasoningText, setReasoningText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // null = not yet submitted this step; non-null = server verdict received.
  const [stepResult, setStepResult] = useState<RLCStepResult | null>(null);
  // The final step's result for the completion screen.
  const [finalResult, setFinalResult] = useState<RLCStepResult | null>(null);
  // Advisory anti-cheat: timing/paste per step (used only on the reasoning step).
  const tele = useAnswerTelemetry(stepIndex);
  const [nudge, setNudge] = useState<{ type: string; message: string } | null>(null);

  // Empty content: graceful skip.
  if (!rlcCase || steps.length === 0) {
    return (
      <div className={s.wrap} data-testid="rlc-empty">
        <Lead>No Real-Life Challenge on this homework.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete}>
            Skip →
          </Button>
        </div>
      </div>
    );
  }

  if (finalResult) {
    return (
      <div className={s.wrap} data-testid="rlc-wrap">
        <CompletionScreen result={finalResult} onComplete={onComplete} />
      </div>
    );
  }

  const currentStep = steps[stepIndex];
  if (!currentStep) {
    // Defensive: shouldn't happen after schema guards 5 steps.
    return (
      <div className={s.wrap}>
        <Lead>Scenario complete.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete}>Continue →</Button>
        </div>
      </div>
    );
  }

  const kind = currentStep.kind;
  const isDecisionKind =
    kind === "decision" || kind === "info_request" || kind === "final_decision";
  const isConceptKind = kind === "concept_select";
  const isReasoningKind = kind === "reasoning";
  const minChars = currentStep.min_chars ?? 80;
  const canSubmitReasoning =
    isReasoningKind && reasoningText.trim().length >= minChars;
  const canSubmitDecision = isDecisionKind && pickedId !== null;
  const canSubmitConcept = isConceptKind && pickedId !== null;
  const canSubmit =
    !submitting &&
    stepResult === null &&
    (canSubmitDecision || canSubmitConcept || canSubmitReasoning);

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);

    // Build the payload fields the backend reads per step kind.
    const extra: Record<string, unknown> = {
      step_id: currentStep.id,
    };
    if (isDecisionKind) extra.selected_option_id = pickedId;
    else if (isConceptKind) extra.selected_chip_id = pickedId;
    else if (isReasoningKind) {
      extra.reasoning_text = reasoningText;
      // Advisory telemetry forwarded ONLY on the typed reasoning step.
      Object.assign(extra, tele.read());
    }

    try {
      const res = await submitGameAnswer<RLCStepResult>(
        hwId,
        sessionId,
        "real-life-challenge",
        extra
      );
      setStepResult(res);
      setNudge(res.integrity_nudge ?? null);
      if (res.complete) {
        setFinalResult(res);
      }
    } catch (err) {
      setError((err as Error).message || "Couldn't submit — please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextStep = () => {
    // If the server already flagged complete, CompletionScreen is shown via
    // finalResult — this branch handles the intermediate steps.
    const next = stepIndex + 1;
    setStepIndex(next < steps.length ? next : stepIndex);
    setPickedId(null);
    setReasoningText("");
    setStepResult(null);
    setError(null);
    setNudge(null);
  };

  const isLastStep = stepIndex === steps.length - 1;

  return (
    <div className={s.wrap} data-testid="rlc-wrap">
      {/* Header */}
      <div className={s.head}>
        <Eyebrow>Real-Life Challenge</Eyebrow>
        <span className={s.progress} data-testid="rlc-progress">
          Step {stepIndex + 1}/{steps.length}
        </span>
      </div>

      {/* Scenario intro (shown on step 1 only) */}
      {stepIndex === 0 && rlcCase.intro && (
        <div className={s.introBox}>
          <p className={s.introText}>{rlcCase.intro}</p>
        </div>
      )}

      {/* Step card */}
      <FeatureCard className={s.stepCard}>
        <p className={s.stepTitle}>{currentStep.title}</p>
        {/* prompt may contain HTML authored by the content creator; we render
            it as text for safety — if HTML rendering is needed, a separate
            sanitized innerHTML prop should be wired per a separate ticket. */}
        <p className={s.stepPrompt}>{currentStep.prompt}</p>

        {/* Input area per kind */}
        {isDecisionKind && (
          <DecisionStep
            step={currentStep}
            onPick={setPickedId}
            submitting={submitting}
            pickedId={pickedId}
            result={stepResult}
          />
        )}

        {isConceptKind && (
          <ConceptSelectStep
            step={currentStep}
            onPick={setPickedId}
            submitting={submitting}
            pickedId={pickedId}
            result={stepResult}
          />
        )}

        {isReasoningKind && (
          <ReasoningStep
            step={currentStep}
            value={reasoningText}
            onChange={setReasoningText}
            submitting={submitting}
            result={stepResult}
            onPaste={tele.onPaste}
          />
        )}
      </FeatureCard>

      {/* Error */}
      {error && (
        <p className={s.error} role="alert">
          {error}
        </p>
      )}

      {/* Submit / feedback */}
      {stepResult === null ? (
        <div className={s.actions}>
          <Button
            variant="blue"
            onClick={handleSubmit}
            disabled={!canSubmit}
            data-testid="rlc-submit"
          >
            {submitting ? "Checking…" : "Submit"}
          </Button>
        </div>
      ) : !finalResult ? (
        <FeedbackPanel
          result={stepResult}
          onNext={handleNextStep}
          isLast={isLastStep}
        />
      ) : null}

      {/* Advisory anti-cheat nudge — beside feedback, never gates the Next/See
          results button above. */}
      <IntegrityNudge nudge={nudge} onDismiss={() => setNudge(null)} />
    </div>
  );
}
