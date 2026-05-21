# Uzbek Linguist Review Gate

Flow v2 adds Case-Based Preview and Memory Check prompts that can produce
student-facing Uzbek. These prompts must not ship Uzbek output rules or Uzbek
student copy without native Uzbek review.

This gate exists because the Flow Debate audit caught a fabricated grammar rule:
`verb-final: subordinate clauses end with -b/-ib/-gan/-adigan`. That rule is
not a safe rule to put in prompts. Wrong language rules are worse than no rule.

## Scope

Review is required for any v2 prompt PR that changes Uzbek-facing behavior in:

- `server/prompts/<subject>/case-based-preview.md`
- `server/prompts/<subject>/memory-check.md`
- shared v2 prompt instructions that mention Uzbek grammar, register, word
  order, morphology, or translation policy

This gate covers 7 subject batches:

- biology
- english
- geometriya-g7-11
- history
- kimyo-g7-11
- math-algebra
- physics

## Owner And SLA

- Linguist owner: TBD
- Candidate owner: Toriqli or external native Uzbek consultant
- SLA: 1 week per subject batch after the PR review file is opened
- Backup rule: if no linguist is available, ship English/Russian v2 first and
  keep Uzbek marked as blocked until signoff

## Rejection Criteria

A prompt batch is rejected if any reviewed sample or instruction contains:

- grammar error that would sound wrong to a native Uzbek student
- register slip, especially mixing formal `Siz` with informal `sen`
- Russian calque or Russian-style syntax where natural Uzbek wording is needed
- unexplained technical term that a student cannot reasonably infer
- fabricated Uzbek grammar rule or over-specific rule not confirmed by the
  linguist
- inconsistent Latin-script Uzbek spelling policy inside the same batch
- unnatural literal translation from English prompt wording

## Required Review File

Every v2 Uzbek prompt PR must add one file under this directory:

```text
docs/linguist-reviews/PR<number>-<feature>.md
```

Use `TEMPLATE.md` for new reviews. The file is the source of truth for:

- who reviewed
- which subject prompts were reviewed
- what was rejected
- what changed after feedback
- final signoff date

## Shipping Policy

- English/Russian v2 prompts may ship day-one.
- Uzbek v2 prompt behavior lands only after this review file is signed off.
- If a PR contains Uzbek prompt behavior but has no signed review file, keep the
  Uzbek part draft/disabled and document the blocker in the PR.

