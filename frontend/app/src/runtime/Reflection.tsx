import type { ReactNode } from "react";
import { useEffect, useRef } from "react";
import { useRuntimeStore } from "./store";
import type { ReflectionDivision } from "../shared/types";
import { Pill, Eyebrow, Title, Lead, Button } from "../shared/ui/primitives";
import ReflectionBackdrop from "./ReflectionBackdrop";
import { play } from "./sfx";
import s from "./Reflection.module.css";

// ---------------------------------------------------------------------------
// Reflection / Debrief — the F5 close. The aftermath after the Boss and the
// final beat of the v2 journey (Hub → CBP → Flashcards+Memory → Gate →
// Practice Arc → Boss → HERE). Full Hub-DNA redesign: a full-bleed living
// backdrop (aurora + candy blobs + pointer color-trail, via ReflectionBackdrop)
// behind a centered Apple-glass content stage, in a calm closing blue→violet
// palette.
//
// Two sub-stages:
//   prompt   — 1–2 free-text reflection prompts ("What was hardest? Why?").
//   debrief  — on submit, POST /api/runtime/reflection/finalize and render the
//              rich, SERVER-AUTHORITATIVE debrief: verdict + verdict_label,
//              overall score ring + band, per-division breakdown, strong/weak
//              points, mistake repairs, next steps, AI narrative + encouragement.
//
// Pass | Needs Retry is now SERVER-AUTHORITATIVE — it comes from the finalize
// response (`verdict`), NOT derived client-side. The store keeps only a
// provisional client guess (`passed`) for the prompt-stage copy + loading state;
// once the debrief lands it overwrites `passed` from the response verdict.
// Flow-v2 forbid #20: never show "Not Completed" alone — always Passed or
// Needs Retry. On Needs Retry the retake CTA calls the redo flow (same concepts,
// fresh questions).
// ---------------------------------------------------------------------------
export function Reflection() {
  const stage = useRuntimeStore((st) => st.reflection.stage);
  return stage === "prompt" ? <PromptStage /> : <DebriefStage />;
}

// Full-bleed shell: living backdrop at z0, centered content stage at z1. Mounted
// in both stages so the backdrop persists across the prompt → debrief transition.
function Shell({ children, testid }: { children: ReactNode; testid: string }) {
  return (
    <main className={s.shell} data-theme="light" data-testid={testid}>
      <ReflectionBackdrop />
      <div className={s.stage}>{children}</div>
    </main>
  );
}

// ---- prompt: short free-text reflection before the debrief ----
function PromptStage() {
  const prompts = useRuntimeStore((st) => st.reflection.prompts);
  const answers = useRuntimeStore((st) => st.reflection.answers);
  const submitting = useRuntimeStore((st) => st.reflection.submitting);
  const submitError = useRuntimeStore((st) => st.reflection.submitError);
  const passed = useRuntimeStore((st) => st.reflection.passed);
  const setAnswer = useRuntimeStore((st) => st.setReflectionAnswer);
  const submit = useRuntimeStore((st) => st.submitReflection);

  // At least one prompt must have a non-empty answer to submit a reflection.
  const hasAnswer = answers.some((a) => a.trim() !== "");

  return (
    <Shell testid="reflection-prompt">
      <Eyebrow cyan className={s.eyebrow}>
        Reflection
      </Eyebrow>
      <Title size="hero">{passed ? "You made it. Look back." : "One honest look back."}</Title>
      <Lead>
        Before your debrief — a moment to think. There are no wrong answers
        here; this is just you and the work.
      </Lead>

      <div className={s.prompts}>
        {prompts.map((p, i) => (
          <div key={i} className={`${s.panel} ${s.promptCard}`}>
            <label className={s.promptLabel} htmlFor={`reflection-${i}`}>
              {p}
            </label>
            <textarea
              id={`reflection-${i}`}
              className={s.promptInput}
              value={answers[i] ?? ""}
              placeholder="Write a sentence or two…"
              rows={3}
              disabled={submitting}
              onChange={(e) => setAnswer(i, e.target.value)}
              data-testid={`reflection-input-${i}`}
            />
          </div>
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
          onClick={() => void submit()}
          disabled={!hasAnswer || submitting}
          data-testid="reflection-submit"
        >
          {submitting ? "Reading your reflection…" : "Get my debrief →"}
        </Button>
      </div>
    </Shell>
  );
}

// ---- debrief: SERVER-AUTHORITATIVE rich coaching + Passed | Needs Retry ----
function DebriefStage() {
  const debrief = useRuntimeStore((st) => st.reflection.debrief);
  const passed = useRuntimeStore((st) => st.reflection.passed);
  const retaking = useRuntimeStore((st) => st.reflection.retaking);
  const retakeError = useRuntimeStore((st) => st.reflection.retakeError);
  const goto = useRuntimeStore((st) => st.goto);
  const retake = useRuntimeStore((st) => st.retakeFromReflection);

  // The verdict is the server's once the debrief lands; fall back to the
  // provisional `passed` only for the brief moment a debrief is null.
  const verdictPassed = debrief ? debrief.verdict === "passed" : passed;

  // Fire the verdict cue once when the debrief first lands.
  const verdictFiredRef = useRef(false);
  useEffect(() => {
    if (!debrief || verdictFiredRef.current) return;
    verdictFiredRef.current = true;
    play(verdictPassed ? "complete" : "boss-lose");
  }, [debrief, verdictPassed]);
  const overallPct =
    typeof debrief?.overall_pct === "number" ? Math.round(debrief.overall_pct) : null;
  const bandName = debrief?.band?.name?.trim() || "";
  const verdictLabel = debrief?.verdict_label?.trim() || "";

  const headline = verdictPassed ? "Passed." : "Needs retry.";
  const subline = verdictPassed
    ? "You faced the Boss and held your reasoning together. That's the bar — and you cleared it."
    : "You're close. Run it once more — same concepts, fresh questions — and it'll click.";

  // Staged-reveal index counter — each block bumps it so the cascade is ordered.
  let order = 0;
  const next = () => order++;

  return (
    <Shell testid="reflection-debrief">
      <div className={s.debrief}>
        {/* ---- verdict frame + overall score ring + band ---- */}
        <div
          className={[
            s.statusFrame,
            verdictPassed ? s.statusPass : s.statusRetry,
            s.reveal,
          ].join(" ")}
          style={{ ["--i" as string]: next() }}
        >
          <div className={s.statusGlow} aria-hidden="true" />
          <div className={s.statusInner}>
            <div className={s.statusPill}>
              {verdictPassed ? (
                <Pill tone="good">✓ Passed</Pill>
              ) : (
                <Pill tone="warn">Needs Retry</Pill>
              )}
            </div>
            <Title size="hero">{headline}</Title>
            {verdictLabel ? (
              <p className={s.verdictLabel}>{verdictLabel}</p>
            ) : (
              <Lead>{subline}</Lead>
            )}

            {(overallPct !== null || bandName) && (
              <div className={s.scoreBlock} data-testid="reflection-score">
                {overallPct !== null && (
                  <div
                    className={`${s.ring} ${verdictPassed ? s.ringPass : s.ringRetry}`}
                    style={{ ["--pct" as string]: overallPct }}
                    role="img"
                    aria-label={`Overall score ${overallPct} percent`}
                  >
                    <span className={s.ringInner}>
                      <span className={s.ringPct}>{overallPct}%</span>
                      <span className={s.ringPctLabel}>Overall</span>
                    </span>
                  </div>
                )}
                {bandName && (
                  <div className={s.bandWrap}>
                    <span className={s.bandKicker}>Your band</span>
                    <span className={s.bandName}>{bandName}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ---- per-division breakdown ---- */}
        {debrief?.divisions && debrief.divisions.length > 0 && (
          <section className={`${s.panel} ${s.reveal}`} style={{ ["--i" as string]: next() }}>
            <header className={s.panelHead}>
              <span className={s.panelTitle}>How each part went</span>
            </header>
            <div className={s.divisions}>
              {debrief.divisions.map((d, i) => (
                <DivisionRow key={d.key} division={d} index={i} />
              ))}
            </div>
          </section>
        )}

        {/* ---- mistake repairs (highlight when > 0) ---- */}
        {typeof debrief?.mistake_repairs === "number" && debrief.mistake_repairs > 0 && (
          <div className={`${s.repairs} ${s.reveal}`} style={{ ["--i" as string]: next() }}>
            <span className={s.repairsBadge}>{debrief.mistake_repairs}</span>
            <span className={s.repairsText}>
              <span className={s.repairsTitle}>
                {debrief.mistake_repairs === 1
                  ? "1 mistake turned around"
                  : `${debrief.mistake_repairs} mistakes turned around`}
              </span>
              <span className={s.repairsSub}>
                You caught these on a second pass — that's exactly how mastery is earned.
              </span>
            </span>
          </div>
        )}

        {/* ---- strong points ---- */}
        {debrief?.strong_points && debrief.strong_points.length > 0 && (
          <section
            className={`${s.panel} ${s.panelGood} ${s.reveal}`}
            style={{ ["--i" as string]: next() }}
          >
            <header className={s.panelHead}>
              <span className={s.panelTitle}>What you nailed</span>
            </header>
            <ul className={s.pointList}>
              {debrief.strong_points.map((pt, i) => (
                <li key={i} className={s.pointItem}>
                  <CheckIcon className={`${s.pointIcon} ${s.iconGood}`} />
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ---- weak points ---- */}
        {debrief?.weak_points && debrief.weak_points.length > 0 && (
          <section
            className={`${s.panel} ${s.panelWarm} ${s.reveal}`}
            style={{ ["--i" as string]: next() }}
          >
            <header className={s.panelHead}>
              <span className={s.panelTitle}>Where to sharpen</span>
            </header>
            <ul className={s.pointList}>
              {debrief.weak_points.map((pt, i) => (
                <li key={i} className={s.pointItem}>
                  <FocusIcon className={`${s.pointIcon} ${s.iconWarn}`} />
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ---- next steps ---- */}
        {debrief?.next_steps && debrief.next_steps.length > 0 && (
          <section className={`${s.panel} ${s.reveal}`} style={{ ["--i" as string]: next() }}>
            <header className={s.panelHead}>
              <span className={s.panelTitle}>{verdictPassed ? "Keep the edge" : "Your next steps"}</span>
            </header>
            <ul className={s.pointList}>
              {debrief.next_steps.map((step, i) => (
                <li key={i} className={s.pointItem}>
                  <span className={s.nextDot} aria-hidden="true" />
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ---- AI narrative + encouragement ---- */}
        {(debrief?.narrative || debrief?.encouragement) && (
          <section className={`${s.panel} ${s.reveal}`} style={{ ["--i" as string]: next() }}>
            <header className={s.panelHead}>
              <span className={s.panelTitle}>Your coach's read</span>
            </header>
            {debrief?.narrative && <p className={s.narrative}>{debrief.narrative}</p>}
            {debrief?.encouragement && (
              <p className={s.encouragement}>{debrief.encouragement}</p>
            )}
            {debrief?.ai_unavailable && (
              <span className={s.aiNote}>
                <SparkIcon className={s.pointIcon} />
                Coach offline — here's the standard read.
              </span>
            )}
          </section>
        )}

        {/* ---- retake note on Needs Retry ---- */}
        {!verdictPassed && (
          <p className={`${s.retakeNote} ${s.reveal}`} style={{ ["--i" as string]: next() }}>
            A retake gives you the same concepts with brand-new questions — nothing
            is memorized, everything is earned.
          </p>
        )}

        {retakeError && (
          <p className={s.error} role="alert">
            {retakeError}
          </p>
        )}

        <div className={s.actions}>
          {verdictPassed ? (
            <Button variant="blue" onClick={() => { play("tick"); goto("hub"); }} data-testid="reflection-done">
              Back to Hub →
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => { play("tick"); goto("hub"); }}
                data-testid="reflection-done"
              >
                Back to Hub
              </Button>
              <Button
                variant="blue"
                onClick={() => { play("tick"); void retake(); }}
                disabled={retaking}
                data-testid="reflection-retake"
              >
                {retaking
                  ? "Reshuffling your questions…"
                  : "Retake — same concepts, fresh questions →"}
              </Button>
            </>
          )}
        </div>
      </div>
    </Shell>
  );
}

// One per-division breakdown row: label · pct · tally + an animated score bar.
function DivisionRow({ division, index }: { division: ReflectionDivision; index: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(division.pct)));
  const statusClass =
    division.status === "passed"
      ? s.divPassed
      : division.status === "needs_retry"
      ? s.divNeedsRetry
      : s.divIncomplete;
  return (
    <div className={`${s.divRow} ${statusClass}`}>
      <span className={s.divLabel}>{division.label}</span>
      <span className={s.divStat}>
        <span className={s.divStatusDot} aria-hidden="true" />
        <span className={s.divTally}>
          {division.correct}/{division.total}
        </span>
        <span className={s.divPct}>{pct}%</span>
      </span>
      <span className={s.divBarTrack} aria-hidden="true">
        <span
          className={s.divBarFill}
          style={{ ["--pct" as string]: pct, ["--i" as string]: index }}
        />
      </span>
    </div>
  );
}

// ---- inline glyphs (24×24 line-icons, one family per nets-design-system §5) ----
const CheckIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

const FocusIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const SparkIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M11 3c.4 3.3 1.7 4.6 5 5-3.3.4-4.6 1.7-5 5-.4-3.3-1.7-4.6-5-5 3.3-.4 4.6-1.7 5-5z" />
  </svg>
);
