"""Regression tests for the Memory Palace runtime UI (frontend polish PR).

Pins the contract between this PR's frontend work and the backend's
phase=memory-palace endpoint (server/routes/ai.py:_check_answer_memory_palace,
shipped on PR #152):

- New required IDs (#gb-panel-mp + 4-step state machine slots).
- gbState.mp initial-shape literal carries required fields.
- Required functions present (gbInitMP + 14 helpers).
- Registry hook: id='mp', sub=7, panel='gb-panel-mp' added to gbActiveGameOrder.
- Dispatch hook: subGame === 7 → gbMPAction OR gbAdvanceFromGame(7, 'gb-panel-mp').
- Single network swap-point: gbMPSubmitSession POSTs to
  /api/ai/check-answer?phase=memory-palace.
- ctx.hwId canonical 3-key chain in gbMPSubmitSession.
- Body shape: palace_key, placements, recall_results, hints_used.
- Tier filter applied (premium palaces hidden from basic students).
- No hardcoded palace/concept content baked into the JS or markup.
- i18n keys (mp.*) present in all 3 runtime languages (uz/ru/en).
- Dark-mode CSS parity (≥10 [data-theme="dark"] .gb-mp-* selectors).
- Foundation stub `const GB_MEMORY_PALACE = __GB_MEMORY_PALACE__` preserved
  pre-inject; substituted post-inject.
- Server-authoritative outcome — gbMPRenderResult reads outcome / accuracy /
  session_xp_display / level_label from response (not computed locally).
- session_xp_display is COSMETIC — no writes to window.__sessionLog or any
  persistent counter.
- Step counter shows "1/4" / "2/4" / "3/4" / "4/4" pattern.

Companion to:
- tests/test_runtime_ttt_ui.py (TTT #150 reference shape)
- tests/test_runtime_sentence_fill_ui.py (SF state-machine pattern)
- tests/test_memory_palace_check_answer.py (backend route contract)
- tests/test_memory_palace_injector.py (wire format)
"""
from __future__ import annotations

import re

import pytest

from server.services.injector import inject


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _empty_content() -> dict:
    return {
        "meta": {"title": "MP UI Smoke", "subject_display": "X", "section": "", "cefr_level": ""},
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


def _mp_fixture() -> dict:
    """Memory Palace fixture with 4 palaces (1 premium) + 5 concepts."""
    return {
        "palaces": [
            {
                "key": "home", "name": "Student's Home", "icon": "🏠",
                "description": "Front door, kitchen, sofa, desk, balcony.",
                "subject_family": "universal", "tier": "basic",
                "locations": [
                    {"name": "Front door", "sensory_cue": "Hear the key turning."},
                    {"name": "Kitchen", "sensory_cue": "Smell warm bread."},
                    {"name": "Sofa", "sensory_cue": "Feel cushions sink."},
                    {"name": "Desk", "sensory_cue": "See your books."},
                    {"name": "Balcony", "sensory_cue": "Feel the air."},
                ],
            },
            {
                "key": "school", "name": "School", "icon": "🏫",
                "description": "Gate, board, lab, library, field.",
                "subject_family": "universal", "tier": "basic",
                "locations": [
                    {"name": "Gate", "sensory_cue": "Hear arrivals."},
                    {"name": "Board", "sensory_cue": "See chalk."},
                    {"name": "Science shelf", "sensory_cue": "Lab jars."},
                    {"name": "Library desk", "sensory_cue": "Smell paper."},
                    {"name": "Field edge", "sensory_cue": "Hear a whistle."},
                ],
            },
            {
                "key": "bio_lab", "name": "Biology Lab", "icon": "🧪",
                "description": "Microscope table, specimens, posters.",
                "subject_family": "bio", "tier": "basic",
                "locations": [
                    {"name": "Microscope table", "sensory_cue": "Bright slide."},
                    {"name": "Specimen tray", "sensory_cue": "Labeled samples."},
                    {"name": "DNA poster wall", "sensory_cue": "Giant helix."},
                    {"name": "Incubator", "sensory_cue": "Warm air."},
                    {"name": "Cold storage", "sensory_cue": "Preserved samples."},
                ],
            },
            {
                "key": "premium_obs", "name": "Samarkand Observatory", "icon": "🔭",
                "description": "Premium-only palace.",
                "subject_family": "universal", "tier": "premium",
                "locations": [
                    {"name": "Quadrant", "sensory_cue": "Stone arc."},
                    {"name": "Star table", "sensory_cue": "Old maps."},
                    {"name": "Brass globe", "sensory_cue": "Polished metal."},
                    {"name": "Observation window", "sensory_cue": "Night sky."},
                    {"name": "Tiled dome", "sensory_cue": "Blue patterns."},
                ],
            },
        ],
        "concepts": [
            {"id": "mp-c1", "term": "Mitochondria", "description": "Powerhouse of the cell.", "image_cue": "Tiny power station glowing."},
            {"id": "mp-c2", "term": "Nucleus", "description": "Control center.", "image_cue": "Royal control room."},
            {"id": "mp-c3", "term": "Cell membrane", "description": "Flexible border.", "image_cue": "Smart security gate."},
            {"id": "mp-c4", "term": "Chloroplast", "description": "Sunlight food maker.", "image_cue": "Green solar kitchen."},
            {"id": "mp-c5", "term": "Ribosome", "description": "Builds proteins.", "image_cue": "Mini factory."},
        ],
    }


@pytest.fixture(scope="module")
def html_empty() -> str:
    return inject(
        _empty_content(),
        runtime_context={"hw_id": "HW-MP-EMPTY", "subject": "bio", "grade": 7},
    )


@pytest.fixture(scope="module")
def html_with_mp() -> str:
    body = _empty_content()
    body["gb_memory_palace"] = _mp_fixture()
    return inject(
        body,
        runtime_context={"hw_id": "HW-MP-1", "subject": "bio", "grade": 7, "tier": "basic"},
    )


# ---------------------------------------------------------------------------
# 1. All required IDs present
# ---------------------------------------------------------------------------


REQUIRED_IDS = [
    "gb-panel-mp",
    "gb-mp-dots",
    "gb-mp-phase-label",
    "gb-mp-step-label",
    "gb-mp-hero-kicker",
    "gb-mp-hero-title",
    "gb-mp-hero-sub",
    "gb-mp-xp-pill",
    "gb-mp-step-1",
    "gb-mp-step-2",
    "gb-mp-step-3",
    "gb-mp-step-4",
    "gb-mp-palace-grid",
    "gb-mp-focus-card",
    "gb-mp-focus-title",
    "gb-mp-concept-counter",
    "gb-mp-location-grid",
    "gb-mp-walk-card",
    "gb-mp-walk-counter",
    "gb-mp-recall-card",
    "gb-mp-recall-counter",
    "gb-mp-result-card",
    "gb-mp-result-title",
    "gb-mp-result-text",
    "gb-mp-accuracy-value",
    "gb-mp-speed-value",
    "gb-mp-level-value",
    "gb-mp-xp-value",
    "gb-mp-retry-btn",
    "gb-mp-toast",
]


@pytest.mark.parametrize("id_", REQUIRED_IDS)
def test_required_id_present(html_empty: str, id_: str):
    assert f'id="{id_}"' in html_empty, f"required id #{id_} missing"


def test_panel_carries_gb_game_panel_class(html_empty: str):
    pat = re.compile(r'<div\s+class="[^"]*\bgb-game-panel\b[^"]*"\s+id="gb-panel-mp"')
    assert pat.search(html_empty), "#gb-panel-mp must carry .gb-game-panel class"


# ---------------------------------------------------------------------------
# 2. gbState.mp initial-shape literal
# ---------------------------------------------------------------------------


def test_gbstate_mp_initial_shape(html_empty: str):
    # The mp object can span multiple lines and contain nested commas — capture
    # the slice between `mp:` and the next sibling property comma at brace depth 1.
    m = re.search(r"mp\s*:\s*\{", html_empty)
    assert m, "gbState.mp literal missing"
    # Walk balanced braces to extract literal body.
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
    body = html_empty[start : i - 1]
    required = [
        "step", "selectedPalace", "filteredPalaces", "conceptIndex",
        "placements", "walkIndex", "recallIndex", "recallResults",
        "recallStartAt", "hintsUsed", "result", "sessionId", "busy", "complete",
    ]
    for name in required:
        assert re.search(rf"\b{name}\s*:", body), (
            f"gbState.mp must declare field `{name}`"
        )


# ---------------------------------------------------------------------------
# 3. All required functions present
# ---------------------------------------------------------------------------


REQUIRED_FUNCTIONS = [
    "gbInitMP",
    "gbMPRenderStep",
    "gbMPRenderPalaceGrid",
    "gbMPSelectPalace",
    "gbMPStartPlacement",
    "gbMPRenderFocusCard",
    "gbMPRenderLocationGrid",
    "gbMPPlace",
    "gbMPStartWalk",
    "gbMPRenderWalkCard",
    "gbMPAdvanceWalk",
    "gbMPStartRecall",
    "gbMPRenderRecall",
    "gbMPAnswerRecall",
    "gbMPSubmitSession",
    "gbMPRenderResult",
    "gbMPAction",
    "gbMPRetry",
    "gbMPShowToast",
]


@pytest.mark.parametrize("fn", REQUIRED_FUNCTIONS)
def test_required_function_present(html_empty: str, fn: str):
    pat = re.compile(
        rf"\bfunction\s+{re.escape(fn)}\s*\(|\basync\s+function\s+{re.escape(fn)}\s*\("
    )
    assert pat.search(html_empty), f"required JS function `{fn}` missing"


# ---------------------------------------------------------------------------
# 4. Registry hook — id='mp', sub=7, panel='gb-panel-mp'
# ---------------------------------------------------------------------------


def test_registry_hook_present(html_empty: str):
    pat = re.compile(
        r"id\s*:\s*['\"]mp['\"]\s*,\s*sub\s*:\s*7\s*,\s*init\s*:\s*gbInitMP\s*,\s*panel\s*:\s*['\"]gb-panel-mp['\"]"
    )
    assert pat.search(html_empty), (
        "gbActiveGameOrder must register Memory Palace at sub-slot 7 with "
        "{id:'mp', sub:7, init:gbInitMP, panel:'gb-panel-mp'}"
    )


# ---------------------------------------------------------------------------
# 5. Dispatch hook — subGame === 7 → gbMPAction / gbAdvanceFromGame
# ---------------------------------------------------------------------------


def test_dispatch_hook_present(html_empty: str):
    # Must have both `subGame === 7` and `gbAdvanceFromGame(7, 'gb-panel-mp')`.
    assert re.search(r"subGame\s*===\s*7", html_empty), (
        "gbHandleAction must route subGame === 7 to MP"
    )
    assert re.search(r"gbAdvanceFromGame\s*\(\s*7\s*,\s*['\"]gb-panel-mp['\"]", html_empty), (
        "gbAdvanceFromGame(7, 'gb-panel-mp') must be present (registry hook)"
    )


# ---------------------------------------------------------------------------
# 6. Single network swap-point — phase=memory-palace POST
# ---------------------------------------------------------------------------


def _function_body(html: str, fn_name: str) -> str:
    """Extract the body of a top-level function declaration."""
    pat = re.compile(
        rf"(?:async\s+)?function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{"
    )
    m = pat.search(html)
    assert m, f"{fn_name} not found"
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


def test_check_answer_endpoint_phase_memory_palace(html_empty: str):
    body = _function_body(html_empty, "gbMPSubmitSession")
    assert "/api/ai/check-answer" in body, (
        "gbMPSubmitSession must POST to /api/ai/check-answer"
    )
    assert re.search(r"phase\s*=\s*memory-palace|phase\s*:\s*['\"]memory-palace['\"]", body), (
        "gbMPSubmitSession must target phase=memory-palace"
    )
    assert re.search(r"method\s*:\s*['\"]POST['\"]", body), (
        "gbMPSubmitSession must use POST"
    )
    assert re.search(r"homework_id\s*:", body), (
        "gbMPSubmitSession body must include `homework_id` field"
    )


def test_submit_session_is_async(html_empty: str):
    pat = re.compile(r"async\s+function\s+gbMPSubmitSession\s*\(")
    assert pat.search(html_empty), (
        "gbMPSubmitSession must be declared async (Promise return)"
    )


# ---------------------------------------------------------------------------
# 7. ctx.hwId canonical 3-key chain
# ---------------------------------------------------------------------------


def test_ctx_hwid_priority_chain(html_empty: str):
    body = _function_body(html_empty, "gbMPSubmitSession")
    pat = re.compile(
        r"ctx\.hwId\s*\|\|\s*ctx\.homework_id\s*\|\|\s*ctx\.homeworkId"
    )
    assert pat.search(body), (
        "gbMPSubmitSession must read homework id via the canonical 3-key chain "
        "(ctx.hwId || ctx.homework_id || ctx.homeworkId) — TM #140 / SF / TTT lesson"
    )


# ---------------------------------------------------------------------------
# 8. Body shape — palace_key, placements, recall_results, hints_used
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["palace_key", "placements", "recall_results", "hints_used"])
def test_submit_session_body_includes_field(html_empty: str, field: str):
    body = _function_body(html_empty, "gbMPSubmitSession")
    assert re.search(rf"\b{re.escape(field)}\s*:", body), (
        f"gbMPSubmitSession POST body must include `{field}` field"
    )


# ---------------------------------------------------------------------------
# 9. Tier filter applied — palace.tier compared with student tier
# ---------------------------------------------------------------------------


def test_tier_filter_applied(html_empty: str):
    body = _function_body(html_empty, "gbInitMP")
    # Code must read palace.tier and decide premium based on ctx.tier.
    assert re.search(r"\.tier\b", body), (
        "gbInitMP must inspect palace.tier for filtering"
    )
    assert re.search(r"premium", body, re.IGNORECASE), (
        "gbInitMP must reference 'premium' tier for filtering"
    )


# ---------------------------------------------------------------------------
# 10. NO HARDCODING — palace/concept content not baked in
# ---------------------------------------------------------------------------


HARDCODED_LEAK_TERMS = [
    # Reference design's biology samples — must never appear hardcoded.
    "Inside the Cell",
    "Mitochondria station",
    "Nucleus chamber",
    "Chloroplast garden",
    "Ribosome workshop",
    "Cell membrane gate",
    "Microscope table",
]


@pytest.mark.parametrize("term", HARDCODED_LEAK_TERMS)
def test_no_hardcoded_content_in_empty_html(html_empty: str, term: str):
    """When MP is unauthored, the empty render must not contain reference-design samples."""
    assert term not in html_empty, (
        f"hardcoded leak: '{term}' appears in empty render — content must come from GB_MEMORY_PALACE only"
    )


# ---------------------------------------------------------------------------
# 11. i18n keys × 3 languages
# ---------------------------------------------------------------------------


I18N_KEYS = [
    "game.mp",
    "mp.heroKicker",
    "mp.heroTitleStep1",
    "mp.heroTitleStep2",
    "mp.heroTitleStep3",
    "mp.heroTitleStep4",
    "mp.step1Label",
    "mp.step4Label",
    "mp.placementOccupied",
    "mp.conceptCounter",
    "mp.walkCounter",
    "mp.recallCounter",
    "mp.recallQuestion",
    "mp.outcome.perfect",
    "mp.outcome.yaxshi",
    "mp.outcome.hali_emas_partial",
    "mp.outcome.hali_emas_fail",
    "mp.level.apprentice",
    "mp.level.proficient",
    "mp.level.mastered",
    "mp.level.pending",
    "mp.accuracyLabel",
    "mp.speedLabel",
    "mp.levelLabel",
    "mp.xpLabel",
    "mp.dockChoosePalace",
    "mp.dockPlaceConcept",
    "mp.dockNextStop",
    "mp.dockAnswerRecall",
    "mp.dockComplete",
    "mp.dockRetry",
    "mp.toastNetwork",
]


@pytest.mark.parametrize("key", I18N_KEYS)
def test_i18n_key_in_three_languages(html_empty: str, key: str):
    """Every mp.* key must appear ≥3 times (once per language block: uz/ru/en)."""
    quoted = re.findall(rf"['\"]{re.escape(key)}['\"]\s*:", html_empty)
    assert len(quoted) >= 3, (
        f"i18n key `{key}` must appear in all 3 language blocks (uz/ru/en); "
        f"found {len(quoted)}"
    )


# ---------------------------------------------------------------------------
# 12. Dark-mode CSS parity
# ---------------------------------------------------------------------------


def test_dark_mode_selectors_count(html_empty: str):
    pat = re.compile(r'\[data-theme="dark"\]\s*\.gb-mp-')
    matches = pat.findall(html_empty)
    assert len(matches) >= 10, (
        f"Memory Palace dark-mode CSS parity requires ≥10 selectors; found {len(matches)}"
    )


# ---------------------------------------------------------------------------
# 13. Foundation stub preserved (substituted post-inject)
# ---------------------------------------------------------------------------


def test_foundation_stub_substituted_not_leaked(html_empty: str):
    # After inject(), the placeholder must be substituted (not present as string).
    assert "__GB_MEMORY_PALACE__" not in html_empty, (
        "Foundation placeholder __GB_MEMORY_PALACE__ must be substituted by injector"
    )
    # The const declaration must remain.
    assert re.search(r"const\s+GB_MEMORY_PALACE\s*=", html_empty), (
        "const GB_MEMORY_PALACE = ... must remain in rendered HTML"
    )


def test_gb_memory_palace_null_when_unauthored(html_empty: str):
    # Empty content → injector ships null, gating registry from pushing the panel.
    pat = re.compile(r"const\s+GB_MEMORY_PALACE\s*=\s*null\s*;")
    assert pat.search(html_empty), (
        "When gb_memory_palace is unauthored, GB_MEMORY_PALACE must be null"
    )


def test_gb_memory_palace_object_when_authored(html_with_mp: str):
    # Authored content → injector ships {palaces, concepts, config}.
    pat = re.compile(r"const\s+GB_MEMORY_PALACE\s*=\s*\{", re.MULTILINE)
    assert pat.search(html_with_mp), (
        "When gb_memory_palace is authored, GB_MEMORY_PALACE must be an object"
    )
    # Premium palace filtered out for basic tier.
    assert "Samarkand Observatory" not in html_with_mp, (
        "Premium palace must be tier-filtered out for basic-tier homework"
    )


# ---------------------------------------------------------------------------
# 14. Server-authoritative outcome — gbMPRenderResult reads from response
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", [
    r"resp\.outcome\b",
    r"resp\.accuracy_pct",
    r"resp\.session_xp_display",
    r"resp\.level_label",
    r"resp\.recall_speed_avg_s",
    r"resp\.retry_offered",
])
def test_render_result_reads_server_response(html_empty: str, field: str):
    body = _function_body(html_empty, "gbMPRenderResult")
    pat = re.compile(field)
    assert pat.search(body), (
        f"gbMPRenderResult must read `{field}` from server response (server-authoritative)"
    )


# ---------------------------------------------------------------------------
# 15. session_xp_display is COSMETIC — no persistent counter writes
# ---------------------------------------------------------------------------


def test_session_xp_not_persisted(html_empty: str):
    body = _function_body(html_empty, "gbMPRenderResult")
    # Must NOT write session_xp_display to __sessionLog or any unified counter.
    assert not re.search(r"__sessionLog\s*[\.\[].*session_xp_display", body), (
        "session_xp_display must NOT be written to window.__sessionLog (cosmetic-only per plan §1.3 + §7 #9)"
    )
    assert not re.search(r"sessionLog.*=.*session_xp_display", body), (
        "session_xp_display must NOT be summed into any persistent session counter"
    )


# ---------------------------------------------------------------------------
# 16. Step counter format "1/4" / "2/4" / etc.
# ---------------------------------------------------------------------------


def test_step_counter_format(html_empty: str):
    body = _function_body(html_empty, "gbMPRenderStep")
    # The render fn must build a label like step + '/4'.
    assert re.search(r"step\s*\+\s*['\"]/4['\"]", body) or re.search(r"['\"]\{n\}/4['\"]", body), (
        "gbMPRenderStep must format step counter as N/4"
    )


# ---------------------------------------------------------------------------
# 17. Result card structure — accuracy/speed/level/xp slots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("slot_id", [
    "gb-mp-accuracy-value",
    "gb-mp-speed-value",
    "gb-mp-level-value",
    "gb-mp-xp-value",
])
def test_result_card_slot(html_empty: str, slot_id: str):
    assert f'id="{slot_id}"' in html_empty, (
        f"result card must include slot #{slot_id}"
    )


# ---------------------------------------------------------------------------
# 18. Retry button conditional on retry_offered
# ---------------------------------------------------------------------------


def test_retry_offered_conditional(html_empty: str):
    body = _function_body(html_empty, "gbMPRenderResult")
    assert re.search(r"retry_offered", body), (
        "gbMPRenderResult must check resp.retry_offered to gate the retry button"
    )


# ---------------------------------------------------------------------------
# 19. No client-side answer leak — there's no author-supplied answer for MP,
# but verify recall question text is rendered from i18n (not server-supplied)
# ---------------------------------------------------------------------------


def test_recall_question_uses_i18n(html_empty: str):
    body = _function_body(html_empty, "gbMPRenderRecall")
    # The recall question is i18n-driven (mp.recallQuestion key), not server-supplied.
    assert re.search(r"mp\.recallQuestion", body), (
        "gbMPRenderRecall must source the question text from i18n key mp.recallQuestion"
    )


# ---------------------------------------------------------------------------
# 20. CSS prefix — every new class uses .gb-mp- prefix
# ---------------------------------------------------------------------------


def test_css_class_prefix_consistency(html_empty: str):
    # The runtime-side panel must use .gb-mp- prefixed classes only (no leakage).
    # Spot-check a few markup pieces.
    assert 'class="gb-mp-topbar"' in html_empty
    assert 'class="gb-mp-hero"' in html_empty
    assert re.search(r'class="gb-game-panel\s+enter-right"\s+id="gb-panel-mp"', html_empty)
