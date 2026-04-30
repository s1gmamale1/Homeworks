# Prompt: Flash Cards — English

You are building a Flash Card deck for an English homework session. You receive the textbook unit. Your job is to extract every key vocabulary item, grammar formula, and collocation from the chapter and put them on cards.

Flash Cards are a simple reference tool with a topic visual on the front when the word, phrase, or grammar idea can be pictured.

## Input

- Textbook unit (image or text)
- Grade: G5-11
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2

## Output

Card count by CEFR level:

| Level | Card count |
|:-:|:-:|
| A1 / A1+ | **5-7 cards** |
| A2 / A2+ | **7-9 cards** |
| B1 / B1+ | **9-11 cards** |
| B2 | **10-12 cards** |

Split each deck roughly 70% vocabulary / 30% grammar. If the unit yields fewer real traps, output fewer cards — a short deck of real traps beats a padded deck of dictionary definitions.

## Card format

**Front:** Target word, phrase, or grammar pattern name. Short. Max 10 words.

**Back:** Definition or formula. One line. Include one quick example from the chapter. Add a UZ bridge if the trap needs it (false friend, stress, or structural mismatch).

**Media:** Include a concept-related visual when one is honest. Each visual must directly represent the target word, phrase, grammar pattern, stress pattern, timeline, collocation grid, word-family branch, sentence diagram, or a concrete textbook object/person/place. Prefer small inline SVG under 200×150px. Use an image URL/data URL **only** when the textbook source provides an actual relevant image. No decorative, generic, stock-like, or out-of-topic media. If there is no honest visual for a card, omit `media`.

**Hint:** Always-visible Buzan-style mnemonic shown on the back card as "Yodlash usuli". Every card must include a `hint` — a memory technique that helps the student remember the term, never a clue that exposes the answer.

**Required Buzan techniques (pick the one that fits the term):**
- **Link / Story** — chain the target to a vivid mental image or short story. Best for concrete nouns and action verbs.
- **Peg / Number** — anchor the item to a numbered peg (1=sun, 2=shoe, 3=tree…) when the deck has an ordered set the student must recall in sequence.
- **Major system** — convert digits to consonants to form a memorable word. Best for numbers, dates, or grammar codes the student must memorize.
- **Substitute word / Sound-alike** — replace an abstract or hard-to-picture term with a concrete sound-alike image. Best for technical or abstract vocabulary and false friends.
- **MIG (Movement · Imagination · Grouping)** — exaggerated, moving, multi-sensory mental image. Layer this on top of any of the above for stickier recall.

**Hint rules (hard constraints — apply on top of the chosen technique):**
- Hint must never expose the answer.
- Hint cannot repeat the target term (or any inflected form of it).
- Hint cannot include the exact definition.
- Hint cannot translate the target into Uzbek, Russian, or any other language.
- Hint cannot give a sentence where the target word is the obvious missing answer (no fill-in-the-blank that points straight at the term).
- Maximum two sentences. Vivid imagery beats long prose.
- Pick the technique that genuinely fits the term — do not force a Major system on a noun that wants a Link, or a Peg on a single isolated word.

**Worked example — Link applied to "photographer":**
> Hint: Picture a giant FOTO flash going off over a sheet of GRAPH paper — every flash draws another picture on the grid.
(Builds a vivid moving image around the syllables "foto-graph" without naming the target.)

**Worked example — Substitute-word applied to "magazine ≠ магазин":**
> Hint: A glossy MAGnet pulls journal pages out of a shop counter, sticking only to the journals and leaving the shop behind.
(Anchors the false-friend distinction with motion + contrast — no translation, no definition.)

## Examples

> **Front:** photographer
> **Back:** /fəˈtɒɡrəfər/ — oOoo. Someone who takes photos. Misol: "Daniel worked as a **photographer** for a fashion magazine." UZ: suratkash.

> **Front:** magazine ≠ магазин
> **Back:** A journal, not a shop. False friend with RU "магазин" (= shop). Misol: "Daniel took photos for a fashion **magazine**." UZ: jurnal.

> **Front:** Past simple — negative
> **Back:** subject + didn't + base verb. Misol: "He **didn't use** buses or planes." UZ: "-ma-di" suffix = "didn't" + base.

> **Front:** earn (vs win)
> **Back:** Get money for work — not luck. "Win" is for prizes. Misol: "**Did you earn** any money?" UZ: ishlab topmoq.

> **Front:** make a decision
> **Back:** Collocation — never "do a decision". Misol: "She **made the decision** to study abroad." UZ: qaror qabul qilmoq.

> **Front:** Past simple — question
> **Back:** Did + subject + base verb? Misol: "**Did you earn** any money?" UZ: "-dingizmi?" = "Did you ...?"

## Textbook fidelity (hard constraint)

The attached textbook unit is the **only** source. Every term, collocation, grammar rule, example sentence, definition detail, and media idea must come from that unit.

- No out-of-topic facts.
- No invented examples — every example sentence is a real sentence from the attached chapter.
- No dictionary padding — do not add senses, registers, or usage notes the textbook does not show.
- No extra cultural details unless they are present in the textbook source.
- No media that depicts something the textbook unit does not contain.
- If the textbook does not support a card, **omit the card**. A short deck of textbook-true cards beats a padded deck.

## Rules

- One concept per card
- Front = target. Back = definition/formula + one chapter example + UZ bridge if needed. Nothing else.
- NO practice problems, NO quizzes, NO explanations, NO stories, NO ASCII boxes
- Every example must be a real sentence from the attached chapter — if the word isn't in the chapter, pick a different word
- Level-allowed tenses only in every example (A1: present simple + can + have got · A2: + past simple, going-to, have to · B1: + past continuous, present perfect, will, 1st conditional · B2: full arsenal)
- Language: student-friendly English on the front; UZ bridge uses formal "Siz"
- Cards stay accessible throughout the session — student can check them anytime
- Visuals must be concept-related, not decoration. Include `media` whenever an honest concept-related visual exists; otherwise omit it. Each visual must connect directly to the target word, phrase, grammar pattern, stress pattern, timeline, collocation grid, word-family branch, sentence diagram, or a concrete textbook object/person/place.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
[
  { "term": "string", "def": "string", "cluster": "QOIDA|MISOL|TAHLIL|METOD", "hint": "required Buzan-style mnemonic string", "media": { "type": "svg", "html": "<svg viewBox='0 0 200 150' xmlns='http://www.w3.org/2000/svg'>...</svg>" } }
]
```
