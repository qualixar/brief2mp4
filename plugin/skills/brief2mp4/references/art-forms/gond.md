# Gond

Also called: gond painting, gond art, gondi art, jangarh kalam.

Family: Folk and print traditions. Cadence: steps 8 times a second. Usual tool: HyperFrames (canvas or SVG).

Animals and trees drawn in thin black outline and filled with bands of dots and dashes in bright colours, each band following the shape, on a light ground. It is a living tradition with working artists; the demo here is a code study of its visual rules, not the craft itself, and a film should credit the tradition and, where it can, commission or license work from the artists.

The Gond, or Gondi, people are an ethnolinguistic group spread across central and eastern India, including Madhya Pradesh, Maharashtra and Chhattisgarh. The artist Jangarh Singh Shyam, born into a Pardhan Gond family in Patangarh, Mandla district, Madhya Pradesh, is credited with starting the school called Jangarh Kalam; he used lines of coloured dots, inspired by Gond tattoos, with bands of dots, dense cross-hatching and comb-lines, and painted animals such as tigers and deer.

Sourcing note: Wikipedia has no standalone Gond painting article, so the sources are the Gond people article and the article on Jangarh Singh Shyam, the artist most closely tied to the modern style. Confirm the wider tradition against a museum source before making claims in a film.

## What makes it read as this

- Thin black outlines round animals, birds and trees
- Inside every shape: rows of dots, dashes, and dots and dashes, each row in its own bright colour
- The rows follow the long axis of the shape
- A light or bright ground, often with a dotted ground and border
- Animals and trees shown as decorated cut-outs, with no shading

## Timing

Parts draw on one after another over about 3 seconds, outline first, then the bands fill. The picture steps about 8 times a second.

## How to build it

- Draw each part with `folkShape()` and a pale tint fill
- Bands: rows along the shape's axis with a gentle wave, alternating dots, ticks and dot-and-tick, cycling six colours (`gondBands()` in `looks-folk.js`)
- Add a dot grid over the ground and a dotted border
- Keep the outline thin so the dots and dashes carry the colour

## Assets

All in code. Use only pictures, footage and music the user owns or may reuse; if the user has an image model available, generate textures and cut-out parts with it and say so in REPORT.md.

## Sound and pacing

Drums and a stringed drone, a rhythmic tapping as each band fills. Practice note.

## What makes it look wrong

- Solid fills and gradients: the pattern is the colour
- Dots all the same size and colour
- Presenting a machine-made picture as authentic Gond art

## Tested demo

This is the look from `art-forms/looks-folk.js`, which `tests/art_forms/check_looks.mjs` draws in a real browser: it must paint, change over time, and give the same pixels when the same time is drawn twice. View it: open `art-forms/gallery.html?look=gond` through a local server. The helpers it calls (`held`, `frameOf`, `jit`, `hash`, `grain`, `prog`, the easings) are at the top of `art-forms/looks.js`. Take the technique, not the picture.

```js
  gond: { kind: '2d', fps: 8, draw(g, t, W, H) {
    // a bird and a tree on a light ground, every part filled with bands of dots and dashes in bright colours, thin black outlines, a dotted border
    const ts = held(t, 8), f = frameOf(t, 8); bg(g, W, H, '#fbf1d3'); g.lineCap = 'round'; g.lineJoin = 'round';
    const k0 = prog(ts, 0, 0.8); g.strokeStyle = INK; g.lineWidth = 3; strokePart(g, [[16, 16], [W - 16, 16], [W - 16, H - 16], [16, H - 16], [16, 16]], k0); g.lineWidth = 1.6; strokePart(g, [[24, 24], [W - 24, 24], [W - 24, H - 24], [24, H - 24], [24, 24]], k0);
    g.fillStyle = INK; for (let i = 0; i < 60 * k0; i++) { const x = 40 + i * ((W - 80) / 60); for (const y of [34, H - 34]) { g.beginPath(); g.arc(x, y, 2.2, 0, TAU); g.fill(); } }
    dots(g, [34, 40, W - 34, H - 40], 24, 1.8, 'rgba(210,160,70,.55)');   // the ground is dotted too
    const shape = (pts, st, ang, seed, lw = 3.2) => folkShape(g, pts, { start: st, dur: 0.6, fill: ['#ffe9b8', '#ffd9c9', '#e6f2cf', '#dfe6f7'][seed % 4], lw, pattern: (c, bb) => gondBands(c, bb, ang, seed) }, ts);
    for (let i = 0; i < 3; i++) shape(leaf(470, 300, 200, 34, -0.35 + i * 0.4), 1.0 + i * 0.12, -0.35 + i * 0.4, i + 2);   // tail feathers
    shape(ellipseLine(340, 305, 168, 96, -0.1), 0.2, -0.1, 0);   // body
    shape(leaf(250, 290, 130, 36, -2.45), 0.7, -2.45, 1);   // neck
    shape(ellipseLine(205, 205, 40, 36), 0.9, 0.4, 4);
    for (const [dx, st] of [[0, 1.5], [-18, 1.6], [18, 1.7]]) shape(leaf(205 + dx * 0.3, 172, 44, 10, -1.57 + dx * 0.025), st, -1.57, 3, 2.6);   // crest
    shape(closed([[0, 0], [1, 0.25], [0, 0.5]], 4).map(([x, y]) => [172 - x * 62, 202 + y * 22]), 1.4, 0, 1, 2.8);   // beak
    if (prog(ts, 1.6, 0.2) > 0.5) { disc(g, 208, 198, 8, '#fff', 2.6); disc(g, 206, 198, 3.6, INK); }
    for (const [x, st] of [[300, 1.8], [372, 1.9]]) { g.strokeStyle = INK; g.lineWidth = 4; strokePart(g, [[x, 395], [x - 8, 440], [x - 24, 478]], prog(ts, st, 0.4)); g.fillStyle = INK; for (let i = 0; i < 8 * prog(ts, st + 0.2, 0.4); i++) { g.beginPath(); g.arc(x + 9 - i * 4.2 + (i % 2) * 4, 410 + i * 9, 2.2, 0, TAU); g.fill(); } }   // legs, with a row of dots beside each
    shape(leaf(790, 480, 270, 20, -1.6), 1.9, -1.6, 5);   // the tree
    for (const [by, d, st] of [[400, -1, 2.3], [400, 1, 2.35], [340, -1, 2.45], [340, 1, 2.5], [285, -1, 2.6], [285, 1, 2.65]]) { const a = d < 0 ? -2.5 : -0.64; shape(leaf(790, by, 120, 22, a), st, a, 3 + (by % 4), 3); }
    for (let i = 0; i < 5; i++) { const a = -1.57 + (i - 2) * 0.42; shape(leaf(790, 230, 90, 18, a), 2.7 + i * 0.05, a, i + 1, 3); }
    const sun = prog(ts, 0.1, 0.8); shape(ellipseLine(112, 100, 38, 38), 0.1, 0.3, 1);
    g.fillStyle = INK; for (let r of [52, 62]) for (let i = 0; i < 16 * sun; i++) { const a = (i / 16) * TAU + (r > 55 ? 0.2 : 0); g.beginPath(); g.arc(112 + Math.cos(a) * r, 100 + Math.sin(a) * r, 2.6, 0, TAU); g.fill(); }
    speckle(g, W, H, 8, 40, [140, 100, 60]);
  } }
```

To use a look in a HyperFrames composition, drive it from the timeline the way `references/threejs.md` shows: a paused GSAP timeline tweens a plain object's `t` from 0 to the duration with `ease: "none"`, and `onUpdate` calls `draw` with that `t`. Vendor GSAP and three.js into the project first.

## Sources

- <https://en.wikipedia.org/wiki/Gond_people>
- <https://en.wikipedia.org/wiki/Jangarh_Singh_Shyam>

Facts checked on 2026-11-21. Lines marked "practice note" are working advice, not sourced facts.
