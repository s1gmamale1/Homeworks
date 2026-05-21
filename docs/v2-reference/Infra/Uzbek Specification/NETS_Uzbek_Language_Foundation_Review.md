# NETS Uzbek Language Foundation Review

## Status

**Ready for boss review.**

This document summarizes the work completed on Uzbek language quality, simplified Uzbek, and subject-specific language guardrails for future NETS homework generation.

It is designed so a reviewer does not need to open every ZIP or read every intermediate file first.

---

# 1. Executive Summary

We identified that Uzbek language issues in generated homework were not isolated grammar mistakes. They were symptoms of a deeper system problem:

```text
Homework was being generated first, then language problems were discovered and patched later.
```

The correct direction is:

```text
Define language fundamentals first → generate homework through those fundamentals → validate before saving.
```

The core decision:

```text
Uzbek correctness must be a generation contract, not an after-generation cleanup task.
```

The v1.2.1 foundation docs are now ready to be reviewed as the proposed source-of-truth for future implementation planning.

---

# 2. Root Context

NETS Homework is being redesigned around the new flow:

```text
Learning Sections → Unlock Gate → Practice Arc → Boss Arena → Reflection
```

This means Uzbek quality must support the whole learning journey, not just individual text blocks.

The Uzbek language layer must work across:

```text
Case-Based Preview
Flashcard Learning
Memory Check
Unlock Gate
Practice Arc
Boss Arena
Reflection
Runtime feedback
Frontend UI
Backend fallback text
Prompt examples
```

The goal is not to replace textbooks. The goal is to transform difficult textbook material into a guided, understandable, student-friendly homework journey while preserving subject accuracy.

---

# 3. What “Simplified Uzbek” Means

## Definition

**Simplified Uzbek** means accurate, formal, natural, student-friendly Uzbek that makes textbook material easier to understand while preserving subject meaning.

## It is NOT

Simplified Uzbek is not:

```text
childish Uzbek
slang Uzbek
casual sen/san register
removing important subject terms
making every sentence tiny
changing formulas, dates, facts, answer logic, SVG, IDs, URLs, or grading fields
oversimplifying until accuracy is damaged
```

## It SHOULD

Simplified Uzbek should:

```text
split long sentences at logical points
reduce heavy textbook wording
avoid Russian/English calques
keep formal Siz register
explain difficult terms with simple glosses
preserve subject accuracy first
keep important terminology
avoid robotic sentence chopping
```

Example:

```text
Too heavy:
Mazkur jarayon muhim ahamiyat kasb etadi.

Better:
Bu jarayon muhim.
```

But simplification must never remove necessary subject meaning.

---

# 4. Evidence Collected

We tested the approach with real homework clones before writing the foundation docs.

## 4.1 Biology Grade 7 Test

- Original: `HW-20260505-004`
- Clone: `HW-20260511-001`
- Subject: Biology
- Fields patched: 25
- Result: Passed after v2 correction
- Main lesson: Biology simplification can improve clarity, but must not narrow organism-wide concepts into human-only examples.

## 4.2 Math Grade 6 Test

- Original: `HW-20260504-004`
- Clone: `HW-20260511-002`
- Subject: Math Algebra
- Fields patched: 23
- Result: Passed after v2 runtime fix
- Main lesson: Math simplification is safe only when formulas, numbers, units, dimensions, answer keys, rendering structure, and Bloom/PISA tags are protected.

## 4.3 Biology Grade 8 Test

- Original: `HW-20260504-005`
- Clone: `HW-20260512-002`
- Subject: Biology
- Fields patched: 20
- Result: Passed after one register fix
- Main lesson: Higher-grade biology needs mechanism-preservation rules. Terms like `ATP`, `mitoz`, `modda almashinuvi`, `sintez`, `nafas olish`, and `hujayra` should be preserved and explained, not removed.

---

# 5. What The Tests Proved

The three clone tests proved:

```text
1. Simplified Uzbek can improve homework clarity.
2. AI self-scoring is not reliable enough.
3. Independent review is needed.
4. Runtime checks are necessary.
5. Subject-specific guardrails are required.
6. Clone-only testing prevents accidental production damage.
7. A global rule should not be accepted from one homework sample.
```

The safest workflow is:

```text
Claude proposal
→ Kimi independent review
→ v2 correction
→ runtime/safety check
→ patch clone only
→ mechanical verification
→ human comparison
→ only then system rule
```

---

# 6. Key Risks Discovered

## 6.1 Biology Risk

Biology simplification can damage meaning if broad concepts become human-only.

Risky direction:

```text
Energy comes from the food we eat.
```

Better direction:

```text
Energiya oziq moddalarning hujayrada parchalanishidan olinadi.
```

## 6.2 Math Risk

Math simplification can break hidden logic if it touches:

```text
formulas
numbers
units
dimensions
answer keys
Bloom/PISA tags
rendering structure
```

## 6.3 Runtime/UI Risk

Some text changes look fine in Markdown but fail in the app.

Example discovered:

```text
\n line breaks collapse inside normal panel <p> blocks.
```

Fix:

```text
Use <br/> where visible panel line breaks are required.
```

## 6.4 Register Risk

Formal Uzbek must remain consistent.

Avoid:

```text
sen/san
mixed Siz + informal verbs
casual -yapti / -iyapti forms in formal generated homework
inconsistent progressive forms in the same paragraph
```

---

# 7. Foundation Docs Created

The v1.2.1 package contains:

```text
docs/UZBEK_LANGUAGE_POLICY.md
docs/SIMPLIFIED_UZBEK_REQUIREMENTS.md
docs/UZBEK_QA_PIPELINE.md
docs/NETS_FORBIDDEN_RULES.md
docs/UZBEK_ROLLOUT_AND_TESTING_PLAN.md
docs/UZBEK_DOCS_INDEX.md
docs/FOUNDATION_DOCS_CHANGELOG.md
docs/subjects/BIOLOGY_UZ_POLICY.md
docs/subjects/MATH_UZ_POLICY.md
docs/subjects/GEOMETRY_UZ_POLICY.md
docs/subjects/CHEMISTRY_UZ_POLICY.md
docs/subjects/PHYSICS_UZ_POLICY.md
docs/subjects/HISTORY_UZ_POLICY.md
docs/subjects/ENGLISH_L2_POLICY.md
```

v1.2.1 fixed the last known blocker in the apostrophe policy.

---

# 8. Current Status of v1.2.1 Docs

## Passed

```text
Folder structure: PASS
Exact issue-analysis template: PASS
NETS Flow v2 mapping: PASS
Evidence wording: PASS
Subject confidence levels: PASS
Rollout modes: PASS
Apostrophe temporary policy: PASS
```

## Current Recommendation

```text
Use v1.2.1 as the root-level Uzbek foundation source-of-truth for implementation planning.
```

Important: this does **not** mean immediate production rollout.

It means the documentation is ready to guide:

```text
prompt updates
QA tests
validator design
generation pipeline changes
future homework generation rules
```

---

# 9. Main Policy Decisions Proposed

## 9.1 Uzbek Correctness

Generated homework should use:

```text
formal Siz
natural Uzbek
student-friendly wording
consistent register
subject-accurate explanations
```

## 9.2 Simplified Uzbek

Simplification must:

```text
make text easier
preserve subject meaning
keep key terms
add simple glosses
protect formulas/dates/facts
avoid casual or childish style
```

## 9.3 Apostrophes

No global apostrophe decision is made yet.

Temporary rule:

```text
Do not globally normalize apostrophes yet.
But one generated homework must not mix apostrophe styles inside the same content_json.
QA should warn on mixed styles.
```

## 9.4 Subject Confidence Levels

Subject policies are not equally proven.

Current confidence levels:

```text
Biology: Level A — clone-tested and verified
Math: Level A — clone-tested and verified
Geometry: Level B — diagnostic-only evidence
History: Level B — diagnostic-only evidence
Physics: Level B — diagnostic-only evidence
English L2: Level B — diagnostic-only evidence
Chemistry: Level C — forward-looking policy, no corpus evidence yet
```

---

# 10. Subject Guardrails

## Biology

Protect:

```text
organism-wide meaning
mechanism terms
process accuracy
ATP / mitoz / fotosintez / nafas olish / sintez / parchalanish
```

Do not simplify biology into only human examples unless the topic is specifically human biology.

## Math

Protect:

```text
numbers
variables
formulas
units
dimensions
answer logic
calculation order
```

Simplify the wording around the math, not the math itself.

## Geometry

Protect:

```text
LaTeX
diagram labels
theorem wording
proof logic
symbols
SVG/media
```

## Chemistry

Protect:

```text
substances
reaction meaning
hazard/safety meaning
units
lab steps
process order
```

## Physics

Protect:

```text
units
formulas
symbols
measurements
cause-effect logic
technical notation
```

## History

Protect:

```text
chronology
names
places
titles
cause-effect chains
source meaning
historical sequence
```

## English L2

English-learning content is a special case.

Do not treat English words as Uzbek code-switching errors when they are part of language learning.

---

# 11. Forbidden Rules

The docs propose forbidding:

```text
passive reading blobs
fake games
MCQ spam
Boss as quiz skin
flashcard recall counted as conceptual mastery
exact-question retake farming
casino-style XP/reward patterns
forced Uzbek context
textbook replacement behavior
Buzan name-dropping without real memory methods
simplified Uzbek that damages accuracy
```

These rules matter because the root system is a guided learning journey, not a decorated worksheet.

---

# 12. QA Pipeline Proposed

Future generation should follow this pipeline:

```text
1. Generate subject content.
2. Apply subject-specific guardrails.
3. Apply simplified Uzbek pass.
4. Validate safe fields were not touched.
5. Run Uzbek QA checks.
6. Run subject QA checks.
7. Save only if safe.
```

Initial implementation should be staged:

```text
Phase 1: docs + tests + warnings
Phase 2: safe mechanical checks
Phase 3: clone-only auto patch
Phase 4: save-blocking validation
```

This avoids overblocking before validators mature.

---

# 13. Required Issue-Analysis Method

All future issues should use this template.

```md
# Issue: [Name]

## 1. What is the issue?
- Location:
- Affects:
- Student result:
- Teacher/product result:

## 2. How is it happening?
- Current mechanic:
- Current prompt behavior:
- Current flow behavior:
- Missing requirement:

## 3. Why was it used originally?
- Original purpose:
- What it solved:
- What is still valuable:
- What no longer works:

## 4. Issue type and severity
- Type:
- Severity:
- Evidence level:

## 5. Solution options
### Option A
- Pros:
- Cons:

### Option B
- Pros:
- Cons:

### Option C
- Pros:
- Cons:

## 6. Recommended solution
- Why this solution:
- Better than alternatives because:
- Existing pieces we can reuse:
- Real-life reference/pattern:

## 7. Implementation concept
- How it should work:
- Where it belongs:
- What needs to change:
- What stays:

## 8. Risks
- Possible downside:
- How to reduce it:

## 9. Success criteria
- We know it worked when:
```

This prevents vague fixes and forces evidence-based decisions.

---

# 14. What Boss Should Review

Please review these decision areas:

## 14.1 Definition

Is this definition acceptable?

```text
Simplified Uzbek = accurate, formal, natural, student-friendly Uzbek that makes textbook material easier to understand while preserving subject meaning.
```

## 14.2 Scope

Should this apply to:

```text
all generated homework
runtime feedback
Boss
Reflection
frontend UI
backend fallback strings
prompt examples
```

or should any layer be excluded?

## 14.3 Apostrophe Temporary Policy

Should we accept the temporary rule?

```text
No global normalization yet, but one generated homework must not mix apostrophe styles.
```

## 14.4 Subject Confidence Levels

Are these confidence levels acceptable?

```text
Biology and Math = Level A
Geometry, History, Physics, English L2 = Level B
Chemistry = Level C
```

## 14.5 Rollout Strategy

Do we agree with:

```text
docs → tests/warnings → mechanical checks → clone-only auto patch → save-blocking validation
```

instead of immediate blocking?

## 14.6 Forbidden Rules

Are any forbidden categories missing?

Current list includes:

```text
passive reading blobs
fake games
MCQ spam
Boss as quiz skin
exact-question retake farming
casino-style XP
textbook replacement behavior
simplification that damages accuracy
```

---

# 15. Recommended Next Steps

If the boss accepts v1.2.1 foundation docs:

## Step 1 — Merge docs into repo

Add the docs package to the repo as source-of-truth.

## Step 2 — Create implementation issue plan

Turn docs into technical implementation tasks:

```text
prompt changes
QA validator
tests
safe-field detector
subject guardrails
generation pipeline updates
```

## Step 3 — Add tests first

Before changing generation behavior, add tests/warnings for:

```text
sen/san
mixed register
-yapti in formal generated homework
mixed apostrophe styles within one homework
long sentence warnings
unexplained difficult terms
unsafe changes to formulas/IDs/SVG/answer keys
```

## Step 4 — Update prompts

Apply the docs to generation prompts.

## Step 5 — Run controlled generation tests

Generate new homeworks under the new rules and compare against old outputs.

## Step 6 — Only then consider save-blocking validation

Do not start with hard blocking until warning data is collected.

---

# 16. Final Recommendation

The current v1.2.1 foundation docs should be considered:

```text
Ready for boss review.
Ready to guide implementation planning.
Not yet automatic production behavior.
```

The work is moving in the correct direction because it prevents future generated homeworks from repeating the same Uzbek language problems, instead of fixing them manually after generation.

---

# 17. Feedback Requested

Please provide feedback on:

```text
1. Is the simplified Uzbek definition correct?
2. Are the subject guardrails strong enough?
3. Should the temporary apostrophe policy be accepted?
4. Should the rollout stay staged instead of immediate blocking?
5. Are any forbidden rules missing?
6. Can v1.2.1 become the source-of-truth for implementation planning?
7. What changes are required before merging docs into the repo?
```
