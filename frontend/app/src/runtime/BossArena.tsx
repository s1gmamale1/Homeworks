import { useEffect, useState } from "react";
import { useRuntimeStore } from "./store";
import type { GameProps } from "./GameHost";
import { DarkSection, Eyebrow, Title, Lead, Button, Pill } from "../shared/ui/primitives";
import s from "./BossArena.module.css";

// ---------------------------------------------------------------------------
// Boss Arena — F4 mastery peak. Plan-5 dynamic boss: each turn is an
// adaptive question generated against the student's running context, and the
// server is authoritative for HP / damage / trials / boss_status. The client
// never self-grades; correctness comes from /boss/submit-answer.
//
// Per-turn flow:
//   1. /boss/start opens the session (resume or fresh based on staleness)
//   2. /boss/generate-question fetches the next adaptive question
//   3. Student types an answer + submits
//   4. /boss/submit-answer returns is_correct + absolute hp + new trials_left
//      + boss_status. If still "active", the store auto-chains step 2 for
//      the NEXT question. Every submission consumes one trial; there is no
//      "retry the same question" path (Plan-5 contract).
//
// 502 on /generate-question (anti-repetition / skill-floor / language-drift
// retry exhaustion) is surfaced as a user-triggered "Try again" affordance
// per Boss Arena spec §10. After 2 consecutive failures we escalate to a
// "Refresh the page" CTA (Decision 3) — don't keep hammering a degraded LLM.
//
// The Why → How → What scaffold is a coaching label (Option B scope), not
// a grader.
// ---------------------------------------------------------------------------

const WHW_STEPS = [
  { label: "Why", hint: "Name the concept in play." },
  { label: "How", hint: "Show the method you'd use." },
  { label: "What", hint: "State the result." },
] as const;

export default function BossArena({ onComplete }: GameProps) {
  const boss = useRuntimeStore((st) => st.boss);
  const payload = useRuntimeStore((st) => st.payload);
  const startBoss = useRuntimeStore((st) => st.startBoss);
  const loadNextQuestion = useRuntimeStore((st) => st.loadNextQuestion);
  const bossAnswer = useRuntimeStore((st) => st.bossAnswer);
  const advanceBossQuestion = useRuntimeStore((st) => st.advanceBossQuestion);
  const retryBoss = useRuntimeStore((st) => st.retryBoss);

  const meta = payload?.content_json.boss_meta;
  const bossName = meta?.name ?? "The Boss";

  const [answer, setAnswer] = useState("");

  // Reset the input whenever a new question is shown (questionIndex bumps on
  // each successful /generate-question landing — store guarantees question_id
  // is unique per turn).
  useEffect(() => {
    setAnswer("");
  }, [boss.currentQuestion?.question_id]);

  // ---- intro ----
  if (boss.status === "intro") {
    return (
      <DarkSection className={s.arena} glow={false} data-testid="boss-intro">
        <div className={s.arenaGlow} aria-hidden="true" />
        <Eyebrow>Final Boss</Eyebrow>
        <Title size="hero">
          {bossName} awaits.
        </Title>
        <Lead>
          {meta?.intro ??
            "This is the peak. Defend every answer with your reasoning — vague guesses do no damage."}
        </Lead>
        <WhyHowWhat />
        <div className={s.actions}>
          <Button
            variant="blue"
            onClick={() => void startBoss()}
            disabled={boss.submitting}
            data-testid="boss-begin"
          >
            {boss.submitting ? "Opening the arena…" : "Enter the arena →"}
          </Button>
        </div>
        {boss.submitError && (
          <p className={s.error} role="alert">
            {boss.submitError}
          </p>
        )}
      </DarkSection>
    );
  }

  // ---- won ----
  if (boss.status === "won") {
    const stars = boss.lastResult?.stars;
    return (
      <DarkSection className={`${s.arena} ${s.arenaWin}`} glow={false} data-testid="boss-won">
        <div className={`${s.arenaGlow} ${s.arenaGlowWin}`} aria-hidden="true" />
        <Eyebrow>Victory</Eyebrow>
        <Title size="hero">
          {bossName} is down.
        </Title>
        <Lead>
          You drained the bar to zero with reasoning that held up. That's
          mastery.
        </Lead>
        {typeof stars === "number" && <Stars count={stars} />}
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete} data-testid="boss-finish">
            Claim the arc →
          </Button>
        </div>
      </DarkSection>
    );
  }

  // ---- lost ----
  if (boss.status === "lost") {
    return (
      <DarkSection className={s.arena} glow={false} data-testid="boss-lost">
        <div className={s.arenaGlow} aria-hidden="true" />
        <Eyebrow>Defeated</Eyebrow>
        <Title size="hero">
          {bossName} stands.
        </Title>
        <Lead>Regroup and come back sharper — the bar resets to full.</Lead>
        <div className={s.actions}>
          <Button
            variant="blue"
            onClick={() => void retryBoss()}
            disabled={boss.submitting}
            data-testid="boss-retry"
          >
            {boss.submitting ? "Resetting…" : "Face it again →"}
          </Button>
        </div>
      </DarkSection>
    );
  }

  // ---- fighting ----
  const result = boss.lastResult;
  const justHit = result?.is_correct === true;
  const hpPct = boss.maxHp > 0 ? Math.max(0, Math.min(100, (boss.hp / boss.maxHp) * 100)) : 0;

  // Decision 3 escalation: after 2 consecutive /generate-question 502s we
  // surface a hard "refresh the page" CTA instead of another retry button.
  const refreshNeeded = boss.consecutiveGenerateFailures >= 2;
  const hasGenerateError = boss.generateError !== null;

  const onSubmit = () => {
    const trimmed = answer.trim();
    if (!trimmed || boss.submitting) return;
    void bossAnswer(trimmed);
  };

  return (
    <DarkSection className={s.arena} glow={false} data-testid="boss-fighting">
      <div className={s.arenaGlow} aria-hidden="true" />

      <div className={s.bossHead}>
        <span className={s.bossName}>{bossName}</span>
        <span className={s.headMeta}>
          <span
            className={s.trialsPill}
            key={`trials-${boss.trialsLeft}`}
            data-testid="boss-trials"
          >
            Trials: {boss.trialsLeft} left
          </span>
          <span className={s.hpLabel} data-testid="boss-hp">
            {boss.hp} / {boss.maxHp} HP
          </span>
        </span>
      </div>

      {/* HP bar — drains with damage; flashes on a hit. HP is server-absolute,
          not a client-side subtraction. */}
      <div className={s.hpTrack} aria-hidden="true">
        <div
          className={`${s.hpFill} ${justHit ? s.hpFillHit : ""}`}
          style={{ width: `${hpPct}%` }}
        />
      </div>

      <WhyHowWhat />

      {/* Question slot — three sub-states:
          1. currentQuestion → render it (the steady-state)
          2. loadingQuestion → calm skeleton (mid-generate)
          3. neither → covered by the generateError block below */}
      {boss.currentQuestion ? (
        <>
          <p className={s.qLabel}>Question {boss.questionIndex + 1}</p>
          <Title size="section" className={s.question}>
            {boss.currentQuestion.question_text}
          </Title>
        </>
      ) : boss.loadingQuestion ? (
        <div className={s.skeleton} data-testid="boss-loading-question">
          <p className={s.qLabel}>Question</p>
          <div className={s.skeletonBar} aria-hidden="true" />
          <div className={s.skeletonBar} aria-hidden="true" />
          <p className={s.lead}>Loading the next question…</p>
        </div>
      ) : null}

      {/* Turn feedback — sits beneath the question until the student
          dismisses via "Next question →". On a wrong answer, the
          misconception_tags chip-row surfaces what tripped them. */}
      {result && (
        <div
          className={`${s.turn} ${result.is_correct ? s.turnHit : s.turnMiss}`}
          role="status"
          data-testid="boss-turn-result"
        >
          <div className={s.turnHead}>
            {result.is_correct ? (
              <Pill tone="good">
                Hit · −{result.damage} HP
              </Pill>
            ) : (
              <Pill tone="warn">
                Wrong · moving on
              </Pill>
            )}
          </div>
          {result.feedback && <p className={s.bossLine}>{result.feedback}</p>}
          {!result.is_correct && result.misconception_tags.length > 0 && (
            <div className={s.tags} data-testid="boss-misconception-tags">
              {result.misconception_tags.map((tag) => (
                <span key={tag} className={s.tag}>
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 502 retry block — Decision 3.
          First failure: "Try again" button re-invokes /generate-question.
          Two failures in a row: hard refresh CTA. Telemetry on the
          consecutiveGenerateFailures counter is the ops signal. */}
      {hasGenerateError && (
        <div className={s.generateError} role="alert" data-testid="boss-generate-error">
          {refreshNeeded ? (
            <>
              <p>Boss generation is unavailable right now.</p>
              <Button
                variant="blue"
                onClick={() => window.location.reload()}
                data-testid="boss-refresh"
              >
                Refresh the page →
              </Button>
            </>
          ) : (
            <>
              <p>{boss.generateError}</p>
              <Button
                variant="blue"
                onClick={() => void loadNextQuestion()}
                disabled={boss.loadingQuestion}
                data-testid="boss-try-again"
              >
                {boss.loadingQuestion ? "Trying…" : "Try again →"}
              </Button>
            </>
          )}
        </div>
      )}

      {boss.submitError && (
        <p className={s.error} role="alert">
          {boss.submitError}
        </p>
      )}

      {/* CTA row.
          - With a result on screen AND no generate-error: "Next question →"
            dismisses the turn summary. The next question is already
            auto-loaded by the store, so the dismissal just reveals it.
          - Result + generateError: hide this CTA; the retry block above
            owns the path forward.
          - No result + currentQuestion: answer textarea + Attack button.
          - Otherwise (loading / generateError without prior result): no CTA. */}
      {result && !hasGenerateError ? (
        <div className={s.actions}>
          <Button
            variant="blue"
            onClick={advanceBossQuestion}
            disabled={boss.loadingQuestion}
            data-testid="boss-next"
          >
            Next question →
          </Button>
        </div>
      ) : !result && boss.currentQuestion ? (
        <div className={s.answerWrap}>
          <label className={s.answerLabel} htmlFor="boss-answer">
            Your answer
          </label>
          <textarea
            id="boss-answer"
            className={s.answerInput}
            value={answer}
            placeholder="Explain your reasoning, then your answer…"
            disabled={boss.submitting}
            rows={3}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") onSubmit();
            }}
            data-testid="boss-answer-input"
          />
          <div className={s.actions}>
            <Button
              variant="blue"
              onClick={onSubmit}
              disabled={boss.submitting || answer.trim() === ""}
              data-testid="boss-attack"
            >
              {boss.submitting ? "Striking…" : "Attack →"}
            </Button>
          </div>
        </div>
      ) : null}
    </DarkSection>
  );
}

// Why → How → What — the 3-up reasoning scaffold (workflow-step style).
function WhyHowWhat() {
  return (
    <ol className={s.whw} aria-label="What the boss demands">
      {WHW_STEPS.map((step, i) => (
        <li key={step.label} className={s.whwStep}>
          <span className={s.whwIndex}>{i + 1}</span>
          <span className={s.whwBody}>
            <span className={s.whwLabel}>{step.label}</span>
            <span className={s.whwHint}>{step.hint}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

function Stars({ count }: { count: number }) {
  const max = 3;
  return (
    <div className={s.stars} aria-label={`${count} of ${max} stars`}>
      {Array.from({ length: max }).map((_, i) => (
        <span key={i} className={`${s.star} ${i < count ? s.starOn : ""}`} aria-hidden="true">
          ★
        </span>
      ))}
    </div>
  );
}
