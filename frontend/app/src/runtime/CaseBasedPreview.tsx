import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useRuntimeStore } from "./store";
import {
  Pill,
  Eyebrow,
  Title,
  Lead,
  FeatureCard,
  LessonPanel,
  Button,
} from "../shared/ui/primitives";
import type { Checkpoint, CheckpointKind } from "../shared/types";
import CbpBackdrop from "./CbpBackdrop";
import IntegrityNudge from "./IntegrityNudge";
import { useAnswerTelemetry } from "./hooks/useAnswerTelemetry";
import { acknowledgeNudge } from "../shared/api";
import s from "./CaseBasedPreview.module.css";
import { play } from "./sfx";

const KIND_LABEL: Record<CheckpointKind, string> = {
  identify: "Identify",
  decide: "Decide",
  justify: "Justify",
};

// Fallback minimum characters before the reasoning step can be submitted when a
// homework doesn't author its own `min_chars`. Mirrors the server's default
// gate (80) so the client soft-gate and the server's hard 400 agree.
const MIN_REASONING_CHARS = 80;

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// The Case-Based Preview sub-machine:
//   LEGACY (no authored blocks[]):
//     setup → (checkpoint → learningBlock) ×N → reasoning → sim → feedback
//   AUTHORED-ORDER (case_based_preview.blocks present + non-empty):
//     setup → walk blocks[] in order — a `text` block → textPage, a `checkpoint`
//     block → checkpoint(ref) → learningBlock — then reasoning → sim → feedback.
// Correctness is NEVER assumed client-side — we read the server `{correct}` /
// `{passed}`. The MCQ checkpoints stay the gated, server-authoritative grade;
// the reasoning step is server-graded but non-blocking.
export function CaseBasedPreview() {
  const subStage = useRuntimeStore((st) => st.cbp.subStage);

  switch (subStage) {
    case "setup":
      return <Setup />;
    case "checkpoint":
      return <CheckpointStage />;
    case "learningBlock":
      return <LearningBlockStage />;
    case "textPage":
      return <TextPageStage />;
    case "reasoning":
      return <ReasoningStage />;
    case "sim":
      return <SimulationStage />;
    case "feedback":
      return <FeedbackStage />;
    default:
      return <Setup />;
  }
}

// Full-bleed immersive shell: the living CbpBackdrop sits at z0 (aurora + blobs
// + pointer trail) and the per-substage content animates in at z1. The shell
// re-pins the §4 contrast tokens so a dark-OS visitor never washes out the ink.
function Shell({
  children,
  testid,
}: {
  children: ReactNode;
  testid: string;
}) {
  return (
    <main className={s.shell} data-testid={testid}>
      <CbpBackdrop />
      <div className={s.stage} key={testid}>
        {children}
      </div>
    </main>
  );
}

// ---- setup: dramatic hero with case_setup ----
function Setup() {
  const payload = useRuntimeStore((st) => st.payload);
  const enterCheckpoint = useRuntimeStore((st) => st.enterCheckpoint);
  const enterBlock = useRuntimeStore((st) => st.enterBlock);
  const goto = useRuntimeStore((st) => st.goto);
  const cbp = payload?.content_json.case_based_preview;
  const setup = cbp?.case_setup;

  // AUTHORED-ORDER: when blocks[] is authored + non-empty, "Begin" walks the
  // blocks from index 0. Otherwise it enters the first checkpoint (legacy flow).
  const blocks = cbp?.blocks;
  const hasBlocks = Array.isArray(blocks) && blocks.length > 0;
  const begin = () => (hasBlocks ? enterBlock(0) : enterCheckpoint(0));

  return (
    <Shell testid="cbp-setup">
      <BackToHub onClick={() => goto("hub")} />
      <section className={s.hero}>
        <span className={s.heroGlow} aria-hidden="true" />
        <div className={s.heroBody}>
          <Eyebrow>Case Study</Eyebrow>
          <Title size="hero">
            {cbp?.title ?? payload?.title ?? "The Case"}
          </Title>
          {setup?.story && <Lead>{setup.story}</Lead>}
          <div className={s.heroFacts}>
            {setup?.role && (
              <div className={s.fact}>
                <span className={s.factLabel}>Your role</span>
                <span className={s.factValue}>{setup.role}</span>
              </div>
            )}
            {setup?.task && (
              <div className={s.fact}>
                <span className={s.factLabel}>Your task</span>
                <span className={s.factValue}>{setup.task}</span>
              </div>
            )}
          </div>
          <div className={s.heroCta}>
            <Button variant="blue" onClick={begin} data-testid="cbp-begin">
              Begin checkpoints →
            </Button>
          </div>
        </div>
      </section>
    </Shell>
  );
}

// ---- checkpoint: question + options as LessonPanel rows ----
// INLINE MARKING (core bug fix): after submit, the tapped option renders its
// SERVER-CONFIRMED state — green `correct` if results[index] === true, red
// `wrong` if false — for a short marked window, THEN the store advances to the
// teaching beat. This makes "it was marked" obvious; the client never decides
// correctness (it only renders the server `{correct}`). Reduced-motion safe:
// under reduce we skip the hold and reveal the learning block immediately, so
// the marked state still flashes but the flow doesn't dwell on motion.
const MARK_HOLD_MS = 900;

function CheckpointStage() {
  const payload = useRuntimeStore((st) => st.payload);
  const index = useRuntimeStore((st) => st.cbp.checkpointIndex);
  const submitting = useRuntimeStore((st) => st.cbp.submitting);
  const submitError = useRuntimeStore((st) => st.cbp.submitError);
  const results = useRuntimeStore((st) => st.cbp.results);
  const submit = useRuntimeStore((st) => st.submitCheckpointAnswer);
  const reveal = useRuntimeStore((st) => st.revealCheckpointLearningBlock);

  const checkpoints = payload?.content_json.case_based_preview?.checkpoints ?? [];
  const total = checkpoints.length || 3;
  const checkpoint = checkpoints[index] as Checkpoint | undefined;
  const [selected, setSelected] = useState<number | null>(null);
  // `marked` flips true once the server verdict lands, so the chosen option
  // paints green/red before the teaching beat. Server-confirmed only.
  const [marked, setMarked] = useState(false);
  // Advisory anti-cheat — MCQ taps → timing only (no paste handler needed).
  const tele = useAnswerTelemetry(index);

  // Reset selection + marking whenever we move to a different checkpoint.
  useEffect(() => {
    setSelected(null);
    setMarked(false);
  }, [index]);

  // Once marked, hold the green/red state briefly, then reveal the learning
  // block. Under reduced motion we advance on the next tick (no dwell). The
  // store guards revealCheckpointLearningBlock() to only fire from the
  // checkpoint substage, so a late timer can't bounce a later stage back.
  useEffect(() => {
    if (!marked) return;
    const hold = prefersReducedMotion() ? 0 : MARK_HOLD_MS;
    const t = setTimeout(() => reveal(), hold);
    return () => clearTimeout(t);
  }, [marked, reveal]);

  if (!checkpoint) {
    return (
      <Shell testid="cbp-checkpoint">
        <Lead>This checkpoint is unavailable.</Lead>
      </Shell>
    );
  }

  const onSubmit = async () => {
    if (selected === null || submitting || marked) return;
    // Tap-MCQ checkpoints grade by option index (answer_spec.type=option_index).
    // We submit the tapped index as a string; the server holds the expected
    // index and decides correctness — the client never self-grades. Telemetry
    // is advisory only (timing for these taps).
    const res = await submit(index, String(selected), tele.read());
    // Only enter the marked window on a successful grade; an error keeps the
    // options interactive so the student can retry the submit.
    if (res) setMarked(true);
  };

  // Server-confirmed correctness of the tapped option (once marked).
  const optionState = (i: number): "idle" | "active" | "correct" | "wrong" => {
    if (selected !== i) return "idle";
    if (!marked) return "active";
    return results[index] ? "correct" : "wrong";
  };

  return (
    <Shell testid="cbp-checkpoint">
      <CheckpointProgress current={index} total={total} />
      <Eyebrow>
        Checkpoint {index + 1}: {KIND_LABEL[checkpoint.kind] ?? checkpoint.kind}
      </Eyebrow>
      <Title size="section">{checkpoint.question}</Title>

      <div className={s.options} role="radiogroup" aria-label="Answer options">
        {checkpoint.options.map((opt, i) => (
          <LessonPanel
            key={i}
            eyebrow={`Option ${String.fromCharCode(65 + i)}`}
            title={opt}
            state={optionState(i)}
            disabled={submitting || marked}
            onClick={() => setSelected(i)}
          />
        ))}
      </div>

      {submitError && (
        <p className={s.error} role="alert">
          {submitError}
        </p>
      )}

      <div className={s.actions}>
        <Button
          variant="blue"
          onClick={onSubmit}
          disabled={selected === null || submitting || marked}
          data-testid="cbp-submit"
        >
          {submitting ? "Checking…" : marked ? "Marked ✓" : "Submit answer"}
        </Button>
      </div>
    </Shell>
  );
}

// ---- learningBlock: server feedback + learning_block after submit ----
function LearningBlockStage() {
  const index = useRuntimeStore((st) => st.cbp.checkpointIndex);
  const blockIndex = useRuntimeStore((st) => st.cbp.blockIndex);
  const results = useRuntimeStore((st) => st.cbp.results);
  const feedback = useRuntimeStore((st) => st.cbp.lastFeedback);
  const learningBlock = useRuntimeStore((st) => st.cbp.lastLearningBlock);
  const advance = useRuntimeStore((st) => st.advanceFromLearningBlock);
  const retry = useRuntimeStore((st) => st.retryCheckpoint);
  const payload = useRuntimeStore((st) => st.payload);
  const nudge = useRuntimeStore((st) => st.cbp.lastNudge);
  const dismissNudge = useRuntimeStore((st) => st.dismissCbpNudge);
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);

  const cbp = payload?.content_json.case_based_preview;
  const blocks = cbp?.blocks;
  const hasBlocks = Array.isArray(blocks) && blocks.length > 0;
  const correct = results[index];

  // "Last teaching beat" decides the Continue label (→ reasoning vs → next).
  //   AUTHORED-ORDER: no further blocks sit after this cursor.
  //   LEGACY: this is the final checkpoint.
  const checkpointTotal = cbp?.checkpoints?.length ?? 3;
  const isLast = hasBlocks
    ? blockIndex + 1 >= blocks.length
    : index + 1 >= checkpointTotal;
  // Whether the homework authored an open-ended reasoning step — mirrors the
  // store's enterCbpClose() routing so the last-beat CTA reads honestly.
  const hasReasoning = Boolean(
    cbp?.decision_process_explanation?.prompt
  );
  // The "Checkpoint X of Y" counter: in authored order, count only checkpoint
  // blocks and show this checkpoint's position among them; legacy uses index.
  const checkpointBlocks = hasBlocks
    ? blocks.filter((b): b is { type: "checkpoint"; ref: number } => b.type === "checkpoint")
    : [];
  const ckPosition = hasBlocks
    ? checkpointBlocks.findIndex((b) => b.ref === index) + 1
    : index + 1;
  const ckTotal = hasBlocks ? checkpointBlocks.length : checkpointTotal;

  return (
    <Shell testid="cbp-learning-block">
      <div className={s.lbHead}>
        {correct ? <Pill tone="good">✓ Correct</Pill> : <Pill tone="warn">Not quite</Pill>}
        <span className={s.lbCounter}>
          Checkpoint {ckPosition} of {ckTotal}
        </span>
      </div>

      <FeatureCard className={correct ? s.lbCardGood : s.lbCardWarn}>
        <Eyebrow>{correct ? "Why that works" : "What to rethink"}</Eyebrow>
        {feedback && <Lead className={s.lbText}>{feedback}</Lead>}
        {learningBlock && (
          <div className={s.lbBlock}>
            <p className={s.lbBlockLabel}>Lesson</p>
            <p className={s.lbBlockBody}>{learningBlock}</p>
          </div>
        )}
      </FeatureCard>

      {/* Advisory anti-cheat nudge — beside feedback, never gates Continue. */}
      <IntegrityNudge
        nudge={nudge}
        onDismiss={dismissNudge}
        onRespond={(choice) =>
          acknowledgeNudge(hwId, sessionId, "case_based_preview", choice)
        }
      />

      <div className={s.actions}>
        {!correct && (
          <Button variant="outline" onClick={() => retry(index)} data-testid="cbp-retry">
            Retry checkpoint
          </Button>
        )}
        <Button variant="blue" onClick={advance} data-testid="cbp-continue">
          {isLast
            ? hasReasoning
              ? "Explain your reasoning →"
              : "Continue →"
            : "Next checkpoint →"}
        </Button>
      </div>
    </Shell>
  );
}

// ---- textPage: authored story/text block (AUTHORED-ORDER walker only) ----
// A `text` block in case_based_preview.blocks[] renders here: a glass card with
// the authored title + body + a "Continue →" CTA that steps the walker to the
// next block. Display-only — no grading, no answer content, no gate effect.
function TextPageStage() {
  const payload = useRuntimeStore((st) => st.payload);
  const blockIndex = useRuntimeStore((st) => st.cbp.blockIndex);
  const advance = useRuntimeStore((st) => st.advanceFromTextPage);

  const blocks = payload?.content_json.case_based_preview?.blocks ?? [];
  const block = blocks[blockIndex];
  const isText = block?.type === "text";
  const title = isText ? block.title : undefined;
  const body = isText ? block.body : undefined;

  return (
    <Shell testid="cbp-text-page">
      <Eyebrow>Case Study</Eyebrow>
      {title && <Title size="section">{title}</Title>}
      <FeatureCard className={s.textCard}>
        {body ? (
          <p className={s.textBody}>{body}</p>
        ) : (
          <Lead className={s.lbText}>Continue when you're ready.</Lead>
        )}
      </FeatureCard>

      <div className={s.actions}>
        <Button variant="blue" onClick={advance} data-testid="cbp-text-continue">
          Continue →
        </Button>
      </div>
    </Shell>
  );
}

// ---- reasoning: open-ended Decision Process Explanation (server-graded) ----
// The student types WHY they decided as they did. The grade is the server's
// (passed/score/feedback); it teaches but never blocks — a failed pass lets the
// student edit + resubmit, and they can continue to the simulation regardless.
function ReasoningStage() {
  const text = useRuntimeStore((st) => st.cbp.reasoningText);
  const result = useRuntimeStore((st) => st.cbp.reasoningResult);
  const submitting = useRuntimeStore((st) => st.cbp.reasoningSubmitting);
  const submitError = useRuntimeStore((st) => st.cbp.submitError);
  const setText = useRuntimeStore((st) => st.setReasoningText);
  const submit = useRuntimeStore((st) => st.submitReasoning);
  const enterSim = useRuntimeStore((st) => st.enterSimulation);
  const nudge = useRuntimeStore((st) => st.cbp.lastNudge);
  const dismissNudge = useRuntimeStore((st) => st.dismissCbpNudge);
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  const dpe = useRuntimeStore(
    (st) =>
      st.payload?.content_json.case_based_preview?.decision_process_explanation
  );
  // Advisory anti-cheat — stable resetKey for this single reasoning step.
  const tele = useAnswerTelemetry("cbp-reasoning");

  // The authored prompt + min length drive the step (we only reach here when a
  // prompt exists). Fall back to sane defaults that match the server's gate.
  const minChars = dpe?.min_chars ?? MIN_REASONING_CHARS;
  const promptText =
    dpe?.prompt?.trim() ||
    "Which concept applies here? Why this method over the alternatives? And what mistake would you warn another student to avoid?";
  const chars = text.trim().length;
  const meetsMin = chars >= minChars;
  const passed = result?.passed === true;
  const failed = result != null && !result.passed;

  const onSubmit = () => {
    if (!meetsMin || submitting) return;
    void submit(tele.read());
  };

  return (
    <Shell testid="cbp-reasoning-stage">
      <Eyebrow>Decision Process</Eyebrow>
      <Title size="section">Explain your reasoning.</Title>
      <Lead>{promptText}</Lead>

      <FeatureCard className={s.reasoningCard}>
        <label className={s.reasoningLabel} htmlFor="cbp-reasoning">
          Your decision process
        </label>
        <textarea
          id="cbp-reasoning"
          data-testid="cbp-reasoning"
          className={s.reasoningInput}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onPaste={tele.onPaste}
          placeholder="Walk through your thinking: the concept, the method, and the trap to avoid…"
          rows={6}
          disabled={submitting}
          aria-describedby="cbp-reasoning-count"
        />
        <div className={s.reasoningMeta}>
          <span
            id="cbp-reasoning-count"
            className={`${s.reasoningCount} ${meetsMin ? s.reasoningCountOk : ""}`}
          >
            {chars}/{minChars} characters minimum
          </span>
        </div>
      </FeatureCard>

      {result && (
        <FeatureCard className={passed ? s.reasoningResultGood : s.reasoningResultWarn}>
          <div className={s.lbHead}>
            {passed ? <Pill tone="good">✓ Strong reasoning</Pill> : <Pill tone="warn">Sharpen it</Pill>}
            {typeof result.score === "number" && (
              <span className={s.lbCounter}>{Math.round(result.score)}% match</span>
            )}
          </div>
          {result.feedback && <Lead className={s.lbText}>{result.feedback}</Lead>}
        </FeatureCard>
      )}

      {submitError && (
        <p className={s.error} role="alert">
          {submitError}
        </p>
      )}

      {/* Advisory anti-cheat nudge — beside the verdict, never gates submit. */}
      <IntegrityNudge
        nudge={nudge}
        onDismiss={dismissNudge}
        onRespond={(choice) =>
          acknowledgeNudge(hwId, sessionId, "case_based_preview_reasoning", choice)
        }
      />

      <div className={s.actions}>
        <Button
          variant="blue"
          onClick={onSubmit}
          disabled={!meetsMin || submitting}
          data-testid="cbp-reasoning-submit"
        >
          {submitting ? "Reviewing…" : failed ? "Resubmit reasoning" : "Submit reasoning"}
        </Button>
        {failed && (
          <Button variant="outline" onClick={enterSim}>
            Continue anyway →
          </Button>
        )}
      </div>
    </Shell>
  );
}

// ---- sim: staged reveal of final_simulation.wrong_path → takeaway ----
// The wrong-path card animates in (amber) first; after a beat the correct /
// takeaway card snaps in (emerald) with a connecting arrow between them. All
// motion is transform/opacity, reduced-motion gated (the CSS shows both cards
// instantly under reduce).
function SimulationStage() {
  const payload = useRuntimeStore((st) => st.payload);
  const feedback = useRuntimeStore((st) => st.cbp.lastFeedback);
  const finish = useRuntimeStore((st) => st.finishCbp);
  const [busy, setBusy] = useState(false);

  const sim = payload?.content_json.case_based_preview?.final_simulation;

  const onFinish = async () => {
    setBusy(true);
    await finish();
  };

  return (
    <Shell testid="cbp-simulation">
      <Eyebrow>Final simulation</Eyebrow>
      <Title size="section">How the case plays out.</Title>
      <Lead>The path you avoided — and why the lesson mattered.</Lead>

      <div className={s.simReveal}>
        {sim?.wrong_path && (
          <FeatureCard className={s.simWrong}>
            <Pill tone="warn">If you’d slipped</Pill>
            <p className={s.simBody}>{sim.wrong_path}</p>
          </FeatureCard>
        )}
        {/* Connecting arrow snaps in between the two cards after the beat. */}
        {sim?.wrong_path && feedback && (
          <span className={s.simArrow} aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14" />
              <path d="m6 13 6 6 6-6" />
            </svg>
          </span>
        )}
        {feedback && (
          <FeatureCard className={s.simRight}>
            <Pill tone="good">The takeaway</Pill>
            <p className={s.simBody}>{feedback}</p>
          </FeatureCard>
        )}
      </div>

      <div className={s.actions}>
        <Button variant="blue" onClick={onFinish} disabled={busy} data-testid="cbp-finish">
          {busy ? "Scoring…" : "Finish case →"}
        </Button>
      </div>
    </Shell>
  );
}

// ---- feedback: gate result + summary; route back to hub ----
function FeedbackStage() {
  const payload = useRuntimeStore((st) => st.payload);
  const gate = useRuntimeStore((st) => st.gateState);
  const goto = useRuntimeStore((st) => st.goto);
  const startCbp = useRuntimeStore((st) => st.startCbp);

  const summary = payload?.content_json.case_based_preview?.feedback_summary;
  const cbpGate = gate?.cbp;
  const passed = cbpGate?.passed ?? false;

  // Fire "complete" once on mount when the CBP is passed.
  const firedRef = useRef(false);
  useEffect(() => {
    if (passed && !firedRef.current) {
      firedRef.current = true;
      play("complete");
    }
  }, [passed]);

  return (
    <Shell testid="cbp-feedback">
      <div className={s.lbHead}>
        {passed ? <Pill tone="good">✓ Passed</Pill> : <Pill tone="warn">Needs retry</Pill>}
        <span className={s.lbCounter}>
          {cbpGate?.checkpoints_correct ?? 0}/{cbpGate?.checkpoints_total ?? 3} checkpoints correct
        </span>
      </div>

      <Title size="hero">
        {passed ? "Case cleared." : "Almost — one more pass."}
      </Title>
      <Lead>
        {passed
          ? "You used the lesson and made the right calls. This section is done."
          : "You need at least 2 of 3 checkpoints. Retake the ones you missed — same concept, fresh question."}
      </Lead>

      {summary && (
        <FeatureCard className={s.summaryCard}>
          {summary.student_understood && (
            <SummaryRow label="What you understood" value={summary.student_understood} />
          )}
          {summary.mistake_appeared && (
            <SummaryRow label="Where mistakes appeared" value={summary.mistake_appeared} />
          )}
          {summary.what_to_review && (
            <SummaryRow label="What to review" value={summary.what_to_review} />
          )}
        </FeatureCard>
      )}

      <div className={s.actions}>
        {passed ? (
          <Button variant="blue" onClick={() => goto("hub")} data-testid="cbp-back-hub">
            Back to Hub →
          </Button>
        ) : (
          <>
            <Button variant="outline" onClick={() => goto("hub")}>
              Back to Hub
            </Button>
            <Button variant="blue" onClick={startCbp} data-testid="cbp-retake">
              Retake case
            </Button>
          </>
        )}
      </div>
    </Shell>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={s.summaryRow}>
      <p className={s.summaryLabel}>{label}</p>
      <p className={s.summaryValue}>{value}</p>
    </div>
  );
}

// ---- shared bits ----
function BackToHub({ onClick }: { onClick: () => void }) {
  return (
    <button
      className={s.back}
      onClick={() => { play("tick"); onClick(); }}
      type="button"
    >
      ← Back to Hub
    </button>
  );
}

function CheckpointProgress({ current, total }: { current: number; total: number }) {
  return (
    <div className={s.progress} aria-label={`Checkpoint ${current + 1} of ${total}`}>
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`${s.dot} ${i < current ? s.dotDone : i === current ? s.dotActive : ""}`}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
