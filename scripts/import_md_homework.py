#!/usr/bin/env python3
"""
import_md_homework.py — Parse a generated MD homework into the builder's
content_json shape, then POST it to a running builder via /api/homeworks
+ PUT the content. Optional --deploy chains to /api/deploy.

Usage:
  python scripts/import_md_homework.py --md "path/to/homework.md" \
      --title "Aylana kesuvchilar" --subject geometriya-g7-11 --grade 8 --mode hard \
      --builder http://127.0.0.1:8000 [--deploy] [--port 5071]

Notes:
- Section boundaries: the MD is split on lines containing only '---'.
- Best-effort extraction. Sections that don't fit a known shape go into the
  closest panel as raw blocks. Notebook Capture (when 'Notebook Capture' or
  'rasmga oling' appears in a question) sets capture=true for that question.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


# -------------------- helpers --------------------

def split_sections(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"\n-{3,}\n", text) if s.strip()]


def extract_svgs(block: str) -> tuple[str, list[str]]:
    """Pull SVG fenced code-blocks out and replace each with a placeholder
    that's guaranteed to be on its own line with blank lines around it,
    so paragraph splitting later picks it up as a standalone block."""
    svgs: list[str] = []
    def _grab(m):
        svgs.append(m.group(1).strip())
        return f"\n\n[[SVG_{len(svgs)-1}]]\n\n"
    cleaned = re.sub(r"```svg\s*(.+?)```", _grab, block, flags=re.S)
    return cleaned, svgs


def _strip_inline_brackets(text: str) -> str:
    """Strip [Diagram ...:] / [Isbot xaritasi:] / [Chizma qoidasi: ...] / [State N: ...]
    brackets which are metadata for the builder/AI, not student-visible content.
    Preserves brief inline parentheticals."""
    # Multi-line brackets: [Anything: ... ] possibly spanning lines
    text = re.sub(r"\[\s*(Diagram[^\]]*|Diagramma[^\]]*|Isbot xaritasi[^\]]*|Chizma qoidasi[^\]]*|State \d+[^\]]*)\]",
                  "", text, flags=re.S)
    # Collapse triple+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# Heuristic Uzbek "callout starter" phrases — when a paragraph starts with
# one of these, render as a callout block rather than plain paragraph.
_CALLOUT_STARTERS = (
    "sodda so'zlar bilan",
    "sodda soʻzlar bilan",
    "sodda tilda",
    "sodda sozlar bilan",  # ASCII-ized fallback
    "eslatma:",
    "diqqat:",
    "muhim eslatma",
)


def _is_callout(para: str) -> bool:
    head = para.strip().lower()[:40]
    return any(head.startswith(s) for s in _CALLOUT_STARTERS)


def md_blocks_from_text(text: str, svgs: list[str]) -> list[dict]:
    """Convert plain-text body into builder-style blocks.
    Builder block types: h1/h2/p/quote/ul/ol/svg/callout.
    """
    text = _strip_inline_brackets(text)
    blocks: list[dict] = []
    # Split on double-newline AND on SVG placeholder boundaries
    paragraphs = re.split(r"\n\n+", text.strip())
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Inline SVG placeholders — split paragraph on them and emit each part
        if "[[SVG_" in para:
            parts = re.split(r"(\[\[SVG_\d+\]\])", para)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                m = re.match(r"\[\[SVG_(\d+)\]\]$", part)
                if m:
                    idx = int(m.group(1))
                    if idx < len(svgs):
                        blocks.append({"type": "svg", "html": svgs[idx]})
                else:
                    if _is_callout(part):
                        # Strip leading marker like "Sodda so'zlar bilan:"
                        body = re.sub(r"^[Ss]odda[^:]*:\s*", "", part)
                        body = re.sub(r"^(Eslatma|Diqqat|Muhim[^:]*):\s*", "", body)
                        # Builder preview template handles 'quote' but not
                        # 'callout' — emit quote so previews don't crash.
                        blocks.append({"type": "quote", "text": body})
                    else:
                        blocks.append({"type": "p", "text": part})
            continue

        # Bullet list
        if re.match(r"^[*\-]\s+", para.split("\n")[0]):
            items = [re.sub(r"^[*\-]\s+", "", ln) for ln in para.split("\n") if ln.strip()]
            blocks.append({"type": "ul", "items": items})
            continue

        # Numbered list
        if re.match(r"^\d+\.\s+", para.split("\n")[0]):
            items = [re.sub(r"^\d+\.\s+", "", ln) for ln in para.split("\n") if ln.strip()]
            blocks.append({"type": "ol", "items": items})
            continue

        # Bold subsection header: **1-Misol: ...** / **Topish kerak: ...**
        m = re.match(r"^\*\*(.+?)\*\*\s*$", para)
        if m and len(m.group(1)) < 100:
            blocks.append({"type": "h2", "text": m.group(1).strip()})
            continue

        # Callout — emitted as 'quote' (builder preview supports quote, not callout)
        if _is_callout(para):
            body = re.sub(r"^[Ss]odda[^:]*:\s*", "", para)
            body = re.sub(r"^(Eslatma|Diqqat|Muhim[^:]*):\s*", "", body)
            blocks.append({"type": "quote", "text": body})
            continue

        # Heading-ish (single short line ending with colon)
        if re.match(r"^[Ѐ-ӿA-Za-z][^\n]{1,80}:$", para) and len(para) < 80:
            blocks.append({"type": "h2", "text": para.rstrip(":")})
            continue

        # Default to paragraph
        blocks.append({"type": "p", "text": para})
    return blocks


def parse_panel(section: str, panel_id: int) -> dict:
    """A preview panel — first non-empty line is the title; everything after that
    line is the body. Blank-line paragraph separators are PRESERVED."""
    cleaned, svgs = extract_svgs(section)
    lines = cleaned.splitlines()
    title = ""
    body_start = 0
    for i, ln in enumerate(lines):
        if ln.strip():
            title = ln.strip()
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:])  # keep blank lines intact
    blocks = md_blocks_from_text(body, svgs)
    return {
        "id": panel_id,
        "title": f"PANEL {panel_id} — {title.upper()}",
        "pages": [{"blocks": blocks}],
    }


def parse_memory_sprint_item(section: str) -> dict | None:
    """Each section here looks like:
       **N. Type ...** [Bloom: ...]
       prompt text
       Options:
       * A) ...
       * B) ... ✓
       ...
       *Izoh:* explanation
    """
    cleaned, svgs = extract_svgs(section)
    text = cleaned.strip()

    # Type detection
    if "(MC)" in text or "Multiple Choice" in text:
        kind = "KO"  # builder uses KO=multiple-choice
    elif "(T/F)" in text or "True / False" in text:
        kind = "TF"
    elif "(YNNG)" in text or "Yes / No / Not Given" in text:
        kind = "YNNG"
    else:
        kind = "KO"

    # Tags
    tag_match = re.search(r"`?\[Bloom:.*?\]`?", text)
    tags = tag_match.group(0).strip("`") if tag_match else ""

    # Prompt: first non-bold non-bullet lines after the title
    body_lines = [ln for ln in text.splitlines()[1:] if ln.strip()]
    prompt_lines = []
    for ln in body_lines:
        if ln.lstrip().startswith(("*", ">", "Variantlar", "Javob")) or ln.strip().startswith("**"):
            break
        prompt_lines.append(ln)
    prompt = " ".join(prompt_lines).strip()
    # Inline any SVGs into the prompt as raw HTML — frontend renders them
    if svgs:
        for svg in svgs:
            prompt += f"<br><div class='svg-wrap' style='display:inline-block;max-width:240px'>{svg}</div>"
    # Strip remaining placeholder tokens
    prompt = re.sub(r"\[\[SVG_\d+\]\]", "", prompt).strip()
    if not prompt:
        return None

    # Options: support both bullet (`* X`) and lettered (`A) X`) formats
    options: list[str] = []
    correct_idx = 0
    for ln in body_lines:
        # Skip the "Javob izohi" / explanation line
        if re.search(r"\*\*?\s*(Javob\s*izohi|Izoh)\s*\*?\*?\s*:", ln, re.I):
            continue
        # Bullet style: "* opt" or "- opt"
        m = re.match(r"^[*\-]\s+(.+?)(\s*✓|\s*\(to‘gri\)|\s*\(toʻgʻri\)|)?\s*$", ln)
        # Lettered style: "A) opt", "B) opt"
        if not m:
            m = re.match(r"^\s*([A-DTFNG]+|\d+)\)\s+(.+?)(\s*✓|\s*\(to‘gri\)|\s*\(toʻgʻri\)|)?\s*$", ln)
            if m:
                opt = m.group(2).strip()
                if "✓" in opt or "✓" in ln:
                    correct_idx = len(options)
                    opt = opt.replace("✓", "").strip()
                options.append(opt)
                continue
        if m:
            opt = m.group(1).strip()
            if "✓" in opt or "✓" in ln:
                correct_idx = len(options)
                opt = opt.replace("✓", "").strip()
            options.append(opt)

    # Heuristic: if YNNG/TF and no options found, supply defaults
    if not options:
        if kind == "TF":
            options = ["To'g'ri", "Noto'g'ri"]
        elif kind == "YNNG":
            options = ["Ha", "Yo'q", "Aytilmagan"]

    # Explanation: try multiple keyword variants
    expl_match = re.search(
        r"\*\*?\s*(?:Javob\s*izohi|Izoh|Tushuntirish)\s*\*?\*?\s*:?\s*(.+?)(?:\n\n|\Z)",
        text, re.S | re.I,
    )
    explain = expl_match.group(1).strip() if expl_match else ""

    return {
        "type": kind,
        "prompt": prompt,
        "subtitle": "",
        "tags": tags,
        "explain": explain,
        "options": options,
        "correct": correct_idx,
    }


def parse_adaptive_quiz(section: str) -> list[dict]:
    """Parse Adaptive Quiz, preserving inline SVGs in each question's text."""
    items: list[dict] = []
    parts = re.split(r"\*\*\d+-Savol\b[^*]*\*\*", section)
    headers = re.findall(r"\*\*(\d+-Savol[^*]*)\*\*\s*(`\[Bloom[^`]*\]`)?", section)
    for i, header in enumerate(headers):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        body = body.strip()
        if not body:
            continue
        # Per-question SVG extraction
        body_clean, body_svgs = extract_svgs(body)
        # Detect tier
        tier_match = re.search(r"(Oson|Oʻrta|Qiyin|Easy|Medium|Hard)", header[0])
        tier_label = (tier_match.group(1) if tier_match else "").lower()
        tier = "EASY" if "oson" in tier_label or "easy" in tier_label else \
               "HARD" if "qiyin" in tier_label or "hard" in tier_label else "MEDIUM"
        capture = bool(re.search(r"Notebook Capture|rasmga oling|daftarga", body_clean, re.I))
        # Strip helper-italics tail and remaining placeholders
        q_text = re.sub(r"\*Javobingizni.*$", "", body_clean, flags=re.S).strip()
        q_text = re.sub(r"\[\[SVG_\d+\]\]", "", q_text).strip()
        # Append SVG below the question text
        for svg in body_svgs:
            q_text += f"<br><div class='svg-wrap' style='max-width:300px'>{svg}</div>"
        items.append({
            "q": q_text,
            "tags": header[1].strip("`") if header[1] else "",
            "tier": tier,
            "ans": [""],
            "capture": capture,
            "answer_spec": {
                "type": "semantic",
                "expected": "",
                "canonical_display": "",
                "allow_ai_fallback": True,
            },
        })
    return items


def parse_tile_match(section: str) -> list[list[str]]:
    pairs: list[list[str]] = []
    # Each pair block: **N-Juftlik** ... * (Chap) X * (O'ng) Y
    blocks = re.split(r"\*\*\d+-Juftlik\b[^*]*\*\*", section)[1:]
    for blk in blocks:
        chap = re.search(r"\(Chap\)\s*(.+?)(?:\n|$)", blk)
        ong = re.search(r"\(O‘ng\)\s*(.+?)(?:\n|$)", blk)
        if not ong:
            ong = re.search(r"\(O'ng\)\s*(.+?)(?:\n|$)", blk)
        if chap and ong:
            pairs.append([chap.group(1).strip(), ong.group(1).strip()])
    return pairs


def parse_sentence_fill(section: str) -> list[dict]:
    items: list[dict] = []
    # Each: **N-Band** [tags]\n sentence with ___ \n Variantlar: [...] \n *(To'g'ri javob: X)*
    blocks = re.split(r"\*\*\d+-Band\b[^*]*\*\*", section)[1:]
    headers = re.findall(r"\*\*(\d+-Band[^*]*)\*\*\s*(`\[Bloom[^`]*\]`)?", section)
    for i, blk in enumerate(blocks):
        sentence = re.split(r"\*\s*Variantlar:", blk)[0].strip()
        ans_match = re.search(r"To‘?gri javob:\s*([^)\n]+)", blk)
        if not ans_match:
            ans_match = re.search(r"javob:\s*([^)\n]+)", blk, re.I)
        ans = ans_match.group(1).strip().rstrip(")") if ans_match else ""
        items.append({
            "q": sentence,
            "tags": headers[i][1].strip("`") if i < len(headers) and headers[i][1] else "",
            "inv": ans,
            "reprompts": [],
        })
    return items


def parse_real_life(*sections: str) -> dict:
    """Combine the W5H, project diagram, and engineering tasks sections.
    Extracts the first SVG as setup_svg for the playable runtime."""
    full = "\n\n".join(sections)
    cleaned, svgs = extract_svgs(full)
    cleaned = re.sub(r"\[\[SVG_\d+\]\]", "", cleaned)

    badge_match = re.search(r"Sizning Ralingiz[:\s]*\*\*?(.+?)\*\*?\.?\n", cleaned)
    badge = "Real-Life Challenge"
    if badge_match:
        badge = badge_match.group(1).strip()

    story_match = re.search(r"(Vazifangiz[\s\S]+?)(?=\n###|\n\*\*\d+-Topshiriq|\Z)", cleaned)
    story = story_match.group(1).strip() if story_match else cleaned[:1500].strip()

    items: dict[str, dict] = {}
    task_pattern = re.compile(
        r"\*\*(\d+)[\.\-]\s*([^*]*)\*\*\s*\n(.+?)(?=\n\*\*\d+[\.\-]|\Z)",
        re.S,
    )
    for m in task_pattern.finditer(cleaned):
        idx = m.group(1)
        sub_title = m.group(2).strip().rstrip(":")
        body = m.group(3).strip()
        capture = bool(re.search(r"rasmga|Notebook Capture|fotosur", body, re.I))
        items[f"q{idx}"] = {
            "prompt": (f"**{sub_title}**\n\n" + body) if sub_title else body,
            "ans": "",
            "fb": "",
            "capture": capture,
        }

    if not items:
        numbered = re.findall(r"^\s*(\d+)\.\s*(.+?)(?=^\s*\d+\.|\Z)", cleaned, re.M | re.S)
        for idx, body in numbered[:6]:
            items[f"q{idx}"] = {"prompt": body.strip(), "ans": "", "fb": "", "capture": False}

    if not items:
        items["q1"] = {"prompt": story, "ans": "", "fb": "", "capture": False}

    return {
        "badge": badge,
        "story": story,
        "setup_svg": svgs[0] if svgs else "",  # first SVG = setup diagram
        "extra_svgs": svgs[1:],                 # any additional context diagrams
        **items,
        "endTitle": "Yakuniy",
        "endSub": "Vazifa yakunlandi",
    }


def parse_boss_question(section: str) -> dict | None:
    cleaned, svgs = extract_svgs(section)
    lines = cleaned.splitlines()
    if not lines:
        return None
    title_line = lines[0]
    # Damage by difficulty word
    dmg = 10
    if re.search(r"Oʻrta|O'rta|Medium", title_line, re.I):
        dmg = 20
    elif re.search(r"Qiyin|Hard", title_line, re.I):
        dmg = 30
    body = "\n".join(lines[1:]).strip()
    body = re.sub(r"\[\[SVG_\d+\]\]", "", body).strip()
    tag_match = re.search(r"`\[Bloom[^`]*\]`", cleaned)
    tags = tag_match.group(0).strip("`") if tag_match else ""
    hint_match = re.search(r"(Hint|Yordam|Maslahat)[^\n]*[:\-]\s*(.+)", cleaned, re.I)
    hint = hint_match.group(2).strip() if hint_match else ""

    return {
        "q": body,
        "tags": tags,
        "ans": [],
        "hint": hint,
        "dmg": dmg,
        "svg": svgs[0] if svgs else "",  # first SVG = visual aid for the boss item
        "answer_spec": {
            "type": "semantic",
            "expected": "",
            "canonical_display": "",
            "allow_ai_fallback": True,
        },
    }


# -------------------- main --------------------

PANEL_TITLES = [
    "Xulosa", "Yaxshiroq tushuntirish", "Kelib chiqishi",
    "Misollar", "Chizma → Teorema Tarjimasi", "Sanoatdagi qo'llanilishi", "Nima uchun bu muhim?"
]


def parse_md(md_text: str, title: str) -> dict:
    sections = split_sections(md_text)

    panels = []
    # First 7 sections become panels
    for i, sec in enumerate(sections[:7]):
        panels.append(parse_panel(sec, i + 1))

    # Memory sprint: sections 7..13 (7 items)
    memory_sprint = []
    for i in range(7, min(14, len(sections))):
        item = parse_memory_sprint_item(sections[i])
        if item:
            memory_sprint.append(item)

    # Game breaks: 14, 15, 16
    gb_adaptive = parse_adaptive_quiz(sections[14]) if len(sections) > 14 else []
    gb_memory_match = parse_tile_match(sections[15]) if len(sections) > 15 else []
    gb_why_chain = parse_sentence_fill(sections[16]) if len(sections) > 16 else []

    # Real-life: combine W5H + diagram + tasks (sections 17, 18, 19)
    rl_sections = [sections[i] for i in (17, 18, 19) if i < len(sections)]
    real_life = parse_real_life(*rl_sections) if rl_sections else None

    # Boss questions: 22..26 (5 items)
    boss_questions = []
    for i in range(22, min(27, len(sections))):
        bq = parse_boss_question(sections[i])
        if bq:
            boss_questions.append(bq)

    # Reflection — search the entire MD for a reflection block.
    # NETS reflections start with "Xotima va Xulosa", "Reflection", or "Refleksiya".
    reflection = {
        "summary": "",
        "question": "",
        "spaced_rep": "",
        "closing": "",
    }
    # Find the start of the reflection block anywhere in the document
    reflection_start = re.search(
        r"(?:^|\n)\s*\*?\*?\s*(?:Xotima va Xulosa|Reflection|Refleksiya|Yakuniy xulosa|Xotima)\s*(?:\([^)]*\))?\s*\*?\*?\s*\n",
        md_text,
        re.I,
    )
    if reflection_start:
        rblock = md_text[reflection_start.end():]
        # Extract subsections by their bold-numbered headers
        # Look for "**1. ...**", "**2. ...**", "**3. ...**", "**4. ..."
        def _get_section(num_pattern: str) -> str:
            m = re.search(
                rf"\*\*\s*{num_pattern}[\.\s][^\*]*\*\*\s*\n?(.+?)(?=\n\*\*\s*\d+[\.\s]|\Z)",
                rblock, re.S
            )
            return m.group(1).strip() if m else ""

        reflection["summary"] = _get_section("1")
        reflection["question"] = _get_section("2")
        reflection["spaced_rep"] = _get_section("3")
        reflection["closing"] = _get_section("4")

    flashcards = []  # source MD doesn't include flashcards as a separate section

    return {
        "meta": {
            "title": title,
            "subject_display": "Geometriya",
            "section": "10-§",
            "cefr_level": "",
        },
        "quotes": [],
        "panels": panels,
        "flashcards": flashcards,
        "memory_sprint": memory_sprint,
        "gb_adaptive_quiz": gb_adaptive,
        "gb_why_chain": gb_why_chain,
        "gb_memory_match": gb_memory_match,
        "real_life": real_life,
        "boss_questions": boss_questions,
        "reflection": reflection,
    }


def http_post(url: str, body: dict) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def http_put(url: str, body: dict) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT",
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--md", type=Path, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--subject", default="geometriya-g7-11")
    p.add_argument("--grade", type=int, default=8)
    p.add_argument("--mode", default="hard")
    p.add_argument("--builder", default="http://127.0.0.1:8000")
    p.add_argument("--deploy", action="store_true")
    p.add_argument("--port", type=int, default=5071)
    p.add_argument("--provider", default="kimi")
    p.add_argument("--out-json", type=Path, help="Write parsed content to this file (debug)")
    args = p.parse_args()

    md_text = args.md.read_text(encoding="utf-8")
    content = parse_md(md_text, args.title)

    # Inject grading config
    content["grading"] = {
        "system": "amr",
        "provider": args.provider,
        "confidence_threshold": 80,
        "boss_hp_override": None,
        "mastery_window": 3,
        "mastery_threshold_proficient": 70,
        "mastery_threshold_mastered": 85,
        "deploy_port": args.port,
    }

    if args.out_json:
        args.out_json.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] Parsed content written to {args.out_json}")

    print(f"Parsed:")
    print(f"  panels:           {len(content['panels'])}")
    print(f"  memory_sprint:    {len(content['memory_sprint'])}")
    print(f"  gb_adaptive_quiz: {len(content['gb_adaptive_quiz'])}")
    print(f"    capture flagged: {sum(1 for q in content['gb_adaptive_quiz'] if q.get('capture'))}")
    print(f"  gb_memory_match:  {len(content['gb_memory_match'])}")
    print(f"  gb_why_chain:     {len(content['gb_why_chain'])}")
    print(f"  real_life q*:     {sum(1 for k in (content.get('real_life') or {}) if k.startswith('q'))}")
    print(f"  boss_questions:   {len(content['boss_questions'])}")

    # POST homework + PUT content
    create_url = args.builder + "/api/homeworks"
    create_body = {
        "title": args.title,
        "subject": args.subject,
        "grade": args.grade,
        "mode": args.mode,
    }
    record = http_post(create_url, create_body)
    hw_id = record["id"]
    print(f"\n[OK] Created: {hw_id}")

    put_url = f"{args.builder}/api/homeworks/{hw_id}"
    record2 = http_put(put_url, {"content_json": content})
    print(f"[OK] Updated content. Has grading: {bool(record2.get('content_json', {}).get('grading'))}")

    if args.deploy:
        print(f"\nDeploying via /api/deploy/{hw_id} ...")
        deploy_url = f"{args.builder}/api/deploy/{hw_id}"
        result = http_post(deploy_url, {"grading": content["grading"]})
        if result.get("ok"):
            print(f"[OK] Deployed to: {result['path']}")
            print(f"     URL: {result['url']}")
        else:
            print(f"[FAIL] Deploy failed: {result.get('error')}")
            print(result.get("details", ""))


if __name__ == "__main__":
    main()
