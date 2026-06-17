"""
Wave J / T4 — frontend tutor widget warning-UI tests.

These tests exercise the floating tutor widget's response to the
warning-state-machine fields the backend started shipping in T2:

    warning_level                — 0..9
    cumulative_deduction_pct     — 0/5/15
    is_big_warning               — true ONLY on the level-8 trigger
    homework_failed              — true when level >= 9
    deduction_pct_this           — 0/5/10 on this specific event

Pattern (mirrors `test_runtime_labels_eval.py`): we render the page,
extract the tutor IIFE's inline <script> block, and run it in Node
with a rich DOM/localStorage polyfill. The polyfill captures DOM
mutations so we can read the resulting state (chip visibility/tier,
banner state, overlay state, custom-event dispatches).

The widget IIFE wires its own `nets:phase-change` listener (plus a
top-level window listener for `nets:homework-failed` is added by
the runtime script outside the IIFE). We rebuild a minimal version
of those listeners in the test harness and verify the chain end-to-end.

Why this style instead of pytest-playwright/JSDOM-via-pip:
 * No new pip / npm dependencies — node is already required for
   tests/test_runtime_labels_eval.py.
 * Windows 32 KB cmdline limit: we write the JS to a tmpfile (per
   the project's test memory).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
_JS_PATH = REPO_ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = REPO_ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = REPO_ROOT / "server" / "template" / "perfect_homework.html"
_TUTOR_JS_PATH = REPO_ROOT / "server" / "template" / "static" / "js" / "tutor.js"
TEMPLATE = (_HTML_PATH.read_text(encoding="utf-8") + "\n" +
            _JS_PATH.read_text(encoding="utf-8") + "\n" +
            _CSS_PATH.read_text(encoding="utf-8") + "\n" +
            _TUTOR_JS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_available() -> bool:
    return shutil.which("node") is not None


pytestmark = pytest.mark.skipif(
    not _node_available(),
    reason="node binary not on PATH",
)


def _read_template() -> str:
    return TEMPLATE


def _extract_tutor_iife(html: str) -> str:
    """Grab the floating-tutor inline <script> block.

    The block opens with the comment marker
    `// Wave F2 — persistent floating tutor widget.`
    inside an IIFE just before `</body>`.
    """
    # Match the Wave F2 IIFE — either inline in HTML (<script> wrapper)
    # or bare in tutor.js (no wrapper, with leading indent).
    pattern = re.compile(
        r"(?:<script>\s*\n\s*)?"
        r"\(function\s*\(\)\s*\{\s*\n"
        r"\s*//\s*Wave F2 — persistent floating tutor widget"
        r"[\s\S]*?"
        r"\}\)\(\);\s*\n"
        r"(?:\s*</script>)?",
        re.MULTILINE,
    )
    m = pattern.search(html)
    assert m, "Could not locate the Wave F2 tutor IIFE in the template"
    block = m.group(0)
    # Strip optional <script>...</script> wrapper.
    inner = re.sub(r"^<script>\s*", "", block)
    inner = re.sub(r"\s*</script>\s*$", "", inner)
    return inner


# ---------------------------------------------------------------------------
# DOM / browser polyfill + element scaffold
#
# We construct a minimal in-memory DOM that supports the IIFE's needs:
#   getElementById, querySelectorAll, createElement, addEventListener,
#   dispatchEvent (CustomEvent), classList, dataset, textContent, hidden,
#   localStorage, console, setTimeout (synchronous-ish for tests).
#
# Each "element" tracks attributes + a children array. The tests inspect
# these after exercising the widget.
# ---------------------------------------------------------------------------

_HARNESS_PRELUDE = r"""
'use strict';

// Minimal DOM node implementation -----------------------------------------
function _mkClassList() {
    const set = new Set();
    return {
        add(c) { set.add(c); },
        remove(c) { set.delete(c); },
        toggle(c) { if (set.has(c)) set.delete(c); else set.add(c); },
        contains(c) { return set.has(c); },
        toString() { return Array.from(set).join(' '); },
    };
}

function _mkEl(tag) {
    const attrs = {};
    const dataset = {};
    const node = {
        tagName: String(tag || 'div').toUpperCase(),
        children: [],
        parentNode: null,
        _hidden: false,
        _text: '',
        _eventListeners: {},
        classList: _mkClassList(),
        style: {},
        dataset: dataset,
        get className() { return this.classList.toString(); },
        set className(v) {
            this.classList = _mkClassList();
            String(v || '').split(/\s+/).forEach(c => { if (c) this.classList.add(c); });
        },
        get hidden() { return this._hidden; },
        set hidden(v) { this._hidden = !!v; },
        get textContent() {
            // Concatenate child textContent where applicable.
            if (this._text) return this._text;
            return this.children.map(c => c && (c.textContent || '')).join('');
        },
        set textContent(v) {
            this._text = String(v == null ? '' : v);
            this.children = [];
        },
        get firstChild() { return this.children[0] || null; },
        appendChild(child) {
            if (!child) return child;
            child.parentNode = this;
            this.children.push(child);
            // Once we append a child, drop the literal text override so
            // textContent re-derives from children.
            if (this.children.length === 1) this._text = '';
            return child;
        },
        removeChild(child) {
            const i = this.children.indexOf(child);
            if (i >= 0) {
                this.children.splice(i, 1);
                child.parentNode = null;
            }
            return child;
        },
        contains(child) {
            if (this === child) return true;
            for (const c of this.children) {
                if (c === child) return true;
                if (c && typeof c.contains === 'function' && c.contains(child)) return true;
            }
            return false;
        },
        setAttribute(k, v) { attrs[k] = String(v); if (k === 'hidden') this._hidden = true; },
        getAttribute(k) { return attrs[k] != null ? attrs[k] : null; },
        hasAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k); },
        removeAttribute(k) { delete attrs[k]; if (k === 'hidden') this._hidden = false; },
        addEventListener(type, fn) {
            (this._eventListeners[type] = this._eventListeners[type] || []).push(fn);
        },
        removeEventListener(type, fn) {
            const arr = this._eventListeners[type] || [];
            const i = arr.indexOf(fn);
            if (i >= 0) arr.splice(i, 1);
        },
        dispatchEvent(ev) {
            const arr = this._eventListeners[ev.type] || [];
            for (const f of arr) {
                try { f(ev); } catch (_) {}
            }
            return true;
        },
        querySelector(sel) { return _querySelector(this, sel); },
        querySelectorAll(sel) { return _querySelectorAll(this, sel); },
        focus() {},
        // For form elements:
        get title() { return attrs.title != null ? attrs.title : ''; },
        set title(v) { attrs.title = String(v); },
        // tagName-conditional placeholders:
        get value() { return attrs.value || ''; },
        set value(v) { attrs.value = String(v); },
        get placeholder() { return attrs.placeholder || ''; },
        set placeholder(v) { attrs.placeholder = String(v); },
        get id() { return attrs.id || ''; },
        set id(v) { attrs.id = String(v); },
        get disabled() { return !!attrs.disabled; },
        set disabled(v) { attrs.disabled = !!v; },
        get scrollHeight() { return 0; },
        get scrollTop() { return 0; },
        set scrollTop(v) {},
        get offsetHeight() { return 1; },
        set innerHTML(v) { /* swallow — we don't care for these tests */ },
    };
    return node;
}

// Trivial selector matcher: supports `#id`, `.cls`, `tag`, and `tag.cls`
// + `tag.cls.cls2` for the few selectors the IIFE uses.
function _matches(el, sel) {
    if (!el || !sel) return false;
    const parts = sel.trim().split(/\s+/);
    // Multi-part selectors not supported beyond last-segment match.
    const last = parts[parts.length - 1];
    if (last.startsWith('#')) {
        return el.id === last.slice(1);
    }
    if (last.startsWith('.')) {
        const classes = last.split('.').filter(Boolean);
        return classes.every(c => el.classList && el.classList.contains(c));
    }
    // tag or tag.cls
    const m = /^([a-z][a-z0-9-]*)?(?:\.(.+))?$/i.exec(last);
    if (!m) return false;
    const tag = m[1];
    const cls = m[2];
    if (tag && el.tagName !== tag.toUpperCase()) return false;
    if (cls) {
        const classes = cls.split('.').filter(Boolean);
        if (!classes.every(c => el.classList && el.classList.contains(c))) return false;
    }
    return true;
}

function _walkAll(root, out) {
    if (!root || !root.children) return;
    for (const c of root.children) {
        out.push(c);
        _walkAll(c, out);
    }
}

function _querySelector(root, sel) {
    const all = [];
    _walkAll(root, all);
    for (const el of all) if (_matches(el, sel)) return el;
    return null;
}
function _querySelectorAll(root, sel) {
    const all = [];
    _walkAll(root, all);
    return all.filter(el => _matches(el, sel));
}

// CustomEvent shim ---------------------------------------------------------
function CustomEvent(type, init) {
    return { type: String(type), detail: (init && init.detail) || null };
}

// Document --------------------------------------------------------------
const _docElements = {};   // id -> element
const _doc = _mkEl('html');
_doc.documentElement = _mkEl('html');
_doc.documentElement.lang = 'uz';
_doc.documentElement.setAttribute = function (k, v) { this.lang = (k === 'lang') ? v : this.lang; };
_doc.documentElement.getAttribute = function (k) { return k === 'lang' ? this.lang : null; };

const document = {
    documentElement: _doc.documentElement,
    body: _mkEl('body'),
    head: _mkEl('head'),
    _eventListeners: {},
    addEventListener(type, fn) {
        (this._eventListeners[type] = this._eventListeners[type] || []).push(fn);
    },
    removeEventListener(type, fn) {
        const arr = this._eventListeners[type] || [];
        const i = arr.indexOf(fn);
        if (i >= 0) arr.splice(i, 1);
    },
    dispatchEvent(ev) {
        const arr = this._eventListeners[ev.type] || [];
        for (const f of arr) {
            try { f(ev); } catch (_) {}
        }
        return true;
    },
    createElement(tag) { return _mkEl(tag); },
    createTextNode(t) {
        const n = _mkEl('#text');
        n.textContent = String(t == null ? '' : t);
        return n;
    },
    getElementById(id) { return _docElements[id] || null; },
    querySelector(sel) {
        // Special-cased — only used for `.screen.active` in this IIFE.
        if (sel === '.screen.active') return null;
        return null;
    },
    querySelectorAll() { return []; },
};

// Register the elements the IIFE expects. Each must be returned by
// document.getElementById exactly as it would in the live page. We keep
// them flat — children/structure don't matter for these state-driven
// assertions, only the element identity + attribute mutations.
const _IDS = [
    'nets-ai-tutor', 'nets-tutor-fab', 'nets-tutor-panel',
    'nets-tutor-phase-badge', 'nets-tutor-close', 'nets-tutor-avatar',
    'nets-tutor-messages', 'nets-tutor-input-form', 'nets-tutor-input',
    'nets-tutor-send', 'nets-tutor-cap-warning',
    'nets-tutor-warning-chip', 'nets-tutor-big-warning',
    'nets-tutor-fail-overlay', 'nets-tutor-cta',
];
for (const id of _IDS) {
    const el = _mkEl('div');
    el.id = id;
    _docElements[id] = el;
}

// Build chip + count child to mirror the markup.
const _chipCount = _mkEl('span');
_chipCount.className = 'nets-tutor-warning-count';
_chipCount.textContent = '0';
_docElements['nets-tutor-warning-chip'].appendChild(_chipCount);
const _chipIcon = _mkEl('span');
_chipIcon.className = 'nets-tutor-warning-icon';
_docElements['nets-tutor-warning-chip'].appendChild(_chipIcon);
_docElements['nets-tutor-warning-chip']._hidden = true;

// Big-warning text + dismiss children.
const _bwTxt = _mkEl('span');
_bwTxt.className = 'nets-tutor-big-warning-text';
_docElements['nets-tutor-big-warning'].appendChild(_bwTxt);
const _bwDismiss = _mkEl('button');
_bwDismiss.className = 'nets-tutor-big-warning-dismiss';
_docElements['nets-tutor-big-warning'].appendChild(_bwDismiss);
_docElements['nets-tutor-big-warning']._hidden = true;

// Fail-overlay children.
const _failTitle = _mkEl('div');
_failTitle.className = 'nets-tutor-fail-title';
_docElements['nets-tutor-fail-overlay'].appendChild(_failTitle);
const _failSub = _mkEl('div');
_failSub.className = 'nets-tutor-fail-subtitle';
_docElements['nets-tutor-fail-overlay'].appendChild(_failSub);
_docElements['nets-tutor-fail-overlay']._hidden = true;

// CTA label child.
const _ctaLabel = _mkEl('span');
_ctaLabel.className = 'nets-tutor-cta-label';
_docElements['nets-tutor-cta'].appendChild(_ctaLabel);
_docElements['nets-tutor-cta']._hidden = true;

// localStorage / globals ---------------------------------------------------
const _ls = {};
const localStorage = {
    getItem(k) { return Object.prototype.hasOwnProperty.call(_ls, k) ? _ls[k] : null; },
    setItem(k, v) { _ls[k] = String(v); },
    removeItem(k) { delete _ls[k]; },
};

const window = {
    NETS_CTX: { lang: 'uz', hwId: 'hw-test', apiBase: '', features: {} },
    NETS_AI: null,  // set per-test
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent(ev) {
        // Forward to a global recorder — the test inspects this.
        _windowEvents.push(ev);
        return true;
    },
    crypto: { randomUUID() { return '00000000-0000-4000-8000-000000000000'; } },
    bossState: {},
};
const _windowEvents = [];

const console = { log() {}, warn() {}, error() {}, info() {}, debug() {} };

// Synchronous setTimeout — fire immediately so tests can assert dispatch
// without async waits. The IIFE relies on setTimeout for the focus + the
// fail-overlay-to-event delay; we don't need real timing here.
const _timers = [];
function setTimeout(fn, ms) {
    _timers.push({ fn: fn, ms: ms });
    return _timers.length - 1;
}
function clearTimeout(handle) {
    if (_timers[handle]) _timers[handle] = null;
}

// Globals the IIFE references implicitly (via closure or naked refs).
globalThis.window = window;
globalThis.document = document;
globalThis.localStorage = localStorage;
globalThis.console = console;
globalThis.setTimeout = setTimeout;
globalThis.clearTimeout = clearTimeout;
globalThis.CustomEvent = CustomEvent;
globalThis.NETS_CTX = window.NETS_CTX;

// Drain pending timers helper (callable from the test JS).
function _drainTimers(maxRounds) {
    let rounds = 0;
    while (rounds++ < (maxRounds || 4)) {
        const pending = _timers.filter(t => t);
        if (!pending.length) break;
        for (let i = 0; i < _timers.length; i++) {
            const t = _timers[i];
            if (!t) continue;
            _timers[i] = null;
            try { t.fn(); } catch (_) {}
        }
    }
}

// Stub `RL_SCENARIO` + `stage6State` (referenced by the CTA wiring) so
// the IIFE doesn't ReferenceError when those inits run.
globalThis.RL_SCENARIO = null;
globalThis.stage6State = null;
"""


_HARNESS_HARNESS = r"""

// ── Mock NETS_AI.tutorChat ────────────────────────────────────────
// Each test substitutes a function via __setTutorMockResponse(...).
// The mock returns synchronously-resolved Promises so the await chain
// can run within drainTimers().
let _nextResponse = { response: 'ok', message_id: 1 };
function __setTutorMockResponse(r) { _nextResponse = r; }

window.NETS_AI = {
    tutorChat(opts) {
        window.__lastChatOpts = opts;
        return Promise.resolve(_nextResponse);
    },
    tutorHistory() { return Promise.resolve({ turns: [] }); },
    isAvailable() { return true; },
};

// ── Drive a chat turn ────────────────────────────────────────────
async function __sendMessage(text) {
    const input = document.getElementById('nets-tutor-input');
    const form  = document.getElementById('nets-tutor-input-form');
    input.value = String(text);
    // Submit event with preventDefault.
    const ev = { type: 'submit', preventDefault() {}, cancelable: true };
    const arr = form._eventListeners['submit'] || [];
    for (const fn of arr) {
        await fn(ev);
    }
    // Drain microtasks so the await inside sendMessage resolves.
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
    _drainTimers();
}

// ── Snapshot helper for the test to JSON.stringify ───────────────
function __snapshot() {
    const chip   = document.getElementById('nets-tutor-warning-chip');
    const banner = document.getElementById('nets-tutor-big-warning');
    const overlay = document.getElementById('nets-tutor-fail-overlay');
    const input  = document.getElementById('nets-tutor-input');
    const send   = document.getElementById('nets-tutor-send');
    const chipCount = chip.querySelector('.nets-tutor-warning-count');
    const bwText = banner.querySelector('.nets-tutor-big-warning-text');
    const failTitle = overlay.querySelector('.nets-tutor-fail-title');
    return {
        chip: {
            hidden: chip.hidden,
            count: chipCount ? chipCount.textContent : null,
            tier: chip.dataset.tier || null,
            title: chip.title || null,
        },
        banner: {
            hidden: banner.hidden,
            text: bwText ? bwText.textContent : null,
        },
        overlay: {
            hidden: overlay.hidden,
            title: failTitle ? failTitle.textContent : null,
        },
        input: {
            disabled: input.disabled,
        },
        send: {
            disabled: send.disabled,
        },
        windowEvents: _windowEvents.map(e => ({ type: e.type, detail: e.detail })),
    };
}
"""


def _build_test_js(test_body: str, lang: str = "uz") -> str:
    iife = _extract_tutor_iife(_read_template())
    # The IIFE inits the badge with phase 'preview' which calls
    # input.placeholder = ... etc. Our polyfill supports that.
    return (
        _HARNESS_PRELUDE
        + f"\n_doc.documentElement.lang = '{lang}';\nNETS_CTX.lang = '{lang}';\nwindow.NETS_CTX.lang = '{lang}';\n"
        + iife
        + _HARNESS_HARNESS
        + "\n\n"
        + test_body
    )


def _run_node(js: str) -> dict:
    """Execute the given JS via node and return parsed JSON output."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(js)
        path = tmp.name
    try:
        proc = subprocess.run(
            ["node", path],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
        )
    finally:
        os.unlink(path)
    assert proc.returncode == 0, (
        f"node exited with {proc.returncode}\n"
        f"STDERR:\n{proc.stderr[:1500]}\n\n"
        f"STDOUT:\n{proc.stdout[:600]}"
    )
    out = (proc.stdout or "").strip()
    # Find the last JSON line — the IIFE's setTimeout/console may emit
    # earlier lines; we standardize on '__RESULT__:<json>' as the marker.
    marker = "__RESULT__:"
    for line in reversed(out.splitlines()):
        if line.startswith(marker):
            return json.loads(line[len(marker):])
    raise AssertionError(
        f"No __RESULT__ marker in node stdout. Got:\n{out[:1000]}\n"
        f"STDERR:\n{proc.stderr[:1000]}"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_warning_chip_yellow_at_level_4():
    """warning_level: 4, cumulative_deduction_pct: 0 → chip visible, 4/9, yellow."""
    body = r"""
    (async function () {
        __setTutorMockResponse({
            response: 'Easy.',
            message_id: 7,
            warning_level: 4,
            cumulative_deduction_pct: 0,
            is_big_warning: false,
            homework_failed: false,
            deduction_pct_this: 0,
        });
        await __sendMessage('hello');
        process.stdout.write('__RESULT__:' + JSON.stringify(__snapshot()) + '\n');
    })();
    """
    result = _run_node(_build_test_js(body))
    assert result["chip"]["hidden"] is False, "chip must be visible at level 4"
    assert result["chip"]["count"] == "4", f"expected count 4, got {result['chip']['count']}"
    # Tier yellow is the default — IIFE only sets dataset.tier explicitly to
    # 'yellow' for level 1..6 (per the spec); confirm:
    assert result["chip"]["tier"] == "yellow", f"expected yellow, got {result['chip']['tier']}"
    # Banner & overlay must be hidden.
    assert result["banner"]["hidden"] is True
    assert result["overlay"]["hidden"] is True
    # Input still enabled.
    assert result["input"]["disabled"] is False


def test_warning_chip_orange_at_level_7():
    """warning_level: 7, cumulative_deduction_pct: 5 → chip 7/9, orange."""
    body = r"""
    (async function () {
        __setTutorMockResponse({
            response: 'Mind the language.',
            message_id: 8,
            warning_level: 7,
            cumulative_deduction_pct: 5,
            is_big_warning: false,
            homework_failed: false,
            deduction_pct_this: 5,
        });
        await __sendMessage('again');
        process.stdout.write('__RESULT__:' + JSON.stringify(__snapshot()) + '\n');
    })();
    """
    result = _run_node(_build_test_js(body))
    assert result["chip"]["hidden"] is False
    assert result["chip"]["count"] == "7"
    assert result["chip"]["tier"] == "orange", f"expected orange, got {result['chip']['tier']}"
    assert result["banner"]["hidden"] is True


def test_warning_chip_red_and_banner_at_level_8():
    """warning_level: 8, is_big_warning: true → chip 8/9 red, banner visible.

    NOTE: __sendMessage normally drains timers — but the banner has an
    8s auto-dismiss that would immediately hide it during drain. So we
    snapshot BEFORE draining for this test.
    """
    body = r"""
    (async function () {
        __setTutorMockResponse({
            response: 'Last chance.',
            message_id: 9,
            warning_level: 8,
            cumulative_deduction_pct: 15,
            is_big_warning: true,
            homework_failed: false,
            deduction_pct_this: 10,
        });
        // Inline send — skip the timer drain so we observe the banner
        // before its 8s auto-dismiss fires.
        const input = document.getElementById('nets-tutor-input');
        const form  = document.getElementById('nets-tutor-input-form');
        input.value = 'once more';
        const ev = { type: 'submit', preventDefault() {}, cancelable: true };
        for (const fn of (form._eventListeners['submit'] || [])) {
            await fn(ev);
        }
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
        process.stdout.write('__RESULT__:' + JSON.stringify(__snapshot()) + '\n');
    })();
    """
    result = _run_node(_build_test_js(body))
    assert result["chip"]["hidden"] is False
    assert result["chip"]["count"] == "8"
    assert result["chip"]["tier"] == "red", f"expected red, got {result['chip']['tier']}"
    # Banner should be visible.
    assert result["banner"]["hidden"] is False, "big-warning banner must show on is_big_warning"
    # Banner text must include the −15% string for uz.
    assert "15%" in (result["banner"]["text"] or ""), (
        f"banner text missing penalty: {result['banner']['text']}"
    )


def test_homework_failed_locks_input_and_dispatches_event():
    """homework_failed: true → input locked, overlay visible, custom event fired."""
    body = r"""
    (async function () {
        __setTutorMockResponse({
            response: "Uy vazifasi tugadi. So'nggi bosqichga o'tamiz.",
            message_id: null,
            warning_level: 9,
            cumulative_deduction_pct: 15,
            homework_failed: true,
        });
        await __sendMessage('one more');
        // Fire the timers — showFailOverlay's setTimeout(2000) dispatches
        // both `nets:phase-change` and `nets:homework-failed`.
        _drainTimers();
        process.stdout.write('__RESULT__:' + JSON.stringify(__snapshot()) + '\n');
    })();
    """
    result = _run_node(_build_test_js(body))
    # Input + send must be locked.
    assert result["input"]["disabled"] is True, "input must be disabled on homework_failed"
    assert result["send"]["disabled"] is True, "send must be disabled on homework_failed"
    # Overlay must be visible.
    assert result["overlay"]["hidden"] is False, "fail overlay must be visible"
    # Window event must include `nets:homework-failed`.
    types = [e["type"] for e in result["windowEvents"]]
    assert "nets:homework-failed" in types, (
        f"expected nets:homework-failed dispatched on window. Got: {types}"
    )
    # Confirm detail.deduction_pct is forwarded.
    failed = [e for e in result["windowEvents"] if e["type"] == "nets:homework-failed"][0]
    assert failed["detail"]["deduction_pct"] == 15, (
        f"deduction_pct not forwarded: {failed['detail']}"
    )


def test_recent_assistant_phrases_forwarded_in_request():
    """sendMessage must include recent_assistant_phrases (first 3 words of last
    3 assistant turns) in the chat request body."""
    body = r"""
    (async function () {
        // Pre-seed two assistant messages into the DOM so the next
        // sendMessage() picks them up. Uses the public DOM API.
        const messages = document.getElementById('nets-tutor-messages');
        function _addAssistant(text) {
            const el = document.createElement('div');
            el.className = 'nets-tutor-msg assistant';
            el.textContent = text;
            messages.appendChild(el);
        }
        _addAssistant('Salom uka, tushuntirib beraman buni');
        _addAssistant('Yaxshi, davom etamiz boshqa savolga');

        __setTutorMockResponse({
            response: 'OK',
            message_id: 1,
            warning_level: 0,
            cumulative_deduction_pct: 0,
            homework_failed: false,
        });
        await __sendMessage('next q');

        const opts = window.__lastChatOpts || {};
        process.stdout.write('__RESULT__:' + JSON.stringify({
            phrases: opts.recent_assistant_phrases || null,
            message: opts.message || null,
        }) + '\n');
    })();
    """
    result = _run_node(_build_test_js(body))
    phrases = result["phrases"]
    assert phrases is not None, "recent_assistant_phrases must be forwarded"
    assert len(phrases) == 2, f"expected 2 phrases, got: {phrases}"
    # Each phrase = first 3 words.
    assert phrases[0] == "Salom uka, tushuntirib", f"unexpected first phrase: {phrases[0]}"
    assert phrases[1] == "Yaxshi, davom etamiz", f"unexpected second phrase: {phrases[1]}"


def test_chip_hidden_at_level_zero():
    """warning_level: 0 → chip stays hidden."""
    body = r"""
    (async function () {
        __setTutorMockResponse({
            response: 'Sure.',
            message_id: 1,
            warning_level: 0,
            cumulative_deduction_pct: 0,
            homework_failed: false,
        });
        await __sendMessage('clean question');
        process.stdout.write('__RESULT__:' + JSON.stringify(__snapshot()) + '\n');
    })();
    """
    result = _run_node(_build_test_js(body))
    assert result["chip"]["hidden"] is True, "chip must stay hidden at level 0"


# ---------------------------------------------------------------------------
# Static-markup guards (cheap, fast, complement the JS-eval tests)
# ---------------------------------------------------------------------------

def test_template_contains_warning_chip_markup():
    html = _read_template()
    assert 'id="nets-tutor-warning-chip"' in html
    assert 'class="nets-tutor-warning-chip"' in html


def test_template_contains_big_warning_markup():
    html = _read_template()
    assert 'id="nets-tutor-big-warning"' in html
    assert 'class="nets-tutor-big-warning"' in html


def test_template_contains_fail_overlay_markup():
    html = _read_template()
    assert 'id="nets-tutor-fail-overlay"' in html
    assert 'class="nets-tutor-fail-overlay"' in html


def test_runtime_js_forwards_recent_assistant_phrases():
    """server/template/runtime.js must accept + forward recent_assistant_phrases."""
    rt = (REPO_ROOT / "server" / "template" / "runtime.js").read_text(encoding="utf-8")
    assert "recent_assistant_phrases" in rt, (
        "runtime.js must forward recent_assistant_phrases to /tutor/chat"
    )


def test_template_wires_homework_failed_window_listener():
    """The template must listen for `nets:homework-failed` on window so the
    runtime can jump to the reflection screen + mark the session log."""
    html = _read_template()
    assert "addEventListener('nets:homework-failed'" in html, (
        "expected a window-level `nets:homework-failed` listener in the template"
    )
    # And the listener must reach into showReflectionScreen / showResultsScreen.
    assert "__homeworkFailed" in html
    assert "__warningDeductions" in html
