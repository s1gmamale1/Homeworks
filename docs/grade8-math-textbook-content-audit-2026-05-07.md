# Grade 8 Math Demo Textbook Content Audit — 2026-05-07

Scope:
- Algebra demo: `HW-20260505-006` — `Nisbiy xatolik`, Grade 8.
- Geometry demo: `HW-20260505-005` — `To'ldiruvchi burchakning trigonometrik funksiyalari uchun formulalar`, Grade 8.
- Sources:
  - `C:/Users/TEXNO/Downloads/8-sinf_Algebra_2019_(elekton_darslikbot).pdf`
  - `C:/Users/TEXNO/Downloads/8-sinf_Geometriya_2019_(elekton_darslikbot).pdf`

## Textbook Anchors

### Algebra — Nisbiy xatolik

Textbook location:
- Algebra PDF pages 119–121.
- Section: `21- §. NISBIY XATOLIK`.

Core textbook ideas:
- Absolute error alone is not enough when comparing different-sized measurements.
- Relative error = absolute error divided by the approximate value modulus.
- Relative error is usually expressed as percent.
- Main examples:
  - Toshkent–Samarqand distance `(300 ± 1) km` vs pencil length `(21.3 ± 0.1) cm`.
  - Earth mass `(5.98 ± 0.01) · 10^24 kg` vs bullet mass `(9 ± 1) g`.
  - Exercises include rounding, comparing measurement quality, and reverse-finding absolute error from relative error.

Current homework alignment:
- `HW-20260505-006` is mostly textbook-aligned.
- Panels already use the Toshkent–Samarqand vs pencil comparison.
- Formula `|x − a| / |a| · 100%` is aligned with the textbook definition.

Problems to fix before demo:
- All 10 algebra flashcards are text-only; this looks unfinished compared with geometry.
- Flashcard 9, `Bobil ildizi`, feels off-topic for §21 and should be replaced.
- The deck should show the measurement-comparison logic visually, not only as text.

Recommended algebra flashcard/media replacements:
- Add number-line SVG: exact value `x`, approximate value `a`, distance `|x − a|`.
- Add fraction SVG: `nisbiy xatolik = absolut xatolik / taqribiy qiymat`.
- Add percent conversion SVG: `δ × 100%`.
- Add comparison SVG: `300 km ± 1 km` vs `21.3 cm ± 0.1 cm`.
- Replace `Bobil ildizi` with `Aniqlik chegarasi: x = a ± h` or `Qaysi o'lchov aniqroq?`.
- Keep the Earth/bullet example, but make it a visual comparison card.

### Geometry — Complementary-Angle Trig Formulas

Textbook location:
- Geometry PDF page 52.
- Section: `22. TO'LDIRUVCHI BURCHAKNING TRIGONOMETRIK FUNKSIYALARI UCHUN FORMULALAR`.
- Exercises continue on page 53.

Core textbook ideas:
- Complementary angles have sum `90°`.
- In a right triangle, the two acute angles are complementary.
- Main formulas:
  - `sin(90° − α) = cos α`
  - `cos(90° − α) = sin α`
  - `tg(90° − α) = ctg α`
  - `ctg(90° − α) = tg α`
- Textbook proof uses one right triangle and side ratios.
- Exercise style asks students to convert `sin x = cos 40°`, `cos x = sin 76°`, `tg x = ctg 56°`, etc.

Current homework alignment:
- `HW-20260505-005` is strongly textbook-aligned.
- It includes the exact four formulas and a right-triangle derivation.
- Flashcards 1–7 and 9 already have SVG media.

Problems to fix before demo:
- 2 of 10 geometry flashcards still have no media:
  - `Asosiy ayniyat (eslatma)`
  - `Co-funksiya almashinuvi (mnemonik)`
- The section number in metadata says `22-§`, which is correct.
- AQ and Puzzle Lock are now hidden for Grade 8 math demo after PR #173, so demo flow is safer.

Recommended geometry flashcard/media replacements:
- Add right-triangle SVG for the two missing cards.
- For `Asosiy ayniyat`, show the same triangle with `sin²α + cos²α = 1`.
- For `Co-funksiya almashinuvi`, show a clean swap diagram:
  - `sin ↔ cos`
  - `tg ↔ ctg`
  - label: `90° − α`

## Demo Flow Recommendation

For Grade 8 math/geometriya demos:
- Keep writing short.
- Use flashcards, Tile Match, Memory Sprint, Real-life example, and Final Challenge.
- Keep Adaptive Quiz hidden for now because image capture/checking is not demo-ready.
- Keep Puzzle Lock hidden for now because its mechanic does not match the intended solve-in-order interaction.

## Gemini Usage Recommendation

Do not use Gemini as the primary textbook extractor for this task.

Better Gemini use:
- Give Gemini the cleaned section notes above.
- Ask it to act as a second reviewer:
  - Does each flashcard map to a textbook concept?
  - Are any demo cards off-topic?
  - Which SVG idea is easiest for an 8th-grade student to understand?
- Do not ask Gemini to rewrite repo files directly for this stage.

## Next Implementation Candidate

One focused PR:
- Branch suggestion: `codex/g8-math-textbook-demo-content-2026-05-07`.
- Update only the saved demo homework content or prompt fixtures used to regenerate it.
- Add SVG media for algebra flashcards.
- Add SVG media for the two missing geometry flashcards.
- Replace algebra `Bobil ildizi` card with a textbook-grounded card.
- Browser-smoke:
  - `http://127.0.0.1:8000/h/HW-20260505-006`
  - `http://127.0.0.1:8000/h/HW-20260505-005`

Stop before PR until the visual/content plan is approved.
