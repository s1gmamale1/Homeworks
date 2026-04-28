// Watch a full student session in real time.
//
// Opens a visible Chromium window and walks every phase of HW-20260427-008
// at human speed so you can SEE the student's experience. Useful for spot-
// checking flows after a code change without manually clicking through.
//
// Usage:
//   node scripts/watch_simulation.cjs
//   PERSONA=strong   node scripts/watch_simulation.cjs   # ~95% correct
//   PERSONA=weak     node scripts/watch_simulation.cjs   # ~30% correct
//   PERSONA=mid      node scripts/watch_simulation.cjs   # ~70% correct (default)
//   SLOWMO=300       node scripts/watch_simulation.cjs   # ms between actions
//   PHASE=boss       node scripts/watch_simulation.cjs   # jump straight to a phase
//
// Pre-reqs:
//   - dev server on http://127.0.0.1:8000 with HW-20260427-008 populated
//   - puppeteer installed somewhere node can resolve
//     (export NODE_PATH=$(npm root -g))

const puppeteer = require('puppeteer');

const URL      = 'http://127.0.0.1:8000/h/HW-20260427-008';
const PERSONA  = (process.env.PERSONA || 'mid').toLowerCase();
const SLOWMO   = parseInt(process.env.SLOWMO || '120', 10);
const PHASE    = (process.env.PHASE || '').toLowerCase();  // '', 'preview', 'sprint', 'aq', 'sf', 'tm', 'rl', 'boss'

// Per-persona accuracy. Affects local-match items only — AI-graded items
// always go to the actual grader.
const ACCURACY = { strong: 0.95, mid: 0.70, weak: 0.30 }[PERSONA] || 0.70;

const log = (msg) => { console.log('  ' + msg); };
const banner = (msg) => console.log('\n── ' + msg + ' '.repeat(Math.max(0, 60 - msg.length - 4)) + '──');

function shouldSkipUntil(target) {
  if (!PHASE) return false;
  const order = ['preview', 'flashcards', 'sprint', 'aq', 'sf', 'tm', 'rl', 'consolidation', 'boss', 'results'];
  const cur = order.indexOf(target);
  const want = order.indexOf(PHASE);
  return cur < want;
}

(async () => {
  const browser = await puppeteer.launch({
    headless: false,           // ← visible browser window
    slowMo: SLOWMO,            // ← throttle every Puppeteer action
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--start-maximized'],
    defaultViewport: null,
  });
  const page = (await browser.pages())[0] || (await browser.newPage());
  page.setDefaultTimeout(60000);
  page.on('pageerror', e => console.log('  PAGEERR:', e.message));

  console.log('\n╔════════════════════════════════════════════════════════════╗');
  console.log('║  Watching student session · HW-20260427-008                ║');
  console.log('║  Persona: ' + PERSONA.padEnd(10) + ' (' + Math.round(ACCURACY * 100) + '% accuracy)' + ' '.repeat(28 - String(Math.round(ACCURACY * 100)).length) + '║');
  console.log('║  SlowMo : ' + SLOWMO + 'ms' + (PHASE ? '  ·  Phase: ' + PHASE : '') + ' '.repeat(40 - String(SLOWMO).length - (PHASE ? PHASE.length + 12 : 0)) + '║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log('\nLoading', URL, '...\n');

  await page.goto(URL, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => typeof MS_QUESTIONS !== 'undefined', { timeout: 10000 });
  await new Promise(r => setTimeout(r, 600));

  // ── Memory Sprint ──────────────────────────────────────────────────
  if (!shouldSkipUntil('sprint')) {
    banner('Phase 1 · Memory Sprint');
    await page.evaluate(async (acc) => {
      setStage(4);
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.getElementById('screen-ms').classList.add('active');
      msInit();
    }, ACCURACY);
    await new Promise(r => setTimeout(r, 500));

    for (let i = 0; i < 7; i++) {
      const result = await page.evaluate((idx, acc) => {
        const item = MS_QUESTIONS[idx];
        const wrongChoice = (item.correct + 1) % (item.options.length);
        const choice = (Math.random() < acc) ? item.correct : wrongChoice;
        msHandleAnswer(choice);
        return { picked: choice, correct: item.correct };
      }, i, ACCURACY);
      log(`Q${i + 1}: picked=${result.picked} correct=${result.correct} ${result.picked === result.correct ? 'OK' : 'wrong'}`);
      await new Promise(r => setTimeout(r, 700));
    }
  }

  // ── Adaptive Quiz ─────────────────────────────────────────────────
  if (!shouldSkipUntil('aq')) {
    banner('Phase 3a · Adaptive Quiz');
    await page.evaluate(async () => {
      setStage(5);
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.getElementById('screen-5').classList.add('active');
      gbInit();
      gbInitAQ();
    });
    await new Promise(r => setTimeout(r, 500));

    for (let r = 0; r < 5; r++) {
      const result = await page.evaluate((acc) => {
        const item = gbState.aq.currentItem;
        const accept = (item.acceptable && item.acceptable[0]) || item.answer || '';
        const useCorrect = Math.random() < acc;
        const ans = useCorrect ? accept : String((parseInt(accept, 10) || 0) + 13);
        gbAQCapture();
        const inp = document.getElementById('gb-aq-input');
        if (inp) inp.value = ans;
        gbAQAction();
        return { id: item.id, tier: item.tier, sent: ans, expect: accept, ok: useCorrect };
      }, ACCURACY);
      log(`R${r + 1}: id=${result.id} tier=${result.tier} sent="${result.sent}" expect="${result.expect}" ${result.ok ? 'OK' : 'wrong'}`);
      await new Promise(r2 => setTimeout(r2, 1100));
      await page.evaluate(() => gbAQAction());  // advance
      await new Promise(r2 => setTimeout(r2, 600));
    }
  }

  // ── Sentence Fill (AI-graded) ──────────────────────────────────────
  if (!shouldSkipUntil('sf')) {
    banner('Phase 3b · Sentence Fill (AI grading, 1-3s per item)');
    await page.evaluate(() => { gbState.subGame = 1; gbInitWC(); });
    await new Promise(r => setTimeout(r, 500));

    for (let c = 0; c < 5; c++) {
      const sent = await page.evaluate(async (idx, acc) => {
        gbState.wc.chainIdx = idx;
        gbState.wc.levelIdx = 0;
        gbState.wc.retries = 0;
        gbWCRenderChain();
        const inv = GB_WHY_CHAIN[idx].invariant || '';
        const useCorrect = Math.random() < acc;
        const ans = useCorrect ? inv : 'noaniq';
        const ta = document.getElementById('gb-wc-textarea');
        if (ta) ta.value = ans;
        await gbWCAction();
        return { expected: inv, sent: ans, useCorrect };
      }, c, ACCURACY);
      log(`C${c + 1}: expect="${sent.expected}" sent="${sent.sent}"`);
      await new Promise(r => setTimeout(r, 1500));
    }
  }

  // ── Tile Match ────────────────────────────────────────────────────
  if (!shouldSkipUntil('tm')) {
    banner('Phase 3c · Tile Match (matching all 6 pairs)');
    await page.evaluate(() => { gbState.subGame = 2; gbInitMM(); });
    await new Promise(r => setTimeout(r, 500));
    for (let p = 0; p < 6; p++) {
      await page.evaluate(async (pid) => {
        const lp = document.querySelector('.gb-tm-left-tile[data-pair="' + pid + '"]');
        if (lp) lp.click();
      }, p);
      await new Promise(r => setTimeout(r, 400));
      await page.evaluate(async (pid) => {
        const rp = document.querySelector('.gb-tm-right-tile[data-pair="' + pid + '"]');
        if (rp) rp.click();
      }, p);
      await new Promise(r => setTimeout(r, 400));
      log(`Pair ${p + 1}/6 matched`);
    }
    await new Promise(r => setTimeout(r, 800));
  }

  // ── Real-Life ─────────────────────────────────────────────────────
  if (!shouldSkipUntil('rl')) {
    banner('Phase 4 · Real-Life Challenge');
    await page.evaluate(() => { startStage6(); });
    await new Promise(r => setTimeout(r, 1500));
    // Click "Boshlash" to leave story → Q1
    await page.evaluate(() => document.getElementById('action-button').click());
    await new Promise(r => setTimeout(r, 1200));

    const expected = ['40', '50', '55', '40', "P binodan uzoqlashayotgan, chunki ko'rish burchagi qisqaradi va yoylar doimiy bo'lib qoladi."];
    for (let i = 0; i < 5; i++) {
      // Capture
      await page.evaluate((idx) => {
        const cap = document.getElementById('rl-q' + (idx + 1) + '-capture-btn');
        if (cap) cap.click();
      }, i);
      await new Promise(r => setTimeout(r, 600));

      const result = await page.evaluate((idx, acc, expected) => {
        const inp = document.getElementById('rl-q' + (idx + 1) + '-input');
        const useCorrect = Math.random() < acc;
        const ans = useCorrect ? expected[idx] : (idx === 4 ? 'qisqa.' : String((parseInt(expected[idx], 10) || 0) + 9));
        if (inp) inp.value = ans;
        rlSubmitQuestion();
        return { sent: ans, useCorrect };
      }, i, ACCURACY, expected);
      log(`Q${i + 1}: sent="${result.sent.slice(0, 50)}${result.sent.length > 50 ? '…' : ''}"`);
      await new Promise(r => setTimeout(r, 1500));

      // Advance to next Q (or closure)
      await page.evaluate(() => rlAdvanceFromQuestion());
      await new Promise(r => setTimeout(r, 1000));
    }

    // On closure → click main button to advance to consolidation/boss
    await page.evaluate(() => {
      if (stage6State.screen === 'closure') document.getElementById('action-button').click();
    });
    await new Promise(r => setTimeout(r, 1500));

    // Skip consolidation if it shows
    await page.evaluate(() => {
      if (state.stage === 6.5) document.getElementById('action-button').click();
    });
    await new Promise(r => setTimeout(r, 1500));
  }

  // ── Final Boss ────────────────────────────────────────────────────
  if (!shouldSkipUntil('boss')) {
    banner('Phase 6 · Final Boss');
    await page.evaluate(() => {
      startFinalBoss();
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.getElementById('screen-boss').classList.add('active');
    });
    await new Promise(r => setTimeout(r, 1200));
    // Click intro → battle if needed
    await page.evaluate(() => {
      const introBtn = document.getElementById('boss-intro-start');
      if (introBtn) introBtn.click();
    });
    await new Promise(r => setTimeout(r, 800));

    for (let a = 0; a < 5; a++) {
      const sent = await page.evaluate((idx, acc) => {
        bossRenderQuestion(idx);
        const q = BOSS_QUESTIONS[idx];
        const accept = (q.acceptable && q.acceptable[0]) || '';
        const useCorrect = Math.random() < acc;
        const ans = useCorrect ? accept : 'noaniq';
        const inp = document.getElementById('boss-input');
        if (inp) inp.value = ans;
        bossHandleAction();  // submit
        return { dmg: q.damage, sent: ans, expect: accept, useCorrect };
      }, a, ACCURACY);
      log(`Attack ${a + 1}: dmg=${sent.dmg} sent="${sent.sent.slice(0, 40)}${sent.sent.length > 40 ? '…' : ''}"`);
      await new Promise(r => setTimeout(r, sent.useCorrect ? 1200 : 2200));  // wait for AI on wrong path
      await page.evaluate(() => bossHandleAction());  // advance
      await new Promise(r => setTimeout(r, 800));
    }
    // Wait for bossEnd transition to land on Reflection or Results
    await new Promise(r => setTimeout(r, 2000));
  }

  // ── Reflection (auto-advances if main button clicked) ─────────────
  // If we're on reflection, click through to Results.
  await page.evaluate(() => {
    if (document.getElementById('screen-reflection').classList.contains('active')) {
      document.getElementById('action-button').click();
    }
  });
  await new Promise(r => setTimeout(r, 1500));

  // ── Results ───────────────────────────────────────────────────────
  banner('Stage 9 · AMR Results scorecard');
  await page.evaluate(() => {
    if (typeof showResultsScreen === 'function' && !document.getElementById('screen-results').classList.contains('active')) {
      showResultsScreen();
    }
  });
  await new Promise(r => setTimeout(r, 1200));

  const summary = await page.evaluate(() => ({
    band:     (document.getElementById('results-band')     || {}).textContent,
    headline: (document.getElementById('results-headline') || {}).innerText,
    phases:   Array.from(document.querySelectorAll('.results-phase-row')).map(r => r.innerText.replace(/\s+/g, ' ').trim()),
    axes:     Array.from(document.querySelectorAll('.results-amr-axis')).map(a => a.innerText.replace(/\s+/g, ' ').trim()),
    hasRetry: !!document.getElementById('results-retry-boss'),
  }));

  log('Band     : ' + (summary.band || ''));
  log('Headline : ' + (summary.headline || '').replace(/\n/g, ' '));
  log('Phases:');
  summary.phases.forEach(p => log('  · ' + p));
  log('AMR axes:');
  summary.axes.forEach(a => log('  · ' + a));
  log('Retry button on results: ' + (summary.hasRetry ? 'yes' : 'no'));

  console.log('\n  Browser stays open — close it manually when done.');
  console.log('  Press Ctrl+C in this terminal to kill the runner too.\n');

  // Keep the script alive so the user can poke at the page.
  await new Promise(() => {});
})().catch(e => { console.error(e); process.exit(2); });
