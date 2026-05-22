"""Regression fence for the React hydration redaction boundary (F1).

GET /api/runtime/homeworks/{id} must NEVER ship answer-bearing fields to the
browser. This mirrors the spirit of the tutor MAGIC_TOKEN leak tests
(test_tutor_chat.py) but guards the *hydration* path — the new delivery
mechanism that replaces the legacy injector's per-game stripping.

If any of these assertions fail, every v2 homework leaks its answer key to
every student. Treat a failure here as a release blocker.
"""

import json

import pytest

from server.services.runtime_redactor import redact_for_runtime


# ---- Endpoint-level: v2 shapes (case_based_preview + memory_check) ----

LEAK_TOKENS = [
    "LEAK_CBP_EXPECTED",
    "LEAK_CBP_ACCEPTED",
    "LEAK_CBP_PATH",
    "LEAK_MC_EXPECTED",
    "LEAK_MC_ACCEPTED",
]
# NOTE: wrong_path + feedback_summary are STUDENT-VISIBLE narrative (rendered by
# CaseBasedPreview.tsx from the hydration payload), so they intentionally SURVIVE
# — see test_hydration_preserves_display_content. correct_path stays stripped
# (server-only right-decision), learning_block stays stripped (arrives via the
# submit RESPONSE, not hydration).
FORBIDDEN_KEYS = [
    "answer_spec",
    "expected",
    "accepted_answers",
    "correct_path",
    "learning_block",
    "inv",
    "answer",
]


@pytest.fixture
def v2_homework_with_secrets(client):
    hw = client.post(
        "/api/homeworks",
        json={"title": "Redaction fence HW", "subject": "math-algebra", "grade": 8, "mode": "hard"},
    ).json()
    hw_id = hw["id"]
    content = {
        "flow_version": "v2",
        "meta": {"title": "Redaction fence HW", "subject_display": "Algebra"},
        "case_based_preview": {
            "checkpoints": [
                {
                    "question": "Which operation splits a quantity equally?",
                    "options": ["multiply", "divide"],
                    "answer_spec": {"expected": "LEAK_CBP_EXPECTED", "accepted_answers": ["LEAK_CBP_ACCEPTED"]},
                    # CBP teaching text — post-submit only, must not hydrate.
                    "learning_block": "LEAK_LEARNING_BLOCK teaching text",
                    "inv": "LEAK_CBP_INV",
                    "answer": "LEAK_CBP_ANSWER",
                },
                {"question": "Q2", "answer_spec": {"expected": "x"}},
                {"question": "Q3", "answer_spec": {"expected": "y"}},
            ],
            "final_simulation": {
                # correct_path is server-only (the right decision); stripped.
                "correct_path": "LEAK_CBP_PATH",
                # wrong_path is STUDENT-VISIBLE simulation narrative; survives.
                "wrong_path": "This wrong-path text is shown to the student",
            },
            # feedback_summary is the STUDENT-VISIBLE debrief; survives hydration.
            "feedback_summary": {
                "student_understood": "You grasped the core idea",
                "mistake_appeared": "A sign slip on the second step",
                "what_to_review": "Revisit distributing the negative",
            },
        },
        "memory_check": {
            "pass_threshold_pct": 60,
            "items": [
                {
                    "prompt": "Term for splitting equally?",
                    "options": ["division", "addition"],
                    "answer_spec": {"expected": "LEAK_MC_EXPECTED", "accepted_answers": ["LEAK_MC_ACCEPTED"]},
                    "correct": 0,
                }
            ],
        },
        # Tile-match: the leak shape — both sides share a pair id, so the DOM
        # would encode every answer. Hydration must replace this with opaque
        # per-side tokens (no shared id).
        "gb_tile_match": [
            {"id": "p0", "left": "atom", "right": "smallest unit"},
            {"id": "p1", "left": "molecule", "right": "two or more atoms"},
            {"id": "p2", "left": "ion", "right": "charged particle"},
        ],
        # TTT: raw authored items carry {q, correct, distractors[]}. Ttt.tsx
        # reads {id, q, options[]} — the redactor must build `options` (the
        # correct TEXT among distractors) while deleting the correct/distractors
        # KEYS, else the component crashes on `options.map`.
        "gb_ttt": [
            {"q": "What is 7 x 8?", "correct": "56", "distractors": ["54", "48", "63"]},
            {"id": "ttt-keep", "q": "Which is prime?", "correct": "11", "distractors": ["9", "15"]},
        ],
    }
    resp = client.put(f"/api/homeworks/{hw_id}", json={"content_json": content})
    assert resp.status_code == 200, resp.text
    return hw_id


def test_hydration_strips_all_answer_tokens(client, v2_homework_with_secrets):
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}")
    assert resp.status_code == 200, resp.text
    blob = json.dumps(resp.json())
    leaked = [t for t in LEAK_TOKENS if t in blob]
    assert not leaked, f"Hydration payload leaked answer values: {leaked}"


def test_hydration_strips_answer_key_names(client, v2_homework_with_secrets):
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}")
    blob = json.dumps(resp.json())
    present = [k for k in FORBIDDEN_KEYS if f'"{k}"' in blob]
    assert not present, f"Hydration payload exposed answer-key fields: {present}"


def test_hydration_preserves_display_content(client, v2_homework_with_secrets):
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}")
    blob = json.dumps(resp.json())
    assert "Which operation splits a quantity equally?" in blob
    assert "Term for splitting equally?" in blob
    # Tile-match display text (concept + meaning sides) still ships — only the
    # pairing is hidden.
    assert "atom" in blob and "smallest unit" in blob


def test_hydration_preserves_simulation_and_debrief_narrative(client, v2_homework_with_secrets):
    """wrong_path + feedback_summary are STUDENT-VISIBLE (CaseBasedPreview.tsx
    renders them straight from hydration). They must SURVIVE redaction."""
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}")
    data = resp.json()
    blob = json.dumps(data)

    sim = data["content_json"]["case_based_preview"]["final_simulation"]
    assert sim.get("wrong_path") == "This wrong-path text is shown to the student"

    fb = data["content_json"]["case_based_preview"]["feedback_summary"]
    assert fb.get("student_understood") == "You grasped the core idea"
    assert fb.get("mistake_appeared") == "A sign slip on the second step"
    assert fb.get("what_to_review") == "Revisit distributing the negative"

    # Both keys present in the payload (the UI reads them by name).
    assert '"wrong_path"' in blob and '"feedback_summary"' in blob


def _walk_keys_and_strings(node, keys: set, strings: list):
    """Recurse a JSON tree collecting every dict key + every string leaf."""
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(k)
            _walk_keys_and_strings(v, keys, strings)
    elif isinstance(node, list):
        for item in node:
            _walk_keys_and_strings(item, keys, strings)
    elif isinstance(node, str):
        strings.append(node)


def test_hydration_deep_walk_no_answer_keys_or_tokens(client, v2_homework_with_secrets):
    """Recursive walk: no forbidden key + no LEAK_* token survives at ANY depth."""
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}")
    payload = resp.json()
    keys: set = set()
    strings: list = []
    _walk_keys_and_strings(payload, keys, strings)

    # NB: wrong_path + feedback_summary are intentionally NOT here — they are
    # student-visible narrative the UI renders from hydration.
    forbidden_keys = {
        "answer_spec", "expected", "accepted_answers", "correct_path",
        "learning_block", "inv", "answer",
        "invariant", "expected_answer", "distractors",
    }
    leaked_keys = forbidden_keys & keys
    assert not leaked_keys, f"answer-bearing keys survived hydration: {leaked_keys}"

    blob = "\n".join(strings)
    leaked_tokens = [t for t in strings if t.startswith("LEAK_")]
    assert not leaked_tokens, f"answer tokens survived hydration: {leaked_tokens}"
    assert "LEAK_LEARNING_BLOCK" not in blob


def test_hydration_tile_match_has_no_recoverable_pairing(client, v2_homework_with_secrets):
    """Tile-match hydrates as {lefts,rights} with opaque tokens — no shared id."""
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}")
    tm = resp.json()["content_json"]["gb_tile_match"]

    # New shape: a dict with two independent token columns, NOT a pair list.
    assert isinstance(tm, dict), f"tile-match should be {{lefts,rights}} dict, got {type(tm)}"
    assert set(tm.keys()) <= {"lefts", "rights"}
    lefts, rights = tm["lefts"], tm["rights"]
    assert len(lefts) == len(rights) == 3

    # No tile carries id/left/right (the recoverable-pairing fields).
    for tile in lefts:
        assert set(tile.keys()) == {"lid", "text"}, tile
        assert "id" not in tile and "right" not in tile
    for tile in rights:
        assert set(tile.keys()) == {"rid", "text"}, tile
        assert "id" not in tile and "left" not in tile

    # The left/right tokens must be DISJOINT (no token appears on both sides),
    # so a left tile can never be matched to a right by id-equality.
    lids = {t["lid"] for t in lefts}
    rids = {t["rid"] for t in rights}
    assert lids.isdisjoint(rids), "left/right tokens overlap — pairing recoverable"

    # The display texts are present but split across columns with no link.
    left_texts = {t["text"] for t in lefts}
    right_texts = {t["text"] for t in rights}
    assert left_texts == {"atom", "molecule", "ion"}
    assert right_texts == {"smallest unit", "two or more atoms", "charged particle"}


def test_hydration_ttt_builds_options_without_answer_key_fields(client, v2_homework_with_secrets):
    """gb_ttt must hydrate as {id, q, options[]} — Ttt.tsx crashes without
    `options`. The correct ANSWER TEXT rides as one visible MCQ option (server
    grades by text-match), but the correct/distractors KEYS must be gone and no
    field may flag which option is right."""
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}")
    ttt = resp.json()["content_json"]["gb_ttt"]

    assert isinstance(ttt, list) and len(ttt) == 2

    by_q = {item["q"]: item for item in ttt}
    first = by_q["What is 7 x 8?"]
    # The component reads exactly these three keys; no answer-key field leaks.
    assert set(first.keys()) == {"id", "q", "options"}, first
    assert "correct" not in first and "distractors" not in first
    # id autoassigns "ttt-{idx+1}" when absent (mirrors injector._serialize_ttt).
    assert first["id"] == "ttt-1"

    opts = first["options"]
    assert isinstance(opts, list) and opts, "options must be a non-empty list"
    # The correct TEXT is among the options, and so are all distractors.
    assert "56" in opts
    assert {"54", "48", "63"}.issubset(set(opts))
    # No marker reveals which option is correct.
    assert all(isinstance(o, str) for o in opts)

    # Authored id is preserved verbatim when present.
    second = by_q["Which is prime?"]
    assert second["id"] == "ttt-keep"
    assert "11" in second["options"] and {"9", "15"}.issubset(set(second["options"]))


def test_hydration_ttt_options_stable_across_calls(client, v2_homework_with_secrets):
    """Re-hydration is deterministic — same student sees the same board."""
    a = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}").json()["content_json"]["gb_ttt"]
    b = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}").json()["content_json"]["gb_ttt"]
    assert a == b, "gb_ttt option order must be stable across hydration calls"


def test_redactor_ttt_builds_options_and_strips_answer_keys():
    """Unit-level: build the {id,q,options} shape, drop correct/distractors."""
    raw = {
        "gb_ttt": [
            {"q": "Capital of France?", "correct": "Paris", "distractors": ["Lyon", "Nice", "Rome"]},
            {"q": "", "correct": "dropped"},          # empty q → dropped
            {"q": "no answer", "correct": ""},         # empty correct → dropped
        ]
    }
    safe = redact_for_runtime(raw, hw_id="HW-TTT-1")
    ttt = safe["gb_ttt"]
    assert len(ttt) == 1, "items with empty q/correct are dropped"
    item = ttt[0]
    assert set(item.keys()) == {"id", "q", "options"}
    assert item["id"] == "ttt-1"
    assert "Paris" in item["options"]
    assert {"Lyon", "Nice", "Rome"}.issubset(set(item["options"]))
    blob = json.dumps(safe)
    assert '"correct"' not in blob and '"distractors"' not in blob


def test_redactor_audited_games_keep_component_fields_drop_answers():
    """Audit fence for the 3 same-bug-class games (sentence_fill, memory_palace,
    real_life_challenge): every field the React component reads survives
    redaction, while the answer-key fields the component does NOT read are gone.

    Unlike gb_ttt these need NO derived shape — the redactor leaves them
    structurally intact; this guards that the deny-list never over-strips a
    display field the component depends on."""
    raw = {
        # SentenceFill.tsx reads id/mode/passage/word_bank/difficulty/pisa_level;
        # answers + explanations are stripped (component never reads them).
        "gb_sentence_fill": [
            {
                "id": "sf1",
                "mode": "word_bank",
                "passage": "The capital is ___.",
                "word_bank": ["Paris", "Lyon"],
                "difficulty": "easy",
                "pisa_level": "L2",
                "answers": ["LEAK_SF_ANS"],
                "explanations": ["LEAK_SF_EXP"],
            }
        ],
        # MemoryPalace.tsx reads palaces[].{name,locations[].name}, concepts[].
        # {id,term} — pedagogical hint material, no answer key to strip.
        "gb_memory_palace": {
            "palaces": [
                {"key": "p1", "name": "Kitchen", "locations": [{"name": "Sink"}, {"name": "Stove"}]}
            ],
            "concepts": [
                {"id": "mp-c1", "term": "Mitosis", "description": "cell division"},
                {"id": "mp-c2", "term": "Osmosis"},
            ],
        },
        # RealLifeChallenge.tsx reads steps[].options[].{id,label} but NOT
        # is_correct/consequence/acceptable_keywords — those are stripped.
        "real_life_challenge": {
            "id": "rlc1",
            "expert_role": "teacher",
            "title": "Case",
            "intro": "Scenario hook.",
            "steps": [
                {
                    "id": "step1",
                    "kind": "decision",
                    "title": "Assess",
                    "prompt": "Pick one.",
                    "options": [
                        {"id": "a", "label": "Option A", "is_correct": True, "consequence": "LEAK_RLC_CONS"},
                        {"id": "b", "label": "Option B", "is_correct": False},
                    ],
                    "acceptable_keywords": ["LEAK_RLC_KW"],
                }
            ],
        },
    }
    safe = redact_for_runtime(raw, hw_id="HW-AUDIT")
    blob = json.dumps(safe)

    # --- SentenceFill: component fields survive, answers/explanations gone ---
    sf = safe["gb_sentence_fill"][0]
    for field in ("id", "mode", "passage", "word_bank", "difficulty", "pisa_level"):
        assert field in sf, f"SentenceFill display field stripped: {field}"
    assert "answers" not in sf and "explanations" not in sf
    assert "LEAK_SF_ANS" not in blob and "LEAK_SF_EXP" not in blob

    # --- MemoryPalace: palaces + concepts intact (no answer field to strip) ---
    mp = safe["gb_memory_palace"]
    assert mp["palaces"][0]["name"] == "Kitchen"
    assert mp["palaces"][0]["locations"][0]["name"] == "Sink"
    assert mp["concepts"][0]["id"] == "mp-c1" and mp["concepts"][0]["term"] == "Mitosis"

    # --- RealLifeChallenge: option {id,label} survive; answer keys stripped ---
    step = safe["real_life_challenge"]["steps"][0]
    opt = step["options"][0]
    assert opt["id"] == "a" and opt["label"] == "Option A"
    assert "is_correct" not in opt and "consequence" not in opt
    assert "acceptable_keywords" not in step
    assert "LEAK_RLC_CONS" not in blob and "LEAK_RLC_KW" not in blob


def test_gate_state_fresh_session_locked(client, v2_homework_with_secrets):
    resp = client.get(f"/api/runtime/homeworks/{v2_homework_with_secrets}/gate-state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["practice_arc_unlocked"] is False
    assert data["cbp"]["checkpoints_total"] == 3
    assert data["cbp"]["threshold"] == 2
    assert data["mc"]["threshold_pct"] == 60


def test_hydration_404_for_missing(client):
    resp = client.get("/api/runtime/homeworks/HW-DOES-NOT-EXIST")
    assert resp.status_code == 404


# ---- Unit-level: legacy game deny-lists (no PUT, no strict-schema fight) ----
# Proves the shared redaction_constants deny-lists strip the per-game
# server-only fields the injector historically stripped.

def test_redactor_strips_legacy_game_answers():
    raw = {
        "boss_questions": [{"q": "Explain.", "ans": ["LEAK_BOSS_ANS"], "answer_spec": {"expected": "LEAK_BOSS_EXP"}}],
        "gb_tile_match": [{"left": "a", "right": "b", "explanation": "LEAK_TM"}],
        "gb_sentence_fill": [{"passage": "fill _", "answers": ["LEAK_SF"], "explanations": ["LEAK_SFX"]}],
        "real_life_challenge": {
            "steps": [{"options": [{"label": "opt", "is_correct": True, "consequence": "LEAK_RLC", "acceptable_keywords": ["LEAK_KW"]}]}]
        },
    }
    safe = redact_for_runtime(raw)
    blob = json.dumps(safe)
    for tok in ["LEAK_BOSS_ANS", "LEAK_BOSS_EXP", "LEAK_TM", "LEAK_SF", "LEAK_SFX", "LEAK_RLC", "LEAK_KW"]:
        assert tok not in blob, f"legacy game answer leaked: {tok}"
    # display content survives
    assert "Explain." in blob and "opt" in blob and "fill _" in blob


def test_redactor_does_not_mutate_input():
    raw = {"case_based_preview": {"checkpoints": [{"answer_spec": {"expected": "keep"}}]}}
    redact_for_runtime(raw)
    # original still has the answer (deep-copied, not mutated)
    assert raw["case_based_preview"]["checkpoints"][0]["answer_spec"]["expected"] == "keep"


def test_hydration_strips_cbp_reasoning_keywords_and_rubric():
    """The CBP "Decision Process Explanation" answer fields (concept/method/
    mistake keyword buckets + acceptable_keywords + rubric + pass_score) are
    stripped from hydration. ONLY the student-visible `prompt` + `min_chars`
    survive.

    If this fails, the open-ended reasoning step ships its grading anchors to
    the browser — a direct answer leak. Release blocker."""
    raw = {
        "case_based_preview": {
            "checkpoints": [
                {"question": "Q1", "answer_spec": {"expected": "LEAK_CKP"}},
            ],
            "decision_process_explanation": {
                "prompt": "Explain which concept applies and why this method.",
                "min_chars": 90,
                "concept_keywords": ["LEAK_CONCEPT_KW"],
                "method_keywords": ["LEAK_METHOD_KW"],
                "mistake_keywords": ["LEAK_MISTAKE_KW"],
                "acceptable_keywords": ["LEAK_ACCEPTABLE_KW"],
                "rubric": {"concept": "LEAK_RUBRIC"},
                "pass_score": 65,
            },
        }
    }
    safe = redact_for_runtime(raw, hw_id="HW-CBP-R")
    dpe = safe["case_based_preview"]["decision_process_explanation"]

    # Student-visible fields survive verbatim.
    assert dpe.get("prompt") == "Explain which concept applies and why this method."
    assert dpe.get("min_chars") == 90

    # Every answer-bearing key is gone — at this nesting level.
    for k in (
        "concept_keywords", "method_keywords", "mistake_keywords",
        "acceptable_keywords", "rubric", "pass_score",
    ):
        assert k not in dpe, f"answer-bearing field survived hydration: {k}"

    # And no anchor value appears anywhere in the serialized payload.
    blob = json.dumps(safe)
    for tok in (
        "LEAK_CONCEPT_KW", "LEAK_METHOD_KW", "LEAK_MISTAKE_KW",
        "LEAK_ACCEPTABLE_KW", "LEAK_RUBRIC",
    ):
        assert tok not in blob, f"reasoning anchor leaked: {tok}"

    # Input is never mutated (server still reads the full object to grade).
    assert raw["case_based_preview"]["decision_process_explanation"]["pass_score"] == 65
