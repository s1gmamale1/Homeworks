"""Regression tests for FE-8 — network smoke pinning the endpoint sequence
the new AI architecture wants browser sessions to follow.

These are static-string-based tests (no live HTTP). They inspect the
rendered template and runtime.js and assert that the call chain a real
browser would build matches the new contract:

* **Tutor flow** — student types in tutor widget → `kind: 'tutor-chat'`
  event OR direct `window.NETS_AI.tutorChat(...)` call → POST to
  `/api/ai/tutor/chat` (runtime resolves `_post('/tutor/chat', ...)`
  under `API_BASE = '/api/ai'`).
* **Boss flow (Plan 5 dynamic)** — boss-phase entry → `bossStart`
  (`/boss/start`) → `bossGenerateQuestion` (`/boss/generate-question`)
  → loop of `bossSubmitAnswer` (`/boss/submit-answer`). NOT the legacy
  `/api/ai/boss-turn`.
* **Answer flow (FE-1)** — `kind: 'answer'` event → `submitRuntimeAnswer`
  → POST to `/api/ai/runtime/submit-answer`.

Companion to:
- tests/test_runtime_fe_foundation.py  (Boss URL contract)
- tests/test_runtime_fe5_dynamic_boss.py (if present)
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
def runtime_js() -> str:
    path = os.path.join(_repo_root(), "server", "template", "runtime.js")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def perfect_homework_html() -> str:
    _js = os.path.join(_repo_root(), "server", "template", "js", "perfect_homework.js")
    _css = os.path.join(_repo_root(), "server", "template", "static", "css", "perfect_homework.css")
    with open(_js, "r", encoding="utf-8") as f:
        content = f.read()
    with open(_css, "r", encoding="utf-8") as f:
        content += "\n" + f.read()
    return content


def _function_window(src: str, fn_name: str, span: int = 800) -> str:
    decl = f"async function {fn_name}("
    idx = src.find(decl)
    assert idx != -1, f"runtime.js missing async function {fn_name}"
    return src[idx : idx + span]


# ---------------------------------------------------------------------------
# 1. Tutor flow — `kind: 'tutor-chat'` → tutorChat → /api/ai/tutor/chat
# ---------------------------------------------------------------------------


def test_no_template_dispatches_kind_tutor(perfect_homework_html: str):
    """FE-7 migration is complete — no bare `kind: 'tutor'` dispatchers in
    perfect_homework.html. (Negative lookahead avoids matching
    `'tutor-chat'` / `'tutor-foo'`.)
    """
    pattern = re.compile(r"kind:\s*['\"]tutor['\"](?![-\w])")
    matches = pattern.findall(perfect_homework_html)
    assert matches == [], (
        "Found bare `kind: 'tutor'` dispatcher(s) in perfect_homework.html. "
        "Migrate to 'tutor-chat' or 'legacy-tutor'."
    )


def test_template_uses_kind_tutor_chat(perfect_homework_html: str, runtime_js: str):
    """At least one reference to `'tutor-chat'` must exist in the rendered
    template tree (runtime.js counts — the event bridge maps it).
    """
    pattern = re.compile(r"['\"]tutor-chat['\"]")
    assert pattern.search(runtime_js) or pattern.search(perfect_homework_html), (
        "No `'tutor-chat'` reference in runtime.js or perfect_homework.html — "
        "the new tutor-chat path is unwired."
    )


def test_tutor_chat_posts_to_tutor_chat_endpoint(runtime_js: str):
    """tutorChat must POST to /tutor/chat (resolves to /api/ai/tutor/chat)."""
    window = _function_window(runtime_js, "tutorChat", span=1200)
    assert "_post('/tutor/chat'" in window, (
        "tutorChat must call _post('/tutor/chat', ...) — anything else is wrong."
    )


# ---------------------------------------------------------------------------
# 2. Boss flow (Plan 5 dynamic) — bossStart → generate → submit loop
# ---------------------------------------------------------------------------


PLAN5_BOSS_PATHS = {
    "bossStart":             "/boss/start",
    "bossGenerateQuestion":  "/boss/generate-question",
    "bossSubmitAnswer":      "/boss/submit-answer",
}


@pytest.mark.parametrize("fn_name,expected_path", list(PLAN5_BOSS_PATHS.items()))
def test_boss_flow_uses_plan5_endpoints(runtime_js: str, fn_name: str, expected_path: str):
    """The Plan-5 boss bridge must POST to /boss/* paths (resolved under
    /api/ai/), NOT the legacy /api/ai/boss-turn.
    """
    window = _function_window(runtime_js, fn_name)
    assert f"_post('{expected_path}'" in window, (
        f"{fn_name} must call _post('{expected_path}', ...) for the Plan-5 flow."
    )


def test_no_boss_turn_in_plan5_bridge_functions(runtime_js: str):
    """The Plan-5 bridge functions must not call /boss-turn (the legacy
    single-shot endpoint).
    """
    for fn_name in PLAN5_BOSS_PATHS:
        window = _function_window(runtime_js, fn_name)
        assert "/boss-turn" not in window, (
            f"{fn_name} must not reference legacy /boss-turn — Plan-5 "
            "uses the multi-step /boss/start, /boss/generate-question, "
            "/boss/submit-answer endpoints."
        )


def test_boss_flow_exposed_on_nets_ai(runtime_js: str):
    """All three Plan-5 bridge functions must be exported on window.NETS_AI."""
    export_block = runtime_js.split("window.NETS_AI = {", 1)[1].split("};", 1)[0]
    for fn_name in PLAN5_BOSS_PATHS:
        assert fn_name in export_block, (
            f"{fn_name} must be exported on window.NETS_AI for templates to call it."
        )


# ---------------------------------------------------------------------------
# 3. Answer flow (FE-1) — `kind: 'answer'` → submitRuntimeAnswer
# ---------------------------------------------------------------------------


def test_runtime_answer_flow_uses_submit_runtime_answer(runtime_js: str):
    """submitRuntimeAnswer must POST to /runtime/submit-answer (resolves to
    /api/ai/runtime/submit-answer).
    """
    window = _function_window(runtime_js, "submitRuntimeAnswer", span=1200)
    assert "_post('/runtime/submit-answer'" in window, (
        "submitRuntimeAnswer must call _post('/runtime/submit-answer', ...)."
    )


def test_event_bridge_routes_answer_kind_to_submit_runtime_answer(runtime_js: str):
    """`kind: 'answer'` must route to `submitRuntimeAnswer` in the event
    bridge — not the legacy checkAnswer.
    """
    body_match = re.search(
        r"document\.addEventListener\('nets:submit',\s*async\s*\(ev\)\s*=>\s*\{(.*?)\n\s*\}\);",
        runtime_js,
        re.DOTALL,
    )
    assert body_match, "nets:submit listener not found in runtime.js"
    body = body_match.group(1)
    pattern = r"kind\s*===\s*'answer'\s*\)\s*result\s*=\s*await\s+submitRuntimeAnswer\("
    assert re.search(pattern, body), (
        "nets:submit kind 'answer' must route to await submitRuntimeAnswer(payload)."
    )


# ---------------------------------------------------------------------------
# 4. Negative — no direct fetch('/api/ai/check-answer'...) inside the
#    Plan-5 boss bridge code path (bossSubmitAnswer body).
# ---------------------------------------------------------------------------


def test_no_check_answer_in_dynamic_boss_branch(runtime_js: str):
    """The dynamic-mode bossSubmitAnswer must not bypass to the legacy
    /check-answer endpoint via direct fetch.
    """
    window = _function_window(runtime_js, "bossSubmitAnswer", span=600)
    assert "/check-answer" not in window, (
        "bossSubmitAnswer must not reference /check-answer — Plan-5 uses "
        "/boss/submit-answer which has its own grading."
    )
    assert "fetch(" not in window, (
        "bossSubmitAnswer must not bypass _post() with direct fetch() calls."
    )


# ---------------------------------------------------------------------------
# 5. API_BASE pin — guards the URL math used in every assertion above
# ---------------------------------------------------------------------------


def test_api_base_resolves_under_api_ai(runtime_js: str):
    """API_BASE prefix is the foundation under which every _post() URL
    resolves. If this changes, all paths above need to adjust.
    """
    assert "/api/ai" in runtime_js, (
        "runtime.js must contain '/api/ai' as the API_BASE prefix."
    )
