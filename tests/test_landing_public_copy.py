"""
Regression tests for landing page public-facing copy.

The landing page used to ship internal/dev-facing strings ("Template asosidagi
builder", "fixture", "/h", "3 o'quv bosqichi") that confused teachers and
students. These tests pin the public-facing replacements in place across all
three languages (uz/ru/en) so a future PR cannot silently revert the copy back
to internal jargon.

Locked surfaces:
  - hero stats (3 cards) — value + label per language
  - feature cards (4 cards) — title + body per language
  - hero text — public-facing pitch per language
"""
from pathlib import Path

import pytest


LANDING_JS = Path(__file__).parent.parent / "frontend" / "js" / "landing.js"


@pytest.fixture(scope="module")
def landing_source() -> str:
    return LANDING_JS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Forbidden: dev/internal jargon that the user explicitly called out
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "forbidden",
    [
        "Template asosidagi builder",
        "Tayyor fixturelarni yuklang",
        '"3", "o‘quv bosqichi"',          # "3", "o'quv bosqichi" — dev hero stat
        '"/h", "ulashiladigan',                 # "/h" hero stat
        '["3", "этапа',  # "3", "этапа обучения" — RU dev stat
        '["/h", "ссылки',  # "/h", "ссылки" — RU dev stat
        '["3", "learning steps"]',
        '["/h", "shareable homework links"]',
    ],
)
def test_landing_does_not_ship_internal_dev_copy(landing_source: str, forbidden: str):
    assert forbidden not in landing_source, (
        f"landing.js still ships dev-facing copy: {forbidden!r}. "
        "The landing page is teacher/student-facing — keep internal jargon "
        "out of i18n strings."
    )


# ---------------------------------------------------------------------------
# Required: public-facing copy locked across uz/ru/en
# ---------------------------------------------------------------------------

# Uzbek
@pytest.mark.parametrize(
    "snippet",
    [
        # Hero stats (uz)
        '"1 link", "dars, mashq va AI yordam bir joyda"',
        '"AI tutor", "o‘quvchini javobni aytmay',
        '"Tezroq", "o‘qituvchi uchun tayyorlash',
        # Feature titles (uz)
        "O‘qituvchi uchun tez yaratish",
        "O‘quvchi uchun bosqichma-bosqich dars",
        "AI yordam va baholash",
        "Bitta link orqali ulashish",
        # Hero text (uz)
        "Homeworks o‘qituvchiga oddiy topshiriq o‘rniga interaktiv dars",
    ],
)
def test_uz_public_copy_present(landing_source: str, snippet: str):
    assert snippet in landing_source, f"missing uz public copy: {snippet!r}"


# Russian
@pytest.mark.parametrize(
    "snippet",
    [
        # Hero stats (ru)
        '"1 ссылка"',  # "1 ссылка"
        "AI-тьютор",   # "AI-тьютор"
        '"Быстрее"',  # "Быстрее"
        # Feature titles (ru)
        "Быстрая сборка",  # "Быстрая сборка"
        "Пошаговый урок",  # "Пошаговый урок"
        "AI-помощь и оценка",  # "AI-помощь и оценка"
        "Поделиться по одной ссылке",  # "Поделиться по одной ссылке"
    ],
)
def test_ru_public_copy_present(landing_source: str, snippet: str):
    assert snippet in landing_source, f"missing ru public copy: {snippet!r}"


# English
@pytest.mark.parametrize(
    "snippet",
    [
        # Hero stats (en)
        '"One link", "lesson, practice and AI help in one place"',
        '"AI tutor", "guides the student to understand',
        '"Faster", "easier for teachers',
        # Feature titles (en)
        "Quick to build, for teachers",
        "Step-by-step lesson for students",
        "AI help and grading",
        "Share with a single link",
        # Hero text (en)
        "Homeworks helps teachers turn a plain assignment into an interactive lesson",
    ],
)
def test_en_public_copy_present(landing_source: str, snippet: str):
    assert snippet in landing_source, f"missing en public copy: {snippet!r}"


# ---------------------------------------------------------------------------
# Sanity: the page itself still serves with the locked copy embedded in JS
# (the JS bundle is fetched separately, but landing.html must still 200).
# ---------------------------------------------------------------------------

def test_landing_html_serves_200(client):
    r = client.get("/landing.html")
    assert r.status_code == 200
    # Stats and features render via JS (data-i18n-*), so we don't grep the HTML
    # for copy — this is just a routing smoke test.
    assert 'data-i18n-stat-value="0"' in r.text
    assert 'data-i18n-feature-title="0"' in r.text


def test_landing_js_serves_200(client):
    r = client.get("/js/landing.js")
    assert r.status_code == 200
    assert "1 link" in r.text  # one of the new uz stat values
    assert "Quick to build, for teachers" in r.text  # en feature title
