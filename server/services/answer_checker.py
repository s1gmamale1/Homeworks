import string
import re
from typing import Optional
from rapidfuzz import fuzz
from sympy import sympify

def is_uzbek(text: str) -> bool:
    return not text.isascii()

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
    else:
        return {"verdict": "incorrect", "reason": f"unknown type: {ans_type}"}

