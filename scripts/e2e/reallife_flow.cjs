// Real-Life Challenge end-to-end smoke.
//   1. Render Q1 (text-with-capture) → assert capture button is visible.
//   2. Click capture → captureDone[0] flips → submission gate passes.
//   3. Submit "40" → local match → advances.
//   4. Render Q5 (textarea) → assert textarea element exists.
//   5. Submit a 30-char analysis → AI dispatch fires.
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1280, height: 1000 },
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));

  const aiCalls = [];
  await page.setRequestInterception(true);
  page.on('request', req => {
    if (req.url().includes('/api/ai/')) aiCalls.push({ url: req.url(), method: req.method() });
    req.continue();
  });

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 700));

  const result = await page.evaluate(async () => {
    if (typeof startStage6 !== 'function') return { ok: false, err: 'startStage6 missing' };
    startStage6();
    await new Promise(r => setTimeout(r, 300));
    if (typeof rlShowQuestion !== 'function') return { ok: false, err: 'rlShowQuestion missing' };

    const out = { perQuestion: [], aiDispatchCount: 0 };

    // Walk Q1 (text-with-capture)
    rlShowQuestion(0);
    await new Promise(r => setTimeout(r, 200));
    const q1 = RL_SCENARIO.questions[0];
    const q1CapBtn = document.getElementById('rl-q1-capture-btn');
    out.perQuestion.push({
      idx: 0, type: q1.type, captureRequired: q1.capture,
      captureBtnExists: !!q1CapBtn,
    });

    // Click capture button → captureDone[0] should flip
    if (q1CapBtn) q1CapBtn.click();
    await new Promise(r => setTimeout(r, 100));
    out.perQuestion[0].captureDoneAfterClick = !!(stage6State.captureDone && stage6State.captureDone[0]);

    // Type "40" + submit
    const q1Input = document.getElementById('rl-q1-input');
    if (q1Input) q1Input.value = '40';
    rlSubmitQuestion();
    await new Promise(r => setTimeout(r, 300));
    out.perQuestion[0].q1SubmittedCorrect = !!stage6State.correct[0];

    // Walk to Q5 (textarea)
    rlShowQuestion(4);
    await new Promise(r => setTimeout(r, 300));
    const q5 = RL_SCENARIO.questions[4];
    const q5Textarea = document.getElementById('rl-q5-input');
    out.perQuestion.push({
      idx: 4, type: q5.type,
      textareaExists: !!q5Textarea,
      textareaIsTextarea: q5Textarea && q5Textarea.tagName === 'TEXTAREA',
    });

    // Type a 50-char interpretation answer + submit
    const aiDispatchPromise = new Promise(resolve => {
      document.addEventListener('nets:submit', (ev) => {
        if (ev.detail && ev.detail.kind === 'tutor') {
          out.aiDispatchCount++;
          resolve(true);
        }
      }, { once: true });
      setTimeout(() => resolve(false), 1500);
    });
    if (q5Textarea) q5Textarea.value = "P binodan uzoqlashayotgan, chunki uzoqdagi obyektga ko'rish burchagi qisqaradi.";
    rlSubmitQuestion();
    await aiDispatchPromise;

    return { ok: true, ...out };
  });

  console.log('\n=== Per-question state ===');
  result.perQuestion.forEach(q => console.log(' ', q));
  console.log('\nAI fetch calls captured:', aiCalls.length);
  console.log('AI dispatch events seen :', result.aiDispatchCount);
  aiCalls.forEach(c => console.log('  ' + c.method + ' ' + c.url));

  // Verdicts
  const q1 = result.perQuestion[0] || {};
  const q5 = result.perQuestion[1] || {};
  const verdict = {
    q1_capture_button_present: q1.captureBtnExists === true,
    q1_capture_click_sets_state: q1.captureDoneAfterClick === true,
    q1_submission_succeeds: q1.q1SubmittedCorrect === true,
    q5_textarea_present: q5.textareaExists === true,
    q5_is_real_textarea: q5.textareaIsTextarea === true,
    ai_dispatched_for_q5: result.aiDispatchCount >= 1,
  };
  console.log('\n=== Verdicts ===');
  console.log(JSON.stringify(verdict, null, 2));
  const allPass = Object.values(verdict).every(Boolean);
  console.log('\n=== ' + (allPass ? 'ALL PASS ✓' : 'FAILURES ✗') + ' ===');

  await browser.close();
  process.exit(allPass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
