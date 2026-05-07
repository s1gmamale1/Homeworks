"""Equation Editor (MathLive integration) — static structure regression.

Pure-file regex tests that pin the wiring contract for the MathLive-based
equation editor:

  1. The four new JS modules (mathlive-bootstrap.js, _equation-symbols.js,
     _equation-picker.js, plus the Σ button in preview.js) are registered
     in builder.html with ?v=__VERSION__ cache-bust (Invariant 5) and
     loaded in the right order (mathlive → symbols → picker → preview).
  2. preview.js wires `cmd === "equation"` to window.EquationPicker.open
     and uses snapshotForSerialize() in syncEditor so math-fields are
     collapsed to $LaTeX$ text BEFORE htmlToBlocks runs.
  3. Hydration runs after every repaint() — every paint walks
     .js-rich-editor and calls hydrateMathInElement so authored content
     containing $LaTeX$ gets WYSIWYG widgets immediately.
  4. The math-block CSS container is position-stable (inline-block,
     vertical-align:middle) and has dark-mode overrides.
  5. Picker keeps the security guarantees from PR #193: no eval, no
     Function ctor, no document.write, all innerHTML is escHtml-guarded.
  6. katex-render now ignores the rich-editor classes so KaTeX doesn't
     double-render LaTeX inside the contenteditable.

Storage contract pin: the serializer writes inline `$LaTeX$` and display
`$$LaTeX$$`, never custom HTML. This protects Invariant 1 (frozen
content_json) — runtime renders the LaTeX via existing KaTeX.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
BOOTSTRAP_JS = ROOT / "frontend" / "js" / "mathlive-bootstrap.js"
SYMBOLS_JS = ROOT / "frontend" / "js" / "editors" / "_equation-symbols.js"
PICKER_JS = ROOT / "frontend" / "js" / "editors" / "_equation-picker.js"
PREVIEW_JS = ROOT / "frontend" / "js" / "editors" / "preview.js"
KATEX_JS = ROOT / "frontend" / "js" / "katex-render.js"
BUILDER_HTML = ROOT / "frontend" / "builder.html"
APP_CSS = ROOT / "frontend" / "css" / "app.css"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ── Builder.html registration (Invariant 5) ─────────────────────────


@pytest.mark.parametrize(
    "script_name",
    [
        "/js/mathlive-bootstrap.js",
        "/js/editors/_equation-symbols.js",
        "/js/editors/_equation-picker.js",
    ],
)
def test_builder_registers_script_with_cachebust(script_name):
    html = _read(BUILDER_HTML)
    assert (
        script_name + "?v=__VERSION__" in html
    ), f"{script_name} not registered with ?v=__VERSION__ in builder.html"


def test_load_order_mathlive_before_symbols_before_picker_before_preview():
    """The picker calls window.netsMathLive (from bootstrap) and
    window.EquationSymbols (from symbols). Preview.js dispatches clicks
    into window.EquationPicker. If the order is wrong, the first user
    interaction races against the IIFEs and crashes."""
    html = _read(BUILDER_HTML)
    bootstrap = html.find("mathlive-bootstrap.js")
    symbols   = html.find("_equation-symbols.js")
    picker    = html.find("_equation-picker.js")
    preview   = html.find("/js/editors/preview.js")
    assert bootstrap > 0 and symbols > 0 and picker > 0 and preview > 0
    assert bootstrap < symbols < picker < preview, (
        "load order broken: expected bootstrap < symbols < picker < preview, "
        f"got {bootstrap} < {symbols} < {picker} < {preview}"
    )


# ── MathLive bootstrap module shape ─────────────────────────────────


def test_mathlive_bootstrap_exposes_global():
    src = _read(BOOTSTRAP_JS)
    assert "window.netsMathLive" in src
    for key in ("ensureLoaded", "isLoaded", "makeField", "fieldToTextNode"):
        assert key in src, f"netsMathLive missing key: {key}"


def test_mathlive_pinned_version():
    """Pin the MathLive version so a release can't change behavior under us."""
    src = _read(BOOTSTRAP_JS)
    m = re.search(r'MATHLIVE_VERSION\s*=\s*"([\d.]+)"', src)
    assert m, "MATHLIVE_VERSION constant missing in bootstrap"
    parts = m.group(1).split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), (
        f"MATHLIVE_VERSION should be major.minor.patch, got {m.group(1)!r}"
    )


# ── Picker module shape (carryover guarantees from PR #193) ─────────


def test_picker_exposes_global_and_helpers():
    src = _read(PICKER_JS)
    assert "window.EquationPicker" in src
    for key in ("open", "close", "insertNewFieldAtCaret", "bindFieldEvents"):
        assert key in src, f"EquationPicker missing helper: {key}"


@pytest.mark.parametrize("banned", [
    r"\beval\s*\(",
    r"\bFunction\s*\(",
    r"document\.write\s*\(",
    r"dangerouslySetInnerHTML",
])
@pytest.mark.parametrize("source_file", [PICKER_JS, SYMBOLS_JS, BOOTSTRAP_JS])
def test_no_dangerous_apis(banned, source_file):
    src = _read(source_file)
    assert not re.search(banned, src), (
        f"{source_file.name} matches banned API /{banned}/ — XSS / RCE risk"
    )


def test_picker_innerHTML_uses_escape():
    src = _read(PICKER_JS)
    suspicious = re.findall(r"(?:innerHTML|outerHTML)\s*=\s*([^;]+);", src)
    for chunk in suspicious:
        if "entry." in chunk or "cat." in chunk or "it." in chunk:
            assert "escHtml(" in chunk, (
                f"unescaped innerHTML interpolation:\n  {chunk[:200]}"
            )


# ── preview.js wiring contracts ─────────────────────────────────────


def test_preview_toolbar_includes_equation_button():
    src = _read(PREVIEW_JS)
    assert 'data-cmd="equation"' in src
    m = re.search(r'<button[^>]*data-cmd="equation"[^>]*>', src)
    assert m and 'aria-haspopup="dialog"' in m.group(0), (
        "Σ button missing or missing aria-haspopup"
    )


def test_runCommand_routes_equation_into_picker():
    src = _read(PREVIEW_JS)
    m = re.search(
        r'else if\s*\(\s*cmd\s*===\s*"equation"\s*\)\s*\{(?P<body>[\s\S]*?)\}\s*else if',
        src,
    )
    assert m, 'runCommand has no `cmd === "equation"` branch'
    body = m.group("body")
    assert "window.EquationPicker.open" in body
    # Must check window.netsMathLive is loaded — otherwise insert is a no-op.
    assert "window.netsMathLive" in body, (
        "equation branch must check window.netsMathLive availability"
    )


def test_syncEditor_uses_snapshot_for_serialize():
    """Pin that syncEditor passes the editor through snapshotForSerialize()
    BEFORE handing it to htmlToBlocks. If a future refactor inlines
    htmlToBlocks(editor) directly, math-field elements get serialized as
    raw <math-field> HTML into block.text — corrupting the runtime render
    path which expects $LaTeX$ text."""
    src = _read(PREVIEW_JS)
    m = re.search(
        r"function syncEditor\s*\([^)]*\)\s*\{(?P<body>[\s\S]*?)^\s{4}\}",
        src,
        re.MULTILINE,
    )
    assert m, "syncEditor function not found"
    body = m.group("body")
    assert "snapshotForSerialize" in body, (
        "syncEditor() must call snapshotForSerialize() before htmlToBlocks "
        "— otherwise math-fields serialize as raw HTML, corrupting storage"
    )


def test_repaint_hydrates_math_in_editors():
    """After every repaint, the editor's $LaTeX$ text must be hydrated to
    math-field widgets. Otherwise content with existing math from a prior
    save reloads as plain `$\\frac{a}{b}$` literal text in the contenteditable."""
    src = _read(PREVIEW_JS)
    # The repaint function ends with the editors-forEach call.
    m = re.search(r"function repaint\s*\([^)]*\)\s*\{[\s\S]*?\}\s*\n\s*function panelIndexOf", src)
    assert m, "repaint() function not found"
    body = m.group(0)
    assert "hydrateMathInElement" in body, (
        "repaint() must call hydrateMathInElement on .js-rich-editor children"
    )


def test_serializer_emits_dollar_dollar_for_display_mode():
    src = _read(PREVIEW_JS)
    m = re.search(r"function snapshotForSerialize\s*\(", src)
    assert m, "snapshotForSerialize not found"
    # Pull the function body — terminate at the next top-level `function `.
    body_start = m.end()
    body = src[body_start: body_start + 3000]
    assert '"$$" + latex + "$$"' in body, (
        "serializer must emit $$..$$ for display-mode (matrix/cases) entries"
    )
    assert '"$" + latex + "$"' in body, (
        "serializer must emit $..$ for inline math"
    )


def test_hydrator_parses_inline_and_display_delimiters():
    src = _read(PREVIEW_JS)
    # Pin the regex shape — display $$..$$ branch + inline $..$ branch.
    m = re.search(r"_MATH_DELIM_RE\s*=\s*(/[^/]+/[gimsuy]*)", src)
    assert m, "_MATH_DELIM_RE constant not found"
    pattern = m.group(1)
    assert "\\$\\$" in pattern, "hydrator regex missing display delimiter"
    assert "(?<!\\\\)\\$" in pattern, (
        "hydrator regex must escape-aware (skip \\$ literal escapes)"
    )


# ── katex-render isolation ──────────────────────────────────────────


def test_katex_ignores_rich_editor_classes():
    """KaTeX must not render LaTeX inside any contenteditable rich-editor
    surface — otherwise the in-editor math-field has its surroundings
    KaTeX-rendered, and saving picks up the rendered HTML instead of the
    original LaTeX."""
    src = _read(KATEX_JS)
    m = re.search(r"ignoredClasses\s*:\s*\[(?P<list>[^\]]+)\]", src)
    assert m, "KATEX_OPTS.ignoredClasses not found"
    listed = m.group("list")
    for cls in ("rich-field", "js-rich-editor", "js-rich-mini"):
        assert f"'{cls}'" in listed, (
            f"KATEX_OPTS.ignoredClasses must include '{cls}'"
        )


# ── CSS contracts ───────────────────────────────────────────────────


def test_math_block_css_present_with_dark_mode():
    css = _read(APP_CSS)
    assert ".math-block" in css
    # Must have a dark-mode override (border + background).
    assert re.search(r'\[data-theme="dark"\]\s*\.math-block', css), (
        "math-block must have a [data-theme=\"dark\"] override"
    )
    # Must use vertical-align:middle so it sits inline with text.
    block = re.search(r"\.math-block\s*\{[^}]+\}", css)
    assert block, ".math-block rule body missing"
    assert "vertical-align: middle" in block.group(0), (
        "math-block must vertical-align:middle so inline math sits "
        "with the surrounding text baseline"
    )


def test_picker_panel_three_responsive_surfaces_css():
    css = _read(APP_CSS)
    for s in ("is-popover", "is-centered", "is-sheet"):
        assert f".equation-picker-panel.{s}" in css, (
            f"missing CSS rule for .equation-picker-panel.{s}"
        )


# ── Nesting + lifecycle contracts ───────────────────────────────────


def test_picker_keeps_active_field_after_close_for_nesting():
    """When the picker closes, `STATE.activeMathField` must NOT be reset.
    Reason: the user often opens the picker, inserts a fraction, closes
    the picker, then types — and the next picker open should target the
    same fraction so a sqrt lands inside its numerator. If closePicker()
    nulls activeMathField, every nested insert mounts a new field instead.
    Pinned by reading the source directly."""
    src = _read(PICKER_JS)
    m = re.search(r"function closePicker\s*\(\s*\)\s*\{(?P<body>[\s\S]*?)^\s{2}\}", src, re.MULTILINE)
    assert m, "closePicker function not found"
    body = m.group("body")
    # Must NOT clear STATE.activeMathField in close (the comment "Don't
    # clear activeMathField" is the documented contract).
    assert "STATE.activeMathField = null" not in body, (
        "closePicker() must NOT reset activeMathField — that breaks "
        "nesting (insert frac → close → re-open targets a fresh field "
        "instead of the existing one)"
    )


def test_picker_passes_selectionMode_placeholder_for_templates():
    """MathLive's executeCommand only honors `#N` placeholders when
    `selectionMode: "placeholder"` is set. If that option drops, every
    template inserts as raw text with no editable cells — defeating the
    entire WYSIWYG feature."""
    src = _read(PICKER_JS)
    # Use re.DOTALL so the regex spans the multi-line executeCommand call.
    m = re.search(
        r'executeCommand\(\[\s*"insert"\s*,\s*entry\.latex\s*,\s*\{[^}]*\}\s*,?\s*\]\)',
        src,
        re.DOTALL,
    )
    assert m, "expected executeCommand([...insert, entry.latex, {...}]) call"
    call = m.group(0)
    assert 'selectionMode: "placeholder"' in call, (
        'tile insertion must pass selectionMode: "placeholder" so the cursor '
        "lands in the first \\placeholder{} after expansion"
    )
    assert 'insertionMode: "replaceSelection"' in call, (
        'tile insertion must pass insertionMode: "replaceSelection" so the '
        "current placeholder is replaced (not appended after)"
    )


def test_math_field_esc_exits_to_surrounding_editor():
    """ESC inside a math-field must move the caret out to the surrounding
    contenteditable, not bubble up and close the picker. The picker's
    keydown listener has a guard: `if event.target.tagName === "MATH-FIELD"
    return` — pin that guard."""
    src = _read(PICKER_JS)
    # The picker's global ESC handler must short-circuit when the event
    # originated inside a math-field (otherwise ESC closes the picker
    # instead of letting MathLive's own ESC handler run).
    assert (
        'event.target.tagName === "MATH-FIELD"' in src
    ), (
        "picker's ESC handler must check event.target.tagName for MATH-FIELD "
        "and return without closing — otherwise ESC inside the equation "
        "closes the picker prematurely"
    )


def test_outside_click_ignores_math_field():
    """Clicks INSIDE a math-field (the field the user is editing) must not
    close the picker. MathLive emits selection events that can register as
    document.mousedown originating inside the field — without this guard,
    every cursor placement inside the equation closes the picker."""
    src = _read(PICKER_JS)
    assert 'closest("math-field")' in src, (
        "outside-click handler must guard with target.closest('math-field') "
        "so cursor placements inside the equation don't close the picker"
    )


# ── Hydration contract pins ─────────────────────────────────────────


def test_hydrator_skips_existing_math_blocks():
    """The hydrator (`hydrateMathInElement` in preview.js) walks text nodes
    looking for $LaTeX$ patterns. It MUST skip subtrees rooted in either an
    existing math-field OR a math-block wrapper — otherwise re-running the
    hydrator (e.g. after a partial repaint) double-mounts every equation,
    leading to nested `<math-field><math-field>...` corruption."""
    src = _read(PREVIEW_JS)
    # The walker's acceptNode function must reject MATH-FIELD ancestors AND
    # the math-block class.
    assert 'cur.tagName' in src and '"MATH-FIELD"' in src and "math-block" in src, (
        "hydrator must skip both <math-field> and .math-block subtrees "
        "(idempotency requirement — repaint must not double-mount)"
    )


def test_serializer_strips_zero_width_spacers():
    """The picker uses a zero-width space character to give the caret a
    target after a math-block insertion. Save must strip those — they'd
    otherwise leak into stored block.text and accumulate on every keystroke."""
    src = _read(PREVIEW_JS)
    m = re.search(r"function snapshotForSerialize\s*\(", src)
    assert m, "snapshotForSerialize not found"
    body = src[m.end(): m.end() + 3000]
    # Either an explicit replace of ​ OR the literal char in a regex.
    assert "​" in body or "\\u200b" in body or "/​/" in body, (
        "serializer must strip zero-width spacers (U+200B) inserted as "
        "caret targets — otherwise they accumulate in saved block.text"
    )
