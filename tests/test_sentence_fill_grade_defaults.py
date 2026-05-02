"""
Regression tests for the Sentence Fill builder editor's grade-band helper
functions. These helpers (defined in
`frontend/js/editors/games/_sentence-fill-helpers.js`) are pure and exposed on
both `window.SentenceFillHelpers` (browser) and `module.exports` (Node), so we
can drive them directly from a Node subprocess and assert their behaviour.

Spec source: SENTENCE_FILL_BACKEND_PLAN.md §3 — grade-band defaults.

If `node` is unavailable (CI without Node), the tests fall back to a regex
smoke check that asserts the helper definitions still exist verbatim in the
source file. The fallback is documented per-test.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPERS_PATH = REPO_ROOT / "frontend" / "js" / "editors" / "games" / "_sentence-fill-helpers.js"


def _node_available() -> bool:
    return shutil.which("node") is not None


def _run_node(script: str) -> dict:
    """Run a Node script that loads the helpers and prints a JSON dict on stdout.

    Returns the parsed dict. Asserts on non-zero exit + presence of `node`.
    """
    if not _node_available():
        pytest.skip("node binary not on PATH; falling back to regex smoke test")
    helpers_url = HELPERS_PATH.as_posix()
    full = (
        f"const SF = require({json.dumps(helpers_url)});\n"
        f"{script}\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(full)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            ["node", tmp_path], capture_output=True, text=True, timeout=10
        )
    finally:
        os.unlink(tmp_path)
    assert proc.returncode == 0, (
        f"node exited with {proc.returncode}\nstderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"
    )
    out = proc.stdout.strip().splitlines()[-1]
    return json.loads(out)


# ---------------------------------------------------------------------------
# defaultModeForGrade — G2-7 → word_bank, G8+ → free_recall
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_default_mode_for_grade_word_bank_band() -> None:
    """G2-7 should default to word_bank mode (per plan §3)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g2: SF.defaultModeForGrade(2),"
        "g4: SF.defaultModeForGrade(4),"
        "g7: SF.defaultModeForGrade(7),"
        "}));"
    )
    assert result["g2"] == "word_bank"
    assert result["g4"] == "word_bank"
    assert result["g7"] == "word_bank"


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_default_mode_for_grade_free_recall_band() -> None:
    """G8+ should default to free_recall mode (per plan §3)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g8: SF.defaultModeForGrade(8),"
        "g11: SF.defaultModeForGrade(11),"
        "}));"
    )
    assert result["g8"] == "free_recall"
    assert result["g11"] == "free_recall"


# ---------------------------------------------------------------------------
# recommendedDistractorCount — 2/blank for G≤4, 3/blank for G5-7, 0 for G8+
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_recommended_distractor_count_low_grade() -> None:
    """G≤4 → 2 distractors per blank."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g3_4blanks: SF.recommendedDistractorCount(3, 4),"
        "g4_2blanks: SF.recommendedDistractorCount(4, 2),"
        "}));"
    )
    assert result["g3_4blanks"] == 8
    assert result["g4_2blanks"] == 4


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_recommended_distractor_count_mid_grade() -> None:
    """G5-7 → 3 distractors per blank."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g6_3blanks: SF.recommendedDistractorCount(6, 3),"
        "g7_5blanks: SF.recommendedDistractorCount(7, 5),"
        "}));"
    )
    assert result["g6_3blanks"] == 9
    assert result["g7_5blanks"] == 15


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_recommended_distractor_count_high_grade() -> None:
    """G8+ → 0 (free_recall mode has no word bank)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g10_5blanks: SF.recommendedDistractorCount(10, 5),"
        "g8_3blanks: SF.recommendedDistractorCount(8, 3),"
        "}));"
    )
    assert result["g10_5blanks"] == 0
    assert result["g8_3blanks"] == 0


# ---------------------------------------------------------------------------
# detectBlanks — counts triple-underscore markers
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_detect_blanks_counts_underscores() -> None:
    result = _run_node(
        "console.log(JSON.stringify({"
        "two: SF.detectBlanks('A ___ B ___ C'),"
        "zero: SF.detectBlanks('no blanks here'),"
        "seven: SF.detectBlanks('___ ___ ___ ___ ___ ___ ___'),"
        "}));"
    )
    assert result["two"] == 2
    assert result["zero"] == 0
    # Note: detectBlanks just *counts* — it's the editor's job to enforce
    # the spec's 1-6 limit when validating.
    assert result["seven"] == 7


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_detect_blanks_handles_non_string() -> None:
    """Defensive: non-string passages must return 0 instead of throwing."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "nullv: SF.detectBlanks(null),"
        "undef: SF.detectBlanks(undefined),"
        "num:   SF.detectBlanks(42),"
        "}));"
    )
    assert result["nullv"] == 0
    assert result["undef"] == 0
    assert result["num"] == 0


# ---------------------------------------------------------------------------
# Fallback smoke test — runs even without Node. Asserts the helper definitions
# are still present verbatim so a future refactor can't silently break the
# contract that the JS editor + frontend agent rely on.
# ---------------------------------------------------------------------------

def test_helpers_file_exists_and_exports_the_three_functions() -> None:
    """Static smoke test — runs without Node. Pins the public API."""
    assert HELPERS_PATH.exists(), f"Helpers file missing: {HELPERS_PATH}"
    src = HELPERS_PATH.read_text(encoding="utf-8")
    # Function definitions
    assert "function defaultModeForGrade(grade)" in src
    assert "function recommendedDistractorCount(grade, blanksCount)" in src
    assert "function detectBlanks(passage)" in src
    # Public exports — both browser (window) and Node (module.exports)
    assert "window.SentenceFillHelpers" in src
    assert "module.exports" in src
    # Grade-band thresholds (so a refactor touching the boundary fails loudly)
    assert "grade >= 8" in src
    assert "grade <= 4" in src
    assert "grade <= 7" in src
