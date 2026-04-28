// Pre-rasterize SVG samples to PNG using headless Chromium, so the deployed
// runtime can serve raster images directly to Kimi vision. Run after
// generate_notebook_samples.py.
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const SAMPLES_DIR = process.argv[2] ||
  'D:/Homework_Builder/repo/dist/aylananing_kesuvchilari_burchaklari_xossasi/static/samples';
const TARGET_WIDTH = 900;

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();

  const svgs = fs.readdirSync(SAMPLES_DIR).filter(f => f.endsWith('.svg'));
  for (const f of svgs) {
    const svgPath = path.join(SAMPLES_DIR, f);
    const svg = fs.readFileSync(svgPath, 'utf8');
    // Detect viewBox for height ratio
    const m = svg.match(/viewBox="\s*\d+\s+\d+\s+(\d+)\s+(\d+)"/);
    const w = parseInt(m?.[1] || '600', 10);
    const h = parseInt(m?.[2] || '800', 10);
    const targetH = Math.round(TARGET_WIDTH * h / w);

    await page.setViewport({ width: TARGET_WIDTH, height: targetH, deviceScaleFactor: 1 });
    const html = `<html><body style="margin:0;padding:0;">${svg}</body></html>`;
    await page.setContent(html, { waitUntil: 'load' });
    // Make the SVG fill the viewport
    await page.evaluate((W) => {
      const svg = document.querySelector('svg');
      if (svg) {
        svg.setAttribute('width', W);
        svg.removeAttribute('height');
      }
    }, TARGET_WIDTH);
    const pngBuf = await page.screenshot({ type: 'png', omitBackground: false });
    const pngPath = path.join(SAMPLES_DIR, f.replace('.svg', '.png'));
    fs.writeFileSync(pngPath, pngBuf);
    const size = (pngBuf.length / 1024).toFixed(1);
    console.log(`  [OK] ${f} -> ${path.basename(pngPath)} (${size} KB)`);
  }

  await browser.close();
})().catch(e => { console.error(e.stack || e); process.exit(2); });
