"""Apply textbook-grounded flashcard media polish to the Grade 8 math demos.

This one-off targets the two local demo rows:

- HW-20260505-006: Algebra, "Nisbiy xatolik" (textbook section 21)
- HW-20260505-005: Geometry, complementary-angle trig formulas (section 22)

It only replaces ``content_json.flashcards``. All panels, games, quotes, and
grading data are preserved.

Run against the local API:

    python scripts/oneoff/polish_g8_math_demo_flashcards.py --apply

Use ``--base-url`` if the server is elsewhere.
"""

from __future__ import annotations

import argparse
import copy
import json
import urllib.error
import urllib.request
from typing import Any


ALGEBRA_HW_ID = "HW-20260505-006"
GEOMETRY_HW_ID = "HW-20260505-005"


BLUE = "#0066CC"
CYAN = "#4CC9F0"
GREEN = "#34C759"
ORANGE = "#FF9F0A"
PINK = "#FF4D8D"
TEXT = "#EAF2FF"
MUTED = "#9FB1C8"
LINE = "#8FB8FF"


def _svg(inner: str) -> dict[str, str]:
    return {
        "type": "svg",
        "html": (
            "<svg viewBox='0 0 200 150' xmlns='http://www.w3.org/2000/svg' "
            "style='font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif'>"
            "<defs>"
            "<linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
            f"<stop offset='0' stop-color='{BLUE}'/>"
            f"<stop offset='1' stop-color='{CYAN}'/>"
            "</linearGradient>"
            "</defs>"
            f"{inner}"
            "</svg>"
        ),
    }


def _frame(title: str, body: str) -> str:
    return (
        "<rect x='12' y='12' width='176' height='126' rx='20' "
        "fill='rgba(0,102,204,0.10)' stroke='rgba(76,201,240,0.50)'/>"
        f"<text x='100' y='34' fill='{TEXT}' font-size='12' font-weight='800' "
        f"text-anchor='middle'>{title}</text>"
        f"{body}"
    )


ALGEBRA_MEDIA_BY_TERM = {
    "Aniq qiymat (x)": _svg(
        _frame(
            "HAQIQIY QIYMAT",
            f"<line x1='32' y1='92' x2='168' y2='92' stroke='{LINE}' stroke-width='3'/>"
            f"<circle cx='112' cy='92' r='8' fill='{GREEN}'/>"
            f"<text x='112' y='78' fill='{TEXT}' font-size='18' font-weight='900' text-anchor='middle'>x</text>"
            f"<text x='100' y='118' fill='{MUTED}' font-size='12' text-anchor='middle'>aniq nuqta</text>",
        )
    ),
    "Taqribiy qiymat (a)": _svg(
        _frame(
            "O'LCHANGAN SON",
            f"<line x1='32' y1='92' x2='168' y2='92' stroke='{LINE}' stroke-width='3'/>"
            f"<circle cx='82' cy='92' r='6' fill='{GREEN}'/>"
            f"<circle cx='122' cy='92' r='8' fill='{ORANGE}'/>"
            f"<text x='82' y='78' fill='{TEXT}' font-size='15' font-weight='800' text-anchor='middle'>x</text>"
            f"<text x='122' y='76' fill='{ORANGE}' font-size='18' font-weight='900' text-anchor='middle'>a</text>"
            f"<text x='100' y='118' fill='{MUTED}' font-size='12' text-anchor='middle'>yaqinlashgan qiymat</text>",
        )
    ),
    "Absolut xatolik": _svg(
        _frame(
            "|x - a|",
            f"<line x1='38' y1='88' x2='162' y2='88' stroke='{LINE}' stroke-width='3'/>"
            f"<circle cx='70' cy='88' r='7' fill='{GREEN}'/>"
            f"<circle cx='130' cy='88' r='7' fill='{ORANGE}'/>"
            f"<path d='M70 105 C86 120 114 120 130 105' fill='none' stroke='{PINK}' stroke-width='3'/>"
            f"<text x='70' y='74' fill='{TEXT}' font-size='15' font-weight='800' text-anchor='middle'>x</text>"
            f"<text x='130' y='74' fill='{ORANGE}' font-size='15' font-weight='800' text-anchor='middle'>a</text>"
            f"<text x='100' y='132' fill='{PINK}' font-size='13' font-weight='800' text-anchor='middle'>masofa</text>",
        )
    ),
    "Nisbiy xatolik (formula)": _svg(
        _frame(
            "ULUSH",
            f"<text x='100' y='69' fill='{TEXT}' font-size='17' font-weight='900' text-anchor='middle'>|x - a|</text>"
            f"<line x1='62' y1='80' x2='138' y2='80' stroke='{CYAN}' stroke-width='3'/>"
            f"<text x='100' y='103' fill='{TEXT}' font-size='17' font-weight='900' text-anchor='middle'>|a|</text>"
            f"<text x='100' y='126' fill='{MUTED}' font-size='12' text-anchor='middle'>xato / o'lchov</text>",
        )
    ),
    "Foizga aylantirish": _svg(
        _frame(
            "FOIZ TILI",
            f"<text x='55' y='78' fill='{TEXT}' font-size='18' font-weight='900' text-anchor='middle'>&delta;</text>"
            f"<path d='M72 73 H126' stroke='{CYAN}' stroke-width='4' stroke-linecap='round'/>"
            f"<text x='150' y='78' fill='{GREEN}' font-size='18' font-weight='900' text-anchor='middle'>%</text>"
            f"<text x='100' y='111' fill='{TEXT}' font-size='18' font-weight='900' text-anchor='middle'>&times; 100%</text>"
        )
    ),
    "Aniqroq o'lchov qoidasi": _svg(
        _frame(
            "KICHIK % = ANIQROQ",
            f"<rect x='46' y='66' width='38' height='18' rx='7' fill='{GREEN}' opacity='0.95'/>"
            f"<rect x='46' y='96' width='92' height='18' rx='7' fill='{ORANGE}' opacity='0.95'/>"
            f"<text x='91' y='80' fill='{TEXT}' font-size='12' font-weight='800'>0.33%</text>"
            f"<text x='145' y='110' fill='{TEXT}' font-size='12' font-weight='800'>0.47%</text>"
        )
    ),
    "Yaxlitlash": _svg(
        _frame(
            "YAXLITLASH",
            f"<line x1='34' y1='92' x2='166' y2='92' stroke='{LINE}' stroke-width='3'/>"
            f"<circle cx='92' cy='92' r='7' fill='{ORANGE}'/>"
            f"<circle cx='128' cy='92' r='7' fill='{GREEN}'/>"
            f"<path d='M96 70 C108 56 126 60 130 78' fill='none' stroke='{CYAN}' stroke-width='3'/>"
            f"<text x='92' y='118' fill='{ORANGE}' font-size='12' font-weight='800' text-anchor='middle'>3.45</text>"
            f"<text x='128' y='118' fill='{GREEN}' font-size='12' font-weight='800' text-anchor='middle'>3</text>",
        )
    ),
    "Teskari masala": _svg(
        _frame(
            "ORQAGA HISOB",
            f"<text x='100' y='64' fill='{TEXT}' font-size='15' font-weight='900' text-anchor='middle'>absolut xato</text>"
            f"<text x='100' y='91' fill='{CYAN}' font-size='18' font-weight='900' text-anchor='middle'>= &delta; &times; |a|</text>"
            f"<text x='100' y='120' fill='{MUTED}' font-size='12' text-anchor='middle'>nisbiydan masofaga</text>",
        )
    ),
    "Aniqlik chegarasi": _svg(
        _frame(
            "a +/- h",
            f"<line x1='42' y1='91' x2='158' y2='91' stroke='{LINE}' stroke-width='3'/>"
            f"<rect x='66' y='79' width='68' height='24' rx='12' fill='{BLUE}' opacity='0.24' stroke='{CYAN}'/>"
            f"<circle cx='100' cy='91' r='7' fill='{ORANGE}'/>"
            f"<text x='66' y='120' fill='{MUTED}' font-size='12' text-anchor='middle'>a-h</text>"
            f"<text x='100' y='72' fill='{ORANGE}' font-size='15' font-weight='900' text-anchor='middle'>a</text>"
            f"<text x='134' y='120' fill='{MUTED}' font-size='12' text-anchor='middle'>a+h</text>",
        )
    ),
    "Yer va o'q misoli": _svg(
        _frame(
            "KATTA SON, KICHIK XATO",
            f"<circle cx='70' cy='87' r='28' fill='{BLUE}' opacity='0.35' stroke='{CYAN}' stroke-width='3'/>"
            f"<path d='M48 87 C58 74 80 74 92 88' fill='none' stroke='{GREEN}' stroke-width='2'/>"
            f"<rect x='125' y='80' width='36' height='14' rx='7' fill='{ORANGE}'/>"
            f"<path d='M161 87 L174 80 L174 94 Z' fill='{ORANGE}'/>"
            f"<text x='70' y='124' fill='{TEXT}' font-size='12' font-weight='800' text-anchor='middle'>Yer</text>"
            f"<text x='148' y='124' fill='{TEXT}' font-size='12' font-weight='800' text-anchor='middle'>o'q</text>",
        )
    ),
}


GEOMETRY_MEDIA_BY_TERM = {
    "Asosiy ayniyat (eslatma)": _svg(
        _frame(
            "sin^2 a + cos^2 a = 1",
            f"<polygon points='42,116 158,116 158,38' fill='rgba(0,102,204,0.12)' stroke='{LINE}' stroke-width='3'/>"
            f"<polyline points='145,116 145,103 158,103' fill='none' stroke='{CYAN}' stroke-width='2'/>"
            f"<text x='101' y='130' fill='{GREEN}' font-size='12' font-weight='800' text-anchor='middle'>cos a</text>"
            f"<text x='170' y='78' fill='{ORANGE}' font-size='12' font-weight='800' text-anchor='middle' transform='rotate(-90 170 78)'>sin a</text>"
            f"<text x='111' y='75' fill='{TEXT}' font-size='12' font-weight='800' text-anchor='middle'>1</text>"
            f"<text x='56' y='109' fill='{TEXT}' font-size='14' font-weight='900'>a</text>",
        )
    ),
    "Co-funksiya almashinuvi (mnemonik)": _svg(
        _frame(
            "90 - a",
            f"<text x='61' y='72' fill='{TEXT}' font-size='17' font-weight='900' text-anchor='middle'>sin</text>"
            f"<text x='139' y='72' fill='{TEXT}' font-size='17' font-weight='900' text-anchor='middle'>cos</text>"
            f"<path d='M80 67 H120' stroke='{CYAN}' stroke-width='4' stroke-linecap='round'/>"
            f"<path d='M120 86 H80' stroke='{CYAN}' stroke-width='4' stroke-linecap='round'/>"
            f"<text x='61' y='115' fill='{TEXT}' font-size='17' font-weight='900' text-anchor='middle'>tg</text>"
            f"<text x='139' y='115' fill='{TEXT}' font-size='17' font-weight='900' text-anchor='middle'>ctg</text>"
            f"<path d='M80 110 H120' stroke='{ORANGE}' stroke-width='4' stroke-linecap='round'/>"
            f"<path d='M120 129 H80' stroke='{ORANGE}' stroke-width='4' stroke-linecap='round'/>",
        )
    ),
}


def _with_media(card: dict[str, Any], media: dict[str, str]) -> dict[str, Any]:
    new_card = copy.deepcopy(card)
    new_card["media"] = media
    return new_card


def polish_algebra_flashcards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    polished: list[dict[str, Any]] = []
    for card in cards:
        term = card.get("term", "")
        if term == "Bobil ildizi":
            card = {
                "term": "Aniqlik chegarasi",
                "def": "x = a +/- h ko'rinishida haqiqiy qiymat a-h va a+h oralig'ida yotadi.",
                "cluster": "QOIDA",
            }
            term = card["term"]
        media = ALGEBRA_MEDIA_BY_TERM.get(term)
        polished.append(_with_media(card, media) if media else copy.deepcopy(card))
    return polished


def polish_geometry_flashcards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    polished: list[dict[str, Any]] = []
    for card in cards:
        media = GEOMETRY_MEDIA_BY_TERM.get(card.get("term", ""))
        if media and not card.get("media"):
            polished.append(_with_media(card, media))
        else:
            polished.append(copy.deepcopy(card))
    return polished


def polish_content(hw_id: str, content: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(content)
    cards = updated.get("flashcards")
    if not isinstance(cards, list):
        return updated
    if hw_id == ALGEBRA_HW_ID:
        updated["flashcards"] = polish_algebra_flashcards(cards)
    elif hw_id == GEOMETRY_HW_ID:
        updated["flashcards"] = polish_geometry_flashcards(cards)
    return updated


def _request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def apply_to_api(base_url: str, apply: bool) -> list[dict[str, Any]]:
    base = base_url.rstrip("/")
    results: list[dict[str, Any]] = []
    for hw_id in (ALGEBRA_HW_ID, GEOMETRY_HW_ID):
        hw = _request_json("GET", f"{base}/api/homeworks/{hw_id}")
        content = hw.get("content_json") or {}
        updated = polish_content(hw_id, content)
        before_cards = content.get("flashcards") if isinstance(content.get("flashcards"), list) else []
        after_cards = updated.get("flashcards") if isinstance(updated.get("flashcards"), list) else []
        before_media = sum(1 for card in before_cards if card.get("media"))
        after_media = sum(1 for card in after_cards if card.get("media"))
        changed = updated != content
        if apply and changed:
            _request_json("PUT", f"{base}/api/homeworks/{hw_id}", {"content_json": updated})
        results.append(
            {
                "id": hw_id,
                "changed": changed,
                "before_media": before_media,
                "after_media": after_media,
                "applied": apply and changed,
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--apply", action="store_true", help="write updates through the local API")
    args = parser.parse_args()

    try:
        results = apply_to_api(args.base_url, args.apply)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {args.base_url}: {exc}") from exc

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not args.apply:
        print("Dry run only. Re-run with --apply to write the content_json changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
