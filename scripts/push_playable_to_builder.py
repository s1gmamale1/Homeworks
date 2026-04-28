#!/usr/bin/env python3
"""
push_playable_to_builder.py — Reverse of deploy_homework.py.

Reads a *playable* runtime's homework_data.js, transforms its shape back into
the builder's content_json format, and POSTs it to a running builder via
/api/homeworks + PUT.

Usage:
  python scripts/push_playable_to_builder.py \
    --playable http://127.0.0.1:5057/js/homework_data.js \
    --builder http://192.168.1.26:8000 \
    --title "Markaziy simmetriya va burish" \
    --subject geometriya-g7-11 --grade 9 --mode hard
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from typing import Any


def fetch_playable_data(url_or_path: str) -> dict:
    """Fetch the playable's homework_data.js and parse it via Node.
    The file is JS (`window.HOMEWORK_DATA = {...};`), not JSON, so we let
    Node evaluate it and emit JSON.
    """
    import shutil, subprocess, tempfile

    # Get raw text
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        with urllib.request.urlopen(url_or_path, timeout=10) as r:
            text = r.read().decode("utf-8")
    else:
        from pathlib import Path
        text = Path(url_or_path).read_text(encoding="utf-8")

    if shutil.which("node") is None:
        # Fall back to the (fragile) string converter
        m = re.search(r"window\.HOMEWORK_DATA\s*=\s*(\{.*\});", text, re.S)
        if not m:
            raise SystemExit("Cannot parse playable: node not installed and regex failed")
        return _coerce_jsobj_to_dict(m.group(1))

    # Write a wrapper JS to a temp file and run with `node <file>`
    # (passing via -e fails on Windows when the source is large.)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".cjs", delete=False) as tf:
        tf.write("var window = {};\n")
        tf.write(text)
        tf.write("\nprocess.stdout.write(JSON.stringify(window.HOMEWORK_DATA));\n")
        tmp_path = tf.name

    try:
        proc = subprocess.run(
            ["node", tmp_path],
            capture_output=True, timeout=15,
        )
        if proc.returncode != 0:
            raise SystemExit(f"node parse failed: {proc.stderr.decode('utf-8', 'replace')}")
        out = proc.stdout.decode("utf-8")
        return json.loads(out)
    except Exception as e:
        raise SystemExit(f"Failed to evaluate playable JS via node: {e}")
    finally:
        try:
            import os
            os.unlink(tmp_path)
        except Exception:
            pass


def _coerce_jsobj_to_dict(s: str) -> dict:
    """Last-resort conversion of a JS object literal to JSON.
    Handles: backtick template strings -> JSON strings, unquoted keys -> quoted.
    """
    # Strip line comments
    s = re.sub(r"//[^\n]*", "", s)
    # Quote unquoted keys: { foo: ... } -> { "foo": ... }
    s = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', s)
    # Convert backtick template strings to JSON-quoted strings (no template substitution support).
    def _replace_backtick(m):
        body = m.group(1)
        # Escape backslashes, double-quotes, and newlines.
        body = body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
        return '"' + body + '"'
    s = re.sub(r"`([^`]*)`", _replace_backtick, s, flags=re.S)
    # Strip trailing commas inside objects/arrays
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    return json.loads(s)


# ---------- transform: playable -> builder content_json ----------

def map_panels_to_builder(panels: list[dict]) -> list[dict]:
    """Playable panels[].blocks[] -> builder panels[].pages[].blocks[].
    Block type mapping is mostly direct; 'h' maps to 'h2'."""
    out = []
    for p in panels:
        blocks = []
        for b in p.get("blocks", []):
            t = b.get("type", "p")
            if t == "h":
                blocks.append({"type": "h2", "text": b.get("text", "")})
            elif t == "p":
                blocks.append({"type": "p", "text": b.get("text", "")})
            elif t == "callout":
                blocks.append({"type": "quote", "text": b.get("text", "")})
            elif t == "ul":
                blocks.append({"type": "ul", "items": b.get("items") or []})
            elif t == "ol":
                blocks.append({"type": "ol", "items": b.get("items") or []})
            elif t == "svg":
                blocks.append({"type": "svg", "html": b.get("html", "")})
            elif t == "qa":
                blocks.append({"type": "p", "text": f"<b>{b.get('q','')}</b><br>→ {b.get('a','')}"})
            else:
                blocks.append({"type": "p", "text": b.get("text") or ""})
        out.append({
            "id": p.get("number") or len(out) + 1,
            "title": f"PANEL {p.get('number') or len(out)+1} — {(p.get('title') or '').upper()}",
            "pages": [{"blocks": blocks}],
        })
    return out


def map_flashcards_to_builder(cards: list[dict]) -> list[dict]:
    out = []
    for c in cards:
        out.append({
            "term": c.get("front", ""),
            "def": c.get("back", ""),
            "cluster": "QOIDA",
        })
    return out


def map_memory_sprint_to_builder(ms: dict) -> list[dict]:
    items = ms.get("items") if isinstance(ms, dict) else (ms or [])
    out = []
    for it in items:
        kind = it.get("type", "mc").lower()
        builder_type = "KO" if kind == "mc" else ("TF" if kind == "tf" else ("YNNG" if kind == "ynng" else "KO"))
        opts_in = it.get("options") or []
        opts = [o.get("text", "") for o in opts_in]
        correct_id = it.get("correct")
        correct_idx = 0
        for i, o in enumerate(opts_in):
            if o.get("id") == correct_id:
                correct_idx = i
                break
        out.append({
            "type": builder_type,
            "prompt": it.get("question", ""),
            "subtitle": "",
            "tags": it.get("title", ""),
            "explain": it.get("rationale", ""),
            "options": opts,
            "correct": correct_idx,
        })
    return out


def map_game_breaks_to_builder(gb: dict) -> dict:
    """Playable {games:[G1,G2,G3]} -> {gb_adaptive_quiz, gb_why_chain, gb_memory_match}."""
    games = (gb or {}).get("games", [])
    aq, wc, mm = [], [], []
    for g in games:
        # Heuristic: identify by id or by title
        gid = (g.get("id") or "").upper()
        title = (g.get("title") or "").lower()
        if gid == "G1" or "adaptive" in title or "viktorina" in title:
            for it in g.get("items") or []:
                aq.append({
                    "q": it.get("question", ""),
                    "tags": it.get("tags", ""),
                    "tier": "MEDIUM",
                    "ans": [it.get("expected", "")],
                    "capture": bool(it.get("notebook")),
                    "answer_spec": {
                        "type": "semantic" if it.get("grading") == "ai_rubric" else "text_fuzzy",
                        "expected": it.get("expected", ""),
                        "canonical_display": it.get("expected", ""),
                        "allow_ai_fallback": True,
                    },
                })
        elif gid == "G2" or "sentence" in title or "fill" in title or "to'ldir" in title:
            for it in g.get("items") or []:
                wc.append({
                    "q": it.get("question", ""),
                    "tags": it.get("tags", ""),
                    "inv": it.get("expected", ""),
                    "reprompts": [],
                })
        elif gid == "G3" or "tile" in title or "match" in title or "moslang" in title or "juftla" in title:
            left = g.get("left") or []
            right = g.get("right") or []
            pairs = g.get("correct_pairs") or {}
            # Map L-id -> R-id pairs into [left_text, right_text]
            l_by_id = {l["id"]: l["text"] for l in left}
            r_by_id = {r["id"]: r["text"] for r in right}
            for lid, rid in pairs.items():
                if lid in l_by_id and rid in r_by_id:
                    mm.append([l_by_id[lid], r_by_id[rid]])
    return {"gb_adaptive_quiz": aq, "gb_why_chain": wc, "gb_memory_match": mm}


def map_real_life_to_builder(rl: dict | None) -> dict | None:
    if not rl:
        return None
    out = {
        "badge": rl.get("title") or "Real-Life Challenge",
        "story": rl.get("scenario", ""),
        "endTitle": "Yakuniy",
        "endSub": "Vazifa yakunlandi",
    }
    items = rl.get("items") or []
    for i, it in enumerate(items, 1):
        out[f"q{i}"] = {
            "prompt": it.get("question", ""),
            "ans": "",
            "fb": "",
            "capture": bool(it.get("notebook")),
            "tags": it.get("tags", ""),
        }
    return out


def map_boss_to_builder(fb: dict | None) -> list[dict]:
    if not fb:
        return []
    items = fb.get("items") or []
    out = []
    for it in items:
        hint = (it.get("hints") or [""])[0] if it.get("hints") else ""
        # Strip "Hint N (-X HP):" prefix
        hint = re.sub(r"^Hint \d+\s*\([^\)]+\):\s*", "", hint)
        out.append({
            "q": it.get("question", ""),
            "tags": it.get("tags", ""),
            "ans": [],
            "hint": hint,
            "dmg": it.get("damage", 10),
            "svg": it.get("svg") or "",
            "answer_spec": {
                "type": "semantic",
                "expected": "",
                "canonical_display": "",
                "allow_ai_fallback": True,
            },
        })
    return out


def map_reflection_to_builder(r: dict | None) -> dict | None:
    if not r:
        return None
    return {
        "summary": r.get("summary", ""),
        "question": r.get("question", ""),
        "spaced_rep": r.get("schedule", ""),
        "closing": r.get("closing", ""),
    }


def transform_playable_to_builder(playable: dict, override: dict) -> dict:
    meta = playable.get("meta") or {}
    gb_split = map_game_breaks_to_builder(playable.get("game_breaks") or {})
    return {
        "meta": {
            "title": meta.get("title", "Homework"),
            "subject_display": meta.get("subject") or override.get("subject", ""),
            "section": meta.get("section", ""),
            "cefr_level": "",
        },
        "quotes": [playable.get("intro", "")] if playable.get("intro") else [],
        "panels": map_panels_to_builder(playable.get("panels") or []),
        "flashcards": map_flashcards_to_builder(playable.get("flashcards") or []),
        "memory_sprint": map_memory_sprint_to_builder(playable.get("memory_sprint")),
        "gb_adaptive_quiz": gb_split["gb_adaptive_quiz"],
        "gb_why_chain": gb_split["gb_why_chain"],
        "gb_memory_match": gb_split["gb_memory_match"],
        "real_life": map_real_life_to_builder(playable.get("real_life")),
        "boss_questions": map_boss_to_builder(playable.get("final_boss")),
        "reflection": map_reflection_to_builder(playable.get("reflection")),
        # Carry grading config if present
        "grading": playable.get("grading") or {
            "system": "amr",
            "provider": "auto",
            "confidence_threshold": 80,
            "deploy_port": 5060,
        },
    }


# ---------- HTTP ----------

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
    p.add_argument("--playable", required=True, help="URL or path to homework_data.js")
    p.add_argument("--builder", required=True, help="Builder base URL, e.g. http://192.168.1.26:8000")
    p.add_argument("--title", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--grade", type=int, required=True)
    p.add_argument("--mode", default="hard")
    args = p.parse_args()

    # Fetch playable
    if args.playable.startswith("http://") or args.playable.startswith("https://"):
        playable = fetch_playable_data(args.playable)
    else:
        # treat as file path
        from pathlib import Path
        text = Path(args.playable).read_text(encoding="utf-8")
        m = re.search(r"window\.HOMEWORK_DATA\s*=\s*(\{.*\});", text, re.S)
        if not m:
            raise SystemExit("Could not parse playable file")
        try:
            playable = json.loads(m.group(1))
        except json.JSONDecodeError:
            playable = _coerce_jsobj_to_dict(m.group(1))

    print(f"Fetched playable: {(playable.get('meta') or {}).get('title','?')}")
    print(f"  panels:        {len(playable.get('panels') or [])}")
    print(f"  flashcards:    {len(playable.get('flashcards') or [])}")
    print(f"  memory sprint: {len((playable.get('memory_sprint') or {}).get('items', []) if isinstance(playable.get('memory_sprint'),dict) else [])}")
    print(f"  games:         {len((playable.get('game_breaks') or {}).get('games', []))}")
    print(f"  real-life:     {len((playable.get('real_life') or {}).get('items', []))}")
    print(f"  boss:          {len((playable.get('final_boss') or {}).get('items', []))}")

    content = transform_playable_to_builder(playable, {"subject": args.subject})

    # POST + PUT into builder
    create_url = args.builder.rstrip("/") + "/api/homeworks"
    record = http_post(create_url, {
        "title": args.title,
        "subject": args.subject,
        "grade": args.grade,
        "mode": args.mode,
    })
    hw_id = record["id"]
    print(f"\n[OK] Created at {args.builder}: {hw_id}")

    put_url = f"{args.builder.rstrip('/')}/api/homeworks/{hw_id}"
    record2 = http_put(put_url, {"content_json": content})
    print(f"[OK] Content uploaded")

    # Verify by reading back
    get_url = put_url
    with urllib.request.urlopen(get_url, timeout=10) as r:
        back = json.loads(r.read().decode("utf-8"))
    cj = back.get("content_json") or {}
    print()
    print("=== Verification — section completeness ===")
    print(f"  meta.title:       {(cj.get('meta') or {}).get('title','-')}")
    print(f"  panels:           {len(cj.get('panels') or [])} panels")
    for pl in cj.get("panels") or []:
        n_blocks = sum(len(pg.get("blocks") or []) for pg in pl.get("pages") or [])
        print(f"    Panel {pl.get('id')}: {n_blocks} blocks ({pl.get('title','')[:50]})")
    print(f"  flashcards:       {len(cj.get('flashcards') or [])}")
    print(f"  memory_sprint:    {len(cj.get('memory_sprint') or [])}")
    print(f"  gb_adaptive_quiz: {len(cj.get('gb_adaptive_quiz') or [])}")
    print(f"  gb_why_chain:     {len(cj.get('gb_why_chain') or [])}")
    print(f"  gb_memory_match:  {len(cj.get('gb_memory_match') or [])}")
    rl = cj.get("real_life") or {}
    rl_qs = sum(1 for k in rl if re.match(r"q\d+$", k))
    print(f"  real_life:        story={'set' if rl.get('story') else 'EMPTY'}, sub-questions={rl_qs}")
    print(f"  boss_questions:   {len(cj.get('boss_questions') or [])}")
    refl = cj.get("reflection") or {}
    print(f"  reflection:       summary={'set' if refl.get('summary') else 'EMPTY'}")
    print()
    print(f"Open the builder editor at: {args.builder}/builder.html?id={hw_id}")


if __name__ == "__main__":
    main()
