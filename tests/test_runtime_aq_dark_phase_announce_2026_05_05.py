"""Visual-polish regressions: AQ tier headline dark-mode + phase
announcement card overflow on long localized labels.

Bug AQ-1
--------
The Adaptive Quiz tier headline used three light-mode hex colors
(deep green ``#2d7a2f``, mustard ``#b3791f``, deep red ``#a02020``)
that turned muddy / illegible against the slate dark surface. The
existing AQ dark-mode coverage (~L6587-6655) handled the topbar,
cards, status pill, and result box but skipped these tier headlines.
Fix: pair each ``.aq-tier-headline.tier-{easy,medium,hard}`` with a
``[data-theme="dark"]`` override that uses a brighter green / amber
/ red matching the existing dark palette.

Bug PA-1
--------
The phase announcement card (``.phase-intro-card`` /
``.phase-intro-text``) had a fixed 460px width, no ``max-height``, no
``box-sizing``, and the text used a fixed ``font-size: 22px`` with
no ``overflow-wrap`` or responsive breakpoints. Russian labels like
"Заключительный вызов" and English "Real-Life Challenge" could
overflow horizontally or get clipped vertically on short viewports.
Fix: bound the card vertically (``max-height: min(72vh, 360px)``),
add ``box-sizing: border-box``, switch the text to
``font-size: clamp(17px, 5.4vw, 22px)`` with ``overflow-wrap:
anywhere`` + ``hyphens: auto``, and add two responsive tiers
(<=480px / <=370px) without breaking the centering transform or
``phaseIntroFadeOut`` keyframe.

These tests pin both fixes so a future "let me clean up the CSS"
PR can't regress either bug.
"""

from __future__ import annotations

import re
from pathlib import Path

_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _css_block(source: str, selector: str) -> str:
    """Return the body of the first CSS rule matching ``selector``."""
    pattern = re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}"
    match = re.search(pattern, source)
    assert match, f"missing CSS block for {selector!r}"
    return match.group("body")


def _find_media_blocks(template: str, query: str) -> list[str]:
    """Return ALL bodies of ``@media (...) { ... }`` matching ``query``.

    Brace-balanced — there can be multiple ``@media`` blocks with the same
    query (e.g. one for Tile Match, one for Puzzle Lock, one for the new
    phase-intro card).
    """
    needle = f"@media {query} {{"
    blocks: list[str] = []
    pos = 0
    while True:
        idx = template.find(needle, pos)
        if idx < 0:
            return blocks
        depth = 0
        started = False
        end = -1
        for i in range(idx + len(needle) - 1, len(template)):
            ch = template[i]
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    end = i + 1
                    break
        if end < 0:
            return blocks
        blocks.append(template[idx:end])
        pos = end


def _hex_brightness(hex_color: str) -> int:
    """Crude perceived-brightness sum (R+G+B) for a 6-digit hex color.

    Used only to assert that the dark override is *brighter* than the
    light hex it replaces — exact luminance math isn't needed.
    """
    h = hex_color.lstrip("#")
    assert len(h) == 6, f"expected 6-digit hex, got {hex_color!r}"
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return r + g + b


# ---------------------------------------------------------------------------
# Bug AQ-1: tier headline dark-mode overrides
# ---------------------------------------------------------------------------


def _extract_dark_tier_color(tier: str) -> str:
    """Pull the hex color for ``[data-theme="dark"] .aq-tier-headline.tier-{tier}``."""
    selector = f'[data-theme="dark"] .aq-tier-headline.tier-{tier}'
    body = _css_block(TEMPLATE, selector)
    match = re.search(r"color:\s*(#[0-9a-fA-F]{6})", body)
    assert match, (
        f"{selector} must declare a `color` (hex) — without it the dark "
        f"override is a no-op and the muddy light hex stays in dark mode"
    )
    return match.group(1).lower()


def test_aq_tier_easy_has_dark_override():
    """`[data-theme="dark"] .aq-tier-headline.tier-easy` must exist
    and use a brighter green than the light ``#2d7a2f``."""
    dark_color = _extract_dark_tier_color("easy")
    light_brightness = _hex_brightness("#2d7a2f")
    dark_brightness = _hex_brightness(dark_color)
    assert dark_brightness > light_brightness, (
        f"dark tier-easy color {dark_color} is not brighter than the light "
        f"#2d7a2f — the muddy-on-slate bug returns. Use a green like "
        f"#86efac or #5bb85d that matches the .aq-status-pill.is-correct "
        f"palette."
    )


def test_aq_tier_medium_has_dark_override():
    """`[data-theme="dark"] .aq-tier-headline.tier-medium` must exist
    and use a brighter amber than the light ``#b3791f``."""
    dark_color = _extract_dark_tier_color("medium")
    light_brightness = _hex_brightness("#b3791f")
    dark_brightness = _hex_brightness(dark_color)
    assert dark_brightness > light_brightness, (
        f"dark tier-medium color {dark_color} is not brighter than the "
        f"light #b3791f. Use an amber like #fcd34d or #fbbf24 that "
        f"matches the existing dark warning treatment."
    )


def test_aq_tier_hard_has_dark_override():
    """`[data-theme="dark"] .aq-tier-headline.tier-hard` must exist
    and use a brighter red than the light ``#a02020``."""
    dark_color = _extract_dark_tier_color("hard")
    light_brightness = _hex_brightness("#a02020")
    dark_brightness = _hex_brightness(dark_color)
    assert dark_brightness > light_brightness, (
        f"dark tier-hard color {dark_color} is not brighter than the "
        f"light #a02020. Use a red like #fca5a5 or #f87171 that matches "
        f".aq-status-pill.is-wrong / .aq-result-box.wrong palette."
    )


# ---------------------------------------------------------------------------
# Bug PA-1: phase announcement card overflow
# ---------------------------------------------------------------------------


def _phase_intro_card_body() -> str:
    """Return the body of the base ``.phase-intro-card`` rule (not the
    ``.show`` variant, not the ``@media`` overrides)."""
    return _css_block(TEMPLATE, ".phase-intro-card")


def _phase_intro_text_body() -> str:
    return _css_block(TEMPLATE, ".phase-intro-text")


def test_phase_intro_card_has_max_height():
    """``.phase-intro-card`` must declare a ``max-height`` so long
    localized labels can't push the card off-screen on short viewports."""
    body = _phase_intro_card_body()
    assert "max-height" in body, (
        ".phase-intro-card has no max-height — long Russian labels like "
        "'Заключительный вызов' will push the card past the viewport "
        "on short screens. Bound it with `max-height: min(72vh, 360px)`."
    )
    # Confirm it uses the recommended bound (or a sane equivalent).
    assert "72vh" in body or "vh" in body, (
        ".phase-intro-card max-height should use a viewport-relative cap "
        "so it stays bounded across heights, not a fixed pixel value alone."
    )


def test_phase_intro_card_has_box_sizing_border_box():
    """``box-sizing: border-box`` is required so the 28px padding doesn't
    push the card past ``min(84vw, 460px)``."""
    body = _phase_intro_card_body()
    assert "box-sizing" in body and "border-box" in body, (
        ".phase-intro-card must declare `box-sizing: border-box` — without "
        "it, the 28px padding adds onto the 460px width and the card "
        "overflows narrow viewports horizontally"
    )


def test_phase_intro_card_keeps_centering_transform():
    """Centering transform ``translate(-50%, -50%)`` must remain — the
    fix must not break centering, and the ``phaseIntroFadeOut`` keyframe
    relies on this initial transform."""
    body = _phase_intro_card_body()
    assert "translate(-50%, -50%)" in body, (
        ".phase-intro-card lost its `translate(-50%, -50%)` centering. "
        "The phaseIntroFadeOut keyframe interpolates from this exact "
        "transform; without it the card jumps off-center during fade-out."
    )


def test_phase_intro_text_has_overflow_wrap():
    """``.phase-intro-text`` must declare ``overflow-wrap`` so long
    Russian / English labels wrap inside the card instead of overflowing."""
    body = _phase_intro_text_body()
    assert "overflow-wrap" in body, (
        ".phase-intro-text has no `overflow-wrap` — labels like "
        "'Real-Life Challenge' or 'Заключительный вызов' will overflow "
        "the 460px card on narrow widths instead of wrapping."
    )
    # Must allow aggressive breaking — `anywhere` (or `break-word`) is
    # the only setting that handles long unbroken Cyrillic words.
    assert "anywhere" in body or "break-word" in body, (
        ".phase-intro-text overflow-wrap must be `anywhere` (preferred) "
        "or `break-word` so long unbroken words still wrap"
    )


def test_phase_intro_text_uses_clamp_font_size():
    """``.phase-intro-text`` font-size must use ``clamp()`` — fixed 22px
    is the bug we're fixing. Pin the contract so a future revert is caught."""
    body = _phase_intro_text_body()
    assert "font-size:" in body, ".phase-intro-text has no font-size declared"
    assert "clamp(" in body, (
        ".phase-intro-text font-size must use clamp() — a fixed 22px "
        "(the pre-fix value) clips long labels on narrow viewports. "
        "Use `clamp(17px, 5.4vw, 22px)` so the text scales between "
        "phone and desktop widths."
    )


def test_phase_intro_text_has_compact_line_height():
    """Line-height must be tightened from 1.45 → 1.4 so the wrapped
    text doesn't stack tall enough to clip vertically inside the
    ``max-height: min(72vh, 360px)`` bound on short viewports."""
    body = _phase_intro_text_body()
    match = re.search(r"line-height:\s*([0-9.]+)", body)
    assert match, ".phase-intro-text has no line-height declared"
    line_height = float(match.group(1))
    assert line_height <= 1.4 + 1e-9, (
        f".phase-intro-text line-height is {line_height} — should be "
        f"<= 1.4 so wrapped text fits in the bounded card on narrow "
        f"viewports. Pre-fix was 1.45."
    )


def test_phase_intro_card_has_responsive_breakpoints():
    """Two ``@media`` tiers must address ``.phase-intro-card``: one at
    ``max-width <= 480px`` (tighten padding + min-height + border-radius)
    and another at ``max-width <= 370px`` (even tighter for narrow phones).

    Without these the card uses desktop padding (28px 24px) on phone-
    sized viewports and the fixed-px border radius looks oversized.
    """
    block_480 = "\n".join(_find_media_blocks(TEMPLATE, "(max-width: 480px)"))
    block_370 = "\n".join(_find_media_blocks(TEMPLATE, "(max-width: 370px)"))
    assert ".phase-intro-card" in block_480, (
        "no `@media (max-width: 480px)` rule targets `.phase-intro-card`. "
        "Phone-width viewports will keep the desktop 28px padding and "
        "28px border-radius."
    )
    assert ".phase-intro-card" in block_370, (
        "no `@media (max-width: 370px)` rule targets `.phase-intro-card`. "
        "True mobile-portrait widths need an even tighter padding tier."
    )


def test_phase_intro_fade_out_keyframe_still_intact():
    """Sanity guard: the ``phaseIntroFadeOut`` keyframe must still exist
    and must still interpolate the centering transform — the comment at
    ~L1540-1547 explicitly warns against breaking this."""
    assert "@keyframes phaseIntroFadeOut" in TEMPLATE, (
        "phaseIntroFadeOut keyframe was removed. The phase-intro card "
        "fade-out depends on it — without it the card snaps off-screen "
        "instead of fading."
    )
    # Find the keyframe body and confirm it preserves the centering.
    kf_idx = TEMPLATE.find("@keyframes phaseIntroFadeOut")
    kf_body = TEMPLATE[kf_idx : kf_idx + 400]
    assert "translate(-50%, -50%)" in kf_body, (
        "phaseIntroFadeOut keyframe lost its `translate(-50%, -50%)` "
        "starting transform. The card will jump off-center during fade-out."
    )
