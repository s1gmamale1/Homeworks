"""
Regression tests for landing page public-facing copy.

The landing page used to ship internal/dev-facing strings ("Template asosidagi
builder", "fixture", "/h", "3 o'quv bosqichi", "Live Tutor", "checkpoint",
"lesson card", "swipe", "concept", "wording", "homework", "teacher flow",
"guided learning", "Har bir homeworkga ozgina miya bering.") that confused
teachers and students. These tests pin the natural public-facing copy in
place across all three languages (uz/ru/en) so a future PR cannot silently
revert the copy back to internal jargon.

The "required copy" snippets below track the shipped Class A Education
positioning ("Teach Anything. Prove it." / "Built on your textbooks" /
"AI tutor that guides — and never spies"). The forbidden-jargon guards are
positioning-independent and stay locked regardless of marketing copy.

Locked surfaces:
  - hero stats (3 cards) — value + label per language
  - feature cards (4 cards) — title + body per language
  - hero text — public-facing pitch per language
  - launch / CTA copy — must read like an education product, not a dev demo
  - lessonPanels, workflow, phone — must not leak panel/checkpoint/flow/
    template/fixture/student-as-English-word into Uzbek visible copy
"""
from pathlib import Path

import pytest


LANDING_JS = Path(__file__).parent.parent / "frontend" / "js" / "landing.js"


@pytest.fixture(scope="module")
def landing_source() -> str:
    return LANDING_JS.read_text(encoding="utf-8")


def _uz_block(src: str) -> str:
    """Return only the uz: { ... } slice of the i18n object so we can grep
    Uzbek-only without false-flagging on RU/EN where English loanwords are
    sometimes acceptable (e.g. "Тьютор", "AI tutor")."""
    start = src.index("uz: {")
    # The next top-level key in the i18n object is "ru:". Find it from start.
    end = src.index("\n    ru: {", start)
    return src[start:end]


def _ru_block(src: str) -> str:
    start = src.index("\n    ru: {")
    end = src.index("\n    en: {", start)
    return src[start:end]


# ---------------------------------------------------------------------------
# Forbidden in the UZ block: dev/English jargon that has no place on a
# teacher/student-facing Uzbek page. These were either explicitly called out
# by the user or are clear English residue from earlier internal copy.
# ---------------------------------------------------------------------------

UZ_FORBIDDEN_SUBSTRINGS = [
    # User explicitly called these out
    "Template asosidagi builder",
    "Tayyor fixturelarni yuklang",
    "Har bir homeworkga ozgina miya bering",
    '"3", "o‘quv bosqichi"',
    '"AI", "tutor + baholash"',
    '"/h", "ulashiladigan',
    # Forbidden English loanwords that should be Uzbek
    "homeworkni",      # → "uy vazifasi"
    "Templatedan",     # → "namuna"
    "Reading Panel",   # → "tushuntirish bosqichi"
    "Reading cardlar", # → "tushuntirish kartalari"
    "Live Tutor",      # → "AI tutor"
    "Live tutor",
    "lesson card",
    "lesson flow",
    "lesson cardlar",
    "swipe qiladi",
    "concept",
    "Concept",
    "Hybrid grading",
    "Swipe learning",
    "Adaptiv Quiz",
    "wording xato",
    "wording-xato",
    "fixturelarini",
    "checkpoint promptlar",
    "explanationsni",
    "stable homework URL",
    "Student uchun",
    "Studentlar",
    "Student hint",
    "Student javobni",
    "casual gaplar",
    "Tutor casual",
    "guided learning",
    "teacher flow",
    "Teacher uchun",
    "Teacher g‘oya",
    "Teacher g'oya",
    "homework slug",
    "rate limit",
    "privacy-aware student",
    "beta wave",
    "publish qiling",
    "AI-assisted checking",
    "student performance",
    "student linkgacha",
    "Builderni ochish",  # nav button — replaced with Uzbek phrase
    "mini learning experience",
    "line-button interaksiyasi",
    "Header"  # phone header should be "Uy vazifasi" in UZ block, not "Homework"/"Header"
    " 01",  # any "Reading Panel 01" / "01 · ..." legacy formatting w/ leading space
]


@pytest.mark.parametrize("forbidden", UZ_FORBIDDEN_SUBSTRINGS)
def test_uz_block_does_not_ship_dev_or_english_jargon(landing_source: str, forbidden: str):
    uz = _uz_block(landing_source)
    assert forbidden not in uz, (
        f"landing.js uz block still contains dev/English jargon: {forbidden!r}. "
        "Uzbek copy must be natural, public-facing — keep template/fixture/"
        "checkpoint/flow/lesson card/Student/Teacher/homework etc. out."
    )


# Also forbid clear dev-token leaks in RU/EN. These are tokens the user
# called out as dev-facing — natural English ("messy", "wording slips",
# "rate limits", "beta wave") is allowed since this *is* a beta product
# describing itself in plain language.
RU_EN_FORBIDDEN = [
    "homework slug",
    "line-to-button",
    "Reading Panel 01",
    "lesson flow",
    "Hybrid grading",
    "Адаптивный Quiz",
    "Live Tutor",
    "Live тьютор",
    "wording-ошибк",
    # CTA that the user explicitly killed in this PR
    "немного мозга",
    "little brain",
]


@pytest.mark.parametrize("forbidden", RU_EN_FORBIDDEN)
def test_ru_en_blocks_do_not_ship_dev_jargon(landing_source: str, forbidden: str):
    # Skip the uz block — those are checked separately above.
    src = landing_source
    uz = _uz_block(src)
    rest = src.replace(uz, "")
    assert forbidden not in rest, (
        f"landing.js ru/en blocks still contain dev jargon: {forbidden!r}. "
        "All three languages should describe the product, not the codebase."
    )


# ---------------------------------------------------------------------------
# Required Uzbek public copy — must be present, must read naturally
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "snippet",
    [
        # Hero stats (uz) — Class A positioning
        '"Sizning darsliklaringiz", "almashtirilmaydi, balki kuchaytiriladi — siz o‘qitayotgan o‘quv dasturi asosida"',
        '"IELTS · SAT · AP mos", "o‘quvchilar bitirish uchun zarur sertifikatlarga bog‘langan natija yo‘nalishlari"',
        '"2–3 kun", "maktabni ulashga — oylar emas"',
        # Feature cards (uz) — title + body
        "Darsliklaringiz asosida",
        "AI har bir mavzuni o‘yinlashtirilgan, mahorat sari yo‘naltirilgan yo‘lga aylantiradi",
        "Davlat talab qilayotgan natijalar",
        "IELTS, SAT, TOEFL va AP’ga moslangan imtihon tayyorgarligi yo‘nalishlari",
        "Yagona operator tizimi",
        "Kundalik’ga mos, ichida AI bilan",
        "O‘qituvchiga kamroq yuk",
        "o‘qituvchilaringiz baholash va nazoratga kamroq vaqt sarflaydi",
        # Launch CTA (uz)
        "Class A Education’ni maktabingizga olib keling.",
        "biz pilotni sozlaymiz: sizning darsliklaringiz, sizning o‘quvchilaringiz, bir necha haftada haqiqiy natijalar",
        # Hero text (uz)
        "Class A Education maktabingizning o‘z darsliklarini o‘yinlashtirilgan, AI yo‘naltirgan mahorat sari yo‘lga aylantiradi",
        # Lesson panels (uz) — mastery-journey labels
        "Har bir mavzu varaqa emas, yo‘lga aylanadi.",
        "XP, kvestlar va streaklar — haqiqiy tushunish uchun mukofot.",
        "Yodlashni emas, mahoratni isbotlang.",
        # Workflow (uz)
        "O‘quv dasturingizni moslaymiz",
        "Yo‘nalishlarni sozlang",
        "O‘quvchilar o‘ynab o‘rganadi",
        "Natijalarni ko‘rasiz",
        # Phone (uz)
        'header: "Class A"',
        'checkpoint: "Mahorat tekshiruvi"',
        # Student label in UZ block
        'studentLabel: "O‘quvchi"',
    ],
)
def test_uz_natural_public_copy_present(landing_source: str, snippet: str):
    assert snippet in landing_source, f"missing uz public copy: {snippet!r}"


# ---------------------------------------------------------------------------
# Required Russian public copy — parallel meaning, no dev jargon
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "snippet",
    [
        '"Ваши учебники", "не заменяем, а усиливаем — на основе программы, которую вы уже преподаёте"',
        '"IELTS · SAT · AP", "треки результатов, привязанные к сертификатам, нужным ученику для выпуска"',
        '"2–3 дня", "на подключение школы — а не месяцы"',
        "На основе ваших учебников",
        "Результаты, которых теперь требует государство",
        "Единая операторская система",
        "Меньше нагрузки на учителя",
        "Приведите Class A Education в вашу школу.",
        "Подключаем вашу программу",
        "Ученики учатся в игре",
        "Вы видите результаты",
    ],
)
def test_ru_natural_public_copy_present(landing_source: str, snippet: str):
    assert snippet in landing_source, f"missing ru public copy: {snippet!r}"


# ---------------------------------------------------------------------------
# Required English public copy
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "snippet",
    [
        '"Your textbooks", "enhanced, never replaced — we build on the curriculum you already teach"',
        '"IELTS · SAT · AP-aligned", "outcome tracks mapped to the certificates students need to graduate"',
        '"2–3 days", "to onboard a school — not months"',
        "Built on your textbooks",
        "Outcomes the state now requires",
        "One operator system",
        "Less teacher labor",
        "Bring Class A Education to your school.",
        "We map your curriculum",
        "Students learn, gamified",
        "You see outcomes",
    ],
)
def test_en_natural_public_copy_present(landing_source: str, snippet: str):
    assert snippet in landing_source, f"missing en public copy: {snippet!r}"


# ---------------------------------------------------------------------------
# Sanity: the page itself still serves with the locked copy embedded in JS.
# ---------------------------------------------------------------------------

def test_landing_html_serves_200(client):
    r = client.get("/landing.html")
    assert r.status_code == 200
    assert 'data-i18n-stat-value="0"' in r.text
    assert 'data-i18n-feature-title="0"' in r.text


def test_landing_js_serves_200(client):
    r = client.get("/js/landing.js")
    assert r.status_code == 200
    assert "Sizning darsliklaringiz" in r.text
    assert "Class A Education’ni maktabingizga olib keling." in r.text
    assert "Built on your textbooks" in r.text
