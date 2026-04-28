"""Tests for server.services.quotes — gate-quote selector + legacy migration."""

import random

import pytest

from server.services import quotes as quotes_service


# --- migrate_legacy --------------------------------------------------------


def test_migrate_legacy_none_returns_auto():
    assert quotes_service.migrate_legacy(None) == {"mode": "auto"}


def test_migrate_legacy_empty_list_returns_auto():
    assert quotes_service.migrate_legacy([]) == {"mode": "auto"}


def test_migrate_legacy_string_array_first_nonempty_becomes_custom():
    result = quotes_service.migrate_legacy(["", "Hello world", "Ignored"])
    assert result == {
        "mode": "custom",
        "custom": {"text": "Hello world", "author": ""},
    }


def test_migrate_legacy_object_array_first_entry_becomes_custom():
    result = quotes_service.migrate_legacy(
        [{"t": "Be kind.", "a": "Plato"}, {"t": "Other", "a": "x"}]
    )
    assert result == {
        "mode": "custom",
        "custom": {"text": "Be kind.", "author": "Plato"},
    }


def test_migrate_legacy_already_envelope_passes_through():
    envelope = {"mode": "pinned", "pinned_id": 7}
    assert quotes_service.migrate_legacy(envelope) == envelope


def test_migrate_legacy_runtime_object_treated_as_custom():
    # A {t, a} object (without mode) — accept as custom.
    result = quotes_service.migrate_legacy({"t": "Hi", "a": "Mum"})
    assert result == {"mode": "custom", "custom": {"text": "Hi", "author": "Mum"}}


# --- select ----------------------------------------------------------------


def _seeded_rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def test_select_custom_returns_verbatim():
    envelope = {"mode": "custom", "custom": {"text": "X", "author": "Y"}}
    out = quotes_service.select(envelope)
    assert out["t"] == "X"
    assert out["a"] == "Y"
    assert out["id"] is None


def test_select_pinned_resolves_by_id():
    library = quotes_service.all_quotes()
    target = library[0]
    envelope = {"mode": "pinned", "pinned_id": target["id"]}
    out = quotes_service.select(envelope)
    assert out["t"] == target["text"]
    assert out["a"] == target["author"]
    assert out["origin"] == target["origin"]
    assert out["id"] == target["id"]


def test_select_pinned_missing_id_falls_back_to_auto():
    envelope = {"mode": "pinned", "pinned_id": 999_999}
    out = quotes_service.select(envelope, rng=_seeded_rng())
    # Should still return SOME quote from the library, not crash.
    assert out["t"]
    # The library is real entries, so id should be present (auto-pick).
    assert out["id"] is not None


def test_select_auto_returns_library_entry():
    out = quotes_service.select({"mode": "auto"}, rng=_seeded_rng(1))
    assert out["t"]
    assert out["a"]
    assert out["origin"] in ("National", "Global")
    assert out["type"] in ("fact", "quote")


def test_select_auto_distribution_over_many_calls():
    """Over 1000 calls, the 55/45 origin and 70/30 type split should hold
    within a generous tolerance band."""
    rng = _seeded_rng(123)
    n = 1000
    national = 0
    facts = 0
    for _ in range(n):
        out = quotes_service.select(None, rng=rng)
        if out["origin"] == "National":
            national += 1
        if out["type"] == "fact":
            facts += 1
    nat_share = national / n
    fact_share = facts / n
    # 55% National ± 5%
    assert 0.50 <= nat_share <= 0.60, f"National share {nat_share:.2f} outside [0.50, 0.60]"
    # 70% fact ± 5%
    assert 0.65 <= fact_share <= 0.75, f"Fact share {fact_share:.2f} outside [0.65, 0.75]"


def test_select_none_envelope_is_auto():
    out = quotes_service.select(None, rng=_seeded_rng(2))
    assert out["t"]
    assert out["origin"] in ("National", "Global")


def test_select_legacy_string_array_treated_as_custom():
    out = quotes_service.select(["Salom dunyo"])
    assert out["t"] == "Salom dunyo"
    assert out["a"] == ""


# --- library shape ---------------------------------------------------------


def test_library_loaded():
    library = quotes_service.all_quotes()
    assert len(library) >= 100, "expected the bundled 600-entry library"
    sample = library[0]
    for field in ("type", "author", "text", "origin", "id"):
        assert field in sample, f"missing {field} on library entry"
