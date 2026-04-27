# NETS Builder — Shared Contracts (FROZEN)

All three agents (Opus 4.7 backend, GPT-5.5 frontend, Gemini 3.1 content) build against this file. Do not deviate. If something is missing, ask before changing.

Version: 1.0 · Last updated: 2026-04-24

---

## 1. Data Model — `content_json`

The single source of truth for a homework's content. Stored as JSON in SQLite `homeworks.content_json` column. Matches the 9 JS constants in `perfect_homework.html`.

```json
{
  "meta": {
    "title": "Kvadrat tenglama",
    "subject_display": "Algebra",
    "section": "22-§",
    "cefr_level": "B1"
  },
  "quotes": ["string", "..."],
  "panels": [
    {
      "id": 1,
      "title": "PANEL 1 — SUMMARY",
      "pages": [
        {
          "blocks": [
            { "type": "p",     "text": "string" },
            { "type": "h2",    "text": "string" },
            { "type": "quote", "text": "string" },
            { "type": "ol",    "items": ["string", "..."] },
            { "type": "ul",    "items": ["string", "..."] }
          ]
        }
      ]
    }
  ],
  "flashcards": [
    { "term": "string", "def": "string", "cluster": "QOIDA|MISOL|TAHLIL|METOD" }
  ],
  "memory_sprint": [
    {
      "type": "KO",
      "prompt": "string",
      "subtitle": "",
      "tags": "[Bloom: L1 | PISA: L1]",
      "explain": "string",
      "options": ["a", "b", "c", "d"],
      "correct": 0
    },
    {
      "type": "TF",
      "prompt": "string",
      "subtitle": "",
      "tags": "[Bloom: L1 | PISA: L1]",
      "explain": "string",
      "options": ["To'g'ri", "Noto'g'ri"],
      "correct": 0
    },
    {
      "type": "YNNG",
      "prompt": "string",
      "subtitle": "",
      "tags": "[Bloom: L1 | PISA: L1]",
      "explain": "string",
      "options": ["Ha", "Yo'q", "Ma'lum emas"],
      "correct": 0
    }
  ],
  "gb_adaptive_quiz": [
    {
      "q": "string",
      "tags": "[Bloom: L1 | PISA: L1]",
      "tier": "EASY|MEDIUM|HARD",
      "ans": ["accepted_answer_1", "accepted_answer_2"],
      "capture": false
    }
  ],
  "gb_why_chain": [
    {
      "q": "string",
      "inv": "correct_answer_string",
      "reprompts": ["hint_1", "hint_2"]
    }
  ],
  "gb_memory_match": [
    ["left", "right"]
  ],
  "real_life": {
    "badge": "VAZIFA · Scenario name",
    "story": "multi-line story text",
    "q1": { "prompt": "string", "ans": "string", "fb": "feedback" },
    "q2": { "prompt": "string", "fields": [{"id": "m", "label": "Label", "ans": "string"}], "fb": "feedback" },
    "q3": { "prompt": "string", "ans": "string", "fb": "feedback" },
    "q4": { "prompt": "string", "fields": [{"id": "c", "label": "Label", "ans": "string"}], "fb": "feedback" },
    "q5": { "prompt": "string", "open": true, "fb": "feedback" },
    "q6": { "prompt": "string", "ans": "string", "fb": "feedback" },
    "endTitle": "string",
    "endSub": "string"
  },
  "boss_questions": [
    {
      "q": "string",
      "tags": "[Bloom: L2 | PISA: L2 | Damage: -10 HP]",
      "ans": ["accepted_1", "accepted_2"],
      "hint": "string",
      "dmg": 10
    }
  ],
  "reflection": {
    "summary": "string",
    "question": "string",
    "spaced_rep": "string",
    "closing": "string"
  }
}
```

### Answer specification (added in Wave D — D1 schema, D2 checker, D3 router)

Every question shape (`memory_sprint[]`, `gb_adaptive_quiz[]`, `boss_questions[]`, `real_life.q1..q6`) MAY include an `answer_spec` object alongside the legacy `ans`/`accepted_answers[]` fields. When present, the deterministic grader (D2) uses `answer_spec` first; the legacy field is preserved for backward compatibility through one release cycle.

```json
{
  "answer_spec": {
    "type": "numeric | set_match | text_exact | text_fuzzy | semantic",
    "expected": "<type-dependent>",
    "tolerance": 0,
    "canonical_display": "string",
    "allow_ai_fallback": true,
    "rubric": { "correct": "...", "partial": "...", "incorrect": "..." }
  }
}
```

Full type spec, edge cases, examples per type: see `docs/ANSWER_SPEC.md`. Migration script: `scripts/migrate_answer_spec.py` (idempotent, requires `--db-path` + recommended `--backup-first`).

**Rules:**
- All strings Uzbek (`Siz` formal), unless subject is English (then English content)
- Empty arrays `[]` for phases not in the pipeline (never omit keys — use `[]` or `null`)
- `correct` is 0-based index into `options`
- `tags` format is exact: `[Bloom: LX | PISA: LX]` — boss adds ` | Damage: -XX HP`
- `dmg` values: 10 (easy), 20 (medium), 30 (hard). G1-4 override: 5/10/15
- `tier` values: EASY, MEDIUM, HARD (uppercase)

---

## 2. Homework Record (DB + API)

```json
{
  "id": "HW-20260424-001",
  "title": "Kvadrat tenglama",
  "subject": "math-algebra",
  "grade": 8,
  "mode": "hard",
  "family": "aniq-fanlar",
  "language": "uz",
  "status": "draft|generating|ready|error",
  "content_json": { /* see section 1 */ },
  "created_at": "2026-04-24T10:00:00Z",
  "updated_at": "2026-04-24T10:00:00Z"
}
```

**ID format:** `HW-{YYYYMMDD}-{3-digit-seq}`. Generated by backend on POST.

---

## 3. Enums (Single Source of Truth)

```python
# Subjects (must match 06-prompts/ folder names exactly)
SUBJECTS = [
    "math-algebra",
    "geometriya-g7-11",
    "physics",
    "biology",
    "kimyo-g7-11",
    "english",
    "history",
]

# Subject → family mapping
SUBJECT_TO_FAMILY = {
    "math-algebra":     "aniq-fanlar",
    "geometriya-g7-11": "aniq-fanlar",
    "physics":          "tabiy-fanlar",
    "biology":          "tabiy-fanlar",
    "kimyo-g7-11":      "tabiy-fanlar",
    "english":          "til-fanlar",
    "history":          "ijtimoiy-fanlar",
}

# Subjects locked to Hard mode
ALWAYS_HARD = {"english", "history"}

# Grade range per subject
SUBJECT_GRADES = {
    "math-algebra":     [5, 6, 7, 8, 9, 10, 11],
    "geometriya-g7-11": [7, 8, 9, 10, 11],
    "physics":          [6, 7, 8, 9, 10, 11],
    "biology":          [5, 6, 7, 8, 9, 10, 11],
    "kimyo-g7-11":      [7, 8, 9, 10, 11],
    "english":          [5, 6, 7, 8, 9, 10, 11],
    "history":          [5, 6, 7, 8, 9, 10, 11],
}

# Phase routing: (family, mode) → ordered phase list
PHASE_PIPELINE = {
    ("aniq-fanlar",    "easy"): ["preview", "flashcards", "memory_sprint", "game_breaks", "reflection"],
    ("aniq-fanlar",    "hard"): ["preview", "flashcards", "memory_sprint", "game_breaks", "real_life", "consolidation", "final_challenge", "reflection"],
    ("tabiy-fanlar",   "easy"): ["preview", "flashcards", "memory_sprint", "game_breaks", "reflection"],
    ("tabiy-fanlar",   "hard"): ["preview", "flashcards", "memory_sprint", "game_breaks", "real_life", "consolidation", "final_challenge", "reflection"],
    ("til-fanlar",     "hard"): ["preview", "flashcards", "memory_sprint", "reading", "game_breaks", "real_life", "consolidation", "final_challenge", "reflection"],
    ("ijtimoiy-fanlar","hard"): ["preview", "flashcards", "memory_sprint", "game_breaks", "consolidation", "final_challenge", "reflection"],
}

# HP by grade band
BOSS_HP = {
    (1, 4):  50,
    (5, 8):  100,
    (9, 11): 150,
}

# Math G5-6 override: 80 HP

# Phase display names (Uzbek)
PHASE_NAMES = {
    "preview":         "Ko'rib chiqish",
    "flashcards":      "Flesh-kartalar",
    "memory_sprint":   "Xotira Sprint",
    "reading":         "O'qish",
    "game_breaks":     "O'yin tanaffus",
    "real_life":       "Hayotiy vazifa",
    "consolidation":   "Mustahkamlash",
    "final_challenge": "Yakuniy jang",
    "reflection":      "Xulosa",
}

PHASE_ICONS = {
    "preview": "📋", "flashcards": "🃏", "memory_sprint": "⚡",
    "reading": "📖", "game_breaks": "🎮", "real_life": "🌍",
    "consolidation": "🧠", "final_challenge": "👾", "reflection": "💭",
}

# Family colors (frontend)
FAMILY_COLORS = {
    "aniq-fanlar":     "#007AFF",
    "tabiy-fanlar":    "#34C759",
    "til-fanlar":      "#AF52DE",
    "ijtimoiy-fanlar": "#FF9500",
}

# Status colors (frontend)
STATUS_COLORS = {
    "draft":      "#86868b",
    "generating": "#FF9500",
    "ready":      "#34C759",
    "error":      "#FF3B30",
}
```

---

## 4. API Endpoints

Base URL: `http://localhost:8000`

All responses JSON unless noted. All errors return `{ "error": "message", "code": "ERROR_CODE" }` with 4xx/5xx status.

### Meta

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/api/subjects` | — | `{ subjects: [{id, family, always_hard, grades}], families: {id: color} }` |
| GET | `/api/health` | — | `{ status: "ok", gemini: true\|false }` |

### Homeworks

| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| GET | `/api/homeworks` | — | `[ {homework record without content_json} ]` |
| POST | `/api/homeworks` | `{ title, subject, grade, mode }` | `{ id, ...full record with empty content_json scaffold }` |
| GET | `/api/homeworks/{id}` | — | Full homework record |
| PUT | `/api/homeworks/{id}` | `{ title?, content_json? }` | Updated full record |
| DELETE | `/api/homeworks/{id}` | — | `{ ok: true }` |

**POST body validation:** `subject` must be in `SUBJECTS`, `grade` must be in `SUBJECT_GRADES[subject]`, `mode` must be `"easy"` or `"hard"` (ignored and forced to `"hard"` if subject in `ALWAYS_HARD`). Backend computes `family` from subject.

**Empty scaffold (POST response content_json):**
```json
{
  "meta": { "title": "...", "subject_display": "...", "section": "", "cefr_level": "" },
  "quotes": [], "panels": [], "flashcards": [], "memory_sprint": [],
  "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [],
  "real_life": null, "boss_questions": [], "reflection": null
}
```

### AI Generation

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/api/homeworks/{id}/generate` | `{ textbook_text, chapter, section }` | SSE stream |

**SSE event format** (backend → frontend):
```
event: classify
data: {"mode": "hard", "level": "B1", "reason": "..."}

event: phase
data: {"phase": "preview", "status": "start|done", "data": { /* phase slice */ }}

event: error
data: {"phase": "flashcards", "message": "..."}

event: done
data: {"id": "HW-...", "status": "ready"}
```

Frontend uses `EventSource` to consume. Each `phase` event with `status: "done"` triggers editor auto-populate.

### Preview + Permanent Share URL

| Method | Path | Response | Content-Type |
|--------|------|----------|--------------|
| GET | `/api/homeworks/{id}/preview` | Injected HTML body (builder live-preview) | `text/html` |
| GET | `/h/{id}` | Injected HTML body (canonical permanent URL with AI runtime) | `text/html` |

**Note:** the legacy `/api/homeworks/{id}/export` endpoint was removed in Wave B1+B2 (commit `0457360`). The platform now serves homeworks via the live `/h/{id}` URL — there is no offline standalone HTML output.

### Sessions (student playback — Wave 4)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/api/sessions` | `{ homework_id, student_name }` | `{ id, started_at }` |
| POST | `/api/sessions/{id}/response` | `{ phase, question_id, answer, time_ms }` | `{ correct: bool, feedback }` |
| GET | `/api/sessions/{id}` | — | Full session with responses |

---

## 5. Injector Contract (Backend)

`server/services/injector.py` must replace these exact constant declarations in `perfect_homework.html`:

| JS Constant | `content_json` key | Type |
|-------------|-------------------|------|
| `PANELS` | `panels` | array |
| `QUOTES` | `quotes` | array |
| `FLASHCARDS` | `flashcards` | array |
| `MS_QUESTIONS` | `memory_sprint` | array |
| `GB_ADAPTIVE_QUIZ` | `gb_adaptive_quiz` | array |
| `GB_WHY_CHAIN` | `gb_why_chain` | array |
| `GB_MEMORY_MATCH` | `gb_memory_match` | array |
| `RL_SCENARIO` | `real_life` | object |
| `BOSS_QUESTIONS` | `boss_questions` | array |

**Regex patterns (use these exactly):**
```python
ARRAY_PATTERN  = r'const {name}\s*=\s*\[.*?\];'        # for arrays
OBJECT_PATTERN = r'const {name}\s*=\s*\{.*?\};\s*// BOSS'  # for RL_SCENARIO (fallback: next const/function)
```

Title/caption regex:
```python
TITLE_PATTERN   = r'<h1>.*?</h1>'
CAPTION_PATTERN = r'<div class="caption">.*?</div>'
```

Injection produces replacement: `const {NAME} = {json.dumps(data, ensure_ascii=False)};`

---

## 6. Gemini Call Contract

`server/services/gemini.py`:

```python
async def generate(prompt: str, context: str = "", json_schema: dict = None) -> str | dict:
    """
    Send prompt + context to Gemini. If json_schema provided, return parsed dict.
    Otherwise return raw text.
    
    Uses model: gemini-2.5-flash for fast tasks, gemini-2.5-pro for complex phases.
    API key from env: GEMINI_API_KEY.
    """
```

**Prompt chain input construction** (done by `pipeline.py`):
```
[PROMPT FILE CONTENT FROM 06-prompts/{subject}/{phase}.md]

---

TEXTBOOK CONTENT:
{textbook_text}

---

PRIOR CONTEXT:
{json.dumps(prior_phases, indent=2)}

---

OUTPUT REQUIREMENT:
Return valid JSON matching this exact schema:
{json_schema}
```

---

## 7. Frontend Contract

**State management:** Plain global object `window.BUILDER_STATE = { homework: {...}, activePhase: "preview", dirty: false }`. No framework.

**Editor module contract:** Each `frontend/js/editors/{phase}.js` exports one global function:
```javascript
window.Editors = window.Editors || {};
window.Editors.preview = {
    render(container, data, onChange) { /* render editor into container, call onChange(newData) on edits */ },
};
```

**Auto-save:** `builder.js` debounces (500ms) `API.updateHomework(id, { content_json })` on any `onChange` call.

**Preview refresh:** After successful auto-save, if preview panel is open, reload iframe: `frame.src = API.getPreviewUrl(id) + '?t=' + Date.now()`.

---

## 8. Directory Layout (CANONICAL)

```
nets-builder/
├── server/
│   ├── app.py
│   ├── db.py
│   ├── config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── meta.py         # /api/subjects, /api/health
│   │   ├── homework.py     # CRUD
│   │   ├── ai.py           # /generate SSE
│   │   ├── homework_page.py # /h/{id} permanent URL + /api/homeworks/{id}/preview
│   │   └── library.py      # /api/library, /api/library/facets
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini.py
│   │   ├── pipeline.py
│   │   ├── parser.py       # AI output → content_json slice
│   │   ├── injector.py
│   │   └── routing.py      # enums above, in code form
│   ├── template/
│   │   └── perfect_homework.html
│   └── prompts/            # copied from ../standards/framework/06-prompts/
├── frontend/
│   ├── index.html
│   ├── builder.html
│   ├── css/
│   │   └── app.css
│   └── js/
│       ├── api.js
│       ├── dashboard.js
│       ├── builder.js
│       └── editors/
│           ├── preview.js
│           ├── flashcards.js
│           ├── memory-sprint.js
│           ├── game-breaks.js
│           ├── reading.js
│           ├── real-life.js
│           ├── consolidation.js
│           ├── boss.js
│           └── reflection.js
├── fixtures/               # Gemini-produced sample content_json for each subject
├── .env                    # GEMINI_API_KEY=...
├── requirements.txt
├── README.md
└── CONTRACTS.md            # this file
```

---

## 9. Agent Responsibilities

| Agent | Owns | Must NOT touch |
|-------|------|----------------|
| **Opus 4.7** (backend) | `server/**`, `requirements.txt`, `.env.example`, `README.md` | `frontend/**` |
| **GPT-5.5** (frontend) | `frontend/**` | `server/**`, prompts |
| **Gemini 3.1** (content) | `fixtures/**`, `server/services/parser.py`, `server/prompts/**` (JSON schema appends only) | UI code, routes |

**Shared read-only:** `CONTRACTS.md` (this file), `perfect_homework.html` (the template).

---

## 10. Integration Verification (end of each wave)

**Wave 1 verify:**
```bash
curl http://localhost:8000/api/subjects                    # returns subject list
curl -X POST http://localhost:8000/api/homeworks -d '...'  # creates record
# Open http://localhost:8000 → dashboard shows created homework
# Click card → builder opens with correct phase sidebar
```

**Wave 2 verify:**
```bash
# Edit flashcards in builder UI → PUT fires → preview iframe re-renders
curl http://localhost:8000/api/homeworks/{id}/preview > out.html
# Open out.html → all edited content appears in rendered homework
```

**Wave 3 verify:**
```bash
# Click AI Generate → SSE events stream → phases auto-populate
# Check content_json has all 9 keys populated
```

**Wave 4 verify:**
```bash
# Permanent share URL (canonical) — opens with AI runtime active
curl http://localhost:8000/h/{id} -o hw.html
# Open in browser → full homework plays correctly, all phases work, AI hints respond.
```
