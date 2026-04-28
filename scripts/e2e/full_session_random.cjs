// Full-session simulation. Walks every phase the way a real student
// would, with mixed correctness so the AMR scorecard has interesting
// data to aggregate. At the end, dumps a per-phase + axis-mean +
// band breakdown.
//
// The student persona: ~70% accurate, occasional wrong answer, rough
// but on-topic prose for open responses. Numeric answers are correct
// most of the time but include realistic typos / unit variants.
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

// Deterministic shuffle so re-runs are comparable.
function rng(seed) {
  return function() {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
}
const rand = rng(42);
const pick = (arr) => arr[Math.floor(rand() * arr.length)];

// Wait for the action button label to change AND no animation in flight.
async function waitForBtn(page, expectedSubstr, maxMs = 4000) {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    const txt = await page.evaluate(() => {
      const el = document.querySelector('#action-button .btn-text');
      return el ? el.textContent : '';
    });
    if (!expectedSubstr || (txt && txt.toLowerCase().includes(expectedSubstr.toLowerCase()))) {
      // Also wait for animation flag if exposed.
      const anim = await page.evaluate(() => typeof state !== 'undefined' && state.isAnimating);
      if (!anim) return txt;
    }
    await new Promise(r => setTimeout(r, 80));
  }
  return null;
}

async function clickAction(page) {
  await page.evaluate(() => document.getElementById('action-button').click());
  await new Promise(r => setTimeout(r, 200));
}

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 900, height: 1100 },
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(60000);
  page.on('pageerror', e => console.log('  ✗ PAGEERR:', e.message));

  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║  Full-session student simulation · HW-20260427-008          ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');
  console.log('Loading', URL, '...');
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));

  // ── Stage 0–4: skip preview / flashcards / sprint setup, jump to MS  ──
  console.log('\n── Phase 1 · Memory Sprint (7 items) ──────────────────────────');
  const msResults = await page.evaluate(async () => {
    if (typeof setStage === 'function') setStage(4);
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const sm = document.getElementById('screen-ms');
    if (sm) sm.classList.add('active');
    if (typeof msShow === 'function') msShow(0);
    else if (typeof msInit === 'function') msInit();
    await new Promise(r => setTimeout(r, 200));

    const out = [];
    for (let i = 0; i < MS_QUESTIONS.length; i++) {
      // Randomized ~75% correct
      const item = MS_QUESTIONS[i];
      const wrongChoice = (item.correct + 1) % (item.options || ['','','','']).length;
      const choice = (Math.random() < 0.75) ? item.correct : wrongChoice;
      msHandleAnswer(choice);
      await new Promise(r => setTimeout(r, 600));  // wait for the auto-advance animation
      out.push({ q: i + 1, type: item.type, picked: choice, correct: item.correct, ok: choice === item.correct });
    }
    return out;
  });
  msResults.forEach(r => console.log(`  Q${r.q}  ${r.type.padEnd(6)} picked=${r.picked} correct=${r.correct}  ${r.ok ? 'OK' : 'wrong'}`));
  const msScore = msResults.filter(r => r.ok).length;
  console.log(`  Memory Sprint score: ${msScore} / ${msResults.length}`);

  // ── Phase 3: Adaptive Quiz ─────────────────────────────────────────
  console.log('\n── Phase 3a · Adaptive Quiz (5 rounds) ────────────────────────');
  const aqResults = await page.evaluate(async () => {
    if (typeof setStage === 'function') setStage(5);
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const s5 = document.getElementById('screen-5');
    if (s5) s5.classList.add('active');
    if (typeof gbInit === 'function') gbInit();
    if (typeof gbInitAQ === 'function') gbInitAQ();
    await new Promise(r => setTimeout(r, 300));

    const out = [];
    for (let r = 0; r < 5; r++) {
      const item = gbState.aq.currentItem;
      // Capture, then submit answer (~70% correct)
      gbAQCapture();
      const accept = (item.acceptable && item.acceptable[0]) || item.answer || '';
      const useCorrect = Math.random() < 0.7;
      const tryAns = useCorrect ? accept : String(parseInt(accept, 10) + 1 || 'guess');
      const inp = document.getElementById('gb-aq-input');
      if (inp) inp.value = tryAns;
      gbAQAction();  // grades the submission
      await new Promise(r2 => setTimeout(r2, 200));
      out.push({ round: r + 1, id: item.id, tier: item.tier, sent: tryAns, expected: accept, ok: useCorrect });
      // Advance to next round
      gbAQAction();
      await new Promise(r2 => setTimeout(r2, 200));
    }
    return out;
  });
  aqResults.forEach(r => console.log(`  R${r.round}  id=${r.id} tier=${r.tier.padEnd(6)} sent="${r.sent}" expect="${r.expected}"  ${r.ok ? 'OK' : 'wrong'}`));
  const aqScore = aqResults.filter(r => r.ok).length;
  console.log(`  Adaptive Quiz score: ${aqScore} / ${aqResults.length}`);

  // ── Phase 3b: Sentence Fill ────────────────────────────────────────
  console.log('\n── Phase 3b · Sentence Fill (5 chains, AI-graded) ─────────────');
  const sfResults = await page.evaluate(async () => {
    gbState.subGame = 1;
    if (typeof gbInitWC === 'function') gbInitWC();
    await new Promise(r => setTimeout(r, 200));
    const out = [];
    for (let c = 0; c < GB_WHY_CHAIN.length; c++) {
      gbState.wc.chainIdx = c;
      gbState.wc.levelIdx = 0;
      gbState.wc.retries = 0;
      gbWCRenderChain();
      const chain = GB_WHY_CHAIN[c];
      const inv = chain.invariant || '';
      const useCorrect = Math.random() < 0.7;
      const ta = document.getElementById('gb-wc-textarea');
      if (ta) ta.value = useCorrect ? inv : 'noaniq javob';
      // gbWCAction is async (awaits AI). Actually fire it and wait.
      await gbWCAction();
      await new Promise(r => setTimeout(r, 200));
      out.push({ chain: c + 1, expected: inv, sent: ta ? ta.value : '', ok: useCorrect });
    }
    return out;
  });
  sfResults.forEach(r => console.log(`  C${r.chain}  expect="${r.expected}" sent="${r.sent}"  ${r.ok ? 'OK' : 'wrong (AI judged)'}`));
  const sfScore = sfResults.filter(r => r.ok).length;
  console.log(`  Sentence Fill score: ${sfScore} / ${sfResults.length}`);

  // ── Phase 3c: Tile Match ──────────────────────────────────────────
  console.log('\n── Phase 3c · Tile Match (6 pairs, all matched) ───────────────');
  const tmResult = await page.evaluate(async () => {
    gbState.subGame = 2;
    if (typeof gbInitMM === 'function') gbInitMM();
    await new Promise(r => setTimeout(r, 200));
    for (let p = 0; p < gbState.mm.total; p++) {
      const lp = document.querySelector('.gb-tm-left-tile[data-pair="' + p + '"]');
      const rp = document.querySelector('.gb-tm-right-tile[data-pair="' + p + '"]');
      if (lp) lp.click();
      await new Promise(r => setTimeout(r, 60));
      if (rp) rp.click();
      await new Promise(r => setTimeout(r, 60));
    }
    return { matched: gbState.mm.matched, total: gbState.mm.total };
  });
  console.log(`  matched ${tmResult.matched} / ${tmResult.total}`);

  // ── Phase 4: Real-Life Challenge ──────────────────────────────────
  console.log('\n── Phase 4 · Real-Life Challenge (5 questions) ───────────────');
  const rlResults = await page.evaluate(async () => {
    if (typeof startStage6 === 'function') startStage6();
    await new Promise(r => setTimeout(r, 300));
    rlShowQuestion(0);
    await new Promise(r => setTimeout(r, 300));
    const expected = ['40', '50', '55', '40',
      "P binodan uzoqlashayotgan, chunki ko'rish burchagi qisqaradi va yoylar doimiy bo'lib qoladi."];
    const sent = [];
    const ok = [];
    for (let i = 0; i < RL_SCENARIO.questions.length; i++) {
      const cap = document.getElementById('rl-q' + (i + 1) + '-capture-btn');
      if (cap) cap.click();
      const inp = document.getElementById('rl-q' + (i + 1) + '-input');
      const useCorrect = Math.random() < 0.75;
      const ans = useCorrect ? expected[i] : (i === 4 ? 'qisqa javob.' : String(parseInt(expected[i], 10) + 5));
      if (inp) inp.value = ans;
      sent.push(ans);
      ok.push(useCorrect);
      // Submit
      rlSubmitQuestion();
      await new Promise(r => setTimeout(r, 600));
      // Advance
      rlAdvanceFromQuestion();
      await new Promise(r => setTimeout(r, 800));
    }
    return { sent, ok, finalScreen: stage6State.screen };
  });
  rlResults.sent.forEach((s, i) => console.log(`  Q${i + 1}  sent="${s.length > 50 ? s.slice(0, 47) + '…' : s}"  ${rlResults.ok[i] ? 'OK' : 'wrong'}`));
  console.log(`  finalScreen: ${rlResults.finalScreen}`);

  // Click closure to advance to consolidation
  await page.evaluate(() => {
    if (stage6State.screen === 'closure') document.getElementById('action-button').click();
  });
  await new Promise(r => setTimeout(r, 1500));

  // Skip consolidation if it shows
  await page.evaluate(() => {
    if (state.stage === 6.5) {
      const cont = document.querySelector('#action-button');
      if (cont) cont.click();
    }
  });
  await new Promise(r => setTimeout(r, 1500));

  // ── Phase 6: Final Boss ───────────────────────────────────────────
  console.log('\n── Phase 6 · Final Boss (5 attacks) ──────────────────────────');
  const bossResults = await page.evaluate(async () => {
    if (typeof bossInit === 'function') bossInit();
    if (typeof startFinalBoss === 'function') startFinalBoss();
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const sb = document.getElementById('screen-boss');
    if (sb) sb.classList.add('active');
    await new Promise(r => setTimeout(r, 300));
    const out = [];
    for (let a = 0; a < BOSS_QUESTIONS.length; a++) {
      bossRenderQuestion(a);
      await new Promise(r => setTimeout(r, 200));
      const q = BOSS_QUESTIONS[a];
      const useCorrect = Math.random() < 0.7;
      const accept = q.acceptable && q.acceptable[0] || '';
      const ans = useCorrect ? accept : 'noaniq';
      const inp = document.getElementById('boss-input');
      if (inp) inp.value = ans;
      bossHandleAction();
      await new Promise(r => setTimeout(r, useCorrect ? 200 : 1500));  // wait for AI on wrong path
      out.push({ attack: a + 1, dmg: q.damage, sent: ans, expect: accept, hp: bossState.hp, correct: bossState.correct });
      bossHandleAction();  // advance
      await new Promise(r => setTimeout(r, 200));
    }
    return out;
  });
  bossResults.forEach(r => console.log(`  Attack ${r.attack}  -${r.dmg} HP  sent="${r.sent}" expect="${r.expect}"  → HP=${r.hp}, total correct=${r.correct}`));

  // ── Force-render results screen (Reflection auto-advances) ──────────
  console.log('\n── Phase 9 · Results / AMR scorecard ──────────────────────────');
  await page.evaluate(async () => {
    if (typeof showResultsScreen === 'function') showResultsScreen();
    await new Promise(r => setTimeout(r, 600));
  });
  const report = await page.evaluate(() => {
    const agg = window.__sessionAggregate || {};
    return {
      band: (document.getElementById('results-band') || {}).textContent,
      headline: (document.getElementById('results-headline') || {}).innerText,
      phases: Array.from(document.querySelectorAll('.results-phase-row')).map(r => r.innerText.replace(/\s+/g, ' ').trim()),
      axes: Array.from(document.querySelectorAll('.results-amr-axis')).map(a => a.innerText.replace(/\s+/g, ' ').trim()),
      mastery: (document.getElementById('results-mastery') || {}).innerText,
      sessionLogSize: (window.__sessionLog || []).length,
      overallScore: agg.overall_score,
      overallAxis1: agg.overall_axis_1,
      overallAxis2: agg.overall_axis_2,
      totalCorrect: agg.totalCorrect,
      totalItems: agg.totalItems,
    };
  });

  console.log('\n  ╔════════════════════════════════════════════════════════════╗');
  console.log(`  ║  Overall band: ${(report.band || '').padEnd(43)}║`);
  console.log('  ╚════════════════════════════════════════════════════════════╝');
  console.log('  ' + (report.headline || '').replace(/\n/g, ' '));
  console.log('\n  Per-phase tally:');
  report.phases.forEach(p => console.log('    · ' + p));
  console.log('\n  AMR axis breakdown:');
  report.axes.forEach(a => console.log('    · ' + a));
  console.log('\n  Mastery promotion note:\n    ' + (report.mastery || '').replace(/\n/g, ' '));
  console.log('\n  Aggregate metrics:');
  console.log('    overall_score    :', report.overallScore !== undefined ? report.overallScore.toFixed(1) + '%' : 'n/a');
  console.log('    overall_axis_1   :', report.overallAxis1 !== undefined ? report.overallAxis1.toFixed(2) + ' / 4' : 'n/a');
  console.log('    overall_axis_2   :', report.overallAxis2 !== undefined ? report.overallAxis2.toFixed(2) + ' / 4' : 'n/a');
  console.log('    raw correct      :', report.totalCorrect, '/', report.totalItems);
  console.log('    session log rows :', report.sessionLogSize);

  await page.screenshot({ path: 'C:/Users/Agent/AppData/Local/Temp/full_session_results.png', fullPage: true });
  console.log('\n  Screenshot: C:/Users/Agent/AppData/Local/Temp/full_session_results.png');

  await browser.close();
})().catch(e => { console.error(e); process.exit(2); });
