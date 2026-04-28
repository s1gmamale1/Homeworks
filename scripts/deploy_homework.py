#!/usr/bin/env python3
"""
deploy_homework.py — One-click "build playable homework" tool.

Reads a homework from one of three sources:
  --fixture path/to/file.json    (a fixtures/*.json file or any builder content_json blob)
  --db HW-20260424-003            (an ID from the running builder's SQLite)
  --json -                        (read content_json from stdin, pipe-friendly)

Generates a self-contained runnable directory at <out>/<slug>/ containing:
  server.py            (Flask backend with AMR grading + Kimi/Anthropic auto-detection)
  static/index.html
  static/css/styles.css
  static/js/app.js
  static/js/homework_data.js   (transformed from the builder's content_json)
  .env                 (with KIMI_API_KEY/ANTHROPIC_API_KEY/PORT if --provider given)
  README.md
  requirements.txt

Then optionally boots the server (--boot) and prints the URL.

Usage examples:
  python scripts/deploy_homework.py --fixture fixtures/geometriya-g8-hard.json --out dist
  python scripts/deploy_homework.py --db HW-20260424-003 --out dist --grading amr --provider kimi --port 5060
  cat content.json | python scripts/deploy_homework.py --json - --out dist --boot
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_TEMPLATE = REPO_ROOT / "scripts" / "_runtime_template"


def slugify(text: str) -> str:
    text = (text or "homework").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "homework"


# -------------------- SOURCE LOADING --------------------

def load_from_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_from_db(homework_id: str) -> dict:
    """Load a homework from the builder's SQLite via the existing async db module."""
    sys.path.insert(0, str(REPO_ROOT))
    from server.db import get_homework  # type: ignore

    record = asyncio.run(get_homework(homework_id))
    if not record:
        raise SystemExit(f"Homework {homework_id} not found in DB")
    if not isinstance(record.get("content_json"), dict):
        raise SystemExit(f"Homework {homework_id} has no content_json")
    return record["content_json"] | {
        "_db_meta": {
            "id": record.get("id"),
            "subject": record.get("subject"),
            "grade": record.get("grade"),
            "mode": record.get("mode"),
            "family": record.get("family"),
            "language": record.get("language"),
            "title": record.get("title"),
        }
    }


def load_from_stdin() -> dict:
    return json.loads(sys.stdin.read())


# -------------------- CONTENT MAPPING --------------------
# Map the builder's content_json shape -> the playable HTML's homework_data.js shape.
# The playable shape is the one used by Homeworks/grade8_geometry_pifagor/.

def map_panels(panels: list[dict]) -> list[dict]:
    """Builder panels[].pages[].blocks[] -> playable panels[].blocks[]."""
    out = []
    for p in panels or []:
        flat_blocks = []
        for page in p.get("pages") or []:
            for b in page.get("blocks") or []:
                t = b.get("type", "p")
                if t in ("h1", "h2", "h3", "h"):
                    flat_blocks.append({"type": "h", "text": b.get("text", "")})
                elif t == "p":
                    flat_blocks.append({"type": "p", "text": b.get("text", "")})
                elif t == "quote":
                    flat_blocks.append({"type": "callout", "text": b.get("text", "")})
                elif t == "ul":
                    flat_blocks.append({"type": "ul", "items": b.get("items") or []})
                elif t == "ol":
                    flat_blocks.append({"type": "ol", "items": b.get("items") or []})
                elif t == "svg":
                    flat_blocks.append({"type": "svg", "html": b.get("html", "")})
                elif t == "callout":
                    flat_blocks.append({"type": "callout", "text": b.get("text", ""), "variant": b.get("variant")})
                else:
                    # Unknown type — fall back to paragraph
                    flat_blocks.append({"type": "p", "text": b.get("text", "")})
        out.append({
            "number": p.get("id") or len(out) + 1,
            "title": p.get("title", "").lstrip("PANEL 0123456789— ").strip() or f"Panel {len(out)+1}",
            "blocks": flat_blocks,
        })
    return out


def map_flashcards(cards: list[dict]) -> list[dict]:
    """Builder term/def/cluster -> playable front/back."""
    return [{"front": c.get("term", ""), "back": c.get("def", "")} for c in (cards or [])]


def map_memory_sprint(items: list[dict]) -> dict:
    """Builder type=KO|YNNG|TF -> playable mc/tf/ynng."""
    out_items = []
    for i, it in enumerate(items or []):
        kind = (it.get("type") or "KO").upper()
        opts = it.get("options") or []
        correct_idx = it.get("correct", 0)
        if kind == "KO":
            options = [{"id": chr(65 + j), "text": o} for j, o in enumerate(opts)]
            correct_id = chr(65 + correct_idx) if 0 <= correct_idx < len(options) else "A"
            out_items.append({
                "id": f"MS{i+1}",
                "type": "mc",
                "title": f"{i+1}. {it.get('tags', '')}".strip(),
                "question": it.get("prompt", ""),
                "options": options,
                "correct": correct_id,
                "rationale": it.get("explain", ""),
            })
        elif kind == "YNNG":
            id_map = ["Y", "N", "NG"]
            options = [{"id": id_map[j] if j < 3 else chr(65 + j), "text": o} for j, o in enumerate(opts)]
            correct_id = options[correct_idx]["id"] if 0 <= correct_idx < len(options) else "Y"
            out_items.append({
                "id": f"MS{i+1}",
                "type": "ynng",
                "title": f"{i+1}. {it.get('tags', '')}".strip(),
                "question": it.get("prompt", ""),
                "options": options,
                "correct": correct_id,
                "rationale": it.get("explain", ""),
            })
        elif kind == "TF":
            options = [{"id": "T", "text": opts[0] if opts else "To'g'ri"},
                       {"id": "F", "text": opts[1] if len(opts) > 1 else "Noto'g'ri"}]
            correct_id = options[correct_idx]["id"] if 0 <= correct_idx < len(options) else "T"
            out_items.append({
                "id": f"MS{i+1}",
                "type": "tf",
                "title": f"{i+1}. {it.get('tags', '')}".strip(),
                "question": it.get("prompt", ""),
                "options": options,
                "correct": correct_id,
                "rationale": it.get("explain", ""),
            })
    return {
        "intro": "Memory Sprint — tezkor xotira mashqi. Javobni tanlang.",
        "items": out_items,
    }


def map_game_breaks(content: dict) -> dict:
    """Adapt the 3 game arrays into our games structure.
    gb_adaptive_quiz -> Game 1 (short-answer / rubric items)
    gb_why_chain     -> if non-empty, Game 2 (sentence fill style)
    gb_memory_match  -> Game 3 (tile match)
    """
    games = []

    # Game 1 — Adaptive Quiz
    aq = content.get("gb_adaptive_quiz") or []
    if aq:
        items = []
        for i, q in enumerate(aq):
            spec = q.get("answer_spec") or {}
            grading = "ai_short"
            if q.get("capture") or spec.get("type") in ("semantic", "rubric"):
                grading = "ai_rubric"
            expected = ""
            if isinstance(q.get("ans"), list) and q["ans"]:
                expected = q["ans"][0]
            elif spec.get("expected"):
                expected = spec["expected"]
            items.append({
                "id": f"G1Q{i+1}",
                "question": q.get("q", ""),
                "expected": expected,
                "tags": q.get("tags", ""),
                "grading": grading,
                "notebook": bool(q.get("capture")),
                "notebook_sample": q.get("notebook_sample") or "",
            })
        games.append({
            "id": "G1",
            "title": "1-o'yin: Adaptive Quiz",
            "instructions": "Har bir savolga javob bering. AI baholaydi.",
            "items": items,
        })

    # Game 2 — Why Chain (if present) as Sentence Fill
    wc = content.get("gb_why_chain") or []
    if wc:
        items = []
        for i, q in enumerate(wc):
            items.append({
                "id": f"G2Q{i+1}",
                "question": q.get("q", ""),
                "expected": q.get("inv", ""),
                "tags": q.get("tags", ""),
                "grading": "ai_short",
            })
        games.append({
            "id": "G2",
            "title": "2-o'yin: Sentence Fill",
            "instructions": "Bo'shliqlarni to'ldiring.",
            "items": items,
        })

    # Game 3 — Memory Match -> Tile Match
    mm = content.get("gb_memory_match") or []
    if mm:
        left = []
        right = []
        pairs = {}
        for i, pair in enumerate(mm):
            if isinstance(pair, list) and len(pair) >= 2:
                lid = f"L{i+1}"
                rid = chr(65 + i)
                left.append({"id": lid, "text": pair[0]})
                right.append({"id": rid, "text": pair[1]})
                pairs[lid] = rid
        if left and right:
            games.append({
                "id": "G3",
                "title": "3-o'yin: Tile Match (Memory Match)",
                "instructions": "Chap va o'ng tomondagi mos juftlarni topib bosing.",
                "tags": "",
                "left": left,
                "right": right,
                "correct_pairs": pairs,
                "visual_svg": "",
            })

    return {
        "intro": "Game Breaks — o'yinli mashqlar.",
        "games": games or [{"id": "G0", "title": "(Hech qanday o'yin topilmadi)", "instructions": "", "items": []}],
    }


def _map_consolidation(c: dict | None) -> dict:
    """If the builder has consolidation content, carry it through. Otherwise
    emit the 'skipped' placeholder."""
    if not c or not isinstance(c, dict):
        return {
            "skipped": True,
            "title": "Consolidation o'tkazilmaydi",
            "intro": "Bu darsda Consolidation bosqichi ochilmagan.",
            "framing": "",
            "rooms": [],
            "rule": {"title": "", "body": "", "bullets": []},
            "exercise": {"title": "", "intro": "", "steps": [], "closing": ""},
        }
    # Has actual content — carry it forward
    return {
        "skipped": False,
        "title":   c.get("title", "Xotirani Mustahkamlash"),
        "intro":   c.get("intro", ""),
        "framing": c.get("framing", ""),
        "rooms":   c.get("rooms", []),
        "rule":    c.get("rule", {"title": "", "body": "", "bullets": []}),
        "exercise": c.get("exercise", {"title": "", "intro": "", "steps": [], "closing": ""}),
    }


def map_real_life(rl: dict) -> dict:
    if not rl:
        return None
    items = []
    for key in sorted(k for k in rl.keys() if re.match(r"q\d+$", k)):
        q = rl[key]
        prompt = q.get("prompt", "")
        if "fields" in q:
            field_lines = "\n".join(f"  - {f.get('label', f.get('id', ''))}" for f in q["fields"])
            prompt = f"{prompt}\n\nBu savolda quyidagilarni keltiring:\n{field_lines}"
        items.append({
            "id": key.upper(),
            "question": prompt,
            "tags": q.get("tags", ""),
            "notebook": bool(q.get("capture")),
            "notebook_sample": q.get("notebook_sample") or "",
        })
    extras = rl.get("extra_svgs") or []
    return {
        "title": rl.get("badge") or "Real-Life Challenge",
        "scenario": rl.get("story", ""),
        "setup": "",
        "setup_svg": rl.get("setup_svg") or "",
        "items": items,
        "closing_svg": extras[0] if extras else "",
    }


def map_final_boss(boss: list[dict], grade: int) -> dict:
    """Builder boss_questions[] -> playable final_boss."""
    hp_by_grade = {1: 50, 2: 50, 3: 50, 4: 50, 5: 100, 6: 100, 7: 100, 8: 100, 9: 150, 10: 150, 11: 150}
    hp = hp_by_grade.get(grade, 100)
    items = []
    for i, q in enumerate(boss or []):
        dmg = q.get("dmg", 10)
        difficulty = "easy" if dmg <= 10 else "medium" if dmg <= 20 else "hard"
        hints = []
        if q.get("hint"):
            hints.append(f"Hint 1 (-5 HP): {q['hint']}")
        items.append({
            "id": f"FB{i+1}",
            "title": f"Q{i+1}",
            "tags": q.get("tags", ""),
            "difficulty": difficulty,
            "damage": dmg,
            "question": q.get("q", ""),
            "svg": q.get("svg") or "",  # preserved from parser
            "hints": hints,
            "notebook": bool(q.get("capture")),
        })
    return {
        "title": "Final Challenge (Boss Fight)",
        "intro": f"Bossning umumiy joni — <b>{hp} HP</b>. Har savolga to'g'ri javob berib, HP ni nolga tushiring.",
        "rule": "Barcha javoblar ochiq bo'lishi va yechish bosqichlari ko'rsatilishi shart.",
        "initial_hp": hp,
        "failure_response": '"Hali emas! Yechishni qaytadan ko\'rib chiqing va qo\'llagan qoidangizni aniq nomlang."',
        "victory_response": '"G\'alaba! Boss mag\'lub etildi."',
        "items": items,
    }


def map_reflection(r: dict) -> dict:
    if not r:
        return None
    return {
        "title": "Reflection — Yakuniy xulosa",
        "summary_title": "1. Xulosa",
        "summary": r.get("summary", ""),
        "question_title": "2. Fikrlash uchun savol",
        "question": r.get("question", ""),
        "schedule_title": "3. Takrorlash jadvali",
        "schedule": r.get("spaced_rep", ""),
        "keys_title": "Asosiy tushunchalar:",
        "keys": [],
        "closing_title": "4. Yakunlovchi so'z",
        "closing": r.get("closing", ""),
    }


def transform_content(content: dict) -> dict:
    """Top-level transform: builder content_json -> playable HOMEWORK_DATA shape."""
    db_meta = content.get("_db_meta") or {}
    meta_in = content.get("meta") or {}

    out = {
        "meta": {
            "title": meta_in.get("title") or db_meta.get("title") or "Homework",
            "subject": meta_in.get("subject_display") or db_meta.get("subject") or "",
            "grade": db_meta.get("grade") or 0,
            "section": meta_in.get("section") or "",
            "mode": (db_meta.get("mode") or "hard").upper(),
            "family": db_meta.get("family") or "aniq-fanlar",
        },
        "intro": (content.get("quotes") or [""])[0] if content.get("quotes") else "",
        "panels": map_panels(content.get("panels") or []),
        "flashcards": map_flashcards(content.get("flashcards") or []),
        "memory_sprint": map_memory_sprint(content.get("memory_sprint") or []),
        "game_breaks": map_game_breaks(content),
        "real_life": map_real_life(content.get("real_life") or {}),
        "consolidation": _map_consolidation(content.get("consolidation")),
        "final_boss": map_final_boss(content.get("boss_questions") or [], db_meta.get("grade") or 8),
        "reflection": map_reflection(content.get("reflection") or {}),
    }

    # Carry over any grading config the builder added
    if content.get("grading"):
        out["grading"] = content["grading"]
    return out


# -------------------- DEPLOY --------------------

def find_runtime_template_dir() -> Path:
    """Where to find the runtime stack to copy.

    Priority:
      1. scripts/_runtime_template/  (vendored alongside this script)
      2. ../Class A Education/Homeworks/grade9_geometry_demo1/  (local dev fallback)
    """
    if RUNTIME_TEMPLATE.is_dir() and (RUNTIME_TEMPLATE / "server.py").exists():
        return RUNTIME_TEMPLATE

    fallback = Path("D:/Class A Education/Homeworks/grade9_geometry_demo1")
    if fallback.is_dir() and (fallback / "server.py").exists():
        return fallback

    raise SystemExit(
        "Runtime template not found. Expected at scripts/_runtime_template/ or "
        "D:/Class A Education/Homeworks/grade9_geometry_demo1/. "
        "Run: python scripts/deploy_homework.py --install-template <path-to-grade9_geometry_demo1>"
    )


def install_template(source: Path):
    """Copy a runtime stack into scripts/_runtime_template/ for future deploys."""
    if not source.is_dir():
        raise SystemExit(f"{source} is not a directory")
    if RUNTIME_TEMPLATE.exists():
        shutil.rmtree(RUNTIME_TEMPLATE)
    RUNTIME_TEMPLATE.mkdir(parents=True)
    # Copy server.py, requirements.txt, .env.example, .gitignore, static/
    for f in ("server.py", "requirements.txt", ".env.example", ".gitignore"):
        src = source / f
        if src.is_file():
            shutil.copy2(src, RUNTIME_TEMPLATE / f)
    static_src = source / "static"
    static_dst = RUNTIME_TEMPLATE / "static"
    if static_src.is_dir():
        shutil.copytree(static_src, static_dst)
    print(f"Template installed at {RUNTIME_TEMPLATE}")


def write_homework_data_js(out_path: Path, hw_data: dict):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_blob = json.dumps(hw_data, ensure_ascii=False, indent=2)
    js_content = (
        "// Generated by scripts/deploy_homework.py from builder content_json\n"
        "// Do not edit by hand — regenerate via the deploy CLI.\n\n"
        f"window.HOMEWORK_DATA = {json_blob};\n"
    )
    out_path.write_text(js_content, encoding="utf-8")


def write_env_file(out_path: Path, provider: str, port: int, kimi_key: str | None,
                    anthropic_key: str | None, builder_url: str | None = None,
                    builder_subject: str | None = None, builder_grade: int | None = None):
    lines = [f"PORT={port}"]
    if provider == "builder" and builder_url:
        lines.append(f"BUILDER_URL={builder_url}")
        if builder_subject:
            lines.append(f"BUILDER_SUBJECT={builder_subject}")
        if builder_grade is not None:
            lines.append(f"BUILDER_GRADE={builder_grade}")
    elif provider == "kimi":
        if kimi_key:
            lines.append(f"KIMI_API_KEY={kimi_key}")
        lines.append("KIMI_BASE_URL=https://api.moonshot.ai/v1")
    elif provider == "anthropic":
        if anthropic_key:
            lines.append(f"ANTHROPIC_API_KEY={anthropic_key}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(out_path: Path, hw_data: dict, port: int, provider: str):
    title = hw_data["meta"]["title"]
    grade = hw_data["meta"]["grade"]
    subject = hw_data["meta"]["subject"]
    out_path.write_text(
        f"""# {title}

Generated playable homework — Grade {grade} · {subject}

## Run

```bash
pip install -r requirements.txt
python server.py
```

Open http://127.0.0.1:{port}/ in a browser.

## Provider

Configured: **{provider}**.
{"Set KIMI_API_KEY in .env to enable real grading." if provider == "kimi" else ""}{"Set ANTHROPIC_API_KEY in .env to enable real grading." if provider == "anthropic" else ""}{"Mock mode active — closed phases score correctly, open phases use heuristic. Set KIMI_API_KEY or ANTHROPIC_API_KEY to enable real AI grading." if provider == "mock" else ""}

## Content

Generated from a homework in the NETS builder. Phases produced:
- Preview ({len(hw_data.get("panels") or [])} panels)
- Flashcards ({len(hw_data.get("flashcards") or [])} cards)
- Memory Sprint ({len(hw_data.get("memory_sprint", {}).get("items") or [])} items)
- Game Breaks ({len(hw_data.get("game_breaks", {}).get("games") or [])} games)
- Real-Life ({len(hw_data.get("real_life", {}).get("items") or []) if hw_data.get("real_life") else 0} sub-questions)
- Final Boss ({len(hw_data.get("final_boss", {}).get("items") or [])} items)
- Reflection
""",
        encoding="utf-8",
    )


def deploy(content: dict, out_root: Path, slug: str, provider: str, port: int,
           kimi_key: str | None, anthropic_key: str | None,
           builder_url: str | None = None, builder_subject: str | None = None,
           builder_grade: int | None = None) -> Path:
    template = find_runtime_template_dir()
    target = out_root / slug
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    # Copy server.py + requirements + .gitignore + .env.example
    for f in ("server.py", "requirements.txt", ".env.example", ".gitignore"):
        src = template / f
        if src.is_file():
            shutil.copy2(src, target / f)

    # Copy static stack
    static_src = template / "static"
    if static_src.is_dir():
        shutil.copytree(static_src, target / "static")

    # Write homework_data.js (transformed)
    hw_data = transform_content(content)
    write_homework_data_js(target / "static" / "js" / "homework_data.js", hw_data)

    # Write .env
    write_env_file(target / ".env", provider, port, kimi_key, anthropic_key,
                    builder_url=builder_url, builder_subject=builder_subject,
                    builder_grade=builder_grade)

    # Write README
    write_readme(target / "README.md", hw_data, port, provider)

    return target


def main():
    p = argparse.ArgumentParser(description="One-click deploy a builder homework into a runnable HTML stack.")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--fixture", type=Path, help="Path to a fixtures/*.json file or any builder content_json blob")
    src.add_argument("--db", type=str, help="Homework ID to load from the running builder's SQLite (e.g. HW-20260424-003)")
    src.add_argument("--json", type=str, help='Read content_json from stdin: pass "-" to consume stdin')

    p.add_argument("--out", type=Path, default=REPO_ROOT / "dist", help="Output directory (default: ./dist)")
    p.add_argument("--name", type=str, help="Override slug for the output subdirectory")
    p.add_argument("--port", type=int, default=5060, help="Port the deployed server binds to (default 5060)")
    p.add_argument("--provider", choices=("builder", "kimi", "anthropic", "mock"), default="mock",
                   help="Grading provider (default: mock). 'builder' forwards to a NETS Builder host; "
                        "kimi/anthropic call those APIs directly.")
    p.add_argument("--builder-url", type=str, help="When --provider builder: NETS Builder base URL, e.g. http://192.168.1.26:8000")
    p.add_argument("--builder-subject", type=str, help="Subject ID to pass to the Builder API (default: geometriya-g7-11)")
    p.add_argument("--builder-grade", type=int, help="Grade to pass to the Builder API (default: 8)")
    p.add_argument("--boot", action="store_true", help="After deploying, start the server in the background")

    p.add_argument("--install-template", type=Path,
                   help="Install runtime template (one-time) from a directory containing server.py + static/")

    args = p.parse_args()

    if args.install_template:
        install_template(args.install_template)
        return

    if not (args.fixture or args.db or args.json):
        p.error("Provide one of --fixture, --db, or --json")

    if args.fixture:
        content = load_from_fixture(args.fixture)
    elif args.db:
        content = load_from_db(args.db)
    else:
        if args.json != "-":
            p.error("--json must be '-' (we read from stdin)")
        content = load_from_stdin()

    title = (content.get("meta") or {}).get("title", "")
    if not title and content.get("_db_meta"):
        title = content["_db_meta"].get("title", "")
    slug = args.name or slugify(title) or "homework"

    kimi_key = os.environ.get("KIMI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    provider = args.provider
    if provider == "kimi" and not kimi_key:
        print("[warn] --provider kimi but KIMI_API_KEY not set in env -- deployed server will boot in mock mode.")
    if provider == "anthropic" and not anthropic_key:
        print("[warn] --provider anthropic but ANTHROPIC_API_KEY not set in env -- deployed server will boot in mock mode.")

    target = deploy(
        content, args.out, slug, provider, args.port, kimi_key, anthropic_key,
        builder_url=args.builder_url,
        builder_subject=args.builder_subject,
        builder_grade=args.builder_grade,
    )

    print(f"\n[OK] Deployed: {target}")
    print(f"  cd \"{target}\"")
    print(f"  pip install -r requirements.txt")
    print(f"  python server.py")
    print(f"  -> http://127.0.0.1:{args.port}/\n")

    if args.boot:
        print("Booting server in background…")
        env = os.environ.copy()
        env["PORT"] = str(args.port)
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            cwd=target,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"  PID: {proc.pid}   http://127.0.0.1:{args.port}/")


if __name__ == "__main__":
    main()
