// UI-sound WIRING verification walk.
//
// We cannot HEAR audio in a headless run, so instead we assert the engine fires
// the RIGHT cue at the right moment: `sfx.play(id)` pushes `id` into a global
// `window.__SFX_LOG` array (set before app boot here). The walk performs real
// interactions and checks the cue log grew with the expected ids — proving the
// wiring deterministically. It also verifies the MUTE toggle stops cues.
//
// Run against a live server seeded by _seed_walk_demo.py:
//   node scripts/e2e/sfx_walk.cjs
// Honors BOSS_E2E_BASE / BOSS_E2E_HW_ID / BOSS_E2E_SESSION. STATIC-CHECK target
// for test_e2e_scripts_use_shared_chrome_launcher.

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
const getLog = (page) => page.evaluate(() => (window.__SFX_LOG || []).slice());

async function clickSel(page, sel) {
  try { const el = await page.$(sel); if (el) { await el.click(); return true; } } catch (_) {}
  return false;
}

(async () => {
  const browser = await puppeteer.launch(launchOptions({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--autoplay-policy=no-user-gesture-required'],
    defaultViewport: { width: 1280, height: 900 },
  }));
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE_ERR:', m.text()); });

  // Set the cue log + force unmuted BEFORE any app code runs.
  await page.evaluateOnNewDocument(() => {
    window.__SFX_LOG = [];
    try { localStorage.setItem('nets_sfx_muted', '0'); } catch (e) {}
  });

  const results = {};
  const expect = (name, ok, detail) => {
    results[name] = ok ? 'PASS' : `FAIL ${detail || ''}`;
    console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}${detail ? ' — ' + detail : ''}`);
  };

  console.log('\n[load]', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await sleep(900);
  // Prime: the engine resumes audio on first pointerdown. A click anywhere primes it.
  await page.mouse.click(640, 450);
  await sleep(150);

  // ── 1. Hub node click → expect "tick" + a "screen" transition ────────────
  let before = (await getLog(page)).length;
  const clickedNode = await clickSel(page, '[data-testid="hub-start-fc"]')
    || await clickSel(page, '[data-testid="hub-start-cbp"]');
  await sleep(1100);
  let after = await getLog(page);
  const slice1 = after.slice(before);
  console.log('  after hub node click, new cues:', JSON.stringify(slice1));
  expect('hub_node_tick', slice1.includes('tick'), JSON.stringify(slice1));
  expect('screen_transition', slice1.includes('screen'), JSON.stringify(slice1));

  // ── 2. Flashcards: flip + "Bildim"(knew) → expect tick + correct ─────────
  before = (await getLog(page)).length;
  await clickSel(page, '[data-testid="fc-card"]');     // flip → tick
  await sleep(200);
  await clickSel(page, '[data-testid="fc-knew"]');     // knew → correct
  await sleep(300);
  after = await getLog(page);
  const slice2 = after.slice(before);
  console.log('  after flip + Bildim, new cues:', JSON.stringify(slice2));
  expect('flashcard_cues', slice2.includes('tick') && slice2.includes('correct'), JSON.stringify(slice2));

  // ── 3. Tutor open → expect popup-open (+ tick on launcher) ───────────────
  before = (await getLog(page)).length;
  await clickSel(page, '[data-testid="tutor-launcher"]')
    || await clickSel(page, '.launcher')
    || await page.evaluate(() => {
         const b = [...document.querySelectorAll('button')].find(x => /tutor|chat|ask/i.test(x.getAttribute('aria-label')||''));
         if (b) b.click();
       });
  await sleep(700);
  after = await getLog(page);
  const slice3 = after.slice(before);
  console.log('  after tutor toggle, new cues:', JSON.stringify(slice3));
  expect('tutor_popup_open', slice3.includes('popup-open') || slice3.includes('tick'), JSON.stringify(slice3));

  // Screenshot the sound toggle (bottom-right, above the tutor bubble).
  await page.screenshot({ path: path.join(SHOTS_DIR, 'sfx-sound-toggle.png'), fullPage: false });
  console.log('  [screenshot] sfx-sound-toggle.png');

  // ── 4. MUTE test: toggle mute, then click → expect NO new cues ───────────
  const toggled = await clickSel(page, '[data-testid="sound-toggle"]');
  await sleep(200);
  const muted = await page.evaluate(() => document.querySelector('[data-testid="sound-toggle"]')?.getAttribute('data-muted'));
  before = (await getLog(page)).length;
  await page.mouse.click(640, 450);                    // a click that would tick
  await clickSel(page, '[data-testid="fc-card"]');
  await sleep(300);
  after = await getLog(page);
  const slice4 = after.slice(before);
  console.log('  muted=', muted, ' new cues after click while muted:', JSON.stringify(slice4));
  expect('mute_silences_cues', toggled && muted === '1' && slice4.length === 0, `muted=${muted} cues=${JSON.stringify(slice4)}`);

  // ── 5. Unmute → cues resume ──────────────────────────────────────────────
  await clickSel(page, '[data-testid="sound-toggle"]');
  await sleep(150);
  before = (await getLog(page)).length;
  await clickSel(page, '[data-testid="fc-card"]');
  await sleep(250);
  after = await getLog(page);
  const slice5 = after.slice(before);
  console.log('  after unmute click, new cues:', JSON.stringify(slice5));
  expect('unmute_resumes', slice5.length > 0, JSON.stringify(slice5));

  console.log('\n=== SFX wiring walk results ===');
  console.log(JSON.stringify(results, null, 2));
  const fails = Object.entries(results).filter(([, v]) => v !== 'PASS');
  console.log('\nFull cue log:', JSON.stringify(await getLog(page)));
  await browser.close();
  process.exit(fails.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
