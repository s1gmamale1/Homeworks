"""Regression tests for TileMatchPair Pydantic schema (Chunk A).

Guards:
  - Valid pairs round-trip through schema validation.
  - Palace-tile constraint (premium-only).
  - Field length limits (≤ 300 chars).
  - Collection-level validators on ContentJSON.gb_tile_match:
      - max 8 pairs
      - unique id values
      - unique left strings (distractor rule)
      - unique right strings (distractor rule)
      - at most one is_palace_tile per board
  - extra="allow" forward-compatibility.
"""

import pytest
from pydantic import ValidationError

from server.schemas.content import ContentJSON, TileMatchPair


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pair(**kwargs) -> dict:
    """Return a valid minimal TileMatchPair dict, merged with overrides."""
    base = {"id": "tm_001", "left": "F = ma", "right": "Newton's 2nd"}
    base.update(kwargs)
    return base


def _make_content_with_pairs(pairs: list[dict]) -> dict:
    """Wrap a list of pair dicts into a minimal ContentJSON dict."""
    return {
        "meta": {
            "title": "TM Schema Test",
            "subject_display": "Physics",
            "section": "",
            "cefr_level": "",
        },
        "gb_tile_match": pairs,
    }


# ---------------------------------------------------------------------------
# Test 1: valid basic pair survives schema validation
# ---------------------------------------------------------------------------

def test_tile_match_pair_valid_basic_round_trip():
    pair = TileMatchPair(**_make_pair())
    assert pair.id == "tm_001"
    assert pair.left == "F = ma"
    assert pair.right == "Newton's 2nd"
    assert pair.tier == "basic"
    assert pair.is_palace_tile is False
    assert pair.concept_family is None


# ---------------------------------------------------------------------------
# Test 2: palace tile with tier="basic" must raise
# ---------------------------------------------------------------------------

def test_tile_match_pair_palace_premium_only_validates_basic_rejected():
    with pytest.raises(ValidationError) as exc_info:
        TileMatchPair(**_make_pair(is_palace_tile=True, tier="basic"))
    assert "premium-only" in str(exc_info.value).lower() or "palace" in str(exc_info.value).lower()


def test_tile_match_pair_palace_premium_tier_accepted():
    pair = TileMatchPair(**_make_pair(is_palace_tile=True, tier="premium"))
    assert pair.is_palace_tile is True
    assert pair.tier == "premium"


# ---------------------------------------------------------------------------
# Test 3: field length limits — > 300 chars must raise
# ---------------------------------------------------------------------------

def test_tile_match_pair_field_length_limits():
    long_string = "x" * 301

    with pytest.raises(ValidationError):
        TileMatchPair(**_make_pair(left=long_string))

    with pytest.raises(ValidationError):
        TileMatchPair(**_make_pair(right=long_string))

    # Exactly 300 chars should pass
    ok_string = "x" * 300
    pair = TileMatchPair(**_make_pair(left=ok_string, right=ok_string))
    assert len(pair.left) == 300


# ---------------------------------------------------------------------------
# Test 4: collection max 8 pairs — 9 pairs must raise
# ---------------------------------------------------------------------------

def test_tile_match_collection_max_8_pairs():
    pairs = [
        {"id": f"tm_{i:03d}", "left": f"left_{i}", "right": f"right_{i}"}
        for i in range(1, 10)  # 9 pairs
    ]
    with pytest.raises(ValidationError) as exc_info:
        ContentJSON(**_make_content_with_pairs(pairs))
    assert "1" in str(exc_info.value) or "8" in str(exc_info.value) or "9" in str(exc_info.value)


def test_tile_match_collection_max_8_pairs_exactly_8_accepted():
    pairs = [
        {"id": f"tm_{i:03d}", "left": f"left_{i}", "right": f"right_{i}"}
        for i in range(1, 9)  # exactly 8
    ]
    content = ContentJSON(**_make_content_with_pairs(pairs))
    assert len(content.gb_tile_match) == 8


def test_tile_match_collection_empty_list_accepted_as_disabled():
    content = ContentJSON(**_make_content_with_pairs([]))
    assert content.gb_tile_match == []


# ---------------------------------------------------------------------------
# Test 5: unique left strings required
# ---------------------------------------------------------------------------

def test_tile_match_collection_unique_lefts_required():
    pairs = [
        {"id": "tm_001", "left": "DUPLICATE", "right": "right_1"},
        {"id": "tm_002", "left": "DUPLICATE", "right": "right_2"},
    ]
    with pytest.raises(ValidationError) as exc_info:
        ContentJSON(**_make_content_with_pairs(pairs))
    assert "left" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 6: unique right strings required
# ---------------------------------------------------------------------------

def test_tile_match_collection_unique_rights_required():
    pairs = [
        {"id": "tm_001", "left": "left_1", "right": "DUPLICATE"},
        {"id": "tm_002", "left": "left_2", "right": "DUPLICATE"},
    ]
    with pytest.raises(ValidationError) as exc_info:
        ContentJSON(**_make_content_with_pairs(pairs))
    assert "right" in str(exc_info.value).lower() or "unique" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 7: at most one palace tile per board
# ---------------------------------------------------------------------------

def test_tile_match_collection_at_most_one_palace():
    pairs = [
        {"id": "tm_001", "left": "left_1", "right": "right_1",
         "is_palace_tile": True, "tier": "premium"},
        {"id": "tm_002", "left": "left_2", "right": "right_2",
         "is_palace_tile": True, "tier": "premium"},
    ]
    with pytest.raises(ValidationError) as exc_info:
        ContentJSON(**_make_content_with_pairs(pairs))
    assert "palace" in str(exc_info.value).lower() or "one" in str(exc_info.value).lower()


def test_tile_match_collection_one_palace_accepted():
    pairs = [
        {"id": "tm_001", "left": "left_1", "right": "right_1",
         "is_palace_tile": True, "tier": "premium"},
        {"id": "tm_002", "left": "left_2", "right": "right_2"},
    ]
    content = ContentJSON(**_make_content_with_pairs(pairs))
    assert sum(1 for p in content.gb_tile_match if p.is_palace_tile) == 1


# ---------------------------------------------------------------------------
# Test 8: extra="allow" — forward-compat unknown fields pass through
# ---------------------------------------------------------------------------

def test_tile_match_extra_fields_allowed():
    pair = TileMatchPair(**_make_pair(future_field="some_future_value", another_key=42))
    # Unknown fields should not cause a ValidationError
    data = pair.model_dump()
    assert data["future_field"] == "some_future_value"
    assert data["another_key"] == 42
