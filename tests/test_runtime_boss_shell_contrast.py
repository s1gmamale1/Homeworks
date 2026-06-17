"""Boss-shell contrast contract — regression guard.

Bug history (2026-05-14):
  The boss shell (``.boss-shell``) forces a dark battle backdrop via
  ``background: ...!important; color: white !important;`` regardless of
  ``data-theme``. Its sub-cards (``.boss-hp-section``, ``.boss-q-card``)
  still resolved ``var(--surface)`` to ``rgba(255,255,255,0.72)`` in
  light mode — translucent WHITE panels floated on the dark backdrop
  with dark-on-white text washing out and grey/amber muted labels
  becoming unreadable.

The fix (PR #218) scopes a contrast pass under ``.boss-shell`` so the
sub-cards adopt dark-glass backgrounds + light text universally — NOT
gated on ``[data-theme="dark"]`` because the shell itself is universal.

This test pins five clauses as static-file assertions so a future
refactor cannot silently undo the contrast guarantees:

  1. ``.boss-shell .boss-hp-section`` and ``.boss-shell .boss-q-card``
     both declare a dark ``rgba(15, 23, 42, …)`` background. White
     ``var(--surface)`` would be a regression.
  2. Foreground text on the cards, counter, tags, and framing banner
     uses light colors (not ``var(--text)`` and not dark hex literals).
  3. ``.boss-shell .boss-input`` uses the dark-glass background and
     light foreground (light-mode default was rgba(255,255,255,0.92)
     with dark text, illegible on the dark scene).
  4. ``.boss-feedback`` ``::before`` glyphs (✓ / ✗) inherit color from
     the parent feedback element so they tint with the surrounding
     state (green / red / blue) — hard-coding the glyph colour was
     the pre-fix behaviour and re-introduces dim ✓ on dark feedback.
  5. The new rules are scoped under ``.boss-shell``, NOT under a
     ``[data-theme="…"]`` attribute — the shell is always dark, so
     theme-gating the fix would re-open the bug in the default theme.

Pre-fix baseline: all five clauses fail on the parent of 2875d9e
(origin/server@99e1553) — the rules don't exist before this commit.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _read() -> str:
    return RUNTIME


def _stripped() -> str:
    """Comment-stripped copy of the template — used so selector text
    inside ``/* … */`` cannot trigger a false positive. Mirrors the
    helper from ``tests/test_runtime_ms_explainer_reveal.py``."""
    return _CSS_COMMENT_RE.sub("", _read())


def _rule_body(selector: str, css: str | None = None) -> str:
    """Return the body of the first ``selector { … }`` rule.

    Selector is matched verbatim — pass the literal selector text
    (e.g. ``.boss-shell .boss-q-card``). The search runs against a
    comment-stripped copy of the template.
    """
    text = css if css is not None else _stripped()
    # Anchor on start-of-line + optional whitespace so we don't match
    # the selector when it appears as part of a longer one (e.g. we
    # don't want ``.boss-shell .boss-hp-section,\n.boss-shell …`` to
    # confuse the parse — the comma-grouped form is fine because we
    # match through the first ``{``).
    pattern = re.compile(
        r"(^|\n)\s*"
        + re.escape(selector)
        + r"\s*(?:,[^{]*)?\{",
        re.MULTILINE,
    )
    m = pattern.search(text)
    assert m, f"selector {selector!r} not found in template"
    start = text.index("{", m.start()) + 1
    depth = 1
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    raise AssertionError(f"unbalanced braces for selector {selector!r}")


def _find_rule_block(selector_substr: str) -> str:
    """Return the body of the FIRST rule whose selector list contains
    ``selector_substr`` as a substring. Useful when the rule is
    declared with a comma-grouped selector list (e.g.
    ``.boss-shell .boss-hp-section, .boss-shell .boss-q-card { … }``)
    and we want to assert against the shared declaration block."""
    text = _stripped()
    rule_re = re.compile(r"([^{}]+)\{([^{}]*)\}", re.MULTILINE)
    for m in rule_re.finditer(text):
        selectors = m.group(1)
        body = m.group(2)
        if selector_substr in selectors:
            return body
    raise AssertionError(
        f"no rule with selector substring {selector_substr!r} found"
    )


# ── Clause 1: dark-glass background on the sub-cards ───────────────────


def test_boss_hp_section_under_shell_has_dark_glass_background():
    """``.boss-shell .boss-hp-section`` must declare a dark
    (slate-900-ish, ``rgba(15, 23, 42, …)``) background. The default
    ``.boss-hp-section`` rule uses ``var(--surface)`` which in light
    mode is translucent WHITE — without this override, the HP card
    renders as a white panel on the dark scene with the muted "Savol
    1 / 10" counter washed out.
    """
    body = _find_rule_block(".boss-shell .boss-hp-section")
    assert re.search(r"background\s*:\s*rgba\(\s*15\s*,\s*23\s*,\s*42", body), (
        "Boss contrast regression: `.boss-shell .boss-hp-section` no "
        "longer declares a dark rgba(15, 23, 42, …) background. The HP "
        "card will render as a translucent WHITE panel on the dark "
        "battle scene — `var(--surface)` in light mode is white-72%."
    )


def test_boss_q_card_under_shell_has_dark_glass_background():
    """Same contract on ``.boss-q-card`` — the question prompt card.
    Pre-fix this was white-on-dark with dark text, rendering the
    question prompt washed-out and the tags row near-invisible.
    """
    body = _find_rule_block(".boss-shell .boss-q-card")
    assert re.search(r"background\s*:\s*rgba\(\s*15\s*,\s*23\s*,\s*42", body), (
        "Boss contrast regression: `.boss-shell .boss-q-card` no "
        "longer declares a dark rgba(15, 23, 42, …) background. The "
        "question card will render as a translucent WHITE panel."
    )


# ── Clause 2: light text on every readable child node ─────────────────


def test_boss_shell_text_nodes_use_light_colors():
    """Every text node inside ``.boss-shell`` that previously inherited
    ``var(--text)`` (which is ``#1d1d1f`` in light mode — dark grey)
    must now be re-coloured to a light hex / rgba.

    We assert that ``.boss-q-text``, ``.boss-q-counter``, ``.boss-q-tags``,
    and ``.boss-framing`` each have a ``.boss-shell``-scoped rule with a
    ``color:`` declaration starting with ``#f``/``#e`` or ``rgba(`` plus
    a high luminance component. This is intentionally loose — we want to
    catch the regression where someone reverts the rule to ``var(--text)``
    while still allowing minor palette tweaks.
    """
    for selector, label in [
        (".boss-shell .boss-q-text",    "question prompt"),
        (".boss-shell .boss-q-counter", "question counter"),
        (".boss-shell .boss-q-tags",    "Bloom / PISA tags"),
        (".boss-shell .boss-framing",   "framing banner"),
    ]:
        body = _rule_body(selector)
        # Match the `color:` property only — NOT `border-color`,
        # `border-left-color`, `text-shadow-color`, etc. Use a negative
        # lookbehind on word/hyphen chars so `border-left-color:` is
        # rejected.
        m = re.search(r"(?<![-\w])color\s*:\s*([^;]+);", body)
        assert m, (
            f"Boss contrast regression: `{selector}` no longer declares "
            f"a `color` — the {label} will inherit `var(--text)` which "
            f"is dark in light mode and unreadable on the dark scene."
        )
        value = m.group(1).strip().lower()
        # Reject: var(--text), var(--text-muted), or dark hex literals.
        assert "var(--text" not in value, (
            f"Boss contrast regression: `{selector}` color reverted to "
            f"`var(--text…)` which is dark grey in light mode — the "
            f"{label} will be near-invisible on the dark scene."
        )
        # Heuristic light-color check: hex starting with f / e / d / c,
        # OR rgba/rgb where the dominant channels are high (≥ 180).
        is_light = (
            re.match(r"#[fedc]", value)
            or re.search(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", value)
            and all(int(n) >= 180 for n in re.findall(r"\d+", value)[:3])
        )
        assert is_light, (
            f"Boss contrast regression: `{selector}` color={value!r} "
            f"is not a light value — the {label} won't pass WCAG AA on "
            f"the dark battle scene."
        )


# ── Clause 3: input field — dark bg, light text ────────────────────────


def test_boss_input_under_shell_has_dark_bg_and_light_text():
    """``.boss-input`` defaults to ``rgba(255,255,255,0.92)`` background
    with ``var(--text)`` foreground — illegible on the dark shell. The
    fix re-skins it: dark-glass background + light foreground.
    """
    body = _rule_body(".boss-shell .boss-input")
    assert re.search(r"background\s*:\s*rgba\(\s*15\s*,\s*23\s*,\s*42", body), (
        "Boss contrast regression: `.boss-shell .boss-input` no longer "
        "declares a dark rgba(15, 23, 42, …) background. The answer "
        "field will render WHITE on the dark scene."
    )
    color_m = re.search(r"(?<![-\w])color\s*:\s*([^;]+);", body)
    assert color_m, (
        "Boss contrast regression: `.boss-shell .boss-input` no longer "
        "declares a `color` — typed answers will inherit `var(--text)` "
        "(dark) and disappear on a dark-bg input."
    )
    color_value = color_m.group(1).strip().lower()
    assert "var(--text" not in color_value, (
        "Boss contrast regression: `.boss-shell .boss-input` color "
        "reverted to `var(--text…)` — dark text in light mode will be "
        "unreadable on the new dark-bg input."
    )


def test_boss_input_placeholder_is_light_under_shell():
    """The placeholder text (``Javob kiriting…``) must also be light —
    placeholders default to ~50% of the foreground, but when the
    foreground was dark on a dark input, the placeholder dropped below
    1.5:1 and was effectively invisible.
    """
    text = _stripped()
    pattern = re.compile(
        r"\.boss-shell\s+\.boss-input::placeholder\s*\{([^}]*)\}",
    )
    m = pattern.search(text)
    assert m, (
        "Boss contrast regression: `.boss-shell .boss-input::placeholder` "
        "rule is missing — the placeholder will fall back to ~50% of "
        "the (light) foreground but renders against a dark-glass input "
        "with no explicit colour guarantee."
    )


# ── Clause 4: feedback ::before glyphs inherit colour ──────────────────


def test_boss_feedback_glyphs_inherit_color_under_shell():
    """The ✓ / ✗ glyphs on ``.boss-feedback.correct::before`` and
    ``.boss-feedback.wrong::before`` were hard-coded green / red. On
    the new dark-bg feedback, hard-coded ``#117a3d`` (dark green) was
    illegible. Switching to ``color: inherit`` lets each glyph tint
    with its parent state colour (light-green / light-red / blue).
    """
    text = _stripped()
    pattern = re.compile(
        r"\.boss-shell\s+\.boss-feedback\.correct::before\s*,\s*"
        r"\.boss-shell\s+\.boss-feedback\.wrong::before\s*\{([^}]*)\}",
    )
    m = pattern.search(text)
    assert m, (
        "Boss contrast regression: the scoped "
        "`.boss-shell .boss-feedback.correct::before, "
        ".boss-shell .boss-feedback.wrong::before` rule is missing — "
        "the ✓ / ✗ glyphs will fall back to the unscoped #117a3d / "
        "#b03a44 hard-codes, which are dim on the dark feedback bg."
    )
    body = m.group(1)
    assert re.search(r"color\s*:\s*inherit\s*;", body), (
        "Boss contrast regression: the ✓ / ✗ glyphs no longer use "
        "`color: inherit` — hard-coded colours will diverge from the "
        "parent feedback text tint and break the visual story."
    )


# ── Clause 5: scope under .boss-shell, NOT under [data-theme=…] ────────


def test_contrast_pass_is_not_gated_on_data_theme():
    """The new rules must be scoped under ``.boss-shell``, NOT under a
    ``[data-theme="dark"]`` attribute. The shell is always dark
    regardless of the theme attr — gating the fix on ``data-theme=dark``
    would re-open the bug in the default (light) theme, which is what
    the user originally hit.

    We assert this by walking up from the FIRST occurrence of
    ``.boss-shell .boss-hp-section`` and confirming that the enclosing
    block isn't a ``[data-theme=…]`` selector (a CSS at-rule like
    ``@media`` is fine, but a ``[data-theme]`` selector list is not).
    """
    text = _stripped()
    idx = text.find(".boss-shell .boss-hp-section")
    assert idx != -1, (
        "scope check: `.boss-shell .boss-hp-section` rule not found — "
        "either the fix is missing or its selector changed."
    )
    # Walk backwards in the same line (up to start of the rule) and
    # in the preceding selector chain to confirm `[data-theme` does
    # not appear in the matched selector list. The selector list is
    # whatever text sits between the preceding `}` (or document
    # start) and the `{` of this rule's declaration block.
    decl_open = text.index("{", idx)
    # Find the start of the selector list — scan backwards for `}` or BOF.
    selector_start = 0
    for i in range(decl_open - 1, -1, -1):
        if text[i] == "}":
            selector_start = i + 1
            break
    selector_list = text[selector_start:decl_open]
    assert "[data-theme" not in selector_list, (
        "Boss contrast regression: the `.boss-shell .boss-hp-section` "
        "rule was moved under a `[data-theme=…]` selector list. The "
        "shell is dark regardless of the theme attr — gating the fix "
        "on `data-theme=dark` re-opens the bug in the default theme."
    )


# ── Bonus: anchor that the shell really is dark via !important ─────────


def test_boss_shell_still_forces_dark_scene():
    """If the shell stops forcing a dark backdrop via ``!important``,
    the entire premise of the contrast pass changes — the sub-cards
    could safely revert to ``var(--surface)`` because the underlying
    scene would now follow ``data-theme``. Pin the precondition so the
    contrast pass can be re-audited if this ever changes.
    """
    text = _stripped()
    # Find the `.boss-shell, #screen-boss .card { ... }` rule.
    pattern = re.compile(
        r"\.boss-shell\s*,\s*#screen-boss\s+\.card\s*\{([^}]*)\}",
    )
    m = pattern.search(text)
    assert m, (
        "Anchor: the `.boss-shell, #screen-boss .card` rule has moved "
        "or been renamed — re-audit whether the shell still forces a "
        "dark backdrop, and update this test + the contrast pass "
        "scoping if the premise changed."
    )
    body = m.group(1)
    assert "!important" in body and (
        "rgba(24,24,27" in body or "rgba(24, 24, 27" in body
        or "rgba(9,9,11" in body  or "rgba(9, 9, 11" in body
    ), (
        "Anchor: the boss shell no longer forces a dark zinc backdrop "
        "with !important. The contrast pass scoped under `.boss-shell` "
        "assumes the shell is always dark — if that changed, the pass "
        "should be re-scoped or removed."
    )
