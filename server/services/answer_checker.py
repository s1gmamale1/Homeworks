import string
import re
from typing import Optional
from rapidfuzz import fuzz

# Fix #2: DoS guard for sympify/parse_expr on untrusted student input.
# SymPy is well-known to hang on inputs like 2**2**2**2**2 (power tower DoS).
MAX_SYMPIFY_INPUT_LEN = 200

# Fix #8: Characters that identify Uzbek text beyond simple isascii().
# Heuristic checks (in order):
#   a) Any character in Cyrillic block U+0400–U+04FF
#   b) Extended Uzbek-specific Cyrillic: ҳ ң ў қ ғ
#   c) Unicode apostrophe variants used in Latin Uzbek: ʻ ʼ ' '
#   d) Latin Uzbek digraph patterns: o' or g' (Latin letter + apostrophe variant)
_UZBEK_APOSTROPHES = set("ʻʼ‘’")
_UZBEK_CYRILLIC_EXTRA = set("ҳңўқғҲҢҮҚҒ")


def is_uzbek(text: str) -> bool:
    """Return True if *text* contains markers of Uzbek script.

    Checks (in order):
      a) Any character in Cyrillic block U+0400–U+04FF (covers Russian too, but
         Uzbek Cyrillic is a strict subset so false positives are acceptable).
      b) Extended Uzbek-specific Cyrillic characters: ҳ ң ў қ ғ (and their
         uppercase equivalents).
      c) Unicode apostrophe variants used in Latin Uzbek: ʻ (U+02BB), ʼ (U+02BC),
         ' (U+2018), ' (U+2019).
      d) Latin Uzbek digraph patterns: o' or g' (any of the apostrophe variants
         following the Latin letters o/g).
    """
    apostrophe_pattern = re.compile(r"[og][ʻʼ‘’']", re.IGNORECASE)
    for ch in text:
        cp = ord(ch)
        # a) Cyrillic block
        if 0x0400 <= cp <= 0x04FF:
            return True
        # b) Extended Uzbek Cyrillic (already covered by block above, kept explicit)
        if ch in _UZBEK_CYRILLIC_EXTRA:
            return True
        # c) Unicode apostrophe variants
        if ch in _UZBEK_APOSTROPHES:
            return True
    # d) Latin Uzbek o' / g' patterns
    if apostrophe_pattern.search(text):
        return True
    return False


def _make_tip(verdict: str, student_answer: str, canonical: str) -> Optional[str]:
    if verdict != 'correct':
        return None

    stu_clean = re.sub(r'\s+', '', student_answer)
    can_clean = re.sub(r'\s+', '', canonical)
    if stu_clean == can_clean:
        return None

    tip = "Javobingiz to'g'ri, lekin formatlashni yaxshilash mumkin: " if is_uzbek(canonical) else "Correct, but format could be improved: "
    tip += canonical
    if len(tip) > 80:
        tip = tip[:77] + "..."
    return tip

def _check_numeric(expected: float, tolerance: float, student_answer: str, canonical: str) -> dict:
    try:
        clean_ans = student_answer.strip().replace(',', '.')
        val = float(clean_ans)
        if abs(val - float(expected)) <= tolerance + 1e-9:
            return {
                "verdict": "correct",
                "reason": "within tolerance",
                "format_tip": _make_tip("correct", student_answer, canonical)
            }
        else:
            return {"verdict": "incorrect", "reason": "outside tolerance"}
    except ValueError:
        return {"verdict": "unsure", "reason": "could not parse numeric value"}

def _check_set_match(expected: list, student_answer: str, canonical: str) -> dict:
    ans = student_answer.strip()
    if not ans:
        return {"verdict": "unsure", "reason": "empty input"}

    # Fix #2: Guard against SymPy DoS via long power-tower expressions.
    if len(ans) > MAX_SYMPIFY_INPUT_LEN:
        return {"verdict": "incorrect", "reason": "answer too long for symbolic parse"}

    # Fix #3: Lazy import — sympy is only loaded when set_match is actually used,
    # saving ~500 ms of cold-start import time for requests that never reach this path.
    from sympy import sympify  # noqa: PLC0415

    ans = re.sub(r'√\s*(\d+)', r'sqrt(\1)', ans)
    ans = re.sub(r'\b(yoki|va)\b', ',', ans, flags=re.IGNORECASE)
    ans = ans.replace(';', ',')

    parts = [p.strip() for p in ans.split(',') if p.strip()]

    values = []
    for p in parts:
        if '=' in p:
            p = p.split('=')[-1].strip()

        if '±' in p or '+/-' in p:
            p_base = p.replace('±', '').replace('+/-', '').strip()
            try:
                val = sympify(p_base)
                val_float = float(val.evalf())
                values.extend([val_float, -val_float])
            except Exception:
                pass
        else:
            try:
                val = sympify(p)
                values.append(float(val.evalf()))
            except Exception:
                pass

    if not values:
        return {"verdict": "unsure", "reason": "could not extract numbers"}

    values.sort()
    try:
        exp_floats = sorted([float(x) for x in expected])
    except Exception:
        return {"verdict": "unsure", "reason": "invalid expected list"}

    if len(values) == len(exp_floats):
        match = True
        for v, e in zip(values, exp_floats):
            if abs(v - e) > 1e-5:
                match = False
                break
        if match:
            return {
                "verdict": "correct",
                "reason": "set match successful",
                "format_tip": _make_tip("correct", student_answer, canonical)
            }

    return {"verdict": "unsure", "reason": "sets do not match"}

def _clean_text_exact(text: str) -> str:
    text = text.casefold()
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _check_text_exact(expected: str, student_answer: str, canonical: str) -> dict:
    if not student_answer.strip():
        return {"verdict": "unsure", "reason": "empty input"}

    stu_clean = _clean_text_exact(student_answer)
    exp_clean = _clean_text_exact(expected)

    if stu_clean == exp_clean:
        return {
            "verdict": "correct",
            "reason": "exact match",
            "format_tip": _make_tip("correct", student_answer, canonical)
        }
    else:
        return {"verdict": "unsure", "reason": "exact match failed"}

def _check_text_fuzzy(expected: str, student_answer: str, canonical: str) -> dict:
    if not student_answer.strip():
        return {"verdict": "unsure", "reason": "empty input"}

    ratio = fuzz.ratio(student_answer.casefold(), expected.casefold())
    if ratio >= 90:
        return {
            "verdict": "correct",
            "reason": f"fuzzy match >= 90 (ratio: {ratio})",
            "format_tip": _make_tip("correct", student_answer, canonical)
        }
    elif ratio >= 75:
        return {"verdict": "unsure", "reason": f"fuzzy match >= 75 (ratio: {ratio})"}
    else:
        return {"verdict": "incorrect", "reason": f"fuzzy match < 75 (ratio: {ratio})"}

def _check_option_index(spec: dict, student_answer: str) -> dict:
    """Check a tap-quiz answer by comparing the tapped option index to the expected index.

    ``student_answer`` must be a stringified non-negative integer.  Inputs that
    cannot be parsed, or that fall outside ``[0, option_count)``, are rejected
    as incorrect so the student sees immediate deterministic feedback without any
    AI round-trip.

    Schema fields consumed:
        expected     (int)  – 0-based index of the correct option.
        option_count (int)  – total number of options; used to validate range.
    """
    expected = spec.get("expected")
    option_count = spec.get("option_count")

    # Parse student input
    try:
        idx = int(str(student_answer).strip())
    except (ValueError, TypeError):
        return {
            "verdict": "incorrect",
            "reason": f"student answer {student_answer!r} is not a valid integer index",
        }

    # Range-check (option_count is required; treat missing/non-int as unlimited)
    if isinstance(option_count, int) and option_count > 0:
        if idx < 0 or idx >= option_count:
            return {
                "verdict": "incorrect",
                "reason": (
                    f"index {idx} is out of range for option_count={option_count}"
                ),
            }

    if idx == expected:
        return {"verdict": "correct", "reason": "option index matches expected"}
    else:
        return {"verdict": "incorrect", "reason": f"selected index {idx} != expected {expected}"}


def check(answer_spec: dict, student_answer: str) -> dict:
    if student_answer is None:
        student_answer = ""
    if not isinstance(student_answer, str):
        student_answer = str(student_answer)

    ans_type = answer_spec.get('type')
    expected = answer_spec.get('expected')
    canonical = answer_spec.get('canonical_display', '')

    # Filter out empty input returning unsure, unless type is semantic.
    # Wait, the checker should return unsure on empty for text types or maybe always?
    # I already handled empty in each method where applicable.

    if ans_type == 'numeric':
        return _check_numeric(expected, answer_spec.get('tolerance', 0.0), student_answer, canonical)
    elif ans_type == 'set_match':
        return _check_set_match(expected, student_answer, canonical)
    elif ans_type == 'text_exact':
        return _check_text_exact(expected, student_answer, canonical)
    elif ans_type == 'text_fuzzy':
        return _check_text_fuzzy(expected, student_answer, canonical)
    elif ans_type == 'semantic':
        return {"verdict": "unsure", "reason": "semantic grading requires AI"}
    elif ans_type == 'option_index':
        return _check_option_index(answer_spec, student_answer)
    else:
        return {"verdict": "incorrect", "reason": f"unknown type: {ans_type}"}
