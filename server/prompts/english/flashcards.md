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

**Media:** Aim to include a topic-related visual on every card: stress-dot pattern, timeline, word-family branch, sentence diagram, collocation grid, or a concrete textbook object/place/person. Prefer small inline SVG under 200×150px. Use an image URL/data URL only when the source is an actual topic picture. If a card truly has no honest visual, omit `media`.

**Hint:** Optional mnemonic shown on the back card as "Yodlash usuli". Use it for traps students will forget.

That's it.

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

## Rules

- One concept per card
- Front = target. Back = definition/formula + one chapter example + UZ bridge if needed. Nothing else.
- NO practice problems, NO quizzes, NO explanations, NO stories, NO ASCII boxes
- Every example must be a real sentence from the attached chapter — if the word isn't in the chapter, pick a different word
- Level-allowed tenses only in every example (A1: present simple + can + have got · A2: + past simple, going-to, have to · B1: + past continuous, present perfect, will, 1st conditional · B2: full arsenal)
- Language: student-friendly English on the front; UZ bridge uses formal "Siz"
- Cards stay accessible throughout the session — student can check them anytime
- Visuals must be concept-related, not decoration. Aim for every card to have `media`; skip only when a visual would be misleading. Each visual must connect directly to the word/formula.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
[
  { "term": "string", "def": "string", "cluster": "QOIDA|MISOL|TAHLIL|METOD", "hint": "optional mnemonic string", "media": { "type": "svg", "html": "<svg viewBox='0 0 200 150' xmlns='http://www.w3.org/2000/svg'>...</svg>" } }
]
```
