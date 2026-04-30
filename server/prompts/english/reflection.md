# Prompt: Reflection — English (final phase)

You are building the Reflection phase (final phase) for an English homework session. Quiet closing — no scoring, no pressure. Summarize what was learned, surface the weak spot, set up next review.

## Input

- All previous phase outputs
- Mode: always HARD per `classify.md`
- Detected CEFR level: A1 · A1+ · A2 · A2+ · B1 · B1+ · B2
- Grade (for UZ location references and calibration)

## Output

6 parts, ~2 minutes total. Micro-exercise count by CEFR level:

| Level | Micro-exercises |
|:-:|:-:|
| A1 / A1+ | 2-3 (tap-level, one-word answers) |
| A2 / A2+ | 3 (tap-level) |
| B1 / B1+ | 3-4 (sentence-level) |
| B2 | 4 (sentence-level) |

---

## 1. Today's Results (2-3 lines)

List the session's topics with status markers:
- ✅ Strong topic — student showed mastery in Game Breaks or Boss
- ⚠️ Weak topic — student needed hints or made errors in Boss

Example:
> ✅ Present perfect formula — demonstrated correctly in Boss Q2
> ⚠️ Time adverb placement (yet / already) — error in Boss Q3

## 2. Micro-exercises

Target the weak topics ONLY. Each has an answer.
- A1/A2: tap-level, max 1 sentence per exercise — not a second boss fight
- B1/B2: sentence-level short production, not analysis
- Use level-allowed tenses only

Example (B1 weak topic: time adverb placement):
> a. Put "already" in the correct place: "She has finished the report." → She has **already** finished the report.
> b. True or False: "I haven't eaten yet" means I am still hungry now. → True.
> c. Complete: "Have you ___ been to Registan?" (ever/already) → ever.

## 3. BOST Check-In

> "Today you learned [goal from Preview Panel 2's key rule] — can you name it in one line?"

Student responds freely. Not scored. Use the same goal/topic line Preview Panel 2's key rule established — do not invent a new one.

Example: "Today you learned that present perfect = a bridge from a past action to a present result — can you name it in one line?"

## 4. Metacognitive Prompts (pick 3, rotate across sessions)

- "What was the hardest moment in today's session, and why?"
- "If a friend asked you to explain [today's grammar] in 30 seconds, what would you say?"
- "Where in your week this week could you actually use this?"
- "What does [today's key vocab word] mean in your life right now — not in English class?"
- "What would you search for to find out more about this topic?"

## 5. Spaced Repetition Schedule

> "Review these items: tomorrow · day 3 · day 7 · day 21"

List 2-3 specific items from this session based on what appeared and what was weak.

Example:
> - Present perfect vs past simple contrast (appeared in Boss Q3)
> - Stress pattern: photographer /fəˈtɒɡrəfər/ (flashcard 1)
> - Time adverbs: yet / already / just / ever — placement rules (weak topic)

## 6. Closing Line

- Score ≥60%: "Your precision builds the Third Renaissance."
- Score <60%: "Every session makes the next one easier. See you tomorrow."

Never punitive. Never "you failed."

---

## Example: B1 reflection — past simple unit

> ✅ Past simple irregular verbs (go/went, see/saw, have/had) — Boss Q1 correct
> ⚠️ Did + base verb in questions — Boss Q2 error: "Did she went?" instead of "Did she go?"
>
> **Micro-exercises:**
> a. Fix: "Did she went to the IT Park?" → Did she **go** to the IT Park?
> b. True or False: "Did" already carries the past — so the main verb stays base form. → True.
> c. Write a question: ask about Kamola's job using did. → Did Kamola work at the Hilton last year?
>
> **BOST:** "Today you learned that did = the time machine — it carries all the past — can you name it in one line?"
>
> **Spaced repetition:** did + base verb rule · went/saw/had irregular trio · base verb after modal helpers

---

## Rules

- ~2 minutes, 6 parts
- Not scored — calm close
- Micro-exercises count per level table. Target weak topics only, not full review.
- Complexity matches level: A1/A2 tap or one-word; B1/B2 short sentences.
- BOST string echoes Preview Panel 2's key rule — not invented
- Language: student-facing English. UZ bridge allowed in metacognitive prompts.
- Closing line tied to score performance — never generic
- Summary must reference actual content from this session
- Use level-allowed tenses in micro-exercise model answers — never a banned tense
- Visuals: inline SVG only if it aids the micro-exercise (rare — mostly text). Under 200×150px.


---

## Schema mapping (6 parts → 4 keys)

The 6 body parts above collapse into 4 JSON fields. Compose them like this:

- **`summary`** ← Part 1 (Today's Results) + Part 2 (Micro-exercises). Join into a single multi-paragraph string. Use plain text with line breaks; results bullets first, then a "Micro-exercises:" subsection with each exercise + answer.
- **`question`** ← Part 3 (BOST Check-In) + ONE rotated prompt from Part 4 (Metacognitive). Join with a single line break — BOST line first, metacognitive prompt second.
- **`spaced_rep`** ← Part 5 (Spaced Repetition Schedule) verbatim, including the "tomorrow · day 3 · day 7 · day 21" header line and the 2-3 item bullets.
- **`closing`** ← Part 6 (Closing Line) verbatim — exactly one of the two score-tied lines.

Do not drop any of the 6 parts. If a part has no content for this session, write a one-line placeholder rather than empty string.

---

## OUTPUT REQUIREMENT
Return valid JSON matching this exact schema:
```json
{
  "summary": "string",
  "question": "string",
  "spaced_rep": "string",
  "closing": "string"
}
```
