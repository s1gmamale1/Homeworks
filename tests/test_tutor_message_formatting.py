"""Tutor assistant-message formatting regression tests.

The tutor used to dump raw JSON / unstyled output into the chat panel.
Wave: the runtime now ships a `formatAssistantMessage(text, container)`
helper that:
  * detects JSON-looking responses and renders them as a styled card
    (`.nets-tutor-json` — definition list for flat objects, pretty-
    printed `<pre><code>` for arrays / nested),
  * falls back to a small markdown subset (paragraphs, `- ` and `1. `
    lists, fenced ``` blocks, inline `code`, **bold**, *italic*, `<br>`),
  * is XSS-safe — every string lands in textContent, never innerHTML.

To avoid depending on jsdom we follow the pattern from
`test_runtime_preview_pagination.py`: re-implement the algorithm in
Python against a tiny pseudo-DOM, and separately scan the runtime
template to assert the JS contract is wired.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
_TUTOR_JS_PATH = ROOT / "server" / "template" / "static" / "js" / "tutor.js"
RUNTIME = (_HTML_PATH.read_text(encoding="utf-8") + "\n" +
           _JS_PATH.read_text(encoding="utf-8") + "\n" +
           _CSS_PATH.read_text(encoding="utf-8") + "\n" +
           _TUTOR_JS_PATH.read_text(encoding="utf-8"))

WHITELIST = {"p", "ul", "ol", "li", "code", "pre", "strong", "em", "br",
             "div", "dl", "dt", "dd"}


# ---------------------------------------------------------------------------
# Tiny pseudo-DOM
# ---------------------------------------------------------------------------


class Node:
    """Minimal stand-in for a DOM node — element or text."""

    __slots__ = ("tag", "text", "children", "class_name")

    def __init__(self, tag: str | None, text: str = "") -> None:
        self.tag = tag           # None → text node
        self.text = text         # used for text nodes; "" otherwise
        self.children: list[Node] = []
        self.class_name = ""

    # ── Traversal helpers ────────────────────────────────────────
    def find_all(self, tag: str) -> list["Node"]:
        out: list[Node] = []
        if self.tag == tag:
            out.append(self)
        for c in self.children:
            out.extend(c.find_all(tag))
        return out

    def text_all(self) -> str:
        if self.tag is None:
            return self.text
        return "".join(c.text_all() for c in self.children)

    def has_class(self, name: str) -> bool:
        return self.tag is not None and name in (self.class_name or "").split()


def el(tag: str, *, class_name: str = "") -> Node:
    n = Node(tag)
    n.class_name = class_name
    return n


def text(s: str) -> Node:
    return Node(None, s)


# ---------------------------------------------------------------------------
# Python port of the JS algorithm in perfect_homework.html
# Mirrors:
#   formatAssistantMessage / renderJsonInto / renderMarkdownWithFencesInto
#   renderMarkdownInto / appendInline / appendBoldItalic
# Keep these in sync if the JS algorithm changes — `test_python_port_*`
# below verifies key constants and identifiers.
# ---------------------------------------------------------------------------


_INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")


def _append_bold_italic(parent: Node, s: str) -> None:
    last = 0
    for m in _INLINE_RE.finditer(s):
        if m.start() > last:
            parent.children.append(text(s[last:m.start()]))
        tok = m.group(0)
        if tok.startswith("**") and tok.endswith("**"):
            n = el("strong")
            n.children.append(text(tok[2:-2]))
            parent.children.append(n)
        else:
            n = el("em")
            n.children.append(text(tok[1:-1]))
            parent.children.append(n)
        last = m.end()
    if last < len(s):
        parent.children.append(text(s[last:]))


def _append_inline(parent: Node, s: str) -> None:
    parts = re.split(r"(`[^`]+`)", s)
    for part in parts:
        if not part:
            continue
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            c = el("code")
            c.children.append(text(part[1:-1]))
            parent.children.append(c)
        else:
            _append_bold_italic(parent, part)


def render_markdown_into(parent: Node, src: str) -> None:
    if not src:
        return
    blocks = re.split(r"\n{2,}", src)
    for block in blocks:
        trimmed = block.strip()
        if not trimmed:
            continue
        lines = trimmed.split("\n")
        is_ul = all(re.match(r"^\s*[-*]\s+", l) for l in lines)
        is_ol = all(re.match(r"^\s*\d+[.)]\s+", l) for l in lines)
        if is_ul or is_ol:
            lst = el("ul" if is_ul else "ol")
            for line in lines:
                li = el("li")
                stripped = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", line)
                _append_inline(li, stripped)
                lst.children.append(li)
            parent.children.append(lst)
        else:
            p = el("p")
            segs = trimmed.split("\n")
            for idx, seg in enumerate(segs):
                _append_inline(p, seg)
                if idx < len(segs) - 1:
                    p.children.append(el("br"))
            parent.children.append(p)


def render_markdown_with_fences_into(parent: Node, src: str) -> None:
    if not src:
        return
    lines = src.split("\n")
    i = 0
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        joined = "\n".join(buf)
        if joined.strip():
            render_markdown_into(parent, joined)
        buf.clear()

    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*```(.*)$", line):
            flush()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not re.match(r"^\s*```\s*$", lines[i]):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            pre = el("pre")
            code = el("code")
            code.children.append(text("\n".join(code_lines)))
            pre.children.append(code)
            parent.children.append(pre)
            continue
        buf.append(line)
        i += 1
    flush()


def _has_nested_object(value) -> bool:
    if isinstance(value, list):
        return any(isinstance(x, (list, dict)) for x in value)
    if isinstance(value, dict):
        return any(isinstance(x, (list, dict)) for x in value.values())
    return False


def render_json_into(parent: Node, value) -> None:
    wrap = el("div", class_name="nets-tutor-json")
    if isinstance(value, list) or _has_nested_object(value):
        pre = el("pre")
        code = el("code")
        code.children.append(text(json.dumps(value, indent=2)))
        pre.children.append(code)
        wrap.children.append(pre)
    else:
        dl = el("dl", class_name="nets-tutor-json-dl")
        for key in value:
            dt = el("dt")
            dt.children.append(text(str(key)))
            dd = el("dd")
            v = value[key]
            if v is None:
                dd.children.append(text("null"))
            elif isinstance(v, str):
                _append_inline(dd, v)
            else:
                dd.children.append(text(str(v)))
            dl.children.append(dt)
            dl.children.append(dd)
        wrap.children.append(dl)
    parent.children.append(wrap)


def format_assistant_message(src: str) -> Node:
    """Python port of the JS `formatAssistantMessage(text, container)`."""
    container = el("div", class_name="nets-tutor-msg assistant")
    raw = "" if src is None else str(src)
    trimmed = raw.strip()
    if trimmed and trimmed[0] in "{[":
        try:
            parsed = json.loads(trimmed)
        except ValueError:
            parsed = None
        if isinstance(parsed, (dict, list)):
            render_json_into(container, parsed)
            return container
    render_markdown_with_fences_into(container, raw)
    if not container.children:
        container.children.append(text(raw))
    return container


# ---------------------------------------------------------------------------
# Whitelist guard — every produced element type is in the safe set.
# ---------------------------------------------------------------------------


def _all_tags(node: Node) -> set[str]:
    out: set[str] = set()
    if node.tag is not None:
        out.add(node.tag)
    for c in node.children:
        out.update(_all_tags(c))
    return out


# ---------------------------------------------------------------------------
# Static checks — assert the runtime template wires the formatter.
# ---------------------------------------------------------------------------


def _runtime() -> str:
    return RUNTIME


def test_runtime_defines_format_assistant_message():
    src = _runtime()
    assert "function formatAssistantMessage(" in src
    assert "function renderJsonInto(" in src
    assert "function renderMarkdownWithFencesInto(" in src
    # Exposed for test harnesses / future callers.
    assert "window._netsFormatAssistantMessage = formatAssistantMessage" in src


def test_runtime_routes_assistant_messages_through_formatter():
    src = _runtime()
    # appendMessage must dispatch on role and call formatAssistantMessage
    # for the assistant branch only.
    m = re.search(
        r"function appendMessage\(role, content\)\s*\{(.+?)\n\s{8}\}",
        src, re.DOTALL,
    )
    assert m, "appendMessage not found"
    body = m.group(1)
    assert "formatAssistantMessage(content, el)" in body
    # User and error still use the simple markdown path.
    assert "renderMarkdownInto(el, content)" in body


def test_runtime_calls_render_math_in_element_after_dom_built():
    src = _runtime()
    # KaTeX integration — formatter calls renderMathInElement after the
    # DOM is assembled (best-effort, guarded by feature detect).
    assert "window.renderMathInElement(container" in src


def test_runtime_does_not_assign_innerHTML_in_formatter():
    src = _runtime()
    # Snip the formatter region and check no innerHTML assignment slipped in.
    start = src.index("Assistant-only formatter")
    end = src.index("function appendTyping()", start)
    region = src[start:end]
    assert ".innerHTML" not in region, (
        "formatter must never assign untrusted output to innerHTML; "
        "use textContent / createTextNode / createElement"
    )


def test_runtime_has_nets_tutor_json_styles():
    src = _runtime()
    assert ".nets-tutor-json" in src
    assert ".nets-tutor-msg.assistant pre" in src


# ---------------------------------------------------------------------------
# Behavioural checks via the Python port.
# ---------------------------------------------------------------------------


def test_json_object_renders_as_definition_list():
    out = format_assistant_message('{"answer": 42, "topic": "vectors"}')
    wrappers = out.find_all("div")
    json_wrappers = [w for w in wrappers if w.has_class("nets-tutor-json")]
    assert len(json_wrappers) == 1, "expected a single .nets-tutor-json wrapper"
    dts = out.find_all("dt")
    dds = out.find_all("dd")
    assert [d.text_all() for d in dts] == ["answer", "topic"]
    assert [d.text_all() for d in dds] == ["42", "vectors"]


def test_json_array_renders_as_pretty_printed_pre_block():
    out = format_assistant_message('[1, 2, 3]')
    wrap = next(iter(w for w in out.find_all("div") if w.has_class("nets-tutor-json")))
    pre_blocks = wrap.find_all("pre")
    assert len(pre_blocks) == 1
    code_blocks = pre_blocks[0].find_all("code")
    assert code_blocks
    assert code_blocks[0].text_all() == "[\n  1,\n  2,\n  3\n]"


def test_json_with_nested_object_uses_pre_block_not_dl():
    out = format_assistant_message('{"meta": {"nested": true}}')
    wrap = next(iter(w for w in out.find_all("div") if w.has_class("nets-tutor-json")))
    assert wrap.find_all("pre"), "nested objects should fall back to <pre><code>"
    assert not wrap.find_all("dl"), "nested objects should NOT use the <dl> path"


def test_markdown_bullets_render_as_ul_li():
    out = format_assistant_message("- one\n- two\n- three")
    uls = out.find_all("ul")
    assert len(uls) == 1
    items = [li.text_all() for li in uls[0].find_all("li")]
    assert items == ["one", "two", "three"]


def test_markdown_numbered_list_renders_as_ol_li():
    out = format_assistant_message("1. first\n2. second\n3. third")
    ols = out.find_all("ol")
    assert len(ols) == 1
    items = [li.text_all() for li in ols[0].find_all("li")]
    assert items == ["first", "second", "third"]


def test_markdown_bold_renders_as_strong():
    out = format_assistant_message("Use **vectors** today.")
    strongs = out.find_all("strong")
    assert [s.text_all() for s in strongs] == ["vectors"]


def test_markdown_italic_renders_as_em():
    out = format_assistant_message("That's *important*.")
    ems = out.find_all("em")
    assert [e.text_all() for e in ems] == ["important"]


def test_markdown_inline_code_renders_as_code():
    out = format_assistant_message("Run `pytest -q` then iterate.")
    codes = out.find_all("code")
    assert any(c.text_all() == "pytest -q" for c in codes)


def test_markdown_fenced_code_block_renders_as_pre_code():
    src = "Here's a snippet:\n\n```\nprint('hi')\n```\n"
    out = format_assistant_message(src)
    pres = out.find_all("pre")
    assert len(pres) == 1
    codes = pres[0].find_all("code")
    assert codes and codes[0].text_all() == "print('hi')"


def test_pure_plain_text_renders_as_single_paragraph():
    out = format_assistant_message("Just some plain text without any markup.")
    ps = out.find_all("p")
    assert len(ps) == 1
    assert ps[0].text_all() == "Just some plain text without any markup."
    # And no markdown-only tags appeared as a side effect.
    assert not out.find_all("strong")
    assert not out.find_all("em")
    assert not out.find_all("code")


def test_adversarial_html_is_rendered_as_visible_text_not_executed():
    payload = '<script>alert(1)</script>'
    out = format_assistant_message(payload)
    # No <script> element can ever appear in the produced DOM.
    assert not out.find_all("script"), "script tag must never appear in output"
    # Literal text must be preserved verbatim.
    assert payload in out.text_all()


def test_adversarial_html_inside_json_string_value_is_text():
    payload = '<img src=x onerror=alert(1)>'
    src = json.dumps({"answer": payload})
    out = format_assistant_message(src)
    # No img tag, no script execution surface.
    assert not out.find_all("img")
    assert not out.find_all("script")
    # Text is preserved verbatim somewhere in the dd cell.
    dds = out.find_all("dd")
    assert any(payload in d.text_all() for d in dds)


def test_only_whitelisted_tags_are_produced():
    """Check several inputs and assert every element tag stays within the
    safe whitelist `p, ul, ol, li, code, pre, strong, em, br` (plus the
    structural `div`/`dl`/`dt`/`dd` we use for the JSON card)."""
    samples = [
        'plain text',
        '**bold** and *italic* and `code`',
        '- a\n- b',
        '1. x\n2. y',
        'paragraph one\n\nparagraph two',
        '```\ncode block\n```',
        '{"a":1,"b":"x"}',
        '[1,2,3]',
        '<script>alert(1)</script>',
        '<img onerror=x>',
    ]
    for s in samples:
        out = format_assistant_message(s)
        produced = _all_tags(out) - {None}
        assert produced.issubset(WHITELIST), (
            f"input {s!r} produced disallowed tags: {produced - WHITELIST}"
        )


def test_invalid_json_falls_back_to_markdown_paragraph():
    # Looks like JSON, isn't — formatter must not crash, must not dump a
    # JSON card, must still render readable markdown.
    out = format_assistant_message('{not really json after all}')
    assert not [w for w in out.find_all("div") if w.has_class("nets-tutor-json")]
    assert out.find_all("p"), "invalid JSON should fall through to markdown <p>"


def test_python_port_matches_runtime_helper_names():
    """Cheap drift check: the JS function names referenced by the Python
    port must still exist in the runtime template."""
    src = _runtime()
    for name in (
        "formatAssistantMessage",
        "renderJsonInto",
        "renderMarkdownWithFencesInto",
        "renderMarkdownInto",
        "appendInline",
        "appendBoldItalic",
    ):
        assert f"function {name}(" in src, f"missing JS function {name}"
