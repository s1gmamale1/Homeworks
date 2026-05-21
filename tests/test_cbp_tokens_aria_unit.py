"""Unit tier — `_tokens.css` content assertions.

Pure file-read + string-search; no DB, no TestClient, no rendering.
"""
from __future__ import annotations

from server.config import BASE_DIR


TOKENS_CSS = BASE_DIR / "frontend" / "css" / "_tokens.css"


def _read() -> str:
    return TOKENS_CSS.read_text(encoding="utf-8")


def test_tokens_file_exists():
    assert TOKENS_CSS.exists()


def test_tokens_file_non_trivial():
    assert TOKENS_CSS.stat().st_size > 1000


def test_root_block_present():
    assert ":root {" in _read()


def test_zinc_scale_tokens_present():
    text = _read()
    for token in (
        "--landing-zinc-950",
        "--landing-zinc-900",
        "--landing-zinc-100",
    ):
        assert token in text, f"missing zinc token: {token}"


def test_blue_accent_tokens_present():
    text = _read()
    for token in ("--landing-blue-600", "--landing-blue-500", "--landing-blue-400"):
        assert token in text


def test_cyan_accent_tokens_present():
    text = _read()
    assert "--landing-cyan-300" in text
    assert "--landing-cyan-200" in text


def test_shadow_tokens_present():
    text = _read()
    for token in (
        "--landing-shadow-card",
        "--landing-shadow-card-hover",
        "--landing-shadow-deep",
        "--landing-shadow-soft",
    ):
        assert token in text


def test_motion_tokens_present():
    text = _read()
    assert "--landing-spring" in text
    assert "cubic-bezier(.16, 1, .3, 1)" in text  # Apple no-overshoot
    assert "--landing-dur-md" in text
    assert "--landing-dur-lg" in text


def test_a11y_focus_visible_rule_present():
    text = _read()
    assert ":focus-visible" in text
    assert "outline: 2px solid var(--landing-blue-500)" in text


def test_a11y_reduced_motion_rule_present():
    text = _read()
    assert "@media (prefers-reduced-motion: reduce)" in text
    assert "transition-duration: 0.01ms" in text


def test_skip_link_class_present():
    text = _read()
    assert ".v2-skip-link" in text


def test_v2_data_attribute_scoped_rules():
    """v2 accessibility rules must be scoped to `[data-flow=\"v2\"]` so
    legacy homeworks aren't impacted by the new selectors."""
    text = _read()
    assert '[data-flow="v2"]' in text
