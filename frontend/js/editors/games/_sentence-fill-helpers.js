// frontend/js/editors/games/_sentence-fill-helpers.js
// Pure helper functions for the Sentence Fill builder editor.
//
// Kept in their own file so tests can load them directly via Node.js
// (test_sentence_fill_grade_defaults.py) without booting the whole browser
// surface. Exported on `window.SentenceFillHelpers` for browser use AND on
// `module.exports` (when running under Node) for the regression test.
//
// See plan §3 for the grade-band rationale:
//   G2-4 → word_bank, 2 distractors per blank
//   G5-7 → word_bank, 3 distractors per blank
//   G8+  → free_recall, no word bank

(function () {
  "use strict";

  function defaultModeForGrade(grade) {
    return grade >= 8 ? "free_recall" : "word_bank";
  }

  function recommendedDistractorCount(grade, blanksCount) {
    if (grade <= 4) return blanksCount * 2;
    if (grade <= 7) return blanksCount * 3;
    return 0;
  }

  function detectBlanks(passage) {
    if (typeof passage !== "string") return 0;
    return (passage.match(/___/g) || []).length;
  }

  const api = { defaultModeForGrade, recommendedDistractorCount, detectBlanks };

  if (typeof window !== "undefined") {
    window.SentenceFillHelpers = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})();
