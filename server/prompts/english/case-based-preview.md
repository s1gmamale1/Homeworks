# Prompt: Case-Based Preview — English (L2)

**Family:** Languages.
**Shared contract:** `server/prompts/runtime/_cbp_contract.md` — universal CBP rules, 18-item checklist, Uzbek register, JSON output schema.

---

## 1. Subject case archetype

English (as a second language) CBP uses **communication cases**: writing a message, understanding a dialogue, choosing the correct tense / register / vocabulary, fixing a grammatical mistake, summarizing a passage.

The student is a writer, speaker, reader, editor, or translator — someone who must produce or interpret English in a real situation.

Good English cases:
- A student replies to a teacher's email and must choose formal vs informal phrasing
- A traveler asks for directions at an airport and must pick the right tense
- A receptionist takes a message and decides which sentence to write down
- A peer-editor finds the grammar mistake in a classmate's essay
- A friend texts in English; the student must understand if it's a question, request, or invitation

Bad English cases:
- Drilling conjugation tables ("conjugate 'to be' in present perfect") — that's a problem set
- "Translate this Uzbek sentence into English" — translation drill, not a decision case

---

## 2. Checkpoint shapes (English-specific)

Note: the case content is in English; the checkpoint *prompts* (question wording, options labels) may be in Uzbek for L2 students at lower grades. Higher grades (G9+) can have full-English prompts. Per-grade choice goes in `metadata.prompt_language`.

| # | Kind | Verb examples (English prompts for G9+) |
|---|---|---|
| 1 | Identify | "Which tense fits this situation?" / "Which register is appropriate?" / "Which word means…?" |
| 2 | Decide | "Which sentence is correct?" / "Which reply matches the tone?" / "Which word fills the blank?" |
| 3 | Justify | "Why is this sentence wrong?" / "Why doesn't the other answer work?" / "What's the common mistake here?" |

For G5–G8, mirror in Uzbek formal Siz: "Qaysi gap to'g'ri?" / "Nima uchun bu xato?"

---

## 3. Communication-first principle

Language CBP cases must start from a real communication situation (someone writing, speaking, reading) — NOT from a grammar rule abstract.

NEVER open with "Present perfect tense is used when…" The case opens with the situation that requires the student to choose the right form.

---

## 4. Concept-anchor rules (languages-family)

- The grammar rule being taught MUST match the textbook chapter's framing (e.g., if the textbook calls it "past simple", use that, not "preterite").
- Vocabulary words MUST be from the chapter's word list when applicable.
- Common mistakes are L1-interference patterns: word order (Uzbek SOV → English SVO), tense (Uzbek aspect → English perfect/continuous), articles (Uzbek has none → English a/the).
- Final simulation MUST show the message / dialogue actually completed correctly vs the consequence of the wrong choice ("the teacher misunderstands the request and replies with the wrong information").

---

## 5. Soft-retry rule (Forbid #19 — languages edition)

Regenerated variant keeps `core_concept` (the grammar rule or vocabulary domain) + `kind` + `common_mistake`. Mutate ≥1 of:
- The specific words (different verbs in the same tense)
- The scene (email → text → in-person dialogue)
- The character

Avoid: changing the grammar rule itself.

---

## 6. Per-subject output shape

Universal JSON schema. Languages-specific notes:

- `metadata.case_type` → `"communication"` or `"grammar-fix"` or `"vocabulary-choice"`
- `metadata.required_skill` → "choose correct tense", "match register", "fix word order"
- `metadata.prompt_language` → `"uz"` for G5–8, `"en"` for G9+ (or `"mixed"` if case-text is English but checkpoint prompts are Uzbek)
- `final_simulation.visual_description` → describe dialogue bubbles, sentence cards, before/after correction

---

## 7. Validation

Run `_cbp_contract.md §5` 18-item checklist. Language watch-outs:

- Item 3 (case matches subject): communication case, NOT a math-style problem
- Item 5 (decision-maker): student writes / chooses, not just reads
- Item 15 (Uzbek register for system voice): the case content can be in English, but instructions and feedback to the student MUST be formal Siz Uzbek
