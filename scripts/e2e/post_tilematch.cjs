// Reproduce the "white screen after Tile Match" bug.
// Programmatically: start AQ → finish AQ → finish SF → win Tile Match
// → click action button → assert screen-6 (Real-Life) is visible.
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1280, height: 900 },
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE_ERR:', m.text()); });

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));

  const trace = await page.evaluate(async () => {
    const log = [];
    const snapshot = (label) => {
      const screens = ['screen-0','screen-1','screen-2','screen-3','screen-ms','screen-5','screen-6','screen-boss','screen-reflection','screen-results'];
      const active = screens.filter(id => {
        const el = document.getElementById(id);
        return el && (el.classList.contains('active') || (el.id === 'screen-5' && getComputedStyle(el).opacity !== '0' && getComputedStyle(el).display !== 'none'));
      });
      const subGame  = (typeof gbState !== 'undefined' && gbState && typeof gbState.subGame !== 'undefined') ? gbState.subGame : 'n/a';
      const stage    = (typeof state !== 'undefined' && state && typeof state.stage !== 'undefined') ? state.stage : 'n/a';
      log.push({ label, stage, subGame, active });
    };

    // Skip ahead: jump straight to Game Breaks (stage 5) and run AQ to finish.
    // Easiest path: directly call gbInitAQ and synthesize completion.
    snapshot('initial');

    // Force into stage 5 / game-break screen.
    if (typeof setStage === 'function') setStage(5);
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const s5 = document.getElementById('screen-5');
    if (s5) {
      s5.style.display = '';
      s5.style.opacity = '';
      s5.style.transition = '';
    }
    // Activate the AQ panel
    if (typeof gbInitAQ === 'function') gbInitAQ();
    snapshot('after gbInitAQ');

    // Skip AQ → SF → directly trigger MM
    gbState.subGame = 2;
    if (typeof gbInitMM === 'function') gbInitMM();
    snapshot('after gbInitMM');

    // Match all 6 pairs to trigger gbMMWin
    for (let p = 0; p < 6; p++) {
      const lp = document.querySelector('.gb-tm-left-tile[data-pair="' + p + '"]');
      const rp = document.querySelector('.gb-tm-right-tile[data-pair="' + p + '"]');
      if (lp) lp.click();
      if (rp) rp.click();
      await new Promise(r => setTimeout(r, 50));
    }
    snapshot('after match 6/6');

    // gbMMWin should have set subGame=3 and queued button "Keyingi bosqich"
    // Now click the action button to advance.
    const btn = document.getElementById('action-button');
    if (btn) btn.click();
    await new Promise(r => setTimeout(r, 700));
    snapshot('after click "Keyingi bosqich"');

    // After gbExitToStage6 + startStage6 should have screen-6 active.
    return {
      log,
      finalScreens: Array.from(document.querySelectorAll('.screen')).map(s => ({
        id: s.id,
        active: s.classList.contains('active'),
        opacity: getComputedStyle(s).opacity,
        display: getComputedStyle(s).display,
      })),
      screen5Style: (function() {
        const s = document.getElementById('screen-5');
        return s ? {
          opacity: s.style.opacity,
          display: getComputedStyle(s).display,
          computedOpacity: getComputedStyle(s).opacity,
        } : null;
      })(),
      stageNow: (typeof state !== 'undefined') ? state.stage : null,
      subGameNow: (typeof gbState !== 'undefined') ? gbState.subGame : null,
      stage6StateScreen: (typeof stage6State !== 'undefined') ? stage6State.screen : null,
    };
  });

  console.log('\n=== Phase trace ===');
  trace.log.forEach(s => {
    console.log(`  [${s.label}]  stage=${s.stage}  subGame=${s.subGame}  active=${JSON.stringify(s.active)}`);
  });
  console.log('\n=== Final state ===');
  console.log('  stage now      :', trace.stageNow);
  console.log('  subGame now    :', trace.subGameNow);
  console.log('  stage6 screen  :', trace.stage6StateScreen);
  console.log('  screen-5 style :', trace.screen5Style);
  console.log('  ALL screens (id, active, opacity, display):');
  trace.finalScreens.forEach(s => console.log(`    ${s.id.padEnd(20)}  active=${s.active}  opacity=${s.opacity}  display=${s.display}`));

  await page.screenshot({ path: 'C:/Users/Agent/AppData/Local/Temp/post_tilematch.png', fullPage: false });
  console.log('\nScreenshot: C:/Users/Agent/AppData/Local/Temp/post_tilematch.png');

  await browser.close();
})().catch(e => { console.error(e); process.exit(2); });
