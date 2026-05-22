// Living-backdrop verification walk.
//
// Confirms the reusable LivingBackdrop (aurora + candy blobs + pointer/touch
// color-trail) renders on the three runtime surfaces that previously lacked it:
// Flashcards (Division 2 · gold), Memory Check (Division 2 · teal), and the
// Practice Arc + its games/Boss (Division 3 · purple). The Hub is screenshotted
// first as a control (it already had the effect).
//
// For each surface we draw a diagonal pointer stroke right before the shot so
// the comet trail is captured mid-life (it fades ~2s after the last input).
//
// Run against a live server seeded by _seed_walk_demo.py:
//   node scripts/e2e/living_backdrop_walk.cjs
// Honors BOSS_E2E_BASE / BOSS_E2E_HW_ID / BOSS_E2E_SESSION (same env as the
// boss walk). STATIC-CHECK target for test_e2e_scripts_use_shared_chrome_launcher.

const puppeteer = require('puppeteer');
const { launchOptions } = require('./puppeteer_launcher.cjs');
const path = require('path');
const fs = require('fs');

const BASE    = process.env.BOSS_E2E_BASE    || 'http://127.0.0.1:8767';
const HW_ID   = process.env.BOSS_E2E_HW_ID   || 'walk-demo';
const SESSION = process.env.BOSS_E2E_SESSION || 'walk-session';
const URL     = `${BASE}/h/${HW_ID}?session=${SESSION}`;

const SHOTS_DIR = path.resolve(__dirname, '../../docs/screenshots');
if (!fs.existsSync(SHOTS_DIR)) fs.mkdirSync(SHOTS_DIR, { recursive: true });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function shot(page, name) {
  const p = path.join(SHOTS_DIR, `living-backdrop-${name}.png`);
  await page.screenshot({ path: p, fullPage: false });
  console.log(`  [screenshot] ${p}`);
}

// Draw a diagonal pointer stroke across the viewport, then a click-burst, so the
// comet trail + a burst ring are alive when we shoot.
async function drawTrail(page) {
  const w = 1280, h = 900;
  await page.mouse.move(180, 220, { steps: 1 });
  await page.mouse.move(1080, 700, { steps: 28 });
  await page.mouse.move(640, 300, { steps: 18 });
  await sleep(120);
}

async function clickFirst(page, selectors, label) {
  for (const sel of selectors) {
    try {
      const el = await page.$(sel);
      if (el) { await el.click(); console.log(`  clicked ${label} via ${sel}`); return true; }
    } catch (_) { /* keep trying */ }
  }
  // XPath text fallback
  console.log(`  WARN: ${label} not found via testids`);
  return false;
}

(async () => {
  const browser = await puppeteer.launch(launchOptions({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1280, height: 900 },
  }));
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE_ERR:', m.text()); });

  const checks = {};

  // ── Hub (control — already has the effect) ──────────────────────────────
  console.log('\n[1] Hub (control)', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await sleep(900);
  checks.hub_rendered = !!(await page.$('#root'));
  await drawTrail(page);
  await shot(page, '1-hub-control');

  // ── Flashcards (Division 2 · gold) ──────────────────────────────────────
  console.log('\n[2] Flashcards');
  await clickFirst(page, [
    '[data-testid="hub-start-fc"]',
    '[data-testid="hub-fc"]',
  ], 'flashcards node');
  await sleep(1000);
  checks.flashcards_screen = !!(await page.$('[data-testid="fc-flashcards"]'));
  // probe the fixed backdrop canvas exists in the DOM
  checks.backdrop_canvas_present = await page.evaluate(() =>
    !!document.querySelector('canvas[aria-hidden="true"]'));
  await drawTrail(page);
  await shot(page, '2-flashcards-gold');

  // ── Memory Check (Division 2 · teal) ────────────────────────────────────
  console.log('\n[3] Memory Check');
  // view all cards then start the check: flip (fc-card) + advance (fc-knew) a
  // few times so every card lands in viewedCards, which enables fc-start-mc.
  for (let i = 0; i < 8; i++) {
    await clickFirst(page, ['[data-testid="fc-card"]'], 'fc-card flip');
    await sleep(120);
    await clickFirst(page, ['[data-testid="fc-knew"]', '[data-testid="fc-didnt"]'], 'fc advance');
    await sleep(160);
  }
  await clickFirst(page, ['[data-testid="fc-start-mc"]'], 'start memory check');
  await sleep(1000);
  checks.memorycheck_screen = !!(await page.$('[data-testid="mc-item"], [data-testid="mc-fill-input"]'));
  await drawTrail(page);
  await shot(page, '3-memorycheck-teal');

  // ── Practice Arc + games (Division 3 · purple) ──────────────────────────
  console.log('\n[4] Practice Arc');
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await sleep(900);
  await clickFirst(page, [
    '[data-testid="hub-enter-practice"]',
    '[data-testid="hub-division-3"] button',
    '[data-testid="enter-arc-btn"]',
  ], 'practice node');
  await sleep(1300);
  checks.practice_screen = !!(await page.$('[data-testid="screen-practice"]'));
  await drawTrail(page);
  await shot(page, '4-practice-purple');

  // first game (whatever node renders inside the arc)
  await sleep(400);
  await drawTrail(page);
  await shot(page, '5-practice-game');

  // ── Boss (Division 3) — best-effort navigation ──────────────────────────
  console.log('\n[5] Boss (best-effort)');
  await clickFirst(page, [
    '[data-testid="game-boss"]', '[data-testid="boss-station"]',
    '[data-testid="boss-enter-btn"]',
  ], 'boss node');
  await sleep(1500);
  await drawTrail(page);
  await shot(page, '6-boss-purple');

  console.log('\n=== Living-backdrop walk checks ===');
  console.log(JSON.stringify(checks, null, 2));
  await browser.close();
  process.exit(checks.hub_rendered ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
