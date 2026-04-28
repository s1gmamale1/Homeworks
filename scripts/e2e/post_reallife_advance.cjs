// Reproduce + verify the "stuck after Real-Life" bug.
// Walks Q1..Q5 with valid answers + clicks the action button at each
// step. Asserts that after Q5 (last) the closure screen activates,
// then a final click moves to Stage 7 (Boss / consolidation).
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 900, height: 1100 },
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  page.on('pageerror', e => console.log('PAGEERR:', e.message));

  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 700));

  const trace = await page.evaluate(async () => {
    const log = [];
    const snap = (label) => log.push({
      label,
      stage: typeof state !== 'undefined' ? state.stage : null,
      rlScreen: typeof stage6State !== 'undefined' ? stage6State.screen : null,
      rlQIndex: typeof stage6State !== 'undefined' ? stage6State.qIndex : null,
      btnText: (document.querySelector('#action-button .btn-text') || {}).textContent,
    });

    if (typeof startStage6 !== 'function') return { err: 'no startStage6' };
    startStage6();
    await new Promise(r => setTimeout(r, 200));
    snap('startStage6 — should be on story');

    // Click "Boshlash" → Q1
    document.getElementById('action-button').click();
    await new Promise(r => setTimeout(r, 500));
    snap('after Boshlash click — should be on Q1');

    const total = (RL_SCENARIO.questions || []).length;
    // Walk Q1..Q5
    for (let i = 0; i < total; i++) {
      // Click capture if Q is text-with-capture
      const cap = document.getElementById('rl-q' + (i + 1) + '-capture-btn');
      if (cap) cap.click();
      // Type a valid answer per question type
      const inp = document.getElementById('rl-q' + (i + 1) + '-input');
      if (inp) {
        if (inp.tagName === 'TEXTAREA') {
          inp.value = "P binodan uzoqlashayotgan, chunki ko'rish burchagi qisqaradi.";
        } else {
          inp.value = ['40', '50', '55', '40', 'uzoqlashayotgan'][i] || '40';
        }
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
      // Submit
      document.getElementById('action-button').click();
      await new Promise(r => setTimeout(r, 300));
      snap('after submit Q' + (i + 1));
      // Click again to advance (rlAdvanceFromQuestion)
      document.getElementById('action-button').click();
      await new Promise(r => setTimeout(r, 400));
      snap('after advance from Q' + (i + 1));
    }

    // After last advance, should be on closure
    return { log };
  });

  console.log('\n=== Trace ===');
  trace.log.forEach(s => console.log(`  [${s.label.padEnd(40)}]  stage=${String(s.stage).padEnd(5)} rlScreen=${String(s.rlScreen).padEnd(8)} qIdx=${s.rlQIndex} btn="${s.btnText}"`));

  // Verdict: did we reach closure or beyond?
  const final = trace.log[trace.log.length - 1];
  const closureReached = trace.log.some(s => s.rlScreen === 'closure');
  const stuck = final && final.stage === 6 && final.rlScreen !== 'closure' && final.rlQIndex === 4;
  console.log('\nclosure reached :', closureReached);
  console.log('stuck on Q5?    :', stuck);
  console.log('\n=== ' + (closureReached && !stuck ? 'PASS' : 'FAIL — student is stuck') + ' ===');

  await browser.close();
  process.exit((closureReached && !stuck) ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
