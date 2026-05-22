// Division-1 integrity walk: ace the 3 CBP checkpoints with a pre-seeded low
// session mastery so the 3rd trips the conservative `sudden_mastery` flag, and
// capture the advisory soft-friction IntegrityNudge — proving it renders BESIDE
// the feedback and never blocks progress. Convention: use the shared launcher.
// (Requires the walk homework seeded + low mastery upserted on :8767.)
const { launchOptions } = require('./puppeteer_launcher.cjs');
const { chromium } = require('playwright');

const HW = process.env.AC_HW || 'HW-20260522-002';
const SESSION = process.env.AC_SESSION || 'nudge-shot';
const URL = `http://127.0.0.1:8767/h/${HW}?session=${SESSION}`;
const OUT = 'docs/screenshots';
// CBP correct option indices for the verify homework: cp0=1, cp1=1, cp2=0.
const CORRECT = [1, 1, 0];

async function shot(page, name) {
  await page.screenshot({ path: `${OUT}/integrity-${name}.png` });
  console.log('SHOT', name);
}

(async () => {
  const browser = await chromium.launch(launchOptions());
  const page = await browser.newPage({ viewport: { width: 1320, height: 980 }, deviceScaleFactor: 2 });
  page.on('pageerror', e => console.log('PAGE-CRASH', String(e).slice(0, 200)));

  await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);
  await shot(page, '1-hub');

  // Enter Case-Based Preview (Division 1) — the whole node is clickable (onClick=startCbp).
  await page.getByTestId('hub-start-cbp').click({ timeout: 12000, force: true }).catch(() => {});
  await page.waitForTimeout(1800);
  await page.getByTestId('cbp-begin').click({ timeout: 12000 }).catch(() => {});
  await page.waitForTimeout(1000);
  await shot(page, '2-cbp-checkpoint0');

  // Answer all 3 checkpoints correctly.
  for (let i = 0; i < 3; i++) {
    const radios = page.locator('[role="radio"], [role="radiogroup"] button, [role="radiogroup"] [role="radio"]');
    const n = await radios.count();
    if (n > CORRECT[i]) {
      await radios.nth(CORRECT[i]).click({ timeout: 8000 }).catch(() => {});
    }
    await page.getByTestId('cbp-submit').click({ timeout: 8000 }).catch(() => {});
    // On the 3rd checkpoint the sudden_mastery nudge should appear in the feedback.
    if (i === 2) {
      const appeared = await page.getByTestId('integrity-nudge')
        .waitFor({ state: 'visible', timeout: 15000 }).then(() => true).catch(() => false);
      console.log('integrity-nudge visible after cp3:', appeared);
      await page.waitForTimeout(800);
      await shot(page, '3-nudge');
      // Prove non-blocking: the Continue button is still present + enabled.
      const cont = page.getByTestId('cbp-continue');
      const contEnabled = await cont.isEnabled().catch(() => false);
      console.log('cbp-continue still enabled (non-blocking):', contEnabled);
    } else {
      await page.getByTestId('cbp-continue').click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(900);
    }
  }

  const txt = await page.evaluate(() => document.body.innerText.replace(/\n{2,}/g, '\n').slice(0, 600));
  console.log('VISIBLE>>>\n' + txt + '\n<<<');
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('WALK_FAIL', e); process.exit(1); });
