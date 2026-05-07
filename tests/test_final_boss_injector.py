"""Regression tests for _serialize_boss_questions + _serialize_boss_meta + injector wiring (Chunk A).

Guards:
  - Answer-leak prevention: accepted[], ans, accepted_answers, answer_spec all stripped.
  - Student-visible fields preserved: id, tier, damage, bloom, pisa, prompt, hints.
  - boss_meta=None → BOSS_META = null.
  - boss_meta populated → BOSS_META JSON matches model.
  - inject() substitutes both BOSS_QUESTIONS and BOSS_META; no raw placeholders remain.
  - Legacy path: boss_questions only (no boss_meta) renders BOSS_META=null correctly.
  - Script injection via _safe_js_json escaping.
  - Transitional flag: _BOSS_LEGACY_CLIENT_MATCH=True keeps acceptable[]; =False strips it.
"""

import json
import re

import pytest

import server.services.injector as injector_module
from server.services.injector import (
    _serialize_boss_meta,
    _serialize_boss_questions,
    inject,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_content(extra: dict | None = None) -> dict:
    """Return a minimal valid content_json dict."""
    base = {
        "meta": {
            "title": "FB Injector Test",
            "subject_display": "Math",
            "section": "",
            "cefr_level": "",
        },
        "gate_quote": {"mode": "auto"},
        "panels": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": [],
        "gb_why_chain": [],
        "gb_memory_match": [],
        "gb_tile_match": None,
        "gb_puzzle_lock": [],
        "gb_mystery_box": [],
        "gb_ttt": [],
        "boss_questions": [],
        "boss_meta": None,
        "real_life": None,
        "reading": None,
        "consolidation": None,
        "reflection": None,
    }
    if extra:
        base.update(extra)
    return base


def _runtime_ctx() -> dict:
    return {"lang": "uz", "subject": "algebra"}


def _make_boss_question_full(**overrides) -> dict:
    """A full boss question with all server-only fields present."""
    base = {
        "q": "Solve x^2 = 9",
        "ans": ["3", "-3"],
        "dmg": 10,
        "tags": "[Bloom: L3 | PISA: L3]",
        "answer_spec": {"type": "exact", "expected": "3"},
        "accepted_answers": ["3", "-3"],
        "accepted": ["3", "-3"],   # extra legacy alias
        "hint": "Take the square root.",
    }
    base.update(overrides)
    return base


def _extract_boss_questions(html: str) -> list:
    """Pull the BOSS_QUESTIONS array out of rendered HTML."""
    match = re.search(r"const BOSS_QUESTIONS\s*=\s*(\[.*?\]);", html, re.DOTALL)
    assert match, "Could not find BOSS_QUESTIONS in HTML"
    return json.loads(match.group(1))


def _extract_boss_meta(html: str):
    """Pull the BOSS_META value out of rendered HTML."""
    match = re.search(r"const BOSS_META\s*=\s*(null|\{.*?\});", html, re.DOTALL)
    assert match, "Could not find BOSS_META in HTML"
    raw = match.group(1)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Test 1: accepted[] is stripped
# ---------------------------------------------------------------------------

def test_serialize_boss_questions_strips_accepted_array():
    """output has zero 'accepted' keys at any depth — answer-leak prevention."""
    items = [_make_boss_question_full()]
    result = _serialize_boss_questions(items)
    data = json.loads(result)
    assert isinstance(data, list)
    for q in data:
        assert "accepted" not in q, f"'accepted' leaked into client payload: {q}"
        assert "acceptable" not in q, f"'acceptable' leaked into client payload: {q}"


# ---------------------------------------------------------------------------
# Test 2: ans legacy alias is stripped
# ---------------------------------------------------------------------------

def test_serialize_boss_questions_strips_ans_legacy_alias():
    """'ans' (legacy alias) must not appear in client payload."""
    items = [_make_boss_question_full()]
    result = _serialize_boss_questions(items)
    data = json.loads(result)
    for q in data:
        assert "ans" not in q, f"'ans' leaked into client payload: {q}"


# ---------------------------------------------------------------------------
# Test 3: answer_spec is stripped
# ---------------------------------------------------------------------------

def test_serialize_boss_questions_strips_answer_spec():
    """answer_spec (full grading contract) must never reach the client."""
    items = [_make_boss_question_full()]
    result = _serialize_boss_questions(items)
    data = json.loads(result)
    for q in data:
        assert "answer_spec" not in q, f"'answer_spec' leaked into client payload: {q}"


# ---------------------------------------------------------------------------
# Test 4: student-visible fields are preserved
# ---------------------------------------------------------------------------

def test_serialize_boss_questions_preserves_student_visible_fields():
    """id, tier, damage, bloom, pisa, prompt, hints are all present in output."""
    items = [_make_boss_question_full()]
    result = _serialize_boss_questions(items)
    data = json.loads(result)
    assert len(data) >= 1
    q = data[0]
    assert "id" in q,      f"'id' missing from output: {q}"
    assert "tier" in q,    f"'tier' missing from output: {q}"
    assert "damage" in q,  f"'damage' missing from output: {q}"
    assert "bloom" in q,   f"'bloom' missing from output: {q}"
    assert "pisa" in q,    f"'pisa' missing from output: {q}"
    assert "prompt" in q,  f"'prompt' missing from output: {q}"
    assert "hints" in q,   f"'hints' missing from output: {q}"
    assert isinstance(q["hints"], list)
    assert len(q["hints"]) >= 1


# ---------------------------------------------------------------------------
# Test 5: boss_meta=None emits null literal
# ---------------------------------------------------------------------------

def test_serialize_boss_meta_none_emits_null_literal():
    """_serialize_boss_meta(None) must return the string 'null'."""
    result = _serialize_boss_meta(None)
    assert result == "null", f"Expected 'null', got {result!r}"


# ---------------------------------------------------------------------------
# Test 6: boss_meta populated → JSON matches model_dump
# ---------------------------------------------------------------------------

def test_serialize_boss_meta_round_trip():
    """Populated BossMeta serializes to JSON matching the model's field values."""
    from server.schemas.content import BossMeta, BossAntiCheatPolicy
    meta = BossMeta(
        boss_type="big",
        grade_band="g9_11",
        attempts_max=1,
        anti_cheat=BossAntiCheatPolicy(paste_detect=True, response_time_floor_ms=300),
        use_dynamic_boss=True,
    )
    result = _serialize_boss_meta(meta)
    data = json.loads(result)
    assert data["boss_type"] == "big"
    assert data["grade_band"] == "g9_11"
    assert data["attempts_max"] == 1
    assert data["anti_cheat"]["paste_detect"] is True
    assert data["anti_cheat"]["response_time_floor_ms"] == 300
    assert data["use_dynamic_boss"] is True


# ---------------------------------------------------------------------------
# Test 7: inject() substitutes both BOSS_QUESTIONS and BOSS_META placeholders
# ---------------------------------------------------------------------------

def test_injector_substitutes_both_boss_questions_and_boss_meta_placeholders():
    """Rendered HTML must contain both const BOSS_QUESTIONS = [...]; and const BOSS_META = ...;
    and the raw __BOSS_META__ / __BOSS_QUESTIONS__ literals must be gone."""
    content = _minimal_content({
        "boss_questions": [_make_boss_question_full()],
        "boss_meta": {"boss_type": "sub", "grade_band": "g5", "use_dynamic_boss": True},
    })
    html = inject(content, runtime_context=_runtime_ctx())

    assert "const BOSS_QUESTIONS = " in html, "BOSS_QUESTIONS const missing"
    assert "const BOSS_META = " in html, "BOSS_META const missing"
    assert "__BOSS_META__" not in html, "__BOSS_META__ placeholder was not replaced"
    # The raw __BOSS_QUESTIONS__ marker doesn't appear in the template (uses _replace_js_const),
    # but verify the BOSS_QUESTIONS const is a valid array.
    bq = _extract_boss_questions(html)
    assert isinstance(bq, list)
    bm = _extract_boss_meta(html)
    assert bm is not None
    assert bm["boss_type"] == "sub"
    assert bm["use_dynamic_boss"] is True


# ---------------------------------------------------------------------------
# Test 8: legacy boss_questions without boss_meta → BOSS_QUESTIONS non-empty, BOSS_META = null
# ---------------------------------------------------------------------------

def test_injector_legacy_boss_questions_path_still_renders_when_meta_absent():
    """When only boss_questions is populated (no boss_meta), BOSS_META must be null."""
    content = _minimal_content({
        "boss_questions": [_make_boss_question_full()],
        "boss_meta": None,
    })
    html = inject(content, runtime_context=_runtime_ctx())

    bq = _extract_boss_questions(html)
    assert len(bq) > 0, "BOSS_QUESTIONS should be non-empty"

    bm = _extract_boss_meta(html)
    assert bm is None, f"BOSS_META should be null when boss_meta absent, got: {bm}"


# ---------------------------------------------------------------------------
# Test 9: _safe_js_json escapes </script> injection vectors
# ---------------------------------------------------------------------------

def test_injector_uses_safe_js_json_against_script_injection():
    """A prompt containing '</script>' must be escaped to prevent XSS."""
    malicious_prompt = "Bad</script><script>alert(1)</script>"
    items = [_make_boss_question_full(q=malicious_prompt)]
    result = _serialize_boss_questions(items)
    # The _safe_js_json helper replaces '</' with '<\/' so '</script>' can't break out.
    assert "</script>" not in result, "Raw </script> must be escaped in serialized output"
    assert "<\\/" in result or "\\/" in result, "Expected escaped forward slash in output"
    # The data should still be parseable.
    data = json.loads(result)
    assert len(data) > 0


# ---------------------------------------------------------------------------
# Test 10: transitional flag keeps accepted when enabled, strips when disabled
# ---------------------------------------------------------------------------

def test_injector_legacy_flag_keeps_accepted_when_enabled(monkeypatch):
    """_BOSS_LEGACY_CLIENT_MATCH=True keeps acceptable[]; =False strips it.

    Tests both paths to prove the flag works correctly in both directions.
    """
    items = [_make_boss_question_full()]

    # Default (flag=False): acceptable must be stripped.
    monkeypatch.setattr(injector_module, "_BOSS_LEGACY_CLIENT_MATCH", False)
    result_off = _serialize_boss_questions(items)
    data_off = json.loads(result_off)
    for q in data_off:
        assert "acceptable" not in q, f"acceptable should be stripped when flag=False: {q}"
        assert "accepted" not in q, f"accepted should be stripped when flag=False: {q}"

    # Legacy flag=True: acceptable must be kept.
    monkeypatch.setattr(injector_module, "_BOSS_LEGACY_CLIENT_MATCH", True)
    result_on = _serialize_boss_questions(items)
    data_on = json.loads(result_on)
    has_acceptable = any("acceptable" in q for q in data_on)
    assert has_acceptable, (
        "acceptable should be present when _BOSS_LEGACY_CLIENT_MATCH=True "
        f"(data_on={data_on})"
    )
