// Verify the two updated mechanics:
//   1. Sentence Fill — typing a paraphrase ("kichraytirish") for "ayirish"
//      now passes via AI grading (was rejected by old keyword-overlap check).
//   2. Tile Match — left-click + right-click matches a pair; wrong picks
//      flash and deselect; six matches → win banner.
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1280, height: 900 },
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(40000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 700));

  // ── 1. Sentence Fill via AI grader ────────────────────────────────────
  console.log('\n=== Sentence Fill — AI grader test ===');
  const sfTest = await page.evaluate(async () => {
    if (typeof gbWCAIGrade !== 'function') return { ok: false, err: 'gbWCAIGrade not exposed' };
    const out = [];
    // Test 1: exact match → deterministic correct
    const t1 = await gbWCAIGrade(
      'Tashqaridagi burchak — yoylar ___ yarmiga teng.',
      'ayirmasining',
      'ayirmasining'
    );
    out.push({ case: 'exact "ayirmasining"', correct: t1.correct, source: t1.source, score: t1.score });
    // Test 2: paraphrase / different form → AI fallback
    const t2 = await gbWCAIGrade(
      'Tashqaridagi burchak — yoylar ___ yarmiga teng.',
      'ayirmasi',  // grammatical variant
      'ayirmasining'
    );
    out.push({ case: 'variant "ayirmasi"', correct: t2.correct, source: t2.source, score: t2.score, feedback: (t2.feedback || '').slice(0, 80) });
    // Test 3: synonym for "ayirish" → AI should accept
    const t3 = await gbWCAIGrade(
      'Yoylar bir-biridan ___ qiladi.',
      'kichraytirish',  // synonym for ayirish (in this context)
      'ayirish'
    );
    out.push({ case: 'synonym "kichraytirish"→"ayirish"', correct: t3.correct, source: t3.source, score: t3.score, feedback: (t3.feedback || '').slice(0, 80) });
    // Test 4: clearly wrong
    const t4 = await gbWCAIGrade(
      'Yoylar bir-biriga ___.',
      'ko\'paytirish',  // multiplication, wrong
      'ayirish'
    );
    out.push({ case: 'wrong "ko\'paytirish"', correct: t4.correct, source: t4.source, score: t4.score });
    return { ok: true, results: out };
  });
  if (sfTest.results) sfTest.results.forEach(r => console.log(' ', r));

  // ── 2. Tile Match — left/right column logic ────────────────────────────
  console.log('\n=== Tile Match — left/right matching ===');
  const tmTest = await page.evaluate(async () => {
    if (typeof gbInitMM !== 'function') return { ok: false, err: 'gbInitMM not defined' };
    gbInitMM();
    await new Promise(r => setTimeout(r, 200));
    const lefts  = document.querySelectorAll('.gb-tm-left-tile');
    const rights = document.querySelectorAll('.gb-tm-right-tile');
    if (lefts.length === 0 || rights.length === 0) return { ok: false, err: 'tiles not rendered' };

    const out = { lefts: lefts.length, rights: rights.length, matchedAfterCorrectClick: null, wrongFlashesAfterMismatch: null, allMatchedAfterFullRun: null };

    // Step A: click first left tile (pair 0) then click the right tile that has data-pair="0"
    const left0  = document.querySelector('.gb-tm-left-tile[data-pair="0"]');
    const right0 = document.querySelector('.gb-tm-right-tile[data-pair="0"]');
    left0.click();
    out.leftSelectedAfterClick = left0.classList.contains('selected');
    right0.click();
    await new Promise(r => setTimeout(r, 200));
    out.matchedAfterCorrectClick = left0.classList.contains('matched') && right0.classList.contains('matched');

    // Step B: click left[1], then click a wrong right (pair 2) → wrong-flash
    const left1  = document.querySelector('.gb-tm-left-tile[data-pair="1"]');
    const right2 = document.querySelector('.gb-tm-right-tile[data-pair="2"]');
    left1.click();
    right2.click();
    await new Promise(r => setTimeout(r, 100));
    out.wrongFlashesAfterMismatch = left1.classList.contains('wrong-flash') && right2.classList.contains('wrong-flash');
    // Wait for the flash animation to clear
    await new Promise(r => setTimeout(r, 500));
    out.deselectAfterWrong = !left1.classList.contains('selected');

    // Step C: walk through all remaining pairs correctly to win
    for (let p = 1; p < gbState.mm.total; p++) {
      const lp = document.querySelector('.gb-tm-left-tile[data-pair="' + p + '"]');
      const rp = document.querySelector('.gb-tm-right-tile[data-pair="' + p + '"]');
      if (!lp || !rp || lp.classList.contains('matched')) continue;
      lp.click();
      await new Promise(r => setTimeout(r, 80));
      rp.click();
      await new Promise(r => setTimeout(r, 80));
    }
    out.matchedTotal = gbState.mm.matched;
    out.winBannerVisible = document.getElementById('gb-mm-win-banner').classList.contains('show');
    return { ok: true, ...out };
  });
  console.log(' ', tmTest);

  // Verdicts
  const sfPass = sfTest.results && sfTest.results.length === 4;
  const verdict = {
    sf_exact_match_correct:  sfPass && sfTest.results[0].correct === true,
    sf_variant_accepted:     sfPass && sfTest.results[1].correct === true,
    sf_synonym_accepted:     sfPass && sfTest.results[2].correct === true,
    sf_wrong_rejected:       sfPass && sfTest.results[3].correct === false,
    sf_uses_ai_path:         sfPass && (sfTest.results[1].source === 'ai' || sfTest.results[2].source === 'ai'),
    tm_lefts_6:              tmTest.lefts === 6,
    tm_rights_6:             tmTest.rights === 6,
    tm_left_select_works:    tmTest.leftSelectedAfterClick === true,
    tm_correct_match:        tmTest.matchedAfterCorrectClick === true,
    tm_wrong_flashes:        tmTest.wrongFlashesAfterMismatch === true,
    tm_wrong_deselects:      tmTest.deselectAfterWrong === true,
    tm_full_win:             tmTest.matchedTotal === 6 && tmTest.winBannerVisible === true,
  };
  console.log('\n=== Verdicts ===');
  console.log(JSON.stringify(verdict, null, 2));
  const allPass = Object.values(verdict).every(Boolean);
  console.log('\n=== ' + (allPass ? 'ALL PASS ✓' : 'FAILURES ✗') + ' ===');

  await browser.close();
  process.exit(allPass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
