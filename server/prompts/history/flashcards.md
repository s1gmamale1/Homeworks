# Prompt: Flash Cards — History (O'zbekiston Tarixi + Jahon Tarixi)

You are building the Flash Card deck (Phase 0-B) for a History homework session. Extract the lesson's key figures, concepts, and modern echoes into atomic recall cards. Flash Cards are a reference tool — not practice, not questions, not scenarios.

## Input

- Textbook lesson content (extracted in orchestrator Step 1 — Uzbek)
- Grade: G5–G11
- Subject: `O'zbekiston Tarixi` or `Jahon Tarixi`
- Milliylik intensity: `high` or `low`
- Preview output (for Memory Palace station references)

## Output

**8 cards** (target; allow 6–10 depending on lesson density) grouped into 3 clusters:

- **1-klaster: Ismlar (Names / Figures)** — ~50% of cards
- **2-klaster: Ramka tushunchalari (Frameworks / Core Concepts)** — ~30% of cards
- **3-klaster: Bogʻliqliklar (Modern Echoes)** — ~20% of cards (Milliylik payload)

All cards in Uzbek. "Siz" if referenced.

## Card format — 4 fields

**Front:** Term name, figure name, or concept phrase. Max 10 words. No context.

**Back:** Definition + key facts. 1–3 sentences. NO practice, NO examples, NO questions.

**Xotira tasviri (Buzan hook):** One vivid memory aid. Pick one type:
- Visual image (figure holding item, place with event)
- Sound chain (e.g., Kebek → kepaki → kopeyka)
- Number pattern (e.g., 1-2-2-5 for the year 1225)
- Evolution chain (e.g., mulk → davlat → xalq for evolving meaning)
- Etymology link (e.g., Qarshi ← qarsh)

**Media:** Aim to include a small topic-related visual on every card: figure silhouette, map/place marker, timeline/date hook, coin/object, dynasty branch, or memory-palace station. Prefer inline SVG under 200×150px. If a card truly has no honest visual, omit `media`.

**Saroy bekati (optional Memory Palace station tag):** When the card's content maps to a station in the Preview's Memory Palace, tag as `N — PLACE NAME`. Skip for abstract frameworks that aren't location-bound.

Include a **Sana qarmogʻi (date hook)** inline with the Xotira tasviri when a figure or reform is tied to a specific year. Embed dates in figure cards; do NOT create standalone date cards.

---

## Cluster guidance

### 1-klaster: Ismlar (Names) — ~50%
- Central figures (rulers, scholars, chroniclers, dynasties)
- Dates embedded via Sana qarmogʻi
- Combine father/son or founder/successor into one card when they share a single historical function

### 2-klaster: Ramka tushunchalari (Frameworks) — ~30%
- Key textbook terms (xoqon/xon, ulus, yasoq, tuman, etc.)
- Concepts whose meaning evolves across the lesson's period
- Definitions only — no how-to content

### 3-klaster: Bogʻliqliklar (Modern Echoes) — ~20%
- Milliylik payload — modern names, currencies, institutions, ideas that trace back to the lesson
- `milliylik_intensity: high` → 1–2 cards tying today's Uzbek present to the lesson
- `milliylik_intensity: low` → 0–1 cards (world parallels only when genuinely historical)

---

## Examples

### Name card

**Front:** Chigʻatoyxon

**Back:** Chingizxonning ikkinchi oʻgʻli. Markaziy Osiyo ulusining xoni (1225–1242). Yasoq qonunining qatʼiy qoʻriqchisi.
**Xotira tasviri:** Yasoq kitobini ikki qoʻli bilan mahkam ushlab turgan, koʻzi oʻtkir.
**Sana qarmogʻi:** 1-2-2-5 (1225, ulus boʻlinishi).
**Saroy bekati:** 1 — Olmaliq

### Framework card

**Front:** Ulus

**Back:** Chingizxon tuzgan mulk birligi. Maʼnosi vaqt bilan oʻzgargan: mulk → mustaqil davlat → "xalq".
**Xotira tasviri:** Uch bosqichli zina — bir soʻz, uch maʼno.

### Modern echo card

**Front:** Kepaki → Kopeyka

**Back:** Kebekxonning 1321-yilgi tangasi Oltin Oʻrda orqali rus pul birligining nomiga aylandi.
**Xotira tasviri:** Tovush zanjiri K-e-p-a-k-i → K-o-p-e-y-k-a.
**Saroy bekati:** 4 — Qarshi

---

## Rules

- **One concept per card.** Atomic recall. Don't combine unrelated facts.
- **Front = name / term only.** No context, no question, no partial sentence.
- **Back = definition + key facts only.** NO practice problems, NO questions, NO scenarios, NO "try this," NO explanatory paragraphs.
- **Every card MUST have a Xotira tasviri.** No naked definitions.
- Put the Xotira tasviri text in `hint`; put the picture/diagram in `media` when possible.
- **Saroy bekati is optional** — include only when card content maps to a Preview palace station.
- **Dates inside figure cards** via Sana qarmogʻi. No standalone date cards.
- **Textbook fidelity** — every fact from the source lesson. If it isn't in the textbook, it isn't on a card.
- **Language:** Uzbek, `Siz` if referenced. Never `sen`.
- **No frozen / removed terminology** (no references to v2+ game mechanics or content that isn't in this lesson).
- **Card count:** 8 target; 6–10 range. Don't pad to hit 10; don't skimp below 6.
- **Returnable throughout session:** cards are reviewable in any later phase as a quick overlay.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
[
  { "term": "string", "def": "string", "cluster": "QOIDA|MISOL|TAHLIL|METOD", "hint": "Xotira tasviri / optional mnemonic string", "media": { "type": "svg", "html": "<svg viewBox='0 0 200 150' xmlns='http://www.w3.org/2000/svg'>...</svg>" } }
]
```
