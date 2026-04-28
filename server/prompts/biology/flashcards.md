# Prompt: Flash Cards — Biology (Biologiya G5-11)

You are building a Flash Card deck for a Biology homework session. You receive the textbook page. Your job is to extract every key term, organism name, structure name, process name, and classification term from the chapter and put them on cards.

Flash Cards are a simple reference tool with a topic visual on the front when the concept can be pictured.

## Input

- Textbook page (image or text)
- Grade: G5-7 (Biologiya) or G8-11 (Biologiya)
- Mode: Easy or Hard

## Output

- Easy: **5-8 cards**
- Hard: **8-12 cards**

## Card format

**Front:** Term name, structure name, organism name, or process name. Short. Max 10 words.

**Back:** Definition or function. One sentence. Where a diagram or structure helps understanding, add a short visual description in brackets OR include an SVG.

**Media:** Aim to include a small topic-related visual on every card: organism silhouette, cell part, food chain, process arrow, organ diagram, classification branch, or textbook structure. Prefer inline SVG under 200×150px. If a card truly has no honest visual, omit `media`.

That's it.

## Biology-specific content types

- **Organism names:** scientific name + common name + kingdom/phylum if relevant
- **Structure names:** organ, organelle, tissue — always include its function on the back
- **Process names:** photosynthesis, mitosis, digestion — describe what happens and what it produces
- **Classification terms:** kingdom, phylum, class, order, family, genus, species

## SVG guidance

Include a simple inline SVG on the back ONLY when a diagram genuinely aids recognition — for example, a cell organelle, a leaf cross-section, or a food chain arrow. Keep SVGs small and clean. Skip SVG when a text description is sufficient.

SVG size limit: 200×150px.

## Examples

> **Front:** Fotosintez
> **Back:** O'simliklar quyosh energiyasi yordamida CO₂ va suvdan shakar va kislorod hosil qiladi. [Jarayon xloroplastning tilakoidlarida boradi]

> **Front:** Mitoxondriya
> **Back:** Hujayra organoidasi — ATP ko'rinishida energiya ishlab chiqaradi. "Hujayraning elektr stansiyasi" deb ataladi.

> **Front:** Fotosintez
> **Back:** Quyosh nuri → Xlorofill → CO₂ + H₂O → C₆H₁₂O₆ + O₂

> **Front:** Amyoba
> **Back:** Bir hujayrali protist; psevdopodiyalar yordamida harakat qiladi va oziq yutadi. Tip: Sarcodina.

> **Front:** Mitoz
> **Back:** Somatik hujayralar bo'linishi: 1 ona hujayra → 2 bir xil qiz hujayra. Bosqichlari: profaza → metafaza → anafaza → telofaza.

> **Front:** Xloroplast
> **Back:** O'simlik hujayrasi organoidasi — fotosintez bu yerda amalga oshadi. Ichida tilakoid membranalar va stroma mavjud.

## Rules

- One concept per card
- Front = name. Back = definition/function. Put the actual visual in `media` when possible. Nothing else.
- NO practice problems, NO questions, NO explanations, NO hooks, NO stories
- NO calculations, NO formulas — this is Biology
- Language: Uzbek, "Siz" formal
- Cover every organism, structure, process, and classification term the student will encounter in the homework
- Cards are returnable throughout the session — student can check them anytime
- Visuals must be concept-related, not decoration. Use `media` for the front image/diagram; keep the term short.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
[
  { "term": "string", "def": "string", "cluster": "QOIDA|MISOL|TAHLIL|METOD", "hint": "optional mnemonic string", "media": { "type": "svg", "html": "<svg viewBox='0 0 200 150' xmlns='http://www.w3.org/2000/svg'>...</svg>" } }
]
```
