# ASCII art

Also called: ascii, text art.

Family: Screens and cinema. Cadence: steps 12 times a second. Usual tool: HyperFrames (canvas).

A scene drawn only from monospaced text characters chosen by brightness: a sunrise over a sea and a headland, with waves, glitter and birds that move.

ASCII art is a graphic design technique of pictures pieced together from the 95 printable characters of the ASCII standard of 1963. Among the oldest examples are works by Kenneth Knowlton from around 1966, and it was invented in large part because early printers lacked graphics ability.

## What makes it read as this

- Only characters from one monospaced font: no lines, no shapes
- Brightness maps to a ramp of characters from sparse to dense: space, dot, colon, plus, hash, at-sign
- A tight grid: about 120 columns and 45 rows
- One or two colours on a near-black ground, brighter for denser characters
- Motion comes from the character values changing, not from moving glyphs

## Timing

The picture is recomputed 12 times a second; waves and glitter change on each step.

## How to build it

- Choose a grid (`cols`, `rows`) and compute a brightness function `lum(u, v, t)` for each cell
- Map brightness to a ramp: `RAMP[Math.floor(L * (RAMP.length - 0.01))]`
- Draw a row as a few strings, one per brightness bucket, with spaces where another bucket has the character, so that monospace alignment holds and a row costs a few `fillText` calls
- Scale horizontally so that the columns fill the frame
- For a real image, sample a downscaled copy of it instead of the function

## Assets

All in code. For video, sample frames and map their luminance. Use only pictures, footage and music the user owns or may reuse; if the user has an image model available, generate textures and cut-out parts with it and say so in REPORT.md.

## Sound and pacing

A dial-up modem, key clicks, a slow arpeggio. Practice note.

## What makes it look wrong

- A proportional font: the grid breaks
- Too few columns: the picture does not read
- Too much contrast between neighbouring characters

## Tested demo

This is the look from `art-forms/looks-screen.js`, which `tests/art_forms/check_looks.mjs` draws in a real browser: it must paint, change over time, and give the same pixels when the same time is drawn twice. View it: open `art-forms/gallery.html?look=ascii` through a local server. The helpers it calls (`held`, `frameOf`, `jit`, `hash`, `grain`, `prog`, the easings) are at the top of `art-forms/looks.js`. Take the technique, not the picture.

```js
  ascii: { kind: '2d', fps: 12, draw(g, t, W, H) {
    // a sunrise over a wavy sea and a headland, drawn only from monospaced characters picked by brightness; the waves, the glitter and the birds move
    const ts = held(t, 12), cols = 120, rows = 45, RAMP = ' .,:;-=+*#%@'; g.fillStyle = '#0b0705'; g.fillRect(0, 0, W, H); g.font = mono;
    const cw = g.measureText('M').width, sx = W / (cols * cw), lum = (u, v) => {
      const dx = (u - 0.62) * 1.78, dy = v - (0.4 - 0.02 * Math.sin(ts)), d = Math.hypot(dx, dy); let L = 0.02 + 0.34 * Math.max(0, 0.66 - v) ** 1.5 + 0.75 * Math.exp(-d * 4.5);
      if (d < 0.14) L = 1; const ridge = 0.5 - 0.09 * vnoise(u * 7, 0, 3) - 0.05 * Math.abs(Math.sin(u * 8)); if (u < 0.38 && v > ridge && v < 0.64) L = 0.05 + 0.08 * Math.sin(u * 60);
      if (v >= 0.64) { const k = v - 0.64; L = 0.06 + 0.2 * Math.max(0, Math.sin(u * 46 + ts * 3.2 + k * 70)) ** 2; if (Math.abs(u - 0.62) < 0.05 + k * 0.5) L += 0.85 * Math.max(0, Math.sin(k * 120 + ts * 5) * 0.5 + 0.5) ** 2 * (1 - k * 2); }
      return clamp(L);
    };
    const rowsTxt = [[], [], [], []]; for (let r = 0; r < rows; r++) { const lines = ['', '', '', '']; for (let c = 0; c < cols; c++) { const L = lum(c / cols, r / rows), ch = RAMP[Math.floor(L * 11.99)], b = L > 0.85 ? 3 : L > 0.55 ? 2 : L > 0.3 ? 1 : 0; for (let k = 0; k < 4; k++) lines[k] += k === b ? ch : ' '; } rowsTxt[r] = lines; }
    g.save(); g.scale(sx, 1); g.textBaseline = 'top'; const cols4 = ['#a8661a', '#e8962a', '#ffc15a', '#fff6dc'], rh = H / rows;
    for (let r = 0; r < rows; r++) for (let k = 0; k < 4; k++) { if (!rowsTxt[r][k].trim()) continue; g.fillStyle = cols4[k]; g.fillText(rowsTxt[r][k], 0, r * rh); }
    for (let i = 0; i < 4; i++) { const bx = (ts * 9 + i * 31) % cols, by = 6 + i * 3 + Math.round(Math.sin(ts * 2 + i)); g.fillStyle = '#ffb347'; g.fillText(Math.floor(ts * 4 + i) % 2 ? 'v' : '^', bx * cw, by * rh); }
    g.restore(); scanlines(g, W, H, 0.12, 4);
  } }
```

To use a look in a HyperFrames composition, drive it from the timeline the way `references/threejs.md` shows: a paused GSAP timeline tweens a plain object's `t` from 0 to the duration with `ease: "none"`, and `onUpdate` calls `draw` with that `t`. Vendor GSAP and three.js into the project first.

## Sources

- <https://en.wikipedia.org/wiki/ASCII_art>

Facts checked on 2026-11-21. Lines marked "practice note" are working advice, not sourced facts.
