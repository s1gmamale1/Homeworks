"""Regression tests for the FE-5 dynamic Final Boss loop (Plan-5 wiring).

Pins the contract introduced when the static `BOSS_QUESTIONS`-driven boss
arc was replaced with a dynamic loop powered by the Plan-5 endpoints:

  bossStart           → /api/ai/boss/start
  bossGenerateQuestion → /api/ai/boss/generate-question
  bossSubmitAnswer     → /api/ai/boss/submit-answer

The frontend reaches those endpoints via the runtime.js bridge
(`window.NETS_AI.bossStart` / `.bossGenerateQuestion` / `.bossSubmitAnswer`)
which is locked by tests/test_runtime_fe_foundation.py.

What this file pins:

1. **`bossDynamicStart`** is defined as an async function inside the boss
   IIFE in perfect_homework.html.
2. **`bossFetchNextQuestion`** is defined as an async function and
   whitelists the response (no `expected_answer` / `acceptable` / `rubric`
   / `hints` rendering) — defense-in-depth for FE-6.
3. **`startFinalBoss`** body invokes `bossDynamicStart()` (and not just
   `initBossPlan`).
4. **`bossSubmitAnswer`** has a dynamic branch that calls
   `window.NETS_AI.bossSubmitAnswer(...)`.
5. **`bossState`** carries the new dynamic-mode fields:
   `bossSessionId`, `trialsLeft`, `currentQuestion`, `useDynamicBoss`.
6. **`bossRenderQuestion`** branches on `bossState.useDynamicBoss`.
7. **`bossHandleResponse`** reads `resp.is_correct` (Plan-5) with
   legacy `resp.correct` fallback.
8. **Hint button hidden in dynamic mode** — `bossRenderQuestion` sets
   `display:none` (or `disabled = true`) on `#boss-hint-btn` when
   `useDynamicBoss` is on.
9. **`bossUseHint`** early-exits when `useDynamicBoss` is true.

Companion to:
- tests/test_runtime_final_boss_ui.py (legacy contract, still pinned)
- tests/test_runtime_fe_foundation.py (runtime.js bridge URLs)
- docs/homeworks_ai_remaining_fix_report.md §FE-5
"""
from __future__ import annotations

import os
import re

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def perfect_homework_html() -> str:
    path = os.path.join(_repo_root(), "server", "template", "perfect_homework.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Helper — extract a JS function body by walking matched braces.
# ---------------------------------------------------------------------------


def _extract_function_body(html: str, fn_name: str) -> str:
    """Return the body of the first `function fn_name(...)` (async or sync)
    by counting matched braces. Raises AssertionError if not found.
    """
    pat = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{"
    )
    m = pat.search(html)
    assert m, f"function `{fn_name}` not found"
    start = m.end()
    depth = 1
    i = start
    while i < len(html) and depth > 0:
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return html[start:i]


# ---------------------------------------------------------------------------
# 1. bossDynamicStart exists as an async function
# ---------------------------------------------------------------------------


def test_boss_dynamic_start_exists(perfect_homework_html: str):
    pat = re.compile(r"async\s+function\s+bossDynamicStart\s*\(")
    assert pat.search(perfect_homework_html), (
        "bossDynamicStart must exist as an async function (FE-5 entry point "
        "for the Plan-5 dynamic boss arc)"
    )


def test_boss_dynamic_start_calls_bridge(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossDynamicStart")
    assert "window.NETS_AI.bossStart" in body, (
        "bossDynamicStart must call window.NETS_AI.bossStart(...)"
    )


def test_boss_dynamic_start_handles_failure(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossDynamicStart")
    # Must guard against null / _error / _offline and flip useDynamicBoss=false.
    assert "useDynamicBoss" in body, (
        "bossDynamicStart must read/write bossState.useDynamicBoss"
    )
    assert re.search(r"useDynamicBoss\s*=\s*false", body), (
        "bossDynamicStart must flip useDynamicBoss=false on failure"
    )
    assert ("_error" in body) or ("_offline" in body), (
        "bossDynamicStart must check for _error or _offline failure markers"
    )


# ---------------------------------------------------------------------------
# 2. bossFetchNextQuestion exists as async function and whitelists response
# ---------------------------------------------------------------------------


def test_boss_fetch_next_question_exists(perfect_homework_html: str):
    pat = re.compile(r"async\s+function\s+bossFetchNextQuestion\s*\(")
    assert pat.search(perfect_homework_html), (
        "bossFetchNextQuestion must exist as an async function"
    )


def test_boss_fetch_next_question_calls_bridge(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossFetchNextQuestion")
    assert "window.NETS_AI.bossGenerateQuestion" in body, (
        "bossFetchNextQuestion must call window.NETS_AI.bossGenerateQuestion(...)"
    )


def test_boss_fetch_next_question_whitelists_safe_fields(perfect_homework_html: str):
    """Whitelist enforcement — only safe fields end up rendered."""
    body = _extract_function_body(perfect_homework_html, "bossFetchNextQuestion")
    for field in ("question_id", "question_text", "target_skill",
                   "difficulty", "why_this_question"):
        assert field in body, (
            f"bossFetchNextQuestion must reference safe field `{field}`"
        )


def test_boss_fetch_next_question_strips_dangerous_fields(perfect_homework_html: str):
    """FE-6 defense-in-depth — even if backend leaks expected_answer /
    acceptable / rubric / hints, frontend must explicitly strip them."""
    body = _extract_function_body(perfect_homework_html, "bossFetchNextQuestion")
    for forbidden in ("expected_answer", "acceptable", "rubric", "hints"):
        assert forbidden in body, (
            f"bossFetchNextQuestion must explicitly mention `{forbidden}` "
            f"in a strip/whitelist context (defense in depth for FE-6)"
        )
        # Make sure the mention is in a delete/strip context, not a render.
        # We look for `delete safe.<field>` or a comment about stripping.
        # If the literal `safe.<field> =` appears that would be a render —
        # forbid that.
        assert not re.search(
            rf"safe\.{re.escape(forbidden)}\s*=\s*res\.",
            body,
        ), (
            f"bossFetchNextQuestion must NOT assign `safe.{forbidden} = res.{forbidden}` "
            f"(would render forbidden field)"
        )


def test_boss_fetch_next_question_caps_recent_phrases(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossFetchNextQuestion")
    assert "recentBossPhrases" in body, (
        "bossFetchNextQuestion must update bossState.recentBossPhrases"
    )


# ---------------------------------------------------------------------------
# 3. startFinalBoss invokes bossDynamicStart
# ---------------------------------------------------------------------------


def test_start_final_boss_calls_dynamic_start(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "startFinalBoss")
    assert "bossDynamicStart" in body, (
        "startFinalBoss must invoke bossDynamicStart() to mint a Plan-5 "
        "boss_session_id before rendering Q0"
    )


def test_start_final_boss_calls_fetch_next_question(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "startFinalBoss")
    assert "bossFetchNextQuestion" in body, (
        "startFinalBoss must invoke bossFetchNextQuestion() so the first "
        "question is server-generated"
    )


# ---------------------------------------------------------------------------
# 4. bossSubmitAnswer has dynamic branch routing through window.NETS_AI
# ---------------------------------------------------------------------------


def test_boss_submit_answer_has_dynamic_branch(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossSubmitAnswer")
    assert "window.NETS_AI.bossSubmitAnswer" in body, (
        "bossSubmitAnswer must contain a branch calling "
        "window.NETS_AI.bossSubmitAnswer(...) for the Plan-5 dynamic path"
    )
    assert "useDynamicBoss" in body, (
        "bossSubmitAnswer must gate the dynamic branch on bossState.useDynamicBoss"
    )


def test_boss_submit_answer_preserves_legacy_branch(perfect_homework_html: str):
    """Legacy branch (POST /api/ai/check-answer phase=final-boss) must
    still exist so older homework templates keep grading."""
    body = _extract_function_body(perfect_homework_html, "bossSubmitAnswer")
    assert "/api/ai/check-answer" in body, (
        "bossSubmitAnswer must preserve the legacy /api/ai/check-answer "
        "branch as a fallback"
    )
    assert re.search(r"phase\s*:\s*['\"]final-boss['\"]", body), (
        "bossSubmitAnswer's legacy branch must still set phase: 'final-boss'"
    )


# ---------------------------------------------------------------------------
# 5. bossState carries new dynamic-mode fields
# ---------------------------------------------------------------------------


REQUIRED_DYNAMIC_FIELDS = [
    "bossSessionId",
    "trialsLeft",
    "currentQuestion",
    "currentDifficulty",
    "recentBossPhrases",
    "useDynamicBoss",
]


@pytest.mark.parametrize("field", REQUIRED_DYNAMIC_FIELDS)
def test_boss_state_has_dynamic_field(perfect_homework_html: str, field: str):
    m = re.search(
        r"const\s+bossState\s*=\s*\{(.*?)\};",
        perfect_homework_html,
        re.DOTALL,
    )
    assert m, "bossState literal missing"
    body = m.group(1)
    assert re.search(rf"\b{field}\s*:", body), (
        f"bossState literal must declare `{field}` for the FE-5 dynamic loop"
    )


# ---------------------------------------------------------------------------
# 6. bossRenderQuestion branches on useDynamicBoss
# ---------------------------------------------------------------------------


def test_boss_render_question_branches_on_dynamic(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossRenderQuestion")
    assert "useDynamicBoss" in body, (
        "bossRenderQuestion must check bossState.useDynamicBoss to branch "
        "between the dynamic path (currentQuestion) and the legacy "
        "BOSS_QUESTIONS path"
    )
    assert "currentQuestion" in body, (
        "bossRenderQuestion's dynamic branch must read bossState.currentQuestion"
    )
    # The dynamic branch must read question_text from currentQuestion.
    assert "question_text" in body, (
        "bossRenderQuestion's dynamic branch must render currentQuestion.question_text"
    )


def test_boss_render_question_hides_hint_btn_in_dynamic(perfect_homework_html: str):
    """In dynamic mode the hint button must be hidden or disabled."""
    body = _extract_function_body(perfect_homework_html, "bossRenderQuestion")
    # Must reference the hint button.
    assert "boss-hint-btn" in body, "bossRenderQuestion must reference #boss-hint-btn"
    # In the dynamic branch, the hint button is hidden (display:none) or
    # disabled. We require BOTH assignments to appear inside the function
    # body (the legacy branch keeps disabled=false / display='').
    assert re.search(r"display\s*=\s*['\"]none['\"]", body), (
        "bossRenderQuestion must set hint button display to 'none' in dynamic mode"
    )
    assert re.search(r"disabled\s*=\s*true", body), (
        "bossRenderQuestion must set hint button disabled=true in dynamic mode"
    )


# ---------------------------------------------------------------------------
# 7. bossHandleResponse reads resp.is_correct (Plan-5) with legacy fallback
# ---------------------------------------------------------------------------


def test_boss_handle_response_reads_is_correct(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossHandleResponse")
    assert re.search(r"resp\.is_correct", body), (
        "bossHandleResponse must read resp.is_correct (Plan-5 contract)"
    )
    # Legacy fallback to resp.correct should still be supported.
    assert re.search(r"resp\.correct", body), (
        "bossHandleResponse must keep resp.correct legacy fallback"
    )


def test_boss_handle_response_mirrors_trials_left(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossHandleResponse")
    assert "trials_left" in body, (
        "bossHandleResponse must mirror resp.trials_left into bossState"
    )


def test_boss_handle_response_mirrors_difficulty(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossHandleResponse")
    assert "current_difficulty" in body, (
        "bossHandleResponse must mirror resp.current_difficulty into bossState"
    )


# ---------------------------------------------------------------------------
# 8. bossUseHint early-exits in dynamic mode
# ---------------------------------------------------------------------------


def test_boss_use_hint_early_exits_in_dynamic(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossUseHint")
    assert "useDynamicBoss" in body, (
        "bossUseHint must check bossState.useDynamicBoss and early-exit"
    )


# ---------------------------------------------------------------------------
# 9. bossHandleAction routes through bossFetchNextQuestion in dynamic mode
# ---------------------------------------------------------------------------


def test_boss_handle_action_fetches_next_question_in_dynamic(perfect_homework_html: str):
    body = _extract_function_body(perfect_homework_html, "bossHandleAction")
    assert "bossFetchNextQuestion" in body, (
        "bossHandleAction must call bossFetchNextQuestion() when advancing "
        "to the next dynamic question"
    )
    assert "useDynamicBoss" in body, (
        "bossHandleAction must gate the dynamic-advance branch on useDynamicBoss"
    )


# ---------------------------------------------------------------------------
# 10. NO hardcoded answer keys / acceptable arrays in new helpers
# ---------------------------------------------------------------------------


def test_dynamic_helpers_no_hardcoded_answer_keys(perfect_homework_html: str):
    """User-locked rule: NO hardcoding of question text or answer keys in
    the FE code. Server is the source of truth in dynamic mode."""
    for fn in ("bossDynamicStart", "bossFetchNextQuestion"):
        body = _extract_function_body(perfect_homework_html, fn)
        for forbidden in ("q.acceptable", "q.accepted", "q.ans", "q.answer_spec"):
            assert forbidden not in body, (
                f"{fn} must not reference `{forbidden}` (server-only field)"
            )


# ---------------------------------------------------------------------------
# BLOCKER 1 — race guard between 3s startFinalBoss timeout and dynamic kickoff
#
# Without this guard, a slow LLM `bossStart`/`bossGenerateQuestion` could
# resolve AFTER the 3s timeout has already flipped the UI into legacy
# BOSS_QUESTIONS[0] mode. Late writes to bossState.currentQuestion /
# bossSessionId / useDynamicBoss=true would then cause the student to
# answer the legacy-rendered question while bossSubmitAnswer posts the
# (different) server-generated question_id — cursed mirror grading.
# ---------------------------------------------------------------------------


def test_boss_kickoff_expired_flag_exists(perfect_homework_html: str):
    """bossState must declare a `kickoffExpired` boolean field so both
    helpers and the timeout promise can coordinate via shared state."""
    m = re.search(
        r"const\s+bossState\s*=\s*\{(.*?)\};",
        perfect_homework_html,
        re.DOTALL,
    )
    assert m, "bossState literal missing"
    body = m.group(1)
    assert re.search(r"\bkickoffExpired\s*:", body), (
        "bossState literal must declare `kickoffExpired` for the FE-5 race guard"
    )


def test_dynamic_helpers_check_kickoff_expired(perfect_homework_html: str):
    """Both bossDynamicStart and bossFetchNextQuestion must read
    bossState.kickoffExpired AFTER their await returns and BEFORE
    writing to bossState — otherwise a slow LLM response can clobber
    legacy-mode UI state."""
    for fn in ("bossDynamicStart", "bossFetchNextQuestion"):
        body = _extract_function_body(perfect_homework_html, fn)
        assert "kickoffExpired" in body, (
            f"{fn} must check bossState.kickoffExpired after awaiting "
            f"the network call (BLOCKER 1 race guard)"
        )
        # The guard must read the flag (an `if (bossState.kickoffExpired)`
        # pattern), not just write it.
        assert re.search(r"bossState\.kickoffExpired", body), (
            f"{fn} must reference `bossState.kickoffExpired` explicitly"
        )


def test_timeout_promise_flips_use_dynamic_boss(perfect_homework_html: str):
    """startFinalBoss's timeout promise must (a) set kickoffExpired=true
    and (b) flip useDynamicBoss=false when the 3s cap is hit before any
    question landed. This is the second half of the race guard — without
    it, a successful late kickoff would still write currentQuestion."""
    body = _extract_function_body(perfect_homework_html, "startFinalBoss")
    # Must set kickoffExpired = true somewhere in the body.
    assert re.search(r"kickoffExpired\s*=\s*true", body), (
        "startFinalBoss timeout must set bossState.kickoffExpired = true"
    )
    # Must flip useDynamicBoss = false when no currentQuestion landed.
    assert re.search(r"useDynamicBoss\s*=\s*false", body), (
        "startFinalBoss must flip bossState.useDynamicBoss = false when "
        "the 3s timeout wins and no currentQuestion was set"
    )
    # Reset kickoffExpired = false at the top so a re-entry into the boss
    # arc starts clean.
    assert re.search(r"kickoffExpired\s*=\s*false", body), (
        "startFinalBoss must reset bossState.kickoffExpired = false at the "
        "top of the function so a re-entry doesn't inherit stale state"
    )


# ---------------------------------------------------------------------------
# BLOCKER 2 — textContent (not innerHTML) on AI-generated text
#
# innerHTML on LLM output is an XSS sink. The dynamic branch renders
# server-generated `question_text` and `feedback` strings, both of
# which are LLM output and must go through textContent. The legacy
# branch keeps innerHTML for q.prompt because BOSS_QUESTIONS is
# server-injected STATIC content (template-side renderer, not LLM).
# ---------------------------------------------------------------------------


def test_boss_q_text_uses_text_content_in_dynamic_branch(perfect_homework_html: str):
    """The dynamic branch of bossRenderQuestion must use textContent for
    `dq.question_text`, NOT innerHTML. The legacy branch can keep
    innerHTML for `q.prompt` — that's static server-injected content."""
    body = _extract_function_body(perfect_homework_html, "bossRenderQuestion")
    # Dynamic branch — must use textContent for dq.question_text.
    assert re.search(
        r"boss-q-text['\"]?\)\s*\.textContent\s*=\s*dq\.question_text",
        body,
    ), (
        "bossRenderQuestion's dynamic branch must use "
        "el('boss-q-text').textContent = dq.question_text (NOT innerHTML) — "
        "dq.question_text is LLM output and innerHTML is an XSS sink"
    )
    # Forbid the unsafe pattern explicitly.
    assert not re.search(
        r"boss-q-text['\"]?\)\s*\.innerHTML\s*=\s*dq\.question_text",
        body,
    ), (
        "bossRenderQuestion must NOT use innerHTML for dq.question_text "
        "(XSS sink — Sigma BLOCKER 2)"
    )
    # Legacy branch — innerHTML on q.prompt is preserved (static content).
    assert re.search(
        r"boss-q-text['\"]?\)\s*\.innerHTML\s*=\s*q\.prompt",
        body,
    ), (
        "bossRenderQuestion's LEGACY branch must keep innerHTML for q.prompt "
        "(BOSS_QUESTIONS static content — inline images/SVGs/bold)"
    )


def test_feedback_rendering_no_innerhtml_on_ai_msg(perfect_homework_html: str):
    """bossHandleResponse must NOT call fbEl.innerHTML = aiMsg. Use
    textContent + programmatic span (createElement + appendChild)."""
    body = _extract_function_body(perfect_homework_html, "bossHandleResponse")
    assert not re.search(r"fbEl\.innerHTML\s*=\s*aiMsg", body), (
        "bossHandleResponse must NOT set fbEl.innerHTML = aiMsg "
        "(aiMsg is LLM-generated → XSS sink — Sigma BLOCKER 2)"
    )
    assert not re.search(r"fbEl\.innerHTML\s*=\s*resp\.feedback", body), (
        "bossHandleResponse must NOT set fbEl.innerHTML = resp.feedback "
        "(resp.feedback is LLM-generated → XSS sink)"
    )
    # The new safe pattern — textContent + appendChild.
    assert re.search(r"fbEl\.textContent\s*=\s*aiMsg", body), (
        "bossHandleResponse must use fbEl.textContent = aiMsg + ' ' for "
        "the AI feedback message"
    )
    assert "fbEl.appendChild(badge)" in body or "appendChild(badge)" in body, (
        "bossHandleResponse must build the AI-baho badge programmatically "
        "via createElement + appendChild instead of innerHTML"
    )


def test_boss_apply_correct_no_innerhtml_on_dynamic(perfect_homework_html: str):
    """bossApplyCorrect's AI-baho rendering site (the aiGraded branch)
    must use textContent + programmatic span, not innerHTML."""
    body = _extract_function_body(perfect_homework_html, "bossApplyCorrect")
    # Forbid innerHTML on the feedback element entirely in this function.
    assert not re.search(r"fbEl\.innerHTML\s*=", body), (
        "bossApplyCorrect must NOT use fbEl.innerHTML — switch to "
        "textContent + createElement('span') for the AI baho badge "
        "(Sigma BLOCKER 2)"
    )
    # Must build the badge programmatically inside the aiGraded branch.
    assert "createElement('span')" in body, (
        "bossApplyCorrect's aiGraded branch must build the AI-baho badge "
        "via document.createElement('span')"
    )
    assert "screen-reading-ai-badge" in body, (
        "bossApplyCorrect must still emit the .screen-reading-ai-badge "
        "class (legacy a11y/visual contract)"
    )


# ---------------------------------------------------------------------------
# 2026-05-13 audit fixes — regression tests for bugs #1, #2, #4
# ---------------------------------------------------------------------------


def test_kickoff_expired_is_cleared_after_planready_when_dynamic_won(perfect_homework_html: str):
    """Bug #1: `kickoffExpired` set by the kickoff timeout used to stay true
    forever, silently aborting all Q2+ fetches via the same race guard in
    bossFetchNextQuestion. After the kickoff race resolves, if dynamic won
    (currentQuestion is populated), the flag MUST be cleared so subsequent
    fetches are not short-circuited.
    """
    body = _extract_function_body(perfect_homework_html, "startFinalBoss")
    # Must reset the guard after `await planReady` AND only when dynamic won.
    assert "kickoffExpired = false" in body, (
        "startFinalBoss must clear bossState.kickoffExpired after the "
        "kickoff race resolves (bug #1 from 2026-05-13 audit)"
    )
    # The reset must be gated on dynamic having actually won — otherwise the
    # legacy fallback path could resurrect dynamic mode mid-arc.
    reset_idx = body.find("kickoffExpired = false")
    preceding = body[max(0, reset_idx - 400):reset_idx]
    assert "useDynamicBoss" in preceding and "currentQuestion" in preceding, (
        "The kickoffExpired reset must be guarded on `useDynamicBoss && "
        "currentQuestion` so it doesn't fire when dynamic lost the race"
    )


def test_boss_handle_response_reads_plan5_field_names_for_damage_and_hp(perfect_homework_html: str):
    """Real bug observed 2026-05-13 in screenshot: student answered correctly
    on hard difficulty, server logged damage=15 + hp=85, but UI displayed
    '−0 HP' and HP bar stayed at 100. Root cause: bossHandleResponse was
    reading resp.damage_dealt and resp.hp_remaining — the LEGACY field
    names from /api/ai/boss-turn. Plan-5 /api/ai/boss/submit-answer returns
    `damage` and `hp` (no suffix). Both shapes must be accepted."""
    body = _extract_function_body(perfect_homework_html, "bossHandleResponse")
    # Must accept Plan-5 names first.
    assert "resp.damage" in body, "must read resp.damage (Plan-5)"
    assert "resp.hp" in body, "must read resp.hp (Plan-5)"
    # Should still fall back to legacy names for /boss-turn compatibility.
    assert "resp.damage_dealt" in body, (
        "must keep legacy resp.damage_dealt fallback for /boss-turn"
    )
    assert "resp.hp_remaining" in body, (
        "must keep legacy resp.hp_remaining fallback for /boss-turn"
    )


def test_boss_handle_response_detects_boss_over_via_boss_status(perfect_homework_html: str):
    """Companion to the damage/hp fix: Plan-5 signals end-of-boss via
    `boss_status: "won"|"failed"|"abandoned"` while legacy /boss-turn used
    `done: true`. Without this, the results card never fires for Plan-5
    boss completions and students keep clicking Next past the end."""
    body = _extract_function_body(perfect_homework_html, "bossHandleResponse")
    assert "boss_status" in body, (
        "bossHandleResponse must accept resp.boss_status for Plan-5 end-of-boss"
    )
    assert "'won'" in body or '"won"' in body, "must check for 'won' status"
    assert "'failed'" in body or '"failed"' in body, "must check for 'failed' status"
    # Legacy `done` check must remain for /boss-turn back-compat.
    assert "resp.done" in body, "must keep legacy resp.done fallback"


def test_kickoff_timeout_timer_cancelled_when_dynamic_wins(perfect_homework_html: str):
    """Regression for 2026-05-13 late-evening bug: the kickoff timeoutPromise
    setTimeout used to fire at T+25s regardless of whether dynamic won the
    race. If dynamic won at T+8s, the late-firing timer would re-set
    bossState.kickoffExpired=true while the student was reading Q1, then
    every Q2+ fetch would hit the kickoffExpired guard in
    bossFetchNextQuestion, return null, and trip the 'Q2+ dynamic fetch
    failed; ending boss session gracefully' fallback. Server-side Q2 was
    being generated successfully but discarded by the runtime.

    Fix: capture the timer ID and clearTimeout it after planReady resolves
    iff dynamic won (currentQuestion is set + useDynamicBoss still true).
    """
    body = _extract_function_body(perfect_homework_html, "startFinalBoss")
    # The kickoff timer ID must be captured (not anonymous in the new Promise).
    assert "kickoffTimeoutTimer" in body, (
        "startFinalBoss must capture the kickoff setTimeout ID as "
        "kickoffTimeoutTimer (or equivalent) so it can be cancelled when "
        "dynamic wins the race"
    )
    # There must be a clearTimeout call on that ID after the race resolves.
    assert "clearTimeout(kickoffTimeoutTimer)" in body, (
        "startFinalBoss must clearTimeout the kickoff timer when dynamic "
        "wins, otherwise the late-firing timer re-arms kickoffExpired and "
        "breaks Q2+ fetches"
    )
    # The clear must be guarded on dynamic having won (currentQuestion set).
    clear_idx = body.find("clearTimeout(kickoffTimeoutTimer)")
    preceding = body[max(0, clear_idx - 400):clear_idx]
    assert "currentQuestion" in preceding, (
        "clearTimeout(kickoffTimeoutTimer) must be guarded on "
        "bossState.currentQuestion being populated (i.e. dynamic won)"
    )


def test_q2_plus_fetch_has_a_timeout_race(perfect_homework_html: str):
    """Bug #2: bossFetchNextQuestion for Q2+ was a bare await with no race —
    a stalled Kimi response would lock the Next button indefinitely. The
    audit fix wraps it in a 20s timeout race so mid-arc stalls surface as a
    graceful boss-end rather than a permanent UI lock.
    """
    body = _extract_function_body(perfect_homework_html, "bossHandleAction")
    # Must call bossFetchNextQuestion AND race it against a setTimeout.
    assert "bossFetchNextQuestion" in body, "bossHandleAction must call bossFetchNextQuestion"
    # The race uses Promise.race with a sentinel timeout marker.
    assert "Promise.race" in body, (
        "Q2+ fetch must be wrapped in Promise.race against a timeout "
        "(bug #2 from 2026-05-13 audit) — bare await is forbidden"
    )
    # The timeout constant must be present and explicit (not a magic number).
    assert "FETCH_TIMEOUT_MS" in body or "20000" in body, (
        "Q2+ fetch timeout must be 20s (or a named constant)"
    )


def test_mid_arc_dynamic_failure_ends_gracefully_not_falls_to_authored(perfect_homework_html: str):
    """Bug #4: when dynamic fails mid-arc (Q3+ fetch fails), the runtime
    used to read `BOSS_QUESTIONS[qIndex]` as a fallback — which renders the
    author's REFERENCE questions verbatim, defeating the whole reference-pool
    refactor. The audit fix calls bossEnd(false) instead. This guards the
    user from ever seeing authored reference text as a live boss question.
    """
    body = _extract_function_body(perfect_homework_html, "bossHandleAction")
    # The dynamic-mid-arc-failure branch must NOT fall through to BOSS_QUESTIONS[idx].
    # Find the dynamic-mode block (begins with `if (bossState.useDynamicBoss) {`).
    dyn_start = body.find("if (bossState.useDynamicBoss)")
    assert dyn_start >= 0, "Could not find dynamic-mode branch in bossHandleAction"
    # Walk forward to the matching close brace.
    depth = 0
    end_idx = dyn_start
    started = False
    for i, ch in enumerate(body[dyn_start:], start=dyn_start):
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                end_idx = i
                break
    dyn_block = body[dyn_start:end_idx]
    # The dynamic branch must call bossEnd on failure, NOT bossRenderQuestion
    # against BOSS_QUESTIONS[idx].
    assert "bossEnd(false)" in dyn_block, (
        "When mid-arc dynamic fetch fails, runtime must call bossEnd(false) "
        "to end the session gracefully (bug #4 fix)"
    )
    # Verify the dynamic branch does NOT contain a BOSS_QUESTIONS.length
    # fallback check (that was the buggy path).
    assert "qIndex >= BOSS_QUESTIONS.length" not in dyn_block, (
        "Mid-arc dynamic failure path must NOT fall back to BOSS_QUESTIONS "
        "indexing — that renders authored REFERENCE questions verbatim"
    )
