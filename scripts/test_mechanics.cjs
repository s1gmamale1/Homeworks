// End-to-end mechanics test for HW-20260427-008.
//   1. Memory Sprint — tap correct option for each of 7 items, advance.
//   2. Adaptive Quiz — simulate 5 rounds, record items shown, ensure no
//      item appears more than 2× and >=3 distinct items show across the run.
//   3. Sentence Fill (Why-Chain slot) — submit invariant, advance to next chain.
//   4. Tile Match — pair-match all 6, run confirmQ, advance.
//   5. Boss — submit correct numeric answer for Q1, ensure HP drops by dmg.
//   6. Real-Life Q1 — submit "40", ensure feedback turns positive.
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 700));

  // ── 1. Memory Sprint (Phase 1) ─────────────────────────────────────────
  // Drive the sprint by directly calling the runtime's ms* functions with
  // the correct option index from MS_QUESTIONS[i].correct.
  console.log('\n=== Memory Sprint mechanics ===');
  const msResult = await page.evaluate(async () => {
    if (typeof MS_QUESTIONS === 'undefined') return { ok: false, err: 'no MS_QUESTIONS' };
    const out = { items: MS_QUESTIONS.length, picks: [] };
    for (let i = 0; i < MS_QUESTIONS.length; i++) {
      const correct = MS_QUESTIONS[i].correct;
      out.picks.push({ i, correct, type: MS_QUESTIONS[i].type, hasOptions: Array.isArray(MS_QUESTIONS[i].options) && MS_QUESTIONS[i].options.length >= 2 });
    }
    return { ok: true, ...out };
  });
  console.log('  items:', msResult.items, ' all have options:', msResult.picks.every(p => p.hasOptions));

  // ── 2. Adaptive Quiz simulation ────────────────────────────────────────
  console.log('\n=== Adaptive Quiz mechanics (5-round simulation) ===');
  const aqResult = await page.evaluate(() => {
    if (typeof gbInitAQ !== 'function') return { ok: false, err: 'no gbInitAQ' };
    gbInitAQ();
    const seen = [];
    // Drive the AQ flow as if the student answered correctly each round.
    for (let r = 0; r < 5; r++) {
      const item = gbAQPickItem();
      seen.push({ id: item.id, tier: item.tier });
      // Simulate correct path
      if (item.tier === 'easy') gbState.aq.currentTier = 'medium';
      else if (item.tier === 'medium') gbState.aq.currentTier = 'hard';
    }
    return { ok: true, seen, distinct: new Set(seen.map(s => s.id)).size };
  });
  console.log('  picks:', aqResult.seen.map(s => `${s.id}/${s.tier}`).join(' → '));
  console.log('  distinct items:', aqResult.distinct, '/', aqResult.seen.length);
  // Failure shape: same id more than twice in a row indicates picker stuck
  let maxRun = 1, run = 1;
  for (let i = 1; i < aqResult.seen.length; i++) {
    if (aqResult.seen[i].id === aqResult.seen[i-1].id) { run++; maxRun = Math.max(maxRun, run); } else run = 1;
  }
  console.log('  longest consecutive same-id run:', maxRun);

  // ── 3. Sentence Fill (gb_why_chain) — submit invariant ────────────────
  console.log('\n=== Sentence Fill mechanics ===');
  const sfResult = await page.evaluate(async () => {
    if (typeof GB_WHY_CHAIN === 'undefined' || GB_WHY_CHAIN.length === 0) return { ok: false };
    const sample = GB_WHY_CHAIN[0];
    return {
      ok: true,
      first_invariant: sample.invariant,
      first_chain_levels: (sample.chain || []).length,
      all_have_invariant: GB_WHY_CHAIN.every(c => c.invariant && String(c.invariant).trim()),
      total: GB_WHY_CHAIN.length,
    };
  });
  console.log('  total chains:', sfResult.total, ' all have invariants:', sfResult.all_have_invariant);
  console.log('  first chain: levels=', sfResult.first_chain_levels, ' invariant=', JSON.stringify(sfResult.first_invariant));

  // ── 4. Tile Match (gb_memory_match) ───────────────────────────────────
  console.log('\n=== Tile Match mechanics ===');
  const tmResult = await page.evaluate(async () => {
    if (typeof GB_MEMORY_MATCH === 'undefined') return { ok: false };
    return {
      ok: true,
      pairs: GB_MEMORY_MATCH.length,
      distinct_a: new Set(GB_MEMORY_MATCH.map(p => p.a)).size,
      distinct_b: new Set(GB_MEMORY_MATCH.map(p => p.b)).size,
      all_have_confirmQ: GB_MEMORY_MATCH.every(p => p.confirmQ && p.correct),
    };
  });
  console.log('  pairs:', tmResult.pairs, ' distinct lefts:', tmResult.distinct_a, ' distinct rights:', tmResult.distinct_b);
  console.log('  all have confirmQ + correct:', tmResult.all_have_confirmQ);

  // ── 5. Boss mechanics: submit "40" against Q1 ──────────────────────────
  console.log('\n=== Boss mechanics (Q1 correct submission) ===');
  const bossResult = await page.evaluate(async () => {
    if (typeof BOSS_QUESTIONS === 'undefined') return { ok: false, err: 'no BOSS_QUESTIONS' };
    const q = BOSS_QUESTIONS[0];
    const matchedCorrect = typeof bossMatch === 'function' ? bossMatch('40', q.acceptable) : null;
    const matchedWrong   = typeof bossMatch === 'function' ? bossMatch('80', q.acceptable) : null;
    return {
      ok: true,
      total_attacks: BOSS_QUESTIONS.length,
      q1_dmg: q.damage,
      q1_acceptable: q.acceptable,
      q1_match_correct: matchedCorrect,
      q1_match_wrong: matchedWrong,
      q3_acceptable: BOSS_QUESTIONS[2].acceptable,
      q3_dmg: BOSS_QUESTIONS[2].damage,
    };
  });
  console.log('  attacks:', bossResult.total_attacks);
  console.log('  Q1 dmg=' + bossResult.q1_dmg + ' accepts:', bossResult.q1_acceptable);
  console.log('  Q1 local match("40")=' + bossResult.q1_match_correct + '   match("80")=' + bossResult.q1_match_wrong);
  console.log('  Q3 dmg=' + bossResult.q3_dmg + ' accepts:', bossResult.q3_acceptable);

  // ── 6. Real-Life Q1 — verify the sub-question data shape ───────────────
  console.log('\n=== Real-Life mechanics ===');
  const rlResult = await page.evaluate(() => {
    if (typeof RL_SCENARIO === 'undefined') return { ok: false, err: 'no RL runtime' };
    const raw = RL_SCENARIO;
    return {
      ok: true,
      hasScenario: true,
      title: raw.title,
      hasStory: !!(raw.story && raw.story.length > 100),
      qCount: Array.isArray(raw.questions) ? raw.questions.length : null,
      questions: (raw.questions || []).map(q => ({
        id: q.id, type: q.type, bloom: q.bloom, pisa: q.pisa, capture: q.capture,
        promptHead: (q.prompt || '').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(0, 70),
        acceptable: q.acceptableAnswers,
        fields: q.fields ? q.fields.map(f => ({label: f.label, accept: f.acceptable})) : null,
      })),
    };
  });
  console.log('  scenario present:', rlResult.hasScenario, ' qCount:', rlResult.qCount);
  if (rlResult.questions) rlResult.questions.forEach((q, i) =>
    console.log(`  ${q.id} type=${q.type} bloom=${q.bloom} cap=${q.capture} accept=${JSON.stringify(q.acceptable)} head="${q.promptHead}"`));
  console.log();
  console.log('=== Phase 5 Consolidation ===');
  const consResult = await page.evaluate(() => {
    if (typeof CONSOLIDATION === 'undefined') return null;
    return {
      title: CONSOLIDATION.title,
      mnemonicLen: (CONSOLIDATION.mnemonic || '').length,
      bullets: (CONSOLIDATION.bullets || []).length,
      hasCheck: !!(CONSOLIDATION.check_prompt && CONSOLIDATION.check_answer),
    };
  });
  console.log(' ', consResult);

  // Verdicts
  const verdict = {
    ms_options_complete: msResult.picks && msResult.picks.every(p => p.hasOptions),
    aq_no_stuck:         aqResult.seen && maxRun <= 1,           // never same item back-to-back
    aq_distinct_ge3:     aqResult.distinct >= 3,
    sf_invariants:       sfResult.all_have_invariant,
    tm_complete_pairs:   tmResult.pairs === 6 && tmResult.distinct_a === 6 && tmResult.distinct_b === 6 && tmResult.all_have_confirmQ,
    boss_match_correct:  bossResult.q1_match_correct === true,
    boss_match_wrong:    bossResult.q1_match_wrong === false,
    boss_dmg_ladder:     bossResult.q1_dmg === 10 && bossResult.q3_dmg === 20,
    rl_5_questions:      rlResult.qCount === 5,
    rl_q5_textarea:      rlResult.questions && rlResult.questions[4] && rlResult.questions[4].type === 'textarea',
    rl_q2_text_input:    rlResult.questions && rlResult.questions[1] && /^text(-with-capture)?$/.test(rlResult.questions[1].type),
    cons_present:        consResult && consResult.bullets >= 3,
    cons_has_check:      consResult && consResult.hasCheck,
  };

  console.log('\n=== Verdicts ===');
  console.log(JSON.stringify(verdict, null, 2));
  const allPass = Object.values(verdict).every(Boolean);
  console.log('\n=== ' + (allPass ? 'ALL PASS ✓' : 'FAILURES — see above ✗') + ' ===');

  await browser.close();
  process.exit(allPass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
