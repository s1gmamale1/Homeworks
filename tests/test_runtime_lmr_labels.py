"""Regression tests for the LMR rubric label fix on the results scorecard.

User-flagged: the final scorecard rendered Uzbek AMR labels for every
homework regardless of subject, so language students saw "1-eksa · Konseptni
nomlash" instead of the LMR-correct "1-eksa · Grammatika to'g'riligi". The
fix made the renderer rubric-aware (consults `card.rubric`) and added LMR
i18n strings to the uz/ru/en bundles.

These tests pin:
  1. The new LMR i18n tokens are present in the served template.
  2. The renderer branches on `card.rubric === 'lmr'`.
  3. The exact pre-fix hardcode is gone from the render block.
  4. All three i18n bundles ship localized LMR axis labels.
  5. The drive-by Uzbek bundle fix sticks (no English placeholder text on
     the Uzbek `res.amr_axis*` keys).

The test reads `perfect_homework.html` directly — same convention as
`tests/test_runtime_dark_mode_coverage.py` etc. No HTTP client needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
RUNTIME = ROOT / "server" / "template" / "perfect_homework.html"


@pytest.fixture(scope="module")
def runtime_html() -> str:
    return RUNTIME.read_text(encoding="utf-8")


# ── i18n tokens are present ──────────────────────────────────────────────

def test_lmr_axis_tokens_present_in_runtime(runtime_html: str) -> None:
    """The render switch references both LMR axis i18n keys."""
    assert "res.lmr_axis1" in runtime_html
    assert "res.lmr_axis2" in runtime_html


def test_lmr_title_token_present_in_runtime(runtime_html: str) -> None:
    """The rubric-aware section title key is wired."""
    assert "res.lmr_title" in runtime_html


# ── Renderer is rubric-aware ─────────────────────────────────────────────

def test_render_branches_on_card_rubric(runtime_html: str) -> None:
    """The render block must check card.rubric to pick AMR vs LMR keys.
    Without this, every subject would fall back to AMR labels — the exact
    bug the fix addresses."""
    assert "card.rubric === 'lmr'" in runtime_html


def test_render_uses_amr_keys_for_amr_path(runtime_html: str) -> None:
    """AMR fallback path must still exist — math/science/social can't lose
    their labels because of the LMR addition."""
    assert "res.amr_axis1" in runtime_html
    assert "res.amr_axis2" in runtime_html
    assert "res.amr_title" in runtime_html


# ── Pre-fix hardcode is gone from the render block ───────────────────────

def test_old_hardcoded_uzbek_amr_label_not_in_render(runtime_html: str) -> None:
    """The exact regression: '1-eksa · Konseptni nomlash' was passed as a
    string literal to _renderAxisBar(). It must no longer be a literal
    argument — the value lives in the i18n bundle now and is fetched
    via RT(axis1Key)."""
    forbidden = "_renderAxisBar('1-eksa · Konseptni nomlash'"
    assert forbidden not in runtime_html, (
        "Hardcoded AMR axis label is back in the render block — "
        "this regresses the LMR scorecard label fix."
    )

    forbidden_axis2 = "_renderAxisBar('2-eksa · Bosqichlar izchilligi'"
    assert forbidden_axis2 not in runtime_html, (
        "Hardcoded AMR axis-2 label is back in the render block."
    )


# ── All three i18n bundles ship localized LMR labels ─────────────────────

def test_uzbek_bundle_has_localized_lmr_labels(runtime_html: str) -> None:
    """Uzbek students must see Uzbek labels, not English fallbacks."""
    # Uzbek translations of "Grammatical Accuracy" / "Lexical Quality".
    assert "Grammatika to’g’riligi" in runtime_html or \
           "Grammatika to'g'riligi" in runtime_html, \
        "Uzbek LMR axis-1 label missing"
    assert "So’z tanlash sifati" in runtime_html or \
           "So'z tanlash sifati" in runtime_html, \
        "Uzbek LMR axis-2 label missing"


def test_russian_bundle_has_localized_lmr_labels(runtime_html: str) -> None:
    """Russian translations of Grammatical Accuracy / Lexical Quality."""
    assert "Грамматическая точность" in runtime_html, \
        "Russian LMR axis-1 label missing (Грамматическая точность)"
    assert "Лексическое качество" in runtime_html, \
        "Russian LMR axis-2 label missing (Лексическое качество)"


def test_english_bundle_has_lmr_labels(runtime_html: str) -> None:
    """English bundle has the canonical labels matching the prompt + spec."""
    assert "Axis 1 — Grammatical Accuracy" in runtime_html
    assert "Axis 2 — Lexical Quality" in runtime_html


# ── Drive-by fix on Uzbek AMR placeholders ───────────────────────────────

def test_uzbek_amr_axis_keys_not_english_placeholders(runtime_html: str) -> None:
    """Pre-fix, the Uzbek bundle had English text on res.amr_axis* keys
    ("Axis 1 — Concept Identification") because the render hardcoded
    Uzbek strings and never read those keys. Now that the render reads
    them via RT(axis1Key), they must hold real Uzbek translations.
    """
    # The Uzbek bundle is uniquely identified by `lang: 'uz'` and starts
    # with 'skip.label': '⏭ Faza...'. Find that block and confirm
    # res.amr_axis1 there is NOT the English placeholder.
    uz_marker = "Faza"  # unique to the uz bundle's skip.label
    en_placeholder_axis1 = "'res.amr_axis1':         'Axis 1 — Concept Identification'"
    en_placeholder_axis2 = "'res.amr_axis2':         'Axis 2 — Process Integrity'"

    # The English placeholder string IS valid in the en bundle. We need
    # to confirm the Uzbek bundle doesn't use it. Easiest check: the
    # string appears at most once (in the en bundle), not twice.
    assert runtime_html.count(en_placeholder_axis1) <= 1, (
        "Uzbek AMR axis-1 key still holds English placeholder — "
        "should be a Uzbek translation now that RT(axis1Key) reads it."
    )
    assert runtime_html.count(en_placeholder_axis2) <= 1, (
        "Uzbek AMR axis-2 key still holds English placeholder."
    )

    # Positive check — the Uzbek translation is present somewhere.
    assert "Konseptni nomlash" in runtime_html, \
        "Uzbek AMR axis-1 translation 'Konseptni nomlash' missing"
    assert "Bosqichlar izchilligi" in runtime_html, \
        "Uzbek AMR axis-2 translation 'Bosqichlar izchilligi' missing"
