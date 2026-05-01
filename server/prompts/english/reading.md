# Prompt: Reading / Story Mode — English (Phase 2, HARD only)

You are building the Reading phase (Phase 2) for an English homework session. The reading is **derived from the textbook unit's own reading section** — not authored from scratch. The runtime presents the passage as an interleaved sequence of **text segments** and **comprehension checkpoints**: the student reads segment 1, answers checkpoint 1, reads segment 2, answers checkpoint 2, and so on. Each checkpoint tests the segment that immediately precedes it.

## Source rule (read first)

**Every English textbook unit at this level has a built-in reading section.** Use it. Do NOT author a fresh passage when the textbook already has one. Do NOT translate or paraphrase the textbook passage — extract it.

**Allowed adjustments:**
- Light trim for length when the textbook passage exceeds the level's word-count target (drop tangential sentences, keep the spine).
- Light cleanup of typography (smart-quote normalization, em-dash spacing, paragraph break tightening).
- Rewrite checkpoint questions to match the trimmed text — if you cut a paragraph the textbook's own question referenced, the question goes too.

**NOT allowed:**
- Inventing a passage when the textbook has one.
- "Improving" the textbook's wording or facts.
- Changing character names, settings, or plot details to fit a cultural-balance preference.

**Fallback** (rare): if the unit truly has no reading section, then author one — same word counts as the table below, same Problem → Struggle → Discovery → Solution beats baked invisibly. Cultural balance (55/45) applies only to authored fallbacks; textbook passages keep their original setting.

## Input

- Textbook unit (image or text) — including its reading section, which is your source material
- Preview + Flash Cards + Sprint outputs (from previous steps)
- Detected CEFR level (from `classify.md`): A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- Grade (for cultural setting on authored fallbacks only)

## Output

Title + context picture (SVG) + N segments interleaved with N checkpoints. Word count, segment count, checkpoint count by CEFR level:

| Level | Total word count | Segments | Checkpoints |
|:-:|:-:|:-:|:-:|
| A1 | 100-200 | 3 | 3 |
| A1+ | 150-250 | 3 | 3 |
| A2 | 200-350 | 3 | 3 |
| A2+ | 280-420 | 3 | 3 |
| B1 | 380-550 | 3 | 3 |
| B1+ | 450-650 | 4 | 4 |
| B2 | 550-900 | 4-5 | 4-5 |

The segment count always equals the checkpoint count. Total panels rendered at runtime = 2 × segment count (each segment followed by its checkpoint).

**Tenses allowed by level:**
- **A1:** present simple + can + have got
- **A2:** + past simple regular, going-to, have to
- **B1:** + past continuous, present perfect, will, 1st conditional, modals
- **B2:** full arsenal

---

## Context Picture (required)

Every reading MUST include a `media` field with an SVG illustration of the passage's main scene or topic. This is the context picture — it sets the visual scene for the student before or alongside reading.

**What the context picture must show:**
- The passage's main character, setting, or central object — as it appears in the narrative
- For example: a photographer holding a camera in front of a magazine cover; a student at a Tashkent IT Park entrance; a receptionist at a hotel lobby desk

**Honest visual rules:**
- The SVG must illustrate the actual passage scene, not generic clipart or decorative stock imagery
- The SVG must NOT be decorative, generic, stock-like, or out-of-topic media
- If the passage is about Daniel the photographer, the SVG shows Daniel (or a figure representing him) with a camera and a magazine
- If the passage is about a receptionist at Hilton Tashkent, the SVG shows a hotel lobby or front desk
- The visual anchors the student in the story world — it is not an ornament

**Size:** inline SVG, maximum 400×280px (the reading box is larger than flash card boxes — use the space). Legible on mobile. Simple line art is fine.

**Placement in the schema:** `media` is a top-level field in the reading output JSON, alongside `text` and `checkpoints`.

---

## Segmentation rule

The passage is split into N segments where N equals the checkpoint count for the level. Each segment ends at a **meaningful boundary** — a paragraph break, a scene shift, the end of an idea — never at a geometric midpoint. The next checkpoint tests the segment that just ended.

**How to choose segment boundaries when extracting from the textbook:**
- If the textbook reading is already in 3-4 paragraphs, those are usually your segments. One paragraph = one segment.
- If the reading is one long block, find the 2-3 natural pause points (a topic shift, a character arriving, a result being revealed) and split there.
- A segment can hold multiple short paragraphs if they cover the same idea — but a checkpoint always lands at a real boundary, never mid-thought.

**Each segment carries its own checkpoint.** The checkpoint tests something the student has just read in that segment — not something from a future segment, not a question only answerable after the whole passage. Checkpoint 1 should be answerable from segment 1 alone.

**HTML inside segments:** Use `<p>` tags only when a segment naturally contains multiple paragraphs. Use `**word**` markdown for bolded vocabulary on first occurrence (the adapter converts to `<strong>`). No other HTML inside segments.

## Narrative principles (apply to authored-fallback passages only; textbook extractions keep their existing structure)

**Structure:** Problem → Struggle → Discovery → Solution. These beats are INVISIBLE INGREDIENTS — baked into the narrative. Do NOT label them. Do NOT write "Problem:" or "Segment 1:" anywhere. A reader should only notice the story, never the frame.

**Grammar delivery:** The chapter's target grammar appears in natural use, as a real speaker would use it. Never explain the grammar inside the narrative. Never make a character suddenly "announce" a rule.

**Vocabulary:** Target vocab items from this chapter (count from Flash Cards deck), bolded on first occurrence only. Do not gloss, define, or translate inline. The story context carries the meaning.

**Tenses:** Level-allowed set only. Never a banned tense — not even in dialogue.

**Setting (authored fallbacks only):** Uzbekistan context for at least 55% of stories. Preferred: Silk Road city, Chorsu bozor, Samarkand school, Tashkent IT Park, Fergana village, Zarafshon riverbank, modern mahalla.

**Stranger Test:** A newcomer to the topic must be able to follow the plot without any prior knowledge of the chapter. The story stands alone.

---

## Example segment (B1, ~120 words)

> Kamola **arrived** at the Hilton Tashkent lobby at 8:55, five minutes before her first shift as a junior receptionist. The marble floor **reflected** the morning light, and guests **were already** moving in every direction. Her supervisor, Mr. Yusupov, handed her a printed schedule. "You **have worked** here for three days now," he said. "Today you **handle** the 9 a.m. check-ins alone." Kamola took a breath. She **had practised** every phrase the night before. Now it was real.

Paired checkpoint testing this segment:

> **Q1.** What is Kamola about to do alone for the first time?
> [Bloom: L1 | PISA: L1]

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

Checkpoint 2 (inference) is the ideal spot for an inline sentence-structure SVG: split a single load-bearing sentence from the narrative into subject / verb / object branches so the student can literally see the grammar pattern they must infer.

---

## Rules

- **Source: textbook reading section**, extracted not invented. Light trim/cleanup OK; rewrite affected checkpoints. Author from scratch only as a documented fallback.
- N segments, N checkpoints, paired by index. Segment count per level table. Each segment ends at a meaningful boundary; each checkpoint tests the segment immediately preceding it.
- Zero segment labels — no "Segment 1:", no "Part 1:" headings inside the text.
- Vocab items bolded on first occurrence using `**word**` markdown, not glossed inline.
- Tenses: level-allowed set only. No exceptions.
- For authored fallbacks: grammar appears naturally — never as a named demonstration inside the story.
- 55/45 national-pride balance applies to **authored fallbacks only**. Textbook passages keep their original setting verbatim.
- Checkpoints tagged `[Bloom: LX | PISA: LX]`. Range: L1-L2 main idea, L2-L3 inference/purpose, L3-L4 language analysis, L4-L5 evaluation.
- Do NOT print a word count label in the output — just meet it.
- `media` is required — it must illustrate the passage's main scene or context. It must NOT be decorative, generic, stock-like, or out-of-topic media.
- **Visuals:** inline SVG only when it aids comprehension of THIS passage's load-bearing sentence — a sentence-diagram tree splitting subject / verb / object at one checkpoint, a timeline of events if the passage spans multiple time points. **No decorative, generic, stock-like, or out-of-topic media.** Under 300×200px for inline checkpoint SVGs. Priority SVG > Mermaid > ASCII.
  - BAD: a generic open-book SVG decorating the top of the reading passage.
  - GOOD: a sentence-tree SVG of the passage's most syntactically complex sentence, branches labeled with the parts of speech the checkpoint question targets.


---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema. The `segments` array length must equal the checkpoint count for the level, and every segment must carry its `checkpoint` object — they are paired structurally, not via separate parallel arrays.

```json
{
  "title": "string",
  "media": { "type": "svg", "html": "<svg viewBox='0 0 400 280' xmlns='http://www.w3.org/2000/svg'>...</svg>" },
  "segments": [
    {
      "text": "first segment text — may include <p> tags for multiple paragraphs and **bold** for target vocab",
      "checkpoint": {
        "q": "question testing what the student just read in this segment",
        "tags": "[Bloom: LX | PISA: LX]",
        "ans": ["accepted answer 1", "accepted answer 2"]
      }
    },
    {
      "text": "...",
      "checkpoint": { "q": "...", "tags": "...", "ans": ["..."] }
    }
  ]
}
```
