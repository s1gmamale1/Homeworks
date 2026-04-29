"""Regression tests for the editor focus-loss bug class.

Bug pattern: ``<label class="field...">`` wrapping a contenteditable
(``.js-rich-host`` or ``.js-rich-mini``) hijacks clicks to the label's
first labelable descendant — typically the rich-text toolbar's Bold
button — which steals focus mid-keystroke and prevents the student
(or author) from typing more than one character into the rich field.

PR #32 fixed this in Sentence Fill + Tile Match (the original report).
PR #67 fixed the remaining 18 sites across boss / real-life /
consolidation / reading / reflection editors that PR #32 missed.

This test guards both fixes structurally by parametrizing over every
editor JS file and asserting zero suspect ``<label>`` wrappers remain.
A future contributor accidentally re-introducing the pattern — e.g.
when resolving a merge conflict — will fail this test before the
regression can land.

Real ``<input>`` / ``<select>`` wrappers MUST stay as ``<label>`` —
that's the correct HTML for form controls. Only contenteditable
wrappers are forbidden.
"""

import re
from pathlib import Path

import pytest

EDITORS_DIR = Path(__file__).resolve().parent.parent / "frontend" / "js" / "editors"

EDITOR_FILES = sorted(EDITORS_DIR.rglob("*.js"))


# Match a complete <label class="field..."> ... </label> block.
# The negative lookahead inside the body prevents nested-<label> swallowing.
_LABEL_FIELD_BLOCK = re.compile(
    r'<label class="field[^"]*">((?:(?!<label|</label>)[\s\S])*?)</label>'
)


@pytest.mark.parametrize(
    "editor_path",
    EDITOR_FILES,
    ids=lambda p: p.relative_to(EDITORS_DIR).as_posix(),
)
def test_no_label_wraps_contenteditable_rich_host(editor_path: Path) -> None:
    src = editor_path.read_text(encoding="utf-8")
    suspects = [
        match.group(0)
        for match in _LABEL_FIELD_BLOCK.finditer(src)
        if "js-rich-host" in match.group(0) or "js-rich-mini" in match.group(0)
    ]
    assert not suspects, (
        f'{editor_path.name} re-introduced <label class="field..."> wrapping '
        f'a contenteditable (.js-rich-host / .js-rich-mini). Use '
        f'<div class="field..."> instead — clicking the label hijacks focus '
        f'to the first labelable descendant (Bold button), stealing keystrokes '
        f'mid-edit. See PR #32 and PR #67. '
        f'Found {len(suspects)} suspect block(s); first preview: '
        f'{suspects[0][:140]!r}'
    )


def test_test_finds_at_least_one_editor_file() -> None:
    """Sanity: if the editors directory got moved or globbed wrong, the
    parametrized test would silently pass with zero parameters. This
    asserts the discovery actually found files — guard against the
    'vacuous green' failure mode the reviewer warned about."""
    assert len(EDITOR_FILES) >= 5, (
        f"Editor file discovery found only {len(EDITOR_FILES)} JS files "
        f"under {EDITORS_DIR}. Expected at least 5 (preview, flashcards, "
        f"memory-sprint, real-life, boss, etc.). Did the directory move?"
    )
