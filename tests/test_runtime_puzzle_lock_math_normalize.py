"""Cross-runtime regression for PL-04: gbPLAnswerMatches uses mathNormalize.

Verifies that the dual-pass answer-matcher embedded in perfect_homework.html
accepts math-equivalent student inputs for real Puzzle Lock answers drawn from
HW-20260505-005 (geometriya G8) and HW-20260505-009 (algebra G9).

Strategy: extract both the mathNormalize block and the gbPLAnswerMatches
function from the template, evaluate them under Node.js, then run each
fixture through gbPLAnswerMatches and assert the outcome matches expectations.

Skipped automatically when Node.js is not on PATH (e.g. stripped CI images).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")

# (student_answer, expected_answer, should_match)
FIXTURES: list[tuple[str, str, bool]] = [
    # Identical inputs — literal-match path
    ("cos α",           "cos α",        True),
    ("AC",              "AC",           True),
    ("gipotenuza",      "gipotenuza",   True),
    ("180",             "180",          True),
    # Greek / Uzbek / English name variants
    ("cos alfa",        "cos α",        True),
    ("cos alpha",       "cos α",        True),
    # Degree marker handling
    ("90",              "90°",          True),
    ("90 deg",          "90°",          True),
    # Decimal comma
    ("0,6",             "0.6",          True),
    # LHS prefix stripping
    ("sin B = 0,6",     "0.6",          True),
    # Trig alias (cot ↔ ctg)
    ("cot β",           "ctg β",        True),
    # Wrong answer — should NOT match
    ("sin B = cos A",   "cos α",        False),
    ("not the answer",  "90",           False),
]


def _read() -> str:
    return RUNTIME


def _extract_math_normalize(html: str) -> str:
    """Return the JS mathNormalize block from the template."""
    m = re.search(
        r"const _MATH_GREEK\s*=\s*\{.*?window\.mathNormalize\s*=\s*mathNormalize;",
        html,
        re.DOTALL,
    )
    assert m, "Cannot locate mathNormalize JS block in perfect_homework.html"
    return m.group(0)


def _extract_gb_pl_answer_matches(html: str) -> str:
    """Return the gbPLAnswerMatches function definition from the template."""
    m = re.search(
        r"function gbPLAnswerMatches\(.*?\{(?P<body>.*?)\n\s{8}\}",
        html,
        re.DOTALL,
    )
    assert m, "Cannot locate gbPLAnswerMatches function in perfect_homework.html"
    # Return the complete function declaration (header + body + closing brace)
    return "function gbPLAnswerMatches(" + m.group(0).split("function gbPLAnswerMatches(", 1)[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not available")
def test_gb_pl_answer_matches_fixtures():
    """gbPLAnswerMatches must accept/reject every real-content fixture."""
    html = _read()
    math_normalize_js = _extract_math_normalize(html)
    answer_matches_js = _extract_gb_pl_answer_matches(html)

    fixtures_json = json.dumps(
        [{"student": s, "expected": e, "shouldMatch": ok} for s, e, ok in FIXTURES],
        ensure_ascii=False,
    )

    node_script = (
        "const window = globalThis;\n"
        + math_normalize_js + "\n"
        + answer_matches_js + "\n"
        + "const fixtures = " + fixtures_json + ";\n"
        + "const results = [];\n"
        + "for (const f of fixtures) {\n"
        + "  const got = gbPLAnswerMatches(f.student, f.expected);\n"
        + "  results.push({student: f.student, expected: f.expected, "
        + "shouldMatch: f.shouldMatch, got: got});\n"
        + "}\n"
        + "process.stdout.write(JSON.stringify(results) + '\\n');\n"
    )

    proc = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert proc.returncode == 0, (
        f"Node.js failed to evaluate gbPLAnswerMatches:\n"
        f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    )

    results = json.loads(proc.stdout.strip())
    failures = [
        r for r in results if r["got"] != r["shouldMatch"]
    ]
    assert not failures, (
        "gbPLAnswerMatches produced wrong results for:\n"
        + "\n".join(
            f"  student={r['student']!r} expected={r['expected']!r} "
            f"want={r['shouldMatch']} got={r['got']}"
            for r in failures
        )
    )
