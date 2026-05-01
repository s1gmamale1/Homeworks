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


def test_run_quote_sequence_uniform_body_first_order():
    """User-locked 2026-05-01: both fact and quote paths render body
    FIRST and label/author chip BELOW. No type-conditional order swap."""
    html = _read(RUNTIME)
    block_match = re.search(
        r"function runQuoteSequence\s*\(\)\s*\{(?P<body>.*?)\n        \}",
        html,
        re.DOTALL,
    )
    assert block_match, "runQuoteSequence body not found"
    body = block_match.group("body")

    # Type detection still present — author label content still depends on type.
    assert "const isFact = q.type !== 'quote'" in body, (
        "function must branch on type to decide author label content"
    )

    # No order swap based on isFact — both paths render uniform.
    assert "if (isFact) {" not in body, (
        "fact and quote paths must render body-first uniformly; no order swap"
    )

    # The --top modifier is gone — both paths use the same chip styling.
    assert "quote-author-chip--top" not in body, (
        "facts no longer use the --top chip modifier; chip sits below body for both"
    )

    # Both append calls present — verifying the body-first sequence.
    assert "item.appendChild(textLine);" in body
    assert "item.appendChild(chipLine);" in body


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
    # The fact label must never leak into the quote author position.
    assert "isFact ? gateLabel : (q.a || gateLabel)" not in body, (
        "the fact-label gateLabel must NOT be the fallback for quote authors"
    )


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


def test_break_card_uniform_column_reverse():
    """Both fact and quote variants render body first, kicker below.
    Was a `.break-card--quote` modifier; now the base `.break-card`
    declares `flex-direction: column-reverse` so the rule applies
    uniformly without a JS-driven class toggle."""
    html = _read(RUNTIME)
    rule = re.search(r"\.break-card\s*\{(?P<body>[^}]*)\}", html)
    assert rule, "missing .break-card rule"
    body = rule.group("body")
    assert "flex-direction: column-reverse" in body, (
        ".break-card must declare column-reverse so the kicker sits below "
        "the body for BOTH fact and quote variants"
    )

    # Default kicker margin matches the new layout (gap above, not below).
    kicker = re.search(r"\.break-kicker\s*\{(?P<body>[^}]*)\}", html)
    assert kicker, "missing .break-kicker rule"
    assert "margin-top: 14px" in kicker.group("body")


def test_break_text_uses_body_color_not_accent():
    """User-flagged 2026-05-01: `.break-text` was rendering blue with
    a glow — wrong. It should match the runtime body text (dark navy
    in light, light text in dark) without any accent text-shadow."""
    html = _read(RUNTIME)
    rule = re.search(r"\.break-text\s*\{(?P<body>[^}]*)\}", html)
    assert rule, "missing .break-text rule"
    body = rule.group("body")
    assert "color: var(--text)" in body, (
        ".break-text body must use --text not --accent"
    )
    assert "var(--accent-glow)" not in body, (
        ".break-text must not carry the accent text-shadow glow"
    )


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
