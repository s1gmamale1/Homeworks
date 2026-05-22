// F4 — Practice Arc game-order resolution.
//
// The arc renders an ordered list of game KEYS. Order is determined here, in
// one place, so PracticeArc + the store agree:
//
//   1. If content_json.practice_arc.games[] is authored, that wins verbatim
//      (it's the explicit author intent — keys are passed straight to GameHost,
//      which renders a "coming soon" skip card for any key it can't map yet).
//   2. Otherwise we DERIVE the order: every gb_* array that exists on
//      content_json contributes its game key, in a stable canonical order, and
//      the Boss is always appended last (when boss_questions exist).
//
// The Boss is ALWAYS the final node of the arc — it's the mastery peak.

import type { ContentJson } from "../shared/types";

export const BOSS_KEY = "boss";

// Maps a content_json gb_* array name → its Practice Arc game key. Only
// tile_match is wired in v1; the other 8 keys are registered here so deriving
// the order picks them up the moment their gb_* array + GameHost entry land.
// NOTE: keys here are the ACTUAL content_json field names. Most games store an
// array under a `gb_*` field, but real_life_challenge stores an OBJECT under
// `real_life_challenge` (no gb_ prefix) and memory_palace stores an OBJECT under
// `gb_memory_palace` — hasContent() below detects both arrays and objects.
const GB_ARRAY_TO_KEY: Record<string, string> = {
  gb_tile_match: "tile_match",
  gb_sentence_fill: "sentence_fill",
  real_life_challenge: "real_life_challenge",
  gb_ttt: "ttt",
  gb_memory_palace: "memory_palace",
  gb_mystery_box: "mystery_box",
  gb_puzzle_lock: "puzzle_lock",
  gb_adaptive_quiz: "adaptive_quiz",
  gb_story_mode: "story_mode",
  // Division-3 practice games (8). Content lives under these gb_* fields.
  gb_error_detection: "error_detection",
  gb_memory_matching: "memory_matching",
  gb_jigsaw_matching: "jigsaw_matching",
  gb_assembly: "assembly",
  gb_sentence_repair: "sentence_repair",
  gb_ttt_grid: "ttt_grid",
  gb_problem_trace: "problem_trace",
  gb_counterexample: "counterexample",
  gb_dependency_chain: "dependency_chain",
  gb_confidence_check: "confidence_check",
};

// Canonical fallback order for derived arcs — keeps a sensible difficulty
// ramp regardless of object-key iteration order on content_json.
const DERIVED_ORDER: string[] = [
  // --- warm-up: recognition / recall ---
  "gb_tile_match",
  "gb_memory_matching",
  "gb_sentence_fill",
  "gb_sentence_repair",
  "gb_error_detection",
  // --- middle: relational + sequencing ---
  "gb_jigsaw_matching",
  "gb_assembly",
  "gb_mystery_box",
  "gb_puzzle_lock",
  "gb_adaptive_quiz",
  "gb_memory_palace",
  "gb_story_mode",
  // --- late: multi-step reasoning + decision ---
  "gb_problem_trace",
  "gb_dependency_chain",
  "gb_ttt_grid",
  "gb_counterexample",
  // --- capstone: metacognition + decision role-play ---
  "gb_confidence_check",
  "gb_ttt",
  "real_life_challenge",
];

// True when the content field holds a non-empty array OR a non-empty object.
// (Most games are arrays; real_life_challenge + memory_palace are objects.)
function hasContent(content: ContentJson, key: string): boolean {
  const v = content[key];
  if (Array.isArray(v)) return v.length > 0;
  if (v && typeof v === "object") return Object.keys(v as object).length > 0;
  return false;
}

/**
 * Resolve the ordered list of game keys for the Practice Arc. Boss is always
 * the last node when boss_questions are present. Returns an empty array only
 * when there's no playable content at all.
 */
export function resolveGameOrder(content: ContentJson | undefined): string[] {
  if (!content) return [];

  // The DYNAMIC boss (Plan 5) generates its questions on demand, so it may
  // ship with NO static `boss_questions` array. Treat the boss as present when
  // ANY of: static boss_questions exist, boss_meta is authored (the dynamic
  // boss's config home), or the authored practice_arc.games already lists
  // "boss". Without this the dynamic-only boss would never appear in the arc.
  const hasBoss =
    (Array.isArray(content.boss_questions) && content.boss_questions.length > 0) ||
    (content.boss_meta != null && typeof content.boss_meta === "object") ||
    (Array.isArray(content.practice_arc?.games) &&
      content.practice_arc!.games!.some((k) => k === BOSS_KEY));

  // 1) Author-specified order wins.
  const authored = content.practice_arc?.games;
  if (Array.isArray(authored) && authored.length > 0) {
    const order = authored.filter((k): k is string => typeof k === "string");
    // Guarantee Boss is last when present and not already authored in.
    if (hasBoss && !order.includes(BOSS_KEY)) order.push(BOSS_KEY);
    return order;
  }

  // 2) Derive from the gb_* arrays that exist, in canonical order.
  const order: string[] = [];
  for (const arrayName of DERIVED_ORDER) {
    if (hasContent(content, arrayName)) order.push(GB_ARRAY_TO_KEY[arrayName]);
  }
  if (hasBoss) order.push(BOSS_KEY);
  return order;
}
