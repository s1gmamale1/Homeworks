"""
Rebuild HW-20260427-008 content_json strictly from
D:/Aylananing Kesuvchilari Burchaklari Xossasi (grade 8 geometry).md

The earlier import (push_playable_to_builder.py via the playable JS bundle)
left several issues:
  - gb_adaptive_quiz items all tagged tier=MEDIUM (causing repeats once the
    runtime settled on EASY/HARD); now properly tier-distributed 2/2/1.
  - memory_sprint prompts contained leaked option markers ("✓ B)") inline.
  - boss_questions had inline tag markdown duplicated inside `q`, empty
    answer_specs (so AI grading had nothing concrete to score against),
    and missing hints.
  - real_life.story dumped Q1-Q5 prompt text into the story body, and q5
    contained text from the consolidation phase instead of the interpretation
    sub-question.
  - panel titles dropped the leading 'N' from "NIMA UCHUN" twice.
  - gb_why_chain now used as Sentence Fill; the runtime was relabeled
    accordingly, but content needed inv values to be authoritative.

This script writes the canonical content_json by hand and PUTs it to
http://127.0.0.1:8000/api/homeworks/HW-20260427-008. Panels' page blocks
are kept (they carry the source SVGs) but titles are corrected.
"""

import json
import urllib.request

API = "http://127.0.0.1:8000"
HW_ID = "HW-20260427-008"


# ── Helpers ─────────────────────────────────────────────────────────────

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


# ── Source content (verbatim from the MD) ───────────────────────────────

PANEL_TITLES = [
    "Nima Uchun Bu Kerak?",
    "Yaxshiroq Tushuntirish",
    "Kelib Chiqishi",
    "Misollar",
    "Chizma → Teorema Tarjimasi",
    "Sanoatdagi Qo'llanilishi",
    "Nima Uchun Bu Muhim?",
]

FLASHCARDS = [
    ("Kesuvchi (Aylana kesuvchisi)",
     "Aylanani ikkita nuqtada kesib o'tuvchi to'g'ri chiziq."),
    ("Urinma (Aylana urinmasi)",
     "Aylana bilan faqat bitta umumiy nuqtaga ega bo'lgan, aylanaga urinib o'tuvchi to'g'ri chiziq."),
    ("Vatar",
     "Aylananing ixtiyoriy ikkita nuqtasini tutashtiruvchi kesma. Misol: Eng katta vatar — aylananing diametri."),
    ("Markaziy burchak",
     "Uchi aylananing markazida yotgan burchak. U o'zi tiralgan yoyning gradus o'lchoviga teng. Misol: Yoy 60° bo'lsa, markaziy burchak = 60°."),
    ("Ichki chizilgan burchak",
     "Uchi aylanada yotib, tomonlari aylanani kesib o'tuvchi burchak. U o'zi tiralgan yoyining yarmiga teng. Misol: Yoy 80° → burchak = 40°."),
    ("Ikkita kesuvchi orasidagi burchak",
     "α = (∪Katta yoy − ∪Kichik yoy) / 2. Misol: Katta yoy 100°, kichik yoy 30° → α = (100° − 30°) / 2 = 35°."),
    ("Ikkita vatar orasidagi burchak",
     "Aylana ichida kesishuvchi vatarlar orasidagi burchak: α = (∪AB + ∪CD) / 2. Misol: Yoylar 40° va 60° → α = (40° + 60°) / 2 = 50°."),
    ("Urinma va vatar orasidagi burchak",
     "Urinish nuqtasidan o'tkazilgan vatar va urinma orasidagi burchak: α = ∪AB / 2. Misol: Vatar tortib turgan yoy 120° → α = 60°."),
    ("Urinma va kesuvchi orasidagi burchak",
     "α = (∪Katta yoy − ∪Kichik yoy) / 2. Misol: Kesuvchi va urinma orasidagi yoylar 140° va 40° → α = (140° − 40°) / 2 = 50°."),
    ("Ikkita urinma orasidagi burchak",
     "α = (∪Katta yoy − ∪Kichik yoy) / 2. Misol: Urinish nuqtalari aylanani 260° va 100° yoylarga ajratsa → α = (260° − 100°) / 2 = 80°."),
]

# ── Memory Sprint (7 items) ─────────────────────────────────────────────

MEMORY_SPRINT = [
    {  # 1. MC
        "type": "KO",
        "prompt": "Aylana tashqarisidagi nuqtadan o'tkazilgan ikkita kesuvchi orasidagi burchak qanday topiladi?",
        "subtitle": "",
        "tags": "[Bloom: L1 | PISA: L1]",
        "options": [
            "Yoylar ayirmasining yarmiga teng",
            "Yoylar yig'indisining yarmiga teng",
            "Yoylar ayirmasiga teng",
            "Faqat katta yoyning yarmiga teng",
        ],
        "correct": 0,
        "explain": "Kesuvchilar orasidagi burchakni topish uchun doimo katta yoydan kichik yoy ayirilib, natija ikkiga bo'linadi. (B variant — ichki vatarlar qoidasi bilan adashtirish; C variant — 2 ga bo'lish unutilgan.)",
    },
    {  # 2. T/F
        "type": "TF",
        "prompt": "Aylananing kesuvchisi aylanani faqat bitta nuqtada kesib o'tadi.",
        "subtitle": "",
        "tags": "[Bloom: L1 | PISA: L1]",
        "options": ["To'g'ri", "Noto'g'ri"],
        "correct": 1,
        "explain": "Noto'g'ri. Kesuvchi aylanani ikkita nuqtada kesib o'tadi; faqat bitta nuqtada urinib o'tuvchi chiziq \"urinma\" deyiladi.",
    },
    {  # 3. MC — error spotting
        "type": "KO",
        "prompt": "O'quvchi masala yechishda $\\alpha = \\frac{100^\\circ + 40^\\circ}{2}$ deb yozdi. U qanday xatoga yo'l qo'ydi?",
        "subtitle": "",
        "tags": "[Bloom: L2 | PISA: L2]",
        "options": [
            "Tashqi burchak uchun yoylarni ayirish o'rniga qo'shib yubordi",
            "Natijani 2 ga bo'lishni esdan chiqardi",
            "Kichik yoydan katta yoyni ayirdi",
            "Yoylar qiymatini bir-biriga ko'paytirdi",
        ],
        "correct": 0,
        "explain": "Yoylarni qo'shish qoidasi aylana ichida kesishadigan vatarlarga tegishli. Tashqaridagi burchak uchun har doim ayirish amali bajarilishi kerak.",
    },
    {  # 4. YNNG
        "type": "YNNG",
        "prompt": "Bobda aytilishicha, qadimgi Xorazm olimlari bu teoremadan yulduzlarni kuzatuvchi teleskoplarda foydalanishgan.",
        "subtitle": "",
        "tags": "[Bloom: L2 | PISA: L1]",
        "options": ["Ha", "Yo'q", "Aytilmagan"],
        "correct": 2,
        "explain": "Aytilmagan. Darslikda minoralar va gumbazlar atrofida ishlagan me'morlar va yer o'lchovchilari haqida gapirilgan, teleskoplar haqida emas.",
    },
    {  # 5. T/F
        "type": "TF",
        "prompt": "Ikkita kesuvchi orasidagi burchakni topish formulasini qo'llash uchun aylananing markazi qayerda joylashganini aniq bilishimiz shart.",
        "subtitle": "",
        "tags": "[Bloom: L2 | PISA: L1]",
        "options": ["To'g'ri", "Noto'g'ri"],
        "correct": 1,
        "explain": "Noto'g'ri. Burchakni topish uchun faqat aylananing ustidagi yoylar o'lchovini (katta va kichik yoy) bilish yetarli; markazning koordinatalari shart emas.",
    },
    {  # 6. MC — order of operations
        "type": "KO",
        "prompt": "Katta yoy $120^\\circ$ va kichik yoy $40^\\circ$ ga teng. Burchakni hisoblashda amallar tartibi qanday bo'lishi kerak?",
        "subtitle": "",
        "tags": "[Bloom: L2 | PISA: L2]",
        "options": [
            "Avval qavs ichida $120^\\circ$ dan $40^\\circ$ ayiriladi, keyin 2 ga bo'linadi",
            "Faqat $120^\\circ$ yoy 2 ga bo'linib, so'ngra $40^\\circ$ ayiriladi",
            "Ikkala yoy bir-biriga qo'shiladi va 2 ga bo'linadi",
            "Yoylar ayirmasi topiladi, lekin 2 ga bo'linmaydi",
        ],
        "correct": 0,
        "explain": "To'g'ri tartib: $\\alpha = (120^\\circ - 40^\\circ) / 2$ — kasr suratidagi ayirma to'liq hisoblangandan keyingina bo'lish amali bajariladi.",
    },
    {  # 7. YNNG
        "type": "YNNG",
        "prompt": "Flash kartalar qoidasiga ko'ra, aylanadan tashqarida kesishuvchi ikkita urinma orasidagi burchak ham aynan shu (ayirma) formulasi bilan topiladi.",
        "subtitle": "",
        "tags": "[Bloom: L2 | PISA: L2]",
        "options": ["Ha", "Yo'q", "Aytilmagan"],
        "correct": 0,
        "explain": "Ha. Ikkita kesuvchi orasidagi burchak ham, ikkita urinma orasidagi burchak ham yoylar ayirmasining yarmiga teng degan umumiy qonuniyatga bo'ysunadi.",
    },
]

# ── Adaptive Quiz (5 items, 2 easy / 2 medium / 1 hard) ─────────────────

AQ_Q1_SVG = '''<svg viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg" style="font-family: sans-serif; font-size: 12px;">
  <circle cx="120" cy="75" r="50" fill="none" stroke="#9CA3AF" stroke-width="2"/>
  <polygon points="10,75 160,40 160,110" fill="none" stroke="#9CA3AF" stroke-width="2" stroke-linejoin="round"/>
  <text x="5" y="80" fill="#111827">P</text>
  <text x="170" y="75" fill="#2563EB">100°</text>
  <text x="75" y="75" fill="#2563EB">40°</text>
  <path d="M 25,70 A 15 15 0 0 0 25,80" fill="none" stroke="#EA580C" stroke-width="2"/>
</svg>'''

AQ_Q3_SVG = '''<svg viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg" style="font-family: sans-serif; font-size: 12px;">
  <circle cx="120" cy="75" r="50" fill="none" stroke="#9CA3AF" stroke-width="2"/>
  <polygon points="10,75 160,25 160,125" fill="none" stroke="#9CA3AF" stroke-width="2" stroke-linejoin="round"/>
  <text x="5" y="80" fill="#111827">P</text>
  <text x="170" y="75" fill="#2563EB">150°</text>
  <text x="75" y="75" fill="#EA580C">?</text>
  <path d="M 25,68 A 20 20 0 0 0 25,82" fill="none" stroke="#16A34A" stroke-width="2"/>
  <text x="30" y="79" fill="#16A34A">45°</text>
</svg>'''

GB_ADAPTIVE_QUIZ = [
    {
        "id": "A1",
        "tier": "easy",
        "tags": "[Bloom: L3 | PISA: L2]",
        "q": ("Aylanadan tashqaridagi $P$ nuqtadan ikkita kesuvchi o'tkazilgan. "
              "Ular aylanadan $100^\\circ$ (katta yoy) va $40^\\circ$ (kichik yoy) "
              "yoylarni ajratib turadi. $\\angle P$ ning qiymatini toping."
              "<br><div class=\"svg-wrap\">" + AQ_Q1_SVG + "</div>"),
        "ans": ["30", "30°", "30 gradus"],
        "hint": "Javob: 30°. Yechim: $\\alpha = (100^\\circ - 40^\\circ) / 2 = 30^\\circ$.",
        "capture": True,
    },
    {
        "id": "A2",
        "tier": "easy",
        "tags": "[Bloom: L3 | PISA: L2]",
        "q": ("$P$ nuqtadan aylanaga bitta urinma va bitta kesuvchi o'tkazildi. "
              "Katta yoy $140^\\circ$, kichik yoy $60^\\circ$. "
              "Urinma va kesuvchi orasidagi burchakni toping."),
        "ans": ["40", "40°", "40 gradus"],
        "hint": "Javob: 40°. Yechim: $\\alpha = (140^\\circ - 60^\\circ) / 2 = 40^\\circ$.",
        "capture": True,
    },
    {
        "id": "A3",
        "tier": "medium",
        "tags": "[Bloom: L4 | PISA: L3]",
        "q": ("Ikkita kesuvchi orasidagi burchak $45^\\circ$ ga teng. "
              "Ular aylanadan ajratgan katta yoy $150^\\circ$ bo'lsa, "
              "kichik yoy necha gradus bo'ladi?"
              "<br><div class=\"svg-wrap\">" + AQ_Q3_SVG + "</div>"),
        "ans": ["60", "60°", "60 gradus"],
        "hint": "Javob: 60°. Tenglama: $45^\\circ = (150^\\circ - x) / 2 \\Rightarrow x = 60^\\circ$.",
        "capture": True,
    },
    {
        "id": "A4",
        "tier": "medium",
        "tags": "[Bloom: L4 | PISA: L3]",
        "q": ("Aylana tashqarisidagi burchak $50^\\circ$ ni tashkil etadi. "
              "Agar ushbu burchak hosil qilgan kichik yoy $20^\\circ$ bo'lsa, "
              "katta yoyning gradus o'lchovini hisoblang."),
        "ans": ["120", "120°", "120 gradus"],
        "hint": "Javob: 120°. Tenglama: $50^\\circ = (x - 20^\\circ) / 2 \\Rightarrow x = 120^\\circ$.",
        "capture": True,
    },
    {
        "id": "A5",
        "tier": "hard",
        "tags": "[Bloom: L5 | PISA: L4]",
        "q": ("Aylana tashqarisidagi $P$ burchak $40^\\circ$ ga teng. "
              "Ikkita kesuvchi ajratgan katta yoy kichik yoydan 3 marta katta "
              "ekanligi ma'lum ($3x$ va $x$). Kichik yoyning qiymatini toping."),
        "ans": ["40", "40°", "40 gradus"],
        "hint": "Javob: 40°. $40^\\circ = (3x - x)/2 = x \\Rightarrow x = 40^\\circ$.",
        "capture": True,
    },
]

# ── Tile Match (gb_memory_match) — 6 pairs ──────────────────────────────

GB_MEMORY_MATCH = [
    ["$\\alpha = \\frac{\\cup AB - \\cup CD}{2}$",
     "Aylanadan tashqarida hosil bo'lgan burchak formulasi"],
    ["Urinma",
     "Aylana bilan faqat $1$ ta umumiy nuqtaga ega bo'lgan to'g'ri chiziq"],
    ["Vatar",
     "Aylanadagi ixtiyoriy $2$ ta nuqtani tutashtiruvchi kesma"],
    ["$50^\\circ = \\frac{130^\\circ - x}{2}$",
     "$x = 30^\\circ$"],
    ["Katta yoy $110^\\circ$, kichik yoy $30^\\circ$",
     "Burchak $40^\\circ$"],
    ["Ichki chizilgan burchak",
     "O'zi tiralgan yoyning yarmiga teng burchak"],
]

# ── Sentence Fill (gb_why_chain slot) — 5 items ─────────────────────────

GB_WHY_CHAIN = [
    {
        "q": "Aylananing tashqarisidagi nuqtadan o'tkazilgan ikkita kesuvchi orasidagi burchak, ular orasida yotgan yoylar ________ yarmiga teng.",
        "inv": "ayirmasining",
        "reprompts": [
            "Eslatma: aylana tashqarisidagi burchak — bu yig'indi emas. Yoylarni qaysi amal bilan birlashtiramiz?",
            "Bitta so'z bilan: yoylarni ayirib, natijani 2 ga bo'lamiz. Bo'shliqqa qaysi bosh kelishik shakli mos keladi?",
        ],
    },
    {
        "q": "Hisoblash: Agar katta yoy $100^\\circ$ va kichik yoy $40^\\circ$ bo'lsa, burchak $\\alpha = \\frac{100^\\circ \\;\\_\\_\\_\\;40^\\circ}{2}$ tenglamasi orqali hisoblanadi.",
        "inv": "-",
        "reprompts": [
            "Eslatma: aylana tashqarisidagi burchak formulasini eslang.",
            "Tashqaridagi burchak: katta yoydan kichikni ayirish.",
        ],
    },
    {
        "q": "Tenglama tuzish: Agar kesuvchilar orasidagi burchak $30^\\circ$ va kichik yoy $20^\\circ$ bo'lsa, noma'lum katta yoyni topish uchun tenglama $30^\\circ = \\frac{x - 20^\\circ}{\\;\\_\\_\\_\\;}$ ko'rinishida tuziladi.",
        "inv": "2",
        "reprompts": [
            "Eslatma: formulada yoylar ayirmasi qaysi songa bo'linadi?",
            "Burchak — yoylar ayirmasining yarmiga teng. Yarmi — nechiga bo'lish?",
        ],
    },
    {
        "q": "Tahlil: Ikkita urinma orasidagi burchakni hisoblashda ham aylana yoylarini ________ qoidasi o'zgarishsiz ishlatiladi.",
        "inv": "ayirish",
        "reprompts": [
            "Eslatma: tashqaridagi burchak nima qiladi — qo'shadi yoki ayiradi?",
            "Tashqaridagi har qanday burchak — yoylarni ayirib, 2 ga bo'lamiz.",
        ],
    },
    {
        "q": "Algebrik almashtirish: Agar burchak $\\alpha$, katta yoy $150^\\circ$ va kichik yoy $y$ bo'lsa, noma'lum $y$ ni topish uchun formuladan foydalanish amali qadami quyidagicha bo'ladi: $y = 150^\\circ - \\;\\_\\_\\_\\;\\cdot\\alpha$.",
        "inv": "2",
        "reprompts": [
            "Eslatma: $\\alpha = (150^\\circ - y)/2$ ni $y$ uchun yeching.",
            "Ikkala tomonni 2 ga ko'paytirsangiz, $\\alpha$ oldida qaysi son paydo bo'ladi?",
        ],
    },
]

# ── Real-Life ───────────────────────────────────────────────────────────

REAL_LIFE_SVG = '''<svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg" style="font-family: sans-serif; font-size: 14px;">
  <rect width="100%" height="100%" fill="#F3F4F6"/>
  <text x="10" y="20" fill="#6B7280" font-size="12">Loyihaviy Chizma — Obyekt: Savdo Markazi</text>
  <circle cx="180" cy="100" r="60" fill="#E5E7EB" stroke="#9CA3AF" stroke-width="2"/>
  <line x1="20" y1="100" x2="235" y2="40" stroke="#4B5563" stroke-width="2" stroke-dasharray="4"/>
  <line x1="20" y1="100" x2="235" y2="160" stroke="#4B5563" stroke-width="2" stroke-dasharray="4"/>
  <path d="M 235,40 A 60 60 0 0 1 235,160" fill="none" stroke="#2563EB" stroke-width="4"/>
  <text x="250" y="105" fill="#2563EB" font-weight="bold">150°</text>
  <path d="M 125,58 A 60 60 0 0 0 125,142" fill="none" stroke="#2563EB" stroke-width="4"/>
  <text x="85" y="105" fill="#2563EB" font-weight="bold">70°</text>
  <path d="M 45,91 A 25 25 0 0 0 45,109" fill="none" stroke="#EA580C" stroke-width="3"/>
  <text x="50" y="105" fill="#EA580C" font-weight="bold">P = ?</text>
  <circle cx="20" cy="100" r="4" fill="#111827"/>
</svg>'''

REAL_LIFE_STORY = (
    "**Sizning Ralingiz:** Siz Toshkent metropolitenining yangi \"Halqa yo'li\" "
    "liniyasida bosh muhandissiz.\n\n"
    "**Vazifangiz:** Yangi bekat loyihasini tasdiqlash.\n\n"
    "Bekat aylanma shakldagi yirik savdo markazining yonidan o'tadi. Sizning "
    "kuzatuv va boshqaruv nuqtangiz ($P$) savdo markazi binosidan tashqarida "
    "joylashgan. Sizdan bekatning ikkita kirish-chiqish yo'lagini (geometrik "
    "jihatdan aylananing kesuvchilarini) binoga qaratib tortish talab "
    "etilmoqda. Yo'laklar bino aylanasi bilan kesishganda, uzoqdagi qism "
    "(katta yoy) $150^\\circ$ ni va yaqindagi qism (kichik yoy) $70^\\circ$ ni "
    "tashkil etadi. Yo'laklarning $P$ nuqtada qanday burchak ostida "
    "kesishishini va muqobil variantlarni aniq hisoblashingiz kerak — aks "
    "holda yo'lovchilar oqimi xato taqsimlanadi va tirbandlik yuzaga keladi.\n\n"
    "### 🧩 Yordamchi Tizim (W5H)\n"
    "* **Kim/Nima?** Metro bosh muhandisi (Siz) bekat yo'laklarining kesishish burchagini topishi kerak.\n"
    "* **Qayerda?** Toshkent metropoliteni, aylanma savdo markazi yonida.\n"
    "* **Qachon?** Qurilishdan oldingi arxitektura loyihalash bosqichida.\n"
    "* **Nima uchun?** Burchakning to'g'ri o'lchami yo'lovchilarning xavfsiz va keng harakatlanishini ta'minlaydi.\n"
    "* **Qanday?** $\\alpha = \\frac{\\text{Katta yoy} - \\text{Kichik yoy}}{2}$ formulasi orqali.\n\n"
    "### 📊 Loyiha Chizmasi\n\n"
    "<div class=\"svg-wrap\">" + REAL_LIFE_SVG + "</div>"
)

REAL_LIFE = {
    "badge": "VAZIFA · Halqa yo'li metro bekati",
    "story": REAL_LIFE_STORY,
    "endTitle": "Loyiha tasdiqlandi",
    "endSub": "Siz barcha hisob-kitoblarni muvaffaqiyatli yakunladingiz!",
    "q1": {
        "prompt": ("**1. Burchakni hisoblash.** Savdo markazining kuzatuv nuqtasi "
                   "($P$) dan o'tuvchi ikkita yo'lak qanday burchak ostida "
                   "kesishishini aniqlang. Daftaringizda formulani yozing va "
                   "hisoblashni Notebook Capture orqali rasmga oling."),
        "ans": "40",
        "fb": "To'g'ri! $\\alpha = (150^\\circ - 70^\\circ) / 2 = 40^\\circ$.",
        "capture": True,
        "tags": "[Bloom: L3 | PISA: L2]",
    },
    "q2": {
        "prompt": ("**2. Arxitektor xatosini to'g'irlash.** Boshqa zaxira "
                   "chiqish yo'lagida ($Q$ nuqta) arxitektorlar burchakni "
                   "$30^\\circ$ bo'lishini talab qilishmoqda. Bu yo'laklar "
                   "aylananing uzoq qismidan $110^\\circ$ li yoyni ajratib "
                   "turadi. Ushbu loyiha amalga oshishi uchun, aylananing "
                   "yaqin qismidagi kichik yoy necha gradus bo'lishi kerak?"),
        "ans": "50",
        "fb": "To'g'ri! $30^\\circ = (110^\\circ - x)/2 \\Rightarrow x = 50^\\circ$.",
        "capture": True,
        "tags": "[Bloom: L4 | PISA: L3]",
    },
    "q3": {
        "prompt": ("**3. O'zgarishlar ssenariysi (What-if).** Loyihaga "
                   "o'zgartirish kiritildi. Savdo markazining orqa tarafida "
                   "kengaytirish ishlari sababli, katta yoy $20\\%$ ga "
                   "kattalashdi. Kichik yoy o'zgarishsiz qoldi ($70^\\circ$). "
                   "Yo'laklar orasidagi yangi $\\angle P$ burchak endi necha "
                   "gradusga teng bo'ladi va u oldingisidan qanchaga "
                   "o'zgardi?"),
        "ans": "55",
        "fb": "To'g'ri! Yangi katta yoy = $150^\\circ \\times 1.2 = 180^\\circ$. Yangi burchak = $(180^\\circ - 70^\\circ)/2 = 55^\\circ$. O'zgarish = $+15^\\circ$.",
        "capture": True,
        "tags": "[Bloom: L5 | PISA: L4]",
    },
    "q4": {
        "prompt": ("**4. Chamalab tekshirish.** Loyiha hujjatlarining "
                   "dastlabki qoralamasida yoylar aniq butun sonlarda emas, "
                   "balki qisman aniqlikda berilgan: katta yoy "
                   "$\\approx 148.5^\\circ$ va kichik yoy $\\approx 68.2^\\circ$. "
                   "Asl 1-savol javobiga ishonch hosil qilish uchun ushbu "
                   "qiymatlarni eng yaqin o'nliklarga yaxlitlang va "
                   "burchakni chamalab hisoblang. Natija 1-savol javobiga "
                   "mos keladimi?"),
        "ans": "40",
        "fb": "To'g'ri! Yaxlitlash: $148.5 \\approx 150$, $68.2 \\approx 70$. Chamasi: $(150 - 70)/2 = 40^\\circ$ — 1-savol javobi bilan mos.",
        "capture": True,
        "tags": "[Bloom: L4 | PISA: L3]",
    },
    "q5": {
        # Source MD Q5 is interpretation-only; mark `open` so the injector
        # uses make_open_q (textarea + AI grading) instead of single-line.
        "prompt": ("**5. Tahlil va qaror (Interpretation).** Aylana "
                   "kesuvchilari xossasiga ko'ra, agar binoning o'lchamlari "
                   "o'zgarmasa-yu (yoylar doimiy bo'lsa), lekin hisoblangan "
                   "burchak kichrayib borsa, muhandis sifatida binoga "
                   "nisbatan joylashuvingiz haqida qanday xulosa qilasiz? "
                   "Bu natija $P$ nuqtaning binodan uzoqlashayotganini "
                   "bildiradimi yoki yaqinlashayotganini? Javobingizni "
                   "asoslang."),
        "ans": "uzoqlashayotganini",
        "fb": "Doimiy yoylar bilan burchak kichraysa — kuzatuvchi binodan uzoqlashayotgan. Uzoqdagi obyektga ko'rish burchagi qisqaradi.",
        "capture": True,
        "open": True,
        "tags": "[Bloom: L6 | PISA: L5]",
    },
}

# ── Consolidation (Phase 5) — Memory Tree from MD §5-Bosqich ────────────

CONSOLIDATION = {
    "title": "Xotirani Mustahkamlash — Aylana va Burchak xaritasi",
    "mnemonic": (
        "Bugun aylanaga doir bir nechta turli burchaklarni o'rgandik: ikkita "
        "kesuvchi, urinma va kesuvchi, ikkita urinma, vatarlar orasidagi "
        "burchaklar. Hammasini bitta umumiy belgi bog'lab turadi: "
        "**burchak uchining qayerda joylashgani.** Markazda \"Burchak qanday "
        "topiladi?\" savoli, undan 3 ta shox tarqaladi:"
    ),
    "bullets": [
        ("**1-Shox: Burchak uchi aylana TASHQARISIDA.** Ikkita kesuvchi, "
         "ikkita urinma yoki urinma + kesuvchi orasidagi burchak. "
         "Qoida: uzoqdagi yoydan yaqindagi yoyni AYIRIB, ikkiga bo'lamiz. "
         "Xotira kaliti: \"Tashqaridagi sovuq — ayirib tashlaymiz (−)\"."),
        ("**2-Shox: Burchak uchi aylana ICHIDA.** Aylananing ichida "
         "kesishuvchi ikkita vatar orasidagi burchak. Qoida: burchak tiralgan "
         "ikkita qarama-qarshi yoyni QO'SHIB, ikkiga bo'lamiz. "
         "Xotira kaliti: \"Ichkaridagi issiqlik — birlashtiramiz, qo'shamiz (+)\"."),
        ("**3-Shox: Burchak uchi aylana USTIDA.** Ichki chizilgan burchak "
         "yoki urinma + vatar orasidagi burchak. Qoida: faqat o'zi tiralgan "
         "yoyning o'zini 2 ga bo'lamiz. "
         "Xotira kaliti: \"Ustida turganga bitta yoy yetarli\"."),
    ],
    "check_prompt": (
        "**O'z-o'zini tekshirish (1 daqiqa).** Quyidagi bo'shliqlarga qaysi "
        "arifmetik amal yoki so'z mos kelishini ichingizda toping:\n\n"
        "1. Agar burchak aylanadan uzoqda (tashqarida) yotsa, yoylar qiymati "
        "bir-biridan ____________.\n"
        "2. Agar burchak aylananing ichida yotsa, yoylar qiymati bir-biriga "
        "____________.\n"
        "3. 3-Shoxda — \"o'zi tiralgan yoy ____________ bo'linadi\". "
        "Qaysi raqam mos keladi?"
    ),
    "check_answer": (
        "1. **Ayiriladi** (tashqaridagi burchak — yoylar ayirmasining yarmi).\n"
        "2. **Qo'shiladi** (ichkaridagi burchak — yoylar yig'indisining yarmi).\n"
        "3. **2 ga** (ichki chizilgan burchak — yoyning yarmiga teng).\n\n"
        "Chuqur nafas oling. Barcha qoidalar bitta tizimga tushdi. "
        "Endi siz \"Yakuniy Boss\" ga tayyorsiz!"
    ),
    "recap": (
        "Ko'p turli burchak formulasi bitta umumiy mantiqqa bo'ysunadi: "
        "burchak uchi qayerda — ichkarida (+), tashqarida (−), yoki ustida "
        "(yarim). Shu tartib bilan har qanday aralash holatda to'g'ri "
        "formulani tanlay olasiz."
    ),
}

# ── Boss (5 attacks) ────────────────────────────────────────────────────

BOSS_Q1_SVG = '''<svg viewBox="0 0 250 150" xmlns="http://www.w3.org/2000/svg" style="font-family: sans-serif; font-size: 14px;">
  <circle cx="150" cy="75" r="60" fill="none" stroke="#9CA3AF" stroke-width="2"/>
  <polygon points="10,75 200,25 200,125" fill="none" stroke="#4B5563" stroke-width="2" stroke-linejoin="round"/>
  <text x="0" y="80" fill="#111827" font-weight="bold">P</text>
  <path d="M 200,41 A 60 60 0 0 1 200,109" fill="none" stroke="#2563EB" stroke-width="3"/>
  <text x="210" y="80" fill="#2563EB" font-weight="bold">120°</text>
  <path d="M 103,40 A 60 60 0 0 0 103,110" fill="none" stroke="#2563EB" stroke-width="3"/>
  <text x="65" y="80" fill="#2563EB" font-weight="bold">40°</text>
  <path d="M 35,68 A 20 20 0 0 0 35,82" fill="none" stroke="#EA580C" stroke-width="3"/>
  <text x="42" y="80" fill="#EA580C" font-weight="bold">?</text>
</svg>'''

BOSS_Q5_SVG = '''<svg viewBox="0 0 250 150" xmlns="http://www.w3.org/2000/svg" style="font-family: sans-serif; font-size: 14px;">
  <circle cx="160" cy="75" r="50" fill="none" stroke="#9CA3AF" stroke-width="2"/>
  <polygon points="10,75 220,30 220,120" fill="none" stroke="#4B5563" stroke-width="2" stroke-dasharray="4"/>
  <text x="0" y="80" fill="#111827" font-weight="bold">P</text>
  <path d="M 35,68 A 20 20 0 0 0 35,82" fill="none" stroke="#EA580C" stroke-width="2"/>
  <text x="40" y="79" fill="#EA580C" font-weight="bold">30°</text>
  <text x="225" y="80" fill="#2563EB" font-weight="bold">3x</text>
  <text x="90" y="80" fill="#2563EB" font-weight="bold">x</text>
</svg>'''

BOSS_QUESTIONS = [
    {
        # Boss adapter drops the standalone `svg` field; the runtime renders
        # only `q.prompt`. So the SVG is inlined into the prompt body.
        "q": ("**1-Hujum: To'g'ridan-to'g'ri hisoblash.** "
              "Quyidagi chizmada $P$ nuqtadan aylanaga ikkita kesuvchi "
              "o'tkazilgan. Ular aylanadan mos ravishda $120^\\circ$ va "
              "$40^\\circ$ li yoylarni kesib ajratadi. "
              "**Topshiriq:** Noma'lum $\\angle P$ burchakni toping. "
              "Yechim qadamlarini yozing."
              "<br><div class=\"svg-wrap\">" + BOSS_Q1_SVG + "</div>"),
        "tags": "[Bloom: L3 | PISA: L2 | Zarba: -10 HP]",
        "ans": ["40", "40°", "40 gradus"],
        "hint": "Tashqi burchak: $\\alpha = (120^\\circ - 40^\\circ) / 2$.",
        "dmg": 10,
        "svg": "",
        "answer_spec": {
            "type": "numeric",
            "expected": 40,
            "tolerance": 0.5,
            "canonical_display": "40°",
            "allow_ai_fallback": True,
        },
    },
    {
        "q": ("**2-Hujum: Teskari hisoblash.** "
              "Aylanaga tashqaridagi nuqtadan bitta urinma va bitta "
              "kesuvchi o'tkazildi. Ular orasidagi burchak $50^\\circ$ ga "
              "teng. Ular aylanadan ajratgan katta yoy $160^\\circ$ ni "
              "tashkil etadi. **Topshiriq:** Kichik yoyning gradus "
              "o'lchovini toping. Tenglamangizni ko'rsating."),
        "tags": "[Bloom: L3 | PISA: L2 | Zarba: -10 HP]",
        "ans": ["60", "60°", "60 gradus"],
        "hint": "Tenglama: $50^\\circ = (160^\\circ - x)/2$.",
        "dmg": 10,
        "svg": "",
        "answer_spec": {
            "type": "numeric",
            "expected": 60,
            "tolerance": 0.5,
            "canonical_display": "60°",
            "allow_ai_fallback": True,
        },
    },
    {
        "q": ("**3-Hujum: Mantiqiy bog'liqlik.** "
              "Aylanaga tashqaridagi $M$ nuqtadan ikkita urinma o'tkazildi. "
              "Bu urinmalar aylanani ikkita yoyga ajratadi (ular birlashib "
              "butun $360^\\circ$ ni tashkil qiladi). Urinmalar orasidagi "
              "burchak $\\angle M = 70^\\circ$. "
              "**Topshiriq:** Katta va kichik yoylarning har birini necha "
              "gradus ekanligini toping. *(Maslahat: yoylar yig'indisi "
              "haqidagi qoidani eslang.)*"),
        "tags": "[Bloom: L4 | PISA: L3 | Zarba: -20 HP]",
        "ans": ["katta yoy 215°, kichik yoy 145°", "215, 145", "215° va 145°"],
        "hint": "Sistema: $b - s = 140^\\circ$, $b + s = 360^\\circ$.",
        "dmg": 20,
        "svg": "",
        "answer_spec": {
            "type": "semantic",
            "expected": "Katta yoy 215°, kichik yoy 145°",
            "canonical_display": "Katta yoy = 215°, kichik yoy = 145°",
            "allow_ai_fallback": True,
        },
    },
    {
        "q": ("**4-Hujum: Haqiqiy hayotdagi muammo.** "
              "Siz telekommunikatsiya muhandisisiz. Toshkent teleminorasidan "
              "tarqalayotgan signal aylanasi (qamrov hududi) chetida "
              "yashovchi ikkita abonentga $P$ stansiyadan to'g'ri chiziqli "
              "kabellar tortildi. Stansiyadagi tarmoqlanish burchagi "
              "$45^\\circ$. Kabellar qamrov hududidan kesib o'tgan katta yoy "
              "$145^\\circ$ ekanligi ma'lum. "
              "**Topshiriq:** Kichik yoy necha gradus? Agar kichik yoy "
              "$40^\\circ$ dan kam bo'lsa, signal uzilishi yuz beradi. "
              "Signal sifatli yetib boradimi?"),
        "tags": "[Bloom: L4 | PISA: L4 | Zarba: -20 HP]",
        "ans": ["55, ha", "kichik yoy 55°, signal sifatli", "55° va ha"],
        "hint": "Tenglama: $45^\\circ = (145^\\circ - x)/2$ → $x = 55^\\circ > 40^\\circ$.",
        "dmg": 20,
        "svg": "",
        "answer_spec": {
            "type": "semantic",
            "expected": "Kichik yoy 55°. 55° > 40° bo'lgani uchun signal sifatli yetib boradi.",
            "canonical_display": "Kichik yoy = 55°. Signal sifatli (55 > 40).",
            "allow_ai_fallback": True,
        },
    },
    {
        "q": ("**5-Hujum: Loyihaviy tahlil va Talqin.** "
              "Siz aylanma shakldagi \"Milliy Bog'\" amfiteatriga yondosh "
              "yo'llar loyihasini baholayapsiz. Ikkita to'g'ri ko'cha $P$ "
              "nuqtada $30^\\circ$ burchak ostida kesishadi. Ular amfiteatr "
              "aylanasi bilan kesishganda hosil bo'lgan yoylarning nisbati "
              "$3:1$ ga teng (katta yoy kichigidan 3 marta katta).\n\n"
              "**Topshiriqlar:**\n"
              "1. Katta va kichik yoylarning aniq gradus o'lchovlarini toping.\n"
              "2. **Talqin:** Agar me'mor ko'chalar orasidagi burchakni "
              "kengaytirib $45^\\circ$ ga yetkazmoqchi bo'lsa, lekin "
              "yo'llarning amfiteatrga yaqinlashuv nuqtasi (kichik yoy $x$) "
              "o'zgarmay qolsa, yangi katta yoy qancha bo'lishi kerak?\n"
              "3. Bu geometrik o'zgarish hayotda nimani anglatadi? "
              "(Ko'chalar amfiteatrning ko'proq qismini qamrab oladimi yoki "
              "kamroqmi?)"
              "<br><div class=\"svg-wrap\">" + BOSS_Q5_SVG + "</div>"),
        "tags": "[Bloom: L6 | PISA: L5 | Zarba: -30 HP]",
        "ans": [
            "kichik yoy 30°, katta yoy 90°. yangi katta 120°. ko'proq qismini qamrab oladi",
            "30, 90, 120, ko'proq",
        ],
        "hint": "$30^\\circ = (3x - x)/2 = x \\Rightarrow x = 30^\\circ$, $3x = 90^\\circ$. Keyin $45^\\circ = (b' - 30^\\circ)/2 \\Rightarrow b' = 120^\\circ$.",
        "dmg": 30,
        "svg": "",
        "answer_spec": {
            "type": "semantic",
            "expected": ("(1) Kichik yoy = 30°, katta yoy = 90°. "
                         "(2) Yangi katta yoy = 120°. "
                         "(3) Ko'chalar amfiteatrning ko'proq qismini qamrab oladi "
                         "(katta yoy 90° → 120° ga oshdi)."),
            "canonical_display": "1) 30° va 90°. 2) 120°. 3) Ko'proq qismini qamrab oladi.",
            "allow_ai_fallback": True,
        },
    },
]

# ── Reflection (verbatim from MD) ───────────────────────────────────────

REFLECTION = {
    "summary": (
        "Bugun Siz aylananing kesuvchilari, urinmalari va vatarlari orasida "
        "hosil bo'ladigan burchaklarni o'rgandingiz. Asosiy usul sifatida "
        "aylananing tashqarisida yotgan burchakni topish uchun katta yoydan "
        "kichik yoyni ayirib, natijani ikkiga bo'lish formulasini amalda "
        "qo'lladingiz. Bu bilimlar shaharsozlikda, transport logistikasida "
        "va yirik arxitektura obidalarini loyihalashda muhandislar "
        "tomonidan aniq chizmalar yaratish uchun ishlatiladi."
    ),
    "question": (
        "*(Bu savol baholanmaydi, unga ichingizda yoki ovoz chiqarib erkin "
        "javob berishingiz mumkin)*:\n"
        "Siz bugun o'rgangan bu qoidalarni o'z do'stingizga qanday "
        "tushuntirgan bo'lar edingiz?"
    ),
    "spaced_rep": (
        "Miyangiz bu bilimlarni doimiy xotiraga saqlab qolishi uchun qisqa "
        "takrorlashlar zarur.\n"
        "Keyingi takrorlash: ertaga (1 kun), 3 kundan keyin, 7 kundan keyin.\n\n"
        "Takrorlash vaqtida aynan mana shu 3 ta jihatga e'tibor qarating:\n"
        "* Burchak aylana tashqarisida bo'lganda yoylarni ayirish, ichida "
        "bo'lganda qo'shish qoidasi.\n"
        "* Ikkita urinma orasidagi burchak masalalarida noma'lum yoylar "
        "yig'indisi $360^\\circ$ ekanligidan foydalanish.\n"
        "* Yoylar nisbati (masalan, $3x$ va $x$) berilganda chiziqli "
        "tenglama tuzish bosqichlari."
    ),
    "closing": (
        "Sizning aniqligingiz va qat'iyatingiz — Uchinchi Renessansning "
        "poydevori. Dars tugadi, dam olishingiz mumkin!"
    ),
}

# ── Build & PUT ─────────────────────────────────────────────────────────

def main():
    print(f"GET {API}/api/homeworks/{HW_ID}")
    current = http_get(f"/api/homeworks/{HW_ID}")
    cj = current["content_json"]

    # Fix panel titles + clean up bracketed authoring directives that the
    # original importer left in as paragraph blocks.
    print("Fixing panel titles + cleaning bracketed directives...")
    import re as _re
    for i, panel in enumerate(cj.get("panels", [])):
        if i < len(PANEL_TITLES):
            panel["title"] = f"PANEL {i + 1} — {PANEL_TITLES[i].upper()}"
        for page in panel.get("pages", []):
            blocks = page.get("blocks", [])
            cleaned = []
            for blk in blocks:
                # Migrate any leftover 'h' blocks from a previous rebuild to
                # the template-recognized 'h2' type.
                if blk.get("type") == "h":
                    cleaned.append({"type": "h2", "text": blk.get("text") or ""})
                    continue
                if blk.get("type") == "p":
                    txt = (blk.get("text") or "").strip()
                    # Drop bracketed image/state directives like
                    # [Chizma: ...]  [State 0 — Setup: ...]
                    if _re.match(r"^\s*\[[^\]]*\]\s*$", txt):
                        continue
                    # Convert bare "1-Misol:" / "2-Misol:" / "3-Bosqich:" labels
                    # into proper heading blocks for visual separation. The
                    # template only recognizes 'h2' from the heading family;
                    # other heading levels fall through to .block-unknown.
                    if _re.match(r"^\d+-(?:Misol|Bosqich|Hujum|Shox)\s*:", txt):
                        cleaned.append({"type": "h2", "text": txt})
                        continue
                cleaned.append(blk)
            page["blocks"] = cleaned

    # Replace flashcards (clean, ordered)
    cj["flashcards"] = [
        {"term": t, "def": d, "cluster": "geometry"} for t, d in FLASHCARDS
    ]

    # Replace memory_sprint with clean prompts
    cj["memory_sprint"] = MEMORY_SPRINT

    # Replace gb_adaptive_quiz with 5 properly tier-distributed items
    cj["gb_adaptive_quiz"] = GB_ADAPTIVE_QUIZ

    # Replace gb_memory_match with the 6 tile-match pairs
    cj["gb_memory_match"] = GB_MEMORY_MATCH

    # Replace gb_why_chain (now Sentence Fill in the runtime label) with the
    # 5 sentence-fill items + per-item reprompts.
    cj["gb_why_chain"] = GB_WHY_CHAIN

    # Real-Life: clean story + 5 sub-questions (q5 had wrong content prior).
    cj["real_life"] = REAL_LIFE

    # Boss: clean prompts + answer_spec on every item so the AI grader has a
    # concrete target to compare student work against.
    cj["boss_questions"] = BOSS_QUESTIONS

    # Reflection
    cj["reflection"] = REFLECTION

    # Phase 5 Consolidation — Memory Tree (was missing entirely from prior import).
    cj["consolidation"] = CONSOLIDATION

    # Grading config — keep AMR + Kimi + 80% confidence threshold + deploy port.
    cj.setdefault("grading", {})
    cj["grading"].update({
        "system": "amr",
        "provider": "kimi",
        "confidence_threshold": 80,
        "deploy_port": 5071,
    })

    # PUT updated content_json. The HomeworkUpdate model accepts {title?, content_json?}.
    print(f"PUT {API}/api/homeworks/{HW_ID}")
    updated = http_put(f"/api/homeworks/{HW_ID}", {
        "title": current["title"],
        "content_json": cj,
    })

    # Verify the round-trip.
    print()
    print("✓ updated record id      :", updated.get("id"))
    print("✓ panels                  :", len(cj["panels"]))
    print("✓ flashcards              :", len(cj["flashcards"]))
    print("✓ memory_sprint           :", len(cj["memory_sprint"]))
    print("✓ gb_adaptive_quiz        :", len(cj["gb_adaptive_quiz"]),
          "tiers=" + ",".join(q["tier"] for q in cj["gb_adaptive_quiz"]))
    print("✓ gb_memory_match (tile)  :", len(cj["gb_memory_match"]))
    print("✓ gb_why_chain (sent fill):", len(cj["gb_why_chain"]))
    print("✓ real_life q1..q5        : present")
    print("✓ boss_questions          :", len(cj["boss_questions"]),
          "dmg=" + ",".join(str(q["dmg"]) for q in cj["boss_questions"]))
    print("✓ reflection              :", "present")
    print("✓ grading                 :", cj["grading"])


if __name__ == "__main__":
    main()
