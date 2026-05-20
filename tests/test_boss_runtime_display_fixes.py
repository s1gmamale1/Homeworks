"""Regression — boss runtime display bugs visible in 2026-05-20 testing.

Two bugs surfaced in screenshots during English-homework boss testing
(HW-20260513-004 on Nggaev). Server-side grading + damage math were correct
(scores 0.95-1.0, HP 100→17 as expected) but the runtime UI rendered:

  Bug #1-visual: verdict pill "−0 HP" on every correct answer. Root cause:
    bossApplyCorrect() drew the pill text using q.damage, but dynamic-boss
    questions have no authored .damage (damage is server-side per Plan 5).
    Local fallback computed 0 → pill said "−0 HP". The cumulative damageDealt
    was being patched post-call but the per-answer pill text was already
    drawn with the wrong value.

  Bug #6: counter "Savol 2 · 4" — middle-dot separator with raw trialsLeft
    is ambiguous (reads as ratio or attempt#). Switched to "Savol N / total"
    matching the static-boss counter format.

These tests assert the bad state cannot return. Both invariants are pinned
against the rendered template body.
"""
from __future__ import annotations

import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"


def _template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _extract_function_body(body: str, fn_name: str) -> str:
    """Extract a JS function body from the template by name. Brace-matching
    walks from the opening { after the param list until the matching }."""
    m = re.search(rf"function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{", body)
    assert m, f"function {fn_name} not found in template"
    start = m.end()
    depth = 1
    i = start
    while i < len(body) and depth > 0:
        ch = body[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return body[start:i - 1]


# ---------------------------------------------------------------------------
# Bug #1 visible regression — −0 HP pill
# ---------------------------------------------------------------------------


def test_bossApplyCorrect_reads_serverDamage_from_opts():
    """The function MUST read opts.serverDamage as the primary damage source
    so dynamic-boss verdict pills show the real server damage, not 0."""
    fn = _extract_function_body(_template_text(), "bossApplyCorrect")
    assert "opts.serverDamage" in fn or "opts?.serverDamage" in fn, (
        "bossApplyCorrect must read opts.serverDamage. Without this, dynamic "
        "boss questions (which lack q.damage) make the pill show '−0 HP' even "
        "when the server dealt real damage."
    )


def test_bossApplyCorrect_falls_back_to_q_damage_for_legacy_static():
    """Legacy static-boss path still ships authored q.damage. The fallback
    branch must remain so /api/ai/boss-turn flow keeps working."""
    fn = _extract_function_body(_template_text(), "bossApplyCorrect")
    assert "q.damage" in fn, (
        "Static-boss fallback (q.damage) must remain — only dynamic boss "
        "uses server-side damage"
    )


def test_bossApplyCorrect_does_not_double_combo_when_serverDamage_present():
    """When serverDamage is passed, dmg = serverDamage directly — no combo
    doubling. The server's damage formula already factors difficulty and
    score; doubling here would make the pill misreport vs. the actual HP
    delta on combo turns."""
    fn = _extract_function_body(_template_text(), "bossApplyCorrect")
    # The if branch using opts.serverDamage should assign dmg directly,
    # not via the 'doubled ? * 2 : ...' path. Check that:
    #   1. There's an `if` that gates on opts.serverDamage being numeric
    #   2. Inside it, dmg is assigned directly to opts.serverDamage (no `* 2`)
    server_branch_re = re.compile(
        r"if\s*\([^)]*opts\.serverDamage[^)]*\)\s*\{\s*dmg\s*=\s*opts\.serverDamage\s*;",
        re.DOTALL,
    )
    assert server_branch_re.search(fn), (
        "When opts.serverDamage is present, dmg must be assigned directly "
        "to opts.serverDamage (no combo doubling). Saw fn body:\n" + fn[:800]
    )


def test_response_handler_passes_serverDamage_into_apply():
    """The bossHandleResponse / submit-answer response path must thread
    resp.damage into bossApplyCorrect's opts so the pill text can use it."""
    body = _template_text()
    # Look for the pattern: serverDamage = ... then passed in opts to apply
    assert re.search(
        r"applyOpts\.serverDamage\s*=\s*serverDamage", body
    ), (
        "Response handler must set applyOpts.serverDamage before calling "
        "bossApplyCorrect — otherwise the −0 HP pill regression returns"
    )


def test_no_post_call_double_count_patch_block():
    """The old patch block (subtract lastDamage, set lastDamage = serverDamage,
    add back) is now redundant because bossApplyCorrect uses serverDamage
    directly. Must be removed, not just neutered."""
    body = _template_text()
    bad_patch = re.compile(
        r"bossState\.damageDealt\s*-=\s*bossState\.lastDamage[\s\S]{0,200}?"
        r"bossState\.damageDealt\s*\+=\s*serverDamage"
    )
    assert not bad_patch.search(body), (
        "The post-call double-count patch (lines ~18817-18828 pre-fix) must "
        "be removed. With opts.serverDamage threaded in, the patch becomes a "
        "double-mutation that hides bugs in bossApplyCorrect."
    )


# ---------------------------------------------------------------------------
# Bug #6 — "Savol N · X" → "Savol N / total"
# ---------------------------------------------------------------------------


def test_dynamic_boss_counter_uses_slash_total_format():
    """The boss-q-counter for dynamic mode must render 'Savol N / total',
    matching the static-boss counter on line ~19098. No raw '· trialsLeft'."""
    body = _template_text()
    # Pull the block that sets boss-q-counter for the dynamic path.
    m = re.search(
        r"if\s*\(\s*el\(['\"]boss-q-counter['\"]\)\s*\)\s*\{([^}]+?bossState\.trialsLeft[^}]+)\}",
        body,
        re.DOTALL,
    )
    assert m, "Dynamic-boss counter block (touching trialsLeft) not found"
    block = m.group(1)
    # Must use ' / ' separator with a computed total — never ' · ' + raw
    # trialsLeft (the legacy ambiguous format).
    bad = re.search(r"counterText\s*\+=\s*['\"][ ·‧]+['\"]\s*\+\s*bossState\.trialsLeft", block)
    assert not bad, (
        "Counter must NOT use 'Savol N · trialsLeft' — that's the Bug #6 "
        "format students mis-read as a ratio. Use 'Savol N / total'."
    )
    assert "' / '" in block or '" / "' in block, (
        "Dynamic counter block must include ' / ' separator (Savol N / total)"
    )


def test_dynamic_counter_total_is_idx_plus_trials_left():
    """Total must be (idx + 1) + trialsLeft. This is the only formula that
    produces stable total — server decrements trials_left after each answer,
    so current_question + remaining gives the authored pool size."""
    body = _template_text()
    m = re.search(
        r"const total = \(idx \+ 1\) \+ bossState\.trialsLeft",
        body,
    )
    assert m, (
        "Total computation must be `(idx + 1) + bossState.trialsLeft` so the "
        "denominator stays constant across the arc"
    )
