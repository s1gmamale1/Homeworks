"""Mobile viewport + safe-area-inset regression guard.

Bug history (2026-05-14, this PR):
  Both the runtime template (server/template/perfect_homework.html)
  and the builder shell (frontend/builder.html) shipped a viewport
  meta WITHOUT ``viewport-fit=cover``. On notched iPhones (X through
  16) that omission silently breaks every ``env(safe-area-inset-*)``
  call in the CSS — the values resolve to 0 instead of the inset, so
  fixed-position controls (action button, tutor FAB, builder Add FAB)
  can be covered by the home indicator or notch.

  The runtime template already references ``--safe-bottom:
  env(safe-area-inset-bottom, 0px)`` on the morphing action button
  (``.state-line`` / ``.state-pill`` / ``#nets-ai-tutor`` at bottom),
  so the dependency was real-but-mute. Builder's mobile FAB rule used
  ``bottom: 16px`` flat, so the home-indicator collision was active
  even after the viewport meta was fixed — both fixes are needed.

  Separately, ``body { min-height: 100vh }`` on app.css renders
  content below the iOS Safari URL bar when the bar is showing
  (``100vh`` is iOS's "large viewport" = URL bar collapsed). The fix
  layers a ``100dvh`` fallback after the ``100vh`` so modern Safari /
  Chrome / Firefox use the dynamic viewport while older browsers keep
  their existing behaviour.

This file pins each invariant. Static-file assertions only — no
network or browser automation. Real-device iOS Safari spot-check is
listed as a remaining-risk item in the PR description because we
can't fully simulate ``env(safe-area-inset-*)`` without a notched
device or BrowserStack.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")
BUILDER = ROOT / "frontend" / "builder.html"
APPCSS = ROOT / "frontend" / "css" / "app.css"


# ── viewport-fit=cover on both shells ────────────────────────────────


_VIEWPORT_RE = re.compile(
    r"<meta\s+name=['\"]viewport['\"][^>]*?content=['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def _viewport_content(src) -> str:
    if isinstance(src, str):
        html = src
    else:
        html = src.read_text(encoding="utf-8")
    m = _VIEWPORT_RE.search(html)
    assert m, "viewport meta tag not found"
    return m.group(1)


def test_runtime_viewport_opts_into_safe_area_cover():
    """Runtime template must declare ``viewport-fit=cover`` so that
    ``env(safe-area-inset-bottom)`` resolves to a real inset on
    notched iPhones. Without it, the action button + tutor FAB sit
    over the home indicator on iPhone X+."""
    content = _viewport_content(RUNTIME)
    assert "viewport-fit=cover" in content.replace(" ", ""), (
        "Mobile-viewport regression: server/template/perfect_homework.html "
        "<meta viewport> is missing `viewport-fit=cover`. Every "
        "env(safe-area-inset-*) call in the runtime's CSS silently "
        "resolves to 0 on notched iPhones without it — see "
        "--safe-bottom on .state-line / .state-pill / #nets-ai-tutor."
    )


def test_builder_viewport_opts_into_safe_area_cover():
    """Builder shell must also declare ``viewport-fit=cover`` so the
    mobile FAB rule (``bottom: calc(16px + env(safe-area-inset-bottom))``)
    actually clears the home indicator."""
    content = _viewport_content(BUILDER)
    assert "viewport-fit=cover" in content.replace(" ", ""), (
        "Mobile-viewport regression: frontend/builder.html <meta viewport> "
        "is missing `viewport-fit=cover`. The mobile-tier .fab-add rule "
        "in app.css uses env(safe-area-inset-bottom) which resolves to 0 "
        "without this attribute, so the home indicator can cover the "
        "Add button on iPhones."
    )


def test_viewport_preserves_user_zoom():
    """We must NOT add ``user-scalable=no`` or ``maximum-scale=1`` —
    WCAG 1.4.4 requires pinch-zoom for accessibility. Pin both files
    to keep the zoom-block out of the viewport content string."""
    for src, name in ((RUNTIME, "perfect_homework.js"), (BUILDER, "builder.html")):
        content = _viewport_content(src)
        normalised = content.replace(" ", "").lower()
        assert "user-scalable=no" not in normalised, (
            f"Mobile-viewport regression: {name} disables pinch-zoom. "
            f"WCAG 1.4.4 requires that users can zoom to at least 200% — "
            f"never ship `user-scalable=no`."
        )
        # maximum-scale=1.0 / 1 also blocks zoom on iOS even if user-scalable
        # is unset. Block both forms.
        assert not re.search(
            r"maximum-scale\s*=\s*1(?:\.0+)?(?:,|$)", normalised,
        ), (
            f"Mobile-viewport regression: {name} sets "
            f"`maximum-scale=1` which blocks zoom on iOS. Either drop it "
            f"or raise it to at least 5 (WCAG 1.4.4)."
        )


# ── Builder FAB respects safe-area-inset-bottom ──────────────────────


def test_builder_fab_uses_safe_area_inset_bottom_on_mobile():
    """The ``@media (max-width: 639px)`` block scoped to ``.fab-add``
    must include ``env(safe-area-inset-bottom`` inside its ``bottom``
    value. Otherwise iPhones with a home indicator put the FAB under
    the indicator's swipe region and taps land below the button."""
    css = APPCSS.read_text(encoding="utf-8")
    # Find the mobile media block that mentions .fab-add and walk its
    # body. The CSS file has many media queries; we anchor by selector.
    pattern = re.compile(
        r"@media\s*\([^)]*max-width\s*:\s*639px[^)]*\)\s*\{",
    )
    block_body: str | None = None
    for m in pattern.finditer(css):
        start = m.end()
        depth = 1
        for i in range(start, len(css)):
            c = css[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body = css[start:i]
                    if ".fab-add" in body:
                        block_body = body
                    break
        if block_body is not None:
            break
    assert block_body is not None, (
        "Mobile-FAB regression: no @media (max-width: 639px) block in "
        "app.css contains a `.fab-add` rule. The mobile-tier sizing "
        "+ safe-area handling for the FAB has been removed."
    )
    # Extract the .fab-add { ... } rule's body inside the media block.
    fab_rule = re.search(
        r"\.fab-add\s*\{([^}]*)\}",
        block_body,
        re.DOTALL,
    )
    assert fab_rule, (
        "Mobile-FAB regression: `.fab-add` selector exists inside the "
        "mobile media block but its rule body could not be parsed."
    )
    body = fab_rule.group(1)
    # The bottom must reference env(safe-area-inset-bottom...). We accept
    # any wrapping calc() so a future refactor can compose insets.
    assert re.search(
        r"bottom\s*:\s*[^;]*env\(\s*safe-area-inset-bottom",
        body,
    ), (
        "Mobile-FAB regression: `.fab-add` mobile rule no longer uses "
        "`env(safe-area-inset-bottom)` in its `bottom`. iPhones with "
        "a home indicator will cover the FAB."
    )


# ── body min-height uses dvh fallback after vh ───────────────────────


_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _stripped_css() -> str:
    """Read app.css with comments stripped. CSS comments can contain
    literal ``}`` characters (e.g. ``/* see body{} */``) that break the
    naive ``[^}]*`` regex below."""
    return _CSS_COMMENT_RE.sub("", APPCSS.read_text(encoding="utf-8"))


def _isolated_rules(css: str, selector_anchor: str) -> list[str]:
    """Return the bodies of every CSS rule whose selector is exactly
    ``selector_anchor`` on its own opening line. There can be multiple
    (``html, body { margin: 0 }`` then ``body { font: ... }``), so the
    caller scans the list for the one that has the property under test.
    """
    pattern = re.compile(
        r"(?:^|\n)" + re.escape(selector_anchor) + r"\s*\{",
    )
    out: list[str] = []
    for m in pattern.finditer(css):
        start = m.end()
        depth = 1
        for i in range(start, len(css)):
            c = css[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append(css[start:i])
                    break
    return out


def _rule_with_property(css: str, selector_anchor: str, prop: str) -> str:
    """Return the rule body whose selector is ``selector_anchor`` AND
    which declares ``prop:``. Errors if zero or >1 match (the latter is
    ambiguous and a sign the test needs a tighter anchor)."""
    matches = [
        body for body in _isolated_rules(css, selector_anchor)
        if re.search(rf"\b{re.escape(prop)}\s*:", body)
    ]
    assert matches, (
        f"no `{selector_anchor}` rule declares `{prop}` in app.css"
    )
    assert len(matches) == 1, (
        f"multiple `{selector_anchor}` rules declare `{prop}` — "
        f"the test anchor is ambiguous; tighten it."
    )
    return matches[0]


def test_app_css_body_min_height_has_dvh_fallback():
    """``body { min-height: 100vh; min-height: 100dvh; }`` is the
    standard iOS-safe pattern. The 100vh line is the fallback for
    browsers without dvh support; the 100dvh override (which comes
    AFTER) wins where supported. Order matters — pin both.
    """
    body = _rule_with_property(_stripped_css(), "body", "min-height")
    vh_pos = re.search(r"min-height\s*:\s*100vh\s*;", body)
    dvh_pos = re.search(r"min-height\s*:\s*100dvh\s*;", body)
    assert vh_pos, (
        "Mobile-viewport regression: `body` no longer declares "
        "`min-height: 100vh` as a fallback. Browsers without dvh "
        "support need this floor."
    )
    assert dvh_pos, (
        "Mobile-viewport regression: `body` no longer declares "
        "`min-height: 100dvh`. On iOS Safari, plain 100vh equals the "
        "URL-bar-collapsed height — content at the bottom sits below "
        "the URL bar when it is shown."
    )
    assert vh_pos.start() < dvh_pos.start(), (
        "Mobile-viewport regression: `min-height: 100dvh` must come "
        "AFTER `min-height: 100vh` in the body rule. Cascade order "
        "matters — the later declaration wins where dvh is supported."
    )


def test_app_css_builder_shell_min_height_has_dvh_fallback():
    """``.builder-shell`` is the layout ceiling for the builder editor.
    Same dvh fallback pattern as `body` so the FAB + Save controls
    don't drop below the visible viewport on iOS."""
    body = _rule_with_property(
        _stripped_css(), ".builder-shell", "min-height",
    )
    vh_pos = re.search(r"min-height\s*:\s*100vh\s*;", body)
    dvh_pos = re.search(r"min-height\s*:\s*100dvh\s*;", body)
    assert vh_pos and dvh_pos and vh_pos.start() < dvh_pos.start(), (
        "Mobile-viewport regression: `.builder-shell` no longer has the "
        "`min-height: 100vh; min-height: 100dvh;` fallback pair. "
        "Builder controls can sit below the iOS URL bar without it."
    )


# ── Runtime safe-area plumbing is consumed where it matters ──────────


def test_runtime_action_button_states_consume_safe_bottom():
    """Static anchor — the `.state-line` and `.state-pill` rules in
    perfect_homework.html must include `var(--safe-bottom)` in their
    `bottom`. The viewport-fit=cover fix is meaningless without these
    consumers; this test prevents a future refactor from removing the
    consumption side."""
    html = RUNTIME
    for selector in (".state-line", ".state-pill"):
        rule = re.search(
            re.escape(selector) + r"\s*\{([^}]*)\}",
            html,
        )
        assert rule, f"{selector!r} rule not found in runtime template"
        body = rule.group(1)
        assert re.search(
            r"bottom\s*:\s*[^;]*var\(\s*--safe-bottom",
            body,
        ), (
            f"Mobile-viewport regression: `{selector}` no longer reads "
            f"`var(--safe-bottom)` in its `bottom`. The morphing action "
            f"button can sit over the home indicator on notched iPhones."
        )
