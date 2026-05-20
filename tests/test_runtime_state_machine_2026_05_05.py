"""Regression tests for runtime state-machine fixes (2026-05-05 batch A).

Pins the four critical state-machine bugs in
`server/template/perfect_homework.html` so they can't silently regress:

  - AQ-2: Adaptive Quiz double-submit race in language subjects.
    A fast double-click during the AI-grader await fired two grade
    requests because aq.answered was only set AFTER the await. Fix
    is a sync `aq.busy` gate at function entry that early-returns
    when a grade is in flight, plus a visual is-busy lock on the
    action button.

  - RLC-1: Real-Life-Challenge finish dead-end. The complete branch
    of rlcHandleAction only called setStage(6.5) — a label-only
    setter — so the student was stuck on the result card forever.
    Fix routes through showConsolidationScreen / startFinalBoss
    matching the legacy rlShowEndPlaceholder pattern.

  - FB-1: Boss damage double-count. bossHandleResponse's AI-graded
    branch added serverDamage on top of bossApplyCorrect's local
    dmg accumulation. Fix subtracts bossState.lastDamage (= the
    local dmg just accumulated) before adding serverDamage so the
    server value is the single source of truth.

  - FB-2: Boss done:true post-result re-render. bossState.done was
    never set to true after `done:true` arrived, so the guard at
    the top of bossHandleAction never fired and subsequent clicks
    incremented qIndex / called bossEnd(false) on a victorious run.
    Fix sets bossState.done early in bossRenderResult and routes
    the post-result click forward to showResultsScreen.

Each test slices the relevant function body via `_slice_function`
and asserts substring presence on the rendered template / inline JS.
No headless browser needed.

If any test breaks, the corresponding bug has likely regressed —
read the comment block under the failing assertion before "fixing"
the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest


TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = TEMPLATE_PATH.read_text(encoding="utf-8")


def _slice_function(name: str) -> str:
    """Return the source text of the named JS function from the template.

    Matches both `function foo(` and `async function foo(` (because
    `find` does substring matching, and `async function foo(` contains
    `function foo(`). Terminator scans for the next 8-space-indented
    function declaration, which is the canonical indent in this file.
    """
    start = TEMPLATE.find(f"function {name}(")
    assert start != -1, f"function {name} not found in template"
    # Walk back to capture an `async ` prefix if present, so the slice
    # starts at the actual function declaration.
    if TEMPLATE[max(0, start - 6):start] == "async ":
        start -= 6
    after_function = TEMPLATE.find("\n        function ", start + 1)
    after_async = TEMPLATE.find("\n        async function ", start + 1)
    candidates = [c for c in (after_function, after_async) if c != -1]
    after = min(candidates) if candidates else len(TEMPLATE)
    return TEMPLATE[start:after]


# ---------------------------------------------------------------------------
# Bug AQ-2 — gbAQAction double-submit race
# ---------------------------------------------------------------------------

def test_aq_action_has_busy_guard():
    """gbAQAction must have an aq.busy gate around the AI grade await
    so a fast double-click doesn't fire two grade requests."""
    body = _slice_function("gbAQAction")
    # Early-return guard against re-entry while a grade is in flight.
    assert "if (aq.busy) return" in body, (
        "gbAQAction is missing the `if (aq.busy) return;` early-return. "
        "Without it a second click during the AI-grader await re-enters "
        "and fires gbAQAIGrade twice (Bug AQ-2)."
    )
    # The gate is armed before the AI grader call.
    assert "aq.busy = true" in body, (
        "gbAQAction must set aq.busy = true before awaiting the AI grader."
    )
    # And cleared so the student can retry on grader error / next question.
    assert "aq.busy = false" in body, (
        "gbAQAction must clear aq.busy = false after the await resolves "
        "(or in a finally block) so the gate doesn't permanently lock "
        "subsequent answers."
    )


def test_aq_action_busy_gate_wraps_ai_grader():
    """The busy gate must arm before the await and clear after — i.e.
    the order is `aq.busy = true` → `await gbAQAIGrade(...)` → `aq.busy = false`.
    Otherwise the gate doesn't actually cover the await window."""
    body = _slice_function("gbAQAction")
    set_pos = body.find("aq.busy = true")
    await_pos = body.find("await gbAQAIGrade(")
    clear_pos = body.find("aq.busy = false")
    assert 0 < set_pos < await_pos < clear_pos, (
        f"aq.busy gate must wrap the AI grader await; got positions "
        f"set@{set_pos} await@{await_pos} clear@{clear_pos}"
    )


def test_aq_action_locks_button_visually_during_await():
    """Action button must be visually busy-locked during the AI grader
    await so the student sees the click was registered (and a fast
    second click is also bounced at the DOM level)."""
    body = _slice_function("gbAQAction")
    # Either pointer-events lock or an is-busy class signal must appear.
    has_pointer_lock = "pointerEvents = 'none'" in body
    has_is_busy_class = "'is-busy'" in body or '"is-busy"' in body
    assert has_pointer_lock or has_is_busy_class, (
        "gbAQAction must visually busy-lock the action button (either "
        "btn.style.pointerEvents = 'none' or btn.classList.add('is-busy')) "
        "during the AI grader await so the student sees the click was "
        "registered (Bug AQ-2)."
    )


# ---------------------------------------------------------------------------
# Bug RLC-1 — rlcHandleAction finish dead-end
# ---------------------------------------------------------------------------

def test_rlc_complete_routes_to_consolidation_or_boss():
    """rlcHandleAction's complete branch must call showConsolidationScreen
    or startFinalBoss — NOT just setStage(6.5), which is a label-only
    setter that dead-ends the student on the RLC result card."""
    body = _slice_function("rlcHandleAction")
    # Must mention forward navigation, not just setStage.
    assert "showConsolidationScreen" in body, (
        "rlcHandleAction's complete branch must call showConsolidationScreen "
        "to advance to consolidation when content is present (Bug RLC-1)."
    )
    assert "startFinalBoss" in body, (
        "rlcHandleAction's complete branch must call startFinalBoss as the "
        "fallback when consolidation has no content (Bug RLC-1)."
    )


def test_rlc_complete_branch_matches_legacy_pattern():
    """The complete-branch navigation must mirror the legacy
    rlShowEndPlaceholder pattern: showConsolidationScreen(startFinalBoss)
    when consolidation has content, else startFinalBoss() directly."""
    body = _slice_function("rlcHandleAction")
    assert "showConsolidationScreen(startFinalBoss)" in body, (
        "rlcHandleAction must call showConsolidationScreen(startFinalBoss) "
        "to chain the same Consolidation → Boss path as the legacy "
        "rlShowEndPlaceholder (Bug RLC-1)."
    )
    assert "consolidationHasContent" in body, (
        "rlcHandleAction must gate showConsolidationScreen on "
        "consolidationHasContent() so empty-fixture homeworks auto-skip "
        "to the boss, matching the legacy pattern."
    )


# ---------------------------------------------------------------------------
# Bug FB-1 — boss damage double-count
#
# Historical context: 2026-05-09 fix used a "subtract local dmg + add
# serverDamage" patch AFTER bossApplyCorrect ran. That patched the
# cumulative damageDealt but left the per-answer verdict pill showing "−0 HP"
# because the pill text was already drawn with the local (zero) dmg.
#
# 2026-05-20 refactor: serverDamage is now threaded INTO bossApplyCorrect via
# opts. bossApplyCorrect uses it directly for dmg + lastDamage + damageDealt
# AND the pill text. The post-call subtract-then-add patch is gone (rendered
# obsolete and would now double-mutate damageDealt if reintroduced).
# ---------------------------------------------------------------------------

def test_boss_damage_not_double_counted():
    """The damageDealt total must accumulate serverDamage exactly once, never
    twice. Post-2026-05-20: the protection lives in bossApplyCorrect (via
    opts.serverDamage) — not in a post-call patch. The previous
    subtract-then-add pattern in bossHandleResponse must NOT return.
    """
    body = _slice_function("bossHandleResponse")
    # The pre-refactor anti-pattern (subtract local lastDamage, then add
    # serverDamage to damageDealt) must not be present — it would re-introduce
    # the bug from the OTHER side now that bossApplyCorrect handles serverDamage
    # natively.
    assert "bossState.damageDealt -= bossState.lastDamage" not in body, (
        "Legacy subtract-before-add patch found. With the 2026-05-20 refactor "
        "(serverDamage threaded into bossApplyCorrect via opts), this pattern "
        "DOUBLE-mutates damageDealt. Remove it."
    )
    assert "bossState.damageDealt += serverDamage" not in body, (
        "Legacy direct mutation of damageDealt in the response handler — see "
        "the comment above. bossApplyCorrect is the single mutation site now."
    )
    # The new invariant: applyOpts.serverDamage must be set before
    # bossApplyCorrect is called so it can pick up the authoritative damage.
    assert "applyOpts.serverDamage = serverDamage" in body, (
        "Response handler must thread serverDamage into bossApplyCorrect via "
        "applyOpts.serverDamage. Without this, dynamic boss verdict pills "
        "regress to '−0 HP' (q.damage is undefined on dynamic questions)."
    )
    # Verify the legacy in-body anchors are removed entirely so the
    # remaining assertions stay coherent.
    sub_pos = body.find("bossState.damageDealt -= bossState.lastDamage")
    add_pos = body.find("bossState.damageDealt += serverDamage")
    assert sub_pos == -1 and add_pos == -1, (
        f"Both legacy mutation lines must be ABSENT — bossApplyCorrect is now "
        f"the single damageDealt mutation site. Got positions "
        f"sub@{sub_pos} add@{add_pos}."
    )


# ---------------------------------------------------------------------------
# Bug FB-2 — boss done flag + forward navigation post-result
# ---------------------------------------------------------------------------

def test_boss_done_flag_set_in_render_result():
    """bossRenderResult must set bossState.done = true so the guard at
    the top of bossHandleAction actually fires post-result. Otherwise
    qIndex keeps incrementing on subsequent clicks and a victorious
    student gets bossEnd(false) called on them (Bug FB-2)."""
    body = _slice_function("bossRenderResult")
    assert "bossState.done = true" in body, (
        "bossRenderResult must set bossState.done = true so the guard "
        "at bossHandleAction (`if (state.isAnimating || bossState.done) "
        "return;` style) actually fires post-result (Bug FB-2)."
    )


def test_boss_done_action_navigates_forward():
    """bossHandleAction's `bossState.done` branch must call the same
    downstream path that bossEnd uses — setStage(7.5) +
    showResultsScreen — instead of silently returning."""
    body = _slice_function("bossHandleAction")
    assert "bossState.done" in body, (
        "bossHandleAction must reference bossState.done."
    )
    # Must explicitly route forward, not just early-return.
    assert "showResultsScreen" in body, (
        "bossHandleAction's bossState.done branch must call "
        "showResultsScreen() to mirror bossEnd's downstream navigation "
        "(Bug FB-2). Without this the action button looks live but does "
        "nothing post-result."
    )
    assert "setStage(7.5)" in body, (
        "bossHandleAction's bossState.done branch must call setStage(7.5) "
        "to mirror bossEnd's stage-label update (Bug FB-2)."
    )


def test_boss_done_branch_routes_before_answered_branch():
    """The bossState.done branch must come before the bossState.answered
    branch in bossHandleAction. Otherwise a post-result click with
    answered=true would increment qIndex past BOSS_QUESTIONS.length and
    fall through to bossEnd(false), mislabeling a victory as defeat."""
    body = _slice_function("bossHandleAction")
    done_pos = body.find("if (bossState.done)")
    answered_pos = body.find("if (bossState.answered)")
    assert 0 < done_pos < answered_pos, (
        f"bossState.done branch must precede bossState.answered branch "
        f"in bossHandleAction; got done@{done_pos} answered@{answered_pos} "
        f"(Bug FB-2)."
    )
