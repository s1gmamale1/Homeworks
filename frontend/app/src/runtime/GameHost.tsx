import { lazy, Suspense } from "react";
import type { ComponentType } from "react";
import { Eyebrow, Title, Lead, Button, FeatureCard } from "../shared/ui/primitives";
import s from "./GameHost.module.css";

// ---------------------------------------------------------------------------
// GameHost — the extensibility seam for the Practice Arc.
//
// A registry mapping a game KEY (the same key gameOrder.ts emits) → a lazily
// loaded game component. Code-splitting via React.lazy keeps the initial
// runtime chunk small: a game's bundle only loads when the arc reaches it.
//
// ADDING ONE OF THE OTHER 8 GAMES (the whole point of this seam):
//   1. Build `games/<YourGame>.tsx` implementing the GameProps contract below
//      (it receives `onComplete` and calls it when the student finishes).
//   2. Add one line to GAME_REGISTRY:
//        your_game: lazy(() => import("./games/YourGame")),
//      using the SAME key gameOrder.ts maps your gb_* array to.
//   3. That's it — PracticeArc renders it, the rail counts it, and the
//      "coming soon" fallback stops firing for that key.
//
// Until a key is registered, GameHost renders a graceful skip card so the 8
// unbuilt games never crash the arc — the student can skip past them.
// ---------------------------------------------------------------------------

/**
 * The contract every Practice Arc game implements. A game is handed its
 * completion callback and reports done when the student clears it (all pairs
 * matched, boss defeated, etc.). Games read everything else (content, ids) from
 * the store directly, mirroring the F2/F3 sub-machines.
 */
export interface GameProps {
  onComplete: () => void;
}

// Friendly labels for the progress rail + skip card. Unregistered keys still
// get a humanized label so the arc reads sensibly.
export const GAME_LABELS: Record<string, string> = {
  tile_match: "Tile Match",
  boss: "Boss Arena",
  sentence_fill: "Sentence Fill",
  real_life_challenge: "Real-Life Challenge",
  ttt: "Tic-Tac-Toe",
  memory_palace: "Memory Palace",
  mystery_box: "Mystery Box",
  puzzle_lock: "Puzzle Lock",
  adaptive_quiz: "Adaptive Quiz",
  story_mode: "Story Mode",
};

// The registry. tile_match + boss + the four backend-backed games are live;
// the remaining keys (adaptive_quiz, mystery_box, puzzle_lock, story_mode)
// fall through to the "coming soon" skip card until their resolvers land.
const GAME_REGISTRY: Record<string, ComponentType<GameProps>> = {
  tile_match: lazy(() => import("./games/TileMatch")),
  sentence_fill: lazy(() => import("./games/SentenceFill")),
  real_life_challenge: lazy(() => import("./games/RealLifeChallenge")),
  ttt: lazy(() => import("./games/Ttt")),
  memory_palace: lazy(() => import("./games/MemoryPalace")),
  adaptive_quiz: lazy(() => import("./games/AdaptiveQuiz")),
  mystery_box: lazy(() => import("./games/MysteryBox")),
  puzzle_lock: lazy(() => import("./games/PuzzleLock")),
  boss: lazy(() => import("./BossArena")),
};

export function gameLabel(key: string): string {
  return (
    GAME_LABELS[key] ??
    key
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  );
}

/** Whether a key resolves to a real, playable game (vs. the skip fallback). */
export function isGameRegistered(key: string): boolean {
  return key in GAME_REGISTRY;
}

export function GameHost({ gameKey, onComplete }: { gameKey: string; onComplete: () => void }) {
  const Game = GAME_REGISTRY[gameKey];

  if (!Game) {
    return <ComingSoon gameKey={gameKey} onSkip={onComplete} />;
  }

  return (
    <Suspense fallback={<GameLoading label={gameLabel(gameKey)} />}>
      <Game onComplete={onComplete} />
    </Suspense>
  );
}

// Graceful fallback for the 8 not-yet-built games. Keeps the arc walkable.
function ComingSoon({ gameKey, onSkip }: { gameKey: string; onSkip: () => void }) {
  return (
    <div data-testid={`game-coming-soon-${gameKey}`}>
      <FeatureCard className={s.skip}>
        <Eyebrow>{gameLabel(gameKey)}</Eyebrow>
        <Title size="section">Coming soon.</Title>
        <Lead>
          This game isn’t built yet — skip ahead and keep your momentum. It’ll
          slot right in here once it ships.
        </Lead>
        <div className={s.skipCta}>
          <Button variant="blue" onClick={onSkip} data-testid={`game-skip-${gameKey}`}>
            Skip for now →
          </Button>
        </div>
      </FeatureCard>
    </div>
  );
}

function GameLoading({ label }: { label: string }) {
  return (
    <div className={s.loading} data-testid="game-loading" aria-busy="true">
      <div className={s.spinner} aria-hidden="true" />
      <p className={s.loadingLabel}>Loading {label}…</p>
    </div>
  );
}
