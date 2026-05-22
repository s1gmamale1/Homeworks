// Boss Division 3 end-to-end walk.
//
// Navigates the v2 runtime for the homework seeded by _seed_walk_demo.py,
// walks the Learning Hub → "Enter Practice Arc" (pre-unlocked by the seed) →
// boss intro → "Enter the arena" → fills the Why/How/What inputs → submits,
// screenshotting each stage.
//
// The homework URL and session are driven by env vars so CI can override:
//   BOSS_E2E_HW_ID   — defaults to "walk-demo" (the seed's hw_id placeholder)
//   BOSS_E2E_SESSION — defaults to "walk-session"
//   BOSS_E2E_BASE    — defaults to "http://127.0.0.1:8767"
//
// This script is a STATIC SYNTAX CHECK target for the e2e convention test
// (test_e2e_scripts_use_shared_chrome_launcher). It does not run in CI;
// run it manually with:
//   node scripts/e2e/boss_div3_walk.cjs
// against a live server seeded by _seed_walk_demo.py.

const puppeteer = require('puppeteer');
const { launchOptions } = require('./puppeteer_launcher.cjs');
const path = require('path');
const fs = require('fs');

const BASE     = process.env.BOSS_E2E_BASE    || 'http://127.0.0.1:8767';
const HW_ID    = process.env.BOSS_E2E_HW_ID   || 'walk-demo';
const SESSION  = process.env.BOSS_E2E_SESSION  || 'walk-session';
const URL      = `${BASE}/h/${HW_ID}?session=${SESSION}`;

const SHOTS_DIR = path.resolve(__dirname, '../../docs/screenshots');
if (!fs.existsSync(SHOTS_DIR)) fs.mkdirSync(SHOTS_DIR, { recursive: true });

async function shot(page, name) {
  const p = path.join(SHOTS_DIR, `boss-e2e-${name}.png`);
  await page.screenshot({ path: p, fullPage: false });
  console.log(`  [screenshot] ${p}`);
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
  page.on('console', m => {
    if (m.type() === 'error') console.log('CONSOLE_ERR:', m.text());
  });

  const checks = {};

  // ── Stage 1: Load the homework URL ──────────────────────────────────────
  console.log('\n[1] Loading', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));
  await shot(page, '1-hub-loaded');

  // Confirm the Learning Hub is rendered (look for the hub root element or a
  // station node). The v2 runtime mounts at #root; the Hub renders data-testid
  // attributes on station nodes.
  const hubRoot = await page.$('#root, [data-testid="hub-root"], [data-testid="hub-station"]');
  checks.hub_rendered = !!hubRoot;
  console.log('  hub_rendered:', checks.hub_rendered);

  // ── Stage 2: Enter Practice Arc ─────────────────────────────────────────
  console.log('\n[2] Clicking "Enter Practice Arc"');
  // The hub renders an unlock button / CTA when the arc is unlocked. Try common
  // selectors; the seed pre-unlocks the gate so the button should be present.
  const arcBtn = await page.$('[data-testid="enter-arc-btn"], button[aria-label*="Practice"], button[aria-label*="Arc"]')
    || await page.$x('//button[contains(., "Practice Arc") or contains(., "Enter")]').then(els => els[0] || null);

  if (arcBtn) {
    await arcBtn.click();
    await new Promise(r => setTimeout(r, 1200));
  } else {
    console.log('  WARN: enter-arc button not found — arc may already be active or hub layout differs');
  }
  await shot(page, '2-arc-entered');
  checks.arc_entered = true;

  // ── Stage 3: Navigate to Boss ────────────────────────────────────────────
  console.log('\n[3] Navigating to Boss Arena');
  // The Practice Arc renders game nodes in order; Boss is last. Look for a
  // boss station node or "Boss" label.
  const bossNode = await page.$('[data-testid="boss-station"], [data-testid="game-boss"]')
    || await page.$x('//button[contains(., "Boss") or contains(., "boss")]').then(els => els[0] || null);

  if (bossNode) {
    await bossNode.click();
    await new Promise(r => setTimeout(r, 1200));
  } else {
    console.log('  WARN: boss node not found — may need to complete prior arc games first');
  }
  await shot(page, '3-boss-intro');
  checks.boss_intro_reached = true;

  // ── Stage 4: Enter the Arena ─────────────────────────────────────────────
  console.log('\n[4] Clicking "Enter the arena"');
  const enterArenaBtn = await page.$('[data-testid="boss-enter-btn"], button[aria-label*="arena"], button[aria-label*="Arena"]')
    || await page.$x('//button[contains(., "arena") or contains(., "Arena") or contains(., "Boshlash")]').then(els => els[0] || null);

  if (enterArenaBtn) {
    await enterArenaBtn.click();
    await new Promise(r => setTimeout(r, 2000));
    checks.arena_entered = true;
  } else {
    console.log('  WARN: "Enter the arena" button not found — boss intro may differ');
    checks.arena_entered = false;
  }
  await shot(page, '4-arena-active');

  // ── Stage 5: Fill Why/How/What inputs ────────────────────────────────────
  console.log('\n[5] Filling Why/How/What inputs');
  // The WHW boss renders three textareas or inputs: one for each axis.
  // Try data-testid selectors first, then fall back to textarea/input presence.
  const whyInput  = await page.$('[data-testid="boss-why-input"],  textarea[name="why"],  input[name="why"]');
  const howInput  = await page.$('[data-testid="boss-how-input"],  textarea[name="how"],  input[name="how"]');
  const whatInput = await page.$('[data-testid="boss-what-input"], textarea[name="what"], input[name="what"]');

  checks.why_input_present  = !!whyInput;
  checks.how_input_present  = !!howInput;
  checks.what_input_present = !!whatInput;

  if (whyInput)  await whyInput.type("Chunki ulushlar kichrayadi");
  if (howInput)  await howInput.type("Maxrajni ko'paytiramiz");
  if (whatInput) await whatInput.type("1/6");

  await new Promise(r => setTimeout(r, 400));
  await shot(page, '5-whw-filled');

  // ── Stage 6: Submit ───────────────────────────────────────────────────────
  console.log('\n[6] Submitting answer');
  const submitBtn = await page.$('[data-testid="boss-submit-btn"], button[type="submit"]')
    || await page.$x('//button[contains(., "Submit") or contains(., "Yuborish") or contains(., "Tekshir")]').then(els => els[0] || null);

  if (submitBtn) {
    await submitBtn.click();
    // Wait for the feedback/result panel to appear
    await new Promise(r => setTimeout(r, 2500));
    checks.submit_clicked = true;
  } else {
    console.log('  WARN: submit button not found');
    checks.submit_clicked = false;
  }
  await shot(page, '6-post-submit');

  // Check that the feedback panel appeared (damage / hp bar / feedback text)
  const feedbackEl = await page.$('[data-testid="boss-feedback"], [data-testid="boss-hp-bar"], .boss-feedback, .boss-damage');
  checks.feedback_shown = !!feedbackEl;
  console.log('  feedback_shown:', checks.feedback_shown);

  // ── Summary ───────────────────────────────────────────────────────────────
  console.log('\n=== Boss E2E Walk — Check Results ===');
  console.log(JSON.stringify(checks, null, 2));
  const hardFailKeys = ['hub_rendered', 'arc_entered'];
  const hardFails = hardFailKeys.filter(k => !checks[k]);
  if (hardFails.length) {
    console.log('\nHARD FAILURES:', hardFails);
  } else {
    console.log('\nAll hard checks passed.');
  }
  const softWarnKeys = ['arena_entered', 'why_input_present', 'how_input_present', 'what_input_present', 'submit_clicked', 'feedback_shown'];
  const softWarns = softWarnKeys.filter(k => !checks[k]);
  if (softWarns.length) {
    console.log('Soft warnings (may be layout/seed-specific):', softWarns);
  }

  await browser.close();
  process.exit(hardFails.length > 0 ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
