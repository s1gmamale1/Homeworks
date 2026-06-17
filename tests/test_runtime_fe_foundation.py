"""Regression tests for the FE foundation runtime bridge (PR #192).

Pins three contracts that the foundation chunk introduced and one that
fixed a live 404 on the Plan-5 Boss bridge:

1. **Boss bridge URL contract** — `bossStart`, `bossGenerateQuestion`,
   `bossSubmitAnswer`, `bossState`, and `bossGiveUp` must POST to
   `/boss/...` paths under `_post(...)`. With `API_BASE = '/api/ai'`,
   the resolved URL is `/api/ai/boss/...`. Before the fix, paths were
   `/ai/boss/...` which resolved to `/api/ai/ai/boss/...` → 404.

2. **`submitRuntimeAnswer` bridge** — must exist as `async function`,
   POST to `/runtime/submit-answer` (resolves to
   `/api/ai/runtime/submit-answer`), and be exposed on `window.NETS_AI`.

3. **Event bridge new kinds** — `nets:submit` must route the new kinds
   to the new implementations:
     - `'answer'`        → `submitRuntimeAnswer`
     - `'boss-answer'`   → `bossSubmitAnswer`
     - `'boss-generate'` → `bossGenerateQuestion`
     - `'tutor-chat'`    → `tutorChat`
     - `'reflection'`    → `reflectionFeedback`
   Legacy kinds preserved as `'legacy-*'` for older templates plus
   back-compat aliases for bare `'boss'`/`'tutor'`.

4. **No bare `kind: 'answer'` callers** — proves the routing flip from
   legacy `checkAnswer` → `submitRuntimeAnswer` is safe (no caller in
   `server/template/` dispatches a bare `kind: 'answer'` payload).

Companion to:
- tests/test_homework_page.py::test_runtime_js_exposes_new_methods
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
    _html = os.path.join(_repo_root(), "server", "template", "perfect_homework.html")
    _js = os.path.join(_repo_root(), "server", "template", "js", "perfect_homework.js")
    _css = os.path.join(_repo_root(), "server", "template", "static", "css", "perfect_homework.css")
    _tutor = os.path.join(_repo_root(), "server", "template", "static", "js", "tutor.js")
    with open(_html, "r", encoding="utf-8") as f:
        content = f.read()
    with open(_js, "r", encoding="utf-8") as f:
        content += "\n" + f.read()
    with open(_css, "r", encoding="utf-8") as f:
        content += "\n" + f.read()
    with open(_tutor, "r", encoding="utf-8") as f:
        content += "\n" + f.read()
    return content


# ---------------------------------------------------------------------------
# 1. Boss bridge URL contract — fixes the double-/ai/ 404 bug
# ---------------------------------------------------------------------------

BOSS_FNS = (
    "bossStart",
    "bossGenerateQuestion",
    "bossSubmitAnswer",
    "bossState",
    "bossGiveUp",
)

BOSS_FN_TO_PATH = {
    "bossStart":             "/boss/start",
    "bossGenerateQuestion":  "/boss/generate-question",
    "bossSubmitAnswer":      "/boss/submit-answer",
    "bossState":             "/boss/state",
    "bossGiveUp":            "/boss/give-up",
}


def test_api_base_is_api_ai(runtime_js: str):
    """Sanity: API_BASE pins the prefix used by every _post(...) call."""
    assert "'/api/ai'" in runtime_js, (
        "runtime.js API_BASE no longer hard-codes /api/ai — the path-resolution "
        "math in this test file (and in the bug fix) depends on it."
    )


def _function_window(src: str, fn_name: str, span: int = 800) -> str:
    """Return a bounded window of source starting at the `async function fn_name`
    declaration. Avoids brace-matching pitfalls when function bodies contain
    nested object literals.
    """
    decl = f"async function {fn_name}("
    idx = src.find(decl)
    assert idx != -1, f"runtime.js missing async function {fn_name}"
    return src[idx : idx + span]


@pytest.mark.parametrize("fn_name,expected_path", list(BOSS_FN_TO_PATH.items()))
def test_boss_bridge_uses_correct_path(runtime_js: str, fn_name: str, expected_path: str):
    """Plan-5 Boss bridge functions must POST to /boss/... (resolves under
    /api/ai prefix), NOT /ai/boss/... (which resolved to /api/ai/ai/boss/...
    → 404 against the real route).
    """
    window = _function_window(runtime_js, fn_name)
    assert f"_post('{expected_path}'" in window, (
        f"{fn_name} must call _post('{expected_path}', ...) "
        f"so the resolved URL is /api/ai{expected_path}"
    )


def test_no_double_ai_prefix_anywhere(runtime_js: str):
    """Belt-and-suspenders: no _post call in runtime.js should pass a path
    starting with `/ai/...` because API_BASE already prefixes /api/ai.
    """
    # Find every _post('<path>', ...) call.
    bad = re.findall(r"_post\('(/ai/[^']+)'", runtime_js)
    assert bad == [], (
        f"runtime.js has _post calls with /ai/ prefix that would resolve to "
        f"/api/ai/ai/... (the very bug PR #192 fixed). Offenders: {bad}"
    )


# ---------------------------------------------------------------------------
# 2. submitRuntimeAnswer bridge (FE-1)
# ---------------------------------------------------------------------------


def test_submit_runtime_answer_exists(runtime_js: str):
    assert "async function submitRuntimeAnswer(" in runtime_js, (
        "runtime.js must define `async function submitRuntimeAnswer(opts)`"
    )


def test_submit_runtime_answer_uses_correct_path(runtime_js: str):
    """Backend route is /api/ai/runtime/submit-answer; with API_BASE=/api/ai
    the path passed to _post must be /runtime/submit-answer (no /ai/ prefix).
    """
    window = _function_window(runtime_js, "submitRuntimeAnswer", span=1200)
    assert "_post('/runtime/submit-answer'" in window, (
        "submitRuntimeAnswer must call _post('/runtime/submit-answer', ...) — "
        "anything else either 404s or hits the wrong endpoint."
    )


def test_submit_runtime_answer_exposed_on_nets_ai(runtime_js: str):
    """Must be reachable via window.NETS_AI.submitRuntimeAnswer."""
    export_block = runtime_js.split("window.NETS_AI = {", 1)[1].split("};", 1)[0]
    assert "submitRuntimeAnswer" in export_block, (
        "submitRuntimeAnswer must be in the window.NETS_AI export block"
    )


def test_submit_runtime_answer_uses_collect_runtime_context(runtime_js: str):
    """submitRuntimeAnswer must reuse collectRuntimeContext for canonical
    phase / subphase / question_id / student_work_text discovery — no
    inline reinvention of that logic.
    """
    window = _function_window(runtime_js, "submitRuntimeAnswer", span=1200)
    assert "collectRuntimeContext" in window, (
        "submitRuntimeAnswer must call collectRuntimeContext(opts) so the "
        "request context matches what tutorChat sees."
    )


# ---------------------------------------------------------------------------
# 3. nets:submit event bridge new kinds (FE-2)
# ---------------------------------------------------------------------------


def _event_bridge_body(runtime_js: str) -> str:
    """Return the body of the document.addEventListener('nets:submit', ...) handler."""
    match = re.search(
        r"document\.addEventListener\('nets:submit',\s*async\s*\(ev\)\s*=>\s*\{(.*?)\n\s*\}\);",
        runtime_js,
        re.DOTALL,
    )
    assert match, "nets:submit listener not found in runtime.js"
    return match.group(1)


@pytest.mark.parametrize(
    "kind,fn_name",
    [
        ("answer",        "submitRuntimeAnswer"),   # NEW: was checkAnswer
        ("boss-answer",   "bossSubmitAnswer"),      # NEW
        ("boss-generate", "bossGenerateQuestion"),  # NEW
        ("tutor-chat",    "tutorChat"),             # NEW
        ("reflection",    "reflectionFeedback"),    # preserved
    ],
)
def test_event_bridge_routes_new_kinds(runtime_js: str, kind: str, fn_name: str):
    body = _event_bridge_body(runtime_js)
    pattern = rf"kind\s*===\s*'{re.escape(kind)}'\s*\)\s*result\s*=\s*await\s+{re.escape(fn_name)}\("
    assert re.search(pattern, body), (
        f"nets:submit kind '{kind}' must route to await {fn_name}(payload)"
    )


@pytest.mark.parametrize(
    "kind,fn_name",
    [
        ("legacy-answer", "checkAnswer"),
        ("legacy-boss",   "bossTurn"),
        ("legacy-tutor",  "tutor"),
    ],
)
def test_event_bridge_preserves_legacy_kinds(runtime_js: str, kind: str, fn_name: str):
    """Old templates can opt into the legacy implementations explicitly."""
    body = _event_bridge_body(runtime_js)
    pattern = rf"kind\s*===\s*'{re.escape(kind)}'\s*\)\s*result\s*=\s*await\s+{re.escape(fn_name)}\("
    assert re.search(pattern, body), (
        f"nets:submit kind '{kind}' must route to await {fn_name}(payload) "
        "for back-compat with older templates"
    )


def test_event_bridge_back_compat_aliases(runtime_js: str):
    """Bare `kind: 'boss'` and `kind: 'tutor'` (no 'legacy-' prefix) must
    still work for older homework HTML that hasn't migrated yet — they
    fall through to the legacy implementations.
    """
    body = _event_bridge_body(runtime_js)
    assert re.search(
        r"kind\s*===\s*'boss'\s*\)\s*result\s*=\s*await\s+bossTurn\(", body,
    ), "Bare kind:'boss' must alias to bossTurn for back-compat"
    assert re.search(
        r"kind\s*===\s*'tutor'\s*\)\s*result\s*=\s*await\s+tutor\(", body,
    ), "Bare kind:'tutor' must alias to legacy tutor() for back-compat"


def test_fallback_map_has_new_and_legacy_keys(runtime_js: str):
    """FALLBACK envelopes must exist for every kind the event bridge can
    dispatch, otherwise a network failure dispatches `undefined`.
    """
    fallback_match = re.search(
        r"const FALLBACK\s*=\s*\{(.*?)\};",
        runtime_js,
        re.DOTALL,
    )
    assert fallback_match, "FALLBACK map not found in runtime.js"
    fallback_block = fallback_match.group(1)
    required_keys = (
        # New kinds
        "'answer'",
        "'boss-answer'",
        "'boss-generate'",
        "'tutor-chat'",
        "'reflection'",
        # Legacy kinds
        "'legacy-answer'",
        "'legacy-boss'",
        "'legacy-tutor'",
    )
    for key in required_keys:
        assert key in fallback_block, f"FALLBACK map missing key {key}"


# ---------------------------------------------------------------------------
# 4. No bare `kind: 'answer'` callers in templates — proves the routing
#    flip from checkAnswer → submitRuntimeAnswer is safe.
# ---------------------------------------------------------------------------


def test_no_template_dispatches_bare_kind_answer():
    """Sigma flagged a back-compat risk: if any template dispatches a bare
    `kind: 'answer'` event with the OLD payload shape (studentAnswer /
    expectedAnswers), it would now hit submitRuntimeAnswer with mismatched
    keys. This test proves no such caller exists in the template tree.
    """
    template_dir = os.path.join(_repo_root(), "server", "template")
    pattern = re.compile(r"kind:\s*['\"]answer['\"]")
    offenders: list[str] = []
    for root, _, files in os.walk(template_dir):
        for fname in files:
            if not (fname.endswith(".html") or fname.endswith(".js")):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                src = f.read()
            if pattern.search(src):
                offenders.append(fpath)
    assert offenders == [], (
        "Found template(s) dispatching bare `kind: 'answer'` — these would "
        "now route to submitRuntimeAnswer instead of legacy checkAnswer "
        "and may break if they use the old payload shape "
        "(studentAnswer / expectedAnswers). Either migrate them to the new "
        "shape or change kind to 'legacy-answer'. Offenders: "
        f"{offenders}"
    )


# ---------------------------------------------------------------------------
# 5. FE-3 partial: window.NETS_STATE mirror in perfect_homework.html
# ---------------------------------------------------------------------------


def test_sync_nets_state_helper_exists(perfect_homework_html: str):
    """The tutor widget IIFE must define syncNetsState() so window.NETS_STATE
    is populated for runtime.js#collectRuntimeContext fallback path.
    """
    assert "function syncNetsState()" in perfect_homework_html, (
        "perfect_homework.html missing syncNetsState() helper — without it "
        "window.NETS_STATE stays empty and tutor/answer-submit lose context."
    )
    assert "window.NETS_STATE.questionId = state.currentQuestionId" in perfect_homework_html
    assert "window.NETS_STATE.phase = state.currentPhase" in perfect_homework_html


def test_sync_nets_state_called_at_write_sites(perfect_homework_html: str):
    """Both write sites for state.currentQuestionId must call syncNetsState()
    so the global mirror stays in lockstep with the widget's internal state.
    """
    # The phase-change listener.
    phase_change_match = re.search(
        r"document\.addEventListener\('nets:phase-change',\s*\(ev\)\s*=>\s*\{(.*?)\n\s*\}\);",
        perfect_homework_html,
        re.DOTALL,
    )
    assert phase_change_match, "nets:phase-change listener not found"
    assert "syncNetsState()" in phase_change_match.group(1), (
        "syncNetsState() must be called inside the nets:phase-change listener"
    )

    # The CTA button click handler — find the wrong-answer CTA branch.
    cta_match = re.search(
        r"ctaBtn\.addEventListener\('click',\s*function\s*\(\)\s*\{(.*?)\n\s*\}\);",
        perfect_homework_html,
        re.DOTALL,
    )
    assert cta_match, "ctaBtn click handler not found"
    assert "syncNetsState()" in cta_match.group(1), (
        "syncNetsState() must be called inside the ctaBtn click handler "
        "since it writes state.currentQuestionId"
    )
