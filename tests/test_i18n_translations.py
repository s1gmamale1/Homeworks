"""
Wave I2 — i18n translation table tests.

Verifies that:
  - Every key in STRINGS.en has a counterpart in STRINGS.uz and STRINGS.ru.
  - No translation value is empty.
  - The shared "common.*" namespace is populated in all three langs.
  - Russian values use Cyrillic (catches accidental copy-paste of English).
  - Dashboard / builder / library HTML actually render data-i18n attributes.
  - The dashboard pages declare <html lang="en"> as the static fallback.

We parse strings.js with regex rather than executing JS — Python has no JS
runtime in CI, and the file is a flat object literal so plain regex is enough.
"""
import re
from pathlib import Path

import pytest


STRINGS_PATH = Path(__file__).parent.parent / "frontend" / "js" / "i18n" / "strings.js"

# Match a single key:'value' or key:"value" pair inside a string-table block.
# Captures the key, the quote char, and the raw inner value (escapes intact).
_KV_RE = re.compile(
    r"""
    ['"]([a-z][a-z0-9_.]*)['"]   # key  (must look like a dotted i18n key)
    \s*:\s*
    (['"])                       # opening quote
    ((?:\\.|(?!\2).)*)           # value contents (escapes allowed)
    \2                           # matching closing quote
    """,
    re.VERBOSE,
)


def _extract_lang_block(src: str, lang: str) -> str:
    """Return the `lang: { ... }` body (string of key:value pairs).

    The blocks are top-level inside `window.STRINGS = { en: { ... }, uz: { ... }, ru: { ... } };`
    so a brace-balance walk is sufficient.
    """
    marker = re.search(rf"\b{lang}\s*:\s*\{{", src)
    assert marker, f"could not find `{lang}:` block in strings.js"
    start = marker.end()  # position right after the opening `{`
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[start:i]
        i += 1
    raise AssertionError(f"unterminated `{lang}:` block in strings.js")


def _parse_lang(src: str, lang: str) -> dict[str, str]:
    body = _extract_lang_block(src, lang)
    pairs: dict[str, str] = {}
    for match in _KV_RE.finditer(body):
        key = match.group(1)
        raw = match.group(3)
        # Decode the JS escapes we actually use: \' \" \\ \n \t. Everything else is
        # passthrough — we don't need full JS-string semantics for our checks.
        decoded = (
            raw.replace("\\\\", "\\")
               .replace("\\'", "'")
               .replace('\\"', '"')
               .replace("\\n", "\n")
               .replace("\\t", "\t")
        )
        pairs[key] = decoded
    return pairs


@pytest.fixture(scope="module")
def strings_src() -> str:
    return STRINGS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lang_tables(strings_src) -> dict[str, dict[str, str]]:
    return {
        "en": _parse_lang(strings_src, "en"),
        "uz": _parse_lang(strings_src, "uz"),
        "ru": _parse_lang(strings_src, "ru"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Parity + value-quality checks on the STRINGS table
# ─────────────────────────────────────────────────────────────────────────────


def test_lang_tables_are_non_trivial(lang_tables):
    """Sanity: each lang block must have meaningfully many keys."""
    for lang, table in lang_tables.items():
        assert len(table) >= 50, (
            f"STRINGS.{lang} has only {len(table)} keys — expected ≥50"
        )


def test_uz_and_ru_have_every_en_key(lang_tables):
    """Parity check — both uz and ru must cover every en key."""
    en_keys = set(lang_tables["en"].keys())
    for lang in ("uz", "ru"):
        missing = sorted(en_keys - set(lang_tables[lang].keys()))
        assert not missing, (
            f"STRINGS.{lang} is missing {len(missing)} keys present in STRINGS.en: "
            f"{missing[:10]}{'…' if len(missing) > 10 else ''}"
        )


def test_no_empty_translation_values(lang_tables):
    """No translation should be an empty string in any language."""
    for lang, table in lang_tables.items():
        empties = [k for k, v in table.items() if v == ""]
        assert not empties, f"STRINGS.{lang} has empty values for: {empties}"


def test_required_common_keys_present_in_all_langs(lang_tables):
    """Shared chrome strings must exist in all three languages."""
    required = (
        "common.cancel",
        "common.close",
        "common.refresh",
        "common.loading",
        "common.retry",
        "common.draft",
        "common.ready",
    )
    for lang in ("en", "uz", "ru"):
        for key in required:
            assert key in lang_tables[lang], f"STRINGS.{lang} missing required key {key!r}"


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_LETTER_RE = re.compile(r"[A-Za-zЀ-ӿ]")


def test_russian_values_use_cyrillic(lang_tables):
    """Every ru: value that contains letters must include at least one Cyrillic
    char. Values that are purely punctuation / numbers / symbols (e.g. '…',
    '⚠ Save failed') are exempt — but if they include any Latin letter, they
    must also include a Cyrillic letter, otherwise it's almost certainly an
    untranslated copy-paste of the English string."""
    ru = lang_tables["ru"]
    offenders = []
    for key, value in ru.items():
        if not _LETTER_RE.search(value):
            # Pure punctuation / digits / symbols — fine.
            continue
        if not _CYRILLIC_RE.search(value):
            offenders.append((key, value))
    assert not offenders, (
        "Russian values without any Cyrillic char (likely untranslated):\n"
        + "\n".join(f"  {k!r}: {v!r}" for k, v in offenders)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Server-side render checks — pages must actually emit data-i18n attrs
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("path,page", [
    ("/index.html", "dashboard"),
    ("/builder.html", "builder"),
    ("/library.html", "library"),
])
def test_page_renders_data_i18n_attributes(client, path, page):
    """Each chrome page must carry a non-trivial set of data-i18n* attributes."""
    r = client.get(path)
    assert r.status_code == 200, f"GET {path} returned {r.status_code}"
    body = r.text
    matches = re.findall(r'data-i18n(?:-placeholder|-aria-label|-title)?="[^"]+"', body)
    assert len(matches) >= 5, (
        f"{page} page rendered only {len(matches)} data-i18n attrs — expected ≥5"
    )


@pytest.mark.parametrize("path", ["/index.html", "/builder.html", "/library.html"])
def test_dashboard_pages_declare_html_lang_en(client, path):
    """Static fallback should match what's actually written in the page —
    English. The lang pill flips to uz/ru via localStorage at runtime."""
    r = client.get(path)
    assert r.status_code == 200
    # Tolerate either single or double quotes; some templating could change them.
    assert re.search(r'<html\s+lang=["\']en["\']', r.text), (
        f"{path} must declare <html lang=\"en\"> as the static fallback"
    )
