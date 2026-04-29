"""
Regression guard against TDZ / ReferenceError in the runtime template's
inline JS (specifically the RUNTIME_LABELS block from Wave I3).

Background: PR #53 shipped with `const RUNTIME_LABELS = { uz: { ...,
  'aq.upload_solution': RT('aq.upload_solution'),
  'aq.upload_first':    RT('aq.upload_first'),
  ... }, ru: {...}, en: {...} };` — the RT() calls inside the uz literal
threw `Cannot access 'RUNTIME_LABELS' before initialization` on every
page load (TDZ: RT reads RUNTIME_LABELS, but RUNTIME_LABELS hasn't been
bound yet during literal evaluation).

All 25 markup-inspection tests in test_homework_page.py passed because
they don't execute the JS — they only grep the HTML string.

This test renders the template, extracts the inline script block(s)
that contain RUNTIME_LABELS, and evaluates them via `node -e` with a
minimal DOM polyfill — failing on any TDZ / ReferenceError / SyntaxError
at initialization time, which is exactly the class of bug that would
otherwise slip past HTML-only tests.
"""

import re
import shutil
import subprocess
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_available() -> bool:
    return shutil.which("node") is not None


# Minimal DOM / browser-global polyfill that silences "not defined" errors
# for globals the runtime template references at top level.  We only care
# about initialization-time crashes (TDZ, SyntaxError); later runtime errors
# that require real DOM methods are allowed to pass through unchecked.
_POLYFILL = r"""
var window = globalThis;
var navigator = { language: 'uz', userAgent: '' };
var document = {
    documentElement: {
        lang: 'uz',
        getAttribute: function(a) { return a === 'lang' ? 'uz' : null; },
        setAttribute: function() {},
        style: {},
        classList: { add: function(){}, remove: function(){}, contains: function(){ return false; } }
    },
    querySelectorAll: function() { return []; },
    querySelector:    function() { return null; },
    getElementById:   function() { return null; },
    addEventListener: function() {},
    removeEventListener: function() {},
    dispatchEvent:    function() { return true; },
    createElement:    function() {
        return {
            style: {}, classList: { add: function(){}, remove: function(){}, contains: function(){ return false; } },
            appendChild: function() {}, addEventListener: function() {},
            setAttribute: function() {}, getAttribute: function() { return null; },
            insertAdjacentHTML: function() {}
        };
    },
    createTextNode: function(t) { return { textContent: t }; },
    head: { appendChild: function() {} },
    body: { appendChild: function() {}, style: {} }
};
var localStorage = { getItem: function(){ return null; }, setItem: function(){}, removeItem: function(){} };
var sessionStorage = { getItem: function(){ return null; }, setItem: function(){}, removeItem: function(){} };
var NETS_CTX = { lang: 'uz', hwId: 'fixture', apiBase: '', features: {} };
var KaTeX = undefined;
var MathJax = undefined;
var requestAnimationFrame = function(fn) { fn(0); };
var cancelAnimationFrame  = function() {};
var setTimeout  = function(fn, ms) { try { fn(); } catch(e) {} return 0; };
var clearTimeout = function() {};
var setInterval  = function() { return 0; };
var clearInterval = function() {};
var fetch = function() { return Promise.resolve({ ok: true, json: function(){ return Promise.resolve({}); }, text: function(){ return Promise.resolve(''); } }); };
var console = { log: function(){}, warn: function(){}, error: function(){}, info: function(){} };
"""

# Errors that indicate an initialization-time crash (TDZ, syntax, missing
# const binding).  Later runtime errors that are DOM-related are acceptable.
_FATAL_PATTERNS = [
    "Cannot access",
    "before initialization",
    "SyntaxError",
    "ReferenceError: RUNTIME_LABELS",
    "ReferenceError: RT is not defined",
]


# ---------------------------------------------------------------------------
# Fixture — same pattern as test_homework_page.py::created_hw
# ---------------------------------------------------------------------------

@pytest.fixture
def _eval_hw(client):
    """Create a minimal homework record and return its dict."""
    payload = {
        "title": "Runtime labels eval fixture",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {
                "title": "Runtime labels eval fixture",
                "subject_display": "Algebra",
            },
            "panels": [],
            "flashcards": [],
            "boss_questions": [],
            "memory_sprint": [],
        },
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_runtime_labels_evaluates_without_throwing(client, _eval_hw):
    """
    Render /h/{id}, extract the inline script block(s) containing
    RUNTIME_LABELS, and evaluate each via `node -e`.  Fails if Node
    reports any TDZ / ReferenceError / SyntaxError at init time.

    This test exists specifically to catch the class of bug where a value
    inside a `const` object literal calls a helper that itself reads the
    same const — causing `Cannot access 'X' before initialization`.
    """
    r = client.get(f"/h/{_eval_hw['id']}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    body = r.text

    # Extract inline <script> blocks only (skip external src= scripts).
    inline_scripts = re.findall(
        r'<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>',
        body,
        re.IGNORECASE,
    )
    relevant = [s for s in inline_scripts if "RUNTIME_LABELS" in s]
    assert relevant, (
        "RUNTIME_LABELS block not found in any inline <script> in the rendered page. "
        "Either the template changed or the route returned an unexpected response."
    )

    import tempfile
    import os

    for i, script in enumerate(relevant):
        full_js = _POLYFILL + "\n" + script
        # Write to a temp file to avoid Windows command-line length limits
        # (the script block can be 100 KB+; `-e` hits WinError 206 on >32 KB).
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(full_js)
            tmp_path = tmp.name
        try:
            proc = subprocess.run(
                ["node", tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
        finally:
            os.unlink(tmp_path)

        stderr = proc.stderr or ""
        for bad in _FATAL_PATTERNS:
            assert bad not in stderr, (
                f"Script block #{i + 1} threw a fatal initialization error via node:\n"
                f"{stderr[:600]}"
            )


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_runtime_labels_uz_values_are_plain_strings(client, _eval_hw):
    """
    Guard that the uz sub-dict of RUNTIME_LABELS contains no RT() calls
    at literal-evaluation time.  This is a belt-and-suspenders HTML check
    (complements the node-eval test above) — catches the specific pattern
    `'key': RT('...')` inside the uz block before it ever reaches Node.
    """
    r = client.get(f"/h/{_eval_hw['id']}")
    assert r.status_code == 200
    body = r.text

    # Locate the uz: { ... } block inside RUNTIME_LABELS.
    # We look for the first occurrence of `uz:` after `RUNTIME_LABELS` and
    # scan ahead until the matching closing `}` at the same indent level.
    rt_block_match = re.search(
        r'const RUNTIME_LABELS\s*=\s*\{([\s\S]*?)\}\s*;',
        body,
    )
    if rt_block_match is None:
        pytest.skip("RUNTIME_LABELS block not found (template may have changed structure)")

    full_block = rt_block_match.group(1)

    # Extract the uz sub-object text (everything between `uz: {` and the
    # next top-level `},` that closes it).
    uz_match = re.search(r'\buz\s*:\s*\{([\s\S]*?)\},\s*\n\s*ru\s*:', full_block)
    if uz_match is None:
        pytest.skip("uz block boundary not found (template structure may have changed)")

    uz_block = uz_match.group(1)

    # There must be NO `RT(` calls anywhere inside the uz literal block.
    bad_calls = re.findall(r"RT\s*\(", uz_block)
    assert not bad_calls, (
        f"Found {len(bad_calls)} RT() call(s) inside RUNTIME_LABELS.uz literal — "
        "these cause a TDZ ReferenceError at page load. Replace with string literals.\n"
        f"Offending fragment: {uz_block[:400]}"
    )
