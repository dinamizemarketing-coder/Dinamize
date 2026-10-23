// render.js: turns cena.html into frames (or a contact sheet) with Playwright.
//
//   node render.js sheet   # a few key frames as PNGs, to check the drawing
//   node render.js video   # 600 frames at 1080x1920 in ./frames, then:
//   ffmpeg -framerate 30 -i frames/%04d.png -vf format=yuv420p -c:v libx264 -preset slow -crf 18 -movflags +faststart out.mp4
const { chromium } = require('playwright');
const fs = require('fs');
const mode = process.argv[2] || 'sheet';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
  const scale = mode === 'video' ? 3 : 1;
  const p = await b.newPage({ viewport: { width: 1000, height: 900 }, deviceScaleFactor: scale });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type()==='error' && errs.push(m.text()));
  await p.goto('file://' + __dirname + '/cena.html');
  await p.evaluate(async () => { await document.fonts.ready; document.querySelector('#play').click(); const f = document.querySelector('.film'); f.style.borderRadius = '0'; f.style.boxShadow = 'none'; f.style.width = '360px'; });
  const film = p.locator('.film');
  if (mode === 'sheet') {
    for (const ms of [1000, 8000, 12900, 14000, 15200, 15620, 16400, 18500]) {
      await p.evaluate(t => window.renderAt(t), ms);
      await film.screenshot({ path: `s${ms}.png` });
    }
  } else {
    fs.mkdirSync('frames', { recursive: true });
    const fps = 30, n = Math.round(20 * fps);
    for (let i = 0; i < n; i++) {
      await p.evaluate(t => window.renderAt(t), i * 1000 / fps);
      await film.screenshot({ path: `frames/${String(i).padStart(4, '0')}.png` });
    }
  }
  console.log('errors:', JSON.stringify(errs));
  await b.close();
})();
