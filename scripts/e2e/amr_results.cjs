// Verify the AMR results screen end-to-end.
//   1. Backend returns axis_1 / axis_2 for semantic+amr requests.
//   2. Sentence Fill skips remaining hint levels on first-try correct.
//   3. window.__sessionLog accumulates per-phase entries.
//   4. showResultsScreen() renders per-phase tally + AMR axis cards.
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1280, height: 1000 },
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(60000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));

  // ── 1. Backend AMR axes via direct fetch ──────────────────────────
  console.log('\n=== Backend AMR axes ===');
  const apiResult = await page.evaluate(async () => {
    const resp = await fetch('/api/ai/check-answer', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: 'wc-test', question: 'Yoylar bir-biridan ___.',
        student_answer: 'ayirmasining', expected_answers: ['ayirmasining'],
        answer_spec: { type: 'semantic', expected: 'ayirmasining',
                       canonical_display: 'ayirmasining', allow_ai_fallback: true, amr: true },
        subject: 'geometriya-g7-11', grade: 8, phase: 'sentence-fill',
      }),
    });
    return await resp.json();
  });
  console.log('  correct:', apiResult.correct, 'source:', apiResult.source);
  console.log('  axis_1:', apiResult.axis_1, 'label:', apiResult.axis_1_label);
  console.log('  axis_2:', apiResult.axis_2, 'label:', apiResult.axis_2_label);

  // ── 2. SF first-try advance + log ─────────────────────────────────
  console.log('\n=== SF first-try advance + session log ===');
  const sfBehavior = await page.evaluate(async () => {
    if (!window.__sessionLog) window.__sessionLog = [];
    window.__sessionLog.length = 0;  // clear
    if (typeof gbInitWC !== 'function') return { ok: false, err: 'gbInitWC missing' };
    gbInitWC();
    // Pretend first-try correct on chain 1
    if (!gbState || !gbState.wc) return { ok: false, err: 'gbState.wc missing' };
    const ta = document.getElementById('gb-wc-textarea');
    if (ta) ta.value = 'ayirmasining';
    const beforeIdx = gbState.wc.chainIdx;
    const beforeLevel = gbState.wc.levelIdx;
    await gbWCAction();
    // gbWCShowInvariant should have been called → invariant box visible.
    const inv = document.getElementById('gb-wc-invariant');
    const invShown = inv && inv.classList.contains('show');
    return {
      ok: true,
      beforeIdx, beforeLevel,
      invShown,
      sessionLogSize: window.__sessionLog.length,
      lastLog: window.__sessionLog[window.__sessionLog.length - 1] || null,
    };
  });
  console.log(' ', sfBehavior);

  // ── 3. Seed a synthetic session log + render the results screen ────
  console.log('\n=== Results screen render with synthetic log ===');
  const resultsRender = await page.evaluate(async () => {
    if (typeof showResultsScreen !== 'function') return { ok: false, err: 'showResultsScreen missing' };
    // Synthetic log: a mix of closed (no axes) + AI-graded (with axes)
    window.__sessionLog = [
      { phase: 'memory-sprint', id: 'ms-1', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-2', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-3', correct: false, score: 0 },
      { phase: 'memory-sprint', id: 'ms-4', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-5', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-6', correct: true,  score: 1 },
      { phase: 'memory-sprint', id: 'ms-7', correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A1',   tier:'easy',   correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A3',   tier:'medium', correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A5',   tier:'hard',   correct: false, score: 0 },
      { phase: 'adaptive-quiz', id: 'A4',   tier:'medium', correct: true,  score: 1 },
      { phase: 'adaptive-quiz', id: 'A2',   tier:'easy',   correct: true,  score: 1 },
      { phase: 'tile-match',    id: 'tm-all', correct: true, score: 1 },
      { phase: 'sentence-fill', id: 'wc-1', correct: true,  score: 1, axis_1: 4, axis_2: 4, first_try: true },
      { phase: 'sentence-fill', id: 'wc-2', correct: true,  score: 1, axis_1: 3, axis_2: 4, first_try: true },
      { phase: 'sentence-fill', id: 'wc-3', correct: false, score: 0, axis_1: 2, axis_2: 2, first_try: false },
      { phase: 'sentence-fill', id: 'wc-4', correct: true,  score: 1, axis_1: 4, axis_2: 3, first_try: false },
      { phase: 'sentence-fill', id: 'wc-5', correct: true,  score: 1, axis_1: 3, axis_2: 3, first_try: true },
      { phase: 'real-life',     id: 'Q1',   correct: true,  score: 1, axis_1: 4, axis_2: 4 },
      { phase: 'real-life',     id: 'Q2',   correct: true,  score: 1, axis_1: 4, axis_2: 4 },
      { phase: 'real-life',     id: 'Q3',   correct: true,  score: 1, axis_1: 4, axis_2: 4 },
      { phase: 'real-life',     id: 'Q4',   correct: false, score: 0, axis_1: 3, axis_2: 2 },
      { phase: 'real-life',     id: 'Q5',   correct: true,  score: 0.85, axis_1: 4, axis_2: 3 },
      { phase: 'final-boss',    id: 'Q1',   correct: true,  score: 1, axis_1: 4, axis_2: 4, damage: 10 },
      { phase: 'final-boss',    id: 'Q2',   correct: true,  score: 1, axis_1: 4, axis_2: 4, damage: 10 },
      { phase: 'final-boss',    id: 'Q3',   correct: true,  score: 1, axis_1: 3, axis_2: 4, damage: 20 },
      { phase: 'final-boss',    id: 'Q4',   correct: true,  score: 1, axis_1: 3, axis_2: 3, damage: 20 },
      { phase: 'final-boss',    id: 'Q5',   correct: false, score: 0.4, axis_1: 2, axis_2: 2, damage: 0 },
    ];
    showResultsScreen();
    await new Promise(r => setTimeout(r, 300));
    const visible = document.getElementById('screen-results').classList.contains('active');
    const headline = document.getElementById('results-headline').textContent;
    const band     = document.getElementById('results-band').textContent;
    const phaseRows = document.querySelectorAll('.results-phase-row');
    const amrAxes  = document.querySelectorAll('.results-amr-axis');
    const masteryNote = document.getElementById('results-mastery').textContent.slice(0, 100);
    return {
      ok: true, visible,
      headline: headline.replace(/\s+/g, ' ').trim(),
      band,
      phaseCount: phaseRows.length,
      phases: Array.from(phaseRows).map(r => r.textContent.replace(/\s+/g,' ').trim()),
      axisCount: amrAxes.length,
      axes: Array.from(amrAxes).map(a => a.textContent.replace(/\s+/g,' ').trim()),
      masteryNote,
      aggregate: window.__sessionAggregate || null,
    };
  });
  console.log(' visible           :', resultsRender.visible);
  console.log(' band              :', resultsRender.band);
  console.log(' headline          :', resultsRender.headline);
  console.log(' phase rows        :', resultsRender.phaseCount);
  resultsRender.phases.forEach(p => console.log('   ', p));
  console.log(' AMR axis cards    :', resultsRender.axisCount);
  resultsRender.axes.forEach(a => console.log('   ', a));
  console.log(' mastery note head :', resultsRender.masteryNote);
  if (resultsRender.aggregate) {
    console.log(' aggregate:');
    console.log('   overall_score :', resultsRender.aggregate.overall_score?.toFixed(1));
    console.log('   axis_1 mean   :', resultsRender.aggregate.overall_axis_1?.toFixed(2));
    console.log('   axis_2 mean   :', resultsRender.aggregate.overall_axis_2?.toFixed(2));
    console.log('   total correct :', resultsRender.aggregate.totalCorrect, '/', resultsRender.aggregate.totalItems);
    console.log('   band          :', resultsRender.aggregate.overall_band?.name);
  }

  // Verdicts
  const verdict = {
    backend_axes_returned: typeof apiResult.axis_1 === 'number' && typeof apiResult.axis_2 === 'number',
    backend_axis_labels:   typeof apiResult.axis_1_label === 'string',
    sf_first_try_advances: sfBehavior.invShown === true,
    sf_log_written:        sfBehavior.sessionLogSize > 0,
    sf_log_has_axes:       sfBehavior.lastLog && typeof sfBehavior.lastLog.axis_1 === 'number',
    results_screen_active: resultsRender.visible === true,
    results_band_set:      /(Mastered|Proficient|Apprentice|Novice)/i.test(resultsRender.band || ''),
    results_phase_rows_6:  resultsRender.phaseCount === 6,
    results_amr_2_axes:    resultsRender.axisCount === 2,
    results_aggregate:     resultsRender.aggregate && typeof resultsRender.aggregate.overall_axis_1 === 'number',
  };
  console.log('\n=== Verdicts ===');
  console.log(JSON.stringify(verdict, null, 2));
  const allPass = Object.values(verdict).every(Boolean);
  console.log('\n=== ' + (allPass ? 'ALL PASS ✓' : 'FAILURES ✗') + ' ===');

  await browser.close();
  process.exit(allPass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
