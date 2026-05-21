import { useEffect, useState } from "react";
import { useRuntimeStore } from "./store";
import type { GameProps } from "./GameHost";
import type { BossQuestion } from "../shared/types";
import { DarkSection, Eyebrow, Title, Lead, Button, Pill } from "../shared/ui/primitives";
import s from "./BossArena.module.css";

// ---------------------------------------------------------------------------
// Boss Arena — the F4 mastery peak. A high-stakes dark arena: the student
// answers boss_questions, each landed hit drains the boss HP bar by the
// SERVER-returned `damage_dealt`. Correctness/damage are ALWAYS the server's
// (phase=final-boss resolves the expected answer by question_id — the client
// holds no answer and NEVER self-grades). HP hitting 0 is the win.
//
// The Why → How → What scaffold is a 3-up reasoning prompt: it frames the
// quality of answer the boss demands (name the concept → show the method →
// state the result), mirroring the workflow-step pattern. It's a coaching
// frame, not a grader.
// ---------------------------------------------------------------------------

const WHW_STEPS = [
  { label: "Why", hint: "Name the concept in play." },
  { label: "How", hint: "Show the method you’d use." },
  { label: "What", hint: "State the result." },
] as const;

export default function BossArena({ onComplete }: GameProps) {
  const payload = useRuntimeStore((st) => st.payload);
  const boss = useRuntimeStore((st) => st.boss);
  const startBoss = useRuntimeStore((st) => st.startBoss);
  const bossAnswer = useRuntimeStore((st) => st.bossAnswer);
  const advanceBossQuestion = useRuntimeStore((st) => st.advanceBossQuestion);
  const retryBoss = useRuntimeStore((st) => st.retryBoss);

  const questions = (payload?.content_json.boss_questions ?? []) as BossQuestion[];
  const meta = payload?.content_json.boss_meta;
  const bossName = meta?.name ?? "The Boss";
  // PR-2: question text now comes from the Plan-5 server response. Static
  // boss_questions[] is read only by the empty-state guard below; PR-3 drops
  // that branch in favor of Plan-5's 502 / no-question-loaded UI states.
  const questionText = boss.currentQuestion?.question_text ?? "Defend your reasoning.";

  const [answer, setAnswer] = useState("");

  // Reset the input whenever a new turn begins (a new question is shown).
  const turnHadResult = boss.lastResult !== null;
  useEffect(() => {
    setAnswer("");
  }, [boss.questionIndex, turnHadResult]);

  if (questions.length === 0) {
    return (
      <DarkSection className={s.arena} glow={false}>
        <div className={s.arenaGlow} aria-hidden="true" />
        <Eyebrow>Boss Arena</Eyebrow>
        <Title size="section">
          No boss to face.
        </Title>
        <Lead>This homework has no boss questions. Wrapping the arc.</Lead>
        <div className={s.actions}>
          <Button variant="blue" onClick={onComplete}>
            Finish arc →
          </Button>
        </div>
      </DarkSection>
    );
  }

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
          <Button variant="blue" onClick={startBoss} data-testid="boss-begin">
            Enter the arena →
          </Button>
        </div>
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
          You drained the bar to zero with reasoning that held up. That’s
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
          <Button variant="blue" onClick={retryBoss} data-testid="boss-retry">
            Face it again →
          </Button>
        </div>
      </DarkSection>
    );
  }

  // ---- fighting ----
  const result = boss.lastResult;
  const justHit = result?.is_correct === true;
  const hpPct = boss.maxHp > 0 ? Math.max(0, Math.min(100, (boss.hp / boss.maxHp) * 100)) : 0;

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
        <span className={s.hpLabel} data-testid="boss-hp">
          {boss.hp} / {boss.maxHp} HP
        </span>
      </div>

      {/* HP bar — drains with damage; flashes on a hit. */}
      <div className={s.hpTrack} aria-hidden="true">
        <div
          className={`${s.hpFill} ${justHit ? s.hpFillHit : ""}`}
          style={{ width: `${hpPct}%` }}
        />
      </div>

      <WhyHowWhat />

      <p className={s.qLabel}>Question {boss.questionIndex + 1}</p>
      <Title size="section" className={s.question}>
        {questionText}
      </Title>

      {/* turn feedback: boss line + damage. Plan-5 returns a single
          `feedback` string (no separate hint field); PR-3 redesigns this
          surface to show "Wrong, moving on" + a "Next question →" CTA. */}
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
              <Pill tone="warn">Blocked · no damage</Pill>
            )}
          </div>
          {result.feedback && <p className={s.bossLine}>{result.feedback}</p>}
        </div>
      )}

      {boss.submitError && (
        <p className={s.error} role="alert">
          {boss.submitError}
        </p>
      )}

      {/* After a landed hit (boss still up), advance to the next question. */}
      {justHit ? (
        <div className={s.actions}>
          <Button variant="blue" onClick={advanceBossQuestion} data-testid="boss-next">
            Press the attack →
          </Button>
        </div>
      ) : (
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
      )}
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
