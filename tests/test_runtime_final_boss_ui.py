"""Regression tests for the Final Boss runtime UI (frontend polish PR).

Pins the contract between this PR's frontend work and the backend's
phase=final-boss endpoint (Chunk B at server/routes/ai.py:1339):
- Existing IDs preserved (#boss-input, #boss-hp-num, #boss-hp-bar,
  #boss-q-counter, #boss-combo, #boss-feedback, #boss-shell, #screen-boss)
  so tutor extractor + AMR scorecard keep working.
- New visual surfaces (#boss-particles-layer, #boss-impact-flash,
  #boss-heal-flash, #boss-attempt-pill, #boss-result-card + 4 children).
- bossState extensions (sessionId, attemptsUsed, outcome, stars, outcomeXp,
  busy, lastDamage).
- All new functions present (bossInit, bossSubmitAnswer, bossHandleResponse,
  bossImpactFlash, bossHealFlash, bossUpdateLowHpPulse,
  bossUpdateAttemptPill, bossRenderResult).
- bossMatch removed (orphan — no client-side correctness check possible
  now that BOSS_QUESTIONS is stripped of acceptable[]).
- bossNorm preserved (still useful for input cleaning).
- Single network swap-point: bossSubmitAnswer POSTs /api/ai/check-answer
  with phase: 'final-boss', reads ctx.hwId FIRST per TM #140 / SF lesson.
- Old /api/ai/boss-turn dispatch (`nets:submit kind:'boss'`) removed from
  bossHandleAction's wrong-answer branch.
- Answer-leak gate at runtime layer (no acceptable / accepted / ans /
  answer_spec keys at any depth in rendered BOSS_QUESTIONS literal).
- No client-side correctness logic in new boss* function bodies.
- i18n keys (boss.*) present in all 3 runtime languages.
- Dark-mode CSS parity (≥10 [data-theme="dark"] [id^=\"boss-\"] OR .boss-).
- completePhase('boss') called from bossRenderResult.
- bossApplyCorrect's __sessionLog.push entry shape unchanged
  (phase / id / correct / score / first_try / damage / axes).
- bossHandleAction is async.

Companion to:
- tests/test_runtime_real_life_challenge_ui.py (reference shape, RLC #142)
- tests/test_runtime_tile_match_ui.py (TM #140 patterns)
- server/routes/ai.py:_check_answer_final_boss (Chunk B endpoint)
- server/services/injector.py:_serialize_boss_questions (server strip)
"""
from __future__ import annotations
from pathlib import Path

import json
import re

import pytest

from server.services.injector import inject

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RUNTIME_EXTRAS = (
    (_REPO_ROOT / "server" / "template" / "js" / "perfect_homework.js").read_text(encoding="utf-8") + "\n" +
    (_REPO_ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css").read_text(encoding="utf-8") + "\n" +
    (_REPO_ROOT / "server" / "template" / "static" / "js" / "tutor.js").read_text(encoding="utf-8")
)

def _inject_full(*args, **kwargs):
    return inject(*args, **kwargs) + "\n" + _RUNTIME_EXTRAS



# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _empty_content():
    return {
        "meta": {"title": "FB UI Smoke", "subject_display": "X", "section": "", "cefr_level": ""},
        "gate_quote": {"mode": "auto"},
        "panels": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": [],
        "gb_why_chain": [],
        "gb_memory_match": [],
        "gb_puzzle_lock": [],
        "gb_mystery_box": [],
        "gb_ttt": [],
        "gb_sentence_fill": [],
        "gb_tile_match": [],
        "boss_questions": [],
        "boss_meta": None,
        "real_life": None,
        "real_life_challenge": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


def _boss_questions_fixture() -> list:
    """Boss questions WITH server-only fields. After inject(), the literal
    must be stripped (acceptable / ans / accepted / answer_spec gone)."""
    return [
        {
            "id": "B1", "tier": "easy", "damage": 10,
            "bloom": "L3", "pisa": "L3",
            "prompt": "Yeching: x = 5", "q": "Yeching: x = 5",
            "ans": ["5", "x=5"],
            "acceptable": ["5", "x=5"],
            "accepted": ["5", "x=5"],
            "answer_spec": {"kind": "exact", "answers": ["5"]},
            "hints": ["Hint 1", "Hint 2", "Hint 3"],
        },
        {
            "id": "B2", "tier": "medium", "damage": 20,
            "bloom": "L4", "pisa": "L4",
            "prompt": "Yeching: x² = 9", "q": "Yeching: x² = 9",
            "ans": ["±3"],
            "acceptable": ["±3"],
            "accepted": ["±3"],
            "answer_spec": {"kind": "exact", "answers": ["±3", "3,-3"]},
            "hints": ["A", "B", "C"],
        },
    ]


@pytest.fixture(scope="module")
def html_empty() -> str:
    return _inject_full(
        _empty_content(),
        runtime_context={"hw_id": "HW-FB-EMPTY", "subject": "math", "grade": 8},
    )


@pytest.fixture(scope="module")
def html_with_boss() -> str:
    body = _empty_content()
    body["boss_questions"] = _boss_questions_fixture()
    body["boss_meta"] = {
        "boss_type": "sub",
        "grade_band": "g6_8",
        "attempts_max": 2,
    }
    return _inject_full(
        body,
        runtime_context={"hw_id": "HW-FB-1", "subject": "math", "grade": 8},
    )


# ---------------------------------------------------------------------------
# 1. Existing IDs preserved (tutor extractor + AMR scorecard depend on these)
# ---------------------------------------------------------------------------


EXISTING_LOCKED_IDS = [
    "boss-input", "boss-hp-num", "boss-hp-bar",
    "boss-q-counter", "boss-combo", "boss-feedback",
    "boss-shell", "screen-boss",
]


@pytest.mark.parametrize("id_", EXISTING_LOCKED_IDS)
def test_existing_locked_id_preserved(html_empty: str, id_: str):
    assert f'id="{id_}"' in html_empty, (
        f"existing locked id #{id_} must be preserved (tutor extractor / AMR scorecard depend on it)"
    )


# ---------------------------------------------------------------------------
# 2. New IDs present
# ---------------------------------------------------------------------------


NEW_REQUIRED_IDS = [
    "boss-particles-layer",
    "boss-impact-flash",
    "boss-heal-flash",
    "boss-attempt-pill",
    "boss-result-card",
    "boss-result-title",
    "boss-result-stars",
    "boss-result-xp",
    "boss-result-summary",
]


@pytest.mark.parametrize("id_", NEW_REQUIRED_IDS)
def test_new_required_id_present(html_empty: str, id_: str):
    assert f'id="{id_}"' in html_empty, f"new required id #{id_} is missing"


# ---------------------------------------------------------------------------
# 3. bossState literal carries new additive fields
# ---------------------------------------------------------------------------


def test_boss_state_extensions(html_empty: str):
    # Locate the bossState literal block.
    m = re.search(r"const\s+bossState\s*=\s*\{(.*?)\};", html_empty, re.DOTALL)
    assert m, "bossState literal missing"
    body = m.group(1)
    required = [
        "sessionId", "attemptsUsed", "outcome",
        "stars", "outcomeXp", "busy", "lastDamage",
    ]
    for name in required:
        assert re.search(rf"\b{name}\s*:", body), (
            f"bossState must declare additive field `{name}`"
        )


# ---------------------------------------------------------------------------
# 4. New functions present
# ---------------------------------------------------------------------------


NEW_REQUIRED_FUNCTIONS = [
    "bossInit",
    "bossSubmitAnswer",
    "bossHandleResponse",
    "bossImpactFlash",
    "bossHealFlash",
    "bossUpdateLowHpPulse",
    "bossUpdateAttemptPill",
    "bossRenderResult",
]


@pytest.mark.parametrize("fn", NEW_REQUIRED_FUNCTIONS)
def test_new_required_function_present(html_empty: str, fn: str):
    pat = re.compile(
        rf"\bfunction\s+{re.escape(fn)}\s*\(|\basync\s+function\s+{re.escape(fn)}\s*\("
    )
    assert pat.search(html_empty), f"required JS function `{fn}` missing"


# ---------------------------------------------------------------------------
# 5. bossMatch removed (orphaned — its input acceptable[] is stripped server-side)
# ---------------------------------------------------------------------------


def test_boss_match_removed(html_empty: str):
    pat = re.compile(r"\bfunction\s+bossMatch\s*\(")
    matches = pat.findall(html_empty)
    assert len(matches) == 0, (
        "bossMatch must be removed (its input `q.acceptable` is now stripped "
        "server-side by _serialize_boss_questions). Found: " + str(matches)
    )


# ---------------------------------------------------------------------------
# 6. bossNorm preserved (still useful for input cleaning)
# ---------------------------------------------------------------------------


def test_boss_norm_preserved(html_empty: str):
    assert re.search(r"\bfunction\s+bossNorm\s*\(", html_empty), (
        "bossNorm must be preserved (input cleanup helper)"
    )


# ---------------------------------------------------------------------------
# 7. Single network swap-point — POSTs /api/ai/check-answer phase=final-boss
# ---------------------------------------------------------------------------


def _boss_submit_body(html: str) -> str:
    """Extract bossSubmitAnswer body (rough — until next bare top-level function)."""
    m = re.search(
        r"async\s+function\s+bossSubmitAnswer\s*\([^)]*\)\s*\{(.*?)\n\s{8}(?:async\s+)?function\s+\w",
        html,
        re.DOTALL,
    )
    assert m, "could not locate bossSubmitAnswer body"
    return m.group(1)


def test_boss_submit_answer_endpoint(html_empty: str):
    body = _boss_submit_body(html_empty)
    assert "/api/ai/check-answer" in body, (
        "bossSubmitAnswer must POST to /api/ai/check-answer"
    )
    assert re.search(r"phase\s*:\s*['\"]final-boss['\"]", body), (
        "bossSubmitAnswer payload must set phase: 'final-boss'"
    )
    assert re.search(r"method\s*:\s*['\"]POST['\"]", body), (
        "bossSubmitAnswer must use POST"
    )


# ---------------------------------------------------------------------------
# 8. ctx.hwId priority — exact 3-key chain (TM/SF lesson)
# ---------------------------------------------------------------------------


def test_ctx_hwid_priority_chain(html_empty: str):
    body = _boss_submit_body(html_empty)
    pat = re.compile(
        r"ctx\.hwId\s*\|\|\s*ctx\.homework_id\s*\|\|\s*ctx\.homeworkId"
    )
    assert pat.search(body), (
        "bossSubmitAnswer must read homework id via the canonical 3-key chain "
        "(ctx.hwId || ctx.homework_id || ctx.homeworkId) — TM #140 / SF lesson"
    )


# ---------------------------------------------------------------------------
# 9. Old /api/ai/boss-turn dispatch removed from bossHandleAction wrong-answer
#    branch (the path that previously called nets:submit kind:'boss').
# ---------------------------------------------------------------------------


def _boss_handle_action_body(html: str) -> str:
    m = re.search(
        r"async\s+function\s+bossHandleAction\s*\([^)]*\)\s*\{",
        html,
    )
    assert m, "bossHandleAction must be async"
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


def test_old_boss_turn_dispatch_removed(html_empty: str):
    body = _boss_handle_action_body(html_empty)
    # The legacy wrong-answer branch dispatched a CustomEvent('nets:submit', { kind:'boss', ... }).
    # That branch is gone — every submit now goes through bossSubmitAnswer.
    assert "nets:submit" not in body, (
        "bossHandleAction must NOT dispatch nets:submit (old /api/ai/boss-turn path removed)"
    )
    assert "kind: 'boss'" not in body and "kind:'boss'" not in body, (
        "bossHandleAction must not reference legacy `kind:'boss'` dispatch"
    )


# ---------------------------------------------------------------------------
# 10. Answer-leak gate — rendered BOSS_QUESTIONS contains zero
#     acceptable / accepted / ans / answer_spec keys at any depth.
# ---------------------------------------------------------------------------


def _extract_boss_questions_literal(html: str) -> list:
    """Pull out the substituted const BOSS_QUESTIONS = [...] literal."""
    m = re.search(
        r"const\s+BOSS_QUESTIONS\s*=\s*(\[.*?\]);",
        html,
        re.DOTALL,
    )
    assert m, "BOSS_QUESTIONS assignment missing"
    return json.loads(m.group(1))


def test_boss_questions_no_answer_leak(html_with_boss: str):
    """Server strips acceptable / accepted / ans / answer_spec at every depth."""
    parsed = _extract_boss_questions_literal(html_with_boss)
    BANNED = {"acceptable", "accepted", "ans", "accepted_answers", "answer_spec"}

    def walk(obj, path="$"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in BANNED, (
                    f"server-only field `{k}` leaked into BOSS_QUESTIONS at {path}"
                )
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    walk(parsed)
    assert len(parsed) == 2, "two boss questions expected"


# ---------------------------------------------------------------------------
# 11. No client-side correctness logic in new boss* functions
# ---------------------------------------------------------------------------


def _new_boss_function_bodies(html: str) -> str:
    """Concatenate every NEW boss* function body for grep assertions.

    The legacy bossApplyCorrect / bossUseHint / bossUpdateHP / bossUpdateCombo
    / bossEnd / bossRenderQuestion / bossNorm are EXCLUDED — those are
    pre-existing and not part of this PR's surface.
    """
    chunks = []
    new_funcs = NEW_REQUIRED_FUNCTIONS + ["bossHandleAction"]
    for fn in new_funcs:
        pat = re.compile(
            rf"(?:async\s+)?function\s+{re.escape(fn)}\s*\([^)]*\)\s*\{{"
        )
        for m in pat.finditer(html):
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
            chunks.append(html[start:i])
    assert chunks, "no new boss* function bodies found"
    return "\n".join(chunks)


def test_no_client_side_correctness_logic(html_empty: str):
    bodies = _new_boss_function_bodies(html_empty)
    # New code must not reference server-only answer-key fields.
    for forbidden in ("q.acceptable", "q.accepted", "q.ans", "q.answer_spec"):
        assert forbidden not in bodies, (
            f"new boss* JS must not reference `{forbidden}` (server-only field)"
        )


# ---------------------------------------------------------------------------
# 12. i18n keys × 3 languages
# ---------------------------------------------------------------------------


REQUIRED_I18N_KEYS = [
    "boss.attempt_of",
    "boss.full_damage", "boss.half_damage", "boss.no_damage",
    "boss.combo_x2_activated",
    "boss.low_hp_warning",
    "boss.outcome.expert", "boss.outcome.strong",
    "boss.outcome.passing", "boss.outcome.hali_emas",
    "boss.stars.1", "boss.stars.2", "boss.stars.3",
    "boss.hint_used_amber",
    "boss.toast.wrong", "boss.toast.try_again",
    "boss.result.xp", "boss.result.summary",
]


@pytest.mark.parametrize("key", REQUIRED_I18N_KEYS)
def test_i18n_key_in_all_three_languages(html_empty: str, key: str):
    """Each new key must appear ≥3 times (uz/ru/en blocks)."""
    pat = re.compile(r"['\"]" + re.escape(key) + r"['\"]\s*:")
    matches = pat.findall(html_empty)
    assert len(matches) >= 3, (
        f"i18n key `{key}` must be defined in uz/ru/en (found {len(matches)})"
    )


# ---------------------------------------------------------------------------
# 13. Dark-mode CSS parity (≥10 selectors)
# ---------------------------------------------------------------------------


def test_dark_mode_boss_selectors_at_least_10(html_empty: str):
    pat = re.compile(
        r'\[data-theme="dark"\]\s+(?:\.boss-|#boss-)'
    )
    matches = pat.findall(html_empty)
    assert len(matches) >= 10, (
        f"dark-mode parity needs ≥10 selectors; found {len(matches)}"
    )


# ---------------------------------------------------------------------------
# 14. Result card structure — required children
# ---------------------------------------------------------------------------


def test_result_card_children(html_empty: str):
    """boss-result-card must contain title/stars/xp/summary children."""
    m = re.search(
        r'<div\s+id="boss-result-card"[^>]*>(.*?)</div>\s*<div\s+id="boss-victory"',
        html_empty,
        re.DOTALL,
    )
    assert m, "boss-result-card block not found in expected position"
    inner = m.group(1)
    for child in ("boss-result-title", "boss-result-stars",
                   "boss-result-xp", "boss-result-summary"):
        assert f'id="{child}"' in inner, (
            f"boss-result-card must contain #{child}"
        )


# ---------------------------------------------------------------------------
# 15. Mythical guard — bossUpdateAttemptPill hides pill when boss_type='mythical'
# ---------------------------------------------------------------------------


def test_mythical_pill_hidden(html_empty: str):
    """When BOSS_META.boss_type === 'mythical', attempt pill must be hidden."""
    m = re.search(
        r"function\s+bossUpdateAttemptPill\s*\([^)]*\)\s*\{(.*?)\n\s{8}(?:async\s+)?function\s+\w",
        html_empty,
        re.DOTALL,
    )
    assert m, "bossUpdateAttemptPill body not found"
    body = m.group(1)
    # Must reference 'mythical' explicitly and set display:none.
    assert "mythical" in body, "bossUpdateAttemptPill must explicitly handle mythical"
    assert re.search(r"style\.display\s*=\s*['\"]none['\"]", body), (
        "bossUpdateAttemptPill must hide pill in some branch"
    )


# ---------------------------------------------------------------------------
# 16. completePhase('boss') called from bossRenderResult
# ---------------------------------------------------------------------------


def test_render_result_calls_complete_phase(html_empty: str):
    m = re.search(
        r"function\s+bossRenderResult\s*\([^)]*\)\s*\{(.*?)\n\s{8}function\s+\w",
        html_empty,
        re.DOTALL,
    )
    assert m, "bossRenderResult body not found"
    body = m.group(1)
    assert re.search(r"completePhase\s*\(\s*['\"]boss['\"]\s*\)", body), (
        "bossRenderResult must call completePhase('boss')"
    )


# ---------------------------------------------------------------------------
# 17. Existing legacy preserved (bossApplyCorrect / bossUpdateHP / etc.)
# ---------------------------------------------------------------------------


LEGACY_FUNCTIONS_PRESERVED = [
    "bossApplyCorrect",
    "bossUpdateHP",
    "bossUpdateCombo",
    "bossEnd",
    "bossRenderQuestion",
    "bossNorm",
    "startFinalBoss",
    "bossUseHint",
]


@pytest.mark.parametrize("fn", LEGACY_FUNCTIONS_PRESERVED)
def test_legacy_function_preserved(html_empty: str, fn: str):
    pat = re.compile(
        rf"\bfunction\s+{re.escape(fn)}\s*\(|\basync\s+function\s+{re.escape(fn)}\s*\("
    )
    assert pat.search(html_empty), (
        f"legacy function `{fn}` must be preserved (do not remove)"
    )


# ---------------------------------------------------------------------------
# 18. bossHandleAction is async
# ---------------------------------------------------------------------------


def test_boss_handle_action_is_async(html_empty: str):
    pat = re.compile(r"async\s+function\s+bossHandleAction\s*\(")
    assert pat.search(html_empty), (
        "bossHandleAction must be async (it awaits bossSubmitAnswer)"
    )


# ---------------------------------------------------------------------------
# 19. Hint-cost path in bossHandleResponse uses server resp.hp_remaining,
#     NOT a hardcoded +5/+10/+15 calculation in NEW code.
# ---------------------------------------------------------------------------


def _boss_handle_response_body(html: str) -> str:
    m = re.search(
        r"function\s+bossHandleResponse\s*\([^)]*\)\s*\{",
        html,
    )
    assert m, "bossHandleResponse not found"
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


def test_hint_cost_from_server(html_empty: str):
    """bossHandleResponse must use resp.hp_remaining, not hardcoded +N HP arithmetic."""
    body = _boss_handle_response_body(html_empty)
    # Must reference the server-side HP field.
    assert "hp_remaining" in body, (
        "bossHandleResponse must read server's resp.hp_remaining"
    )
    # Must NOT contain hardcoded +5/+10/+15 hint-cost arithmetic.
    forbidden = re.compile(r"\.hp\s*\+=\s*(?:5|10|15)\b|hp\s*\+\s*(?:5|10|15)\s*[;,)]")
    assert not forbidden.search(body), (
        "bossHandleResponse must not hardcode +5/+10/+15 hint-cost arithmetic"
    )


# ---------------------------------------------------------------------------
# 20. __sessionLog push intact in bossApplyCorrect — AMR scorecard depends on it
# ---------------------------------------------------------------------------


def test_session_log_push_shape_preserved(html_empty: str):
    m = re.search(
        r"function\s+bossApplyCorrect\s*\([^)]*\)\s*\{",
        html_empty,
    )
    assert m, "bossApplyCorrect not found"
    start = m.end()
    depth = 1
    i = start
    while i < len(html_empty) and depth > 0:
        c = html_empty[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    body = html_empty[start:i]
    # Required entry shape — AMR scorecard reads these.
    for marker in (
        "__sessionLog",
        "phase: 'final-boss'",
        "correct: true",
        "first_try",
        "damage:",
    ):
        assert marker in body, (
            f"bossApplyCorrect's __sessionLog.push entry must preserve `{marker}`"
        )


# ---------------------------------------------------------------------------
# 21. BOSS_META global wiring — null when meta absent, populated otherwise
# ---------------------------------------------------------------------------


def test_boss_meta_null_when_absent(html_empty: str):
    """When boss_meta is None, the substituted BOSS_META is null."""
    m = re.search(r"const\s+BOSS_META\s*=\s*(.*?);", html_empty)
    assert m, "BOSS_META assignment missing"
    val = m.group(1).strip()
    assert val == "null", (
        f"BOSS_META should be null when boss_meta absent; got `{val[:40]}`"
    )


def test_boss_meta_populated_when_present(html_with_boss: str):
    m = re.search(r"const\s+BOSS_META\s*=\s*(.*?);", html_with_boss)
    assert m, "BOSS_META assignment missing"
    val = m.group(1).strip()
    assert val != "null", "BOSS_META must be populated when boss_meta provided"
    parsed = json.loads(val)
    assert parsed.get("boss_type") == "sub"
    assert parsed.get("attempts_max") == 2
