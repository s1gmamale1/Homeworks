"""Regression guard: the boss-context deny-list cannot drift from the
redaction single-source-of-truth (Gap B).

`boss_context_builder._ANSWER_LEAK_KEYS` is now bound to
`redaction_constants.ANSWER_BEARING_KEYS` (union with boss-local extras), so a
new answer-bearing key added there (e.g. `expected_concepts`, the Boss-Arena
grading anchor) is automatically stripped from the boss prompt too.
"""
from __future__ import annotations

from server.services import boss_context_builder as bcb
from server.services.redaction_constants import ANSWER_BEARING_KEYS


def test_answer_leak_keys_superset_of_shared_constant():
    """Every shared answer-bearing key must be in the boss deny-list."""
    leak = set(bcb._ANSWER_LEAK_KEYS)
    missing = set(ANSWER_BEARING_KEYS) - leak
    assert not missing, f"boss deny-list drifted, missing: {missing}"


def test_expected_concepts_now_in_boss_deny_list():
    """The specific key the old hardcoded tuple was missing."""
    assert "expected_concepts" in set(bcb._ANSWER_LEAK_KEYS)


def test_boss_local_historical_extras_preserved():
    """The union must keep the boss-local extras the old tuple carried."""
    leak = set(bcb._ANSWER_LEAK_KEYS)
    assert "canonical" in leak
    assert "answer_spec" in leak


def test_scrub_dict_strips_expected_concepts():
    """`_scrub_dict` removes `expected_concepts` at any nesting level."""
    node = {
        "question_text": "What is the boss asking?",
        "expected_concepts": ["secret concept A", "secret concept B"],
        "nested": {
            "expected_concepts": ["deeper secret"],
            "safe": "keep me",
        },
    }
    scrubbed = bcb._scrub_dict(node)
    assert "expected_concepts" not in scrubbed
    assert "expected_concepts" not in scrubbed["nested"]
    assert scrubbed["nested"]["safe"] == "keep me"
    assert scrubbed["question_text"] == "What is the boss asking?"

    # And the secret values are nowhere in the serialized result.
    import json
    blob = json.dumps(scrubbed, ensure_ascii=False)
    assert "secret concept A" not in blob
    assert "deeper secret" not in blob


def test_scrub_dict_strips_other_answer_bearing_keys():
    """Spot-check that the classic answer keys are still stripped."""
    node = {"expected": "42", "ans": ["42"], "accepted_answers": ["42"], "keep": "ok"}
    scrubbed = bcb._scrub_dict(node)
    assert scrubbed == {"keep": "ok"}
