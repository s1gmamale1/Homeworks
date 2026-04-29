// Headless simulation for the redesigned AMR results screen.
//   Adapted from the upstream amr_results.cjs. Targets the local
//   builder at 127.0.0.1:8000 and HW-20260429-001 (the homework we
//   transferred over). Verifies:
//     1. Backend /api/ai/check-answer returns axis_1/axis_2 for semantic+amr.
//     2. window.__sessionLog can be seeded.
//     3. showResultsScreen() activates the new statistical scorecard
//        (donut gauge + per-phase bars + 2 AMR axis bars + tinted tip).
//
// Run:
//   NODE_PATH="C:/Users/Agent/AppData/Local/Temp/node_modules" \
//     node D:/Homeworks/scripts/e2e/amr_results.cjs

const puppeteer = require('puppeteer');
const HW_ID = process.env.HW_ID  || 'HW-20260429-001';
const BASE  = process.env.BASE   || 'http://127.0.0.1:8000';
const URL_  = `${BASE}/h/${HW_ID}`;

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1280, height: 1000 },
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(60000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));

  console.log('Load', URL_);
  await page.goto(URL_, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));

  // ── 1. Backend AMR axes via direct fetch ──────────────────────────
  // Per GRADING.md, the 2-axis rubric is for Phase 4 Real-Life and Phase 6
  // Final Boss. We exercise both ends of the axis range:
  //   (a) bare correct number "13" → must be A1=1, A2=1, item ≈ 25%
  //   (b) full Pifagor walkthrough  → must be A1=4, A2=4, item ≈ 100%
  // The strict prompt rewrite is what enforces this.
  const RL_PROMPT = "Sevara is laying a 12 m × 5 m garden bed and wants a "
                  + "diagonal walking path corner-to-corner. How long is the "
                  + "path? Show your reasoning.";
  const FULL_RESP = "Bu to'g'ri to'rtburchak, demak diagonal Pifagor "
                  + "teoremasi bilan topiladi (chunki uchburchak to'g'ri "
                  + "burchakli). d² = 12² + 5² = 144 + 25 = 169. "
                  + "d = √169 = 13 m.";

  async function gradeAmr(student, label) {
    return await page.evaluate(async ({ s, p }) => {
      const resp = await fetch('/api/ai/check-answer', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: 'amr-' + Date.now(),
          question: p,
          student_answer: s,
          expected_answers: ['13'],
          answer_spec: { type: 'semantic', expected: '13',
                         canonical_display: '13 m',
                         allow_ai_fallback: true, amr: true },
          subject: 'geometriya-g7-11', grade: 8, phase: 'real-life',
        }),
      });
      return await resp.json();
    }, { s: student, p: RL_PROMPT });
  }

  console.log('\n=== Backend AMR axes — bare result "13" (expect A1=1, A2=1) ===');
  const bare = await gradeAmr('13', 'bare');
  console.log('  axis_1 :', bare.axis_1, 'label:', bare.axis_1_label);
  console.log('  axis_2 :', bare.axis_2, 'label:', bare.axis_2_label);
  console.log('  reason1:', (bare.axis_1_reason || '').slice(0, 110));
  console.log('  reason2:', (bare.axis_2_reason || '').slice(0, 110));

  console.log('\n=== Backend AMR axes — full Pifagor walkthrough (expect A1=4, A2=4) ===');
  const full = await gradeAmr(FULL_RESP, 'full');
  console.log('  axis_1 :', full.axis_1, 'label:', full.axis_1_label);
  console.log('  axis_2 :', full.axis_2, 'label:', full.axis_2_label);
  console.log('  reason1:', (full.axis_1_reason || '').slice(0, 110));
  console.log('  reason2:', (full.axis_2_reason || '').slice(0, 110));

  // Use the upper-bound result for the legacy `apiResult` shape so the
  // existing aggregate-render checks still see numeric axes.
  const apiResult = full;

  // ── 2. Seed a synthetic session log + render the redesigned screen ─
  console.log('\n=== Results screen render with synthetic log ===');
  const r = await page.evaluate(async () => {
    if (typeof showResultsScreen !== 'function') return { ok: false, err: 'showResultsScreen missing' };
    window.__sessionLog = [
      { phase: 'memory-sprint', id: 'ms-1', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-2', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-3', correct: false, score: 0 },
      { phase: 'memory-sprint', id: 'ms-4', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-5', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-6', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-7', correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A1', tier:'easy',   correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A3', tier:'medium', correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A5', tier:'hard',   correct: false, score: 0 },
      { phase: 'adaptive-quiz', id: 'A4', tier:'medium', correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A2', tier:'easy',   correct: true,  score: 1 },
      { phase: 'tile-match',    id: 'tm-all', correct: true, score: 1 },
      { phase: 'sentence-fill', id: 'wc-1', correct: true,  score: 1, axis_1: 4, axis_2: 4, first_try: true },
      { phase: 'sentence-fill', id: 'wc-2', correct: true,  score: 1, axis_1: 3, axis_2: 4, first_try: true },
      { phase: 'sentence-fill', id: 'wc-3', correct: false, score: 0, axis_1: 2, axis_2: 2, first_try: false },
      { phase: 'sentence-fill', id: 'wc-4', correct: true,  score: 1, axis_1: 4, axis_2: 3, first_try: false },
      { phase: 'sentence-fill', id: 'wc-5', correct: true,  score: 1, axis_1: 3, axis_2: 3, first_try: true },
      { phase: 'real-life',     id: 'Q1', correct: true,  score: 1,    axis_1: 4, axis_2: 4 },
      { phase: 'real-life',     id: 'Q2', correct: true,  score: 1,    axis_1: 4, axis_2: 4 },
      { phase: 'real-life',     id: 'Q3', correct: true,  score: 1,    axis_1: 4, axis_2: 4 },
      { phase: 'real-life',     id: 'Q4', correct: false, score: 0,    axis_1: 3, axis_2: 2 },
      { phase: 'real-life',     id: 'Q5', correct: true,  score: 0.85, axis_1: 4, axis_2: 3 },
      { phase: 'final-boss',    id: 'Q1', correct: true,  score: 1,    axis_1: 4, axis_2: 4, damage: 10 },
      { phase: 'final-boss',    id: 'Q2', correct: true,  score: 1,    axis_1: 4, axis_2: 4, damage: 10 },
      { phase: 'final-boss',    id: 'Q3', correct: true,  score: 1,    axis_1: 3, axis_2: 4, damage: 20 },
      { phase: 'final-boss',    id: 'Q4', correct: true,  score: 1,    axis_1: 3, axis_2: 3, damage: 20 },
      { phase: 'final-boss',    id: 'Q5', correct: false, score: 0.4,  axis_1: 2, axis_2: 2, damage: 0 },
    ];
    showResultsScreen();
    await new Promise(r => setTimeout(r, 400));

    const screen = document.getElementById('screen-results');
    const visible = screen && screen.classList.contains('active');
    const headlineEl = document.getElementById('results-headline');
    const bandEl = document.getElementById('results-band');

    // New (redesigned) DOM
    const gauge       = headlineEl && headlineEl.querySelector('.results-gauge');
    const gaugePct    = gauge && gauge.querySelector('.results-gauge-pct');
    const gaugeFill   = gauge && gauge.querySelector('.results-gauge-fill');
    const phaseRows   = document.querySelectorAll('.results-phase-row');
    const phaseFills  = document.querySelectorAll('.results-phase-bar-fill');
    const axisBlocks  = document.querySelectorAll('.results-axis');
    const axisMarkers = document.querySelectorAll('.results-axis-marker');
    const axisTags    = document.querySelectorAll('.results-axis-tag');
    const masteryEl   = document.getElementById('results-mastery');
    const actionBtn   = document.querySelector('#results-actions .results-action-btn');

    return {
      ok: true, visible,
      bandText: bandEl && bandEl.textContent,
      bandClass: bandEl && bandEl.className,
      gaugeFound: !!gauge,
      gaugePct: gaugePct && gaugePct.textContent,
      gaugeStroke: gaugeFill && gaugeFill.getAttribute('stroke'),
      phaseCount: phaseRows.length,
      phases: Array.from(phaseRows).map(r => r.textContent.replace(/\s+/g,' ').trim()),
      phaseFillClasses: Array.from(phaseFills).map(f => f.className.replace('results-phase-bar-fill', '').trim()),
      axisCount: axisBlocks.length,
      axisMarkerCount: axisMarkers.length,
      axisMarkerLefts: Array.from(axisMarkers).map(m => m.style.left),
      actionBtnText:  actionBtn && actionBtn.textContent.trim(),
      actionBtnClass: actionBtn && actionBtn.className,
      axisTags: Array.from(axisTags).map(t => t.textContent.trim()),
      masteryClass: masteryEl && masteryEl.className,
      masteryHead: masteryEl && masteryEl.textContent.slice(0, 90),
      aggregate: window.__sessionAggregate || null,
    };
  });

  console.log(' visible            :', r.visible);
  console.log(' band text/class    :', JSON.stringify(r.bandText), '|', r.bandClass);
  console.log(' gauge              :', r.gaugeFound, ' pct=', r.gaugePct, ' stroke=', r.gaugeStroke);
  console.log(' phase rows         :', r.phaseCount, '· phase bar fills:', r.phaseFillClasses.length);
  r.phases.forEach(p => console.log('   ·', p));
  console.log(' phase fill classes :', r.phaseFillClasses.join(', '));
  console.log(' AMR axis blocks    :', r.axisCount);
  console.log(' AMR markers        :', r.axisMarkerCount, ' positions:', r.axisMarkerLefts.join(', '));
  console.log(' AMR tags           :', r.axisTags.join(' | '));
  console.log(' mastery class      :', r.masteryClass);
  console.log(' mastery head       :', r.masteryHead);
  console.log(' action button      :', JSON.stringify(r.actionBtnText), '|', r.actionBtnClass);
  if (r.aggregate) {
    console.log(' aggregate:');
    console.log('   overall_score :', r.aggregate.overall_score && r.aggregate.overall_score.toFixed(1));
    console.log('   axis_1 mean   :', r.aggregate.overall_axis_1 && r.aggregate.overall_axis_1.toFixed(2));
    console.log('   axis_2 mean   :', r.aggregate.overall_axis_2 && r.aggregate.overall_axis_2.toFixed(2));
    console.log('   total correct :', r.aggregate.totalCorrect, '/', r.aggregate.totalItems);
    console.log('   band          :', r.aggregate.overall_band && r.aggregate.overall_band.name);
  }

  // ── 3. Re-render with a deliberately LOW score and confirm the button flips
  //      to "Qayta bajarish" with the redo class. The threshold is 60%.
  console.log('\n=== Low-score re-render — expect Qayta bajarish ===');
  const low = await page.evaluate(async () => {
    window.__sessionLog = [
      { phase: 'memory-sprint', id: 'ms-1', correct: false, score: 0 },
      { phase: 'memory-sprint', id: 'ms-2', correct: false, score: 0 },
      { phase: 'memory-sprint', id: 'ms-3', correct: false, score: 0 },
      { phase: 'memory-sprint', id: 'ms-4', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-5', correct: false, score: 0 },
      { phase: 'memory-sprint', id: 'ms-6', correct: false, score: 0 },
      { phase: 'memory-sprint', id: 'ms-7', correct: false, score: 0 },
      { phase: 'sentence-fill', id: 'wc-1', correct: false, score: 0, axis_1: 1, axis_2: 1 },
      { phase: 'sentence-fill', id: 'wc-2', correct: false, score: 0, axis_1: 2, axis_2: 1 },
      { phase: 'real-life',     id: 'Q1',   correct: false, score: 0, axis_1: 1, axis_2: 2 },
      { phase: 'final-boss',    id: 'B1',   correct: false, score: 0, axis_1: 1, axis_2: 1, damage: 0 },
    ];
    showResultsScreen();
    await new Promise(r => setTimeout(r, 200));
    const ab = document.querySelector('#results-actions .results-action-btn');
    return {
      pct: (document.querySelector('.results-gauge-pct') || {}).textContent,
      btnText: ab && ab.textContent.trim(),
      btnClass: ab && ab.className,
    };
  });
  console.log(' low gauge pct      :', low.pct);
  console.log(' low action button  :', JSON.stringify(low.btnText), '|', low.btnClass);

  const verdict = {
    backend_axes_returned : typeof apiResult.axis_1 === 'number' && typeof apiResult.axis_2 === 'number',
    backend_axis_labels   : typeof apiResult.axis_1_label === 'string',
    results_screen_active : r.visible === true,
    band_label_set        : /(Mastered|Proficient|Apprentice|Novice)/i.test(r.bandText || ''),
    band_perf_class       : /\bperf-(good|mid|bad)\b/.test(r.bandClass || ''),
    donut_gauge_rendered  : r.gaugeFound && /%/.test(r.gaugePct || ''),
    phase_rows_present    : r.phaseCount >= 5,
    phase_fills_colored   : r.phaseFillClasses.length > 0 && r.phaseFillClasses.every(c => /perf-(good|mid|bad|neutral)/.test(c)),
    amr_two_axes          : r.axisCount === 2,
    amr_markers_two       : r.axisMarkerCount === 2,
    amr_tags_two          : r.axisTags.length === 2,
    mastery_perf_class    : /\bperf-(good|mid|bad)\b/.test(r.masteryClass || ''),
    aggregate_has_axes    : r.aggregate && typeof r.aggregate.overall_axis_1 === 'number',
    high_score_button     : r.actionBtnText === 'Tugatish' && /is-finish/.test(r.actionBtnClass || ''),
    low_score_button      : low.btnText === 'Qayta bajarish' && /is-redo/.test(low.btnClass || ''),

    // GRADING.md strictness: bare number "13" must NOT score above the
    // Apprentice band on either axis. Anchor: A1=1, A2≤2, item ≤ 50%.
    bare_axis_1_floored   : typeof bare.axis_1 === 'number' && bare.axis_1 === 1,
    bare_axis_2_low       : typeof bare.axis_2 === 'number' && bare.axis_2 <= 2,

    // Full Pifagor walkthrough must score Mastered or Proficient on both
    // axes. Anchor: A1≥3, A2≥3, item ≥ 75%.
    full_axis_1_high      : typeof full.axis_1 === 'number' && full.axis_1 >= 3,
    full_axis_2_high      : typeof full.axis_2 === 'number' && full.axis_2 >= 3,
  };
  console.log('\n=== Verdicts ===');
  console.log(JSON.stringify(verdict, null, 2));
  const allPass = Object.values(verdict).every(Boolean);
  console.log('\n=== ' + (allPass ? 'ALL PASS' : 'SOME FAILED') + ' ===');

  await browser.close();
  process.exit(allPass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
