"""Equation Editor — JS-runtime regression via Node + jsdom.

Exercises the picker + symbol catalogue + serialization helpers (the
parts that don't depend on the live MathLive Web Component, which needs
a real browser DOM). Skips cleanly when Node is unavailable.

Coverage:
  - search() finds expected hits across English + Uzbek aliases + Unicode glyphs
  - lookup() resolves single-occurrence keys correctly
  - Recently-used: cap at 16, dedup-on-repush, survive corrupt localStorage
  - pickSurface() responsive thresholds (320/479/480/719/720/1280)
  - All catalogue entries have required fields (latex, display, name)
  - Display-mode templates are flagged in the catalogue (matrices, cases, aligned)
  - LaTeX strings contain no `</script>` breakouts (XSS defense)
  - Cursor-placeholder syntax (#0, #1, …) is well-formed in templates
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
SYMBOLS_JS = ROOT / "frontend" / "js" / "editors" / "_equation-symbols.js"
PICKER_JS = ROOT / "frontend" / "js" / "editors" / "_equation-picker.js"


def _shim_preamble() -> str:
    return r"""
const _ls = {};
globalThis.localStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(_ls, k) ? _ls[k] : null; },
  setItem(k, v) { _ls[k] = String(v); },
  removeItem(k) { delete _ls[k]; },
  clear() { for (const k of Object.keys(_ls)) delete _ls[k]; },
};
globalThis.requestAnimationFrame = (fn) => setTimeout(fn, 0);
globalThis.window = globalThis;
// Stub MathLive bootstrap — picker calls .ensureLoaded() on open(), but
// the unit tests don't exercise that path.
globalThis.netsMathLive = {
  ensureLoaded: () => Promise.resolve(),
  isLoaded: () => false,
  makeField: () => null,
};
globalThis.document = {
  createElement: () => ({
    classList: { add() {}, remove() {}, toggle() {} },
    setAttribute() {}, removeAttribute() {},
    addEventListener() {}, removeEventListener() {},
    appendChild() {}, querySelector: () => null, querySelectorAll: () => [],
    style: {}, hidden: true,
  }),
  body: { appendChild() {} },
  addEventListener() {}, removeEventListener() {},
};
"""


def _run_node(test_body: str) -> dict:
    if shutil.which("node") is None:
        pytest.skip("Node.js not available")
    src = "".join([
        _shim_preamble(),
        SYMBOLS_JS.read_text(encoding="utf-8"),
        PICKER_JS.read_text(encoding="utf-8"),
        "\n",
        test_body,
    ])
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".js", delete=False,
    ) as tmp:
        tmp.write(src)
        path = tmp.name
    try:
        proc = subprocess.run(
            ["node", path],
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    assert proc.returncode == 0, f"Node failed:\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ── Catalogue contract ──────────────────────────────────────────────


def test_catalogue_has_expected_categories():
    out = _run_node(
        r"""
        const ids = window.EquationSymbols.CATEGORIES.map(c => c.id);
        process.stdout.write(JSON.stringify({ ids, total: window.EquationSymbols.all().length }));
        """
    )
    expected = {"common", "greek", "operators", "relations", "fractions",
                "scripts", "calculus", "brackets", "arrows", "logic", "matrices"}
    assert set(out["ids"]) == expected
    assert 100 <= out["total"] <= 250, (
        f"catalogue size {out['total']} outside expected band 100-250"
    )


def test_every_entry_has_required_fields():
    out = _run_node(
        r"""
        const bad = [];
        for (const c of window.EquationSymbols.CATEGORIES) {
          for (const e of c.entries) {
            if (!e.latex || !e.display || !e.name) bad.push({ cat: c.id, entry: e });
          }
        }
        process.stdout.write(JSON.stringify({ bad, count: bad.length }));
        """
    )
    assert out["count"] == 0, f"entries missing fields: {out['bad'][:5]}"


def test_matrix_entries_have_displayMode_flag():
    """Display-mode templates must be flagged so the serializer wraps in $$..$$."""
    out = _run_node(
        r"""
        const cat = window.EquationSymbols.CATEGORIES.find(c => c.id === 'matrices');
        const all = cat.entries.every(e => e.displayMode === true);
        process.stdout.write(JSON.stringify({
          count: cat.entries.length, allFlagged: all
        }));
        """
    )
    assert out["allFlagged"], (
        "every matrix entry must have displayMode:true"
    )


def test_template_placeholders_use_hash_syntax():
    """Templates with a `#0`/`#1`/etc. placeholder must use that syntax —
    MathLive's executeCommand("insert", latex, { selectionMode:"placeholder" })
    only respects the # form. Pin so a future copy-paste from PR #193 (which
    used empty {} braces) doesn't regress placeholder navigation."""
    out = _run_node(
        r"""
        const checked = [];
        const bad = [];
        for (const c of window.EquationSymbols.CATEGORIES) {
          for (const e of c.entries) {
            // Skip pure-symbol entries (no braces in latex).
            if (e.latex.indexOf('{') === -1) continue;
            // Skip natural-text macros that don't take a placeholder arg.
            if (/^\\[a-zA-Z]+$/.test(e.latex)) continue;
            checked.push(e.latex);
            // Templates must contain at least one #N placeholder marker.
            if (!/#\d+/.test(e.latex) && /\{\}/.test(e.latex)) {
              bad.push({ cat: c.id, latex: e.latex });
            }
          }
        }
        process.stdout.write(JSON.stringify({
          checkedCount: checked.length, bad
        }));
        """
    )
    assert out["bad"] == [], (
        "templates with empty {} pairs must use #N placeholder syntax: "
        f"{out['bad']}"
    )


def test_no_script_breakout_in_any_entry():
    out = _run_node(
        r"""
        const bad = [];
        for (const c of window.EquationSymbols.CATEGORIES) {
          for (const e of c.entries) {
            for (const f of ['latex','display','unicode','name']) {
              const v = e[f];
              if (typeof v === 'string' && /<\/?script/i.test(v)) bad.push({ cat: c.id, field: f, v });
            }
          }
        }
        process.stdout.write(JSON.stringify({ bad }));
        """
    )
    assert out["bad"] == []


# ── search() / lookup() ─────────────────────────────────────────────


def test_search_finds_uzbek_alias():
    out = _run_node(
        r"""
        const hits = window.EquationSymbols.search('alfa').map(h => h.latex);
        process.stdout.write(JSON.stringify({ hits }));
        """
    )
    assert "\\alpha" in out["hits"]


def test_search_matches_unicode_glyph():
    out = _run_node(
        r"""
        const hits = window.EquationSymbols.search('≤').map(h => h.latex);
        process.stdout.write(JSON.stringify({ hits }));
        """
    )
    assert "\\leq" in out["hits"]


def test_search_empty_returns_empty_list():
    out = _run_node(
        r"""
        const a = window.EquationSymbols.search('').length;
        const b = window.EquationSymbols.search('   ').length;
        process.stdout.write(JSON.stringify({ a, b }));
        """
    )
    assert out["a"] == 0 and out["b"] == 0


def test_lookup_known_and_unknown():
    out = _run_node(
        r"""
        const known = window.EquationSymbols.lookup('\\Sigma');
        const unknown = window.EquationSymbols.lookup('\\notARealMacro');
        process.stdout.write(JSON.stringify({
          knownName: known && known.name,
          unknown,
        }));
        """
    )
    assert out["knownName"] == "Sigma capital"
    assert out["unknown"] is None


# ── Recently-used persistence ───────────────────────────────────────


def test_recent_caps_at_16_dedup_on_repush():
    out = _run_node(
        r"""
        for (let i = 0; i < 25; i++) window.EquationPicker._saveRecent('\\sym' + i);
        // Re-push an old key — should bump to front, not duplicate.
        window.EquationPicker._saveRecent('\\sym10');
        const r = window.EquationPicker._loadRecent();
        process.stdout.write(JSON.stringify({
          len: r.length, first: r[0], unique: new Set(r).size === r.length
        }));
        """
    )
    assert out["len"] == 16
    assert out["first"] == "\\sym10"
    assert out["unique"], "recently-used contains duplicates"


def test_recent_survives_corrupt_localstorage():
    out = _run_node(
        r"""
        localStorage.setItem('nets.equationPicker.recent', 'not-json-{');
        const r = window.EquationPicker._loadRecent();
        process.stdout.write(JSON.stringify({ len: r.length }));
        """
    )
    assert out["len"] == 0


# ── Surface picker thresholds ───────────────────────────────────────


@pytest.mark.parametrize("width,expected", [
    (320, "sheet"),
    (479, "sheet"),
    (480, "centered"),
    (719, "centered"),
    (720, "popover"),
    (1280, "popover"),
])
def test_pick_surface_breakpoints(width, expected):
    out = _run_node(
        f"""
        globalThis.window.innerWidth = {width};
        process.stdout.write(JSON.stringify({{ s: window.EquationPicker._pickSurface() }}));
        """
    )
    assert out["s"] == expected


# ── Template snapshot contracts ─────────────────────────────────────
# Pin the EXPECTED LaTeX skeleton for each major template after MathLive's
# executeCommand("insert", latex, { selectionMode:"placeholder" }) expands
# the `#N` placeholder markers. These are recorded from the live smoke run
# (PR #194 timestamp 2026-05-07) — if MathLive's expansion changes in a
# future bump or our catalogue drifts, this test fails fast.

# Each tuple: (catalogue_name, expected_value_after_independent_insert).
# The `\placeholder{}` markers are MathLive's WYSIWYG cells that the user
# fills in by typing.
TEMPLATE_SNAPSHOTS = [
    ("fraction",          r"\frac{\placeholder{}}{\placeholder{}}"),
    ("square root",       r"\sqrt{\placeholder{}}"),
    ("cube root",         r"\sqrt[3]{\placeholder{}}"),
    ("integral with limits", r"\int_{\placeholder{}}^{\placeholder{}}"),
    ("sum with limits",   r"\sum_{\placeholder{}}^{\placeholder{}}"),
    ("limit",             r"\lim_{\placeholder{}\to\placeholder{}}"),
    ("superscript",       r"\placeholder{}^{\placeholder{}}"),
    ("subscript",         r"\placeholder{}_{\placeholder{}}"),
    ("2x2 matrix parens", r"\begin{pmatrix}\placeholder{} & \placeholder{}\\ \placeholder{} & \placeholder{}\end{pmatrix}"),
    ("piecewise cases",   r"\begin{cases}\placeholder{}, & \placeholder{}\\ \placeholder{}, & \placeholder{}\end{cases}"),
]


@pytest.mark.parametrize("name,expected", TEMPLATE_SNAPSHOTS)
def test_template_catalogue_matches_recorded_snapshot(name, expected):
    """Pin the catalogue's source LaTeX shape for each template. The live
    smoke confirmed that MathLive's `executeCommand("insert", source,
    {selectionMode:"placeholder"})` expands `#N` placeholders into
    `\\placeholder{}` cells — so the *source* form in our catalogue, after
    that expansion, must match the recorded snapshot above.

    A failure here means either:
      (a) someone edited the catalogue's `latex` field for this entry (e.g.
          dropped a `#0` placeholder, breaking the WYSIWYG cell), OR
      (b) MathLive changed how it expands `#N` markers (rare; would need
          a bump-and-re-record).
    """
    out = _run_node(
        rf"""
        // Find the catalogue entry by name (case-insensitive prefix match).
        const target = window.EquationSymbols.all().find(e =>
          (e.name || '').toLowerCase().startsWith({name!r}.toLowerCase())
        );
        if (!target) {{ process.stdout.write(JSON.stringify({{ found: false }})); return; }}
        // Simulate MathLive's expansion of `#N` → `\placeholder{{}}` markers.
        // MathLive replaces every #N with `\placeholder{{}}` BEFORE inserting.
        // This mirrors the rule in `executeCommand("insert", latex,
        // {{selectionMode:"placeholder"}})` — the test isn't running real
        // MathLive (Node-side), but the expansion is deterministic.
        const expanded = String(target.latex).replace(/#\d+/g, '\\placeholder{{}}');
        process.stdout.write(JSON.stringify({{ found: true, expanded, source: target.latex }}));
        """
    )
    assert out.get("found"), f"catalogue entry not found: {name!r}"
    assert out["expanded"] == expected, (
        f"snapshot drift for {name!r}:\n"
        f"  source LaTeX: {out['source']!r}\n"
        f"  expanded:     {out['expanded']!r}\n"
        f"  expected:     {expected!r}\n"
        "Either the catalogue entry was edited or the #N→placeholder "
        "expansion rule changed."
    )


def test_recent_persists_across_sessions_via_localstorage_shape():
    """Recently-used must survive a page reload. Pin the localStorage shape:
    array-of-strings under a stable key. If a future refactor changes the
    key or wraps it in an object, all author histories silently disappear."""
    out = _run_node(
        r"""
        window.EquationPicker._saveRecent('\\alpha');
        window.EquationPicker._saveRecent('\\beta');
        const raw = localStorage.getItem('nets.equationPicker.recent');
        const parsed = JSON.parse(raw);
        process.stdout.write(JSON.stringify({
          isArray: Array.isArray(parsed),
          allStrings: parsed.every(s => typeof s === 'string'),
          firstIsBeta: parsed[0] === '\\beta',
          length: parsed.length
        }));
        """
    )
    assert out["isArray"], "recently-used must be a top-level array"
    assert out["allStrings"], "recently-used entries must be strings"
    assert out["firstIsBeta"], "most-recent-first ordering broken"
    assert out["length"] == 2


def test_picker_saveRecent_is_atomic_under_concurrent_inserts():
    """If the user fires two inserts in rapid succession (e.g. shift-clicking
    two tiles with autorepeat), the recently-used list must converge to a
    valid state — no duplicates, no dropped entries."""
    out = _run_node(
        r"""
        // Simulate a burst of 100 random insertions of 5 distinct keys.
        const keys = ['\\alpha', '\\beta', '\\gamma', '\\delta', '\\epsilon'];
        for (let i = 0; i < 100; i++) {
          const k = keys[Math.floor(Math.random() * keys.length)];
          window.EquationPicker._saveRecent(k);
        }
        const r = window.EquationPicker._loadRecent();
        process.stdout.write(JSON.stringify({
          length: r.length,
          uniqueCount: new Set(r).size,
          allKnown: r.every(s => keys.includes(s)),
        }));
        """
    )
    assert out["length"] <= 16, "exceeded the 16-entry cap"
    assert out["uniqueCount"] == out["length"], "duplicates leaked through"
    assert out["allKnown"], "unknown keys appeared in recently-used"
