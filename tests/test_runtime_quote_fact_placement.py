"""Quote/fact label placement regression tests.

Final rule the user pinned down:
- Facts use a "Bilarmidingiz?" pill ABOVE the content (label heading).
- Quotes use the author pill BELOW the content (attribution line).
- Same rule applies on the opening gate quote (`runQuoteSequence`)
  and on the mid-homework break card (`renderBreakQuote`).

Backend slot sequencing (quote-before-preview, fact-after-flashcards,
~30%-spaced interstitials) lives in server/services/quotes.py and is
covered by Codex's PR #66 tests; this file only checks the runtime
side — placement, classes, and that the helpers stay deduped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
RUNTIME = ROOT / "server" / "template" / "perfect_homework.html"
QUOTES_DB = ROOT / "server" / "data" / "quotes_database.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Opening gate quote / fact (Phase 0) ──────────────────────────────


def test_run_quote_sequence_branches_on_type():
    html = _read(RUNTIME)
    block_match = re.search(
        r"function runQuoteSequence\s*\(\)\s*\{(?P<body>.*?)\n        \}",
        html,
        re.DOTALL,
    )
    assert block_match, "runQuoteSequence body not found"
    body = block_match.group("body")

    # Type detection — facts go above, quotes go below.
    assert "const isFact = q.type !== 'quote'" in body, (
        "function must branch on type to decide chip placement"
    )

    # Both append orderings must be present (one for each branch).
    assert "if (isFact) {" in body
    assert "item.appendChild(chipLine);" in body
    assert "item.appendChild(textLine);" in body

    # Facts get the --top modifier so the chip's vertical margin flips.
    assert "quote-author-chip--top" in body


def test_run_quote_sequence_drops_emoji_for_facts():
    """The leading 💡 emoji prefix on facts duplicated the
    Bilarmidingiz? label and looked noisy. Confirm facts no longer
    render an icon."""
    html = _read(RUNTIME)
    block_match = re.search(
        r"function runQuoteSequence\s*\(\)\s*\{(?P<body>.*?)\n        \}",
        html,
        re.DOTALL,
    )
    body = block_match.group("body")
    # Either the icon is empty for facts, or it's a quote-only ❝.
    assert "isFact ? '' : '❝'" in body or 'isFact ? "" : "❝"' in body, (
        "facts must render with no leading icon since the label pill is the heading"
    )


def test_gate_quote_card_keeps_body_text_visible():
    """The gate quote card must show the text body under/above the label.

    A stale branch hid `.quote-text-line`, leaving only the Bilarmidingiz?
    pill floating in an empty card. Keep the restored glass card layout pinned.
    """
    html = _read(RUNTIME)
    rule = re.search(
        r"\.quote-card \.quote-text-line\s*\{(?P<body>[^}]*)\}",
        html,
        re.DOTALL,
    )
    assert rule, "missing .quote-card .quote-text-line rule"
    body = rule.group("body")
    assert "display: none" not in body, (
        "gate quote text must stay visible; do not hide .quote-text-line"
    )
    assert "color: var(--text)" in body, (
        "gate quote text should use the runtime body text color"
    )

    item_rule = re.search(
        r"\.quote-card \.quote-item\s*\{(?P<body>[^}]*)\}",
        html,
        re.DOTALL,
    )
    assert item_rule, "missing .quote-card .quote-item layout rule"
    item_body = item_rule.group("body")
    assert "display: flex" in item_body
    assert "align-items: center" in item_body


def test_run_quote_sequence_does_not_use_fact_label_as_quote_author():
    html = _read(RUNTIME)
    block_match = re.search(
        r"function runQuoteSequence\s*\(\)\s*\{(?P<body>.*?)\n        \}",
        html,
        re.DOTALL,
    )
    body = block_match.group("body")
    assert "isFact ? gateLabel : (q.a || gateLabel)" not in body
    assert "isFact ? gateLabel : (q.a || 'Iqtibos')" in body


# ── Mid-homework break card ──────────────────────────────────────────


def test_render_break_quote_is_not_duplicated():
    """Codex's earlier PR declared the function twice back-to-back.
    Two definitions are dead code; the second silently shadows the
    first. Make sure we have exactly one."""
    html = _read(RUNTIME)
    matches = re.findall(r"^\s*function renderBreakQuote\s*\(", html, re.MULTILINE)
    assert len(matches) == 1, (
        f"renderBreakQuote should be defined exactly once, found {len(matches)}"
    )


def test_render_break_quote_flips_kicker_for_quotes():
    html = _read(RUNTIME)
    block_match = re.search(
        r"function renderBreakQuote\s*\([^)]*\)\s*\{(?P<body>.*?)\n        \}",
        html,
        re.DOTALL,
    )
    assert block_match, "renderBreakQuote body not found"
    body = block_match.group("body")

    assert "const isQuote = q.type === 'quote'" in body, (
        "renderBreakQuote must branch on type"
    )
    assert "card.classList.toggle('break-card--quote', isQuote)" in body, (
        "the function must toggle the .break-card--quote class so the "
        "kicker visually flips below the text via flex-direction"
    )


def test_break_card_quote_modifier_uses_column_reverse():
    html = _read(RUNTIME)
    rule = re.search(
        r"\.break-card--quote\s*\{(?P<body>[^}]*)\}", html
    )
    assert rule, "missing .break-card--quote rule"
    body = rule.group("body")
    assert "flex-direction: column-reverse" in body

    inner = re.search(
        r"\.break-card--quote \.break-kicker\s*\{(?P<body>[^}]*)\}", html
    )
    assert inner, "missing .break-card--quote .break-kicker rule"
    inner_body = inner.group("body")
    assert "margin-top: 14px" in inner_body
    assert "margin-bottom: 0" in inner_body


def test_quote_author_chip_top_modifier_swaps_margins():
    html = _read(RUNTIME)
    rule = re.search(
        r"\.quote-author-chip--top\s*\{(?P<body>[^}]*)\}", html
    )
    assert rule, "missing .quote-author-chip--top rule"
    body = rule.group("body")
    assert "margin-top: 0" in body
    assert "margin-bottom: 14px" in body


# ── Scholar / historical names use Uzbek-Latin orthography ────────────


def test_scholar_names_use_uzbek_latin_orthography():
    """Quote DB authors must use the Uzbek-Latin form expected by the
    user. Old anglicized spellings like "Babur" / "Ulugbek" /
    "al-Khwarizmi" should never come back."""
    data = json.loads(QUOTES_DB.read_text(encoding="utf-8"))
    authors = {q.get("author") for q in data if q.get("type") == "quote"}

    expected_present = {
        "Abu Ali ibn Sino",
        "Abu Rayhon Beruniy",
        "Abu Nasr Forobiy",
        "Alisher Navoiy",
        "Mirzo Ulug'bek",
        "Muhammad al-Xorazmiy",
        "Zahiriddin Muhammad Bobur",
    }
    missing = expected_present - authors
    assert not missing, f"expected author spellings missing from DB: {missing}"

    forbidden = {
        "Abu Ali ibn Sina",
        "Abu Rayhan al-Biruni",
        "Al-Farabi",
        "Alisher Navoi",
        "Mirzo Ulugbek",
        "Muhammad al-Khwarizmi",
        "Zahiriddin Muhammad Babur",
    }
    leaked = forbidden & authors
    assert not leaked, (
        f"old anglicized spellings leaked back into the quote DB: {leaked}"
    )


def test_fact_default_label_is_bilarmidingiz():
    """The opening fact pill must read 'Bilarmidingiz?' when the row
    has no explicit author. (Codex's quote DB sets every fact's
    author to that string already; this is a defensive check that the
    runtime falls back the same way if a future row leaves it blank.)"""
    html = _read(RUNTIME)
    block_match = re.search(
        r"function renderBreakQuote\s*\([^)]*\)\s*\{(?P<body>.*?)\n        \}",
        html,
        re.DOTALL,
    )
    body = block_match.group("body")
    assert "'Bilarmidingiz?'" in body, (
        "renderBreakQuote must keep 'Bilarmidingiz?' as the fact default label"
    )


# ── Apple-glass port (Image #11 reference) ────────────────────────────


def test_quote_card_drops_linen_repeating_gradient():
    """PR #128's repeating-linear-gradient linen layer was removed (user-flagged "weird inner light")."""
    src = (Path("server/template/perfect_homework.html")).read_text(encoding="utf-8")
    import re
    block = re.search(r"\.quote-card\s*\{[^}]*\}", src, re.S).group(0)
    assert "repeating-linear-gradient" not in block, (
        "quote-card no longer ships the linen-texture 3rd layer — keep this assertion"
    )


def test_quote_card_uses_premium_radius():
    src = (Path("server/template/perfect_homework.html")).read_text(encoding="utf-8")
    import re
    block = re.search(r"\.quote-card\s*\{[^}]*\}", src, re.S).group(0)
    assert "border-radius: 34px" in block


def test_quote_card_uses_explicit_blur_46():
    src = (Path("server/template/perfect_homework.html")).read_text(encoding="utf-8")
    import re
    block = re.search(r"\.quote-card\s*\{[^}]*\}", src, re.S).group(0)
    assert "blur(46px)" in block


def test_quote_text_line_has_premium_letter_spacing():
    src = (Path("server/template/perfect_homework.html")).read_text(encoding="utf-8")
    import re
    block = re.search(r"\.quote-card \.quote-text-line\s*\{[^}]*\}", src, re.S).group(0)
    assert "letter-spacing" in block
