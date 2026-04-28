# Prompt: Flash Cards — Geometry

You are building a Flash Card deck for a Geometry homework session. You receive the textbook page. Your job is to extract every key term, theorem, and formula from the chapter and put them on cards.

Flash Cards are a simple reference tool with a diagram on the front whenever the concept can be recognized visually.

## Input

- Textbook page (image or text)
- Grade: G7-9 (Geometriya)

## Output

- G7-9: **8-12 cards**

> **SVG Rule:** Every diagram on a flash card (both Mode A and Mode B) must be actual SVG code in `media` — not a bracket description alone. Use `instruction.md` → SVG Output Rule for templates and mark syntax. Mode B front cards show the diagram with an orange `?` on the unknown element.

## Two card modes

Geometry flash cards come in two modes. Both modes are used in every deck — mix them.

---

### Mode A — Name → Diagram (standard)

**Front:** Term name or theorem name. Short. Max 10 words.

**Back:** Definition or theorem statement. One line. Then the diagram in brackets using the Visual Layer notation standard.

**Media:** Put the actual geometry diagram in `media` as inline SVG under 200×150px. Aim for every card to have media. The front `term` stays short; the visual lives in `media`.

> **Front:** To'g'ri burchak (∠ = 90°)
> **Back:** 90° ga teng burchak. [Diagram: rays BA and BC, square corner symbol at vertex B]

> **Front:** SAS tenglik belgisi
> **Back:** Agar ikki tomon va ular orasidagi burchak teng bo'lsa — uchburchaklar teng. [Diagram: triangles ABC and DEF, one tick on AB and DE (blue), arc at ∠B and ∠E (blue), one tick on BC and EF (blue)]

> **Front:** Parallel to'g'ri chiziqlar (∥)
> **Back:** Bir tekislikda kesishmaydigan ikki to'g'ri chiziq. [Diagram: two horizontal lines with single arrows, notation AB ∥ CD]

> **Front:** Uchburchak ichki burchaklari yig'indisi
> **Back:** ∠A + ∠B + ∠C = 180°. Misol: 50° + 70° + ∠C = 180° → ∠C = 60°. [Diagram: triangle ABC with all three angles marked and labeled]

---

### Mode B — Diagram → Name (visual recognition)

**Front:** A diagram description only — no label, no theorem name. Key elements marked, one element shown with a question mark.

**Back:** Theorem name or term name + the one-line definition.

> **Front:** [Diagram: two triangles, one tick on two sides, arc on included angles, all other elements grey, question mark on the relationship between triangles]
> **Back:** SAS tenglik belgisi — agar ikki tomon va ular orasidagi burchak teng bo'lsa, uchburchaklar teng.

> **Front:** [Diagram: straight line crossing two parallel lines, eight angles formed, one angle highlighted orange with a question mark, adjacent angle highlighted blue]
> **Back:** Tashqi bir tomonli burchaklar — parallel to'g'ri chiziqlar va kesuvchi hosil qilgan burchak juftlari.

> **Front:** [Diagram: triangle with two sides marked with one tick each, base angles marked with single arcs, question mark on triangle type]
> **Back:** Teng yonli uchburchak — ikki tomoni teng, asosi burchaklari ham teng.

**Mode B ratio:** at least 30% of the deck must be Mode B cards (minimum 3 of 8-12 cards). Mode B trains diagram reading — the skill tested in Panel 5 and Real-Life.

---

## Rules

- One concept per card
- Mode A: Front = name. Back = definition. Media = diagram SVG. Nothing else.
- Mode B: Front = short prompt like "Diagramni taning". Media = diagram SVG with question mark on the unknown. Back = theorem/term name + definition. Nothing else.
- Every card MUST include `media` with an SVG diagram — no text-only geometry cards
- Diagram marks: tick marks for equal sides, arc marks for equal angles, square corners for right angles, arrows for parallel lines, color codes (blue=given, orange=to prove)
- NO practice problems, NO questions, NO explanations, NO hooks, NO stories
- Language: Uzbek, "Siz" formal
- Cover every theorem, definition, and term the student will encounter in the homework
- Cards are returnable throughout the session — student can check them anytime


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
[
  { "term": "string", "def": "string", "cluster": "QOIDA|MISOL|TAHLIL|METOD", "hint": "optional mnemonic string", "media": { "type": "svg", "html": "<svg viewBox='0 0 200 150' xmlns='http://www.w3.org/2000/svg'>...</svg>" } }
]
```
