"""
Wave J.2 / T2 — frontend tutor widget input/screen extractors.

Background: T1 of Wave J.2 relaxes the backend gate so `screen_context`,
`student_work_text`, and `subphase` can flow through every turn (not just
preview). This test guards the FRONTEND helpers introduced in T2:

  * `extractStudentWork(currentSubphase)` — reads the student's CURRENT
    raw input on the active screen (per-subphase DOM selector dispatch).
  * `sanitizeScreenContext(activeRoot)` — clones the active screen root,
    strips answer-key DOM markers (data-correct=true, .correct, etc.),
    serializes the surviving text, and slices to 2000 chars.

We slice the helpers' source out of `server/template/perfect_homework.html`
by their function names, evaluate them in Node with a minimal DOM polyfill
(same approach as `test_runtime_labels_eval.py`), and assert the inputs
produce the expected outputs.

Why a JS-eval test (not a Python unit test): both helpers run client-side,
manipulate DOM nodes directly, and depend on globals (gbState, msState,
stage6State) that only exist in the browser. The only way to test them
end-to-end without spinning up a real browser is to extract the source and
eval under a polyfilled `document` / `window`.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(REPO_ROOT, "server", "template", "perfect_homework.html")


def _node_available() -> bool:
    return shutil.which("node") is not None


def _slice_function(src: str, fn_name: str) -> str:
    """
    Extract a `function NAME(...) { ... }` block from `src` by counting
    braces from the opening `{` of the function body. Robust to nested
    braces, regex literals, and string literals containing `}` characters
    inside this template.
    """
    pat = re.compile(r"function\s+" + re.escape(fn_name) + r"\s*\([^)]*\)\s*\{")
    m = pat.search(src)
    assert m, f"Function `{fn_name}` not found in template."
    start = m.start()
    body_start = m.end() - 1  # index of the opening `{`
    depth = 0
    in_str: str | None = None  # quote char if inside string literal
    escape = False
    in_line_comment = False
    in_block_comment = False
    in_regex = False
    i = body_start
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_str is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if in_regex:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "/":
                in_regex = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
        i += 1
    raise AssertionError(f"Unbalanced braces extracting `{fn_name}` from template.")


def _read_helpers() -> tuple[str, str]:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        src = f.read()
    extract = _slice_function(src, "extractStudentWork")
    sanitize = _slice_function(src, "sanitizeScreenContext")
    return extract, sanitize


# Minimal DOM polyfill — provides querySelector / querySelectorAll, a
# tiny Element class with .value / .textContent / .innerText / cloneNode
# / removeChild / removeAttribute / parentNode plumbing. Sufficient for
# the two helpers under test, not a general-purpose jsdom replacement.
_DOM_POLYFILL = r"""
'use strict';

class FakeElement {
    constructor(tag, attrs, children, value) {
        this.tagName = (tag || 'div').toUpperCase();
        this._attrs = Object.assign({}, attrs || {});
        this.children = (children || []).map((c) => {
            if (typeof c === 'string') {
                const t = new FakeElement('#text', {}, [], null);
                t._text = c;
                return t;
            }
            c.parentNode = this;
            return c;
        });
        this.children.forEach((c) => { c.parentNode = this; });
        this.value = value != null ? value : null;
        this.disabled = !!(attrs && attrs.disabled);
        this.parentNode = null;
        this._text = null;
    }
    get textContent() {
        if (this._text != null) return this._text;
        return this.children.map((c) => c.textContent || '').join(' ');
    }
    get innerText() { return this.textContent; }
    getAttribute(name) {
        return this._attrs[name] != null ? this._attrs[name] : null;
    }
    setAttribute(name, val) { this._attrs[name] = val; }
    removeAttribute(name) { delete this._attrs[name]; }
    hasAttribute(name) { return Object.prototype.hasOwnProperty.call(this._attrs, name); }
    cloneNode(deep) {
        const cloned = new FakeElement(this.tagName.toLowerCase(), this._attrs, [], this.value);
        cloned._text = this._text;
        cloned.disabled = this.disabled;
        if (deep) {
            cloned.children = this.children.map((c) => {
                const cc = c.cloneNode(true);
                cc.parentNode = cloned;
                return cc;
            });
        }
        return cloned;
    }
    removeChild(child) {
        const idx = this.children.indexOf(child);
        if (idx >= 0) {
            this.children.splice(idx, 1);
            child.parentNode = null;
        }
        return child;
    }
    appendChild(child) {
        child.parentNode = this;
        this.children.push(child);
        return child;
    }
    _flatten() {
        const out = [this];
        for (const c of this.children) {
            if (typeof c._flatten === 'function') out.push(...c._flatten());
        }
        return out;
    }
    _matches(selector) {
        // Tiny selector matcher: supports `#id`, `.class`,
        // `[attr]`, `[attr="val"]`, `tag`, `tag[attr^="val"]`,
        // `input[id^="prefix"]`. Combinations like `tag.class` are
        // supported via simple sequential checks.
        if (!selector) return false;
        // Handle commas
        if (selector.indexOf(',') >= 0) {
            return selector.split(',').some((s) => this._matches(s.trim()));
        }
        // Tokenize: tag part, then [attr...] / .class / #id repeating.
        let s = selector.trim();
        // Tag
        const tagMatch = s.match(/^([a-zA-Z][a-zA-Z0-9_-]*)/);
        if (tagMatch) {
            if (this.tagName.toLowerCase() !== tagMatch[1].toLowerCase()) return false;
            s = s.slice(tagMatch[0].length);
        }
        while (s.length) {
            if (s[0] === '#') {
                const idMatch = s.match(/^#([A-Za-z0-9_:.-]+)/);
                if (!idMatch) return false;
                if (this.getAttribute('id') !== idMatch[1]) return false;
                s = s.slice(idMatch[0].length);
            } else if (s[0] === '.') {
                const clsMatch = s.match(/^\.([A-Za-z0-9_-]+)/);
                if (!clsMatch) return false;
                const cls = (this.getAttribute('class') || '').split(/\s+/);
                if (cls.indexOf(clsMatch[1]) < 0) return false;
                s = s.slice(clsMatch[0].length);
            } else if (s[0] === '[') {
                const attrMatch = s.match(/^\[([A-Za-z0-9_-]+)(?:([\^\$\*]?=)(?:"([^"]*)"|'([^']*)'|([^\]]*)))?\]/);
                if (!attrMatch) return false;
                const name = attrMatch[1];
                const op = attrMatch[2];
                const val = attrMatch[3] != null ? attrMatch[3] : (attrMatch[4] != null ? attrMatch[4] : attrMatch[5]);
                if (op == null) {
                    if (!this.hasAttribute(name)) return false;
                } else {
                    const got = this.getAttribute(name);
                    if (got == null) return false;
                    if (op === '=') { if (got !== val) return false; }
                    else if (op === '^=') { if (!String(got).startsWith(val)) return false; }
                    else if (op === '$=') { if (!String(got).endsWith(val)) return false; }
                    else if (op === '*=') { if (String(got).indexOf(val) < 0) return false; }
                }
                s = s.slice(attrMatch[0].length);
            } else {
                return false;
            }
        }
        return true;
    }
    querySelector(sel) {
        for (const node of this._flatten()) {
            if (node === this) continue;
            if (node._matches(sel)) return node;
        }
        return null;
    }
    querySelectorAll(sel) {
        const out = [];
        for (const node of this._flatten()) {
            if (node === this) continue;
            if (node._matches(sel)) out.push(node);
        }
        return out;
    }
}

const __ROOT__ = new FakeElement('body', {}, [], null);

const document = {
    body: __ROOT__,
    querySelector(sel) { return __ROOT__.querySelector(sel); },
    querySelectorAll(sel) { return __ROOT__.querySelectorAll(sel); },
};

globalThis.document = document;
globalThis.FakeElement = FakeElement;
globalThis.__ROOT__ = __ROOT__;

// Dummies for any unrelated globals the helpers might reference.
globalThis.window = globalThis;
"""


def _run_node(test_body: str, helpers_js: str, fixture_setup_js: str = "") -> dict:
    """
    Run the helpers + a small test body under Node and return the parsed
    JSON the body printed on stdout. Any thrown error or non-JSON stdout
    fails the test.
    """
    full = (
        _DOM_POLYFILL
        + "\n// ── helpers under test ──\n"
        + helpers_js
        + "\n// ── fixture setup ──\n"
        + fixture_setup_js
        + "\n// ── test body ──\n"
        + test_body
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(full)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            ["node", tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
    finally:
        os.unlink(tmp_path)

    assert proc.returncode == 0, (
        f"Node exited {proc.returncode}.\nstderr:\n{proc.stderr[:2000]}\n"
        f"stdout:\n{proc.stdout[:1000]}"
    )
    out = proc.stdout.strip()
    # Find the last line that parses as JSON (helpers may print debug).
    for line in reversed(out.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except Exception:
            continue
    raise AssertionError(
        f"Node test body printed no JSON line.\nstdout: {out!r}\nstderr: {proc.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_helpers_are_findable_in_template():
    """Both helpers must be present in the template and brace-balanced."""
    extract, sanitize = _read_helpers()
    assert "function extractStudentWork" in extract
    assert "function sanitizeScreenContext" in sanitize
    # Sanity: each ends with a `}` and the slice closes at depth 0.
    assert extract.rstrip().endswith("}")
    assert sanitize.rstrip().endswith("}")


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_extract_real_life_reads_indexed_input():
    """real-life: with stage6State.qIndex=1 (0-indexed → q2), reads `#rl-q2-input` value."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    var stage6State = { qIndex: 1 };  // 0-indexed → DOM id `rl-q2-input`
    __ROOT__.appendChild(new FakeElement(
        'input', { id: 'rl-q2-input' }, [], 'my answer'
    ));
    """
    body = r"""
    const v = extractStudentWork('real-life');
    console.log(JSON.stringify({ value: v }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    assert result["value"] == "my answer"


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_extract_adaptive_quiz_reads_input_value():
    """adaptive-quiz: reads `#gb-aq-textarea` (the AQ multi-line answer input the runtime defines)."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    var gbState = { aq: {} };  // present but no 'lastSelectedLabel' (textarea input)
    __ROOT__.appendChild(new FakeElement(
        'textarea', { id: 'gb-aq-textarea' }, [], 'Option B'
    ));
    """
    body = r"""
    const v = extractStudentWork('adaptive-quiz');
    console.log(JSON.stringify({ value: v }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    assert result["value"] == "Option B"


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_extract_mystery_box_falls_back_to_pickedLabel():
    """mystery-box: when `#gb-mb-solve-input` is empty, fall back to `gbState.mb.pickedLabel`."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    var gbState = { mb: { pickedLabel: 'Box-Alpha' } };
    // No #gb-mb-solve-input element at all → fall through to pickedLabel.
    """
    body = r"""
    const v = extractStudentWork('mystery-box');
    console.log(JSON.stringify({ value: v }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    assert result["value"] == "Box-Alpha"


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_extract_tile_match_reads_selected_left_tile():
    """tile-match: surfaces the currently-selected left tile's text (runtime uses `selectedLeft`, not `pendingPair`)."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    const tileEl = new FakeElement('div', {}, ['cat'], null);
    var gbState = {
        mm: {
            selectedLeft: { pairId: 0, el: tileEl },
        },
    };
    """
    body = r"""
    const v = extractStudentWork('tile-match');
    console.log(JSON.stringify({ value: v }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    # We surface as `selected: <text>` since pendingPair doesn't exist here.
    assert result["value"] is not None
    assert "cat" in result["value"]


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_extract_unknown_subphase_returns_null():
    """An unknown subphase name returns null (no selectors registered)."""
    extract, sanitize = _read_helpers()
    body = r"""
    const v = extractStudentWork('nonexistent-phase-xyz');
    console.log(JSON.stringify({ value: v }));
    """
    result = _run_node(body, extract + "\n" + sanitize, "")
    assert result["value"] is None


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_sanitize_strips_answer_key_nodes():
    """sanitizeScreenContext drops [data-correct=true] children but keeps the rest of the prompt text."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    const root = new FakeElement('div', {}, [
        new FakeElement('p', {}, ['Question text'], null),
        new FakeElement('span', { 'data-correct': 'true' }, ['42'], null),
    ], null);
    """
    body = r"""
    const out = sanitizeScreenContext(root);
    console.log(JSON.stringify({ out: out }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    out = result["out"]
    assert "Question text" in out
    assert "42" not in out, f"Answer key leaked through: {out!r}"


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_sanitize_strips_class_correct_and_answer_key_classes():
    """sanitizeScreenContext drops `.correct`, `.answer-key`, `.is-correct`, and `.gb-aq-answer` nodes."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    const root = new FakeElement('div', {}, [
        new FakeElement('p', {}, ['Visible prompt'], null),
        new FakeElement('div', { 'class': 'correct' }, ['SECRET-ANSWER'], null),
        new FakeElement('div', { 'class': 'is-correct' }, ['IS-CORRECT-LEAK'], null),
        new FakeElement('div', { 'class': 'answer-key' }, ['ANSWER-KEY-LEAK'], null),
        new FakeElement('div', { 'class': 'gb-aq-answer' }, ['AQ-ANSWER-LEAK'], null),
    ], null);
    """
    body = r"""
    const out = sanitizeScreenContext(root);
    console.log(JSON.stringify({ out: out }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    out = result["out"]
    assert "Visible prompt" in out
    assert "SECRET-ANSWER" not in out
    assert "IS-CORRECT-LEAK" not in out
    assert "ANSWER-KEY-LEAK" not in out
    assert "AQ-ANSWER-LEAK" not in out


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_sanitize_strips_data_expected_and_data_answer_nodes():
    """sanitizeScreenContext removes any node carrying data-expected or data-answer (treated as answer-key markers)."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    const root = new FakeElement('div', {}, [
        new FakeElement('p', {}, ['Plain prompt text'], null),
        new FakeElement('span', { 'data-expected': '99' }, ['LEAKED-EXPECTED'], null),
        new FakeElement('span', { 'data-answer': 'X' }, ['LEAKED-ANSWER'], null),
    ], null);
    """
    body = r"""
    const out = sanitizeScreenContext(root);
    console.log(JSON.stringify({ out: out }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    out = result["out"]
    assert "Plain prompt text" in out
    assert "LEAKED-EXPECTED" not in out
    assert "LEAKED-ANSWER" not in out


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_sanitize_null_root_returns_empty_string():
    """sanitizeScreenContext(null) returns '' (defensive — no active screen)."""
    extract, sanitize = _read_helpers()
    body = r"""
    const out = sanitizeScreenContext(null);
    console.log(JSON.stringify({ out: out }));
    """
    result = _run_node(body, extract + "\n" + sanitize, "")
    assert result["out"] == ""


@pytest.mark.skipif(not _node_available(), reason="node binary not on PATH")
def test_extract_caps_at_2000_chars():
    """A very long input value is sliced to 2000 chars."""
    extract, sanitize = _read_helpers()
    fixture = r"""
    var stage6State = { qIndex: 0 };
    const long = 'x'.repeat(5000);
    __ROOT__.appendChild(new FakeElement(
        'input', { id: 'rl-q1-input' }, [], long
    ));
    """
    body = r"""
    const v = extractStudentWork('real-life');
    console.log(JSON.stringify({ length: v ? v.length : -1 }));
    """
    result = _run_node(body, extract + "\n" + sanitize, fixture)
    assert result["length"] == 2000
