# Answer Spec Schema

The `answer_spec` field structures the expected answers for deterministic grading and AI fallback.

## Schema
```json
{
  "answer_spec": {
    "type": "numeric | set_match | text_exact | text_fuzzy | semantic",
    "expected": "ANY",
    "tolerance": 0, // only for numeric
    "canonical_display": "String", // teacher's model answer
    "allow_ai_fallback": true,
    "rubric": {
      "correct": "String",
      "partial": "String",
      "incorrect": "String"
    }
  }
}
```

## Types

### Numeric
Used for float/int answers.
```json
{
  "type": "numeric",
  "expected": 9.81,
  "tolerance": 0.05,
  "canonical_display": "9.81",
  "allow_ai_fallback": false,
  "rubric": {
    "correct": "Exact match within tolerance.",
    "partial": "Off by power of 10 or sign error.",
    "incorrect": "Wrong value."
  }
}
```

### Set Match
Used for mathematical sets or multiple roots.
```json
{
  "type": "set_match",
  "expected": [-9, 9],
  "canonical_display": "x₁,₂ = ±9",
  "allow_ai_fallback": true,
  "rubric": {
    "correct": "Both roots given (or equivalent ±form).",
    "partial": "Only one root given, or method correct but answer incomplete.",
    "incorrect": "Wrong roots."
  }
}
```

### Text Exact
Used when capitalization/spacing can be ignored but words must match perfectly.
```json
{
  "type": "text_exact",
  "expected": "Toshkent",
  "canonical_display": "Toshkent",
  "allow_ai_fallback": false,
  "rubric": {
    "correct": "Exact string match (ignoring case/whitespace/punctuation).",
    "partial": "N/A",
    "incorrect": "Incorrect string."
  }
}
```

### Text Fuzzy
Used when spelling variations or typos are expected.
```json
{
  "type": "text_fuzzy",
  "expected": "mitoxondriya",
  "canonical_display": "Mitoxondriya",
  "allow_ai_fallback": true,
  "rubric": {
    "correct": "Matches within >=90% RapidFuzz ratio.",
    "partial": "Matches within >=75% ratio.",
    "incorrect": "Low similarity."
  }
}
```

### Semantic
Used for long-form free text where AI is required.
```json
{
  "type": "semantic",
  "expected": "Because the magnetic field lines form closed loops.",
  "canonical_display": "Magnit maydon chiziqlari yopiq halqalarni tashkil etgani uchun.",
  "allow_ai_fallback": true,
  "rubric": {
    "correct": "Understands that magnetic monopoles don't exist / field lines are closed.",
    "partial": "Mentions field lines but not closed loops.",
    "incorrect": "Unrelated or factually wrong."
  }
}
```
