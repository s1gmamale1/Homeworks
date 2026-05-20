# Content Production + Grade-Band Gap Audit — 2026-05-09

---

## TL;DR

- **Grades 1-4 are completely absent.** Zero prompts, zero schema support, zero subject coverage. Trello card #1 has no codebase footprint at all.
- **Grades 5-6 exist only inside math-algebra** (`preview-hard.md:10` stamps G5-6 explicitly). Every other subject starts at G7. This leaves a 2-grade dead zone for biology, physics, kimyo, geometriya, and history.
- **No video or audio infrastructure exists** anywhere in the runtime or content_json schema. "Preview" is a text+SVG reading phase, not a media phase. Trello cards #2 and #3 are entirely aspirational.
- **Teacher-facing materials are absent.** No teacher route, no PPTX pipeline, no export endpoint. One i18n string mentions "teachers"; grading.py has one teacher-facing comment. That is the full extent.
- **Three subject families referenced in frontend code (til-fanlar: russian, uzbek, literature; ijtimoiy-fanlar: social) have zero prompt directories.** They are UI labels only.
- **Language coverage is Uzbek-primary everywhere except English (English-content) and kimyo-g7-11 (Uzbek + Russian conditional).** No Russian-language prompt set exists in-repo despite the routing.py mapping `geometry` to a `geometriya-g7-ru/` dir that does not exist.

---

## What Content Surfaces Exist (Codebase Scan)

### "Preview" phase
The word "preview" in the runtime (`perfect_homework.html:10902`) and prompt dirs refers to **Phase 0-A: reading panels**. It is a paginated text+SVG reader — not a video player. `server/prompts/history/preview.md`, `server/prompts/*/preview-hard.md`, and `server/prompts/*/preview-easy.md` all define the preview phase as JSON panels of `{type: p|h2|quote|ul|ol|svg|image}` blocks. No `{type: video}` block type exists.

### Video / audio
- `perfect_homework.html` contains zero `<video>`, `<audio>`, or `<iframe src>` elements for media.
- Grep across `server/` + `frontend/` for `mp4|mp3|audio|video` returns:
  - `frontend/js/editors/preview.js:525` — a `querySelector` guard that includes `video` and `audio` as elements that make a rich-field block "not plain text" (defensive check, not a media player).
  - `server/prompts/english/instruction.md:14` — instructs the AI to extract "audio scripts" from textbooks. No runtime playback exists to serve them.
  - One inline demo sentence in the runtime fixture data at line 10354 uses the word "video" in Uzbek prose ("basketbol video o'yinidagi"). That is content, not infrastructure.
- **No mp4, mp3, or pptx files exist in the repo** (glob returns empty).

### Teacher materials
- `server/routes/grading.py:62` — inline comment "Useful for the dashboard (so a teacher can see the rubric)". No `/teacher/` route prefix exists.
- `frontend/js/i18n/strings.js:132` — one string: `'dashboard.insights_text': 'Fast glance for teachers: what is ready, what needs edits, and what can be shared now.'` This is a UI label on the dashboard, not a teacher-mode page.
- No PPTX generation library, no export endpoint, no builder "export" button.

### Listening / audio scripts
- English `instruction.md` says "extract any audio scripts" from textbooks — treating them as source material for reading-phase text, not for playback.
- No TTS integration, no CDN audio URL field, no waveform component.

---

## Per-Subject Inventory Matrix

| Subject | Files | LOC | Media refs in prompts | Languages | Grade band |
|---|:-:|:-:|---|---|---|
| biology | 12 | 1 242 | SVG mandatory per instruction; no video/audio | Uzbek only | G5–11 |
| english | 11 | 1 651 | SVG context picture in reading phase; audio scripts as text only | English (student-facing); Uzbek bridge lines | G5–11 (CEFR A1–B2) |
| geometriya-g7-11 | 12 | 1 625 | SVG mandatory per instruction.md; instruction.md references `geometriya-g7-ru/` dir (does NOT exist in repo) | Uzbek (Russian conditional, missing dir) | G7–9 (dir name says G7-11 but classify.md says G7-9) |
| history | 9 | 1 121 | IMAGE placeholders (bracket format), no actual media pipeline | Uzbek only | G5–11 |
| kimyo-g7-11 | 12 | 1 513 | SVG mandatory; no video | Uzbek or Russian (conditional per textbook) | G7–11 |
| math-algebra | 12 | 1 091 | SVG mandatory; bar models, number lines | Uzbek only | G5–6 (Matematika) + G7–9 (Algebra) |
| physics | 12 | 1 043 | SVG mandatory; 2 `.svg` files in dir (circular-motion) | Uzbek only | G7–11 |

**Not in repo — UI-only subject IDs registered in dashboard.js:**
- `russian` (til-fanlar) — no prompt dir
- `uzbek` (til-fanlar) — no prompt dir
- `literature` (til-fanlar) — no prompt dir
- `social` (ijtimoiy-fanlar) — no prompt dir

---

## Grade-Band Coverage Matrix

| Subject | G1–4 | G5 | G6 | G7–9 | G10–11 |
|---|:-:|:-:|:-:|:-:|:-:|
| math-algebra | absent | partial (Matematika) | partial (Matematika) | yes (Algebra) | absent |
| geometriya-g7-11 | absent | absent | absent | yes | yes (dir name says G7-11; classify.md only says G7-9 — ambiguous) |
| physics | absent | absent | absent | yes | yes |
| biology | absent | yes | yes | yes | yes |
| kimyo-g7-11 | absent | absent | absent | yes | yes |
| history | absent | yes | yes | yes | yes |
| english | absent | yes | yes | yes | yes |
| russian | absent | absent | absent | absent | absent |
| uzbek (lit) | absent | absent | absent | absent | absent |
| literature | absent | absent | absent | absent | absent |
| social | absent | absent | absent | absent | absent |

**G1–4: 0/7 subjects covered. G5–6: 3/7 covered (biology, history, english). G7–9: 7/7 covered. G10–11: 6/7 covered (math-algebra stops at G9).**

Evidence:
- `server/prompts/math-algebra/preview-hard.md:10` — "Grade: G5-6 (Matematika) or G7-9 (Algebra)"
- `server/prompts/math-algebra/reflection.md:8` — "Grade: G5-6 (Matematika) or G7-9 (Algebra)"
- `server/prompts/biology/classify.md:8` — "Grade: G5-11"
- `server/prompts/history/instruction.md:31` — "G1–4 / G5–8 / G9–11" (HP bands referenced; G1-4 mentioned as a band but no lesson content authored for it)
- `server/prompts/physics/classify.md:1` line 1 — "Grade: G7-11 (Fizika)"
- `server/prompts/kimyo-g7-11/classify.md:8` — "Grade: G7-11"
- `server/prompts/english/classify.md:83` — table starts at G5

---

## Language Coverage Matrix

| Subject | English | Uzbek | Russian |
|---|:-:|:-:|:-:|
| math-algebra | absent | yes | absent |
| geometriya-g7-11 | absent | yes | missing dir (`geometriya-g7-ru/` referenced at instruction.md:20, not in repo) |
| physics | absent | yes | absent |
| biology | absent | yes | absent |
| kimyo-g7-11 | absent | yes | conditional (instruction.md says "if textbook is Russian, use Russian"; no Russian-specific prompt variant) |
| history | absent | yes | absent |
| english | yes (student-facing) | yes (bridge lines only) | absent |
| russian | absent | absent | absent (no dir) |
| uzbek/literature | absent | absent | absent (no dir) |

The tutor (`tutor-assistant.md:156`) responds in Russian when student writes Cyrillic — that is chat-register handling, not subject-language coverage.

---

## Multimedia Infrastructure Status

- **Video player:** no. `perfect_homework.html` has no `<video>` element. `content_json` has no `video` field (`CONTRACTS.md` reviewed in full).
- **Audio player:** no. No `<audio>` element, no TTS API call, no waveform widget.
- **content_json fields for media:** `{type: "svg", html}` and `{type: "image", src, alt}` exist inside `panels[].pages[].blocks[]` and inside `flashcards[].media`. No `{type: "video"}` or `{type: "audio"}` block type.
- **Delivery pipeline:** none. Static assets are served via FastAPI `StaticFiles`. No CDN config, no media upload endpoint, no presigned URL logic. The only "upload" flow is notebook photo capture for vision grading (`server/routes/notebook.py`), which is raw base64 → Kimi K2.6.
- **PPTX / PDF export:** none. No export route, no python-pptx dependency in requirements.

---

## Teacher-Facing Materials Status

The platform has no teacher mode today. Evidence by exhaustion:

- `grep -r "teacher" server/routes/` returns one hit: `grading.py:62` — a comment.
- `grep -r "teacher" frontend/` returns hits in: mathlive-bootstrap, i18n/strings.js, index.html (one label string), editor helpers, landing.js — all UI labels or defensive field names, never a teacher-gated route.
- No `/teacher/`, `/admin/`, or `/export/` prefix in any route file.
- `docs/AUTH_MODEL.md` describes token-in-URL auth; no role-based access control.

What PPTX export would require (given current architecture):
1. New dependency: `python-pptx` (or similar).
2. New route: `GET /api/homeworks/{id}/export/pptx` — reads `content_json`, maps panels/flashcards/questions to slide shapes.
3. The `{type: svg}` blocks would need rasterization (cairo/pillow) to embed into PPTX as images.
4. The runtime template is not Jinja — cannot be repurposed for slide generation; a separate render layer needed.

Effort estimate: 4–6 dev-days for a basic "panels + flashcards as slides" export.

---

## Language Style Lesson — Readiness

**Trello card #7: "5 subjects, video + listening."**

Mapping the "5 subjects" to likely candidates:
1. English — prompt dir exists (1 651 LOC)
2. Russian — prompt dir absent (til-fanlar family registered in dashboard.js, no prompts)
3. Uzbek / Ona tili — prompt dir absent
4. Literature (Adabiyot) — prompt dir absent
5. Potentially a 5th (German/French as elective) — no evidence in codebase

Current English prompt design (`english/instruction.md`, `english/reading.md`): Reading phase extracts the textbook's own passage and builds comprehension checkpoints. Audio scripts are mentioned as source extraction material but have no runtime delivery mechanism. The English prompt is grammar/vocabulary-first, not style-first. Style considerations (register, tone, formality) appear only in `real-life.md:41` (G11 pro roles) and `answer-checker-language.md:71–72`.

**"Listening" infrastructure: zero.** No TTS, no pre-recorded audio field, no `<audio>` tag anywhere. To add listening: minimum viable path is YouTube embed or a hosted `.mp3` URL stored in a new `content_json.reading.audio_url` field, rendered as `<audio controls>` in the reading phase panel.

Readiness score: 1/5. English prompts exist. Everything else (4 subjects, all audio/video infra, style-specific prompt design) is absent.

---

## Highest-Leverage Gap Fills (Top 5, Priority Order)

### 1. Grades 1–4 subject scaffolds — math + Uzbek + English (effort: 8–12 dev-days)
Zero coverage today. The grade band exists as a named HP tier in history's instruction but has no lesson-generation prompts. A G1-4 math prompt requires CPA-only (no algebra), tap-only answer formats (no typing), shorter panel counts (3 panels max), and pictorial flashcards. This unblocks Trello card #1 and is the largest addressable gap by student-count. Suggested first subject: Matematika G1-4 (builds on the existing G5-6 math-algebra flow).

### 2. Video block type + YouTube embed in Preview phase (effort: 3–5 dev-days)
Add `{type: "video", src: "youtube-id|url", caption: "string"}` to `content_json` panels schema and a matching renderer in `perfect_homework.html`. No CDN needed: YouTube embed `<iframe>` via `youtube.com/embed/{id}` is zero-infra. This unblocks Trello cards #2 and #3. The Preview phase is the natural placement — it is already the "watch/read before you practice" gate. Adds interactivity via pause-and-answer checkpoints (one content_json field per video block can hold a checkpoint question).

### 3. Russian-language geometry prompt set + kimyo Russian variant (effort: 2–3 dev-days)
`geometriya-g7-11/instruction.md` references `06-prompts/geometriya-g7-ru/` which does not exist. This is a broken reference that silently falls back to Uzbek even when a teacher uploads a Russian-language textbook. Create `geometriya-g7-11/preview-hard-ru.md`, `preview-easy-ru.md`, and update `instruction.md` to use the correct relative path. Kimyo already has the conditional language rule but no Russian-specific prompt tuning. Combined effort is low; impact is high for Russian-medium school users.

### 4. Prompt directories for `russian`, `uzbek`, `literature` subjects (effort: 5–8 dev-days)
These three subject IDs are live in dashboard.js and routing.py family maps but have no prompt directories. Any teacher creating a homework for these subjects gets an empty or errored session. Minimum viable: copy the `english/` prompt set as a skeleton and adapt for Russian/Uzbek literary analysis conventions (primary source focus for literature, grammar structure for language subjects).

### 5. Teacher PPTX export — `panels[]` as slides (effort: 4–6 dev-days)
Add `python-pptx`, a new route `GET /api/homeworks/{id}/export/pptx`, and a slide renderer that maps each `panels[].pages[].blocks[]` to slide text + each `{type: svg}` block to an embedded rasterized image. No frontend work beyond a download button in the builder. This directly addresses Trello card #10 and is independent of all other gaps.

---

## Constraint Scoring (User's 5 Criteria)

| Criterion | Score (1–5) | Justification |
|---|:-:|---|
| Interactive / gamified | 4 | Adding video to Preview only makes it MORE interactive if videos are checkpointed (pause-and-answer). Pure lecture video makes the cycle LESS interactive. Score assumes checkpoint wiring. |
| Simple, not over-complicated | 5 | YouTube embed + new block type is the lowest-infra path. No CDN, no upload pipeline, no transcoding. |
| Knowledge quality | 3 | Video quality depends entirely on content production outside the codebase. Platform infra can enforce a checkpoint-per-video contract to ensure active watching, but cannot enforce production quality. |
| Phase cycle fit | 5 | Preview phase (Phase 0-A) is architecturally the right slot: students read/watch before practice. The phase name was always a hint. Checkpoints are already the reading phase pattern in English. |
| PISA + real-world | 4 | Short explainer videos tied to real-life contexts (Trello card #2: Tabiy/Aniq fan demos) directly support PISA science/math literacy. G1-4 scaffolding supports foundational PISA-L1 numeracy. |

---

## Open Questions for User

1. **Grades 1–4 subject scope**: which subjects are in scope for the G1-4 push — Matematika only, or also Uzbek Tili and O'qish (reading)? This determines whether 1 new prompt dir or 3 are needed.

2. **Video hosting**: are the "Tabiy + Aniq fan videos" (Trello card #2) already recorded and hosted somewhere (YouTube channel, internal server), or does video production still need to happen? The infra gap is 3–5 dev-days to wire; the content gap depends on this answer.

3. **Language Style Lessons (card #7)**: confirm the 5 subjects. If Russian and Uzbek lit are two of the five, do they share a common prompt scaffold with the existing `english/` flow, or do they need a fundamentally different structure (e.g., close reading vs. grammar drills)?
