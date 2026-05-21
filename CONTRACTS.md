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
  "gate_quote": {
    "mode": "auto",
    "pinned_id": null,
    "pinned_preview": null,
    "custom": null
  },
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
            { "type": "ul",    "items": ["string", "..."] },
            { "type": "svg",   "html": "string (raw <svg>...</svg> markup)" },
            { "type": "image", "src":  "string (URL or images/img-N.png)", "alt": "string" }
          ]
        }
      ]
    }
  ],
  "flashcards": [
    { "term": "string", "def": "string", "cluster": "QOIDA|MISOL|TAHLIL|METOD", "hint": "optional", "media": { "type": "svg|image", "html": "svg only", "src": "image only", "alt": "image only" } }
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
  "gb_puzzle_lock": [
    { "content": "tile fragment HTML", "q": "question to gate this tile", "a": "accepted answer" }
  ],
  "gb_mystery_box": [
    { "category": "Algebra", "q": "Solve 3x+5=14", "a": "3" }
  ],
  "gb_ttt": [
    { "id": "ttt-1", "q": "What is 7 x 8?", "correct": "56", "distractors": ["54", "48", "63"] }
  ],
  "gb_ttt_config": {
    "session_games": 3, "xp_correct": 50, "xp_draw": 200, "xp_win": 300,
    "xp_strong_session": 100, "xp_mercy": 10, "mercy_chance": 0.002
  },
  "gb_memory_palace": {
    "palaces": [
      {
        "key": "school-corridor",
        "label": "Maktab yo'lagi",
        "locations": [
          { "idx": 0, "label": "Eshik" },
          { "idx": 1, "label": "Devor" },
          { "idx": 2, "label": "Stol" },
          { "idx": 3, "label": "Deraza" },
          { "idx": 4, "label": "Shkaf" }
        ]
      }
    ],
    "concepts": [
      { "id": "concept-1", "term": "Kvadrat tenglamasining discriminanti", "short": "D = b²−4ac" },
      { "id": "concept-2", "term": "Ildizlar formulasi", "short": "x = (−b ± √D) / 2a" }
    ],
    "config": {}
  },
  "gb_memory_palace_config": {
    "concepts_low": 3, "concepts_default": 5, "concepts_high": 7
  },
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
  "gate_quote": { "mode": "auto" }, "panels": [], "flashcards": [], "memory_sprint": [],
  "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [], "gb_puzzle_lock": [], "gb_mystery_box": [], "gb_ttt": [],
  "real_life": null, "boss_questions": [], "reflection": null
}
```

**Phase 3 games are all optional.** All `gb_*` keys above are independently optional — the injector keeps empty arrays as `[]` and the runtime registry (`gbActiveGameOrder()` in `perfect_homework.html`) skips empty slots. If every game is empty, Stage 5 is skipped entirely and the student goes straight from Reading/Memory Sprint to Real-Life Challenge. **Never re-add placeholder fallbacks for game-break keys** — see `tests/test_optional_games.py` for the regression contract. This rule applies to every new Phase 3 game added in the future.

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
| `QUOTES` | `gate_quote` (legacy `quotes`) | array (length 1, server-selected) |
| `FLASHCARDS` | `flashcards` | array |
| `MS_QUESTIONS` | `memory_sprint` | array |
| `GB_ADAPTIVE_QUIZ` | `gb_adaptive_quiz` | array |
| `GB_WHY_CHAIN` | `gb_why_chain` | array |
| `GB_MEMORY_MATCH` | `gb_memory_match` | array |
| `GB_PUZZLE_LOCK` | `gb_puzzle_lock` | array |
| `GB_MYSTERY_BOX` | `gb_mystery_box` | array (adapter stamps shared `labels` per item) |
| `GB_TTT` | `gb_ttt` | array of side-disjoint MC items: `{id, q, options[]}` — `correct` + `distractors` stripped server-side; client never sees them. Server keeps key map in `_TTT_ANSWER_KEY[hw_id]` for `/api/ai/check-answer?phase=ttt` validation. |
| `GB_MEMORY_PALACE` | `gb_memory_palace` | object: `{palaces: [], concepts: [], config: {}}` — full author content shipped to client (NOT side-disjoint; see plan §1.3 — student creates answer themselves via Step 2 placements, server-recomputes `is_correct` from submitted placement map for tampering defense). Server slices `concepts[]` per grade band (low=3 / default=5 / high=7) and filters premium-tier palaces for basic-tier homeworks. |
| `RL_SCENARIO` | `real_life` | object |
| `BOSS_QUESTIONS` | `boss_questions` | array |

#### Optional config keys

These keys are not injected as runtime JS constants. They are read server-side at request time to override default behaviour for their respective mechanic.

| `content_json` key | Consumed by | Shape / defaults |
|---|---|---|
| `gb_ttt_config` | `POST /api/ai/check-answer` (`phase=ttt` + `phase=ttt-session`) | `{ session_games: 3, xp_correct: 50, xp_draw: 200, xp_win: 300, xp_strong_session: 100, xp_mercy: 10, mercy_chance: 0.002 }` — any subset may be provided; missing keys fall back to defaults. Explicit `0` values are valid overrides; `null` values are ignored. |
| `boss_meta` | `POST /api/ai/check-answer` (`phase=final-boss`) | `{ boss_type, grade_band, attempts_max, anti_cheat, starting_hp_override }` — injected into runtime as `BOSS_META` (or `null` if absent). Existing rows without this key render unchanged. |
| `gb_memory_palace_config` | `POST /api/ai/check-answer` (`phase=memory-palace`) + injector | `{ concepts_low: 3, concepts_default: 5, concepts_high: 7 }` — controls how many concepts are sliced per grade band at inject time. Any subset may be provided; missing keys fall back to defaults. |

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

### 5.1 Gate Quote selector (Phase 0-A)

The `QUOTES` constant is special: it is always a length-1 array, populated by the
server-side selector at inject time, not stored in `content_json`.

**Library:** `server/data/quotes_database.json` — 600 entries copied from the NETS
framework repo (`Homework_Engine_Platform/standards/system/narrative/quotes_database.json`,
Cheeks branch). Each entry: `{id, type, author, text, category, origin}`.

**Author input:** `content_json.gate_quote = {mode, pinned_id?, pinned_preview?, custom?}`

| `mode` | Behaviour at inject time |
|--------|--------------------------|
| `"auto"` (default) | Selector picks one entry applying **55% National / 45% Global** origin and **70% fact / 30% quote** type, uniform within bucket. Fresh pick on every render. |
| `"pinned"` | Selector looks up `pinned_id` in the library and returns it. Unknown id → falls back to auto. `pinned_preview` is a builder-side cache for displaying the pinned card without a round-trip — the selector ignores it. |
| `"custom"` | Selector returns `custom = {text, author}` verbatim. |

**Legacy migration:** `content_json.quotes` (array of strings or `{t,a}` objects) is
auto-migrated by `server.services.quotes.migrate_legacy()` — first non-empty entry
becomes a `custom` quote. Empty/missing → `{mode: "auto"}`. Saves go through
`gate_quote` going forward; the old `quotes` key is still read as a fallback.

**Runtime contract:** the array element is `{t, a, origin, type, id?, category?}`.
The template uses `t`/`a` for text + author and `origin`/`type` for the visual chip
and icon. Skip lock is fixed at 5s in `runQuoteSequence`.

**API:** `GET /api/quotes?q=&type=&origin=&category=&author=&limit=&offset=` returns
`{items, total, limit, offset, facets: {types, origins, categories, authors}}`.
Used by the builder's quote picker modal (`frontend/js/editors/_quote-picker.js`).

---

## 6. Gemini Call Contract

`server/services/gemini.py`:

```python
async def generate(prompt: str, context: str = "", json_schema: dict = None) -> str | dict:
    """
    Send prompt + context to Kimi. If json_schema provided, return parsed dict.
    Otherwise return raw text.

    Uses model: moonshot-v1-32k for fast tasks, moonshot-v1-128k for complex phases.
    API key from env: KIMI_API_KEY.
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
├── fixtures/               # Sample content_json for each subject
├── .env                    # KIMI_API_KEY=...
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

---

## 11. Tutor conversation tables (Wave F1)

The live AI tutor widget persists chat turns and reads (read-only) from a shared
attempts log produced by the grading lane.

### `tutor_conversations` (owned by tutor lane — we read AND write)

```sql
CREATE TABLE IF NOT EXISTS tutor_conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,    -- client-generated UUID, in localStorage
    hw_id       TEXT NOT NULL,    -- homeworks.id
    phase       TEXT NOT NULL,    -- preview|practice|boss
    question_id TEXT NULL,        -- null in preview, set in practice/boss when scoped
    role        TEXT NOT NULL,    -- user|assistant|system
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tutor_session
    ON tutor_conversations(session_id, hw_id, created_at);
```

- Append-only — rows are never updated after insertion.
- Per-(session_id, hw_id) message cap of **60 turns** is enforced in
  `server/services/tutor.py::tutor_chat`. The 61st request returns 429.
- Migration: `python scripts/migrate_tutor_conversations.py [--db-path X] [--dry-run]`.
  Idempotent. Also auto-applied via `init_db()` for fresh installs.

**Note:** The `tutor_attempts` producer (grading lane) was cancelled per Wave F4 cleanup.
Our read-side `list_recent_attempts` helper is removed. See PR #34 for lane decision.

**Answer-leak prevention (Bridge B).** When `phase != "preview"`, the tutor
strips `expected`, `ans`, `accepted_answers`, and `correct` from any question
payload at top level AND inside `answer_spec` before the prompt enters the LLM.
See `server/services/tutor.py::_redact_question_for_tutor`.

---

## v2 flow (`flow_version: "v2"`)

**ADDITIVE — the frozen contract is unchanged.** Every field below is a NEW
optional key on `content_json`; no existing key is renamed or retyped. Legacy
rows omit these and render through the unchanged HTML injector. A row is served
by the React SPA runtime (`frontend/app/`) only when `content_json.flow_version
== "v2"`; the fork lives in `server/routes/homework_page.py`. Pydantic models
are in `server/schemas/content.py` (all `extra="allow"`).

### Hand-authored by the React v2 builder (DaddysBranch, 2026-05-21)

All v2 fields documented in this section are now **hand-authored by the React v2
builder** (`frontend/app/src/builder/`). Previously, v2 content could only be
seeded by the AI generation pipeline or test fixtures. This makes the
**frozen-schema rule even more critical**: the builder writes these keys directly
to `content_json` on every `PUT /api/homeworks/{id}` save; renaming or
restructuring a key silently breaks every existing v2 row in the DB (not just
runtime rendering, but the builder's own load → edit → save cycle). New optional
fields must use `extra="allow"` Pydantic models and never replace an existing
key. The `GET /api/homeworks` list also now surfaces `flow_version` per row so
the dashboard can route authoring without fetching the full record.

### New top-level fields

| Key | Type | Purpose |
|---|---|---|
| `flow_version` | string | Runtime dispatcher: absent/`"v1"` → legacy HTML injector; `"v2"` → React SPA. |
| `case_based_preview` | object (`CaseBasedPreview`) | Learning Hub Tile A — guided 3-checkpoint real-life case. One of the two ungated unlock paths. |
| `memory_check` | object (`MemoryCheck`) | Learning Hub Tile B gate — Quizlet-style test after flashcards. The second unlock path. |

`practice_arc` is also read by the runtime (`practice_arc.games[]` — an optional
ordered list of game-key strings); when absent the arc derives its order from
whichever `gb_*` arrays exist, with Boss always last. The 8 built game keys map
to `gb_tile_match`, `gb_sentence_fill`, `real_life_challenge`, `gb_ttt`,
`gb_memory_palace`, `gb_mystery_box`, `gb_puzzle_lock`, `gb_adaptive_quiz`; a 9th
key `gb_story_mode` → `story_mode` is reserved but unbuilt (renders a "coming
soon" skip card).

### `case_based_preview` (CaseBasedPreview)

```json
{
  "title": "string",
  "metadata": {},
  "source_extraction": {},
  "visual_plan": [],
  "case_setup": { "story": "...", "role": "...", "task": "..." },
  "checkpoints": [
    {
      "kind": "identify | decide | justify",
      "question": "string",
      "options": ["..."],
      "answer_spec": { /* AnswerSpec — STRIPPED before hydration */ },
      "learning_block": "post-submit teaching text — STRIPPED from hydration; returned by /check-answer response only",
      "feedback": "string"
    }
  ],
  "final_simulation": { "correct_path": "STRIPPED", "wrong_path": "..." },
  "feedback_summary": {},
  "completion_rules": {}
}
```

#### `case_based_preview.decision_process_explanation` (additive, commit 92824a3)

An **optional** sub-object on `case_based_preview`. When absent, the CBP flow goes
directly from the 3 checkpoints to the simulation (legacy behaviour preserved).
When present, a "Decision Process Explanation" step is inserted between the
checkpoints and the simulation.

```json
"decision_process_explanation": {
  "prompt": "string — student-visible instruction text",
  "min_chars": 80,
  "concept_keywords":    ["..."],
  "method_keywords":     ["..."],
  "mistake_keywords":    ["..."],
  "acceptable_keywords": ["..."],
  "rubric": "string — AI grading rubric",
  "pass_score": 60
}
```

**Answer-bearing fields (stripped at hydration; never reach the client):**
`concept_keywords`, `method_keywords`, `mistake_keywords`, `acceptable_keywords`,
`rubric`, `pass_score`.

**Client-visible fields only:** `prompt`, `min_chars`.

Grading is via `POST /api/ai/check-answer` with `phase="case_based_preview_reasoning"`
(see `docs/API.md`). The step is **non-blocking**: `gate_state.compute_gate_state`
includes `reasoning_required` and `reasoning_passed` flags and factors
`reasoning_passed` into `cbp.passed`, but the MCQ checkpoints remain the
Practice-Arc unlock gate.

### `memory_check` (MemoryCheck)

```json
{
  "items": [
    {
      "type": "mcq | fill_blank | choose_explanation | true_false",
      "prompt": "string",
      "options": ["..."],
      "answer_spec": { /* AnswerSpec — STRIPPED before hydration */ },
      "flashcard_ref": "optional id"
    }
  ],
  "pass_threshold_pct": 60,
  "modes_enabled": ["..."],
  "retake_pool_size": 0
}
```

### gb_* practice-arc game arrays (additive, structured)

These coexist with the legacy `gb_*` shapes documented in §1. New structured
models add validation; existing rows are untouched.

| Key | Model | Notes |
|---|---|---|
| `gb_adaptive_quiz` | `AdaptiveQuizItem[]` | `{q\|prompt, tier, ans[]/answer_spec}` (same answer_spec contract as boss). |
| `gb_mystery_box` | `MysteryBoxItem[]` | `{category, q, a}`. |
| `gb_puzzle_lock` | `PuzzleLockItem[]` | `{content, q, a}` (legacy `{text, question, answer}` aliases accepted). |
| `gb_ttt` | `TttItem[]` | `{id?, q, correct, distractors[]}` — `correct`/`distractors` are server-only. `gb_ttt_config` carries XP/session overrides. |
| `gb_sentence_fill` | `SentenceFillItem[]` | cloze `passage` with 1–6 `___` blanks + per-blank `answers[]` + optional `word_bank`. |
| `gb_tile_match` | `TileMatchPair[]` | structured `{id, left, right, tier, …}`; 0–8 pairs, unique ids/lefts/rights, ≤1 `is_palace_tile`. |
| `gb_memory_palace` | `MemoryPalaceGame` | `{palaces[], concepts[]}` Method-of-Loci routes (3–7 locations each). |
| `real_life_challenge` | `RealLifeChallengeCase` | 5-step expert role-play (decision → info_request → final_decision → concept_select → reasoning). |
| `boss_questions` | `BossQuestion[]` | unchanged final-boss phase. |

### Runtime API + check-answer contracts (v2)

Two NEW read endpoints (`server/routes/runtime.py`):

| Method | Path | Returns |
|---|---|---|
| GET | `/api/runtime/homeworks/{id}` | Redacted hydration payload `{id, title, subject, grade, lang, flow_version, content_json}` — answers stripped server-side. |
| GET | `/api/runtime/homeworks/{id}/gate-state?session_id=` | Server-authoritative `{cbp:{passed,checkpoints_correct,checkpoints_total,threshold}, mc:{passed,score_pct,correct,total,threshold_pct}, practice_arc_unlocked}`. |

**Hydration-redaction boundary** (`server/services/runtime_redactor.py`, deny-list
in `server/services/redaction_constants.py::ANSWER_BEARING_KEYS`):

- Fail-closed DENY-list: every key in `ANSWER_BEARING_KEYS` (incl. the whole
  `answer_spec` subtree, `expected`, `accepted_answers`, `correct`,
  `option_index`, `is_correct`, `acceptable_keywords`, `consequence`,
  `correct_path`, `learning_block`, `distractors`, …) is deleted at every
  nesting depth. The input DB row is never mutated.
- **Tile-match** ships opaque per-side tokens — `{lefts:[{lid,text}], rights:[{rid,text}]}` —
  with the two columns shuffled independently (seeded on `hw_id`). No field links
  a left to its right; the grader recovers the pair index from each HMAC token
  server-side. `gb_memory_match` is dropped from hydration entirely.
- **TTT** ships `{id, q, options[]}` with the correct answer riding as one
  unmarked, shuffled MCQ option; `correct`/`distractors` keys stay stripped.
- **`learning_block` / `feedback`** are post-submit teaching text — they come
  from the `/check-answer` *response*, never from hydration.

**Per-phase `POST /api/ai/check-answer` submit + response** (all carry
`homework_id` + `session_id`; response is `{correct, feedback}` unless noted):

| `phase` | Submit fields | Response |
|---|---|---|
| `case_based_preview` | `{item_index, student_answer}` | `{correct, feedback, learning_block?}` |
| `memory_check` | `{item_index, student_answer}` | `{correct, feedback}` |
| `tile-match` | `{left_id, right_id}` (opaque tokens) | `{correct, …xp/hint}` |
| `ttt` | `{item_id, picked}` | `{is_correct, mercy, xp_delta, correct_value}` |
| `ttt-session` | `{results:[{outcome}]}` | `{session_xp, strong_session_bonus, mastery_tier, wins, draws, losses, …}` |
| `sentence-fill` | `{item_id, blank_idx, student_value}` | `{correct, …}` |
| `real-life-challenge` | `{step_id, selected_option_id \| selected_chip_id \| reasoning_text}` | `{correct, …}` (step-dependent) |
| `memory-palace` | `{palace_key, placements[], recall_results[]}` | `{outcome, accuracy_pct, correct_count, total_count, …}` |
| `final-boss` | `{question_id: "bq_{i}", student_answer}` | boss-turn shape (delegates to `tutor.boss_turn`) |
| `adaptive-quiz` | `{item_index, student_answer}` | `{correct, feedback}` |
| `mystery-box` | `{item_index, student_answer}` | `{correct, feedback}` |
| `puzzle-lock` | `{item_index, student_answer}` | `{correct, feedback}` |

**Gate computation** (`server/services/gate_state.py`): aggregates on the
SERVER-DERIVED `subphase` key (`checkpoint_{idx}` / `item_{idx}`), never on the
client `question_id` (no-inflation invariant). `practice_arc_unlocked` is true
only when CBP ≥ max(2, 60% of checkpoints) AND Memory Check ≥ `pass_threshold_pct`
(default 60%).

**Practice-arc gating (403 enforcement).** All 8 practice-arc phases
(`tile-match`, `sentence-fill`, `real-life-challenge`, `ttt`, `ttt-session`,
`memory-palace`, `adaptive-quiz`, `mystery-box`, `puzzle-lock`, `final-boss`)
call `_enforce_practice_unlocked(req)` before grading and return `403
{code: "PRACTICE_LOCKED"}` until the arc is unlocked. `case_based_preview` and
`memory_check` are deliberately UNGATED — they ARE the unlock path.

---

## Dynamic Boss Arena (Plan-5 + WHW)

Shipped in PRs #252 (backend) and #253 (frontend). Five net-new endpoints under
`/ai/boss/*` in `server/routes/ai_plan5.py`. The legacy `/ai/boss-turn` and the
static `content_json.boss_questions` flow remain as fallbacks; the dynamic path
opts in only when the runtime calls these new endpoints with a `boss_session_id`.

**Hard rules:**
- Backend is authoritative for HP, trials, difficulty, and outcome. The client
  never sets or trusts these values.
- Generator output is validated server-side (Pydantic + business rules) before
  storage; rejected questions are not persisted.
- The frontend never receives `expected_answer`, `rubric`, or any answer-bearing
  field for a generated boss question — only prompt text (`question_text`,
  `scenario`, `why`, `how`, `what`) plus `difficulty` and `target_skill`.

---

### Endpoint shapes

#### POST /ai/boss/start

Request:
```json
{
  "session_id": "string",
  "homework_id": "string",
  "max_hp": 100,
  "trials_left": 7,
  "initial_difficulty": "medium",
  "force_fresh": false
}
```

`max_hp` is advisory only — the server derives the real HP from `boss_meta.grade_band` +
`boss_meta.starting_hp_override`. `force_fresh: true` archives any existing active
session for this `(session_id, homework_id)` pair and starts a clean one (use when
the student explicitly clicks "Restart boss").

Response:
```json
{
  "boss_session_id": "bs_<hex16>",
  "hp": 100,
  "max_hp": 100,
  "trials_left": 5,
  "current_difficulty": "medium",
  "weak_topics": ["string"],
  "strong_topics": ["string"],
  "missing_context_flags": ["string"]
}
```

Idempotent on page refresh: if an active session exists and was updated within the
last 30 minutes, it is returned unchanged instead of creating a new row.

---

#### POST /ai/boss/generate-question

Request:
```json
{
  "boss_session_id": "bs_<hex16>",
  "recent_boss_phrases": ["string"]
}
```

Response (no answer-bearing fields):
```json
{
  "question_id": "gbq_<hex16>",
  "question_text": "string",
  "scenario": "string",
  "why": "string",
  "how": "string",
  "what": "string",
  "target_skill": "string",
  "difficulty": "easy|medium|hard",
  "why_this_question": "string",
  "boss_session_id": "bs_<hex16>"
}
```

`scenario`, `why`, `how`, `what` are PROMPT text only — they contain no answer or
rubric content and are safe to send to the client. On a 502 with
`code: "BOSS_GEN_REJECTED"` the runtime shows a "Try again" state; one retry
usually succeeds (Kimi ReadTimeout is the most common transient cause).

---

#### POST /ai/boss/submit-answer

Request:
```json
{
  "boss_session_id": "bs_<hex16>",
  "question_id": "gbq_<hex16>",
  "student_answer": "string"
}
```

`student_answer` is the only answer field the client ever sends to a boss endpoint.

Response:
```json
{
  "is_correct": true,
  "score": 0.9,
  "confidence": 0.85,
  "feedback": "string",
  "damage": 18,
  "hp": 82,
  "trials_left": 4,
  "current_difficulty": "medium",
  "boss_status": "active|won|failed",
  "should_retry_same_skill": false,
  "misconception_tags": ["string"],
  "outcome": "expert|strong|passing|hali_emas",
  "stars": 3,
  "outcome_xp": 200,
  "coverage": {"why": 0.9, "how": 0.8, "what": 0.95}
}
```

`outcome`, `stars`, `outcome_xp` are populated only when `boss_status` is `won` or
`failed`. `coverage` is populated only when the answer-checker returns a per-axis
breakdown; it is absent (null) for legacy/flat verdicts.

`boss_status` is a state-machine label, not a student-facing performance judgment
(`won` means boss HP reached 0; `failed` means trials ran out). The
student-facing tier is `outcome`.

---

#### POST /ai/boss/state

Request:
```json
{
  "boss_session_id": "bs_<hex16>"
}
```

Response (mirrors `/start` shape plus the current question summary):
```json
{
  "boss_session_id": "bs_<hex16>",
  "session_id": "string",
  "homework_id": "string",
  "status": "active|won|failed|abandoned",
  "hp": 82,
  "max_hp": 100,
  "trials_left": 4,
  "current_difficulty": "medium",
  "current_question_id": "gbq_<hex16>|null",
  "asked_question_ids": ["gbq_<hex16>"],
  "weak_topics": ["string"],
  "strong_topics": ["string"],
  "current_question": {
    "question_id": "gbq_<hex16>",
    "question_text": "string",
    "scenario": "string",
    "why": "string",
    "how": "string",
    "what": "string",
    "difficulty": "medium",
    "target_skill": "string"
  }
}
```

`current_question` is null when no question is active. No answer or rubric fields
are included — this endpoint is safe to poll for resume-on-refresh.

---

#### POST /ai/boss/give-up

Request:
```json
{
  "boss_session_id": "bs_<hex16>"
}
```

Response: same shape as `/ai/boss/state`. Sets `status = "abandoned"`. If the
session is already in a terminal state, the existing state is returned unchanged.

---

### Authored `content_json.boss_questions[]` — WHW fields

The existing legacy fields (`q`, `ans`, `dmg`, `hint`, `tags`) remain valid. The
following WHW fields are ALL OPTIONAL and additive; legacy rows without them
continue to render and grade through the unchanged fallback path.

```json
{
  "q": "string (legacy headline — still valid)",
  "ans": ["accepted_answer"],
  "dmg": 20,
  "hint": "string",
  "tags": "[Bloom: L2 | PISA: L2 | Damage: -20 HP]",

  "scenario": "string — real-life framing shown to the student",
  "why": "string — Why axis prompt shown to the student",
  "how": "string — How axis prompt shown to the student",
  "what": "string — What axis prompt shown to the student",

  "expected_concepts": ["string"],
  "concept_tag": "string",
  "bloom": "L1|L2|L3|L4|L5|L6",
  "pisa": "L1|L2|L3|L4",

  "hints": ["string — ordered hint list, max 3"],
  "correct_feedback": "string — shown on full-credit answer",
  "partial_feedback": "string — shown on partial-credit answer",
  "wrong_feedback": "string — shown on wrong answer"
}
```

All WHW fields (`scenario`, `why`, `how`, `what`, `expected_concepts`,
`concept_tag`, `bloom`, `pisa`, `hints`, `correct_feedback`, `partial_feedback`,
`wrong_feedback`) are stripped from hydration before the payload reaches the
client, just like `answer_spec.expected`. They are only used server-side for
grading and dynamic generation anchoring.

---

### `boss_meta` fields

`content_json.boss_meta` is read server-side at `/ai/boss/start` time to
configure the session. It is NOT injected into the runtime as a JS constant.

```json
{
  "boss_type": "string",
  "grade_band": "g1_4|g5|g6_8|g9_11|G1-4|G5-8|G9-11|1..11",
  "attempts_max": 7,
  "starting_hp_override": null,
  "anti_cheat": {
    "paste_detect": false,
    "response_time_floor_ms": 0
  }
}
```

`grade_band` drives the server-authoritative starting HP (see grade-band HP table
below). `starting_hp_override` (integer, minimum 10) overrides the band lookup
entirely when set. `anti_cheat` is read but not enforced in the current lane —
see the Anti-cheat extension points section below.

---

### Grade-band HP table

| Band | `grade_band` values accepted | Starting HP |
|---|---|---|
| G1-4 | `g1_4`, `G1-4`, grades 1–4 | 50 |
| G5-8 | `g5`, `g6_8`, `G5-8`, grades 5–8 | 100 |
| G9-11 | `g9_11`, `G9-11`, grades 9–11 | 150 |
| (default) | absent / unrecognized | 100 |

`starting_hp_override` (integer, minimum 10) takes precedence over all band
lookups when present in `boss_meta`.

---

### Coverage-based damage formula

Each answer submission computes `damage = BASE × accuracy × hint_penalty × multiplier × combo`.

**BASE damage by difficulty:**

| difficulty | BASE |
|---|---|
| easy | 10 |
| medium | 20 |
| hard | 30 |

**Accuracy tier** (derived from `coverage_mean` when a per-axis `coverage` dict
is returned by the checker, else from the flat `score`):

| coverage/score | accuracy multiplier |
|---|---|
| >= 0.85 | 1.0 |
| >= 0.55 | 0.7 |
| >= 0.30 | 0.5 |
| < 0.30 | 0.0 (wrong — no damage) |

**Hint penalty** (from `boss_sessions.hints_used`):

| hints used | multiplier |
|---|---|
| 0 | 1.0 |
| 1 | 0.8 |
| 2 | 0.6 |
| 3+ | 0.3 |

**Combo bonus:** if the student enters a roll on a tail streak of 3 or more
consecutive full-accuracy correct answers (score >= 0.85) with zero hints used,
damage is multiplied by 1.2. The streak resets on any wrong answer or hint use.

**Invariant:** an `is_correct` answer always deals > 0 damage. The server
floors `score` and coverage mean to 0.60 on a correct verdict so the answer
never lands in the zero-accuracy tier.

**`multiplier`** is recommended by the AI checker (range 0.0–1.5, clamped by the
server). On a correct answer the server floors it to 1.0.

---

### `boss_sessions` table schema

```sql
CREATE TABLE IF NOT EXISTS boss_sessions (
  id                     TEXT PRIMARY KEY,
  session_id             TEXT NOT NULL,
  homework_id            TEXT NOT NULL,
  status                 TEXT NOT NULL DEFAULT 'active',
  hp                     INTEGER NOT NULL DEFAULT 100,
  max_hp                 INTEGER NOT NULL DEFAULT 100,
  trials_left            INTEGER NOT NULL DEFAULT 7,
  current_difficulty     TEXT NOT NULL DEFAULT 'medium',
  current_question_id    TEXT,
  asked_question_ids_json TEXT NOT NULL DEFAULT '[]',
  weak_topics_json       TEXT NOT NULL DEFAULT '[]',
  strong_topics_json     TEXT NOT NULL DEFAULT '[]',
  hints_used             INTEGER NOT NULL DEFAULT 0,    -- NEW (Plan-5 + WHW)
  correct_count          INTEGER NOT NULL DEFAULT 0,    -- NEW (Plan-5 + WHW)
  total_attempts         INTEGER NOT NULL DEFAULT 0,    -- NEW (Plan-5 + WHW)
  question_kind          TEXT,                          -- NEW (Plan-5 + WHW)
  created_at             TEXT NOT NULL,
  updated_at             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_boss_sessions_session
ON boss_sessions(session_id, homework_id, status);
```

The four new columns are added by the migration in `server/db/migrations.py`
(idempotent `ALTER TABLE … ADD COLUMN` guards). Legacy rows without them default
to `0 / NULL`.

| Column | Purpose |
|---|---|
| `hints_used` | Running count of hints consumed in this session; drives the hint_penalty multiplier. |
| `correct_count` | Running count of correct submissions; used by `compute_boss_outcome`. |
| `total_attempts` | Running count of all submissions (correct + wrong); used by `compute_boss_outcome`. |
| `question_kind` | Optional shape tag for the question type (e.g. `"whw"`); reserved for analytics. |

---

### Answer-leak guarantee for the boss

The dynamic boss path enforces a strict boundary:

1. `/ai/boss/generate-question` returns `question_text`, `scenario`, `why`, `how`,
   `what`, `target_skill`, `difficulty`, and `why_this_question` ONLY. The
   `expected_answer`, `rubric`, and all coverage-rubric fields are stored
   server-side and never returned to the client.

2. `/ai/boss/state` rehydrates the current question from storage but strips the
   same fields — only the four prompt parts (`scenario`/`why`/`how`/`what`) and
   `question_text` are returned.

3. `student_answer` is the only answer payload the client ever sends. The server
   fetches the stored expected answer and rubric for grading; the client never
   sees them.

4. The generator prompt never receives answer keys from prior asked questions
   (the internal anti-repetition queue carries only `question_text` and
   `target_skill`).

5. Student text (`student_answer`) is wrapped in
   `<UNTRUSTED_STUDENT_MESSAGE>…</UNTRUSTED_STUDENT_MESSAGE>` before it enters
   any LLM prompt (Plan 7 §2).

---

### Anti-cheat extension points (RESERVED — not enforced here)

The following seams are documented for the separate anti-cheat lane. They are
NOT implemented in the current backend code. Documenting them here prevents
accidental collision when the anti-cheat lane is built.

**(S1) `boss_meta.anti_cheat` config block** — `{paste_detect: bool, response_time_floor_ms: int}`.
The server reads this field from `content_json.boss_meta` inside
`/ai/boss/submit-answer` but does NOT act on it yet. The anti-cheat lane should
read these flags to enable enforcement without modifying the schema.

**(S2) `client_time_ms` on `BossSubmitAnswerRequest`** — An optional integer field
may be added additively to the submit-answer request body and persisted to the
existing `attempt.time_ms` column. The column already exists in `phase_attempts`;
no schema change is needed. The anti-cheat lane should add this field without
altering other request fields.

**(S3) `boss:paste_detected` client telemetry event** — A `nets:boss-telemetry`
CustomEvent (or similar) in `BossArena.tsx` is the intended hook for
paste-detection signals. The frontend currently dispatches no such event; the
anti-cheat lane should add it addend-only without touching the existing
`nets:submit` event contract.

**(S4) `session_metrics.avg_time_ms < response_time_floor_ms` flag condition** —
`session_metrics` already stores per-session `avg_time_ms`. The anti-cheat lane
can query this against `boss_meta.anti_cheat.response_time_floor_ms` to flag
suspiciously fast sessions without a new table.

**(S5) `ai_call_logs` source tag** — `ai_call_logs.task_type` distinguishes boss
generation (`boss_question_generate`) from answer checking (`boss_answer_check`).
The anti-cheat lane may add a `source_tag` or similar column to correlate an
answer submission latency against the AI generation latency for the same question,
without altering existing rows.

All five seams are additive — no existing field or table is modified to
accommodate them.
