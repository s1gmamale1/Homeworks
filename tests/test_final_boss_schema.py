"""Regression tests for BossMeta schema additions (Chunk A).

Guards:
  - BossMeta minimal round-trip.
  - Default boss_type is "sub".
  - Validation rejects attempts_max=0.
  - Validation rejects starting_hp_override < 10.
  - Mythical + attempts_max=2 → ValidationError.
  - Mythical + attempts_max=None → valid (forward-compat).
  - BossAntiCheatPolicy nested round-trip.
  - BossQuestion pisa_level/bloom_level/hint_cost_per_use optional fields.
  - ContentJSON-level mythical+hints cross-validator.
  - extra="allow" forward-compatibility on BossMeta + BossAntiCheatPolicy.
  - Legacy boss_questions without boss_meta validates clean (back-compat).
"""

import pytest
from pydantic import ValidationError
import json
from pathlib import Path

from server.schemas.content import (
    BossAntiCheatPolicy,
    BossBloomLevel,
    BossMeta,
    BossPisaLevel,
    BossQuestion,
    ContentJSON,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_meta() -> dict:
    return {
        "title": "FB Schema Test",
        "subject_display": "Math",
        "section": "",
        "cefr_level": "",
    }


def _minimal_content(**kwargs) -> dict:
    base = {"meta": _minimal_meta()}
    base.update(kwargs)
    return base


def _make_boss_question(**overrides) -> dict:
    base = {
        "q": "Solve x^2 = 4",
        "ans": ["2", "-2"],
        "dmg": 10,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test 1: BossMeta minimal round-trip
# ---------------------------------------------------------------------------

def test_boss_meta_minimal_round_trip():
    """Minimal BossMeta dict validates and all defaults are populated."""
    meta = BossMeta()
    assert meta.boss_type == "sub"
    assert meta.grade_band is None
    assert meta.attempts_max is None
    assert meta.anti_cheat is None
    assert meta.starting_hp_override is None
    assert meta.use_dynamic_boss is False


# ---------------------------------------------------------------------------
# Test 2: default boss_type is "sub"
# ---------------------------------------------------------------------------

def test_boss_meta_default_boss_type_sub():
    """When boss_type is omitted, it defaults to 'sub'."""
    meta = BossMeta(grade_band="g5")
    assert meta.boss_type == "sub"


def test_boss_meta_dynamic_boss_round_trip():
    """Builder opt-in flag validates and survives model serialization."""
    meta = BossMeta(use_dynamic_boss=True)

    assert meta.use_dynamic_boss is True
    assert meta.model_dump()["use_dynamic_boss"] is True


def test_content_schema_mirror_includes_dynamic_boss_flag():
    """The checked-in JSON schema mirror must expose boss_meta.use_dynamic_boss."""
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "server" / "schema" / "content_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    boss_meta = schema["$defs"]["BossMeta"]
    flag = boss_meta["properties"]["use_dynamic_boss"]
    assert flag["type"] == "boolean"
    assert flag["default"] is False


# ---------------------------------------------------------------------------
# Test 3: attempts_max=0 → ValidationError
# ---------------------------------------------------------------------------

def test_boss_meta_attempts_max_zero_rejected():
    """attempts_max=0 violates the >=1 rule (use None for unlimited)."""
    with pytest.raises(ValidationError) as exc_info:
        BossMeta(attempts_max=0)
    assert "attempts_max" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 4: starting_hp_override < 10 → ValidationError
# ---------------------------------------------------------------------------

def test_boss_meta_starting_hp_below_10_rejected():
    """starting_hp_override=5 is below the minimum of 10."""
    with pytest.raises(ValidationError) as exc_info:
        BossMeta(starting_hp_override=5)
    assert "starting_hp_override" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 5: mythical + attempts_max=2 → ValidationError
# ---------------------------------------------------------------------------

def test_boss_meta_mythical_with_attempts_2_rejected():
    """Mythical boss has fixed attempts_max=1; any other positive value is invalid."""
    with pytest.raises(ValidationError) as exc_info:
        BossMeta(boss_type="mythical", attempts_max=2)
    assert "mythical" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 6: mythical + attempts_max=None → valid
# ---------------------------------------------------------------------------

def test_boss_meta_mythical_with_attempts_none_accepted():
    """Mythical + attempts_max=None is valid (forward-compat — treated as 1 at runtime)."""
    meta = BossMeta(boss_type="mythical", attempts_max=None)
    assert meta.boss_type == "mythical"
    assert meta.attempts_max is None


# ---------------------------------------------------------------------------
# Test 7: BossAntiCheatPolicy nested round-trip
# ---------------------------------------------------------------------------

def test_boss_meta_anti_cheat_nested_round_trip():
    """BossAntiCheatPolicy fields survive through BossMeta round-trip."""
    meta = BossMeta(
        boss_type="big",
        anti_cheat=BossAntiCheatPolicy(paste_detect=True, response_time_floor_ms=500),
    )
    assert meta.anti_cheat is not None
    assert meta.anti_cheat.paste_detect is True
    assert meta.anti_cheat.response_time_floor_ms == 500


# ---------------------------------------------------------------------------
# Test 8: BossQuestion pisa_level optional — both with and without
# ---------------------------------------------------------------------------

def test_boss_question_pisa_level_optional():
    """pisa_level is Optional — both present and absent validate correctly."""
    without = BossQuestion(**_make_boss_question())
    assert without.pisa_level is None

    with_level = BossQuestion(**_make_boss_question(pisa_level="L4"))
    assert with_level.pisa_level == "L4"


# ---------------------------------------------------------------------------
# Test 9: bloom_level enum — invalid value raises, valid passes
# ---------------------------------------------------------------------------

def test_boss_question_bloom_level_optional_enum_only():
    """bloom_level only accepts the four spec values; invalid → ValidationError."""
    with pytest.raises(ValidationError):
        BossQuestion(**_make_boss_question(bloom_level="invalid_value"))

    valid = BossQuestion(**_make_boss_question(bloom_level="apply"))
    assert valid.bloom_level == "apply"


# ---------------------------------------------------------------------------
# Test 10: hint_cost_per_use — int and None both accepted
# ---------------------------------------------------------------------------

def test_boss_question_hint_cost_per_use_optional_int():
    """hint_cost_per_use accepts int or None; both are valid."""
    without = BossQuestion(**_make_boss_question())
    assert without.hint_cost_per_use is None

    with_cost = BossQuestion(**_make_boss_question(hint_cost_per_use=15))
    assert with_cost.hint_cost_per_use == 15


# ---------------------------------------------------------------------------
# Test 11: ContentJSON mythical + question hints → ValidationError
# ---------------------------------------------------------------------------

def test_content_json_mythical_with_question_hints_rejected():
    """Mythical boss spec §11: zero hints. Non-empty hints array → ValidationError."""
    content = _minimal_content(
        boss_meta={"boss_type": "mythical"},
        boss_questions=[
            {
                "q": "Hard question",
                "ans": ["answer"],
                "dmg": 30,
                "hints": ["Hint 1", "Hint 2", "Hint 3"],
            }
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        ContentJSON(**content)
    assert "mythical" in str(exc_info.value).lower() or "hints" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 12: ContentJSON mythical + zero hints → valid
# ---------------------------------------------------------------------------

def test_content_json_mythical_with_zero_hints_accepted():
    """Mythical boss with zero hints satisfies spec §11."""
    content = _minimal_content(
        boss_meta={"boss_type": "mythical"},
        boss_questions=[
            {
                "q": "Hard question",
                "ans": ["answer"],
                "dmg": 30,
                "hints": [],
            }
        ],
    )
    cj = ContentJSON(**content)
    assert cj.boss_meta is not None
    assert cj.boss_meta.boss_type == "mythical"


# ---------------------------------------------------------------------------
# Test 13: legacy boss_questions without boss_meta validates clean
# ---------------------------------------------------------------------------

def test_content_json_legacy_boss_questions_without_meta_validates_clean():
    """Existing homeworks with boss_questions but no boss_meta validate unchanged."""
    content = _minimal_content(
        boss_questions=[
            _make_boss_question(),
            _make_boss_question(q="Another question", dmg=20),
        ],
    )
    cj = ContentJSON(**content)
    assert cj.boss_meta is None
    assert cj.boss_questions is not None
    assert len(cj.boss_questions) == 2


# ---------------------------------------------------------------------------
# Test 14: extra="allow" works on BossMeta + BossAntiCheatPolicy
# ---------------------------------------------------------------------------

def test_content_json_extra_fields_allowed_for_forward_compat():
    """extra='allow' on BossMeta + BossAntiCheatPolicy accepts unknown keys."""
    # Future fields unknown today should not break existing rows.
    meta = BossMeta(
        boss_type="sub",
        future_field_xyz="some_value",  # unknown future key
    )
    # Should not raise ValidationError
    assert meta.boss_type == "sub"

    anti_cheat = BossAntiCheatPolicy(
        paste_detect=False,
        unknown_future_field=42,
    )
    assert anti_cheat.paste_detect is False

    content = _minimal_content(
        boss_meta={
            "boss_type": "sub",
            "unknown_future_boss_meta_key": "forward_compat",
        },
    )
    cj = ContentJSON(**content)
    assert cj.boss_meta is not None
    assert cj.boss_meta.boss_type == "sub"
