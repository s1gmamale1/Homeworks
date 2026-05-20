from __future__ import annotations

import json
import re

from server.services.injector import inject


def _content_with_memory_check(**overrides):
    content = {
        "meta": {"title": "Memory Check", "subject_display": "Biology", "section": "1"},
        "panels": [],
        "quotes": [],
        "flashcards": [
            {"id": "fc_cell", "cluster": "QOIDA", "front": {"term": "Cell"}, "back": {"definition": "Basic unit"}},
            {"id": "fc_mito", "cluster": "QOIDA", "front": {"term": "Mitochondria"}, "back": {"definition": "Energy release"}},
        ],
        "memory_sprint": [],
        "memory_check": {
            "pass_threshold_pct": 60,
            "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
            "items": [
                {
                    "type": "mcq",
                    "prompt": "Which organelle releases usable energy?",
                    "options": ["Vacuole", "Mitochondria", "Cell wall", "Chloroplast"],
                    "answer_spec": {"type": "option_index", "option_index": 1},
                    "flashcard_ref": "fc_mito",
                },
                {
                    "type": "fill_blank",
                    "prompt": "The basic unit of life is the _____.",
                    "answer_spec": {"type": "text_exact", "expected": "cell", "accepted_answers": ["Cell"]},
                    "flashcard_ref": "fc_cell",
                },
            ],
        },
        "boss_questions": [],
    }
    content.update(overrides)
    return content


def _html() -> str:
    return inject(
        _content_with_memory_check(),
        runtime_context={"hw_id": "HW-MC", "subject": "biology", "grade": 6},
    )


def _extract_const_json(src: str, const_name: str):
    match = re.search(rf"const\s+{const_name}\s*=\s*", src)
    assert match, f"{const_name} const not found"
    start = match.end()
    while start < len(src) and src[start].isspace():
        start += 1
    opening = src[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_str = False
    esc = False
    for pos in range(start, len(src)):
        ch = src[pos]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return json.loads(src[start : pos + 1])
    raise AssertionError(f"{const_name} literal did not terminate")


def test_memory_check_injects_mc_object_and_screen_hooks():
    html = _html()
    mc = _extract_const_json(html, "MC")
    assert mc["pass_threshold_pct"] == 60
    assert len(mc["items"]) == 2
    for hook in [
        'id="screen-mc"',
        'id="mc-item-list"',
        'id="mc-submit"',
        'id="mc-review"',
        "feature-grid mc-feature-grid",
        "pill--dark",
    ]:
        assert hook in html


def test_memory_check_runtime_has_gate_and_soft_retry_contract():
    html = _html()
    assert "function startMemoryCheckPhase(" in html
    assert "function mcSubmitAnswers(" in html
    assert "pct >= threshold" in html, "Memory Check must pass only at/above threshold"
    assert "state.mc.passed" in html
    assert "state.mc.weakRefs" in html
    assert "mcReturnToFlashcards" in html
    assert "Weak — review" in html
    assert "state.mc.retake = (state.mc.retake || 0) + 1" in html


def test_flashcards_must_all_be_viewed_before_memory_check_gate():
    html = _html()
    end_stage = re.search(
        r"function\s+endStage3\s*\(\)\s*\{(?P<body>.*?)\n\s{8}const MS_QUESTIONS",
        html,
        re.DOTALL,
    )
    assert end_stage, "endStage3/Memory Check block not found"
    body = end_stage.group("body")
    assert "seenTotal < fcTotal" in body
    assert "Hamma kartalarni" in body
    assert "startMemoryCheckPhase();" in body
