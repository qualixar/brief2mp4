#!/usr/bin/env node
// tests/art_forms/check_looks.mjs: prove every art-form look in looks.js draws, moves and repeats exactly.
//   node tests/art_forms/check_looks.mjs                 check all, print PASS or FAIL per look
//   node tests/art_forms/check_looks.mjs --sheet out.jpg  also write a contact sheet (one frame per look)
//   node tests/art_forms/check_looks.mjs --frames dir      also write one PNG per look
//   node tests/art_forms/check_looks.mjs risograph felt   only these
// For each look, in headless Chrome: draw t = 0.4, 1.5 and 2.3 s; the three pictures must differ (it animates) and
// must not be blank; then draw 1.5 s again, which must match the first 1.5 s pixel for pixel (it is a pure function
// of time and keeps no state). One browser, one look at a time. Needs Chrome and, for the five 3D looks, the network
// (three.js comes from a CDN in the viewer). playwright-core is installed once into ~/.cache/brief2mp4/deps.
import fs from 'node:fs';
import os from 'node:os';
import http from 'node:http';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DIR = path.resolve(HERE, '..', '..', 'plugin', 'skills', 'brief2mp4', 'art-forms');
const DEPS = process.env.BRIEF2MP4_DEPS || path.join(os.homedir(), '.cache', 'brief2mp4', 'deps');
const PW = '1.65.1';
const args = process.argv.slice(2), si = args.indexOf('--sheet'), sheet = si >= 0 ? args[si + 1] : null;
const fi = args.indexOf('--frames'), framesDir = fi >= 0 ? args[fi + 1] : null;   // --frames <dir>: one PNG per look, at 2.2 s
const only = args.filter((a, i) => !a.startsWith('--') && !(si >= 0 && i === si + 1) && !(fi >= 0 && i === fi + 1));
if (framesDir) fs.mkdirSync(framesDir, { recursive: true });

async function playwright() {
  const entry = path.join(DEPS, 'node_modules', 'playwright-core', 'index.mjs');
  if (!fs.existsSync(entry)) {
    console.error(`installing playwright-core ${PW} into ${DEPS} (one time, about 14 MB, install scripts off)`);
    fs.mkdirSync(DEPS, { recursive: true });
    execFileSync(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['i', '--no-save', '--no-audit', '--no-fund', '--ignore-scripts', '--prefix', DEPS, `playwright-core@${PW}`], { stdio: ['ignore', 'inherit', 'inherit'], shell: process.platform === 'win32' });
  }
  return import(pathToFileURL(entry).href);
}
async function launch(pw) {
  const tries = [];
  if (process.env.BRIEF2MP4_CHROME) tries.push({ executablePath: process.env.BRIEF2MP4_CHROME });
  tries.push({ channel: 'chrome' }, {});
  for (const t of tries) { try { return await pw.chromium.launch({ headless: true, ...t }); } catch { /* next */ } }
  console.error(`Could not start Chrome. Install Google Chrome, or run: npx playwright@${PW} install chromium, or set BRIEF2MP4_CHROME.`); process.exit(2);
}
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8' };
const server = http.createServer((req, res) => {
  const file = path.join(DIR, path.basename(new URL(req.url, 'http://x').pathname) || 'gallery.html');
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(req.url === '/favicon.ico' ? 204 : 404).end(); return; }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' }).end(fs.readFileSync(file));
});
await new Promise((ok) => server.listen(0, '127.0.0.1', ok));
const base = `http://127.0.0.1:${server.address().port}/gallery.html`;

const pw = await playwright(), browser = await launch(pw);
const ctx = await browser.newContext({ viewport: { width: 1000, height: 700 }, deviceScaleFactor: 1 });
const { IDS } = await import(pathToFileURL(path.join(DIR, 'looks.js')).href);
const ids = only.length ? only : IDS;
const results = [], thumbs = [];
// a short fingerprint of the canvas, and how much of it is not the corner colour
const PROBE = async ({ id, t }) => {
  window.__draw(t);
  const c = document.getElementById(`c-${id}`), s = new OffscreenCanvas(240, 135), g = s.getContext('2d'); g.drawImage(c, 0, 0, 240, 135);
  const d = g.getImageData(0, 0, 240, 135).data; let h = 2166136261, differ = 0;
  for (let i = 0; i < d.length; i += 4) { h = Math.imul(h ^ d[i], 16777619); h = Math.imul(h ^ d[i + 1], 16777619); h = Math.imul(h ^ d[i + 2], 16777619); if (Math.abs(d[i] - d[0]) + Math.abs(d[i + 1] - d[1]) + Math.abs(d[i + 2] - d[2]) > 30) differ++; }
  return { hash: h >>> 0, painted: differ / (d.length / 4) };
};
for (const id of ids) {
  const page = await ctx.newPage(); const errors = [];
  page.on('pageerror', (e) => errors.push(e.message)); page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  let ok = false, detail = '';
  try {
    await page.goto(`${base}?look=${encodeURIComponent(id)}&t=0`, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__ready === true, null, { timeout: 30000 });
    const a = await page.evaluate(PROBE, { id, t: 0.4 }), b = await page.evaluate(PROBE, { id, t: 1.5 }), c = await page.evaluate(PROBE, { id, t: 2.3 }), b2 = await page.evaluate(PROBE, { id, t: 1.5 });
    const moves = new Set([a.hash, b.hash, c.hash]).size === 3, repeats = b.hash === b2.hash, painted = Math.max(a.painted, b.painted, c.painted) > 0.005;
    ok = moves && repeats && painted && errors.length === 0;
    detail = `moves=${moves}, same t twice matches=${repeats}, painted ${(Math.max(a.painted, b.painted, c.painted) * 100).toFixed(0)}%${errors.length ? `, errors: ${errors[0].slice(0, 140)}` : ''}`;
    if (sheet || framesDir) { await page.evaluate((x) => window.__draw(x.t), { t: 2.2 }); const png = await page.locator(`#c-${id}`).screenshot(); if (sheet) thumbs.push({ id, png: png.toString('base64') }); if (framesDir) fs.writeFileSync(path.join(framesDir, `${id}.png`), png); }
  } catch (e) { detail = String(e.message || e).split('\n')[0]; }
  results.push({ id, ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${id}  (${detail})`);
  await page.close();
}
if (sheet && thumbs.length) {
  const cols = 6, tw = 320, th = 180, lab = 26, gap = 10, rows = Math.ceil(thumbs.length / cols);
  const page = await ctx.newPage();
  const jpg = await page.evaluate(async ({ thumbs, cols, tw, th, lab, gap, rows }) => {
    const c = new OffscreenCanvas(cols * (tw + gap) + gap, rows * (th + lab + gap) + gap), g = c.getContext('2d'); g.fillStyle = '#16130f'; g.fillRect(0, 0, c.width, c.height);
    g.font = '600 15px system-ui, sans-serif'; g.fillStyle = '#f2ede4';
    for (const [i, t] of thumbs.entries()) { const im = await createImageBitmap(await (await fetch('data:image/png;base64,' + t.png)).blob()); const x = gap + (i % cols) * (tw + gap), y = gap + Math.floor(i / cols) * (th + lab + gap); g.drawImage(im, x, y, tw, th); g.fillText(t.id, x + 2, y + th + 18); }
    const blob = await c.convertToBlob({ type: 'image/jpeg', quality: 0.84 }); const buf = new Uint8Array(await blob.arrayBuffer()); let s = ''; for (const b of buf) s += String.fromCharCode(b); return btoa(s);
  }, { thumbs, cols, tw, th, lab, gap, rows });
  fs.writeFileSync(sheet, Buffer.from(jpg, 'base64')); console.log(`wrote ${sheet}`);
}
await browser.close(); server.close();
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed} of ${results.length} looks pass`);
process.exit(failed ? 1 : 0);
