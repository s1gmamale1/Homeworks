"""
Unit tests for `server.services.progress.compute_progress`.

The dashboard card progress bar must reflect real content completeness,
not arbitrary status-bucket numbers. These tests pin the canonical
content checklist (9 sections) and the status overrides in place.
"""
import pytest

from server.services.progress import (
    CANONICAL_SECTIONS,
    compute_progress,
    filled_sections,
)


# ---------------------------------------------------------------------------
# Canonical section list — the denominator of the ratio
# ---------------------------------------------------------------------------

def test_canonical_sections_locked():
    """The set of sections counted toward progress is the load-bearing
    contract — adding/removing one shifts every existing homework's bar.
    Lock the exact list."""
    assert tuple(CANONICAL_SECTIONS) == (
        "title",
        "quotes",
        "panels",
        "flashcards",
        "memory_sprint",
        "real_life",
        "game_breaks",
        "boss_questions",
        "reflection",
    )


# ---------------------------------------------------------------------------
# Status overrides
# ---------------------------------------------------------------------------

def test_ready_status_returns_100_regardless_of_content():
    """A homework whose status is "ready" has been fully built by the
    pipeline — progress is 100 by definition."""
    assert compute_progress({"status": "ready", "content_json": None}) == 100
    assert compute_progress({"status": "ready", "content_json": "{}"}) == 100


def test_error_status_returns_0_regardless_of_content():
    """An "error" homework failed to build — show 0% so the empty bar
    matches the failure pill."""
    full = {"meta": {"title": "x"}, "quotes": ["q"], "panels": [{"pages": [{}]}],
            "flashcards": [{"term": "a"}], "memory_sprint": [{"prompt": "p"}],
            "real_life": {"story": "s"}, "gb_adaptive_quiz": [{"q": "q"}],
            "boss_questions": [{"q": "q"}], "reflection": {"summary": "s"}}
    assert compute_progress({"status": "error", "content_json": full, "title": "T"}) == 0


# ---------------------------------------------------------------------------
# Empty draft → 0 (or close to)
# ---------------------------------------------------------------------------

def test_empty_draft_returns_zero():
    assert compute_progress({"status": "draft", "content_json": None}) == 0
    assert compute_progress({"status": "draft", "content_json": {}}) == 0


def test_draft_with_only_title_counts_one_section():
    pct = compute_progress({"status": "draft", "title": "Algebra basics", "content_json": {}})
    # 1 / 9 sections = 11.1% → rounded → 11
    assert pct == 11


# ---------------------------------------------------------------------------
# Each section contributes evenly
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "content_overlay,expected_section",
    [
        ({"quotes": ["q1"]}, "quotes"),
        ({"panels": [{"pages": [{"blocks": []}]}]}, "panels"),
        ({"flashcards": [{"term": "a", "def": "b"}]}, "flashcards"),
        ({"memory_sprint": [{"prompt": "?"}]}, "memory_sprint"),
        ({"real_life": {"story": "Once upon a time"}}, "real_life"),
        ({"gb_adaptive_quiz": [{"q": "?"}]}, "game_breaks"),
        ({"gb_memory_match": [["a", "b"]]}, "game_breaks"),  # alternative gb_*
        ({"boss_questions": [{"q": "?"}]}, "boss_questions"),
        ({"reflection": {"summary": "Wrap up"}}, "reflection"),
    ],
)
def test_each_section_counts_when_filled(content_overlay, expected_section):
    """Drop each section in isolation into an empty draft and verify it
    bumps the count by exactly one."""
    hw = {"status": "draft", "title": "T", "content_json": content_overlay}
    sections = filled_sections(hw)
    assert "title" in sections
    assert expected_section in sections
    # Title + this one section = 2 of 9 → 22%
    assert compute_progress(hw) == 22


# ---------------------------------------------------------------------------
# Empty / malformed sub-fields don't count
# ---------------------------------------------------------------------------

def test_empty_lists_do_not_count():
    hw = {"status": "draft", "title": "T", "content_json": {
        "quotes": [], "flashcards": [], "memory_sprint": [],
        "boss_questions": [], "panels": [],
    }}
    # Only title fills — 1/9 = 11
    assert compute_progress(hw) == 11


def test_panels_without_pages_dont_count():
    """A panel object with no `pages` array is just a stub — doesn't count."""
    hw = {"status": "draft", "title": "T", "content_json": {
        "panels": [{"id": 1, "title": "Stub"}],  # no pages
    }}
    assert "panels" not in filled_sections(hw)
    assert compute_progress(hw) == 11  # title only


def test_real_life_story_is_enough():
    hw = {"status": "draft", "title": "T", "content_json": {
        "real_life": {"story": "Once a teacher..."},
    }}
    assert "real_life" in filled_sections(hw)


def test_real_life_with_only_questions_counts():
    hw = {"status": "draft", "title": "T", "content_json": {
        "real_life": {"q1": {"prompt": "What?", "ans": "x"}},
    }}
    assert "real_life" in filled_sections(hw)


def test_real_life_completely_empty_does_not_count():
    hw = {"status": "draft", "title": "T", "content_json": {
        "real_life": {"badge": "RL"},  # no story, no questions
    }}
    assert "real_life" not in filled_sections(hw)


def test_reflection_with_only_closing_counts():
    hw = {"status": "draft", "title": "T", "content_json": {
        "reflection": {"closing": "See you tomorrow"},
    }}
    assert "reflection" in filled_sections(hw)


def test_game_breaks_only_counts_once_even_if_multiple_present():
    """All 4 gb_* lists together count as ONE 'game_breaks' section."""
    hw = {"status": "draft", "title": "T", "content_json": {
        "gb_adaptive_quiz": [{"q": "1"}],
        "gb_memory_match": [["a", "b"]],
        "gb_why_chain": [{"q": "?"}],
    }}
    sections = filled_sections(hw)
    assert sections.count("game_breaks") == 1
    # Title + game_breaks = 2/9 = 22
    assert compute_progress(hw) == 22


# ---------------------------------------------------------------------------
# generating cap
# ---------------------------------------------------------------------------

def test_generating_status_caps_at_90_even_with_full_content():
    full = {
        "meta": {"title": "Done"},
        "quotes": ["q"],
        "panels": [{"pages": [{"blocks": []}]}],
        "flashcards": [{"term": "a"}],
        "memory_sprint": [{"prompt": "p"}],
        "real_life": {"story": "s"},
        "gb_adaptive_quiz": [{"q": "q"}],
        "boss_questions": [{"q": "q"}],
        "reflection": {"summary": "s"},
    }
    pct = compute_progress({"status": "generating", "content_json": full, "title": "T"})
    # All 9 sections filled → 100, but "generating" caps at 90.
    assert pct == 90


def test_generating_with_partial_content_uses_real_ratio_when_under_cap():
    hw = {"status": "generating", "title": "T", "content_json": {
        "flashcards": [{"term": "a", "def": "b"}],
        "memory_sprint": [{"prompt": "?"}],
    }}
    # title + flashcards + memory_sprint = 3/9 = 33
    assert compute_progress(hw) == 33


# ---------------------------------------------------------------------------
# content_json may be a JSON string or a dict
# ---------------------------------------------------------------------------

def test_content_json_as_string_is_parsed():
    hw = {"status": "draft", "title": "T", "content_json":
          '{"flashcards":[{"term":"a","def":"b"}]}'}
    # title + flashcards = 2/9 = 22
    assert compute_progress(hw) == 22


def test_invalid_json_string_is_handled_safely():
    hw = {"status": "draft", "title": "T", "content_json": "not json {{"}
    # Falls back to title only.
    assert compute_progress(hw) == 11


def test_content_json_none_treated_as_empty():
    assert compute_progress({"status": "draft", "content_json": None}) == 0


# ---------------------------------------------------------------------------
# Realistic: a fully-built fixture should hit 100
# ---------------------------------------------------------------------------

def test_fully_built_fixture_hits_100():
    full = {
        "meta": {"title": "Quadratic equations"},
        "quotes": ["Math is the language of the universe."],
        "panels": [{"pages": [{"blocks": [{"type": "p", "text": "..."}]}]}],
        "flashcards": [{"term": "a", "def": "b"}],
        "memory_sprint": [{"prompt": "p", "options": ["a"], "correct": 0}],
        "real_life": {"story": "Once...", "q1": {"prompt": "?", "ans": "x"}},
        "gb_adaptive_quiz": [{"q": "?", "tier": "EASY"}],
        "boss_questions": [{"q": "?", "ans": ["x"]}],
        "reflection": {"summary": "Recap", "question": "What did you learn?"},
    }
    pct = compute_progress({"status": "draft", "title": "Quadratic", "content_json": full})
    # 9/9 = 100. Status is draft (not capped), so should hit 100 honestly.
    assert pct == 100


# ---------------------------------------------------------------------------
# Defensive
# ---------------------------------------------------------------------------

def test_non_dict_input_returns_zero():
    assert compute_progress(None) == 0
    assert compute_progress("nope") == 0
    assert compute_progress(42) == 0
    assert compute_progress([]) == 0
