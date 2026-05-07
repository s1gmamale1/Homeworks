"""
Regression tests for the Final Boss builder editor's pure helper functions.

Helpers live at `frontend/js/editors/_boss-helpers.js` and are exported on both
`window.BossHelpers` (browser) and `module.exports` (Node), so we can drive
them directly from a Node subprocess and assert their behaviour without
booting the whole browser surface.

Spec sources:
  FINAL_BOSS_BACKEND_PLAN.md §1 (BossMeta schema), §4b (UI deltas), §4c (helpers)
  standards/system/games/Game_Mechanics_Docs/21_Final-Boss/NETS-Final-Boss-Specification.md
    §3 (boss types), §6 (grade-banded HP), §8 (hint cost), §11 (mastery + mythical)

If `node` is unavailable (CI without Node), the static smoke tests at the
bottom assert the helper definitions are still present verbatim.
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
# Paths + Node harness (mirrors test_builder_tile_match.py)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPERS_PATH = REPO_ROOT / "frontend" / "js" / "editors" / "_boss-helpers.js"
EDITOR_PATH = REPO_ROOT / "frontend" / "js" / "editors" / "boss.js"
BUILDER_HTML_PATH = REPO_ROOT / "frontend" / "builder.html"


def _node_available() -> bool:
    return shutil.which("node") is not None


def _run_node(script: str) -> dict:
    """Run a Node script that loads the helpers and prints a JSON dict on stdout."""
    if not _node_available():
        pytest.skip("node binary not on PATH; falling back to regex smoke test")
    helpers_url = HELPERS_PATH.as_posix()
    full = (
        f"const BH = require({json.dumps(helpers_url)});\n"
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
        f"node exited with {proc.returncode}\n"
        f"stderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"
    )
    out = proc.stdout.strip().splitlines()[-1]
    return json.loads(out)


# ---------------------------------------------------------------------------
# gradeBandFromGrade — bin grades into spec §6 bands
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_grade_band_from_grade_g1_4() -> None:
    """Grades 1-4 map to g1_4 (spec §6 — 50 HP starting band)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g2: BH.gradeBandFromGrade(2),"
        "g4: BH.gradeBandFromGrade(4),"
        "g1: BH.gradeBandFromGrade(1),"
        "}));"
    )
    assert result["g1"] == "g1_4"
    assert result["g2"] == "g1_4"
    assert result["g4"] == "g1_4"


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_grade_band_from_grade_g5() -> None:
    """Grade 5 has its own band (transition between primary and middle)."""
    result = _run_node(
        "console.log(JSON.stringify({g5: BH.gradeBandFromGrade(5)}));"
    )
    assert result["g5"] == "g5"


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_grade_band_from_grade_g6_8() -> None:
    """Grades 6-8 map to g6_8 (middle-school band)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g6: BH.gradeBandFromGrade(6),"
        "g7: BH.gradeBandFromGrade(7),"
        "g8: BH.gradeBandFromGrade(8),"
        "}));"
    )
    assert result["g6"] == "g6_8"
    assert result["g7"] == "g6_8"
    assert result["g8"] == "g6_8"


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_grade_band_from_grade_g9_11() -> None:
    """Grades 9-11 map to g9_11 (upper band — 150 HP)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g9: BH.gradeBandFromGrade(9),"
        "g10: BH.gradeBandFromGrade(10),"
        "g11: BH.gradeBandFromGrade(11),"
        "}));"
    )
    assert result["g9"] == "g9_11"
    assert result["g10"] == "g9_11"
    assert result["g11"] == "g9_11"


# ---------------------------------------------------------------------------
# defaultHpForGradeBand — spec §6 starting HP ladder
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_default_hp_for_grade_band() -> None:
    """50 / 100 / 100 / 150 across the four bands per spec §6."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g1_4: BH.defaultHpForGradeBand('g1_4'),"
        "g5: BH.defaultHpForGradeBand('g5'),"
        "g6_8: BH.defaultHpForGradeBand('g6_8'),"
        "g9_11: BH.defaultHpForGradeBand('g9_11'),"
        "fallback: BH.defaultHpForGradeBand('unknown'),"
        "}));"
    )
    assert result["g1_4"] == 50
    assert result["g5"] == 100
    assert result["g6_8"] == 100
    assert result["g9_11"] == 150
    # Fallback to 100 for unknown bands (defensive default).
    assert result["fallback"] == 100


# ---------------------------------------------------------------------------
# defaultHintCostForGradeBand — spec §8 hint cost ladder
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_default_hint_cost_for_grade_band() -> None:
    """+5 / +10 / +10 / +15 HP regen per hint per spec §8."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "g1_4: BH.defaultHintCostForGradeBand('g1_4'),"
        "g5: BH.defaultHintCostForGradeBand('g5'),"
        "g6_8: BH.defaultHintCostForGradeBand('g6_8'),"
        "g9_11: BH.defaultHintCostForGradeBand('g9_11'),"
        "}));"
    )
    assert result["g1_4"] == 5
    assert result["g5"] == 10
    assert result["g6_8"] == 10
    assert result["g9_11"] == 15


# ---------------------------------------------------------------------------
# defaultAttemptsForBossType — spec §3 attempts policy
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_default_attempts_basic_sub_is_2() -> None:
    """Sub Boss on Basic tier → 2 attempts default (spec §3)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "v: BH.defaultAttemptsForBossType('sub', 'basic'),"
        "}));"
    )
    assert result["v"] == 2


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_default_attempts_premium_sub_is_null() -> None:
    """Sub Boss on Premium tier → unlimited (null sentinel for None on Pydantic side)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "v: BH.defaultAttemptsForBossType('sub', 'premium'),"
        "}));"
    )
    assert result["v"] is None


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_default_attempts_big_or_mythical_always_1() -> None:
    """Big and Mythical bosses are always 1 attempt regardless of tier (spec §3)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "big_basic: BH.defaultAttemptsForBossType('big', 'basic'),"
        "big_premium: BH.defaultAttemptsForBossType('big', 'premium'),"
        "myth_basic: BH.defaultAttemptsForBossType('mythical', 'basic'),"
        "myth_premium: BH.defaultAttemptsForBossType('mythical', 'premium'),"
        "}));"
    )
    assert result["big_basic"] == 1
    assert result["big_premium"] == 1
    assert result["myth_basic"] == 1
    assert result["myth_premium"] == 1


# ---------------------------------------------------------------------------
# bossTypeOptions — premium gating (UI dropdown contents)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_boss_type_options_premium_returns_all_3() -> None:
    """Premium tier exposes sub + big + mythical (3 options)."""
    result = _run_node(
        "console.log(JSON.stringify({v: BH.bossTypeOptions('premium')}));"
    )
    assert result["v"] == ["sub", "big", "mythical"]


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_boss_type_options_basic_only_sub() -> None:
    """Basic tier collapses to ['sub'] only — premium gates Big and Mythical."""
    result = _run_node(
        "console.log(JSON.stringify({v: BH.bossTypeOptions('basic')}));"
    )
    assert result["v"] == ["sub"]


# ---------------------------------------------------------------------------
# pisaLevelOptions / bloomLevelOptions — advisory dropdown enums (spec §1)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_pisa_level_options_returns_6() -> None:
    """L1-L6 PISA levels per spec §1."""
    result = _run_node(
        "console.log(JSON.stringify({v: BH.pisaLevelOptions()}));"
    )
    assert result["v"] == ["L1", "L2", "L3", "L4", "L5", "L6"]


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_bloom_level_options_returns_4() -> None:
    """Bloom upper-tier verbs apply/analyze/evaluate/create per spec §1."""
    result = _run_node(
        "console.log(JSON.stringify({v: BH.bloomLevelOptions()}));"
    )
    assert result["v"] == ["apply", "analyze", "evaluate", "create"]


# ---------------------------------------------------------------------------
# clearHintsForMythical — spec §11 zero-hints enforcement helper
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_clear_hints_for_mythical() -> None:
    """Each question's hints[] array is reset to [] (other fields preserved)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "v: BH.clearHintsForMythical([{q:'Q1', hints:['a','b']}, {q:'Q2', hints:['c'], dmg:20}]),"
        "}));"
    )
    out = result["v"]
    assert len(out) == 2
    assert out[0]["q"] == "Q1"
    assert out[0]["hints"] == []
    assert out[1]["q"] == "Q2"
    assert out[1]["hints"] == []
    # Other fields preserved.
    assert out[1]["dmg"] == 20


@pytest.mark.skipif(not _node_available(), reason="node not installed")
def test_clear_hints_for_mythical_handles_undefined() -> None:
    """Defensive: null / undefined / non-array input → empty array (no throw)."""
    result = _run_node(
        "console.log(JSON.stringify({"
        "nul: BH.clearHintsForMythical(null),"
        "undef: BH.clearHintsForMythical(undefined),"
        "obj: BH.clearHintsForMythical({}),"
        "num: BH.clearHintsForMythical(42),"
        "}));"
    )
    assert result["nul"] == []
    assert result["undef"] == []
    assert result["obj"] == []
    assert result["num"] == []


# ---------------------------------------------------------------------------
# Static smoke tests — run without Node. Pin the public API + integration
# wiring so a future refactor breaking the contract fails loudly.
# ---------------------------------------------------------------------------

def test_helpers_file_exists_and_exports_the_public_api() -> None:
    """Pin _boss-helpers.js public API + dual export (browser + Node)."""
    assert HELPERS_PATH.exists(), f"Helpers file missing: {HELPERS_PATH}"
    src = HELPERS_PATH.read_text(encoding="utf-8")
    # Function definitions
    assert "function gradeBandFromGrade(grade)" in src
    assert "function defaultHpForGradeBand(band)" in src
    assert "function defaultHintCostForGradeBand(band)" in src
    assert "function defaultAttemptsForBossType(bossType, tier)" in src
    assert "function bossTypeOptions(tier)" in src
    assert "function pisaLevelOptions()" in src
    assert "function bloomLevelOptions()" in src
    assert "function clearHintsForMythical(questions)" in src
    # Public exports — both browser (window) and Node (module.exports)
    assert "window.BossHelpers" in src
    assert "module.exports" in src
    # Spec-tied constants — fail loudly if the ladder shifts without spec update
    assert "g1_4: 50" in src
    assert "g9_11: 150" in src
    assert "g1_4: 5" in src
    assert "g9_11: 15" in src


def test_boss_editor_uses_4_arg_signature_and_meta_helpers() -> None:
    """boss.js render() upgraded to 4-arg context signature + integrates meta + per-q metadata."""
    assert EDITOR_PATH.exists(), f"Boss editor missing: {EDITOR_PATH}"
    src = EDITOR_PATH.read_text(encoding="utf-8")
    # 4-arg signature with default-empty context
    assert "function render(container, data, onChange, context = {})" in src
    # Reads context fields per plan §4a
    assert "context.grade" in src
    assert "context.tier" in src
    # Boss-meta wiring
    assert "boss_meta" in src
    assert "BOSS_TYPES" in src or "boss_type" in src
    assert "Enable AI Dynamic Boss Questions" in src
    assert "use_dynamic_boss" in src
    assert "js-meta-dynamic" in src
    assert "Fallback Static Boss Questions" in src
    assert "Boss questions map to <strong>BOSS_QUESTIONS</strong>" in src
    assert "content.boss_questions" in Path(__file__).resolve().parents[1].joinpath("frontend/js/builder.js").read_text(encoding="utf-8")
    assert "use_dynamic_boss: meta.use_dynamic_boss === true" in src
    assert "sanitizeQuestionForEmit" in src
    assert "out.pisa_level = PISA_LEVELS.includes(out.pisa_level) ? out.pisa_level : null" in src
    assert "out.bloom_level = BLOOM_LEVELS.includes(out.bloom_level) ? out.bloom_level : null" in src
    # Per-question metadata fields (spec §1 additive schema)
    assert "pisa_level" in src
    assert "bloom_level" in src
    assert "hint_cost_per_use" in src
    # Premium gates
    assert 'tier !== "premium"' in src or "tier !== 'premium'" in src
    # Mythical hint-clear side effect
    assert "mythical" in src.lower()
    # Editor still registers under the existing key (no migration)
    assert "window.Editors.boss = { render }" in src


def test_builder_html_loads_boss_helpers_with_cache_bust() -> None:
    """builder.html includes _boss-helpers.js with the ?v=__VERSION__ token."""
    assert BUILDER_HTML_PATH.exists(), f"builder.html missing: {BUILDER_HTML_PATH}"
    src = BUILDER_HTML_PATH.read_text(encoding="utf-8")
    assert "_boss-helpers.js" in src, "builder.html must load _boss-helpers.js"
    # Cache-bust token must be present on the same line as the helper script tag.
    helper_line = next(
        (line for line in src.splitlines() if "_boss-helpers.js" in line), ""
    )
    assert "?v=__VERSION__" in helper_line, (
        "_boss-helpers.js script tag must carry ?v=__VERSION__ for cache-busting "
        f"(line was: {helper_line!r})"
    )
