"""HTML injector — stamps content_json into perfect_homework.html template.

Pure functions, no side effects. Template is read ONCE at module import and
cached in memory. See CONTRACTS.md §5 for the injector contract.
"""

import json
import re

from ..config import TEMPLATE_PATH

# Read template ONCE at module load (not per request)
with open(TEMPLATE_PATH, "r", encoding="utf-8") as _f:
    _TEMPLATE = _f.read()

# Mapping: content_json key -> JS constant name in template
_ARRAY_CONSTANTS = [
    ("panels",           "PANELS"),
    ("quotes",           "QUOTES"),
    ("flashcards",       "FLASHCARDS"),
    ("memory_sprint",    "MS_QUESTIONS"),
    ("gb_adaptive_quiz", "GB_ADAPTIVE_QUIZ"),
    ("gb_why_chain",     "GB_WHY_CHAIN"),
    ("gb_memory_match",  "GB_MEMORY_MATCH"),
    ("boss_questions",   "BOSS_QUESTIONS"),
]

# Mapping: content_json key -> JS constant name in template, for OBJECT (non-array) constants.
# Wave 2: reading/consolidation/reflection are objects, like RL_SCENARIO.
_OBJECT_CONSTANTS = [
    ("reading",       "READING"),
    ("consolidation", "CONSOLIDATION"),
    ("reflection",    "REFLECTION"),
]


def _esc(s) -> str:
    """Escape text for safe insertion into HTML content."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _strip_html(s) -> str:
    """Strip HTML tags + decode common entities. Used for plain-text fields like
    flashcard front terms, which the template renders via textContent."""
    if not s:
        return ""
    text = str(s)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#039;", "'")
            .replace("&apos;", "'")
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_answers(value) -> list:
    """Normalize an answer field (string or list) into a list of accepted strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    s = str(value).strip()
    if not s:
        return []
    # Accept common separators so authors can cram multiple answers into one input.
    parts = [p.strip() for p in re.split(r"\s*(?:\|\||;|\n)\s*", s) if p.strip()]
    return parts or [s]


def _rl_adapt_to_template(rl: dict) -> dict:
    """Convert builder-shape real_life ({badge, story, q1..q6, endTitle, endSub})
    into the template-shape {title, story, questions:[...], closure:{...}}."""
    out = dict(rl)
    badge = rl.get("badge") or "VAZIFA"
    title = rl.get("title") or badge
    story = rl.get("story") or ""

    def make_text_q(key: str, bloom: str, pisa: str) -> dict:
        q = rl.get(key) or {}
        capture = bool(q.get("capture"))
        answers = _split_answers(q.get("ans"))
        fb_html = q.get("fb") or ""
        hint = _strip_html(fb_html) or ""
        q_type = "text-with-capture" if capture else "text"
        out_q = {
            "id":                key.upper(),
            "type":              q_type,
            "bloom":             bloom,
            "pisa":              pisa,
            "capture":           capture,
            "prompt":            q.get("prompt") or "",
            "acceptableAnswers": answers or ["—"],
            "hint":              hint,
        }
        if capture:
            out_q["expectedWork"] = hint
        return out_q

    def make_fields_q(key: str, bloom: str, pisa: str) -> dict:
        q = rl.get(key) or {}
        # If author provided no fields[] but did provide ans, fall through to a
        # single-input text question — otherwise the player gets a phantom
        # multi-input box that only accepts "—".
        fields_in = q.get("fields") or []
        if not fields_in and (q.get("ans") or q.get("prompt")):
            return make_text_q(key, bloom, pisa)
        capture = bool(q.get("capture"))
        fields_out = []
        for f in fields_in:
            if not isinstance(f, dict):
                continue
            fields_out.append({
                "label":      f.get("label") or f.get("id") or "",
                "acceptable": _split_answers(f.get("ans")) or ["—"],
            })
        if not fields_out:
            fields_out = [{"label": "Javob", "acceptable": ["—"]}]
        return {
            "id":      key.upper(),
            "type":    "multi-input",
            "bloom":   bloom,
            "pisa":    pisa,
            "capture": capture,
            "prompt":  q.get("prompt") or "",
            "fields":  fields_out,
        }

    def make_open_q(key: str, bloom: str, pisa: str) -> dict:
        q = rl.get(key) or {}
        return {
            "id":       key.upper(),
            "type":     "textarea",
            "bloom":    bloom,
            "pisa":     pisa,
            "capture":  bool(q.get("capture")),
            "prompt":   q.get("prompt") or "",
            "accepted": "open-ended",
        }

    # Only emit a question slot if the author actually provided content for it.
    # Phantom empty questions (acceptableAnswers: ["—"], no prompt) make the
    # runtime un-completable.
    def _has(key: str) -> bool:
        q = rl.get(key) or {}
        return bool((q.get("prompt") or "").strip()) or bool(q.get("ans")) or bool(q.get("fields"))

    questions = []
    if _has("q1"): questions.append(make_text_q("q1", "L3", "P2"))
    if _has("q2"): questions.append(make_fields_q("q2", "L2", "P2"))
    if _has("q3"): questions.append(make_text_q("q3", "L4", "P3"))
    if _has("q4"): questions.append(make_text_q("q4", "L4", "P3"))
    if _has("q5"):
        questions.append(make_open_q("q5", "L5", "P4")
                         if (rl.get("q5") or {}).get("open")
                         else make_text_q("q5", "L3", "P2"))
    if _has("q6"): questions.append(make_text_q("q6", "L3", "P2"))

    out["title"] = title
    out["story"] = story
    out["questions"] = questions
    out["closure"] = {
        "title":   rl.get("endTitle") or "Loyiha tugadi ✓",
        "message": rl.get("endSub")   or "Ajoyib ish! Siz vazifani muvaffaqiyatli yakunladingiz.",
    }
    return out


def _parse_bloom_pisa(tags: str, default_bloom: str = "L2", default_pisa: str = "L2"):
    """Extract Bloom and PISA level codes from a tags string like
    ``[Bloom: L3 | PISA: L2 | Damage: -20 HP]``. Returns (bloom, pisa)."""
    if not tags:
        return default_bloom, default_pisa
    src = str(tags)
    bm = re.search(r"bloom\s*:\s*([A-Za-z]?\d+)", src, flags=re.IGNORECASE)
    pm = re.search(r"pisa\s*:\s*([A-Za-z]?\d+)", src, flags=re.IGNORECASE)
    bloom = (bm.group(1) if bm else default_bloom).upper()
    pisa = (pm.group(1) if pm else default_pisa).upper()
    if not bloom.startswith("L"):
        bloom = "L" + bloom.lstrip("Ll")
    if not pisa.startswith("L"):
        pisa = "L" + pisa.lstrip("Ll")
    return bloom, pisa


def _strip_text_tags_keep_media(s) -> str:
    """Strip formatting tags (p/b/i/br/span/div/strong/em/u/h1-h6) but PRESERVE
    inline <img ...> and <svg>...</svg> elements. Used for the flashcard front
    term, which now renders via innerHTML so users can embed visuals via the
    RichField toolbar. NBSP/whitespace normalized; other entities left intact
    so &amp; etc. survive into innerHTML correctly."""
    if not s:
        return ""
    text = str(s)
    # 1. Extract <img ...> and <svg>...</svg> into placeholders so the tag
    #    stripper below doesn't eat them.
    placeholders: list[str] = []

    def _stash(match):
        placeholders.append(match.group(0))
        return f"\x00MEDIA{len(placeholders) - 1}\x00"

    # SVG first (multiline body), then img.
    text = re.sub(r"<svg\b[^>]*>.*?</svg>", _stash, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<img\b[^>]*?/?>", _stash, text, flags=re.IGNORECASE)
    # 2. Strip all remaining tags (formatting only — p, b, i, br, span, div, etc.).
    text = re.sub(r"<[^>]+>", " ", text)
    # 3. Normalize whitespace + nbsp.
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    # 4. Restore stashed media.
    def _restore(match):
        idx = int(match.group(1))
        return placeholders[idx] if 0 <= idx < len(placeholders) else ""

    text = re.sub(r"\x00MEDIA(\d+)\x00", _restore, text)
    return text


def inject(
    content_json: dict,
    meta_override: dict | None = None,
    *,
    runtime_context: dict,
) -> str:
    """Inject content_json into the Perfect Homework HTML template.

    content_json: full schema per CONTRACTS §1
    meta_override: optional {title, subject_display, section, cefr_level} to force
                   specific values. If None, uses content_json['meta'].
    runtime_context: required keyword-only dict — AI tutor runtime hook context
                     (window.NETS_CTX + runtime.js). Always injected before </body>.

    Returns: rendered HTML string.
    """
    html = _TEMPLATE
    meta = meta_override or content_json.get("meta") or {}

    # 1. Replace title h1 (first occurrence only)
    title = meta.get("title", "Homework")
    subject_display = meta.get("subject_display", "")
    section = meta.get("section", "")

    html = re.sub(
        r"<h1>.*?</h1>",
        f"<h1>NETS · {_esc(title)}</h1>",
        html,
        count=1,
    )

    # 2. Replace caption div (first occurrence — the one at top of homework)
    if subject_display or section:
        caption_text = f"{subject_display}"
        if section:
            caption_text += f" · {section}"
        html = re.sub(
            r'<div class="caption">.*?</div>',
            f'<div class="caption">{_esc(caption_text)}</div>',
            html,
            count=1,
        )

    # 3. Replace each array constant
    for (key, const_name) in _ARRAY_CONSTANTS:
        data = content_json.get(key, [])
        if data is None:
            data = []
        # Shape adapter: template expects quotes as [{t, a}] objects.
        # If content_json has plain strings, wrap them into {t: str, a: ""}.
        # If empty, inject a single placeholder so runQuoteSequence doesn't crash.
        if key == "quotes":
            data = [
                q if isinstance(q, dict) else {"t": str(q), "a": ""}
                for q in data
            ]
            if not data:
                data = [{"t": "Bilim — aql va sabrning mevasidir.", "a": ""}]

        # Shape adapter: Memory Sprint editor emits type codes MC|TF|YNNG, but the
        # template renders item.type directly as a human label in "Savol X / Y · {type}".
        # Map codes to Uzbek labels so the runtime UI reads naturally. Legacy values
        # (KO, full-label strings) are accepted and passed through.
        if key == "memory_sprint":
            _MS_LABELS = {
                "MC":   "Ko'p variantli",
                "TF":   "To'g'ri / Noto'g'ri",
                "YNNG": "Ha / Yo'q / Aniq emas",
                "KO":   "Ko'p variantli",  # legacy
            }
            adapted = []
            for q in data:
                if not isinstance(q, dict):
                    continue
                q2 = dict(q)
                raw_type = q2.get("type", "MC")
                q2["type"] = _MS_LABELS.get(raw_type, raw_type)
                # Template expects options, correct, prompt, subtitle, tags, explain.
                q2.setdefault("options", ["", "", "", ""])
                q2.setdefault("correct", 0)
                q2.setdefault("prompt", "")
                q2.setdefault("subtitle", "")
                q2.setdefault("tags", "[Bloom: L1 | PISA: L1]")
                q2.setdefault("explain", "")
                adapted.append(q2)
            data = adapted

        # Shape adapter: Adaptive Quiz editor emits {q, tags, tier: "EASY", ans[], capture, hint, media}
        # but the template expects {id, tier: "easy", bloom, pisa, prompt, answer, work}.
        # The template filters by lowercase tier strings in gbAQPickItem, so we lowercase tier.
        # We also parse Bloom/PISA out of the tags string.
        if key == "gb_adaptive_quiz":
            adapted = []
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                # Already in template shape? pass through.
                if "prompt" in item and "answer" in item:
                    adapted.append(item)
                    continue
                tier = str(item.get("tier", "easy")).lower()
                if tier not in ("easy", "medium", "hard"):
                    tier = "easy"
                bloom, pisa = _parse_bloom_pisa(item.get("tags", ""), "L2", "L2")
                ans_list = item.get("ans") or [""]
                if not isinstance(ans_list, list):
                    ans_list = [str(ans_list)]
                # Strip empties; preserve order; primary answer = first non-empty.
                acceptable = [str(a).strip() for a in ans_list if str(a).strip()]
                if not acceptable:
                    acceptable = [""]
                answer = acceptable[0]
                hint_text = item.get("hint") or ""
                adapted.append({
                    "id":     item.get("id", f"A{i+1}"),
                    "tier":   tier,
                    "bloom":  bloom,
                    "pisa":   pisa,
                    "prompt": item.get("q", ""),
                    "answer": answer,
                    # Wave 2 fix: runtime checks acceptable[] first, falls back to answer.
                    "acceptable": acceptable,
                    "work":   hint_text or f"Javob: {answer}",
                    # Preserve extras for future use
                    "capture": bool(item.get("capture", False)),
                    "ans_all": acceptable,
                })
            # Ensure each tier has at least one DISTINCT item so the picker never
            # returns undefined and the student never sees the same question twice
            # in different tiers. If the source data collapses everything into one
            # tier (common when an importer hardcodes "tier": "MEDIUM"), redistribute
            # real items across easy/medium/hard by Bloom level — fall back to index
            # buckets when Bloom is missing.
            if adapted:
                tiers_present = {x["tier"] for x in adapted}
                missing = [t for t in ("easy", "medium", "hard") if t not in tiers_present]
                if missing and len(adapted) >= 2:
                    def _bloom_to_tier(b: str) -> str:
                        # L1-L2 → easy, L3 → medium, L4+ → hard. Default medium.
                        m = re.search(r"L(\d)", str(b or ""))
                        if not m:
                            return "medium"
                        n = int(m.group(1))
                        return "easy" if n <= 2 else ("hard" if n >= 4 else "medium")

                    have_bloom = any(re.search(r"L\d", str(x.get("bloom") or "")) for x in adapted)
                    if have_bloom:
                        # Bloom-driven redistribution
                        for x in adapted:
                            x["tier"] = _bloom_to_tier(x.get("bloom"))
                    else:
                        # Index buckets: first third → easy, middle → medium, last third → hard
                        n = len(adapted)
                        for i, x in enumerate(adapted):
                            if   i < n / 3:        x["tier"] = "easy"
                            elif i < 2 * n / 3:    x["tier"] = "medium"
                            else:                  x["tier"] = "hard"

                    # If a tier is still empty, fill it with the item whose Bloom
                    # is *closest to* that tier's target band — never with the most
                    # advanced item demoted to easy or vice-versa.
                    def _bloom_n(x):
                        m = re.search(r"L(\d)", str(x.get("bloom") or ""))
                        return int(m.group(1)) if m else 3
                    target = {"easy": 1, "medium": 3, "hard": 5}
                    by_tier = {"easy": [], "medium": [], "hard": []}
                    for x in adapted:
                        by_tier.setdefault(x["tier"], []).append(x)
                    for t in ("easy", "medium", "hard"):
                        if by_tier[t]:
                            continue
                        # Find a donor tier with > 1 item; among its items pick the
                        # one whose Bloom level is closest to target[t].
                        donors = [k for k in ("easy", "medium", "hard") if k != t and len(by_tier[k]) >= 2]
                        if not donors:
                            continue
                        # Choose donor whose pool has an item closest to target[t]
                        best = None  # (donor_key, item_index, distance)
                        for d in donors:
                            for i, item in enumerate(by_tier[d]):
                                dist = abs(_bloom_n(item) - target[t])
                                if best is None or dist < best[2]:
                                    best = (d, i, dist)
                        if best:
                            d, i, _ = best
                            moved = by_tier[d].pop(i)
                            moved["tier"] = t
                            by_tier[t].append(moved)
            data = adapted

        # Shape adapter: Sentence Fill editor emits {q, inv, reprompts[]} but the
        # template expects {id, bloom, pisa, chain:[{level, probe, expect}], invariant}.
        # We wrap the single q into a 3-level chain (using reprompts as levels 2-3 probes),
        # and invariant = inv.
        if key == "gb_why_chain":
            adapted = []
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                # Already nested? pass through.
                if isinstance(item.get("chain"), list) and item["chain"]:
                    if "invariant" not in item and "inv" in item:
                        item = dict(item); item["invariant"] = item.get("inv", "")
                    adapted.append(item)
                    continue
                q = item.get("q", "")
                inv = item.get("inv", "") or item.get("invariant", "")
                reprompts = item.get("reprompts") or []
                if not isinstance(reprompts, list):
                    reprompts = []
                # Wave 2: per-level expects. If author provides expects[], use them; else
                # fall back to invariant (legacy behavior).
                expects = item.get("expects") or []
                if not isinstance(expects, list):
                    expects = []
                # Build a chain of up to 3 levels from [q] + reprompts, expect = per-level
                # keyword (or invariant fallback).
                levels = [q] if q else []
                for rp in reprompts:
                    if len(levels) >= 3:
                        break
                    if rp:
                        levels.append(rp)
                while len(levels) < 3:
                    levels.append(q or "Keyingi qadam?")
                chain = []
                for li, probe in enumerate(levels[:3]):
                    per_level_expect = ""
                    if li < len(expects):
                        per_level_expect = str(expects[li] or "").strip()
                    chain.append({
                        "level":  li + 1,
                        "probe":  probe,
                        "expect": per_level_expect or inv,
                    })
                adapted.append({
                    "id":        item.get("id", f"C{i+1}"),
                    "bloom":     "L3",
                    "pisa":      "L3",
                    "chain":     chain,
                    "invariant": inv or "—",
                })
            data = adapted

        # Shape adapter: builder stores flashcards as flat {term, def, cluster, hint?, media?}.
        # Template expects {cluster, front:{term, term_html?, media?, formula?}, back:{definition, bullets?, hook}}.
        if key == "flashcards":
            adapted = []
            for card in data:
                if not isinstance(card, dict):
                    continue
                # Already nested shape — pass through.
                if isinstance(card.get("front"), dict) or isinstance(card.get("back"), dict):
                    adapted.append(card)
                    continue
                cluster = card.get("cluster") or "QOIDA"
                # Plain-text fallback (used for side-peek cards via textContent).
                term_plain = _strip_html(card.get("term") or "")
                # Mixed HTML — formatting stripped but inline <img>/<svg> preserved
                # so users can embed visuals inside the term RichField.
                term_html = _strip_text_tags_keep_media(card.get("term") or "")
                definition = card.get("def") or ""
                # Structured front media (dedicated builder zone above the term).
                media = card.get("media") if isinstance(card.get("media"), dict) else None
                front_media_html = ""
                if media:
                    if media.get("type") == "image" and media.get("src"):
                        front_media_html = (
                            f'<img src="{_esc(media["src"])}" '
                            f'alt="{_esc(media.get("alt") or "")}" />'
                        )
                    elif media.get("type") == "svg" and media.get("html"):
                        front_media_html = media["html"]
                adapted.append({
                    "cluster": cluster,
                    "front": {
                        "term": term_plain,
                        "term_html": term_html,
                        "media": front_media_html,
                    },
                    "back": {
                        "definition": definition,
                        "bullets": [],
                        "hook": card.get("hint") or "",
                    },
                })
            data = adapted

        # Shape adapter: Boss editor emits {q, tags, ans[], hint, dmg} but the
        # template expects {id, tier, damage, bloom, pisa, prompt, acceptable[], hints[]}.
        # We parse Bloom/PISA/Damage from tags, split hint into an array (by newline/pipe),
        # and map damage → tier (10→easy, 20→medium, 30→hard).
        if key == "boss_questions":
            adapted = []
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                # Already template shape? pass through.
                if "prompt" in item and "acceptable" in item:
                    adapted.append(item)
                    continue
                dmg = int(item.get("dmg", 10) or 10)
                tier = "easy" if dmg <= 10 else "medium" if dmg <= 20 else "hard"
                bloom, pisa = _parse_bloom_pisa(item.get("tags", ""), "L3", "L3")
                ans_list = item.get("ans") or [""]
                if not isinstance(ans_list, list):
                    ans_list = [str(ans_list)]
                # Split the single hint into hint array on newlines or ' | '.
                hint_raw = item.get("hint") or ""
                # Strip HTML and split on lines / bullet separators.
                hint_plain = _strip_html(hint_raw)
                hint_parts = [p.strip() for p in re.split(r"\n|\s\|\s|•", hint_plain) if p.strip()]
                if not hint_parts:
                    hint_parts = [hint_plain or "—"]
                # Provide up to 3 progressive hints.
                while len(hint_parts) < 3:
                    hint_parts.append(hint_parts[-1])
                adapted.append({
                    "id":         item.get("id", f"Q{i+1}"),
                    "tier":       tier,
                    "damage":     dmg,
                    "bloom":      bloom,
                    "pisa":       pisa,
                    "prompt":     item.get("q", ""),
                    "acceptable": [a for a in ans_list if a],
                    "hints":      hint_parts[:3],
                })
            data = adapted

        # Shape adapter: contract uses [[left, right]] arrays; template expects
        # [{a, b, confirmQ, correct}] objects. Convert + back-fill missing fields.
        if key == "gb_memory_match":
            adapted = []
            for pair in data:
                if isinstance(pair, dict):
                    # Already object-shaped — ensure required fields exist.
                    a = pair.get("a") or pair.get("left") or ""
                    b = pair.get("b") or pair.get("right") or ""
                    adapted.append({
                        "a": a,
                        "b": b,
                        "confirmQ": pair.get("confirmQ") or f"{a} ↔ ?",
                        "correct": pair.get("correct") or b,
                    })
                elif isinstance(pair, list) and len(pair) >= 2:
                    a, b = pair[0], pair[1]
                    adapted.append({
                        "a": a,
                        "b": b,
                        "confirmQ": f"{a} ↔ ?",
                        "correct": b,
                    })
            data = adapted

        # Empty-array placeholders to prevent template runtime crashes on new homeworks
        if not data:
            if key == "panels":
                data = [{
                    "id": 1,
                    "title": "PANEL 1 — Ko'rib chiqish",
                    "pages": [{"blocks": [{"type": "p", "text": "Bu bosqich hali to'ldirilmagan."}]}]
                }]
            elif key == "flashcards":
                data = [{
                    "cluster": "QOIDA",
                    "front": {"term": "Joylashtirilmagan", "term_html": "Joylashtirilmagan", "media": ""},
                    "back": {"definition": "Kontent tayyorlanishi kutilmoqda.", "bullets": [], "hook": ""},
                }]
            elif key == "memory_sprint":
                data = [{
                    "type": "KO",
                    "prompt": "Bu bosqich hali to'ldirilmagan.",
                    "subtitle": "",
                    "tags": "[Bloom: L1 | PISA: L1]",
                    "explain": "Builder'da savollarni qo'shing.",
                    "options": ["OK"],
                    "correct": 0,
                }]
            elif key == "gb_adaptive_quiz":
                # Must match template shape (already adapted by this point in the loop).
                data = [
                    {"id": "AF", "tier": "easy",   "bloom": "L2", "pisa": "L2",
                     "prompt": "Bu bosqich hali to'ldirilmagan.", "answer": "ok", "acceptable": ["ok"], "work": "Builder'dan savollarni qo'shing.", "capture": False, "ans_all": ["ok"]},
                    {"id": "MF", "tier": "medium", "bloom": "L3", "pisa": "L3",
                     "prompt": "Bu bosqich hali to'ldirilmagan.", "answer": "ok", "acceptable": ["ok"], "work": "Builder'dan savollarni qo'shing.", "capture": False, "ans_all": ["ok"]},
                    {"id": "HF", "tier": "hard",   "bloom": "L4", "pisa": "L4",
                     "prompt": "Bu bosqich hali to'ldirilmagan.", "answer": "ok", "acceptable": ["ok"], "work": "Builder'dan savollarni qo'shing.", "capture": False, "ans_all": ["ok"]},
                ]
            elif key == "gb_why_chain":
                # Template shape with 3-level chain.
                data = [{
                    "id": "CF",
                    "bloom": "L3", "pisa": "L3",
                    "chain": [
                        {"level": 1, "probe": "Bu bosqich hali to'ldirilmagan.", "expect": "—"},
                        {"level": 2, "probe": "Builder'dan savol qo'shing.",     "expect": "—"},
                        {"level": 3, "probe": "Keyingi qadam?",                   "expect": "—"},
                    ],
                    "invariant": "—",
                }]
            elif key == "gb_memory_match":
                data = [
                    {"a": "—", "b": "—", "confirmQ": "— ↔ ?", "correct": "—"},
                    {"a": "—", "b": "—", "confirmQ": "— ↔ ?", "correct": "—"},
                ]
            elif key == "boss_questions":
                # Template shape.
                data = [{
                    "id":         "QF",
                    "tier":       "easy",
                    "damage":     10,
                    "bloom":      "L3",
                    "pisa":       "L3",
                    "prompt":     "Bu bosqich hali to'ldirilmagan.",
                    "acceptable": ["ok"],
                    "hints":      ["Builder'dan savollarni qo'shing.", "Savollar shu yerda paydo bo'ladi.", "Kontent tayyorlanishi kutilmoqda."],
                }]
        replacement = f"const {const_name} = {json.dumps(data, ensure_ascii=False)};"
        pattern = rf"const {const_name}\s*=\s*\[.*?\];"
        html = re.sub(pattern, lambda _, r=replacement: r, html, count=1, flags=re.DOTALL)

    # 4. Replace RL_SCENARIO (object, not array). Fallback if missing to avoid template crash.
    rl = content_json.get("real_life")
    if not rl:
        rl = {
            "badge": "VAZIFA · Joylashtirilmagan",
            "story": "Bu bosqich hali to'ldirilmagan. Builder orqali ssenariy qo'shing.",
            "q1": {"prompt": "Savol kutilmoqda.", "ans": "ok", "fb": "OK"},
            "q2": {"prompt": "Savol kutilmoqda.", "fields": [{"id": "x", "label": "Javob", "ans": "ok"}], "fb": "OK"},
            "q3": {"prompt": "Savol kutilmoqda.", "ans": "ok", "fb": "OK"},
            "q4": {"prompt": "Savol kutilmoqda.", "fields": [{"id": "y", "label": "Javob", "ans": "ok"}], "fb": "OK"},
            "q5": {"prompt": "Savol kutilmoqda.", "open": True, "fb": "OK"},
            "q6": {"prompt": "Savol kutilmoqda.", "ans": "ok", "fb": "OK"},
            "endTitle": "Vazifa bajarildi!",
            "endSub": "Kontent builder'da to'ldirilgandan keyin to'liq tajriba paydo bo'ladi.",
        }
    if rl:
        # Shape adapter: builder stores {badge, story, q1..q6, endTitle, endSub}
        # but the template expects {title, story, questions:[{...}], closure:{title, message}}.
        # Convert if the template shape isn't already present.
        if "questions" not in rl or "closure" not in rl:
            rl = _rl_adapt_to_template(rl)
        rl_json = f"const RL_SCENARIO = {json.dumps(rl, ensure_ascii=False)};"
        # Try primary pattern (with // BOSS marker)
        primary = re.search(r"const RL_SCENARIO\s*=\s*\{.*?\};\s*// BOSS", html, flags=re.DOTALL)
        if primary:
            html = html[: primary.start()] + rl_json + "\n// BOSS" + html[primary.end():]
        else:
            # Fallback: find object literal followed by const/var/let/function/comment
            fallback = re.search(
                r"const RL_SCENARIO\s*=\s*\{.*?\}\s*(?=\s*(const|var|let|function|//))",
                html,
                flags=re.DOTALL,
            )
            if fallback:
                html = html[: fallback.start()] + rl_json + "\n\n" + html[fallback.end():]

    # 5. Replace OBJECT constants — reading / consolidation / reflection.
    # Authors edit these via dedicated editors; builder routes them straight into
    # content_json under their own keys. Empty/missing → empty placeholder object
    # (template auto-skips empty phases at runtime).
    for (key, const_name) in _OBJECT_CONSTANTS:
        obj = content_json.get(key)
        if not isinstance(obj, dict):
            obj = {}
        # Normalize per-phase known fields (strings → strings; lists → lists).
        if key == "reading":
            checkpoints = obj.get("checkpoints") or []
            if not isinstance(checkpoints, list):
                checkpoints = []
            normalized = {
                "title":       str(obj.get("title") or ""),
                "passage":     str(obj.get("passage") or ""),
                "checkpoints": [
                    {
                        "prompt": str(cp.get("prompt") or "") if isinstance(cp, dict) else "",
                        "ans":    str(cp.get("ans") or "")    if isinstance(cp, dict) else "",
                        "fb":     str(cp.get("fb") or "")     if isinstance(cp, dict) else "",
                    }
                    for cp in checkpoints
                ],
            }
        elif key == "consolidation":
            bullets = obj.get("bullets") or []
            if not isinstance(bullets, list):
                bullets = []
            normalized = {
                "title":        str(obj.get("title") or ""),
                "mnemonic":     str(obj.get("mnemonic") or ""),
                "bullets":      [str(b or "") for b in bullets if str(b or "").strip()],
                "check_prompt": str(obj.get("check_prompt") or ""),
                "check_answer": str(obj.get("check_answer") or ""),
                # Legacy alias used by the parity report
                "recap":        str(obj.get("recap") or obj.get("mnemonic") or ""),
            }
        elif key == "reflection":
            normalized = {
                "summary":    str(obj.get("summary") or ""),
                "question":   str(obj.get("question") or ""),
                "spaced_rep": str(obj.get("spaced_rep") or ""),
                "closing":    str(obj.get("closing") or ""),
            }
        else:
            normalized = obj

        replacement = f"const {const_name} = {json.dumps(normalized, ensure_ascii=False)};"
        # Replace the existing object literal (matches: const NAME = { ... };).
        pattern = rf"const {const_name}\s*=\s*\{{.*?\}};"
        if re.search(pattern, html, flags=re.DOTALL):
            html = re.sub(pattern, lambda _, r=replacement: r, html, count=1, flags=re.DOTALL)

    # Always inject the AI tutor runtime hook before </body>.
    ctx_json = json.dumps(runtime_context, ensure_ascii=False)
    runtime_snippet = (
        f'<script>window.NETS_CTX = {ctx_json};</script>\n'
        f'<script src="/static/runtime/runtime.js"></script>\n'
    )
    html = html.replace('</body>', runtime_snippet + '</body>', 1)

    return html


def verify_template() -> dict:
    """Check that all expected JS constants exist in the template. For startup validation."""
    missing = []
    for (_, const_name) in _ARRAY_CONSTANTS:
        if not re.search(rf"const {const_name}\s*=\s*\[", _TEMPLATE):
            missing.append(const_name)
    if not re.search(r"const RL_SCENARIO\s*=\s*\{", _TEMPLATE):
        missing.append("RL_SCENARIO")
    for (_, const_name) in _OBJECT_CONSTANTS:
        if not re.search(rf"const {const_name}\s*=\s*\{{", _TEMPLATE):
            missing.append(const_name)
    return {"ok": len(missing) == 0, "missing": missing}
