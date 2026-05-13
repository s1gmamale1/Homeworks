"""Regression tests for PR #219 — Real-Life image max-height override.

Pins the four invariants of the fix at server/template/perfect_homework.html:

  1. Each of the 4 .rl-* selectors (.rl-story-text / .rl-q-prompt /
     .rl-prompt / .rl-feedback, in both img and svg forms) has a rule
     with max-height: <digits>vh — i.e. the diagram size is bounded by
     a viewport-relative unit, not the 220/240px pixel caps from the
     shared inline-media rules above.

  2. The override block's source-order index is greater than both base
     rules' indices. Cascade is load-bearing here: equal-specificity
     selectors are resolved by source order, so the override only wins
     if it sits after both base rules.

  3. Anchor — the two base rules (at the original 220px and 240px
     blocks) still exist. Premise of the fix: there's something to
     override.

  4. (Pin) Other inline-image classes that ALSO live in the base rules
     (.ms-question-title / .boss-q-text / .fc-definition / .page p)
     do NOT receive vh max-height — confirming the override is scoped
     to Real-Life only.

Style mirrors tests/test_pr68_visual_regressions.py (substring +
regex assertions against the runtime template).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
RUNTIME = ROOT / "server" / "template" / "perfect_homework.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# Each base rule is identified by a representative selector pair from its
# selector list AND its specific pixel max-height value. We avoid matching the
# override block by anchoring on the pixel cap.

_BASE_RULE_220PX = re.compile(
    r"\.rl-story-text\s+img[^{]*?\.rl-q-prompt\s+svg[^{]*?\{[^}]*?max-height:\s*220px",
    re.DOTALL,
)
_BASE_RULE_240PX = re.compile(
    r"\.rl-story-text\s+img[^{]*?\.rl-prompt\s+svg[^{]*?\.rl-feedback\s+svg[^{]*?\{[^}]*?max-height:\s*240px",
    re.DOTALL,
)

# Override rule must list all FOUR rl-* selectors (img+svg each = 8 total) AND
# its max-height value must end in `vh` (viewport-relative; the reviewer
# explicitly allowed any \d+vh, not just 60vh).
_OVERRIDE_RULE = re.compile(
    r"\.rl-story-text\s+img,\s*\.rl-story-text\s+svg,\s*"
    r"\.rl-q-prompt\s+img,\s*\.rl-q-prompt\s+svg,\s*"
    r"\.rl-prompt\s+img,\s*\.rl-prompt\s+svg,\s*"
    r"\.rl-feedback\s+img,\s*\.rl-feedback\s+svg\s*"
    r"\{[^}]*?max-height:\s*(\d+)vh",
    re.DOTALL,
)


def test_base_rules_with_pixel_caps_still_exist():
    """Clause 3 — anchor. Without these, the override would not be necessary
    and a future cleanup might delete the override without realizing the caps
    have been removed too."""
    html = _read(RUNTIME)

    base1 = _BASE_RULE_220PX.search(html)
    assert base1, (
        "Base rule at perfect_homework.html ~line 170 with max-height: 220px is "
        "missing. The override at the bottom of this file presumes a 220px cap "
        "still applies to .rl-story-text / .rl-q-prompt — if the base rule has "
        "been removed, delete the override too."
    )

    base2 = _BASE_RULE_240PX.search(html)
    assert base2, (
        "Base rule at perfect_homework.html ~line 5857 with max-height: 240px is "
        "missing. The override presumes a 240px cap still applies to "
        ".rl-story-text / .rl-prompt / .rl-feedback — if the base rule has been "
        "removed, delete the override too."
    )


def test_rl_image_override_has_all_four_selectors_with_vh_max_height():
    """Clause 1 — every Real-Life image class is covered by a rule whose
    max-height is in vh (viewport-relative) rather than the 220/240px cap."""
    html = _read(RUNTIME)

    override = _OVERRIDE_RULE.search(html)
    assert override, (
        "Override rule covering all 4 .rl-* image classes (story-text, "
        "q-prompt, prompt, feedback) with `max-height: <digits>vh` not found. "
        "Real-Life images would render crushed at 220/240px without it."
    )

    # Sanity bound on the chosen vh value — clearly larger than the 220-240
    # pixel range would have shown on a typical 800-900px-tall screen, and
    # clearly not 100vh (which would push the rest of the card off-screen).
    vh_value = int(override.group(1))
    assert 30 <= vh_value <= 90, (
        f"max-height: {vh_value}vh is outside the reasonable range [30, 90]. "
        f"Too small defeats the purpose; too large pushes the card past the fold."
    )


def test_override_appears_after_both_base_rules_in_source_order():
    """Clause 2 — cascade is load-bearing. Equal-specificity selectors are
    resolved by source order, so the override only wins if it sits after
    both base rules."""
    html = _read(RUNTIME)

    base1 = _BASE_RULE_220PX.search(html)
    base2 = _BASE_RULE_240PX.search(html)
    override = _OVERRIDE_RULE.search(html)
    assert base1 and base2 and override, (
        "Prerequisite anchors / override not present — see other tests in "
        "this file."
    )

    assert base1.end() < override.start(), (
        "Override block at source index {} must come AFTER the 220px base "
        "rule which ends at index {}. Currently the override is BEFORE the "
        "base rule, so the cascade resolves to 220px (not vh) and Real-Life "
        "images stay crushed."
    ).format(override.start(), base1.end())

    assert base2.end() < override.start(), (
        "Override block at source index {} must come AFTER the 240px base "
        "rule which ends at index {}. Currently the override is BEFORE the "
        "base rule, so the cascade resolves to 240px (not vh) and Real-Life "
        "images stay crushed."
    ).format(override.start(), base2.end())


def test_non_rl_inline_image_classes_keep_pixel_caps_unchanged():
    """Clause 4 (optional pin) — the override is scoped to Real-Life only.
    Other inline-image classes that share the base rules' selector list
    (boss prompts, panel paragraphs, memory-sprint titles, flashcard
    definitions) must NOT receive vh max-height.
    """
    html = _read(RUNTIME)

    # Pick one representative selector per "should-not-be-changed" class.
    # We then locate EVERY CSS block that includes that selector and verify
    # none of them switches max-height to a vh-based value.
    for selector in (
        ".ms-question-title img",
        ".boss-q-text img",
        ".fc-definition img",
        ".page p img",
    ):
        # Iterate over each rule that lists this selector. A rule is
        # `selectors... { ... body ... }` so we scan for the closing brace.
        # We don't bother re-validating that max-height is in px — a future
        # cleanup could in principle move the cap into `clamp()` or
        # `min(<px>, …vh)`. What we care about here is that NO bare-vh value
        # appears, since that would mean the Real-Life override has leaked
        # to non-RL classes.
        cursor = 0
        found_any = False
        while True:
            idx = html.find(selector, cursor)
            if idx < 0:
                break
            found_any = True
            block_end = html.find("}", idx)
            assert block_end > idx, f"unterminated CSS block containing {selector}"
            body = html[idx:block_end]
            mh_vh = re.search(r"max-height:\s*\d+vh", body)
            assert not mh_vh, (
                f"Selector {selector} appears in a CSS block whose max-height "
                f"is vh-based: {mh_vh.group(0)!r}. This PR's Real-Life override "
                f"should NOT affect non-RL inline images."
            )
            cursor = block_end + 1
        assert found_any, f"Sanity: selector {selector} expected to appear somewhere in template"
