import time
import pytest
from server.services.answer_checker import check, is_uzbek

def test_numeric():
    spec = {"type": "numeric", "expected": 9.81, "tolerance": 0.05, "canonical_display": "9.81"}
    assert check(spec, "9.81")["verdict"] == "correct"
    assert check(spec, "9.80")["verdict"] == "correct"
    assert check(spec, "9.87")["verdict"] == "incorrect"
    assert check(spec, "9,81")["verdict"] == "correct"  # comma decimal
    assert check(spec, "  9.81  ")["verdict"] == "correct"
    assert check(spec, "abc")["verdict"] == "unsure"  # fails to parse
    assert check(spec, "")["verdict"] == "unsure"

def test_numeric_format_tip():
    spec = {"type": "numeric", "expected": 1000, "tolerance": 0.0, "canonical_display": "1 000"}
    res = check(spec, "1000")
    assert res["verdict"] == "correct"
    assert res.get("format_tip") is None  # spaces difference only, so None

    # canonical_display uses Latin Uzbek apostrophe (o') so is_uzbek returns True
    spec_uz = {"type": "numeric", "expected": 10, "tolerance": 0.0, "canonical_display": "10 m/s (o'lchov)"}
    res = check(spec_uz, "10")
    assert res["verdict"] == "correct"
    assert "Javobingiz to'g'ri" in res["format_tip"]

def test_set_match():
    spec = {"type": "set_match", "expected": [-9, 9], "canonical_display": "x₁,₂ = ±9"}
    assert check(spec, "x₁=-9, x₂=9")["verdict"] == "correct"
    assert check(spec, "±9")["verdict"] == "correct"
    assert check(spec, "-9, 9")["verdict"] == "correct"
    assert check(spec, "9, -9")["verdict"] == "correct"
    assert check(spec, "x = +/- 9")["verdict"] == "correct"
    assert check(spec, "-9 yoki 9")["verdict"] == "correct"
    assert check(spec, "-9 va 9")["verdict"] == "correct"
    assert check(spec, "x_1 = 9; x_2 = -9")["verdict"] == "correct"
    assert check(spec, "±sqrt(81)")["verdict"] == "correct"
    assert check(spec, "±√81")["verdict"] == "correct"
    
    assert check(spec, "9")["verdict"] == "unsure" # Valid parse, missing -9
    assert check(spec, "abc")["verdict"] == "unsure"
    assert check(spec, "")["verdict"] == "unsure"

def test_text_exact():
    spec = {"type": "text_exact", "expected": "Toshkent", "canonical_display": "Toshkent"}
    assert check(spec, "toshkent")["verdict"] == "correct"
    assert check(spec, "Toshkent ")["verdict"] == "correct"
    assert check(spec, " Toshkent! ")["verdict"] == "correct"
    
    assert check(spec, "Samarqand")["verdict"] == "unsure"
    assert check(spec, "")["verdict"] == "unsure"

def test_text_exact_format_tip():
    spec = {"type": "text_exact", "expected": "Ali va Vali", "canonical_display": "Ali va Vali"}
    # English tip fallback if canonical is ASCII
    res = check(spec, "ali va vali")
    assert res["verdict"] == "correct"
    assert "Correct, but format could be improved" in res["format_tip"]
    assert "Ali va Vali" in res["format_tip"]

def test_text_fuzzy():
    spec = {"type": "text_fuzzy", "expected": "mitoxondriya", "canonical_display": "Mitoxondriya"}
    # Exact
    assert check(spec, "mitoxondriya")["verdict"] == "correct"
    # Minor typo (>=90%)
    assert check(spec, "mitoxondria")["verdict"] == "correct" # ratio: 95.6
    # Medium typo (>=75%)
    assert check(spec, "mitoxond")["verdict"] == "unsure"
    # Bad typo (<75%)
    assert check(spec, "ribosoma")["verdict"] == "incorrect"
    
    assert check(spec, "")["verdict"] == "unsure"

def test_semantic():
    spec = {"type": "semantic", "expected": "Any", "canonical_display": "Any"}
    assert check(spec, "Good answer")["verdict"] == "unsure"
    assert check(spec, "")["verdict"] == "unsure"

def test_unknown_type():
    spec = {"type": "magic"}
    assert check(spec, "answer")["verdict"] == "incorrect"


def test_sympify_dos_cap():
    """Inputs longer than MAX_SYMPIFY_INPUT_LEN must be rejected quickly as
    'incorrect' without invoking sympify (which would hang on power-tower DoS).
    The whole check must finish well under 1 second.
    """
    # Build a 500-char power-tower expression: 2**2**2**... (repeating)
    fragment = "2**"
    long_input = (fragment * 200)[:500]  # 500 chars of "2**2**2**..."
    spec = {"type": "set_match", "expected": [4], "canonical_display": "4"}

    t0 = time.perf_counter()
    result = check(spec, long_input)
    elapsed = time.perf_counter() - t0

    assert result["verdict"] == "incorrect", (
        f"Expected 'incorrect' for oversized input, got {result['verdict']!r}"
    )
    assert elapsed < 1.0, (
        f"DoS cap check took {elapsed:.3f}s — must be < 1s"
    )


# ---------------------------------------------------------------------------
# Wave E: option_index type tests
# ---------------------------------------------------------------------------


def test_option_index_correct():
    """Student taps the correct option index → verdict correct."""
    spec = {"type": "option_index", "expected": 2, "option_count": 4}
    result = check(spec, "2")
    assert result["verdict"] == "correct"
    assert "reason" in result


def test_option_index_wrong():
    """Student taps a different valid index → verdict incorrect."""
    spec = {"type": "option_index", "expected": 2, "option_count": 4}
    result = check(spec, "1")
    assert result["verdict"] == "incorrect"
    assert "reason" in result


def test_option_index_out_of_range():
    """Index >= option_count is rejected as incorrect with a descriptive reason."""
    spec = {"type": "option_index", "expected": 0, "option_count": 3}
    result = check(spec, "5")
    assert result["verdict"] == "incorrect"
    assert "out of range" in result["reason"]


def test_option_index_non_integer():
    """Non-integer student answer is rejected as incorrect with a descriptive reason."""
    spec = {"type": "option_index", "expected": 0, "option_count": 4}
    result = check(spec, "foo")
    assert result["verdict"] == "incorrect"
    assert "not a valid integer" in result["reason"]


def test_is_uzbek_heuristic():
    """is_uzbek() must correctly classify common cases."""
    # Plain ASCII — not Uzbek
    assert is_uzbek("Hello world") is False
    assert is_uzbek("plain ASCII") is False

    # Latin Uzbek with o' digraph
    assert is_uzbek("o'qituvchi") is True

    # Cyrillic (covers Russian/Uzbek Cyrillic alike)
    assert is_uzbek("Привет мир") is True

    # Uzbek Cyrillic-specific chars
    assert is_uzbek("ўзбек") is True   # ў is U+04AF
    assert is_uzbek("қалб") is True    # қ is U+049B

    # Unicode apostrophe variant (ʻ) without o'/g' pattern — still Uzbek
    assert is_uzbek("soʻz") is True

    # Latin Uzbek g' pattern
    assert is_uzbek("g'oya") is True
