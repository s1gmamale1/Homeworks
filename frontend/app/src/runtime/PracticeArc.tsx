import { useRuntimeStore } from "./store";
import { Eyebrow, Title, Lead, Button, FeatureCard } from "../shared/ui/primitives";
import { GameHost, gameLabel } from "./GameHost";
import LivingBackdrop from "./LivingBackdrop";
import { play } from "./sfx";
import s from "./PracticeArc.module.css";

// ---------------------------------------------------------------------------
// PracticeArc — the F4 orchestrator. The homework body that opens after the
// Unlock Gate. Reads the dynamic game order (resolved on entry by the store),
// renders a progress rail (game 1..N → Boss), and hosts the current node via
// <GameHost>. Boss is ALWAYS the final node. Each game self-reports completion
// through `advanceGame`; when the last node clears, the arc shows the outro.
// ---------------------------------------------------------------------------
export function PracticeArc() {
  const payload = useRuntimeStore((st) => st.payload);
  const gameOrder = useRuntimeStore((st) => st.practice.gameOrder);
  const currentGameIndex = useRuntimeStore((st) => st.practice.currentGameIndex);
  const completed = useRuntimeStore((st) => st.practice.completed);
  const finished = useRuntimeStore((st) => st.practice.finished);
  const advanceGame = useRuntimeStore((st) => st.advanceGame);
  const goto = useRuntimeStore((st) => st.goto);

  const arc = payload?.content_json.practice_arc;
  const currentKey = gameOrder[currentGameIndex];

  // No playable content — calm empty state rather than a blank screen.
  if (gameOrder.length === 0) {
    return (
      <main className="v2-shell" data-testid="screen-practice">
        <LivingBackdrop variant="purple" />
        <div className={s.inner}>
          <Eyebrow>Practice Arc</Eyebrow>
          <Title size="hero">Nothing to practice yet.</Title>
          <Lead>This homework has no practice games. Head back to the Hub.</Lead>
          <div className={s.actions}>
            <Button variant="blue" onClick={() => { play("tick"); goto("hub"); }} data-testid="arc-back-hub">
              ← Back to Hub
            </Button>
          </div>
        </div>
      </main>
    );
  }

  if (finished) {
    return (
      <main className="v2-shell" data-testid="screen-practice">
        <LivingBackdrop variant="purple" />
        <div className={s.inner}>
          <Eyebrow cyan>Practice Arc</Eyebrow>
          <Title size="hero">Arc cleared.</Title>
          <Lead>
            You ran the full Practice Arc and faced the Boss. That’s mastery —
            nice work.
          </Lead>
          <FeatureCard className={s.outroCard}>
            <Rail order={gameOrder} current={currentGameIndex} completed={completed} done />
          </FeatureCard>
          <div className={s.actions}>
            <Button variant="blue" onClick={() => { play("tick"); goto("hub"); }} data-testid="arc-finish-hub">
              Back to Hub →
            </Button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="v2-shell" data-testid="screen-practice">
      <LivingBackdrop variant="purple" />
      <div className={s.inner}>
        <button className={s.back} type="button" onClick={() => { play("tick"); goto("hub"); }}>
          ← Back to Hub
        </button>

        <Eyebrow cyan>Practice Arc</Eyebrow>
        <Title size="section">{arc?.title ?? payload?.title ?? "Put it into play."}</Title>
        {arc?.intro && <Lead className={s.intro}>{arc.intro}</Lead>}

        <Rail order={gameOrder} current={currentGameIndex} completed={completed} />

        <div className={s.stageLabel} aria-live="polite">
          <span className={s.stageCount}>
            {currentGameIndex + 1} / {gameOrder.length}
          </span>
          <span className={s.stageName}>{gameLabel(currentKey)}</span>
        </div>

        <div className={s.gameSlot} key={currentKey}>
          <GameHost gameKey={currentKey} onComplete={advanceGame} />
        </div>
      </div>
    </main>
  );
}

// The progress rail: one node per game, Boss visually distinct as the final
// peak. Done nodes fill in; the current node pulses.
function Rail({
  order,
  current,
  completed,
  done,
}: {
  order: string[];
  current: number;
  completed: boolean[];
  done?: boolean;
}) {
  return (
    <ol className={s.rail} aria-label="Practice Arc progress">
      {order.map((key, i) => {
        const isBoss = key === "boss";
        const isDone = done || completed[i];
        const isCurrent = !done && i === current;
        const cls = [
          s.node,
          isBoss && s.nodeBoss,
          isDone && s.nodeDone,
          isCurrent && s.nodeCurrent,
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <li key={`${key}-${i}`} className={`${s.railItem} ${isDone ? s.itemDone : ""}`}>
            <span className={cls} aria-current={isCurrent ? "step" : undefined}>
              {isBoss ? <BossGlyph /> : isDone ? <CheckGlyph /> : i + 1}
            </span>
            <span className={`${s.nodeLabel} ${isCurrent ? s.nodeLabelOn : ""}`}>
              {gameLabel(key)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

const CheckGlyph = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

const BossGlyph = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M3 7l3 3 3-4 3 4 3-4 3 4 3-3v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
  </svg>
);
