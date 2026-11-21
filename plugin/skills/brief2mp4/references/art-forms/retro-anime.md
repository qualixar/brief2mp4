# Retro anime (80s and 90s)

Also called: 80s anime, 90s anime, retro cel anime.

Family: Drawn and painted. Cadence: steps 8 times a second. Usual tool: HyperFrames (canvas), or Blender with a toon material for 3D.

A hand-painted television look: hard two-tone shading, banded sunset skies, a striped sun, a lit skyline, a figure from behind with hair and scarf in the wind, a little film grain and a soft glow.

Anime is animation originating from Japan; a characteristic art style emerged in the 1960s and spread in the following decades. Traditional animation paints the characters on transparent cels laid over a static painted background, a process generally credited to Earl Hurd, who patented it in 1914.

## What makes it read as this

- Hard-edged two-tone shading: one base colour and one shadow colour, no soft gradients on the characters
- Banded, graded skies in stepped colour: violet to magenta to orange to cream
- A big sun with horizontal slits, a lit skyline, a rim of warm light on the edges
- Characters seen from behind or in profile, hair and scarf moving in the wind
- Film grain, and a soft bloom around bright areas

## Timing

Drawn on threes: about 8 changes a second inside a 24 frames-a-second film. The sun rises slowly, windows twinkle and hair streams.

## How to build it

- Quantise time with `held(t, 8)` and key every flicker to `frameOf(t, 8)`
- Sky: eight flat bands from `fillRect`; the sun is a clipped disc with a hard shadow tone and slits cut across it
- Shade a character with a base polygon and a second polygon of the shadow colour on one side
- Bloom: a radial gradient drawn with `lighter` over the picture; grain: a speckle with a seed from `frameOf(t, 8) % 6`

## Assets

All in code. For real character art, paint on layers and keep the shadow tone as its own layer. Use only pictures, footage and music the user owns or may reuse; if the user has an image model available, generate textures and cut-out parts with it and say so in REPORT.md.

## Sound and pacing

A synth pad and a drum machine, city ambience, wind on the rooftop. Practice note.

## What makes it look wrong

- Smooth gradients on the figures: the shading is hard-edged
- Smooth 24 frames-a-second motion on every layer, which loses the television feel
- Copying a recognisable character

## Tested demo

This is the look from `art-forms/looks-toon.js`, which `tests/art_forms/check_looks.mjs` draws in a real browser: it must paint, change over time, and give the same pixels when the same time is drawn twice. View it: open `art-forms/gallery.html?look=retro-anime` through a local server. The helpers it calls (`held`, `frameOf`, `jit`, `hash`, `grain`, `prog`, the easings) are at the top of `art-forms/looks.js`. Take the technique, not the picture.

```js
  'retro-anime': { kind: '2d', fps: 8, draw(g, t, W, H) {
    // an 80s or 90s cel look: hard two-tone shading, banded sunset sky and a striped sun, a lit skyline, a figure from behind with hair and scarf in the wind, film grain and a soft bloom
    const ts = held(t, 8), f = frameOf(t, 8), sunY = lerp(440, 255, easeOut(prog(ts, 0, 3.2)));
    bg(g, W, H, '#ffe9a0');   // every pixel is repainted each frame, so the same time always gives the same picture
    ['#1d0b3d', '#3b1366', '#6a1b8a', '#b3237f', '#e8505b', '#ff8a3d', '#ffc15a', '#ffe9a0'].forEach((c, i) => { g.fillStyle = c; g.fillRect(0, i * 54, W, 56); });
    for (let i = 0; i < 26; i++) if ((f + i) % 5) { const x = hash(i, 1) * W, y = hash(i, 2) * 160, r = 1.5 + hash(i, 3) * 2; g.fillStyle = '#fff6d8'; g.fillRect(x - r, y - 0.5, 2 * r, 1); g.fillRect(x - 0.5, y - r, 1, 2 * r); }
    g.save(); g.beginPath(); g.arc(480, sunY, 140, 0, TAU); g.clip(); g.fillStyle = '#ffe27a'; g.fillRect(0, 0, W, H); g.fillStyle = '#ffb347'; g.fillRect(0, sunY + 12, W, H);   // the sun: a hard shadow tone below
    for (let k = 0; k < 7; k++) { g.fillStyle = '#ff8a3d'; g.fillRect(0, sunY + 24 + k * 19, W, 2.5 + k * 2.4); } g.restore();   // slits of sky cut across it
    const city = (base, minH, maxH, col, win, seed, step) => { for (let x = -10, i = 0; x < W; x += step * (0.7 + hash(i, seed) * 0.8), i++) { const w = 34 + hash(i, seed + 1) * 52, h = minH + hash(i, seed + 2) * (maxH - minH); g.fillStyle = col; g.fillRect(x, base - h, w, h + 60); if (hash(i, seed + 3) > 0.6) g.fillRect(x + w / 2 - 1, base - h - 26, 2, 26); if (win) for (let wy = base - h + 10; wy < base - 8; wy += 15) for (let wx = x + 7; wx < x + w - 8; wx += 12) if (hash(wx | 0, wy | 0, seed) > 0.5 && (f + wx) % 13 !== 0) { g.fillStyle = '#ffd35a'; g.fillRect(wx, wy, 5, 7); g.fillStyle = col; } } };
    city(430, 40, 120, '#4a1a6e', true, 11, 58); city(470, 28, 78, '#1b0b2e', true, 21, 70);
    g.fillStyle = '#0f0620'; g.fillRect(0, 462, W, 80); g.fillStyle = '#ff8a3d'; g.fillRect(0, 462, W, 3);   // the rooftop, with a rim of sunset light
    const bloom = g.createRadialGradient(480, sunY, 20, 480, sunY, 330); bloom.addColorStop(0, 'rgba(255,220,130,.5)'); bloom.addColorStop(1, 'rgba(255,160,90,0)'); g.save(); g.globalCompositeOperation = 'lighter'; g.fillStyle = bloom; g.fillRect(0, 0, W, H); g.restore();
    const hx = 300, by = 470, sway = Math.sin(ts * 3) * 6; g.save(); g.translate(hx, by); g.scale(1.45, 1.45);
    polyFill(g, [[-40, -150], [40, -150], [32, -70], [-32, -70]], '#2f4bb5'); polyFill(g, [[6, -150], [40, -150], [32, -70], [6, -70]], '#1e327f');
    g.fillStyle = '#10102a'; g.fillRect(-28, -72, 24, 72); g.fillRect(4, -72, 24, 72);
    for (let i = 0; i < 3; i++) polyFill(g, [[26, -186], [70 + i * 26 + sway * (i + 1), -194 + i * 14 + Math.sin(ts * 4 + i) * 7], [110 + i * 30 + sway * 2, -170 + i * 18], [28, -170 + i * 8]], '#1b1b3a');   // hair streaming in the wind
    disc(g, 0, -184, 32, '#1b1b3a'); g.fillStyle = '#4a56a0'; g.beginPath(); g.arc(0, -184, 32, Math.PI * 1.15, Math.PI * 1.65); g.arc(0, -178, 24, Math.PI * 1.65, Math.PI * 1.15, true); g.fill();
    path(g, Array.from({ length: 12 }, (_, i) => [34 + i * 14 + sway * i * 0.2, -146 + Math.sin(ts * 5 + i * 0.7) * 9 - i * 1.5])); g.lineWidth = 12; g.strokeStyle = '#e8363f'; g.lineJoin = 'round'; path(g, Array.from({ length: 12 }, (_, i) => [34 + i * 14 + sway * i * 0.2, -146 + Math.sin(ts * 5 + i * 0.7) * 9 - i * 1.5]), false); g.stroke();   // the scarf
    g.restore();
    speckle(g, W, H, 40 + (f % 6), 55, [255, 240, 220]);
  } }
```

To use a look in a HyperFrames composition, drive it from the timeline the way `references/threejs.md` shows: a paused GSAP timeline tweens a plain object's `t` from 0 to the duration with `ease: "none"`, and `onUpdate` calls `draw` with that `t`. Vendor GSAP and three.js into the project first.

## Sources

- <https://en.wikipedia.org/wiki/Anime>
- <https://en.wikipedia.org/wiki/Cel>

Facts checked on 2026-11-21. Lines marked "practice note" are working advice, not sourced facts.
