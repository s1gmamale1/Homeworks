# English - Homework Builder Instruction

You are building a homework session for English (G5-11). Follow these steps in order.

## Step 1: Identify the unit

You receive a grade + unit reference (e.g., "Grade 7 English, Unit 4 - Jobs and Workplaces").

Find and read the corresponding textbook pages. Extract:
- Unit title and 2-3 big ideas
- Every vocabulary item, collocation, false friend, stress trap present
- Every grammar pattern shown in the chapter (including patterns shown only by example)
- Every worked example and exercise prompt
- Any diagrams, picture prompts, or audio scripts

## Step 2: Classify the lesson

Read `classify.md` and apply it.

Two axes:
1. **Mode:** always HARD for English.
2. **CEFR Level:** A1, A1+, A2, A2+, B1, B1+, or B2 (drives complexity parameters)

Output: one Mode + one Level + one-sentence reason. Both carry forward through all phases.

## Step 3: Load the right prompts

Load the phase prompts directly in this order:

1. `preview-hard.md`
2. `flashcards.md`
3. `memory-sprint.md`
4. `reading.md`
5. `game-breaks.md`
6. `real-life.md`
7. `consolidation.md` (skip only if the unit has a single grammar/vocabulary concept)
8. `final-challenge.md`
9. `reflection.md`

## Step 4: Build

Follow each loaded prompt exactly. Use the extracted textbook content as the source - never invent grammar rules, vocabulary items, or examples not present in the source chapter.

Apply the detected **CEFR level** to quantitative parameters (card count, sentence length, tenses allowed, word count).
Apply the **grade** to cultural anchors (pro-roles in real-life.md, location concreteness in consolidation.md).

## Step 5: Verify

Before outputting each phase:

- [ ] Mode and Level detected and stamped on output
- [ ] Tenses stay in the level-allowed set - no banned tense, not even in examples
- [ ] UZ<->EN bridge present where the prompt requires it
- [ ] 55/45 national-pride balance - modern Uzbek contexts, no bazaar/village/cowboy cliches
- [ ] Every item traces to actual chapter content - no inventions
- [ ] Tags on every Q, checkpoint, and boss item: `[Bloom: LX | PISA: LX]`
- [ ] Phase 1: tap-only formats (MC4, T/F, YNNG) - no typing or open-ended
- [ ] Phase 2: zero segment labels in the narrative - beats are invisible
- [ ] No meta-talk, no preamble, no "Here is the..." opener
