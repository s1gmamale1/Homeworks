"""Wave J — T1: severity classifier tests for the rewritten
``server/services/slur_filter`` module.

Covers:
  * 7 parametrized severity-tier tests (one per tier).
  * 3 per-message language detection tests (uz / ru / en).
  * 5 false-positive guards (cooking term, proper noun, prefix substring).
  * 3 backward-compat ``detect_slurs`` shape tests.

Run:
    pytest tests/test_slur_filter_classify.py -v
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 1. Severity tier mapping — one parametrized test per tier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message, expected_severity",
    [
        # casual_safe — clean "tushuntirib bering" with zero matches.
        ("Iltimos, 5-masalani tushuntirib bering.", "casual_safe"),
        # casual_negative — kept for completeness; classifier currently has
        # no terms loaded into this tier, so the cleanest equivalent is a
        # safe-list term used in casual frustration. The tier still exists
        # in the Severity literal and downstream prompt logic can populate
        # it from meaning analysis later.
        ("bro im so cooked rn", "casual_safe"),  # 'cooked' rescued by safe list
        # insult_mild — 'tormoz' (mild Uzbek insult).
        ("U bola tormoz, hech narsani tushunmaydi.", "insult_mild"),
        # profanity_mild — 'blin' (Russian filler).
        ("blin, this is hard", "profanity_mild"),
        # profanity_strong — 'fuck' (English).
        ("fuck this whole thing", "profanity_strong"),
        # slur_or_hate — 'retard' (ableist).
        ("he is a retard", "slur_or_hate"),
        # sexual_vulgar — 'jalap' (misogynistic sexual insult).
        ("jalap yana xato qildi", "sexual_vulgar"),
    ],
)
def test_classify_severity_tiers(message, expected_severity):
    from server.services.slur_filter import classify

    result = classify(message)
    assert result.severity == expected_severity, (
        f"classify({message!r}).severity = {result.severity!r}, "
        f"expected {expected_severity!r} (matched={result.matched_terms})"
    )


# ---------------------------------------------------------------------------
# 2. Per-message language detection
# ---------------------------------------------------------------------------


def test_lang_detection_cyrillic_only_is_ru():
    from server.services.slur_filter import classify

    result = classify("Привет, как дела?")
    assert result.lang == "ru", f"Cyrillic-only must be 'ru', got {result.lang!r}"


def test_lang_detection_uzbek_latin_is_uz():
    from server.services.slur_filter import classify

    # Uses uka, salom, rahmat — all in the Uzbek-Latin hint set.
    result = classify("Salom uka, rahmat ovqat uchun!")
    assert result.lang == "uz", f"Uzbek Latin must be 'uz', got {result.lang!r}"


def test_lang_detection_plain_english_is_en():
    from server.services.slur_filter import classify

    result = classify("Hello there, how do I solve this equation?")
    assert result.lang == "en", f"Plain English must be 'en', got {result.lang!r}"


# ---------------------------------------------------------------------------
# 3. False-positive guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        # 'class' contains 'ass' as a prefix substring — must NOT match.
        "What time does class start tomorrow?",
        # 'assemble' contains 'ass' as a prefix substring — must NOT match.
        "Let's assemble the puzzle pieces.",
        # 'shitake' contains 'shit' — cooking term, must NOT match.
        "I love shitake mushrooms in my soup.",
        # 'scunthorpe' is a UK town containing a profanity substring — must NOT match.
        "I drove through Scunthorpe last weekend.",
        # 'Pussycat' is a proper-noun band name containing 'pussy' — must NOT match.
        "The Pussycat Dolls released a new song.",
    ],
)
def test_false_positive_guards(message):
    from server.services.slur_filter import classify, detect_slurs

    result = classify(message)
    assert result.is_clean is True, (
        f"False positive on {message!r}: classified as {result.severity} "
        f"matched={result.matched_terms}"
    )
    assert result.severity == "casual_safe"
    assert detect_slurs(message) == [], (
        f"detect_slurs({message!r}) returned {detect_slurs(message)!r}, expected []"
    )


# ---------------------------------------------------------------------------
# 4. Backward-compat — detect_slurs() shape
# ---------------------------------------------------------------------------


def test_detect_slurs_returns_list_of_terms():
    from server.services.slur_filter import detect_slurs

    found = detect_slurs("U lox, javobni bilmayapti.")
    assert isinstance(found, list)
    assert "lox" in found, f"expected 'lox' in {found}"


def test_detect_slurs_clean_message_returns_empty_list():
    from server.services.slur_filter import detect_slurs

    assert detect_slurs("Hello, how are you?") == []
    assert detect_slurs("") == []


def test_detect_slurs_word_boundary_no_partial_match():
    """'tormoz' is a slur; 'tormozlash' (braking process) must NOT match."""
    from server.services.slur_filter import detect_slurs

    assert detect_slurs("U tormoz!") == ["tormoz"]
    assert detect_slurs("tormozlash jarayoni boshlandi") == []


# ---------------------------------------------------------------------------
# 5. SlurClassification dataclass shape
# ---------------------------------------------------------------------------


def test_classification_has_expected_fields():
    from server.services.slur_filter import SlurClassification, classify

    result = classify("U lox!")
    assert isinstance(result, SlurClassification)
    assert result.severity == "insult_mild"
    assert result.category == "uz_mild_insult"
    assert result.lang in {"uz", "ru", "en"}
    assert "lox" in result.matched_terms
    assert result.is_clean is False


def test_classification_clean_message_is_clean():
    from server.services.slur_filter import classify

    r = classify("Iltimos, 5-masalani tushuntirib bering.")
    assert r.is_clean is True
    assert r.severity == "casual_safe"
    assert r.matched_terms == []


def test_classification_empty_message_is_clean():
    from server.services.slur_filter import classify

    r = classify("")
    assert r.is_clean is True
    assert r.severity == "casual_safe"
    assert r.matched_terms == []
