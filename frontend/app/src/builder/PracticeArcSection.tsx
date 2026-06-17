import { useState } from "react";
import type { BuilderDraft, DraftPracticeArc } from "./types";
import { gameLabel } from "../runtime/GameHost";
import { EditorCard, SmallButton } from "./fields";
import { TileMatchEditor } from "./TileMatchEditor";
import { SentenceFillEditor } from "./SentenceFillEditor";
import { MysteryBoxEditor } from "./MysteryBoxEditor";
import { PuzzleLockEditor } from "./PuzzleLockEditor";
import { AdaptiveQuizEditor } from "./AdaptiveQuizEditor";
import { MemoryPalaceEditor } from "./MemoryPalaceEditor";
import { TttEditor } from "./TttEditor";
import { RealLifeChallengeEditor } from "./RealLifeChallengeEditor";
import { ListeningEditor } from "./ListeningEditor";
import s from "./editors.module.css";
import t from "./PracticeArcSection.module.css";

// The Practice Arc game keys an author can compose. Boss is implicit (always
// the last node) so it's authored in the Boss section, not orderable here.
// Mirrors gameOrder.ts's keys. `story_mode` has no editor yet — it remains
// orderable (renders a "coming soon" skip card in the runtime).
const ARC_GAME_KEYS = [
  "tile_match",
  "sentence_fill",
  "mystery_box",
  "puzzle_lock",
  "adaptive_quiz",
  "memory_palace",
  "listening",
  "story_mode",
  "ttt",
  "real_life_challenge",
];

// ---------------------------------------------------------------------------
// Practice Arc section — game ORDER (moved out of BossEditor) + a per-game
// sub-tab that renders the matching game editor wired to its draft slice.
//
// STRUCTURAL DECISION (Wave-1 must know): the section is two stacked panels.
//   1. "Practice Arc order" — the existing reorder/toggle list (reused from the
//      old BossEditor verbatim). Adding/removing a key here is what makes a game
//      appear in the sub-tab strip.
//   2. A sub-tab strip (one chip per ordered, EDITABLE game key) + the active
//      game's editor. The selected sub-tab is local state; each editor receives
//      `value={draft.<slice>}` + `onChange` that calls `updateDraft`. `boss` is
//      filtered out (authored in the Boss section); `story_mode` shows a
//      "coming soon" note (no editor yet).
// ---------------------------------------------------------------------------
export function PracticeArcSection({
  draft,
  updateDraft,
}: {
  draft: BuilderDraft;
  updateDraft: (next: BuilderDraft) => void;
}) {
  const practiceArc = draft.practice_arc;
  const onPracticeArcChange = (next: DraftPracticeArc) =>
    updateDraft({ ...draft, practice_arc: next });

  // The ordered, editable game keys (drop boss — authored in the Boss section).
  const editableGames = practiceArc.games.filter((g) => g !== "boss");
  const [activeGame, setActiveGame] = useState<string | null>(
    editableGames[0] ?? null
  );

  const moveGame = (i: number, delta: number) => {
    const games = [...practiceArc.games];
    const j = i + delta;
    if (j < 0 || j >= games.length) return;
    [games[i], games[j]] = [games[j], games[i]];
    onPracticeArcChange({ games });
  };

  const toggleGame = (key: string) => {
    const has = practiceArc.games.includes(key);
    onPracticeArcChange({
      games: has
        ? practiceArc.games.filter((g) => g !== key)
        : [...practiceArc.games, key],
    });
  };

  // Keep the active sub-tab valid as games are added/removed.
  const selected =
    activeGame && editableGames.includes(activeGame)
      ? activeGame
      : editableGames[0] ?? null;

  return (
    <div className={s.editor}>
      <EditorCard title="Practice Arc order">
        <p className={s.help}>
          The arc plays games in this order, then the Boss (always last).
          Reorder with the arrows; toggle games on or off below. Pick a game
          chip to edit its content.
        </p>
        <ol className={s.arcList}>
          {practiceArc.games.map((key, i) => (
            <li key={key} className={s.arcRow}>
              <span className={s.arcIndex}>{i + 1}</span>
              <span className={s.arcLabel}>{gameLabel(key)}</span>
              <span className={s.arcControls}>
                <SmallButton onClick={() => moveGame(i, -1)} disabled={i === 0}>
                  ↑
                </SmallButton>
                <SmallButton
                  onClick={() => moveGame(i, 1)}
                  disabled={i === practiceArc.games.length - 1}
                >
                  ↓
                </SmallButton>
                <SmallButton tone="danger" onClick={() => toggleGame(key)}>
                  Remove
                </SmallButton>
              </span>
            </li>
          ))}
          <li className={`${s.arcRow} ${s.arcBoss}`}>
            <span className={s.arcIndex}>★</span>
            <span className={s.arcLabel}>Boss Arena (always last)</span>
          </li>
        </ol>
        <div className={s.gamePicker}>
          {ARC_GAME_KEYS.filter((k) => !practiceArc.games.includes(k)).map(
            (key) => (
              <SmallButton key={key} onClick={() => toggleGame(key)}>
                + {gameLabel(key)}
              </SmallButton>
            )
          )}
        </div>
      </EditorCard>

      {editableGames.length > 0 && selected && (
        <>
          <div className={t.gameTabs} role="tablist" aria-label="Practice Arc games">
            {editableGames.map((key) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={selected === key}
                className={`${t.gameTab} ${selected === key ? t.gameTabActive : ""}`}
                onClick={() => setActiveGame(key)}
              >
                {gameLabel(key)}
              </button>
            ))}
          </div>
          <GameEditor gameKey={selected} draft={draft} updateDraft={updateDraft} />
        </>
      )}
    </div>
  );
}

// Renders the matching editor for the active game key, wired to its draft slice.
function GameEditor({
  gameKey,
  draft,
  updateDraft,
}: {
  gameKey: string;
  draft: BuilderDraft;
  updateDraft: (next: BuilderDraft) => void;
}) {
  switch (gameKey) {
    case "tile_match":
      return (
        <TileMatchEditor
          value={draft.gb_tile_match}
          onChange={(gb_tile_match) => updateDraft({ ...draft, gb_tile_match })}
        />
      );
    case "sentence_fill":
      return (
        <SentenceFillEditor
          value={draft.gb_sentence_fill}
          onChange={(gb_sentence_fill) =>
            updateDraft({ ...draft, gb_sentence_fill })
          }
        />
      );
    case "mystery_box":
      return (
        <MysteryBoxEditor
          value={draft.gb_mystery_box}
          onChange={(gb_mystery_box) => updateDraft({ ...draft, gb_mystery_box })}
        />
      );
    case "puzzle_lock":
      return (
        <PuzzleLockEditor
          value={draft.gb_puzzle_lock}
          onChange={(gb_puzzle_lock) => updateDraft({ ...draft, gb_puzzle_lock })}
        />
      );
    case "adaptive_quiz":
      return (
        <AdaptiveQuizEditor
          value={draft.gb_adaptive_quiz}
          onChange={(gb_adaptive_quiz) =>
            updateDraft({ ...draft, gb_adaptive_quiz })
          }
        />
      );
    case "memory_palace":
      return (
        <MemoryPalaceEditor
          value={draft.gb_memory_palace}
          config={draft.gb_memory_palace_config}
          onChange={(gb_memory_palace) =>
            updateDraft({ ...draft, gb_memory_palace })
          }
          onConfigChange={(gb_memory_palace_config) =>
            updateDraft({ ...draft, gb_memory_palace_config })
          }
        />
      );
    case "ttt":
      return (
        <TttEditor
          value={draft.gb_ttt}
          config={draft.gb_ttt_config}
          onChange={(gb_ttt) => updateDraft({ ...draft, gb_ttt })}
          onConfigChange={(gb_ttt_config) =>
            updateDraft({ ...draft, gb_ttt_config })
          }
        />
      );
    case "real_life_challenge":
      return (
        <RealLifeChallengeEditor
          value={draft.real_life_challenge}
          onChange={(real_life_challenge) =>
            updateDraft({ ...draft, real_life_challenge })
          }
        />
      );
    case "listening":
      return (
        <ListeningEditor
          value={draft.listening}
          onChange={(listening) => updateDraft({ ...draft, listening })}
        />
      );
    default:
      // story_mode (and any future key) — no editor yet.
      return (
        <p className={t.noEditor}>
          No content editor for “{gameLabel(gameKey)}” yet — it’ll play as a
          skip card in the runtime until its editor ships.
        </p>
      );
  }
}
