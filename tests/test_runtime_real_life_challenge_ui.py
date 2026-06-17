"""Regression tests for the Real-Life Challenge runtime UI (PR #N+1, frontend).

Pins the contract between this PR's frontend work and the backend's
phase=real-life-challenge endpoint:
- #rlc-screen root markup with `screen` class (so screen-cleanup loops work)
- All required structural IDs (topbar, hero, 5 step hosts, result card, dock, toast)
- rlcState initial declaration with required fields
- ~14 rlc* functions present
- handleAction dispatch branch routes to rlcHandleAction when RLC_CASE non-null
- rlcCheckStep reads ctx.hwId FIRST (not ctx.homework_id) — TM #140 lesson
- rlcCheckStep POSTs phase='real-life-challenge'
- i18n keys (rlc.*) present in all 3 runtime languages
- Dark-mode CSS parity (≥15 [data-theme="dark"] .rlc-* selectors)
- Answer-leak guard: rendered RLC_CASE contains zero is_correct / consequence /
  acceptable_keywords inside the JS literal (also tested by injector tests, but
  pinned here at the runtime template layer)
- No client-side correctness logic in rlc* function bodies
- Per-step retry gate via attemptsByStep + correct_option_label
- completePhase('realLife') called from rlcRenderResult
- Legacy RL_SCENARIO / startStage6 / rl-q1..rl-q6 markers preserved
- rlcShowToast 1800ms auto-dismiss
- Result card rubric IDs present
- Reasoning textarea references min_chars + charcount
- RLC_CASE consumed (expert_role / title / intro / steps[])

Companion to:
- tests/test_runtime_tile_match_ui.py (reference shape)
- tests/test_real_life_challenge_injector.py (server-side strip pinned)
- tests/test_real_life_challenge_schema.py (schema invariants pinned)
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
        "meta": {"title": "RLC UI Smoke", "subject_display": "X", "section": "", "cefr_level": ""},
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
        "real_life": None,
        "real_life_challenge": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }


def _rlc_case_fixture() -> dict:
    """Populated RLC case used to test the answer-leak gate end-to-end."""
    return {
        "id": "rlc_test_001",
        "expert_role": "fire_inspector",
        "title": "Test fire-safety case",
        "intro": "A bazaar has wood-frame stalls in narrow rows.",
        "pisa_level": "L4",
        "tier": "basic",
        "grade_band": "g7_9",
        "variant": "standard",
        "steps": [
            {
                "id": "step1", "kind": "decision",
                "title": "Step 1", "prompt": "Initial assessment.",
                "options": [
                    {"id": "a", "label": "Evacuate now", "is_correct": True,  "consequence": "Lives saved"},
                    {"id": "b", "label": "Wait and watch", "is_correct": False, "consequence": "Fire spreads"},
                ],
            },
            {
                "id": "step2", "kind": "info_request",
                "title": "Step 2", "prompt": "Info to request.",
                "options": [
                    {"id": "x", "label": "Egress map",  "is_correct": True,  "info_cost": {"time": "high"}},
                    {"id": "y", "label": "Lunch break", "is_correct": False, "info_cost": {"budget": "low"}},
                ],
            },
            {
                "id": "step3", "kind": "final_decision",
                "title": "Step 3", "prompt": "Final call.",
                "options": [
                    {"id": "p", "label": "Order shutdown", "is_correct": True,  "consequence": "Stalls saved"},
                    {"id": "q", "label": "Issue warning",  "is_correct": False, "consequence": "Confusion"},
                ],
            },
            {
                "id": "step4", "kind": "concept_select",
                "title": "Step 4", "prompt": "Pick the concept.",
                "concept_chips": [
                    {"id": "c1", "label": "Compartmentation", "is_correct": True},
                    {"id": "c2", "label": "Branding",         "is_correct": False},
                    {"id": "c3", "label": "Color theory",     "is_correct": False},
                ],
            },
            {
                "id": "step5", "kind": "reasoning",
                "title": "Step 5", "prompt": "Explain your reasoning.",
                "placeholder": "Type at least 80 chars",
                "min_chars": 80,
                "acceptable_keywords": ["egress", "compartment", "evacuation"],
            },
        ],
    }


@pytest.fixture(scope="module")
def html_empty() -> str:
    return _inject_full(_empty_content(), runtime_context={"hw_id": "HW-RLC-EMPTY", "subject": "math", "grade": 8})


@pytest.fixture(scope="module")
def html_with_case() -> str:
    body = _empty_content()
    body["real_life_challenge"] = _rlc_case_fixture()
    return _inject_full(body, runtime_context={"hw_id": "HW-RLC-1", "subject": "math", "grade": 8})


# ---------------------------------------------------------------------------
# 1. #rlc-screen presence + class screen
# ---------------------------------------------------------------------------


def test_rlc_screen_present_with_screen_class(html_empty: str):
    """#rlc-screen must exist and carry the `screen` CSS class so screen-cleanup loops work."""
    assert 'id="rlc-screen"' in html_empty, "#rlc-screen is missing from the template"
    # The order of class/id attrs varies — accept either ordering.
    pat = re.compile(
        r'<div[^>]*(?:'
        r'id="rlc-screen"[^>]*class="[^"]*\bscreen\b[^"]*"'
        r'|'
        r'class="[^"]*\bscreen\b[^"]*"[^>]*id="rlc-screen"'
        r')'
    )
    assert pat.search(html_empty), "#rlc-screen must carry class=\"screen\" (PR #136 lesson)"


# ---------------------------------------------------------------------------
# 2. Required structural IDs
# ---------------------------------------------------------------------------


REQUIRED_IDS = [
    "rlc-progress-dots", "rlc-step-counter",
    "rlc-role-badge", "rlc-xp-pill", "rlc-title", "rlc-subtitle",
    "rlc-step-1", "rlc-step-2", "rlc-step-3", "rlc-step-4", "rlc-step-5",
    "rlc-reasoning-textarea", "rlc-reasoning-charcount",
    "rlc-result-card",
    "rlc-rubric-decision", "rlc-rubric-reasoning", "rlc-rubric-concept",
    "rlc-rubric-bonus", "rlc-rubric-total",
    "rlc-toast", "rlc-dock", "rlc-submit-btn",
]


@pytest.mark.parametrize("id_", REQUIRED_IDS)
def test_required_structural_ids_present(html_empty: str, id_: str):
    assert f'id="{id_}"' in html_empty, f"required #{id_} is missing"


# ---------------------------------------------------------------------------
# 3. rlcState initial declaration + required fields
# ---------------------------------------------------------------------------


def test_rlc_state_declaration_and_fields(html_empty: str):
    assert "const rlcState = {" in html_empty, "rlcState declaration missing"
    required_field_names = [
        "case",
        "stepIndex",
        "sessionId",
        "selectedOptionId",
        "selectedChipId",
        "reasoningDraft",
        "stepResults",
        "rubric",
        "busy",
        "complete",
        "outcome",
        "totalXp",
        "attemptsByStep",
        "_toastTimer",
    ]
    for name in required_field_names:
        assert re.search(rf'\b{re.escape(name)}\s*:', html_empty), (
            f"rlcState missing required field `{name}`"
        )


# ---------------------------------------------------------------------------
# 4. Required ~14 rlc* functions present
# ---------------------------------------------------------------------------


REQUIRED_FUNCTIONS = [
    "rlcInit",
    "startRLCStage6",
    "rlcRenderStep",
    "rlcRenderDecisionStep",
    "rlcRenderConceptStep",
    "rlcRenderReasoningStep",
    "rlcSelectOption",
    "rlcSelectChip",
    "rlcOnReasoningInput",
    "rlcHandleAction",
    "rlcCheckStep",
    "rlcHandleResponse",
    "rlcRenderResult",
    "rlcShowToast",
]


@pytest.mark.parametrize("fn", REQUIRED_FUNCTIONS)
def test_required_function_present(html_empty: str, fn: str):
    pat = re.compile(rf'\bfunction\s+{re.escape(fn)}\s*\(|\basync\s+function\s+{re.escape(fn)}\s*\(')
    assert pat.search(html_empty), f"required JS function `{fn}` missing"


# ---------------------------------------------------------------------------
# 5. handleAction dispatch branch
# ---------------------------------------------------------------------------


def test_handle_action_routes_to_rlc_when_case_present(html_empty: str):
    """state.stage === 6 && RLC_CASE → rlcHandleAction()."""
    assert re.search(
        r'state\.stage\s*===\s*6\s*&&\s*RLC_CASE[^;]*rlcHandleAction',
        html_empty,
    ), "dispatch branch missing — RLC_CASE non-null path must call rlcHandleAction"


# ---------------------------------------------------------------------------
# 6. rlcCheckStep reads ctx.hwId FIRST (TM #140 lesson)
# ---------------------------------------------------------------------------


def _rlc_check_step_body(html: str) -> str:
    """Extract the rlcCheckStep function body (rough — until the next bare top-level `function ` line)."""
    m = re.search(
        r'async\s+function\s+rlcCheckStep\s*\([^)]*\)\s*\{(.*?)\n\s{8}function\s+\w',
        html,
        re.DOTALL,
    )
    assert m, "could not locate rlcCheckStep body"
    return m.group(1)


def test_rlc_check_step_reads_hwId_first(html_empty: str):
    body = _rlc_check_step_body(html_empty)
    # `ctx.hwId` must appear and must come BEFORE `ctx.homework_id` if the latter is present at all.
    hwid_pos = body.find("ctx.hwId")
    homework_id_pos = body.find("ctx.homework_id")
    assert hwid_pos != -1, "rlcCheckStep must read ctx.hwId"
    if homework_id_pos != -1:
        assert hwid_pos < homework_id_pos, (
            "ctx.hwId must be probed FIRST before ctx.homework_id (TM #140 lesson)"
        )


# ---------------------------------------------------------------------------
# 7. rlcCheckStep POSTs to /api/ai/check-answer with phase=real-life-challenge
# ---------------------------------------------------------------------------


def test_rlc_check_step_posts_correct_endpoint_and_phase(html_empty: str):
    body = _rlc_check_step_body(html_empty)
    assert "/api/ai/check-answer" in body, "rlcCheckStep must POST to /api/ai/check-answer"
    assert re.search(r"phase\s*:\s*'real-life-challenge'", body), (
        "rlcCheckStep payload must set phase: 'real-life-challenge'"
    )
    assert re.search(r"method\s*:\s*'POST'", body), "rlcCheckStep must use POST"


# ---------------------------------------------------------------------------
# 8. i18n keys present in all 3 languages (uz/ru/en)
# ---------------------------------------------------------------------------


REQUIRED_I18N_KEYS = [
    "rlc.eyebrow", "rlc.title", "rlc.subtitle",
    "rlc.step.decision", "rlc.step.info", "rlc.step.final",
    "rlc.step.concept", "rlc.step.reasoning",
    "rlc.dock.continue", "rlc.dock.submit", "rlc.dock.next", "rlc.dock.finish",
    "rlc.outcome.expert_decision", "rlc.outcome.strong_analysis",
    "rlc.outcome.passing", "rlc.outcome.hali_emas",
    "rlc.toast.correct", "rlc.toast.wrong", "rlc.toast.try_again", "rlc.toast.locked",
    "rlc.role.fire_inspector", "rlc.role.structural_engineer",
    "rlc.role.business_consultant", "rlc.role.medical_diagnostician",
    "rlc.role.agronomist", "rlc.role.teacher", "rlc.role.lawyer",
    "rlc.role.city_planner", "rlc.role.epidemiologist", "rlc.role.ethicist",
    "rlc.role.historian", "rlc.role.general",
    "rlc.placeholder.reasoning", "rlc.charcount",
    "rlc.consequence_reveal", "rlc.correct_was",
]


@pytest.mark.parametrize("key", REQUIRED_I18N_KEYS)
def test_i18n_key_in_all_three_languages(html_empty: str, key: str):
    """Each required key must appear ≥3 times (one per language block)."""
    # Quote-tolerant: match either 'rlc.x':  or "rlc.x":
    pat = re.compile(r"['\"]" + re.escape(key) + r"['\"]\s*:")
    matches = pat.findall(html_empty)
    assert len(matches) >= 3, (
        f"i18n key `{key}` must be defined in uz/ru/en (found {len(matches)} occurrences)"
    )


# ---------------------------------------------------------------------------
# 9. Dark-mode CSS parity (≥15 selectors)
# ---------------------------------------------------------------------------


def test_dark_mode_rlc_selectors_at_least_15(html_empty: str):
    """At least 15 [data-theme="dark"] .rlc-* (or #rlc-*) selectors for parity."""
    pat = re.compile(r'\[data-theme="dark"\]\s+(?:\.rlc-|#rlc-)')
    matches = pat.findall(html_empty)
    assert len(matches) >= 15, (
        f"dark-mode parity needs ≥15 selectors; found {len(matches)}"
    )


# ---------------------------------------------------------------------------
# 10. Answer-leak guard — server-only fields stripped from rendered RLC_CASE
# ---------------------------------------------------------------------------


def _extract_rlc_case_literal(html: str) -> str:
    """Pull out the substituted RLC_CASE = ... ; literal."""
    m = re.search(r'const\s+RLC_CASE\s*=\s*(.*?);\s*\n', html, re.DOTALL)
    assert m, "RLC_CASE assignment missing"
    return m.group(1)


def test_rlc_case_literal_strips_server_only_fields(html_with_case: str):
    """Rendered RLC_CASE JS literal must NOT contain is_correct / consequence /
    acceptable_keywords inside the case JSON. Pinned at the runtime layer too,
    not just the injector."""
    literal = _extract_rlc_case_literal(html_with_case)
    # The literal is a JSON-escaped object emitted by _safe_js_json. Decode it.
    parsed = json.loads(literal)
    # Walk the structure and assert no banned keys anywhere.
    BANNED = {"is_correct", "consequence", "acceptable_keywords"}

    def walk(obj, path="$"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in BANNED, (
                    f"server-only field `{k}` leaked into RLC_CASE at {path}"
                )
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    walk(parsed)


def test_rlc_case_literal_preserves_student_visible_fields(html_with_case: str):
    """Student-visible fields stay in the literal — id, label, prompt, title, expert_role, etc."""
    literal = _extract_rlc_case_literal(html_with_case)
    parsed = json.loads(literal)
    assert parsed.get("expert_role") == "fire_inspector"
    assert parsed.get("title")
    assert parsed.get("intro")
    steps = parsed.get("steps") or []
    assert len(steps) == 5
    # Each option keeps id + label.
    for step in steps:
        if step.get("options"):
            for opt in step["options"]:
                assert "id" in opt and "label" in opt


# ---------------------------------------------------------------------------
# 11. No client-side correctness logic in rlc* function bodies
# ---------------------------------------------------------------------------


def _all_rlc_function_bodies(html: str) -> str:
    """Concatenate every rlc*/startRLCStage6 function body for grep-style assertions."""
    chunks = []
    pat = re.compile(
        r'(?:async\s+)?function\s+(?:rlc\w+|startRLCStage6)\s*\([^)]*\)\s*\{',
    )
    for m in pat.finditer(html):
        start = m.end()
        depth = 1
        i = start
        while i < len(html) and depth > 0:
            c = html[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            i += 1
        chunks.append(html[start:i])
    assert chunks, "could not extract any rlc* function bodies"
    return "\n".join(chunks)


def test_no_client_side_correctness_logic(html_empty: str):
    bodies = _all_rlc_function_bodies(html_empty)
    # Forbidden client-side answer-key patterns. `consequence` is allowed
    # because the server returns it on wrong-attempt responses (per plan §3c).
    for forbidden in ("is_correct", "correctAnswer", "acceptable_keywords"):
        assert forbidden not in bodies, (
            f"rlc* JS must not reference `{forbidden}` (server-only field)"
        )


# ---------------------------------------------------------------------------
# 12. Per-step retry gate — attemptsByStep + correct_option_label
# ---------------------------------------------------------------------------


def test_retry_gate_uses_attempts_and_correct_option_label(html_empty: str):
    bodies = _all_rlc_function_bodies(html_empty)
    assert "attemptsByStep" in bodies, (
        "per-step retry tracking via attemptsByStep is missing"
    )
    assert "correct_option_label" in bodies, (
        "pedagogical reveal must read resp.correct_option_label after attempt 2"
    )


# ---------------------------------------------------------------------------
# 13. completePhase('realLife') called from rlcRenderResult
# ---------------------------------------------------------------------------


def test_render_result_calls_complete_phase(html_empty: str):
    """rlcRenderResult must fire completePhase('realLife')."""
    m = re.search(
        r'function\s+rlcRenderResult\s*\([^)]*\)\s*\{(.*?)^\s{8}function\s+\w',
        html_empty,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "rlcRenderResult body not found"
    body = m.group(1)
    assert re.search(r"completePhase\(\s*['\"]realLife['\"]\s*\)", body), (
        "rlcRenderResult must call completePhase('realLife')"
    )


# ---------------------------------------------------------------------------
# 14. Legacy preserved — startStage6 / RL_SCENARIO / rl-card / rl-q1..rl-q6
# ---------------------------------------------------------------------------


def test_legacy_real_life_markers_preserved(html_empty: str):
    """The legacy RL flow must coexist (NOT replace) with the new RLC flow."""
    assert "function startStage6" in html_empty, "legacy startStage6 was removed"
    assert "const RL_SCENARIO" in html_empty, "legacy RL_SCENARIO global was removed"
    assert 'id="rl-card"' in html_empty, "legacy rl-card markup was removed"
    for i in range(1, 7):
        assert f'id="rl-q{i}"' in html_empty, f"legacy rl-q{i} markup was removed"
    # Legacy rl.* i18n keys still around (smoke).
    assert "'rl.task_badge'" in html_empty or '"rl.task_badge"' in html_empty, (
        "legacy rl.* i18n keys were removed"
    )


# ---------------------------------------------------------------------------
# 15. rlcShowToast 1800ms auto-dismiss + _toastTimer
# ---------------------------------------------------------------------------


def test_show_toast_uses_timer_and_1800ms(html_empty: str):
    m = re.search(
        r'function\s+rlcShowToast\s*\([^)]*\)\s*\{(.*?)^\s{8}function\s+\w',
        html_empty,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "rlcShowToast body not found"
    body = m.group(1)
    assert "_toastTimer" in body, "rlcShowToast must use _toastTimer"
    assert "1800" in body, "rlcShowToast must auto-dismiss at 1800ms"
    assert "setTimeout" in body, "rlcShowToast must use setTimeout"


# ---------------------------------------------------------------------------
# 16. Result card has the four rubric IDs
# ---------------------------------------------------------------------------


def test_result_card_has_rubric_ids(html_empty: str):
    for rid in ("rlc-rubric-decision", "rlc-rubric-reasoning", "rlc-rubric-concept", "rlc-rubric-total"):
        assert f'id="{rid}"' in html_empty, f"#{rid} missing from result card"


# ---------------------------------------------------------------------------
# 17. Reasoning step references min_chars + renders charcount
# ---------------------------------------------------------------------------


def test_reasoning_step_uses_min_chars(html_empty: str):
    m = re.search(
        r'function\s+rlcRenderReasoningStep\s*\([^)]*\)\s*\{(.*?)^\s{8}function\s+\w',
        html_empty,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "rlcRenderReasoningStep body not found"
    body = m.group(1)
    assert re.search(r"\.min_chars\b|step\.min_chars", body), (
        "rlcRenderReasoningStep must read step.min_chars"
    )


def test_reasoning_input_handler_updates_charcount(html_empty: str):
    m = re.search(
        r'function\s+rlcOnReasoningInput\s*\([^)]*\)\s*\{(.*?)^\s{8}(?:async\s+)?function\s+\w',
        html_empty,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "rlcOnReasoningInput body not found"
    body = m.group(1)
    assert "rlc-reasoning-charcount" in body, (
        "rlcOnReasoningInput must update the charcount element"
    )


# ---------------------------------------------------------------------------
# 18. RLC_CASE consumed — JS reads expert_role / title / intro / steps[]
# ---------------------------------------------------------------------------


def test_rlc_case_globals_consumed(html_empty: str):
    bodies = _all_rlc_function_bodies(html_empty)
    assert re.search(r'\.expert_role\b', bodies), "JS must read RLC_CASE.expert_role"
    assert re.search(r'\.title\b', bodies), "JS must read RLC_CASE.title"
    assert re.search(r'\.intro\b', bodies), "JS must read RLC_CASE.intro"
    assert re.search(r'\.steps\b', bodies), "JS must read RLC_CASE.steps"


# ---------------------------------------------------------------------------
# 19. Stage activation hook — startRLCStage6 wired when RLC_CASE non-null
# ---------------------------------------------------------------------------


def test_stage_activation_branches_to_rlc_when_case_present(html_empty: str):
    """The setStage(6) call site must branch into startRLCStage6 when RLC_CASE non-null."""
    assert re.search(
        r'RLC_CASE\s*&&\s*typeof\s+startRLCStage6\s*===\s*[\'"]function[\'"][^;]*startRLCStage6\(\)',
        html_empty,
    ), "stage activation does not branch to startRLCStage6 when RLC_CASE is non-null"


# ---------------------------------------------------------------------------
# 20. Empty case path emits null literal (legacy fallback unchanged)
# ---------------------------------------------------------------------------


def test_rlc_case_emits_null_when_no_case(html_empty: str):
    """When real_life_challenge is None, RLC_CASE = null so legacy flow runs."""
    literal = _extract_rlc_case_literal(html_empty)
    assert literal.strip() == "null", (
        f"RLC_CASE must be `null` when no case is provided (got `{literal[:80]!r}`)"
    )
