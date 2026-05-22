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
import type { MemoryCheckItem, MemoryCheckItemType } from "../shared/types";
import IntegrityNudge from "./IntegrityNudge";
import { useAnswerTelemetry } from "./hooks/useAnswerTelemetry";
import { acknowledgeNudge } from "../shared/api";
import LivingBackdrop from "./LivingBackdrop";
import s from "./MemoryCheck.module.css";
import { play } from "./sfx";

const KIND_LABEL: Record<MemoryCheckItemType, string> = {
  mcq: "Multiple choice",
  true_false: "True / False",
  choose_explanation: "Choose the explanation",
  fill_blank: "Fill in the blank",
};

// Tile B, graded half. Iterates the Memory Check items; renders each by type
// (option types → tappable LessonPanel rows; fill_blank → text input). After
// each submit it shows server-driven inline feedback. At the end it refetches
// the gate: pass → result/done; fail → soft-retry back to the deck. Mirrors the
// CaseBasedPreview sub-machine: correctness is ALWAYS the server's call.
export function MemoryCheck() {
  const subStage = useRuntimeStore((st) => st.fc.subStage);
  if (subStage === "result") return <ResultStage />;
  return <ItemStage />;
}

function ItemStage() {
  const payload = useRuntimeStore((st) => st.payload);
  const itemIndex = useRuntimeStore((st) => st.fc.itemIndex);
  const results = useRuntimeStore((st) => st.fc.results);
  const scorePct = useRuntimeStore((st) => st.fc.scorePct);
  const submitting = useRuntimeStore((st) => st.fc.submitting);
  const submitError = useRuntimeStore((st) => st.fc.submitError);
  const lastFeedback = useRuntimeStore((st) => st.fc.lastFeedback);
  const lastCorrect = useRuntimeStore((st) => st.fc.lastCorrect);
  const submitMemoryItem = useRuntimeStore((st) => st.submitMemoryItem);
  const advanceMemoryItem = useRuntimeStore((st) => st.advanceMemoryItem);
  const goto = useRuntimeStore((st) => st.goto);
  const nudge = useRuntimeStore((st) => st.fc.lastNudge);
  const dismissNudge = useRuntimeStore((st) => st.dismissMcNudge);
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);
  // Advisory anti-cheat — re-baseline timing/paste per item.
  const tele = useAnswerTelemetry(itemIndex);

  const items = (payload?.content_json.memory_check?.items ?? []) as MemoryCheckItem[];
  const total = items.length;
  const item = items[itemIndex] as MemoryCheckItem | undefined;
  const hasOptions = !!item?.options && item.options.length > 0;

  // Local input state — selection index for option types, text for fill_blank.
  const [selected, setSelected] = useState<number | null>(null);
  const [text, setText] = useState("");

  // Reset inputs whenever we move to a different item.
  useEffect(() => {
    setSelected(null);
    setText("");
  }, [itemIndex]);

  // The current item is "answered" once the store recorded a server result.
  const answered = results[itemIndex] !== null && results[itemIndex] !== undefined;

  if (!item) {
    return (
      <Shell testid="mc-item">
        <Lead>This Memory Check item is unavailable.</Lead>
      </Shell>
    );
  }

  const onSubmit = () => {
    if (submitting || answered) return;
    if (hasOptions) {
      if (selected === null) return;
      // Option types grade by option_index server-side: submit the tapped
      // index as a string. The client never decides correctness. Telemetry is
      // advisory (timing for taps; no paste on options).
      void submitMemoryItem(itemIndex, String(selected), tele.read());
    } else {
      // fill_blank: submit the typed text verbatim, with advisory telemetry.
      const trimmed = text.trim();
      if (!trimmed) return;
      void submitMemoryItem(itemIndex, trimmed, tele.read());
    }
  };

  const answeredCount = results.filter((r) => r !== null && r !== undefined).length;
  const isLastUnanswered =
    results.filter((r, i) => i !== itemIndex && (r === null || r === undefined)).length === 0;

  return (
    <Shell testid="mc-item">
      <BackToHub onClick={() => goto("hub")} />

      <div className={s.head}>
        <Eyebrow>Memory Check</Eyebrow>
        <span className={s.counter}>
          <span className={s.score}>{scorePct}%</span> · {answeredCount}/{total} answered
        </span>
      </div>

      <Progress current={itemIndex} results={results} total={total} />

      <Pill className={s.kind} tone="accent">
        {KIND_LABEL[item.type] ?? item.type}
      </Pill>
      <Title size="section">{item.prompt}</Title>

      {hasOptions ? (
        <div className={s.options} role="radiogroup" aria-label="Answer options">
          {item.options!.map((opt, i) => (
            <LessonPanel
              key={i}
              eyebrow={`Option ${String.fromCharCode(65 + i)}`}
              title={opt}
              state={
                answered
                  ? selected === i
                    ? lastCorrect
                      ? "correct"
                      : "wrong"
                    : "idle"
                  : selected === i
                  ? "active"
                  : "idle"
              }
              disabled={submitting || answered}
              onClick={() => setSelected(i)}
            />
          ))}
        </div>
      ) : (
        <div className={s.fillWrap}>
          <label className={s.fillLabel} htmlFor="mc-fill">
            Your answer
          </label>
          <input
            id="mc-fill"
            className={s.fillInput}
            type="text"
            value={text}
            placeholder="Type your answer…"
            disabled={submitting || answered}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSubmit();
            }}
            onPaste={tele.onPaste}
            data-testid="mc-fill-input"
            autoComplete="off"
          />
        </div>
      )}

      {submitError && (
        <p className={s.error} role="alert">
          {submitError}
        </p>
      )}

      {answered && lastFeedback && (
        <div
          className={`${s.feedback} ${lastCorrect ? s.feedbackGood : s.feedbackWrong}`}
          role="status"
        >
          <div className={s.feedbackHead}>
            {lastCorrect ? (
              <Pill tone="good">✓ Correct</Pill>
            ) : (
              <Pill tone="warn">Not quite</Pill>
            )}
          </div>
          <p className={s.feedbackBody}>{lastFeedback}</p>
        </div>
      )}

      {/* Advisory anti-cheat nudge — beside feedback, never gates Continue. */}
      <IntegrityNudge
        nudge={nudge}
        onDismiss={dismissNudge}
        onRespond={(choice) =>
          acknowledgeNudge(hwId, sessionId, "memory_check", choice)
        }
      />

      <div className={s.actions}>
        {!answered ? (
          <Button
            variant="blue"
            onClick={onSubmit}
            disabled={
              submitting || (hasOptions ? selected === null : text.trim() === "")
            }
            data-testid="mc-submit"
          >
            {submitting ? "Checking…" : "Submit answer"}
          </Button>
        ) : (
          <Button variant="blue" onClick={advanceMemoryItem} data-testid="mc-continue">
            {isLastUnanswered ? "See results →" : "Next item →"}
          </Button>
        )}
      </div>
    </Shell>
  );
}

// ---- result: gate-driven pass vs. soft-retry ----
function ResultStage() {
  const payload = useRuntimeStore((st) => st.payload);
  const gate = useRuntimeStore((st) => st.gateState);
  const fcScore = useRuntimeStore((st) => st.fc.scorePct);
  const goto = useRuntimeStore((st) => st.goto);
  const retryMemoryCheck = useRuntimeStore((st) => st.retryMemoryCheck);

  const mc = gate?.mc;
  const passed = mc?.passed ?? false;
  // Prefer the server's score; fall back to the locally tracked running score.
  const scorePct = mc?.score_pct ?? fcScore;

  // Fire "complete" once on mount when the Memory Check is passed.
  const firedRef = useRef(false);
  useEffect(() => {
    if (passed && !firedRef.current) {
      firedRef.current = true;
      play("complete");
    }
  }, [passed]);
  const threshold = mc?.threshold_pct ?? payload?.content_json.memory_check?.pass_threshold_pct ?? 60;
  const unlocked = gate?.practice_arc_unlocked ?? false;

  return (
    <Shell testid="mc-result">
      <div className={s.resultHead}>
        {passed ? <Pill tone="good">✓ Passed</Pill> : <Pill tone="warn">Needs another pass</Pill>}
        <span className={s.counter}>
          {mc?.correct ?? 0}/{mc?.total ?? 0} correct
        </span>
      </div>

      <Title size="hero">
        {passed ? "Recall locked in." : "Close — review and retry."}
      </Title>
      <Lead>
        {passed
          ? `You scored ${scorePct}% — at or above the ${threshold}% bar. This section is done.`
          : `You scored ${scorePct}%, just under the ${threshold}% bar. Review the cards you missed, then re-take just those items.`}
      </Lead>

      <FeatureCard className={s.resultCard}>
        <div className={s.resultStat}>
          <span className={s.resultBig}>{scorePct}</span>
          <span className={s.resultUnit}>% recall</span>
        </div>
        <div className={s.resultBar} aria-hidden="true">
          <div
            className={`${s.resultBarFill} ${passed ? s.pass : ""}`}
            style={{ width: `${Math.max(0, Math.min(100, scorePct))}%` }}
          />
          <div className={s.resultThreshold} style={{ left: `${threshold}%` }} />
        </div>
      </FeatureCard>

      <div className={s.actions}>
        {passed ? (
          unlocked ? (
            // Division 3 is unlocked — return to the hub, where the
            // chained→shake→break→fireworks unlock choreography auto-plays on
            // the Homework Practices node (play-once per device).
            <Button variant="blue" onClick={() => goto("hub")} data-testid="mc-continue-hub">
              Continue →
            </Button>
          ) : (
            <Button variant="blue" onClick={() => goto("hub")} data-testid="mc-back-hub">
              Back to Hub →
            </Button>
          )
        ) : (
          <>
            <Button variant="outline" onClick={() => goto("hub")}>
              Back to Hub
            </Button>
            <Button variant="blue" onClick={retryMemoryCheck} data-testid="mc-retry">
              Review &amp; retry →
            </Button>
          </>
        )}
      </div>
    </Shell>
  );
}

// ---- shared bits ----
function Shell({ children, testid }: { children: ReactNode; testid: string }) {
  return (
    <main className="v2-shell" data-testid={testid}>
      <LivingBackdrop variant="teal" />
      <div className={s.stage} key={testid}>
        {children}
      </div>
    </main>
  );
}

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

function Progress({
  current,
  results,
  total,
}: {
  current: number;
  results: (boolean | null)[];
  total: number;
}) {
  return (
    <div className={s.progress} aria-label={`Item ${current + 1} of ${total}`}>
      {Array.from({ length: total }).map((_, i) => {
        const r = results[i];
        const cls =
          i === current
            ? s.dotActive
            : r === true
            ? s.dotCorrect
            : r === false
            ? s.dotWrong
            : "";
        return <span key={i} className={`${s.dot} ${cls}`} aria-hidden="true" />;
      })}
    </div>
  );
}
