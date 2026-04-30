# Prompt: Preview — English — Hard Mode

You are building the Preview phase for an English homework session in HARD mode. Used for units that introduce new grammar, production tasks, or multi-paragraph reading. You will receive a textbook unit. Your job is to create 8 teaching panels in student-friendly English that fully prepare the student to use this unit's language in real-world situations.

This is HARD mode — the student will face a Real-Life Challenge later where they must apply what you teach here. Panel 5 (Word→Structure Translation) is the critical bridge. If you don't teach them HOW to extract data from situations and convert it to the target form, the Real-Life phase becomes guesswork.

## Input

- Textbook unit (image or text)
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- Grade (for pro-roles in Panel 6 only)

## Output

8 panels in order. Student-facing English throughout. UZ bridge lines use formal "Siz" — never "sen".

Sentence count per panel by CEFR level: A1: 4-5 · A2: 6-7 · B1: 8-10 · B2: 10-12.

Word→Structure mini-cases (Panel 5): A1: 1 · A2: 2 · B1: 2-3 · B2: 3.

**Tenses allowed by level:**
- **A1:** present simple + can + have got
- **A2:** + past simple regular, going-to, have to
- **B1:** + past continuous, present perfect, will, 1st conditional, modals (should/might/could)
- **B2:** full arsenal — all tenses, inversion, cleft, participles, modal perfects

Never use a tense banned at the detected level — not even in examples.

---

## Panel 1: Summary

Reframe the unit as something useful the student can DO, not a definition to memorize.

- 2 big ideas in plain student-English. No restatement of the book title.
- Optional 1-line attributed quote (≤125 chars) — prefer Navoiy, Ibn Sino, Malala, Obama, Rowling.
- No jargon, no fragments.

## Panel 2: Better Explanation

The hidden rule or trick the textbook shows but never explains.

- One explicit mental model OR one algebraic grammar formula (e.g., `(Wh-) + did + subject + base verb + ?`)
- Mandatory UZ↔EN bridge: map the English structure to its Uzbek grammatical equivalent with a labelled side-by-side
- Show WHY the form exists — the logic behind it, not just the shape
- Stress + IPA for any 2+-syllable target word with non-initial stress or known UZ/RU mis-stress (B1+ only)

## Panel 3: Examples

3 examples lifted directly from the chapter with page refs.

- Bold the target form on every occurrence
- At least one example must demonstrate the Panel 2 rule in action
- Annotate any spelling trap, register note, or false friend inline
- Never invent sentences not in the source chapter

## Panel 4: Real-Life Research

How this concept lives in the world right now.

- Real 2020+ sources (BBC, Tashkent IT Park, NASA Artemis, Samarkand tourism board, UN updates)
- One explicit Uzbekistan parallel anchoring the global fact locally
- Concrete, dateable situations — no abstract "you'll need this later"

## Panel 5: Word → Structure Translation

THIS IS THE BRIDGE TO REAL-LIFE. Without this panel, Phase 4 becomes guesswork.

Teach the student HOW to:
1. **Read** a real-world English sentence and identify the grammar/vocab target
2. **Extract** the relevant pattern — what structure matters, what's noise
3. **Produce** their own version using the same pattern

Structure: mini-cases per level (count above), building in complexity.

Example pattern:
> "NASA announced that the Artemis crew **had completed** their training."
> Target: present perfect (has/have + V3). UZ: "bajargan edi" → EN past result.
> Extract: subject + has/have + V3. Produce: "Samarkand **has become** a UNESCO site."

- First case: obvious, one clear target
- Last case (B1+/B2): two possible patterns, student must choose the correct one
- Mandatory UZ↔EN bridge in each case

## Panel 6: Industry Application

Where professionals use this English daily. Pick 2-3 roles from the grade-appropriate set:

- **G5-6:** Chorsu bozor helper, school monitor, mahalla football captain, Samarkand kid-tourist guide
- **G7-8:** Tashkent IT intern, Hilton receptionist, BBC Tashkent reporter, airline ground staff
- **G9-10:** BBC stringer, UN interpreter trainee, Uzbekistan Airways customer-service lead, IELTS tutor
- **G11:** IELTS Task-2 essayist, TEDx Tashkent speaker, UCAS personal-statement writer, startup pitcher

For each role: concrete task + what goes wrong if the English is incorrect.

## Panel 7: Mental Model

One visual or analogy that compresses the entire lesson into one image.

- Examples: "did = time machine" · "present perfect = bridge from past to now" · "passive = spotlight on the action, not the actor" · "modal + base verb = a remote control for certainty"
- Must be memorable and strange enough to stick
- Apply the UZ↔EN bridge to the analogy itself

## Panel 8: Why This Matters

Two parts:
1. What BREAKS if you don't know this — mistimed verb, wrong register, failed interview, embarrassing false friend
2. What OPENS UP — you pass DTM-level questions, speak with confidence, write competitive applications

End with BOST goal prompt: "Bugun [actual topic name] haqida nimani bilmoqchisiz?" — this is the line Reflection's BOST Check-In will echo back.

---

## Rules

- Language: student-friendly English. UZ bridge lines use formal "Siz" only, never "sen".
- Avg sentence length by level: A1 ≤9 words · A2 9-12 · B1 12-16 · B2 18-25.
- Tenses: level-allowed set only. Never a banned tense — not even in examples.
- UZ↔EN bridge MANDATORY on Panels 2, 5, 7 at minimum. A1 levels: every panel.
- Stress + IPA: mandatory B1+ for any 2+-syllable word with non-initial stress or known UZ/RU mis-stress.
- 55/45 Uzbekistan/global balance. Modern 2020+ contexts only. No cowboy/cricket/baseball clichés.
- Every panel: bold target form on actual chapter examples. Never invent.
- Each panel closes with `[Bloom: LX | PISA: LX]` tag.
- **Visuals:** inline SVG when a visual genuinely teaches the panel's point — timeline bridges for tense contrast, stress-dot patterns for pronunciation traps, IPA charts for sound distinctions, sentence-diagram trees for grammar structure, word-family trees, collocation grids, Buzan mind maps. The visual must depict the specific concept the panel is teaching. **No decorative, generic, stock-like, or out-of-topic media.** Under 300×200px. Priority SVG > Mermaid > ASCII. Place SVG immediately after the text it illustrates.
  - BAD: a generic schoolroom SVG dropped into a Word→Structure panel about past simple.
  - GOOD: a timeline SVG with a single tick on the past axis labeled "yesterday" and an arrow to "She went" beneath it, paired to the past-simple panel.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
{
  "quotes": ["string", "string"],
  "panels": [
    {
      "id": 1,
      "title": "string",
      "pages": [
        {
          "blocks": [
            { "type": "p|h2|quote|ul|ol", "text": "string (optional)", "items": ["string (optional)"] }
          ]
        }
      ]
    }
  ]
}
```
