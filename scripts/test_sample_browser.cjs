// Headless Chromium test: opens deployed playable, walks to Phase 4,
// clicks "Use sample" on Q1, submits, captures the actual data URL sent to
// /api/grade and the grade card.
const puppeteer = require('puppeteer');
const SERVER = 'http://127.0.0.1:5071';

(async () => {
  console.log('Launching headless Chromium...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);

  let lastGradeBody = null;
  page.on('request', (req) => {
    if (req.url().endsWith('/api/grade') && req.method() === 'POST') {
      try { lastGradeBody = JSON.parse(req.postData() || '{}'); } catch (_) {}
    }
  });
  page.on('console', msg => {
    const t = msg.text();
    if (t && !t.includes('Failed to load resource')) console.log('  [page]', t);
  });

  console.log('Loading', SERVER);
  await page.goto(SERVER + '/', { waitUntil: 'networkidle0' });

  // Walk to Phase 4 Real-Life
  for (let i = 0; i < 4; i++) {
    await page.click('#next-phase-btn');
    await new Promise(r => setTimeout(r, 250));
  }

  console.log('On Real-Life — finding sample button on Q1...');
  await page.waitForSelector('[data-item-id="Q1"] .photo-sample');

  console.log('Clicking sample button...');
  await page.click('[data-item-id="Q1"] .photo-sample');
  await page.waitForFunction(
    () => !document.querySelector('[data-item-id="Q1"] .photo-preview').hidden,
    { timeout: 10000 }
  );
  console.log('  [OK] Photo preview visible');

  const imgInfo = await page.evaluate(() => {
    const img = document.querySelector('[data-item-id="Q1"] .photo-preview img');
    return {
      src_prefix: (img.src || '').slice(0, 50),
      length: (img.src || '').length,
    };
  });
  console.log('  Image data URL:', imgInfo.src_prefix + '...', '(' + imgInfo.length + ' chars)');

  await page.evaluate(() => {
    document.querySelector('[data-item-id="Q1"] textarea').value =
      'Daftaringizdagi hisob: P = (150-70)/2 = 40 darja.';
  });
  console.log('Submitting...');
  await page.click('[data-item-id="Q1"] .btn-primary');

  await page.waitForSelector('[data-item-id="Q1"] .grade-card', { timeout: 90000 });
  const gradeInfo = await page.evaluate(() => {
    const c = document.querySelector('[data-item-id="Q1"] .grade-card');
    return {
      score: c.querySelector('.pct-label')?.textContent,
      band: c.querySelector('.pct-band')?.textContent,
      meta: [...c.querySelectorAll('.grade-meta .pill')].map(p => p.textContent).join(' | '),
    };
  });
  console.log('\n=========================================');
  console.log('  Grade card:');
  console.log('    score:', gradeInfo.score);
  console.log('    band: ', gradeInfo.band);
  console.log('    meta: ', gradeInfo.meta);
  console.log();
  console.log('  Image sent to /api/grade:', lastGradeBody?.image_b64 ? 'YES' : 'NO');
  if (lastGradeBody?.image_b64) {
    console.log('    starts with:', lastGradeBody.image_b64.slice(0, 30) + '...');
    console.log('    size:       ', lastGradeBody.image_b64.length, 'chars');
  }
  console.log('=========================================');

  await browser.close();
  process.exit(0);
})().catch(e => { console.error('crash:', e.stack || e); process.exit(2); });
