# Prompt: Reading / Story Mode — English (Phase 2, HARD only)

You are building the Reading phase (Phase 2) for an English homework session. This is ONE continuous narrative. The student reads it. The grammar and vocabulary arrive through story — never through labels.

## Input

- Textbook unit (image or text)
- Preview + Flash Cards + Sprint outputs (from previous steps)
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- Grade (for cultural setting, 55/45 UZ/global balance)

## Output

ONE continuous narrative + checkpoints. Word count and checkpoint count by CEFR level:

| Level | Word count | Paragraphs | Checkpoints |
|:-:|:-:|:-:|:-:|
| A1 | 100-200 | 1 | 3 |
| A1+ | 150-250 | 1-2 | 3 |
| A2 | 200-350 | 2 | 3 |
| A2+ | 280-420 | 2-3 | 3 |
| B1 | 380-550 | 3 | 3 |
| B1+ | 450-650 | 3 | 4 |
| B2 | 550-900 | 3-4 | 4-5 |

**Tenses allowed by level:**
- **A1:** present simple + can + have got
- **A2:** + past simple regular, going-to, have to
- **B1:** + past continuous, present perfect, will, 1st conditional, modals
- **B2:** full arsenal

---

## Narrative Construction

**Structure:** Problem → Struggle → Discovery → Solution. These beats are INVISIBLE INGREDIENTS — baked into the narrative. Do NOT label them. Do NOT write "Problem:" or "Segment 1:" anywhere. A reader should only notice the story, never the frame.

**Grammar delivery:** The chapter's target grammar appears in natural use, as a real speaker would use it. Never explain the grammar inside the narrative. Never make a character suddenly "announce" a rule.

**Vocabulary:** Target vocab items from this chapter (count from Flash Cards deck), bolded on first occurrence only. Do not gloss, define, or translate inline. The story context carries the meaning.

**Tenses:** Level-allowed set only. Never a banned tense — not even in dialogue.

**Setting:** Uzbekistan context for at least 55% of stories. Preferred: Silk Road city, Chorsu bozor, Samarkand school, Tashkent IT Park, Fergana village, Zarafshon riverbank, modern mahalla.

**Stranger Test:** A newcomer to the topic must be able to follow the plot without any prior knowledge of the chapter. The story stands alone.

---

## Example opening paragraph (B1, ~80 words)

> Kamola **arrived** at the Hilton Tashkent lobby at 8:55, five minutes before her first shift as a junior receptionist. The marble floor **reflected** the morning light, and guests **were already** moving in every direction. Her supervisor, Mr. Yusupov, handed her a printed schedule. "You **have worked** here for three days now," he said. "Today you **handle** the 9 a.m. check-ins alone." Kamola took a breath. She **had practised** every phrase the night before. Now it was real.

---

## Checkpoint Questions

Count per level table. Cover:
1. Main idea (what the narrative is about)
2. Inference (what the text implies but doesn't state)
3. Purpose (why a character did something OR why a particular form was used)
4. (B1+/B2 only) Language analysis — identify and explain a grammar or vocabulary choice
5. (B2 only) Evaluation — assess the writer's approach or a character's decision

Format:
> **Q1.** What is the main challenge [character] faces in this story?
> [Bloom: L1-L2 | PISA: L1-L2]

---

## Rules

- ONE narrative only. Not multiple stories, not segmented passages.
- Zero segment labels — beats are invisible.
- Vocab items bolded on first occurrence, not glossed.
- Tenses: level-allowed set only. No exceptions.
- Grammar appears naturally — never as a named demonstration inside the story.
- 55/45 national-pride balance. Modern 2020+ contexts for global settings.
- No bazaar/shopkeeper/farmer clichés in pro-role settings.
- Checkpoints tagged `[Bloom: LX | PISA: LX]`. Range: L1-L2 main idea, L2-L3 inference/purpose, L3-L4 language analysis, L4-L5 evaluation.
- Do NOT print a word count label in the output — just meet it.
- **Visuals:** inline SVG only when it aids comprehension of THIS narrative's load-bearing sentence — a sentence-diagram tree splitting subject / verb / object at Checkpoint 2, a timeline of events if the narrative spans multiple time points. **No decorative, generic, stock-like, or out-of-topic media.** Under 300×200px. Priority SVG > Mermaid > ASCII.
  - BAD: a generic open-book SVG decorating the top of the reading passage.
  - GOOD: a sentence-tree SVG of the narrative's most syntactically complex sentence, branches labeled with the parts of speech the checkpoint question targets.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
{
  "text": "string",
  "checkpoints": [
    {
      "q": "string",
      "tags": "[Bloom: LX | PISA: LX]",
      "ans": ["string"]
    }
  ]
}
```
