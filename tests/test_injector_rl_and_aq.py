"""
Unit tests for two recent injector behaviours that previously lived only
in headless e2e audits:

1. _rl_adapt_to_template
   - phantom q6 suppression: when the author authored only q1..q5, the
     runtime must not get a 6th empty question slot
   - q2 fields fallback: when q2 has prompt + ans but no fields[], the
     adapter must emit a single-input "text" question, not a phantom
     multi-input with [{label: "Javob", acceptable: ["—"]}]

2. gb_adaptive_quiz tier redistribution
   - when the author tagged every item the same tier (the importer
     used to hardcode "MEDIUM"), the injector must redistribute items
     across easy/medium/hard by Bloom level instead of cloning item[0]
     into the missing tiers (which caused "same question shown 5×")

Both behaviours are pure-Python, so we exercise them in-process without
HTTP, the dev server, or a browser.
"""

import pytest

from server.services.injector import (
    _rl_adapt_to_template,
    inject,
)


# ── _rl_adapt_to_template ───────────────────────────────────────────────


def _rl_with_text_q(**overrides):
    """Build a minimally valid builder-shape real_life dict."""
    base = {
        "badge": "Test scenario",
        "story": "A short setup paragraph.",
        "endTitle": "Done",
        "endSub": "Wrapped up.",
        "q1": {"prompt": "What is 2+2?",  "ans": "4",  "fb": "Correct.", "capture": False},
        "q2": {"prompt": "What is 3+3?",  "ans": "6",  "fb": "Correct.", "capture": False},
        "q3": {"prompt": "What is 4+4?",  "ans": "8",  "fb": "Correct.", "capture": False},
        "q4": {"prompt": "What is 5+5?",  "ans": "10", "fb": "Correct.", "capture": False},
        "q5": {"prompt": "Why?",          "ans": "Because.",
               "fb": "Right.", "capture": False, "open": True},
    }
    base.update(overrides)
    return base


def test_rl_adapter_no_phantom_q6_when_author_only_authored_5():
    """Author left q6 unset. Adapter must NOT emit a 6th question slot
    with empty prompt + acceptableAnswers=['—'] (which would render as
    an unanswerable question in the runtime)."""
    rl = _rl_with_text_q()
    # Sanity: q6 absent.
    assert "q6" not in rl

    out = _rl_adapt_to_template(rl)
    questions = out["questions"]

    assert len(questions) == 5, f"expected 5 questions, got {len(questions)}"
    ids = [q["id"] for q in questions]
    assert ids == ["Q1", "Q2", "Q3", "Q4", "Q5"], ids
    # No phantom q6 sneaking in via empty prompt
    for q in questions:
        assert q["prompt"].strip(), f"{q['id']} has empty prompt"
        # textarea questions are open-ended (no acceptableAnswers); others
        # must not carry the "—" placeholder emitted for empty content.
        if q["type"] != "textarea":
            assert q.get("acceptableAnswers") not in (None, ["—"]), (
                f"{q['id']} has placeholder answer"
            )


def test_rl_adapter_emits_q6_when_author_does_provide_it():
    """Phantom suppression must NOT remove a real q6 — only suppress when
    the author left it blank."""
    rl = _rl_with_text_q(q6={
        "prompt": "Bonus question?", "ans": "yes",
        "fb": "Sure.", "capture": False,
    })

    out = _rl_adapt_to_template(rl)

    assert len(out["questions"]) == 6
    assert out["questions"][5]["id"] == "Q6"
    assert out["questions"][5]["prompt"] == "Bonus question?"


def test_rl_adapter_q2_with_ans_falls_through_to_text_input():
    """q2 historically routed through make_fields_q. When the author
    provides only ans (no fields[]), the adapter must fall through to
    text-input shape — not emit type=multi-input with a placeholder
    [{label:'Javob', acceptable:['—']}] field that the runtime can't
    grade against any user input."""
    rl = _rl_with_text_q()  # q2 has prompt + ans, no fields

    out = _rl_adapt_to_template(rl)
    q2 = out["questions"][1]

    assert q2["id"] == "Q2"
    # Should be one of the text variants (text or text-with-capture),
    # NOT multi-input with a placeholder field.
    assert q2["type"] in ("text", "text-with-capture"), q2["type"]
    assert "fields" not in q2, "text fall-through must not emit fields[]"
    assert q2["acceptableAnswers"] == ["6"]


def test_rl_adapter_q2_with_explicit_fields_stays_multi_input():
    """When the author DOES author multi-input fields, the adapter must
    keep them — fall-through is the exception, not the default."""
    rl = _rl_with_text_q(q2={
        "prompt": "Decompose 6 into prime factors.",
        "fields": [
            {"id": "p1", "label": "First factor",  "ans": "2"},
            {"id": "p2", "label": "Second factor", "ans": "3"},
        ],
        "fb": "Right.",
        "capture": False,
    })

    out = _rl_adapt_to_template(rl)
    q2 = out["questions"][1]

    assert q2["type"] == "multi-input"
    assert len(q2["fields"]) == 2
    assert q2["fields"][0]["acceptable"] == ["2"]
    assert q2["fields"][1]["acceptable"] == ["3"]


def test_rl_adapter_q5_open_flag_yields_textarea():
    """q5 with open:true must produce type=textarea (used for AI-graded
    interpretation prompts that need free-form responses)."""
    rl = _rl_with_text_q()
    assert rl["q5"].get("open") is True

    out = _rl_adapt_to_template(rl)
    q5 = out["questions"][4]

    assert q5["id"] == "Q5"
    assert q5["type"] == "textarea"


def test_rl_adapter_q5_without_open_stays_text():
    """If the author didn't set q5.open, q5 should default to text input."""
    rl = _rl_with_text_q(q5={
        "prompt": "Bir gap bilan tushuntiring.",
        "ans": "javob",
        "fb": "OK",
        "capture": False,
        # no `open` key
    })

    out = _rl_adapt_to_template(rl)
    q5 = out["questions"][4]

    assert q5["type"] in ("text", "text-with-capture")


# ── gb_adaptive_quiz tier redistribution ────────────────────────────────


def _content_json_with_aq(aq_items):
    """Minimal content_json so inject() doesn't crash on missing keys."""
    return {
        "meta": {"title": "T", "subject_display": "X", "section": "1", "cefr_level": ""},
        "panels": [],
        "quotes": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": aq_items,
        "gb_why_chain": [],
        "gb_memory_match": [],
        "boss_questions": [],
        "real_life": None,
        "reflection": None,
    }


def _extract_aq_constant(html: str):
    """Pull the GB_ADAPTIVE_QUIZ JS literal out of injected HTML and parse it."""
    import re
    import json
    m = re.search(r"const GB_ADAPTIVE_QUIZ\s*=\s*(\[.*?\]);", html, flags=re.DOTALL)
    assert m, "GB_ADAPTIVE_QUIZ not found in injected HTML"
    return json.loads(m.group(1))


def test_aq_tier_redistribution_when_all_items_collapsed_to_medium():
    """The original importer hardcoded tier='MEDIUM' for every item, which
    triggered the picker's clone-into-empty-tiers fallback and resulted in
    A1 being shown for every easy/hard round (the "same question 5×"
    bug). The injector now redistributes by Bloom level so each tier
    has at least one DISTINCT item."""
    aq = [
        {"q": "Easy concept",   "tags": "[Bloom: L2 | PISA: L1]", "tier": "MEDIUM", "ans": ["a"]},
        {"q": "Easy procedure", "tags": "[Bloom: L2 | PISA: L2]", "tier": "MEDIUM", "ans": ["b"]},
        {"q": "Apply rule",     "tags": "[Bloom: L3 | PISA: L2]", "tier": "MEDIUM", "ans": ["c"]},
        {"q": "Analyse case",   "tags": "[Bloom: L4 | PISA: L3]", "tier": "MEDIUM", "ans": ["d"]},
        {"q": "Synthesise",     "tags": "[Bloom: L5 | PISA: L4]", "tier": "MEDIUM", "ans": ["e"]},
    ]
    cj = _content_json_with_aq(aq)

    html = inject(cj, runtime_context={"subject": "x", "grade": 8})
    items = _extract_aq_constant(html)

    assert len(items) == 5
    tiers = {x["tier"] for x in items}
    assert tiers == {"easy", "medium", "hard"}, (
        f"all three tiers should be populated after redistribution, got {tiers}"
    )

    # Every item is DISTINCT — none of them are clones of A1 with a
    # different tier label.
    prompts_by_tier = {}
    for x in items:
        prompts_by_tier.setdefault(x["tier"], set()).add(x["prompt"])
    # No prompt should appear under more than one tier
    seen = set()
    for tier, prompts in prompts_by_tier.items():
        for p in prompts:
            assert p not in seen, f"prompt {p!r} appears under multiple tiers"
            seen.add(p)


def test_aq_redistribution_respects_bloom_ordering():
    """Items with low Bloom (L1-L2) should land in 'easy', mid (L3) in
    'medium', high (L4+) in 'hard'. The hardest item must NEVER be
    demoted to easy when filling missing tiers."""
    aq = [
        {"q": "Lookup",   "tags": "[Bloom: L1 | PISA: L1]", "tier": "MEDIUM", "ans": ["a"]},
        {"q": "Recall",   "tags": "[Bloom: L2 | PISA: L1]", "tier": "MEDIUM", "ans": ["b"]},
        {"q": "Apply",    "tags": "[Bloom: L3 | PISA: L2]", "tier": "MEDIUM", "ans": ["c"]},
        {"q": "Evaluate", "tags": "[Bloom: L5 | PISA: L4]", "tier": "MEDIUM", "ans": ["d"]},
    ]
    cj = _content_json_with_aq(aq)

    html = inject(cj, runtime_context={"subject": "x", "grade": 8})
    items = _extract_aq_constant(html)

    # Lookup: L1 → easy ; Recall: L2 → easy ; Apply: L3 → medium ;
    # Evaluate: L5 → hard. After redistribution every tier should be
    # populated and the L5 item must be in hard, not demoted.
    by_prompt = {x["prompt"]: x["tier"] for x in items}
    assert by_prompt["Lookup"]   == "easy"
    assert by_prompt["Recall"]   == "easy"
    assert by_prompt["Apply"]    == "medium"
    assert by_prompt["Evaluate"] == "hard"


def test_aq_redistribution_skipped_when_all_three_tiers_already_present():
    """If the source already has at least one item per tier, the
    redistributor must leave tiers alone (no over-correction)."""
    aq = [
        {"q": "E1", "tags": "[Bloom: L2 | PISA: L1]", "tier": "EASY",   "ans": ["a"]},
        {"q": "M1", "tags": "[Bloom: L3 | PISA: L2]", "tier": "MEDIUM", "ans": ["b"]},
        {"q": "H1", "tags": "[Bloom: L5 | PISA: L4]", "tier": "HARD",   "ans": ["c"]},
    ]
    cj = _content_json_with_aq(aq)

    html = inject(cj, runtime_context={"subject": "x", "grade": 8})
    items = _extract_aq_constant(html)

    by_prompt = {x["prompt"]: x["tier"] for x in items}
    assert by_prompt == {"E1": "easy", "M1": "medium", "H1": "hard"}


# ── PR #67 follow-up regression guards ──────────────────────────────────


def test_aq_runtime_breaks_inline_option_markers_onto_separate_lines():
    """Authors of MC-style AQ items often write the options inline in the
    prompt text:  "Which sentence …?  A) opt-1  B) opt-2  C) opt-3"

    Without intervention, the runtime stamps that as one line via innerHTML
    and the student sees an unreadable wall of text (Unit 19 regression
    2026-04-29). The fix is a render-time regex that inserts <br> before
    each "A)" / "B)" / "C)" / "D)" marker preceded by whitespace.

    This test guards both halves:
    - the regex transform code is present in the runtime template
    - the result is assigned to the question element's innerHTML
    so future template refactors can't silently drop one of the two and
    re-introduce the wall-of-text rendering."""
    cj = _content_json_with_aq([
        {
            "q": 'Which means "X"?  A) one  B) two  C) three',
            "tags": "[Bloom: L1 | PISA: L1]",
            "tier": "EASY",
            "ans": ["one"],
        }
    ])
    html = inject(cj, runtime_context={"subject": "x", "grade": 8})

    # Half 1: the regex transform is in the runtime.
    transform_pattern = r".replace(/\s+([A-D]\))/g, '<br>$1')"
    assert transform_pattern in html, (
        "AQ option-formatting regex was removed from the runtime. "
        "Authors writing 'A) ... B) ... C) ...' inline expect each option "
        "on its own line. See Unit 19 regression 2026-04-29."
    )

    # Half 2: the formatted result is actually used (assigned via innerHTML).
    # If a refactor ever computed `formattedPrompt` but stamped item.prompt
    # raw, the previous check passes but rendering is broken.
    assert "qEl.innerHTML = formattedPrompt" in html, (
        "AQ runtime computes formattedPrompt but no longer assigns it to "
        "the question element. The regex transform is dead code unless "
        "qEl.innerHTML reads from formattedPrompt."
    )


def test_aq_injector_does_not_default_work_to_repeating_the_answer():
    """When the author leaves `hint` empty, the injector previously
    defaulted `work` to ``f"Javob: {answer}"``. The runtime then printed
    the correct answer twice in wrong-answer feedback:

        "Noto'g'ri. To'g'ri javob: doesn't have to wear. Javob: doesn't have to wear"

    Fix: when there is no authored hint, `work` must be empty so the
    runtime's `workSuffix = item.work ? '. ' + item.work : ''` appends
    nothing. This test guards against the default returning."""
    cj = _content_json_with_aq([
        {
            "q": "Stem ___",
            "tags": "[Bloom: L3 | PISA: L2]",
            "tier": "MEDIUM",
            "ans": ["doesn't have to wear"],
            # No `hint` key — author left it blank.
        }
    ])
    html = inject(cj, runtime_context={"subject": "x", "grade": 8})
    items = _extract_aq_constant(html)
    assert len(items) == 1

    work = items[0].get("work")
    assert work == "", (
        f'AQ item with no hint must have empty work field, got {work!r}. '
        f'A non-empty default (e.g. "Javob: {{answer}}") makes the runtime '
        f'print the correct answer twice in wrong-answer feedback.'
    )

    # Defensive: also assert the literal "Javob:" prefix never appears
    # for an item where the author didn't author a hint — catches future
    # variations of the default like "Answer: X" or " {answer}".
    assert "Javob: " not in items[0].get("work", ""), (
        "AQ item with no hint must not have a default work that repeats "
        "the answer — this caused the wrong-answer-feedback duplication."
    )


def test_aq_injector_preserves_authored_hint_in_work_field():
    """Negative case for the no-default test: when the author DOES
    provide a hint, it must round-trip into `work` unchanged. The fix
    only suppresses the default — real hints still flow through."""
    cj = _content_json_with_aq([
        {
            "q": "Stem ___",
            "tags": "[Bloom: L3 | PISA: L2]",
            "tier": "MEDIUM",
            "ans": ["X"],
            "hint": "Subject-verb agreement: third-person singular takes 's'.",
        }
    ])
    html = inject(cj, runtime_context={"subject": "x", "grade": 8})
    items = _extract_aq_constant(html)
    assert len(items) == 1
    assert items[0]["work"] == (
        "Subject-verb agreement: third-person singular takes 's'."
    ), (
        "Authored hint must survive into the work field unchanged. "
        "The PR #67 fix only suppresses the empty-hint default; real "
        "hints must still round-trip."
    )
