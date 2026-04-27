import pytest
from server.services.answer_checker import check

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

    spec_uz = {"type": "numeric", "expected": 10, "tolerance": 0.0, "canonical_display": "10 m/s²"}
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
