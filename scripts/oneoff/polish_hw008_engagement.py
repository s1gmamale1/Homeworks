"""
One-shot content polish for HW-20260427-008: makes the homework feel
more like a journey and less like a worksheet. Three layers:

1. Strip leading markdown bold (e.g. `**1. Burchakni hisoblash.**`) and
   re-emit as proper <strong> HTML so the runtime's innerHTML rendering
   doesn't show literal asterisks. The original importer left these in
   because the source MD used `**...**` as section headers.

2. Add a single-line narrative hook before the dry "Quyidagi nuqtadan
   ikkita kesuvchi..." problem statement on each Adaptive Quiz item +
   Boss attack. Brief, in-character, formal Siz — gives the student a
   reason to care about THIS specific arrangement of arcs.

3. Restructure Real-Life story:
   - "Sizning Ralingiz" + "Vazifangiz" become inline header pills, not
     dangling markdown asterisks.
   - The W5H block becomes a collapsible-style card with cleaner spacing.
   - The Loyiha Chizmasi heading sits closer to the SVG.

This is intentionally a surgical PATCH, not a rebuild — every field that
has structural correctness (acceptable answers, Bloom tags, capture
flags, answer specs) is left untouched.
"""

import json
import re
import urllib.request

API   = "http://127.0.0.1:8000"
HW_ID = "HW-20260427-008"


def http_get(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=10) as r:
        return json.load(r)


def http_put(path: str, body: dict) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API + path, data=data, method="PUT",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


# ── Markdown → HTML conversion ──────────────────────────────────────────


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", flags=re.DOTALL)
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)")
_TICK_RE = re.compile(r"`([^`\n]+)`")


def md_to_html(s: str) -> str:
    """Convert the lightweight markdown the runtime currently leaks
    (bold, italic, inline code) into the HTML the student actually sees.
    Preserves any pre-existing HTML / SVG / KaTeX tokens."""
    if not s:
        return s
    # Bold first so nested `**foo*bar*`-shaped strings collapse cleanly.
    out = _BOLD_RE.sub(r"<strong>\1</strong>", s)
    out = _ITALIC_RE.sub(r"<em>\1</em>", out)
    out = _TICK_RE.sub(r"<code>\1</code>", out)
    return out


# ── Section polishers ───────────────────────────────────────────────────


def polish_memory_sprint(items: list) -> list:
    """MS items already have clean prompts; just sweep markdown."""
    for q in items:
        q["prompt"] = md_to_html(q.get("prompt") or "")
        q["explain"] = md_to_html(q.get("explain") or "")
    return items


# Per-item narrative hooks for Adaptive Quiz. Each one frames the math
# in a tiny scene before the dry numbers — designed to take ~3 seconds
# to read and give the student something to picture.
AQ_HOOKS = [
    "Tasavvur qiling, siz balandlikdan aylana shaklidagi binoning ikki chetiga qarayapsiz. ",
    "Quyoshli kunda parkning tashqarisidan turib aylanma maydonni kuzatasiz. ",
    "Bu masala teskari savol — javob berilgan, yoyni topish kerak. ",
    "Yana bir teskari savol, ammo bu safar katta yoyni qidirayapmiz. ",
    "Bu safar yoylar qiymat sifatida emas, nisbat sifatida berilgan — algebra kerak bo'ladi. ",
]


def polish_adaptive_quiz(items: list) -> list:
    for i, q in enumerate(items):
        body = q.get("q") or ""
        body = md_to_html(body)
        # Strip any prior hook to keep the script idempotent.
        body = re.sub(
            r'^<span class="rl-hook">[^<]*</span>\s*',
            "",
            body,
            flags=re.IGNORECASE,
        )
        if i < len(AQ_HOOKS):
            hook = AQ_HOOKS[i].strip()
            body = f'<span class="rl-hook">{hook}</span> ' + body
        q["q"] = body
    return items


# Per-attack openers for the Boss. These set up the encounter with one
# line of drama instead of dropping straight into "Quyidagi chizmada...".
# Order matches the existing 5-attack ladder. Tier (oson / o'rta / qiyin)
# is rendered as a text pill in the runtime CSS, not via emoji.
BOSS_OPENERS = [
    ("1-Hujum · Asosiy hisob (oson)",
     "Boss sizga eng oddiy holatni beradi. Toza yechim — toza zarar."),
    ("2-Hujum · Teskari yoy (oson)",
     "Bu safar javobgina emas, yoyni qidirasiz. Tenglama tuzing."),
    ("3-Hujum · Ikkala yoy (o'rta)",
     "Endi qiyinroq — ikkita noma'lum bor, ikkita tenglama kerak."),
    ("4-Hujum · Sifat tekshiruvi (o'rta)",
     "Telekom muhandisi sifatida hisoblang va keyin xulosa chiqaring: signal o'tib boradimi?"),
    ("5-Hujum · Loyihaviy talqin (qiyin)",
     "Yakuniy savol uch bosqichli: hisoblang, kengaytiring, tushuntiring."),
]


def polish_boss(items: list) -> list:
    for i, q in enumerate(items):
        prompt = q.get("q") or ""
        # Strip ALL prior boss-opener blocks (idempotency — the script
        # may run multiple times and openers should not stack). The
        # opener spans an outer <div class="boss-opener">...</div> with
        # exactly two children, so the closing `</div></div>` is unique.
        prev = None
        while prev != prompt:
            prev = prompt
            prompt = re.sub(
                r'<div class="boss-opener">\s*<div class="boss-opener-title">[^<]*</div>\s*<div class="boss-opener-drama">[^<]*</div>\s*</div>\s*',
                "",
                prompt,
            )
        # Drop the leading `**N-Hujum: ...**` markdown header — it'll be
        # replaced with a proper HTML opener below.
        prompt = re.sub(
            r"^\*\*\d+-Hujum[^*]*\*\*\s*",
            "",
            prompt,
            flags=re.DOTALL,
        )
        prompt = md_to_html(prompt)
        if i < len(BOSS_OPENERS):
            title, drama = BOSS_OPENERS[i]
            opener = (
                f'<div class="boss-opener">'
                f'  <div class="boss-opener-title">{title}</div>'
                f'  <div class="boss-opener-drama">{drama}</div>'
                f'</div>'
            )
            prompt = opener + prompt
        q["q"] = prompt
        if q.get("hint"):
            q["hint"] = md_to_html(q["hint"])
    return items


def polish_real_life(rl: dict) -> dict:
    """Restructure the story so the role + mission read as a briefing
    card, then the scenario flows as plain prose, then the Loyiha Chizmasi
    sits under a proper subheading."""
    # Hard reset — the polished story is fully reauthored each run from
    # a canonical source. This makes the script idempotent: running it
    # twice yields the same output, and any stale nested HTML from an
    # earlier polish run is wiped out.
    story = (
        "Bekat aylanma shakldagi yirik savdo markazining yonidan o'tadi. "
        "Sizning kuzatuv va boshqaruv nuqtangiz ($P$) savdo markazi "
        "binosidan tashqarida joylashgan. Sizdan bekatning ikkita "
        "kirish-chiqish yo'lagini (geometrik jihatdan aylananing "
        "kesuvchilarini) binoga qaratib tortish talab etilmoqda. "
        "Yo'laklar bino aylanasi bilan kesishganda, uzoqdagi qism "
        "(katta yoy) $150^\\circ$ ni va yaqindagi qism (kichik yoy) "
        "$70^\\circ$ ni tashkil etadi. Yo'laklarning $P$ nuqtada qanday "
        "burchak ostida kesishishini va muqobil variantlarni aniq "
        "hisoblashingiz kerak — aks holda yo'lovchilar oqimi xato "
        "taqsimlanadi va tirbandlik yuzaga keladi.\n\n"
        "### Yordamchi Tizim (W5H)\n"
        "* **Kim/Nima?** Metro bosh muhandisi (Siz) bekat yo'laklarining kesishish burchagini topishi kerak.\n"
        "* **Qayerda?** Toshkent metropoliteni, aylanma savdo markazi yonida.\n"
        "* **Qachon?** Qurilishdan oldingi arxitektura loyihalash bosqichida.\n"
        "* **Nima uchun?** Burchakning to'g'ri o'lchami yo'lovchilarning xavfsiz va keng harakatlanishini ta'minlaydi.\n"
        "* **Qanday?** $\\alpha = \\frac{\\text{Katta yoy} - \\text{Kichik yoy}}{2}$ formulasi orqali.\n\n"
        "### Loyiha Chizmasi\n\n"
        '<div class="svg-wrap"><svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg" style="font-family: sans-serif; font-size: 14px;">\n'
        '  <rect width="100%" height="100%" fill="#F3F4F6"/>\n'
        '  <text x="10" y="20" fill="#6B7280" font-size="12">Loyihaviy Chizma — Obyekt: Savdo Markazi</text>\n'
        '  <circle cx="180" cy="100" r="60" fill="#E5E7EB" stroke="#9CA3AF" stroke-width="2"/>\n'
        '  <line x1="20" y1="100" x2="235" y2="40" stroke="#4B5563" stroke-width="2" stroke-dasharray="4"/>\n'
        '  <line x1="20" y1="100" x2="235" y2="160" stroke="#4B5563" stroke-width="2" stroke-dasharray="4"/>\n'
        '  <path d="M 235,40 A 60 60 0 0 1 235,160" fill="none" stroke="#2563EB" stroke-width="4"/>\n'
        '  <text x="250" y="105" fill="#2563EB" font-weight="bold">150°</text>\n'
        '  <path d="M 125,58 A 60 60 0 0 0 125,142" fill="none" stroke="#2563EB" stroke-width="4"/>\n'
        '  <text x="85" y="105" fill="#2563EB" font-weight="bold">70°</text>\n'
        '  <path d="M 45,91 A 25 25 0 0 0 45,109" fill="none" stroke="#EA580C" stroke-width="3"/>\n'
        '  <text x="50" y="105" fill="#EA580C" font-weight="bold">P = ?</text>\n'
        '  <circle cx="20" cy="100" r="4" fill="#111827"/>\n'
        '</svg></div>'
    )

    # Pull out the W5H block (between "### 🧩 Yordamchi Tizim" and the
    # next "### " heading) so we can re-emit it as a styled list.
    w5h_pat = re.compile(
        r"###\s*[^\n]*Yordamchi Tizim[^\n]*\n(.*?)(?=\n###\s|\Z)",
        flags=re.DOTALL,
    )
    w5h_match = w5h_pat.search(story)
    w5h_lines = []
    if w5h_match:
        for line in w5h_match.group(1).splitlines():
            line = line.strip()
            m = re.match(r"\*\s*\*\*([^*]+)\*\*\s*(.+)", line)
            if m:
                w5h_lines.append((m.group(1).strip(), m.group(2).strip()))
        # Remove the original W5H block (we'll re-insert as HTML).
        story = w5h_pat.sub("", story)

    # Pull out the Loyiha Chizmasi block.
    chizma_pat = re.compile(
        r"###\s*[^\n]*Loyiha Chizmasi[^\n]*\n(.*?)(?=\n###\s|\Z)",
        flags=re.DOTALL,
    )
    chizma_match = chizma_pat.search(story)
    chizma_html = ""
    if chizma_match:
        # Keep whatever raw HTML/SVG was inside.
        chizma_html = chizma_match.group(1).strip()
        story = chizma_pat.sub("", story)

    # Extract the "two role lines" + flowing narrative paragraph that
    # remain in story after the headings were stripped.
    body = md_to_html(story.strip())

    # Compose the final story with explicit semantic structure.
    parts = []
    parts.append(
        '<div class="rl-briefing">'
        '<div class="rl-briefing-row"><span class="rl-briefing-label">Sizning rolingiz</span>'
        '<span class="rl-briefing-value">Toshkent metropolitenining yangi "Halqa yo\'li" '
        "liniyasi bo'yicha bosh muhandis</span></div>"
        '<div class="rl-briefing-row"><span class="rl-briefing-label">Vazifa</span>'
        '<span class="rl-briefing-value">Yangi bekat loyihasini tasdiqlash</span></div>'
        '</div>'
    )
    parts.append('<div class="rl-narrative">' + body + '</div>')

    if w5h_lines:
        items_html = "".join(
            f'<li><strong>{label}</strong> {value}</li>'
            for label, value in w5h_lines
        )
        parts.append(
            '<details class="rl-w5h">'
            '<summary>Yordamchi tahlil (W5H) — bosib oching</summary>'
            f'<ul class="rl-w5h-list">{items_html}</ul>'
            '</details>'
        )

    if chizma_html:
        parts.append(
            '<div class="rl-blueprint">'
            '<div class="rl-blueprint-title">Loyiha chizmasi</div>'
            f'{chizma_html}'
            '</div>'
        )

    rl["story"] = "\n".join(parts)

    # Per-question titles, used to re-emit the heading regardless of
    # whether the input is raw markdown (`**N. Title.**`) or already-
    # polished HTML from a previous script run. Order matches q1..q5.
    rl_titles = [
        ("1", "Burchakni hisoblash"),
        ("2", "Arxitektor xatosini to'g'irlash"),
        ("3", "O'zgarishlar ssenariysi (What-if)"),
        ("4", "Chamalab tekshirish"),
        ("5", "Tahlil va qaror (Interpretation)"),
    ]

    # Polish each sub-question prompt.
    for idx, k in enumerate(("q1", "q2", "q3", "q4", "q5")):
        q = rl.get(k) or {}
        prompt = q.get("prompt") or ""
        # Idempotency — strip any prior heading wrapper, then recover
        # the stem (or fall through to the raw text if neither wrapper
        # is present, e.g. on a freshly-imported homework).
        prompt = re.sub(
            r'<div class="rl-q-heading">.*?</div>\s*',
            "",
            prompt,
            flags=re.DOTALL,
        )
        m_stem = re.search(
            r'<div class="rl-q-stem">(.*?)</div>\s*$',
            prompt,
            flags=re.DOTALL,
        )
        if m_stem:
            prompt = m_stem.group(1)
        # Drop leading `**N. Title.**` markdown that the original
        # importer left in.
        prompt = re.sub(
            r"^\*\*\d+\.\s*[^*]+\*\*\s*",
            "",
            prompt,
            flags=re.DOTALL,
        )
        # Convert remaining markdown to HTML.
        rest = md_to_html(prompt.strip())
        num, title = rl_titles[idx] if idx < len(rl_titles) else (str(idx + 1), "")
        q["prompt"] = (
            f'<div class="rl-q-heading"><strong>{num}-savol — {title}</strong></div>'
            f'<div class="rl-q-stem">{rest}</div>'
        )
        if q.get("fb"):
            q["fb"] = md_to_html(q["fb"])
        rl[k] = q

    return rl


def polish_reflection(ref: dict) -> dict:
    ref["summary"] = md_to_html(ref.get("summary") or "")
    ref["spaced_rep"] = md_to_html(ref.get("spaced_rep") or "")
    ref["closing"] = md_to_html(ref.get("closing") or "")
    # The reflection question — make it more specific + warmer.
    ref["question"] = (
        '<em>(Bu savol baholanmaydi — ichingizda yoki ovoz chiqarib '
        'erkin javob bering.)</em><br><br>'
        "Tasavvur qiling, do'stingiz \"aylananing tashqarisidagi burchakni "
        "ham qo'shish kerakmi?\" deb so'radi. Siz unga bir gap bilan, "
        "imkoni boricha sodda tilda qanday javob berasiz?"
    )
    return ref


# ── Light CSS additions ─────────────────────────────────────────────────


# Optional polish — author can opt in via content_json.meta.engagement_css.
# We don't inject CSS into the runtime template here; instead the new
# class names degrade gracefully (browser default styling) when CSS is
# missing. The recommended classes are documented for the platform team:
ENGAGEMENT_CSS_HINT = """
/* Optional CSS for engagement classes (add to perfect_homework.html):
   .rl-hook            { display:inline-block; padding:2px 8px; border-radius:8px;
                         background:rgba(99,184,255,0.12); color:var(--accent);
                         font-size:13px; margin-right:6px; }
   .boss-opener        { padding:10px 14px; margin-bottom:12px; border-radius:10px;
                         background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.25); }
   .boss-opener-title  { font-weight:700; color:#fca5a5; }
   .boss-opener-drama  { font-size:13px; color:var(--text-dim); margin-top:4px; }
   .rl-briefing        { display:grid; gap:8px; padding:14px; margin-bottom:14px;
                         background:rgba(99,184,255,0.06); border-radius:10px; }
   .rl-briefing-row    { display:flex; gap:10px; }
   .rl-briefing-label  { min-width:160px; color:var(--text-dim); font-size:13px; }
   .rl-briefing-value  { font-weight:600; }
   .rl-narrative       { margin-bottom:14px; }
   .rl-w5h             { margin-bottom:14px; }
   .rl-w5h summary     { cursor:pointer; padding:8px 12px; background:rgba(168,85,247,0.07);
                         border-radius:8px; font-weight:600; }
   .rl-w5h-list        { padding:10px 26px; }
   .rl-blueprint       { margin-bottom:14px; }
   .rl-blueprint-title { font-weight:700; margin-bottom:6px; color:var(--accent); }
   .rl-q-heading       { font-size:15px; margin-bottom:8px; color:var(--text); }
   .rl-q-stem          { line-height:1.55; }
*/
"""


def main() -> None:
    print(f"GET {API}/api/homeworks/{HW_ID}")
    current = http_get(f"/api/homeworks/{HW_ID}")
    cj = current["content_json"]

    print("Polishing memory_sprint...")
    cj["memory_sprint"] = polish_memory_sprint(cj.get("memory_sprint", []))
    print("Polishing gb_adaptive_quiz...")
    cj["gb_adaptive_quiz"] = polish_adaptive_quiz(cj.get("gb_adaptive_quiz", []))
    print("Polishing boss_questions...")
    cj["boss_questions"] = polish_boss(cj.get("boss_questions", []))
    print("Polishing real_life...")
    cj["real_life"] = polish_real_life(cj.get("real_life") or {})
    print("Polishing reflection...")
    cj["reflection"] = polish_reflection(cj.get("reflection") or {})

    print(f"PUT {API}/api/homeworks/{HW_ID}")
    updated = http_put(f"/api/homeworks/{HW_ID}", {
        "title": current["title"],
        "content_json": cj,
    })

    print()
    print("✓ updated id   :", updated.get("id"))
    print("✓ MS prompts   :", "<strong>" in (cj["memory_sprint"][0].get("prompt") or "")
          or "<strong>" in (cj["memory_sprint"][2].get("prompt") or ""))
    print("✓ AQ has hooks :", '<span class="rl-hook">' in cj["gb_adaptive_quiz"][0]["q"])
    print("✓ Boss openers :", '<div class="boss-opener">' in cj["boss_questions"][0]["q"])
    print("✓ RL briefing  :", '<div class="rl-briefing">' in cj["real_life"]["story"])
    print("✓ RL Q1 hdr    :", 'rl-q-heading' in cj["real_life"]["q1"]["prompt"])

    print()
    print(ENGAGEMENT_CSS_HINT)


if __name__ == "__main__":
    main()
