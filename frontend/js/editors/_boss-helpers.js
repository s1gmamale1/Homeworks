// frontend/js/editors/_boss-helpers.js
// Pure helpers for the Final Boss builder editor.
//
// Mirrors `_tile-match-helpers.js` and `_real-life-challenge-helpers.js` so
// regression tests can drive helpers directly from Node (no browser surface).
// Exposed on `window.BossHelpers` for the browser editor and on
// `module.exports` for Node tests.
//
// Spec sources:
//   FINAL_BOSS_BACKEND_PLAN.md §1 (BossMeta schema), §4b (UI deltas), §4c (helpers)
//   standards/system/games/Game_Mechanics_Docs/21_Final-Boss/NETS-Final-Boss-Specification.md
//   §3 (boss types) / §6 (grade-banded HP) / §8 (hint cost) / §11 (mastery + mythical)

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Grade band — bins (Number(grade) → "g1_4" | "g5" | "g6_8" | "g9_11")
  // Per spec §6: HP scales 50 / 100 / 100 / 150 across these bins.
  // ---------------------------------------------------------------------------

  function gradeBandFromGrade(grade) {
    const g = Number(grade) || 8;
    if (g <= 4) return "g1_4";
    if (g === 5) return "g5";
    if (g <= 8) return "g6_8";
    return "g9_11";
  }

  // Spec §6 — Sub Boss starting HP ladder.
  function defaultHpForGradeBand(band) {
    return { g1_4: 50, g5: 100, g6_8: 100, g9_11: 150 }[band] || 100;
  }

  // Spec §8 — hint cost ladder (+5 / +10 / +10 / +15 HP regen to boss).
  function defaultHintCostForGradeBand(band) {
    return { g1_4: 5, g5: 10, g6_8: 10, g9_11: 15 }[band] || 10;
  }

  // Spec §3 attempts policy:
  //   - Big / Mythical → 1 (fixed)
  //   - Sub Premium    → null (unlimited)
  //   - Sub Basic      → 2
  // null is the sentinel for "unlimited" — Pydantic accepts None there.
  function defaultAttemptsForBossType(bossType, tier) {
    if (bossType === "big") return 1;
    if (bossType === "mythical") return 1;
    return tier === "premium" ? null : 2;
  }

  // Premium gates: Big + Mythical only available on premium tier.
  function bossTypeOptions(tier) {
    return tier === "premium" ? ["sub", "big", "mythical"] : ["sub"];
  }

  // PISA literacy level enum (spec §1) — advisory metadata per question.
  function pisaLevelOptions() {
    return ["L1", "L2", "L3", "L4", "L5", "L6"];
  }

  // Bloom's revised taxonomy upper-tier verbs (spec §1) — advisory.
  function bloomLevelOptions() {
    return ["apply", "analyze", "evaluate", "create"];
  }

  // Spec §11 — Mythical Boss has zero hints. Used by the editor's
  // boss_type-change side-effect to scrub all per-question hints.
  // Defensive: handles null / undefined / non-array input by returning [].
  function clearHintsForMythical(questions) {
    if (!Array.isArray(questions)) return [];
    return questions.map((q) => ({ ...q, hints: [] }));
  }

  const api = {
    gradeBandFromGrade,
    defaultHpForGradeBand,
    defaultHintCostForGradeBand,
    defaultAttemptsForBossType,
    bossTypeOptions,
    pisaLevelOptions,
    bloomLevelOptions,
    clearHintsForMythical,
  };

  if (typeof window !== "undefined") {
    window.BossHelpers = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})();
