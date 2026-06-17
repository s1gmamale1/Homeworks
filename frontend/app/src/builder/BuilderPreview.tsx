import { useEffect } from "react";
import type { ReactNode } from "react";
import { useRuntimeStore } from "../runtime/store";
import { CaseBasedPreview } from "../runtime/CaseBasedPreview";
import { MemoryCheck } from "../runtime/MemoryCheck";
import { Flashcards } from "../runtime/Flashcards";
import { Reflection } from "../runtime/Reflection";
import BossArena from "../runtime/BossArena";
import TileMatch from "../runtime/games/TileMatch";
import SentenceFill from "../runtime/games/SentenceFill";
import MysteryBox from "../runtime/games/MysteryBox";
import PuzzleLock from "../runtime/games/PuzzleLock";
import AdaptiveQuiz from "../runtime/games/AdaptiveQuiz";
import MemoryPalace from "../runtime/games/MemoryPalace";
import Ttt from "../runtime/games/Ttt";
import RealLifeChallenge from "../runtime/games/RealLifeChallenge";
import Listening from "../runtime/games/Listening";
import { ExtraMaterialsView } from "../shared/ExtraMaterialsView";
import type { BuilderDraft } from "./types";
import { toContentJson } from "./draft";
import type { HydratePayload } from "../shared/types";
import s from "./BuilderPreview.module.css";

// Which runtime surface the preview pane shows. The author flips this with the
// section tabs / preview tabs; it maps 1:1 to the runtime components reused
// here (the Tile-B screens, each Practice Arc game, the Boss, and Reflection).
export type PreviewSurface =
  | "cbp"
  | "flashcards"
  | "memory"
  | "tile_match"
  | "sentence_fill"
  | "mystery_box"
  | "puzzle_lock"
  | "adaptive_quiz"
  | "memory_palace"
  | "ttt"
  | "real_life_challenge"
  | "listening"
  | "extra_materials"
  | "boss"
  | "reflection";

// The Practice Arc game surfaces (everything that renders a runtime/games/*
// component). These read their own gb_* slice straight from the store payload.
const GAME_SURFACES: ReadonlySet<PreviewSurface> = new Set<PreviewSurface>([
  "tile_match",
  "sentence_fill",
  "mystery_box",
  "puzzle_lock",
  "adaptive_quiz",
  "memory_palace",
  "ttt",
  "real_life_challenge",
  "listening",
]);

// The runtime components read EVERYTHING from useRuntimeStore (payload +
// sub-machine state) — they take no content props. So the live preview works by
// feeding the AUTHOR'S draft into the SAME store as a synthetic HydratePayload,
// then driving the relevant sub-machine to the screen we want to show. The
// preview shows the FULL draft (answers present) — that's the authoring context;
// the components are redaction-agnostic (they only read display fields anyway),
// so no answer leaks into the rendered preview surface.

function draftToPayload(draft: BuilderDraft): HydratePayload {
  const content = toContentJson(draft);

  // Memory Palace preview shim: the runtime MemoryPalace reads
  // content_json.gb_memory_palace as the SERVER-MERGED { palaces, concepts,
  // config } shape (the injector folds gb_memory_palace_config in via
  // __GB_MEMORY_PALACE__). toContentJson keeps the persisted contract split
  // (gb_memory_palace + gb_memory_palace_config), so for the LIVE PREVIEW only
  // we synthesize the merged `config` the runtime component expects. This does
  // NOT change what gets persisted (toContentJson is untouched).
  const mp = content.gb_memory_palace as
    | { palaces?: unknown[]; concepts?: unknown[] }
    | undefined;
  if (mp && (mp.palaces?.length || mp.concepts?.length)) {
    const cfg = draft.gb_memory_palace_config;
    content.gb_memory_palace = {
      ...mp,
      config: {
        concept_count: cfg.concept_count ?? 5,
        min_palace_options: cfg.min_palace_options ?? 4,
        enable_reverse_recall: cfg.enable_reverse_recall ?? false,
      },
    };
  }

  return {
    id: "__builder_preview__",
    title: draft.case_based_preview.title || "Untitled homework",
    subject: null,
    grade: null,
    lang: null,
    flow_version: "v2",
    // The runtime ContentJson type carries leak guards (answer_spec?: never), but
    // a preview legitimately holds the author's full blob. Cast through unknown
    // — the components never READ the answer fields, so this is display-safe.
    content_json: content as unknown as HydratePayload["content_json"],
  };
}

export function BuilderPreview({
  draft,
  surface,
}: {
  draft: BuilderDraft;
  surface: PreviewSurface;
}) {
  const setPayload = useRuntimeStore((st) => st.setPayload);
  const setGateState = useRuntimeStore((st) => st.setGateState);
  const startCbp = useRuntimeStore((st) => st.startCbp);
  const enterFlashcards = useRuntimeStore((st) => st.enterFlashcards);
  const startMemoryCheck = useRuntimeStore((st) => st.startMemoryCheck);
  const startBoss = useRuntimeStore((st) => st.startBoss);
  const enterReflection = useRuntimeStore((st) => st.enterReflection);

  // Re-push the draft into the store whenever it changes so the preview is live.
  useEffect(() => {
    setPayload(draftToPayload(draft));
    // A neutral, non-blocking gate state so result screens render sensibly.
    setGateState({
      cbp: { passed: false, checkpoints_correct: 0, checkpoints_total: 3 },
      mc: { passed: false, score_pct: 0, threshold_pct: draft.memory_check.pass_threshold_pct },
      practice_arc_unlocked: false,
    });
  }, [draft, setPayload, setGateState]);

  // Reset the relevant sub-machine to its first screen whenever the author
  // switches surfaces (so the preview always opens on a meaningful screen).
  // Game surfaces (TileMatch, SentenceFill, …) read their gb_* slice straight
  // from the store payload and own their local state, so they need NO
  // sub-machine reset here — the payload effect above keeps them live.
  useEffect(() => {
    switch (surface) {
      case "cbp":
        startCbp();
        break;
      case "flashcards":
        enterFlashcards();
        break;
      case "memory":
        enterFlashcards();
        startMemoryCheck();
        break;
      case "boss":
        startBoss();
        break;
      case "reflection":
        enterReflection();
        break;
      default:
        // Practice Arc game surface — nothing to reset (local-state games).
        break;
    }
    // We intentionally reset only on surface change (not on every keystroke);
    // the payload effect above keeps content live without losing the screen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [surface]);

  // Game surfaces remount on every keystroke (keyed on the content) so the
  // preview reflects edits live — the games snapshot their slice into local
  // state on mount, so we force a fresh mount when the draft changes.
  const isGame = GAME_SURFACES.has(surface);

  return (
    <PreviewFrame surface={surface}>
      {surface === "cbp" && <CaseBasedPreview />}
      {surface === "flashcards" && <Flashcards />}
      {surface === "memory" && <MemoryCheck />}
      {surface === "reflection" && <Reflection />}
      {surface === "extra_materials" && (
        <div className={s.gameWrap}>
          <ExtraMaterialsView value={draft.extra_materials} />
        </div>
      )}
      {surface === "boss" && (
        // BossArena is a Practice Arc game — it just needs an onComplete no-op.
        <div className={s.bossWrap}>
          <BossArena onComplete={() => undefined} />
        </div>
      )}
      {isGame && (
        <div className={s.gameWrap}>
          <GameSurface surface={surface} draft={draft} />
        </div>
      )}
    </PreviewFrame>
  );
}

// Renders the matching runtime game component for a Practice Arc surface, fed a
// no-op onComplete. Keyed on a content signature so it remounts when the author
// edits the slice (the games snapshot their slice into local state on mount).
function GameSurface({
  surface,
  draft,
}: {
  surface: PreviewSurface;
  draft: BuilderDraft;
}) {
  const noop = () => undefined;
  // A cheap content signature → the React key, so edits force a fresh mount.
  const sig = (() => {
    switch (surface) {
      case "tile_match":
        return JSON.stringify(draft.gb_tile_match);
      case "sentence_fill":
        return JSON.stringify(draft.gb_sentence_fill);
      case "mystery_box":
        return JSON.stringify(draft.gb_mystery_box);
      case "puzzle_lock":
        return JSON.stringify(draft.gb_puzzle_lock);
      case "adaptive_quiz":
        return JSON.stringify(draft.gb_adaptive_quiz);
      case "memory_palace":
        return JSON.stringify(draft.gb_memory_palace);
      case "ttt":
        return JSON.stringify(draft.gb_ttt);
      case "real_life_challenge":
        return JSON.stringify(draft.real_life_challenge);
      case "listening":
        return JSON.stringify(draft.listening);
      default:
        return surface;
    }
  })();

  switch (surface) {
    case "tile_match":
      return <TileMatch key={sig} onComplete={noop} />;
    case "sentence_fill":
      return <SentenceFill key={sig} onComplete={noop} />;
    case "mystery_box":
      return <MysteryBox key={sig} onComplete={noop} />;
    case "puzzle_lock":
      return <PuzzleLock key={sig} onComplete={noop} />;
    case "adaptive_quiz":
      return <AdaptiveQuiz key={sig} onComplete={noop} />;
    case "memory_palace":
      return <MemoryPalace key={sig} onComplete={noop} />;
    case "ttt":
      return <Ttt key={sig} onComplete={noop} />;
    case "real_life_challenge":
      return <RealLifeChallenge key={sig} onComplete={noop} />;
    case "listening":
      return <Listening key={sig} onComplete={noop} />;
    default:
      return null;
  }
}

function PreviewFrame({
  surface,
  children,
}: {
  surface: PreviewSurface;
  children: ReactNode;
}) {
  return (
    <div className={s.frame} data-surface={surface}>
      <div className={s.frameBar} aria-hidden="true">
        <span className={s.dot} />
        <span className={s.dot} />
        <span className={s.dot} />
        <span className={s.frameLabel}>Live student preview</span>
      </div>
      <div className={s.viewport} data-testid="builder-preview-viewport">
        {children}
      </div>
    </div>
  );
}
