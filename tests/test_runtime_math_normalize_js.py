"""Cross-runtime regression: the JS mathNormalize embedded in
server/template/perfect_homework.html must produce identical output to the
Python normalize_math in server/services/math_normalize.py for every fixture.

Why both: gbAQAction (client) and answer_checker (server) both compare student
answers, but only one of them runs at a time depending on AI availability and
phase routing. A divergence between the two normalizers would surface as
"works in dev, broken in demo" — exactly what AC-01 is fixing.

Strategy: pull the JS function source out of the template, hand it to Node via
stdin, run each fixture, compare to the Python result. Skip cleanly when Node
is not on PATH (CI containers without it).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from server.services.math_normalize import normalize_math


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


# Fixtures the JS normalizer must reproduce. Kept short — the Python suite
# exhaustively covers normalize_math; this test just guarantees parity.
PARITY_FIXTURES = [
    "α",
    "alfa",
    "alpha",
    "tg(α)",
    "ctg β",
    "cotan β",
    "(a−4b)(a²+4ab+16b²)",
    "0,6",
    "3,14",
    "sin B = 0,6",
    "x = 5",
    "ctg α = tg(90 − α)",
    "52°",
    "52 gradus",
    "90°−α",
    "−1.5",
    " 2 x  +  3 ",
    "ALPHA",
    "0.6.",
    "",
    "Alfa + Beta",
]


def _extract_js_function(html: str) -> str:
    """Return the mathNormalize JS body + its dependency tables from the template."""
    # Pull the chunk that starts with "const _MATH_GREEK = {" and ends at
    # "window.mathNormalize = mathNormalize;" inclusive. The audit pinned this
    # block immediately after gbIsLanguageSubject; if a future PR moves it,
    # this regex still locates it by content.
    m = re.search(
        r"const _MATH_GREEK\s*=\s*\{.*?window\.mathNormalize\s*=\s*mathNormalize;",
        html,
        re.DOTALL,
    )
    assert m, "Cannot locate mathNormalize JS block in perfect_homework.html"
    return m.group(0)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not available")
def test_js_mathNormalize_matches_python():
    html = RUNTIME
    js_block = _extract_js_function(html)

    # Build a Node script that loads the function then prints normalized
    # output for each fixture (one JSON per line — easy to parse without any
    # quoting drama on Windows shells).
    fixtures_json = json.dumps(PARITY_FIXTURES, ensure_ascii=False)
    # Browser-only globals the template references (window). Shim them so Node
    # can evaluate the JS verbatim — production behavior is unaffected.
    node_script = (
        "const window = globalThis;\n"
        + js_block
        + "\nconst fixtures = " + fixtures_json + ";\n"
        + "for (const f of fixtures) { "
        + "  process.stdout.write(JSON.stringify({input: f, out: mathNormalize(f)}) + '\\n'); "
        + "}\n"
    )

    proc = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert proc.returncode == 0, f"Node failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"

    js_results = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        js_results[rec["input"]] = rec["out"]

    mismatches = []
    for f in PARITY_FIXTURES:
        py_out = normalize_math(f)
        js_out = js_results.get(f)
        if py_out != js_out:
            mismatches.append((f, py_out, js_out))
    assert not mismatches, (
        "JS / Python normalize_math divergence:\n"
        + "\n".join(f"  {f!r}: py={py!r}  js={js!r}" for f, py, js in mismatches)
    )
