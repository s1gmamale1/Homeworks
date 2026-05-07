"""Lightweight LaTeX validator for the equation editor.

Pure Python — no third-party renderer dependency. Catches the four classes
of problems that actually break content storage / runtime rendering:

  1. Unbalanced delimiters: `{` `}`, `(` `)`, `[` `]`, plus `\\begin{X}` /
     `\\end{X}` pairs (must match name + nesting depth).
  2. Forbidden constructs that would break the answer-leak boundary or
     enable HTML/JS injection at render-time:
       - `<script` / `</script` (script tag breakouts)
       - `\\input{` / `\\include{` / `\\write18` (LaTeX file inclusion)
       - `\\href{` (would escape the math context once rendered)
  3. Length cap (default 2000 chars). Math content longer than this is
     almost always a paste accident and slows KaTeX render time.
  4. Unfilled MathLive `\\placeholder{}` markers — flagged as a *warning*,
     not an error. Authors sometimes save in-progress equations.

The validator is deliberately CONSERVATIVE — it errors on the small set of
constructs above and approves everything else. KaTeX's own renderer is the
final authority on whether something renders at runtime; this layer just
catches the cases that would corrupt storage or render-output before they
reach the DB.

Public API:
  validate_latex(latex: str, *, mode: str = "inline", max_length: int = 2000)
    -> dict
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_LENGTH = 2000

# Forbidden substrings (case-insensitive). Each maps to a friendly error code
# the API surfaces in the response. All of these are real breakout vectors:
#   - script tags would survive innerHTML insertion at render time
#   - \input would let LaTeX include other files (in renderers that support it)
#   - \href would inject clickable links into rendered math output
_FORBIDDEN_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"<\s*/?\s*script", "script_tag", "<script> tags are not allowed inside math content"),
    (r"\\input\s*\{", "latex_include", "\\input{} is not allowed"),
    (r"\\include\s*\{", "latex_include", "\\include{} is not allowed"),
    (r"\\write\s*18", "latex_shell_escape", "\\write18 (shell escape) is not allowed"),
    (r"\\href\s*\{", "href_macro", "\\href{} is not allowed inside math content"),
)


# Balanced brace/bracket/paren tokens. Order matters — {} must close { with },
# etc. \\begin{X} / \\end{X} are tracked separately because the name has to match.
_BRACE_OPEN = "{"
_BRACE_CLOSE = "}"
_BRACKET_OPEN = "["
_BRACKET_CLOSE = "]"


# Regex for \begin{name}/\end{name} pairs. Captures the env name.
_BEGIN_RE = re.compile(r"\\begin\s*\{([a-zA-Z*]+)\}")
_END_RE = re.compile(r"\\end\s*\{([a-zA-Z*]+)\}")

# Macro extraction: every \alpha, \frac, \begin, etc. The name is the longest
# run of letters after the backslash. Star variants (\\section*) included.
_MACRO_RE = re.compile(r"\\([a-zA-Z]+\*?)")

# MathLive's placeholder marker — used by templates the author hasn't filled.
_PLACEHOLDER_RE = re.compile(r"\\placeholder\s*\{[^{}]*\}")


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def _strip_escaped(latex: str) -> str:
    """Remove `\\\\`, `\\{`, `\\}`, `\\[`, `\\]` so the brace-balance check
    doesn't trip on escaped delimiters."""
    return re.sub(r"\\([\\{}\[\]])", "  ", latex)  # replace with spaces to keep indices

def _check_balance(latex: str) -> tuple[bool, str | None, int | None]:
    """Walk the (escape-stripped) string tracking brace/bracket/paren depth.
    Returns (ok, error_message, position). Position is 0-based byte offset
    in the ORIGINAL latex string."""
    stripped = _strip_escaped(latex)
    stack: list[tuple[str, int]] = []  # (open_char, position)
    pairs = {_BRACE_CLOSE: _BRACE_OPEN, _BRACKET_CLOSE: _BRACKET_OPEN, ")": "("}
    for i, ch in enumerate(stripped):
        if ch in (_BRACE_OPEN, _BRACKET_OPEN, "("):
            stack.append((ch, i))
        elif ch in (_BRACE_CLOSE, _BRACKET_CLOSE, ")"):
            if not stack:
                return False, f"unmatched closing '{ch}'", i
            top, _ = stack.pop()
            if top != pairs[ch]:
                return False, f"mismatched '{top}' / '{ch}'", i
    if stack:
        top, pos = stack[-1]
        return False, f"unclosed '{top}'", pos
    return True, None, None


def _check_environments(latex: str) -> tuple[bool, str | None, int | None]:
    """Walk through \\begin{X}/\\end{Y} pairs and verify each \\begin has a
    matching \\end with the same env name and proper nesting. Returns
    (ok, error_message, position-of-offender)."""
    # Build a list of (kind, name, position) events in document order.
    events: list[tuple[str, str, int]] = []
    for m in _BEGIN_RE.finditer(latex):
        events.append(("begin", m.group(1), m.start()))
    for m in _END_RE.finditer(latex):
        events.append(("end", m.group(1), m.start()))
    events.sort(key=lambda e: e[2])

    stack: list[tuple[str, int]] = []
    for kind, name, pos in events:
        if kind == "begin":
            stack.append((name, pos))
        else:
            if not stack:
                return False, f"\\end{{{name}}} without matching \\begin", pos
            top_name, _ = stack.pop()
            if top_name != name:
                return False, f"\\end{{{name}}} closes \\begin{{{top_name}}}", pos
    if stack:
        top_name, pos = stack[-1]
        return False, f"\\begin{{{top_name}}} not closed", pos
    return True, None, None


def _scan_forbidden(latex: str) -> tuple[bool, str | None, str | None, int | None]:
    """Return (ok, error_code, error_message, position) for the first
    forbidden pattern found, or (True, None, None, None)."""
    for pattern, code, msg in _FORBIDDEN_PATTERNS:
        m = re.search(pattern, latex, re.IGNORECASE)
        if m:
            return False, code, msg, m.start()
    return True, None, None, None


def _extract_macros(latex: str) -> list[str]:
    """Return the list of macro names used (e.g. ['frac', 'sqrt', 'alpha']).
    De-duplicated and sorted for stable output."""
    names = set()
    for m in _MACRO_RE.finditer(latex):
        names.add(m.group(1))
    return sorted(names)


def _count_placeholders(latex: str) -> int:
    """How many MathLive `\\placeholder{}` markers are present (= unfilled
    template cells the author left blank)."""
    return len(_PLACEHOLDER_RE.findall(latex))


def _max_brace_depth(latex: str) -> int:
    """Maximum nesting depth of { } blocks. Useful as a "this is genuinely
    a complex equation" signal."""
    stripped = _strip_escaped(latex)
    depth = 0
    max_depth = 0
    for ch in stripped:
        if ch == _BRACE_OPEN:
            depth += 1
            if depth > max_depth:
                max_depth = depth
        elif ch == _BRACE_CLOSE:
            depth -= 1
    return max_depth


def validate_latex(
    latex: str,
    *,
    mode: str = "inline",
    max_length: int = DEFAULT_MAX_LENGTH,
) -> dict[str, Any]:
    """Validate a LaTeX expression intended for KaTeX rendering.

    Args:
        latex: the raw LaTeX string. May or may not include $...$ delimiters
            (the validator strips a single matching pair before checking).
        mode: "inline" or "display". Display mode allows display-only macros
            (\\displaystyle, \\begin{aligned}, etc.) — but the validator
            doesn't currently treat them differently; the field is reserved
            for future per-mode rules.
        max_length: hard cap on the LaTeX string length. Default 2000 — chosen
            to comfortably hold a multi-line aligned equation while rejecting
            paste accidents.

    Returns:
        A dict with these keys:
          valid (bool):       overall verdict
          latex (str):        the input, with outer delimiters stripped if any
          mode (str):         echoed back
          length (int):       character count after stripping delimiters
          warnings (list):    non-fatal issues (e.g., unfilled placeholders)
          error (str|None):   error code if invalid (one of: too_long,
                              unbalanced_braces, unbalanced_environments,
                              script_tag, latex_include, latex_shell_escape,
                              href_macro, empty)
          message (str|None): human-readable description of the error
          position (int|None): 0-based offset of the offending character
                              in the cleaned latex (or None)
          macros (list[str]): all \\macro names used (dedup'd, sorted)
          placeholders (int): count of \\placeholder{} markers
          depth (int):        max brace nesting depth
    """
    if not isinstance(latex, str):
        return {
            "valid": False,
            "latex": "",
            "mode": mode,
            "length": 0,
            "warnings": [],
            "error": "type_error",
            "message": "latex must be a string",
            "position": None,
            "macros": [],
            "placeholders": 0,
            "depth": 0,
        }

    # Strip a single matching pair of $..$ or $$..$$ delimiters if present.
    stripped = latex.strip()
    if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) >= 4:
        stripped = stripped[2:-2]
    elif stripped.startswith("$") and stripped.endswith("$") and len(stripped) >= 2:
        stripped = stripped[1:-1]

    base = {
        "latex": stripped,
        "mode": mode,
        "length": len(stripped),
        "macros": _extract_macros(stripped),
        "placeholders": _count_placeholders(stripped),
        "depth": _max_brace_depth(stripped),
    }
    warnings: list[str] = []

    # 0. Empty input
    if not stripped:
        return {
            **base,
            "valid": False,
            "warnings": warnings,
            "error": "empty",
            "message": "latex is empty",
            "position": None,
        }

    # 1. Length cap
    if len(stripped) > max_length:
        return {
            **base,
            "valid": False,
            "warnings": warnings,
            "error": "too_long",
            "message": f"latex exceeds {max_length} characters",
            "position": max_length,
        }

    # 2. Forbidden constructs (security)
    ok, code, msg, pos = _scan_forbidden(stripped)
    if not ok:
        return {
            **base,
            "valid": False,
            "warnings": warnings,
            "error": code,
            "message": msg,
            "position": pos,
        }

    # 3. Brace / bracket balance
    ok, msg, pos = _check_balance(stripped)
    if not ok:
        return {
            **base,
            "valid": False,
            "warnings": warnings,
            "error": "unbalanced_braces",
            "message": msg,
            "position": pos,
        }

    # 4. \begin{X} / \end{X} matching
    ok, msg, pos = _check_environments(stripped)
    if not ok:
        return {
            **base,
            "valid": False,
            "warnings": warnings,
            "error": "unbalanced_environments",
            "message": msg,
            "position": pos,
        }

    # 5. Warnings — non-fatal
    if base["placeholders"] > 0:
        warnings.append(
            f"latex has {base['placeholders']} unfilled \\placeholder{{}} marker(s) — "
            "MathLive cells the author hasn't typed into yet"
        )

    return {
        **base,
        "valid": True,
        "warnings": warnings,
        "error": None,
        "message": None,
        "position": None,
    }
