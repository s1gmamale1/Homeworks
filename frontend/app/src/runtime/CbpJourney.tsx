// CbpJourney — a PRESENTATIONAL winding rail of 9 station nodes that maps the
// CBP sub-machine to a visible journey (Hub DNA: 3D-press pebbles + a recoloring
// connector). It reads the store (cbp.subStage + checkpointIndex + results) and
// derives each station's state — passed (green) / current (bobs) / future (idle).
//
// HARD RULE: this is presentational only. It renders NO navigation, mutates NO
// store, and carries NO answer content. Tapping a node does nothing (the rail
// reflects progress, the stage controls drive the actual flow). The 3D press is
// purely tactile feedback.

import { useRuntimeStore } from "./store";
import type { CbpSubStage } from "./store";
import s from "./CbpJourney.module.css";

type StationState = "passed" | "current" | "future";

interface Station {
  key: string;
  label: string;
  short: string; // compact badge label
}

// The fixed 9-station journey. CP/LB pairs interleave ×3, then the new Reasoning
// step, the staged Simulation, and the Feedback close.
const STATIONS: Station[] = [
  { key: "setup", label: "Setup", short: "S" },
  { key: "cp1", label: "Checkpoint 1", short: "1" },
  { key: "lb1", label: "Lesson 1", short: "L1" },
  { key: "cp2", label: "Checkpoint 2", short: "2" },
  { key: "lb2", label: "Lesson 2", short: "L2" },
  { key: "cp3", label: "Checkpoint 3", short: "3" },
  { key: "reasoning", label: "Reasoning", short: "R" },
  { key: "simulation", label: "Simulation", short: "Sim" },
  { key: "feedback", label: "Feedback", short: "F" },
];

// Map the live sub-machine onto a 0-based "furthest reached" position along the
// 9-station rail. Each checkpoint and its lesson occupy distinct stations, so we
// fold (subStage, checkpointIndex) into a single ordinal. The CP→LB pairs are at
// indices: cp1=1,lb1=2, cp2=3,lb2=4, cp3=5, then reasoning=6, sim=7, feedback=8.
function activeIndex(subStage: CbpSubStage, checkpointIndex: number): number {
  switch (subStage) {
    case "setup":
      return 0;
    case "checkpoint":
      // checkpointIndex 0/1/2 → station 1/3/5
      return 1 + checkpointIndex * 2;
    case "learningBlock":
      // checkpointIndex 0/1/2 → station 2/4/ (cp3 has no lesson station → 6)
      return checkpointIndex >= 2 ? 6 : 2 + checkpointIndex * 2;
    case "reasoning":
      return 6;
    case "sim":
      return 7;
    case "feedback":
      return 8;
    default:
      return 0;
  }
}

const CheckMark = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

export default function CbpJourney() {
  const subStage = useRuntimeStore((st) => st.cbp.subStage);
  const checkpointIndex = useRuntimeStore((st) => st.cbp.checkpointIndex);
  const results = useRuntimeStore((st) => st.cbp.results);
  const cbpGate = useRuntimeStore((st) => st.gateState?.cbp);

  const active = activeIndex(subStage, checkpointIndex);
  // Once feedback shows, a passed gate means the whole rail is cleared.
  const cleared = subStage === "feedback" && (cbpGate?.passed ?? false);

  // Which checkpoint stations are server-confirmed correct, so the rail can mark
  // a passed checkpoint green even before the student reaches the end.
  const stationState = (i: number): StationState => {
    if (cleared) return "passed";
    if (i < active) return "passed";
    if (i === active) return "current";
    return "future";
  };

  // The recoloring connector fill fraction (0..1) from start → active station.
  const lastIndex = STATIONS.length - 1;
  const fillPct = cleared ? 100 : Math.round((active / lastIndex) * 100);

  return (
    <nav className={s.journey} data-testid="cbp-journey" aria-label="Case progress">
      <ol
        className={s.rail}
        style={{ ["--fill" as string]: `${fillPct}%` }}
      >
        {STATIONS.map((station, i) => {
          const state = stationState(i);
          // Checkpoint stations (cp1/cp2/cp3) carry a server-confirmed result so
          // a wrong-then-correct retake reads honestly: passed only when correct.
          const cpIdx =
            station.key === "cp1" ? 0 : station.key === "cp2" ? 1 : station.key === "cp3" ? 2 : -1;
          const cpAnswered = cpIdx >= 0 && i < active;
          const cpCorrect = cpAnswered ? results[cpIdx] === true : null;

          const align = i % 2 === 0 ? s.alignLeft : s.alignRight;
          return (
            <li
              key={station.key}
              className={[
                s.station,
                align,
                state === "passed" ? s.statePassed : "",
                state === "current" ? s.stateCurrent : "",
                state === "future" ? s.stateFuture : "",
                cpAnswered && cpCorrect === false ? s.stateMissed : "",
              ]
                .filter(Boolean)
                .join(" ")}
              data-state={state}
            >
              <span className={s.node} aria-hidden="true">
                <span className={s.nodeFace}>
                  {state === "passed" && !(cpAnswered && cpCorrect === false) ? (
                    <CheckMark />
                  ) : (
                    <span className={s.nodeBadge}>{station.short}</span>
                  )}
                </span>
              </span>
              <span className={s.label}>{station.label}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
