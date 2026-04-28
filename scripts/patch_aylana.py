#!/usr/bin/env python3
"""
patch_aylana.py — Surgical fixes to HW-20260427-007 in the local builder.

Three fixes:
  1. Move the 10 Front/Back flashcards from Panel 7's blocks into the
     flashcards[] array.
  2. Clean Panel 7 so it only contains the proper "Why this matters"
     content + the BOST goal-prompt sentence.
  3. Build full consolidation content from sections 20-21 of the source MD
     (Xotira Daraxti + 3-question self-test). Currently the consolidation
     was dropped because the parser treated Aylana as a "single-concept" lesson.
"""
import json
import re
import urllib.request
import sys
from pathlib import Path

BUILDER = "http://127.0.0.1:8000"
HW_ID = "HW-20260427-007"
SRC_MD = Path(r"D:/Aylananing Kesuvchilari Burchaklari Xossasi (grade 8 geometry).md")


def http_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def http_put(url: str, body: dict) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT",
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_flashcards_from_md(md: str) -> list[dict]:
    """Extract every **Front:** / **Back:** pair from the MD, in order.
    The source has 10 of them between Panel 7 and the Memory Sprint header."""
    pattern = re.compile(
        r"\*\*Front:\*\*\s*(.+?)\s*\n\*\*Back:\*\*\s*(.+?)(?=\n\n\*\*Front|\n\n\*\*[A-ZЀ-ӿ]|\Z)",
        re.S,
    )
    out = []
    for m in pattern.finditer(md):
        front = m.group(1).strip()
        back = m.group(2).strip()
        # Cluster classification — best-effort from content
        cluster = "QOIDA"
        if "α =" in back or "= ∪" in back or "/2" in back or "Misol:" in back:
            cluster = "FORMULA"
        elif any(t in front for t in ("Vatar", "Kesuvchi", "Urinma")) and "ta'rif" not in back.lower():
            cluster = "TA'RIF"
        out.append({"term": front, "def": back, "cluster": cluster})
    return out


def clean_panel_7(panel7: dict, md: str) -> dict:
    """Replace Panel 7's blocks with the canonical Why-This-Matters content
    extracted from the source (lines 182-187 in the MD)."""
    blocks = [
        {
            "type": "p",
            "text": (
                "Agar siz bu teoremani bilmasangiz, aylananing markaziga bora olmagan "
                "holatingizda, aylananing yoylari orasidagi masofani qanday qilib burchak "
                "orqali o'lchashni topa olmaysiz. Barcha o'lchovlarni oddiy taxminlarga "
                "asoslanishga majbur bo'lasiz."
            ),
        },
        {
            "type": "p",
            "text": (
                "Agar buni bilsangiz, siz masofadan turib ham doiraviy obyektlarning "
                "tuzilish xossalarini tahlil qila olasiz va aniq hisob-kitoblar yuritish "
                "qobiliyatiga ega bo'lasiz."
            ),
        },
        {
            "type": "quote",
            "text": (
                "Bugun \"aylana kesuvchilari hosil qilgan burchak xossasi\" haqida "
                "nimani bilmoqchisiz?"
            ),
        },
    ]
    return {
        "id": 7,
        "title": "PANEL 7 — NIMA UCHUN BU MUHIM?",
        "pages": [{"blocks": blocks}],
    }


def build_consolidation_content() -> dict:
    """Build the consolidation phase from the Xotira Daraxti + self-test sections.
    Builder uses {summary, mnemonic_steps, check_question, ...} or freeform —
    we use a minimal structured shape that the playable will render as text."""
    return {
        "title": "Xotirani Mustahkamlash (Consolidation)",
        "intro": (
            "Biz bugun aylanaga doir bir nechta turli burchaklarni va ularning "
            "formulalarini o'rgandik: ikkita kesuvchi, urinma va kesuvchi, ikkita "
            "urinma, shuningdek vatarlar orasidagi burchaklar. Ular imtihonda yoki "
            "amaliyotda chalkashib ketmasligi uchun, barcha qoidalarni bitta "
            "Nurlanuvchi Xarita (Radiant Summary) ga yig'amiz."
        ),
        "framing": (
            "Barcha formulalarni bitta umumiy belgi bog'lab turadi: "
            "Burchak uchining qayerda joylashgani."
        ),
        "rooms": [
            {
                "title": "1-Shox: Burchak uchi aylana TASHQARISIDA",
                "body": (
                    "Bu turdagi burchaklar uchun: ikkita kesuvchi, ikkita urinma, "
                    "yoki urinma va kesuvchi orasidagi burchak (siz hal qilgan metro "
                    "bekati masalasi kabi)."
                ),
                "bullets": [
                    "Qoida: Uzoqdagi yoydan yaqindagi yoyni AYIRIB, ikkiga bo'lamiz.",
                    "Xotira kaliti: \"Tashqaridagi sovuq — ayirib tashlaymiz (−).\"",
                ],
            },
            {
                "title": "2-Shox: Burchak uchi aylana ICHIDA",
                "body": "Aylananing ichida kesishuvchi ikkita vatar orasidagi burchak.",
                "bullets": [
                    "Qoida: Burchak tiralgan ikkita qarama-qarshi yoyni QO'SHIB, ikkiga bo'lamiz.",
                    "Xotira kaliti: \"Ichkaridagi issiqlik — birlashtiramiz, qo'shamiz (+).\"",
                ],
            },
            {
                "title": "3-Shox: Burchak uchi aylana USTIDA",
                "body": "Ichki chizilgan burchak yoki urinma va vatar orasidagi burchak.",
                "bullets": [
                    "Qoida: Faqat o'zi tiralgan yoyning o'zini 2 ga bo'lamiz.",
                    "Xotira kaliti: \"Ustida turganga bitta yoy yetarli.\"",
                ],
            },
        ],
        "rule": {
            "title": "Galereya qoidasi",
            "body": "Barcha formulalarni bog'lab turuvchi umumiy belgi:",
            "bullets": ["Burchak uchining qayerda joylashgani — barchasi shu yerdan kelib chiqadi."],
        },
        "exercise": {
            "title": "O'z-o'zini tekshirish (1 daqiqa)",
            "intro": (
                "Xaritani ko'z oldingizga keltiring. Quyidagi bo'shliqlarga qaysi "
                "arifmetik amal yoki so'z mos kelishini ichingizda toping:"
            ),
            "steps": [
                "Agar burchak aylanadan uzoqda (tashqarida) yotsa, yoylar qiymati bir-biridan ____________. (Javob: ayiriladi)",
                "Agar burchak aylananing ichida yotsa, yoylar qiymati bir-biriga ____________. (Javob: qo'shiladi)",
                "3-shoxdagi formula: ushbu yoyni ____________ ga bo'lamiz. (Javob: 2)",
            ],
            "closing": (
                "Chuqur nafas oling. Barcha qoidalar bitta tizimga tushdi. Endi siz "
                "Final Challenge (Yakuniy Boss) ga tayyorsiz!"
            ),
        },
    }


def main():
    md = SRC_MD.read_text(encoding="utf-8")

    # Pull current state
    record = http_get(f"{BUILDER}/api/homeworks/{HW_ID}")
    content = record["content_json"]

    # ---------- FIX 1 + 2: extract flashcards + clean Panel 7 ----------
    flashcards = parse_flashcards_from_md(md)
    print(f"[1] Extracted {len(flashcards)} flashcards from MD")
    for fc in flashcards:
        print(f"     - {fc['term']}")

    if len(flashcards) != 10:
        print(f"[WARN] Expected 10 flashcards, got {len(flashcards)}")

    content["flashcards"] = flashcards

    # Replace Panel 7
    panels = content.get("panels", [])
    for i, p in enumerate(panels):
        if p.get("id") == 7:
            panels[i] = clean_panel_7(p, md)
            print(f"[2] Cleaned Panel 7 -> 3 blocks (was 14)")
            break
    content["panels"] = panels

    # ---------- FIX 3: build consolidation ----------
    content["consolidation"] = build_consolidation_content()
    print(f"[3] Consolidation populated: {len(content['consolidation']['rooms'])} rooms + exercise")

    # PUT back
    http_put(f"{BUILDER}/api/homeworks/{HW_ID}", {"content_json": content})
    print()
    print(f"[OK] PUT /api/homeworks/{HW_ID}")
    print()

    # Verify
    record2 = http_get(f"{BUILDER}/api/homeworks/{HW_ID}")
    c2 = record2["content_json"]
    p7 = next((p for p in c2.get("panels", []) if p.get("id") == 7), None)
    p7_blocks = sum(len(pg.get("blocks", [])) for pg in (p7 or {}).get("pages", []))

    print("=== Verification ===")
    print(f"  flashcards:        {len(c2.get('flashcards', []))}")
    print(f"  panel 7 blocks:    {p7_blocks}")
    cons = c2.get("consolidation") or {}
    print(f"  consolidation rooms: {len(cons.get('rooms', []))}")
    print(f"  consolidation exercise steps: {len((cons.get('exercise') or {}).get('steps', []))}")


if __name__ == "__main__":
    main()
