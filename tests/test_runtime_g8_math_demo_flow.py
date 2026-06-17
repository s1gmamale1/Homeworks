"""Grade 8 math demo runtime guardrails.

These tests pin the temporary showcase rule: G8 math/geometriya demos should
stay interactive and low-writing, so Adaptive Quiz and Puzzle Lock are skipped
without deleting authored data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from server.services.injector import get_ttt_answer_key, inject


ROOT = Path(__file__).parent.parent
_JS_PATH = ROOT / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = ROOT / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = ROOT / "server" / "template" / "perfect_homework.html"
RUNTIME = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


def _read() -> str:
    return RUNTIME


def _css_block(source: str, selector: str) -> str:
    pattern = re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}"
    match = re.search(pattern, source)
    assert match, f"missing CSS block for {selector}"
    return match.group("body")


def _extract_gb_ttt(html: str) -> list:
    match = re.search(r"const\s+GB_TTT\s*=\s*(\[.*?\]);", html, re.DOTALL)
    assert match, "GB_TTT constant missing"
    return json.loads(match.group(1))


def test_g8_math_demo_skip_helper_is_subject_and_grade_gated():
    html = _read()
    assert "function gbIsGrade8MathDemo()" in html
    assert "grade === 8" in html
    assert "subject === 'math-algebra'" in html
    assert "subject === 'geometriya-g7-11'" in html
    assert "return gbIsGrade8MathDemo() ? new Set(['aq', 'wc', 'pl']) : new Set();" in html


def test_g8_math_demo_filters_text_heavy_games_at_registry():
    html = _read()
    assert "const skipped = gbDemoSkippedGames();" in html
    assert "if (!skipped.has('aq') && Array.isArray(GB_ADAPTIVE_QUIZ)" in html
    assert "if (!skipped.has('wc') && Array.isArray(GB_WHY_CHAIN)" in html
    assert "if (!skipped.has('pl') && Array.isArray(GB_PUZZLE_LOCK)" in html
    # Data declarations and panels remain available; the demo skips render order only.
    assert "const GB_ADAPTIVE_QUIZ" in html
    assert "const GB_WHY_CHAIN" in html
    assert "const GB_PUZZLE_LOCK" in html
    assert 'id="gb-panel-aq"' in html
    assert 'id="gb-panel-wc"' in html
    assert 'id="gb-panel-pl"' in html


def test_tile_match_xp_pill_cannot_clip_text_mid_character():
    html = _read()
    body = _css_block(html, ".gb-tm-xp-pill")
    assert "min-width: 0" in body
    assert "overflow: hidden" in body
    assert "text-overflow: ellipsis" in body


def test_tile_match_timer_removed_from_visible_runtime():
    html = _read()
    stats_body = _css_block(html, ".gb-tm-stats")
    assert "grid-template-columns: 1fr 1fr" in stats_body
    assert 'id="gb-tm-timer"' not in html
    assert 'id="gb-tm-stat-timer-card"' not in html
    assert "tm.stats_timer" not in html
    assert "gbTMSetTimerDisplay" not in html
    assert "remaining_seconds" not in html


def test_tile_match_matched_tiles_remain_solved_placeholders():
    html = _read()
    body = _css_block(html, ".gb-tm-tile.matched")
    assert "pointer-events: none" in body
    assert "opacity: 0.52" in body
    assert "max-height: 0" not in body
    assert "min-height: 0" not in body
    assert "padding-top: 0" not in body


def test_tile_match_light_mode_tiles_have_solid_readable_surface():
    html = _read()
    tile_body = _css_block(html, ".gb-tm-tile")
    board_body = _css_block(html, ".gb-tm-board-card")
    assert "rgba(255,255,255,.25)" not in tile_body
    assert "rgba(255,255,255,.42)" not in board_body
    assert "rgba(255,255,255,.98)" in tile_body
    assert "rgba(15,23,42,.12)" in tile_body
    assert "0 9px 18px rgba(24,38,64,.08)" in tile_body
    assert "font-weight: 590" in tile_body


def test_tile_match_dark_mode_tiles_have_explicit_surface():
    html = _read()
    body = _css_block(html, '[data-theme="dark"] .gb-tm-tile')
    assert "background: var(--surface)" not in body
    assert "rgba(30,41,59,.96)" in body
    assert "rgba(148,163,184,.30)" in body


def test_g8_math_demo_synthesizes_ttt_from_why_chain_without_client_answer_leak():
    content = {
        "meta": {"title": "G8 Algebra Demo", "subject_display": "Algebra"},
        "panels": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": [],
        "gb_why_chain": [
            {"q": "Nisbiy xatolik = |x - a| _____ |a|", "inv": "/"},
            {"q": "Aniqlik chegarasi: x = a _____ h", "inv": "+/-"},
        ],
        "gb_memory_match": [],
        "gb_puzzle_lock": [],
        "gb_mystery_box": [],
        "gb_ttt": [],
        "boss_questions": [],
    }

    html = inject(
        content,
        runtime_context={"hwId": "HW-G8-TTT-FALLBACK", "subject": "math-algebra", "grade": 8},
    )
    items = _extract_gb_ttt(html)

    assert len(items) == 2
    assert items[0]["id"] == "demo-ttt-1"
    assert "options" in items[0]
    assert "correct" not in items[0]
    assert "distractors" not in items[0]
    assert get_ttt_answer_key("HW-G8-TTT-FALLBACK")["demo-ttt-1"] == "/"
