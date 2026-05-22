"""Regression guard: tile-match HMAC secret resolution (Gap D).

`_resolve_secret()`:
  - uses TILE_MATCH_SECRET / SECRET_KEY when set,
  - raises RuntimeError in production when neither is set (fail loud — never
    sign with the well-known dev fallback in prod),
  - warns + uses the dev fallback otherwise.
"""
from __future__ import annotations

import logging

import pytest

from server.services import tile_match_tokens as tmt


def _clear_secret_env(monkeypatch):
    monkeypatch.delenv("TILE_MATCH_SECRET", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("NETS_ENV", raising=False)


def test_resolve_secret_uses_tile_match_secret(monkeypatch):
    _clear_secret_env(monkeypatch)
    monkeypatch.setenv("TILE_MATCH_SECRET", "real-secret-123")
    assert tmt._resolve_secret() == b"real-secret-123"


def test_resolve_secret_falls_back_to_secret_key(monkeypatch):
    _clear_secret_env(monkeypatch)
    monkeypatch.setenv("SECRET_KEY", "shared-app-secret")
    assert tmt._resolve_secret() == b"shared-app-secret"


def test_resolve_secret_production_unset_raises(monkeypatch):
    _clear_secret_env(monkeypatch)
    monkeypatch.setenv("NETS_ENV", "production")
    with pytest.raises(RuntimeError):
        tmt._resolve_secret()


def test_resolve_secret_dev_warns_and_uses_fallback(monkeypatch, caplog):
    _clear_secret_env(monkeypatch)  # not production, no secret → dev fallback
    with caplog.at_level(logging.WARNING, logger="nets.tile_match_tokens"):
        secret = tmt._resolve_secret()
    assert secret == tmt._DEV_FALLBACK_SECRET.encode()
    assert any("dev fallback" in rec.message.lower() for rec in caplog.records)


def test_resolve_secret_production_with_secret_ok(monkeypatch):
    """Production WITH a configured secret resolves cleanly (no raise)."""
    _clear_secret_env(monkeypatch)
    monkeypatch.setenv("NETS_ENV", "production")
    monkeypatch.setenv("TILE_MATCH_SECRET", "prod-secret")
    assert tmt._resolve_secret() == b"prod-secret"
