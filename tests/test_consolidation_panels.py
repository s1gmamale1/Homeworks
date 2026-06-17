"""Regression tests for the new Consolidation panels[] contract (Bug #7).

Pins the contracts that make Consolidation generic across mnemonic
techniques (Radiant Summary branches, Memory Palace stations, Link
System steps, Peg System pegs) instead of hardcoded to one shape:

  - Prompt OUTPUT REQUIREMENT documents the new {title, panels[], check?}
    schema and the legacy {mnemonic, lock_code, explanation} fallback.
  - Injector passes panels[] + media + check through to the CONSOLIDATION
    JS const so the runtime can render them as wave2 sliding panels.
  - Backward-compat: legacy fixtures (no panels[]) still get the old
    {mnemonic, bullets, check_prompt, check_answer} shape and render via
    the existing single-card renderer.
  - Adapter accepts both shapes from content_json and emits the right
    fields for the runtime + the legacy mirror.

If any of these regress, Consolidation either loses its generic-across-
techniques property or starts rejecting old homework rows.
"""

from __future__ import annotations

import re
from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent.parent / "server" / "prompts" / "english" / "consolidation.md"
INJECTOR_PATH = Path(__file__).resolve().parent.parent / "server" / "services" / "injector.py"

PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
INJECTOR_SRC = INJECTOR_PATH.read_text(encoding="utf-8")


# ---- Invariant 1: prompt OUTPUT REQUIREMENT specifies the new shape -------

def test_consolidation_prompt_output_requirement_has_panels_array():
    """Prompt must instruct the LLM to emit `panels:[...]` as the primary shape."""
    output_block_start = PROMPT.find("## OUTPUT REQUIREMENT")
    assert output_block_start != -1
    block = PROMPT[output_block_start:]
    assert '"panels"' in block, (
        "OUTPUT REQUIREMENT must show panels[] as the primary shape — that's "
        "the contract the wave2 sliding renderer reads"
    )
    assert '"check"' in block, (
        "OUTPUT REQUIREMENT must declare the optional check{prompt, answer} "
        "block for non-graded reveal-on-demand recall prompts"
    )


def test_consolidation_prompt_documents_panel_kinds_generically():
    """Panel `kind` documentation must list all techniques, not just one."""
    output_block_start = PROMPT.find("## OUTPUT REQUIREMENT")
    block = PROMPT[output_block_start:]
    # The kind enum must reference branch / station / step at minimum so the
    # prompt is readable for Radiant Summary, Memory Palace, AND Link System.
    assert "branch" in block.lower()
    assert "station" in block.lower()
    assert "step" in block.lower()


def test_consolidation_prompt_documents_check_block_is_not_graded():
    """The check block must explicitly say "NOT graded" / reveal-on-demand."""
    output_block_start = PROMPT.find("## OUTPUT REQUIREMENT")
    block = PROMPT[output_block_start:]
    # Either "NOT graded" or "not graded" + reveal-on-demand language.
    assert re.search(r"NOT graded|not graded", block), (
        "the check block must be explicitly documented as NOT graded so the "
        "LLM doesn't try to author auto-advance / correctness logic"
    )


def test_consolidation_prompt_keeps_legacy_shape_documented():
    """Legacy {mnemonic, lock_code, explanation} fallback must still be mentioned."""
    output_block_start = PROMPT.find("## OUTPUT REQUIREMENT")
    block = PROMPT[output_block_start:]
    # Backward-compat note explicitly mentions the legacy shape so anyone
    # auditing old fixtures knows they're still valid.
    assert "mnemonic" in block.lower()
    assert "Backward compatibility" in block or "backward compatibility" in block.lower()


# ---- Invariant 2: injector passes panels[] + check through ----------------

def _inject_consolidation(consolidation_payload):
    """Helper: inject() with content_json carrying just `consolidation` + `meta`,
    return the resulting `const CONSOLIDATION = {...};` text."""
    from server.services.injector import inject
    cj = {
        "meta": {"title": "T", "subject_display": "english", "section": "", "cefr_level": "B1"},
        "gate_quote": {"mode": "auto"},
        "panels": [], "flashcards": [], "memory_sprint": [],
        "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [],
        "gb_puzzle_lock": [], "gb_mystery_box": [], "gb_ttt": [],
        "boss_questions": [],
        "real_life": {}, "reading": {}, "reflection": {},
        "consolidation": consolidation_payload,
    }
    html = inject(cj, runtime_context={"lang": "uz", "subject": "english", "grade": 8, "hwId": "X", "homeworkSummary": ""})
    m = re.search(r"const CONSOLIDATION\s*=\s*(\{.*?\});", html, flags=re.DOTALL)
    assert m, "const CONSOLIDATION block not found in injected HTML"
    return m.group(1)


def test_injector_passes_panels_through_to_consolidation_const():
    """The new panels[] array survives injection into CONSOLIDATION JS const."""
    src = _inject_consolidation({
        "title": "Radiant Summary — Test",
        "panels": [
            {"kind": "center", "title": "Center", "html": "<p>seed</p>"},
            {"kind": "branch", "title": "Branch 1", "html": "<p>leaf-one</p>"},
            {"kind": "branch", "title": "Branch 2", "html": "<p>leaf-two</p>"},
        ],
    })
    assert '"panels":' in src, (
        "injector must pass panels[] through; without it the runtime falls "
        "back to legacy single-panel rendering and Bug #7 returns"
    )
    assert "leaf-one" in src and "leaf-two" in src
    # Each panel must carry kind, title, html
    assert '"kind":' in src
    assert '"title":' in src
    assert '"html":' in src


def test_injector_passes_panel_media_through():
    """Per-panel SVG media survives injection."""
    src = _inject_consolidation({
        "title": "T",
        "panels": [
            {
                "kind": "branch",
                "title": "Tree",
                "html": "<p>x</p>",
                "media": {"type": "svg", "html": "<svg id='branch-svg'></svg>"},
            },
        ],
    })
    assert '"media":' in src
    assert "branch-svg" in src


def test_injector_passes_check_block_through():
    """Optional `check` block (prompt + answer) lands in the const."""
    src = _inject_consolidation({
        "title": "T",
        "panels": [{"kind": "center", "title": "C", "html": "<p>x</p>"}],
        "check": {"prompt": "What is the lock code?", "answer": "FAM-LY-5"},
    })
    assert '"check":' in src
    assert "What is the lock code?" in src
    assert "FAM-LY-5" in src


def test_injector_omits_panels_when_legacy_only():
    """Legacy fixtures (no panels[]) don't get a stray panels:[] in the const."""
    src = _inject_consolidation({
        "title": "T",
        "mnemonic": "<p>old prose</p>",
        "lock_code": "ABC",
        "explanation": "first; second; third",
    })
    assert '"panels"' not in src, (
        "injector must NOT emit a panels key when content_json has none — "
        "the runtime's `Array.isArray(CONSOLIDATION.panels)` check would "
        "otherwise fire with an empty array and suppress the legacy renderer"
    )


def test_injector_legacy_shape_still_emits_mnemonic_bullets():
    """Legacy fixture (post-adapter shape) still gets all old runtime keys.

    Note: the adapter maps `lock_code` → `check_answer` before the data
    reaches the injector. The injector itself reads the post-adapter shape
    (`check_answer` directly), not raw prompt output. So this test sends
    the post-adapter shape and asserts the runtime const contains it.
    """
    src = _inject_consolidation({
        "title": "T",
        "mnemonic": "<p>old prose</p>",
        "bullets": ["alpha", "beta"],
        "check_prompt": "What's the lock?",
        "check_answer": "ABC",
    })
    assert '"mnemonic":' in src
    assert '"bullets":' in src
    assert '"check_answer":' in src
    assert '"ABC"' in src
    # bullets array elements survive
    assert '"alpha"' in src and '"beta"' in src


# ---- Invariant 3: kind/title/html structure preserved per panel -----------

def test_injector_normalizes_panel_kind_to_string():
    """Even if kind is missing/null, panel emits kind:"" (not undefined)."""
    src = _inject_consolidation({
        "title": "T",
        "panels": [
            {"title": "Untyped", "html": "<p>x</p>"},  # no kind
        ],
    })
    # The panel still emits kind, just empty.
    assert '"kind":' in src


def test_injector_drops_non_dict_panel_entries():
    """Garbage entries (strings, nulls) in panels[] don't crash injection."""
    src = _inject_consolidation({
        "title": "T",
        "panels": [
            "this is a string, not a dict",
            None,
            {"kind": "branch", "title": "Real", "html": "<p>real-panel</p>"},
        ],
    })
    # Real panel makes it through.
    assert "real-panel" in src


# ---- Invariant 4: runtime wiring (renderConsolidation dispatches by shape) -

_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _slice_function(name: str) -> str:
    start = TEMPLATE.find(f"function {name}(")
    assert start != -1, f"function {name} not found"
    after = TEMPLATE.find("\n        function ", start + 1)
    if after == -1:
        after = len(TEMPLATE)
    return TEMPLATE[start:after]


def test_consolidation_dom_has_wave2_stream_and_legacy_block():
    """Both DOM scaffolds must exist so renderConsolidation can pick one."""
    assert '<div class="wave2-slide-stream" id="cons-stream"' in TEMPLATE
    assert '<div class="wave2-dot-row" id="cons-dots"' in TEMPLATE
    assert '<div id="cons-legacy-block">' in TEMPLATE


def test_renderConsolidation_dispatches_on_panels_field():
    """renderConsolidation chooses path based on Array.isArray(CONSOLIDATION.panels)."""
    body = _slice_function("renderConsolidation")
    assert "Array.isArray(CONSOLIDATION.panels)" in body, (
        "renderConsolidation must check panels[] presence at the top to "
        "choose between wave2-stream rendering and legacy fallback"
    )


def test_renderConsolidation_panels_path_inits_wave2_stream():
    """When panels[] is present, renderConsolidation calls wave2SlideInit on cons-stream."""
    body = _slice_function("renderConsolidation")
    assert "wave2SlideInit(" in body, (
        "renderConsolidation must call wave2SlideInit when rendering panels[]"
    )
    assert "containerId: 'cons-stream'" in body
    assert "dotsId: 'cons-dots'" in body


def test_renderConsolidation_panels_path_uses_permissive_canAdvance():
    """Consolidation is NOT graded — canAdvance must always return true."""
    body = _slice_function("renderConsolidation")
    # The pattern is `canAdvance: () => true` (or function variant).
    assert "canAdvance: () => true" in body, (
        "Consolidation's canAdvance must be permissive — the user explicitly "
        "said 'consolidation is not graded' so navigation must never block"
    )


def test_renderConsolidation_panels_path_hides_legacy_block():
    """When panels[] is present, the legacy single-card block is hidden."""
    body = _slice_function("renderConsolidation")
    assert "legacyBlock.style.display = 'none'" in body, (
        "the legacy {mnemonic, bullets} block must be hidden when panels[] "
        "rendering takes over — leaving it visible would show two layouts"
    )


def test_renderConsolidation_legacy_path_shows_legacy_block_hides_stream():
    """Legacy fixtures (no panels[]) hide cons-stream and show cons-legacy-block."""
    body = _slice_function("renderConsolidation")
    # The legacy branch path explicitly hides stream + dots.
    legacy_path_signal = "legacyBlock.style.display = ''"
    assert legacy_path_signal in body, (
        "the legacy fallback must explicitly show cons-legacy-block — without "
        "this, content_json without panels[] would render an empty screen"
    )


def test_renderConsolidation_check_panel_renders_reveal_toggle_not_graded():
    """The 'check' kind panel renders a reveal-on-demand button, no auto-advance."""
    body = _slice_function("renderConsolidation")
    # The check-panel branch renders a button + answer div + click handler.
    assert "p.kind === 'check'" in body, (
        "renderConsolidation must detect the 'check' kind panel and render "
        "the reveal-on-demand block on it specifically"
    )
    assert "is-revealed" in body, (
        "the reveal toggle must add 'is-revealed' to the answer element on "
        "click — same affordance the legacy renderer uses"
    )


def test_consolidation_swipe_dispatches_to_wave2_helper():
    """Pointerup on stage 6.5 calls wave2SlideNavigate('cons-stream', dir)."""
    assert re.search(
        r"absDx\s*>\s*50\s*&&\s*state\.stage\s*===\s*6\.5",
        TEMPLATE,
    ), "pointerup must dispatch a stage-6.5 branch for Consolidation swipes"
    assert "wave2SlideNavigate('cons-stream'," in TEMPLATE, (
        "Consolidation swipe handling must route through wave2SlideNavigate so "
        "the shared helper owns the slide animation + dot updates"
    )


def test_consolidation_oncontinue_stored_for_swipe_exit():
    """showConsolidationScreen stores onContinue on consState so swipe-past-last fires it."""
    body = _slice_function("showConsolidationScreen")
    assert "consState.onContinue =" in body, (
        "the parent's onContinue must be stored on consState so the wave2 "
        "stream's onExitForward (swipe past last panel) can trigger phase exit"
    )
