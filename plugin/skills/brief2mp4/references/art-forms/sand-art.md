# Sand animation

Also called: sand art, sand drawing, sand painting animation.

Family: Drawn and painted. Cadence: steps 12 times a second. Usual tool: HyperFrames (canvas).

Light shining through a thin layer of sand on a light table: figures are wiped out as bright lines, thin sand glows amber, and the piles at the edges stay dark. A figure morphs as the sand is pushed.

A form of stop motion in which sand is shaped under a camera, often lit from behind by a lightbox so that the thickness of the sand gives shading and lines. Sand art is older than film: Navajo, Aboriginal Australian and Tibetan cultures made it, and the Japanese bonseki has been practised since at least the 7th century. Swiss animators Gisèle and Nag Ansorge and the American Caroline Leaf took it up for films in the 1960s.

## What makes it read as this

- An amber, grainy field lit from behind, brightest at the centre and darker at the edges
- Figures are bright wiped lines with a soft glow, with darker piles of sand at the sides
- A small heap of sand ahead of the finger while a line is drawn
- Loose grains over everything, light and dark
- One form flows into the next as the sand is pushed

## Timing

Lines are wiped on over 0.5 to 1.5 seconds each and the figure morphs over about 2 seconds. The picture steps about 12 times a second.

## How to build it

- Fill with a warm amber, add blotches of lighter and darker sand with radial gradients, then a soft central glow
- Each wiped line: a dark wide pass, an amber glow pass, a bright core pass (`wipe()` in `looks-painted.js`)
- Morph the outline by interpolating radius functions of the angle (`sandFigure()`), so sun rays become petals
- Finish with light and dark grain and a dark multiplied vignette

## Assets

All in code. Real sand photographed on a light table makes a good grain layer. Use only pictures, footage and music the user owns or may reuse; if the user has an image model available, generate textures and cut-out parts with it and say so in REPORT.md.

## Sound and pacing

A soft, dry, whispering rub under each wipe, a slow music bed that suits a story. Practice note.

## What makes it look wrong

- Clean vector lines on a flat colour, which is not sand
- A dark background with no glow
- Figures that appear without being wiped on

## Tested demo

This is the look from `art-forms/looks-painted.js`, which `tests/art_forms/check_looks.mjs` draws in a real browser: it must paint, change over time, and give the same pixels when the same time is drawn twice. View it: open `art-forms/gallery.html?look=sand-art` through a local server. The helpers it calls (`held`, `frameOf`, `jit`, `hash`, `grain`, `prog`, the easings) are at the top of `art-forms/looks.js`. Take the technique, not the picture.

```js
  'sand-art': { kind: '2d', fps: 12, draw(g, t, W, H) {
    // a sun that becomes a flower, wiped out of a layer of sand on a light table: bright where the sand is cleared, amber where it is thin, dark in the piles
    const ts = held(t, 12), f = frameOf(t, 12), m = easeInOut(prog(ts, 1.7, 1.8)), cx = W / 2, cy = H * 0.42 - m * 24, R = 118, gy = H * 0.88;
    bg(g, W, H, '#fff3d4'); g.fillStyle = 'rgb(204,126,42)'; g.fillRect(0, 0, W, H); const glow = g.createRadialGradient(W / 2, H * 0.42, 20, W / 2, H * 0.42, W * 0.5); glow.addColorStop(0, 'rgba(255,226,150,.5)'); glow.addColorStop(1, 'rgba(255,226,150,0)'); g.fillStyle = glow; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 9; i++) { const bx = hash(i, 1) * W, by = hash(i, 2) * H, b = g.createRadialGradient(bx, by, 10, bx, by, 150 + hash(i, 3) * 110); b.addColorStop(0, i % 2 ? 'rgba(255,196,96,.3)' : 'rgba(70,34,6,.32)'); b.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = b; g.fillRect(0, 0, W, H); }   // the sand is thicker in some places
    wipe(g, spline([[40, gy + 6], [240, gy - 8], [480, gy + 4], [720, gy - 10], [920, gy + 2]], 10), easeOut(prog(ts, 0.05, 0.9)), 7, f);
    wipe(g, sandFigure(cx, cy, R, m), prog(ts, 0.25, 1.4), 8, f);
    wipe(g, circlePts(cx, cy, 0.3 * R, 30), prog(ts, 1.1, 0.5), 6, f);
    for (let i = 0; i < 12; i++) { const a = (i / 12) * TAU + m, k = prog(ts, 2.0 + i * 0.05, 0.1) * m; if (k > 0) { g.fillStyle = 'rgba(255,248,222,.95)'; g.beginPath(); g.arc(cx + Math.cos(a) * 0.55 * R, cy + Math.sin(a) * 0.55 * R, 4.5 * k, 0, TAU); g.fill(); } }
    const sb = cy + R, mid = lerp(sb, gy, 0.55);   // the flower's lowest petal is at R below the centre
    wipe(g, spline([[cx, sb], [cx - 7, mid], [cx + 3, gy]], 10), prog(ts, 2.3, 0.9), 7, f);
    wipe(g, spline([[cx - 3, mid + 8], [cx + 50, mid - 38], [cx + 112, mid - 34], [cx + 66, mid - 2], [cx - 3, mid + 8]], 10), prog(ts, 2.9, 0.7), 6, f);
    wipe(g, spline([[cx - 4, mid + 40], [cx - 56, mid + 2], [cx - 116, mid + 6], [cx - 70, mid + 38], [cx - 4, mid + 40]], 10), prog(ts, 3.2, 0.7), 6, f);
    g.drawImage(grain(W, H, 41, 150, [255, 226, 160]), 0, 0); g.drawImage(grain(W, H, 42, 130, [46, 22, 4]), 0, 0);   // loose sand over everything, light and dark
    g.save(); g.globalCompositeOperation = 'multiply'; const v = g.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.98); v.addColorStop(0, 'rgba(255,255,255,0)'); v.addColorStop(1, 'rgba(60,28,0,.5)'); g.fillStyle = v; g.fillRect(0, 0, W, H); g.restore();
  } }
```

To use a look in a HyperFrames composition, drive it from the timeline the way `references/threejs.md` shows: a paused GSAP timeline tweens a plain object's `t` from 0 to the duration with `ease: "none"`, and `onUpdate` calls `draw` with that `t`. Vendor GSAP and three.js into the project first.

## Sources

- <https://en.wikipedia.org/wiki/Sand_animation>

Facts checked on 2026-11-21. Lines marked "practice note" are working advice, not sourced facts.
