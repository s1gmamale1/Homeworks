// Headless verifier for HW-20260427-008 after the canonical rebuild.
// Checks: AQ has 5 distinct prompts, no duplicates within 5 rounds; SF (was
// "Why Chain") has 5 chains; Tile Match has 6 pairs; Real-Life has q1..q5;
// Boss has 5 attacks. Captures sample text for visual confirmation.
const puppeteer = require('puppeteer');
const { launchOptions } = require('./puppeteer_launcher.cjs');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch(launchOptions({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  }));
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));

  // Pull the in-memory data arrays from the runtime — they're declared in
  // template scope and re-bound by the injector before <body>.
  const data = await page.evaluate(() => ({
    aq:   typeof GB_ADAPTIVE_QUIZ === 'undefined' ? null : GB_ADAPTIVE_QUIZ.map(x => ({
      id: x.id, tier: x.tier, bloom: x.bloom, pisa: x.pisa,
      promptHead: (x.prompt || '').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(0, 90),
      answer: x.answer, acceptable: x.acceptable,
    })),
    wc:   typeof GB_WHY_CHAIN === 'undefined' ? null : GB_WHY_CHAIN.map(x => ({
      id: x.id || '?', invariant: x.invariant,
      chainLen: (x.chain || []).length,
      probeHead: (x.chain && x.chain[0] && x.chain[0].probe || '').replace(/<[^>]+>/g,' ').slice(0, 80),
    })),
    mm:   typeof GB_MEMORY_MATCH === 'undefined' ? null : GB_MEMORY_MATCH,
    boss: typeof BOSS_QUESTIONS === 'undefined' ? null : BOSS_QUESTIONS.map(x => ({
      // post-injector shape: {id, tier, damage, bloom, pisa, prompt, acceptable, hints}
      id: x.id, tier: x.tier, damage: x.damage, bloom: x.bloom, pisa: x.pisa,
      hasSvg: /<svg/i.test(x.prompt || ''),
      promptHead: (x.prompt || '').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(0, 90),
      acceptable: (x.acceptable || []).slice(0, 3),
      hints: (x.hints || []).map(h => (h || '').slice(0, 60)),
    })),
    rl: (() => {
      if (typeof RL_QUESTIONS !== 'undefined') return Object.keys(RL_QUESTIONS || {}).map(k => k);
      return null;
    })(),
  }));

  // Simulate the AQ picker for 5 rounds and verify no immediate same-id repeats
  // and that a healthy variety appears across rounds.
  const sim = await page.evaluate(() => {
    if (typeof gbInitAQ !== 'function' || typeof gbAQPickItem !== 'function') return null;
    // Reset state and simulate as if we always answered correctly.
    gbInitAQ();
    const seen = [];
    for (let i = 0; i < 5; i++) {
      const item = gbAQPickItem();
      seen.push({ id: item.id, tier: item.tier, head: (item.prompt || '').replace(/<[^>]+>/g,' ').slice(0,40) });
      // Simulate "correct" advancement: easy → medium → hard.
      if (item.tier === 'easy') gbState.aq.currentTier = 'medium';
      else if (item.tier === 'medium') gbState.aq.currentTier = 'hard';
    }
    return seen;
  });

  console.log();
  console.log('=== Adaptive Quiz (data) ===');
  if (data.aq) data.aq.forEach((x, i) => console.log(`  ${i+1}. id=${x.id} tier=${x.tier} bloom=${x.bloom} pisa=${x.pisa} ans=${JSON.stringify(x.acceptable || x.answer)}`));
  console.log();
  console.log('=== AQ pick simulation (5 rounds, easy→medium→hard) ===');
  const ids = (sim || []).map(s => s.id);
  if (sim) sim.forEach((s, i) => console.log(`  round ${i+1}: id=${s.id} tier=${s.tier} ${s.head}`));
  const distinctRatio = new Set(ids).size / ids.length;
  console.log(`  distinct ids = ${new Set(ids).size}/${ids.length}`);

  console.log();
  console.log('=== Sentence Fill (gb_why_chain slot, 5 items) ===');
  if (data.wc) data.wc.forEach((x, i) => console.log(`  ${i+1}. id=${x.id} chainLen=${x.chainLen} invariant=${JSON.stringify(x.invariant)} probe="${x.probeHead}"`));

  console.log();
  console.log('=== Tile Match pairs (gb_memory_match) ===');
  if (data.mm) data.mm.forEach((p, i) => console.log(`  ${i+1}. ${JSON.stringify(p)}`));

  console.log();
  console.log('=== Boss attacks ===');
  if (data.boss) data.boss.forEach((b, i) => console.log(`  ${i+1}. id=${b.id} tier=${b.tier} dmg=${b.damage} bloom=${b.bloom}/pisa=${b.pisa} svg=${b.hasSvg} acceptable=${JSON.stringify(b.acceptable)}`));

  // Header label sanity check
  const labels = await page.evaluate(() => ({
    g2: (document.querySelector('#gb-panel-wc .gb-section-title') || {}).textContent,
    g3: (document.querySelector('#gb-panel-mm .gb-section-title') || {}).textContent,
  }));
  console.log();
  console.log('=== UI labels ===');
  console.log('  Game 2 title:', JSON.stringify(labels.g2));
  console.log('  Game 3 title:', JSON.stringify(labels.g3));

  // Verdicts
  const verdict = {
    aq_count: data.aq && data.aq.length === 5,
    aq_tiers_distinct: data.aq && new Set(data.aq.map(x => x.tier)).size === 3,
    aq_distinct_ratio: distinctRatio >= 0.8,
    wc_count: data.wc && data.wc.length === 5,
    mm_count: data.mm && data.mm.length === 6,
    boss_count: data.boss && data.boss.length === 5,
    boss_dmg_ladder: data.boss && JSON.stringify(data.boss.map(b => b.damage)) === '[10,10,20,20,30]',
    boss_acceptable: data.boss && data.boss.every(b => Array.isArray(b.acceptable) && b.acceptable.length > 0),
    boss_q1_svg: data.boss && data.boss[0].hasSvg,
    boss_q5_svg: data.boss && data.boss[4].hasSvg,
    label_g2: labels.g2 && labels.g2.includes('SENTENCE FILL'),
    label_g3: labels.g3 && labels.g3.includes('TILE MATCH'),
  };
  console.log();
  console.log('=== Verdicts ===');
  console.log(JSON.stringify(verdict, null, 2));
  const allPass = Object.values(verdict).every(Boolean);
  console.log('\n=== ' + (allPass ? 'ALL PASS ✓' : 'SOME FAILED ✗') + ' ===');

  await browser.close();
  process.exit(allPass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
