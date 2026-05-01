"""Regression tests for the dynamic boss-name resolution introduced in PR #106.

Pre-fix code: the runtime template hardcoded `Algebra Boshlig'i` on every
homework regardless of subject. A Physics or Biology homework would still
greet the student with `Algebra Boshlig'i` at the final-boss screen.

Post-fix: `boss_name_for(subject_id, explicit)` resolves the right name —
explicit override wins, otherwise subject default, otherwise generic `Boss`.
The runtime IIFE reads `window.NETS_CTX.boss_name` and rewrites every
`[data-boss-name]` and `[data-boss-name-label]` element.

Each test below would fail on the pre-fix code (the helper didn't exist;
the template's hardcoded string never varied).
"""

from server.services.injector import boss_name_for


def test_boss_name_for_subject_default_algebra():
    """Default subject map: algebra → 'Algebra Boshlig'i'."""
    assert boss_name_for("algebra", None) == "Algebra Boshlig'i"


def test_boss_name_for_subject_default_physics():
    """Pre-fix: physics homeworks still showed 'Algebra Boshlig'i'."""
    assert boss_name_for("physics", None) == "Fizika Boshlig'i"
    assert boss_name_for("fizika", None) == "Fizika Boshlig'i"


def test_boss_name_for_explicit_override_wins():
    """Author-supplied content_json.boss_name overrides the subject default."""
    assert boss_name_for("algebra", "Custom Boss") == "Custom Boss"


def test_boss_name_for_explicit_override_strips_whitespace():
    """Whitespace-only explicit value falls through to default; trim is applied."""
    assert boss_name_for("algebra", "   ") == "Algebra Boshlig'i"
    assert boss_name_for("algebra", "  Custom  ") == "Custom"


def test_boss_name_for_unknown_subject_falls_back_to_generic():
    """Unknown subject id → generic 'Boss', not the algebra default."""
    assert boss_name_for("unknown_xyz", None) == "Boss"


def test_boss_name_for_none_subject_falls_back_to_generic():
    """No subject id and no override → generic 'Boss'."""
    assert boss_name_for(None, None) == "Boss"


def test_boss_name_for_subject_id_is_case_insensitive():
    """Subject id resolution must tolerate casing variations from the API."""
    assert boss_name_for("ALGEBRA", None) == "Algebra Boshlig'i"
    assert boss_name_for("Physics", None) == "Fizika Boshlig'i"
