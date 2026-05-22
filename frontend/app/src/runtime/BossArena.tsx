import { useEffect, useState } from "react";
import type { KeyboardEvent } from "react";
import { useRuntimeStore, COMBO_BONUS_THRESHOLD } from "./store";
import type { GameProps } from "./GameHost";
import { DarkSection, Eyebrow, Title, Lead, Button, Pill } from "../shared/ui/primitives";
import s from "./BossArena.module.css";

// ---------------------------------------------------------------------------
// Boss Arena — the F4 mastery peak, DYNAMIC (Plan 5). The SERVER owns
// hp/trials/difficulty and grades every answer:
//   intro  → "Enter the arena" → POST /boss/start (+ first /generate-question)
//   loading → generation skeleton while a question is fetched
//   fighting → HP bar + trials + difficulty + combo, Why→How→What answer inputs
//   won    → stars + XP from the final verdict
//   lost   → "Face it again" → POST /boss/start force_fresh
//
// The client NEVER holds an answer, computes HP, or self-grades — it mirrors
// the server's absolute hp/trials/difficulty and renders the verdict it's
// handed. The Why → How → What scaffold is the structured prompt: when the
// question carries why/how/what we render three labelled inputs and concatenate
// them as "Why: …\nHow: …\nWhat: …" on submit; otherwise a single textarea on
// question_text. A hint is LOCAL-only (no answer reveal) — it just notes its
// cost. All motion is transform/opacity and honors prefers-reduced-motion.
// ---------------------------------------------------------------------------

const WHW_STEPS = [
  { key: "why", label: "Why", hint: "Name the concept in play." },
  { key: "how", label: "How", hint: "Show the method you’d use." },
  { key: "what", label: "What", hint: "State the result." },
] as const;

export default function BossArena({ onComplete }: GameProps) {
  const payload = useRuntimeStore((st) => st.payload);
  const boss = useRuntimeStore((st) => st.boss);
  const startBoss = useRuntimeStore((st) => st.startBoss);
  const submitBossAnswer = useRuntimeStore((st) => st.submitBossAnswer);
  const loadNextQuestion = useRuntimeStore((st) => st.loadNextQuestion);
  const requestHint = useRuntimeStore((st) => st.requestHint);
  const retryBoss = useRuntimeStore((st) => st.retryBoss);

  const meta = payload?.content_json.boss_meta;
  const bossName = meta?.name ?? "The Boss";

  // Structured answer fields (Why/How/What). For a non-structured question we
  // only use `what` as the single free-text answer.
  const [why, setWhy] = useState("");
  const [how, setHow] = useState("");
  const [what, setWhat] = useState("");

  const q = boss.currentQuestion;
  const structured = Boolean(q && (q.why || q.how || q.what || q.scenario));

  // Reset inputs whenever a new question arrives.
  const qid = q?.question_id ?? null;
  useEffect(() => {
    setWhy("");
    setHow("");
    setWhat("");
  }, [qid]);

  // ---- intro ----
  if (boss.status === "intro") {
    // Once /start has fired we may be mid-load of the first question — show the
    // generation skeleton so the student isn't staring at a dead "Enter" button.
    const opening = boss.submitting || boss.loadingQuestion;
    if (opening && !boss.submitError && !boss.generateError) {
      return <GeneratingFrame bossName={bossName} />;
    }
    return (
      <DarkSection className={s.arena} glow={false}>
        <div className={s.arenaGlow} aria-hidden="true" />
        <div data-testid="boss-intro">
          <Eyebrow>Final Boss</Eyebrow>
          <Title size="hero">{bossName} awaits.</Title>
          <Lead>
            {meta?.intro ??
              "This is the peak. Defend every answer with your reasoning — vague guesses do no damage."}
          </Lead>
          <WhyHowWhatScaffold />
          {boss.submitError && (
            <p className={s.error} role="alert" data-testid="boss-start-error">
              {boss.submitError}
            </p>
          )}
          {boss.generateError && !boss.submitError && (
            <p className={s.error} role="alert" data-testid="boss-start-error">
              {boss.generateError}
            </p>
          )}
          <div className={s.actions}>
            <Button
              variant="blue"
              onClick={() => void startBoss()}
              disabled={opening}
              data-testid="boss-begin"
            >
              {opening ? "Opening…" : "Enter the arena →"}
            </Button>
          </div>
        </div>
      </DarkSection>
    );
  }

  // ---- won ----
  if (boss.status === "won") {
    const stars = boss.lastResult?.stars;
    const xp = boss.lastResult?.outcome_xp;
    return (
      <DarkSection className={`${s.arena} ${s.arenaWin}`} glow={false}>
        <div className={`${s.arenaGlow} ${s.arenaGlowWin}`} aria-hidden="true" />
        <div data-testid="boss-won">
          <Eyebrow>Victory</Eyebrow>
          <Title size="hero">{bossName} is down.</Title>
          <Lead>
            You drained the bar to zero with reasoning that held up. That’s
            mastery.
          </Lead>
          {typeof stars === "number" && <Stars count={stars} />}
          {typeof xp === "number" && xp > 0 && (
            <div>
              <span className={s.xpPill} data-testid="boss-xp">
                +{xp} XP
              </span>
            </div>
          )}
          <div className={s.actions}>
            <Button variant="blue" onClick={onComplete} data-testid="boss-finish">
              Claim the arc →
            </Button>
          </div>
        </div>
      </DarkSection>
    );
  }

  // ---- lost ----
  if (boss.status === "lost") {
    const restarting = boss.submitting || boss.loadingQuestion;
    return (
      <DarkSection className={s.arena} glow={false}>
        <div className={s.arenaGlow} aria-hidden="true" />
        <div data-testid="boss-lost">
          <Eyebrow>Defeated</Eyebrow>
          <Title size="hero">{bossName} stands.</Title>
          <Lead>
            Trials ran out before the bar did. Regroup and come back sharper —
            a fresh attempt resets your trials.
          </Lead>
          {boss.lastResult?.feedback && (
            <p className={s.bossLine}>{boss.lastResult.feedback}</p>
          )}
          {boss.submitError && (
            <p className={s.error} role="alert">
              {boss.submitError}
            </p>
          )}
          <div className={s.actions}>
            <Button
              variant="blue"
              onClick={() => void retryBoss()}
              disabled={restarting}
              data-testid="boss-retry"
            >
              {restarting ? "Resetting…" : "Face it again →"}
            </Button>
          </div>
        </div>
      </DarkSection>
    );
  }

  // ---- fighting ----
  const result = boss.lastResult;
  const justHit = result?.is_correct === true;
  const hpPct =
    boss.maxHp > 0 ? Math.max(0, Math.min(100, (boss.hp / boss.maxHp) * 100)) : 0;
  const comboHot = boss.combo >= COMBO_BONUS_THRESHOLD;

  const onSubmit = () => {
    if (boss.submitting || boss.loadingQuestion) return;
    const trimmedWhat = what.trim();
    if (!trimmedWhat) return; // gate on the What field
    const answer = structured
      ? `Why: ${why.trim()}\nHow: ${how.trim()}\nWhat: ${trimmedWhat}`
      : trimmedWhat;
    void submitBossAnswer(answer);
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") onSubmit();
  };

  return (
    <DarkSection className={s.arena} glow={false}>
      <div className={s.arenaGlow} aria-hidden="true" />
      <div data-testid="boss-fighting">
        <div className={s.bossHead}>
          <span className={s.bossName}>{bossName}</span>
          <span className={s.hpLabel} data-testid="boss-hp">
            {boss.hp} / {boss.maxHp} HP
          </span>
        </div>

        {/* HP bar — driven by the absolute server hp/maxHp; flashes on a hit. */}
        <div className={s.hpTrack} aria-hidden="true">
          <div
            className={`${s.hpFill} ${justHit ? s.hpFillHit : ""}`}
            style={{ width: `${hpPct}%` }}
          />
        </div>

        {/* status rail — trials · difficulty · combo */}
        <div className={s.statusRail}>
          <span className={s.trialsPill} data-testid="boss-trials">
            {boss.trialsLeft} {boss.trialsLeft === 1 ? "trial" : "trials"} left
          </span>
          <span className={s.tierChip} data-testid="boss-difficulty">
            {boss.currentDifficulty}
          </span>
          <span
            className={`${s.combo} ${comboHot ? s.comboHot : ""}`}
            data-testid="boss-combo"
          >
            Combo ×{boss.combo}
            {comboHot && <span className={s.comboBonus}>+20%</span>}
          </span>
        </div>

        {boss.loadingQuestion ? (
          <SkeletonBody />
        ) : boss.generateError ? (
          <GenerateErrorBlock
            message={boss.generateError}
            failures={boss.consecutiveGenerateFailures}
            onRetry={() => void loadNextQuestion()}
          />
        ) : q ? (
          <>
            <p className={s.qLabel}>Question {boss.questionIndex + 1}</p>

            {structured ? (
              <>
                {q.scenario && <p className={s.scenario}>{q.scenario}</p>}
                {!q.scenario && q.question_text && (
                  <Title size="section" className={s.question}>
                    {q.question_text}
                  </Title>
                )}
                <div className={s.whwInputs} onKeyDown={onKeyDown}>
                  {WHW_STEPS.map((step) => {
                    const prompt =
                      step.key === "why" ? q.why : step.key === "how" ? q.how : q.what;
                    const value =
                      step.key === "why" ? why : step.key === "how" ? how : what;
                    const setValue =
                      step.key === "why" ? setWhy : step.key === "how" ? setHow : setWhat;
                    return (
                      <div className={s.whwField} key={step.key}>
                        <label
                          className={s.whwFieldLabel}
                          htmlFor={`boss-${step.key}`}
                        >
                          {step.label}
                        </label>
                        <p className={s.whwFieldPrompt}>{prompt || step.hint}</p>
                        <textarea
                          id={`boss-${step.key}`}
                          className={s.answerInput}
                          value={value}
                          rows={2}
                          disabled={boss.submitting}
                          placeholder={step.hint}
                          onChange={(e) => setValue(e.target.value)}
                          data-testid={`boss-input-${step.key}`}
                        />
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <>
                <Title size="section" className={s.question}>
                  {q.question_text || "Defend your reasoning."}
                </Title>
                <div className={s.answerWrap} onKeyDown={onKeyDown}>
                  <label className={s.answerLabel} htmlFor="boss-what">
                    Your answer
                  </label>
                  <textarea
                    id="boss-what"
                    className={s.answerInput}
                    value={what}
                    placeholder="Explain your reasoning, then your answer…"
                    disabled={boss.submitting}
                    rows={3}
                    onChange={(e) => setWhat(e.target.value)}
                    data-testid="boss-input-what"
                  />
                </div>
              </>
            )}

            {/* hint affordance — local cost only, reveals nothing answer-bearing */}
            <div className={s.hintRow}>
              <button
                type="button"
                className={s.hintBtn}
                onClick={requestHint}
                data-testid="boss-hint"
              >
                Ask for a hint
              </button>
              <span className={s.hintNote}>
                {boss.hintsUsed > 0
                  ? `Hints used: ${boss.hintsUsed} — each one trims the damage you deal.`
                  : "A hint trims the damage you deal — try without one first."}
              </span>
            </div>

            {/* turn-result card — verdict, feedback, misconceptions, coverage */}
            {result && (
              <div
                className={`${s.turn} ${result.is_correct ? s.turnHit : s.turnMiss}`}
                role="status"
                data-testid="boss-turn-result"
              >
                <div className={s.turnHead}>
                  {result.is_correct ? (
                    <Pill tone="good">Hit · −{result.damage} HP</Pill>
                  ) : (
                    <Pill tone="warn">Wrong · no damage</Pill>
                  )}
                </div>
                {result.feedback && <p className={s.bossLine}>{result.feedback}</p>}
                {result.misconception_tags && result.misconception_tags.length > 0 && (
                  <div className={s.miscRow} data-testid="boss-misconceptions">
                    {result.misconception_tags.map((tag, i) => (
                      <span className={s.miscChip} key={`${tag}-${i}`}>
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                {result.coverage && (
                  <div className={s.coverage} data-testid="boss-coverage">
                    {WHW_STEPS.map((step) => {
                      const v = result.coverage?.[step.key] ?? 0;
                      const pct = Math.round(Math.max(0, Math.min(1, v)) * 100);
                      return (
                        <div className={s.covRow} key={step.key}>
                          <span className={s.covLabel}>{step.label}</span>
                          <div className={s.covTrack} aria-hidden="true">
                            <div className={s.covFill} style={{ width: `${pct}%` }} />
                          </div>
                          <span className={s.covPct}>{pct}%</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {boss.submitError && (
              <p className={s.error} role="alert">
                {boss.submitError}
              </p>
            )}

            <div className={s.actions}>
              <Button
                variant="blue"
                onClick={onSubmit}
                disabled={boss.submitting || what.trim() === ""}
                data-testid="boss-attack"
              >
                {boss.submitting ? "Striking…" : "Attack →"}
              </Button>
            </div>
          </>
        ) : null}
      </div>
    </DarkSection>
  );
}

// Generation skeleton frame (used while the first question loads from intro).
function GeneratingFrame({ bossName }: { bossName: string }) {
  return (
    <DarkSection className={s.arena} glow={false}>
      <div className={s.arenaGlow} aria-hidden="true" />
      <div>
        <Eyebrow>Final Boss</Eyebrow>
        <Title size="hero">{bossName} sizes you up…</Title>
        <SkeletonBody />
      </div>
    </DarkSection>
  );
}

// The shimmer skeleton body — also reused inline while chaining questions.
function SkeletonBody() {
  return (
    <div className={s.skeleton} data-testid="boss-loading-question" aria-busy="true">
      <p className={s.skelLabel}>Forging the next challenge…</p>
      <div className={s.skelLine} />
      <div className={s.skelLine} />
      <div className={s.skelLine} />
      <div className={`${s.skelLine} ${s.skelTall}`} />
    </div>
  );
}

// 502 / generation-failure block. Two failures in a row → recommend a refresh
// (the generator is wedged); otherwise offer an in-place retry.
function GenerateErrorBlock({
  message,
  failures,
  onRetry,
}: {
  message: string;
  failures: number;
  onRetry: () => void;
}) {
  const refresh = failures >= 2;
  return (
    <div className={s.genError} role="alert" data-testid="boss-generate-error">
      <p className={s.genErrorTitle}>
        {refresh ? "The boss is stuck thinking." : "That question didn’t land."}
      </p>
      <p className={s.genErrorBody}>{message}</p>
      <div className={s.actions} style={{ marginTop: 0 }}>
        {refresh ? (
          <Button
            variant="blue"
            onClick={() => window.location.reload()}
            data-testid="boss-generate-refresh"
          >
            Refresh the page →
          </Button>
        ) : (
          <Button variant="blue" onClick={onRetry} data-testid="boss-generate-retry">
            Try again →
          </Button>
        )}
      </div>
    </div>
  );
}

// Why → How → What — the 3-up reasoning scaffold shown on the intro screen.
function WhyHowWhatScaffold() {
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
