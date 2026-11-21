#!/usr/bin/env node
// tests/art_forms/contact_sheet.mjs: one PNG with every chosen look at several moments, to see a batch at a glance.
//   node tests/art_forms/contact_sheet.mjs --out sheet.png                      every look, t = 0.5, 2 and 4 s
//   node tests/art_forms/contact_sheet.mjs --out sheet.png --times 1,3 pencil-sketch sand-art
//   node tests/art_forms/contact_sheet.mjs --out sheet.png --tile 640 oil-painting    bigger tiles, to inspect one look
// One row per look, one column per time. Same browser set-up as check_looks.mjs (headless Chrome, the looks files
// listed in art-forms/looks-files.json); it only draws and photographs, it does not judge.
import fs from 'node:fs';
import os from 'node:os';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DIR = path.resolve(HERE, '..', '..', 'plugin', 'skills', 'brief2mp4', 'art-forms');
const DEPS = process.env.BRIEF2MP4_DEPS || path.join(os.homedir(), '.cache', 'brief2mp4', 'deps');
const args = process.argv.slice(2), opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const out = opt('--out', null), times = opt('--times', '0.5,2,4').split(',').map(Number), tw = Number(opt('--tile', 400)), th = Math.round(tw * 9 / 16);
const taken = new Set(['--out', '--times', '--tile'].flatMap((n) => (args.indexOf(n) >= 0 ? [args.indexOf(n) + 1] : [])));
const only = args.filter((a, i) => !a.startsWith('--') && !taken.has(i));
if (!out) { console.error('usage: contact_sheet.mjs --out sheet.png [--times 0.5,2,4] [--tile 400] [look ...]'); process.exit(2); }

const entry = path.join(DEPS, 'node_modules', 'playwright-core', 'index.mjs');
if (!fs.existsSync(entry)) { console.error('playwright-core is not installed: run tests/art_forms/check_looks.mjs once, it installs it'); process.exit(2); }
const pw = await import(pathToFileURL(entry).href);
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const file = path.join(DIR, path.basename(new URL(req.url, 'http://x').pathname) || 'gallery.html');
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(req.url === '/favicon.ico' ? 204 : 404).end(); return; }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' }).end(fs.readFileSync(file));
});
await new Promise((ok) => server.listen(0, '127.0.0.1', ok));
const base = `http://127.0.0.1:${server.address().port}/gallery.html`;
let browser;
for (const t of [process.env.BRIEF2MP4_CHROME ? { executablePath: process.env.BRIEF2MP4_CHROME } : null, { channel: 'chrome' }, {}].filter(Boolean)) { try { browser = await pw.chromium.launch({ headless: true, ...t }); break; } catch { /* next */ } }
if (!browser) { console.error('Could not start Chrome (set BRIEF2MP4_CHROME)'); process.exit(2); }
const ctx = await browser.newContext({ viewport: { width: 1000, height: 700 }, deviceScaleFactor: 1 });
const files = JSON.parse(fs.readFileSync(path.join(DIR, 'looks-files.json'), 'utf8')), all = [];
for (const f of files) all.push(...Object.keys((await import(pathToFileURL(path.join(DIR, f)).href)).LOOKS));
const ids = only.length ? only : all, rows = [];
for (const id of ids) {
  const page = await ctx.newPage(), errors = []; page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`${base}?look=${encodeURIComponent(id)}&t=0`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 30000 });
  const frames = [];
  for (const t of times) { await page.evaluate((x) => window.__draw(x), t); frames.push((await page.locator(`#c-${id}`).screenshot()).toString('base64')); }
  rows.push({ id, frames }); await page.close(); if (errors.length) console.error(`${id}: ${errors[0]}`);
}
const page = await ctx.newPage(), gap = 8, lab = 22;
const png = await page.evaluate(async ({ rows, times, tw, th, gap, lab }) => {
  const c = new OffscreenCanvas(times.length * (tw + gap) + gap, rows.length * (th + lab + gap) + gap), g = c.getContext('2d');
  g.fillStyle = '#16130f'; g.fillRect(0, 0, c.width, c.height); g.font = '600 14px system-ui, sans-serif';
  for (const [r, row] of rows.entries()) {
    const y = gap + r * (th + lab + gap); g.fillStyle = '#f2ede4'; g.fillText(`${row.id}   (t = ${times.join(' s, ')} s)`, gap, y + 15);
    for (const [i, b64] of row.frames.entries()) g.drawImage(await createImageBitmap(await (await fetch('data:image/png;base64,' + b64)).blob()), gap + i * (tw + gap), y + lab, tw, th);
  }
  const buf = new Uint8Array(await (await c.convertToBlob({ type: 'image/png' })).arrayBuffer()); let s = ''; for (const b of buf) s += String.fromCharCode(b); return btoa(s);
}, { rows, times, tw, th, gap, lab });
fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true }); fs.writeFileSync(out, Buffer.from(png, 'base64'));
console.log(`wrote ${out} (${rows.length} looks x ${times.length} times)`);
await browser.close(); server.close();
