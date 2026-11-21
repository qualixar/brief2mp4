/*
 * stage.js: a small 2D stage. It puts a backdrop, a cast of rigged characters and captions in one frame, all as a
 * pure function of time, in the skin the scene names.
 *
 *   const stage = B2M.createStage(scene, cast);       // cast: { child: <character>, ... }
 *   stage.draw(ctx2d, t);                             // or stage.items(t) for the display list (SVG backend, tests)
 *
 * scene = {
 *   width, height, skin, ground,                      // ground: the y where feet stand
 *   palette: { sky, hill1, hill2, ground, sun },      // backdrop colours; every skin restyles them
 *   hills: [{ pts: [[x, y], ...], fill: "hill1" }],   // optional silhouettes behind the cast
 *   set:   [{ type: "circle", c: [x, y], r: 90, fill: "sun", layer: "back" }],   // optional shapes (same records as a character part);
 *                                                     // layer "back" draws behind the hills, the default "front" on the ground
 *   cast:  [{ id, character, x, y, scale, facing, track }],   // x, y: where its feet are (y defaults to the ground top, so feet are never hidden); track as in rig.js, visemes included;
 *                                                       // a move key's x and y are absolute and replace x and y while it plays
 *   captions: [{ from, to, text }] }              // at the bottom, or at the top when a character stands there
 */
(function (g) {
  'use strict';
  if (typeof require === 'function' && !(g.B2M && g.B2M.SKINS)) require('./index.js');
  const B = (g.B2M = g.B2M || {});
  const IDENT = [1, 0, 0, 1, 0, 0];

  function styled(scene, skin, shape, tag, frame) {
    const d = B.shapePath(shape);
    const ctx = { character: { id: 'scene', palette: scene.palette }, part: { id: tag }, shape, d, posed: { cycles: [] }, skin, frame, seed: 'scene:' + tag, color: (k) => scene.palette[k] || B.DEFAULT_PALETTE[k] || '#ff00ff', bounds: () => B.pathBounds(d) };
    return skin.shape(ctx).map((p) => Object.assign({ kind: 'path', part: tag, m: IDENT }, p));
  }

  function backdrop(scene, skin, frame) {
    const W = scene.width, H = scene.height, rect = B.rectPath(0, 0, W, H, 0);
    const items = (skin.sky ? skin.sky({ W, H, rect, color: (k) => scene.palette[k] || '#ffffff' }) : [{ d: rect, fill: scene.palette.sky, stroke: null }])
      .map((p) => Object.assign({ kind: 'path', part: 'sky', m: IDENT }, p));
    const setItems = (layer) => (scene.set || []).forEach((sh, i) => { if ((sh.layer || 'front') === layer) items.push(...styled(scene, skin, Object.assign({ role: 'base' }, sh), 'set' + i, frame)); });
    setItems('back');
    (scene.hills || []).forEach((h, i) => {
      const pts = h.pts.concat([[W + 40, H + 40], [-40, H + 40]]);
      items.push(...styled(scene, skin, { type: 'poly', pts, smooth: false, fill: h.fill, role: 'base', shade: false }, 'hill' + i, frame));
    });
    items.push(...styled(scene, skin, { type: 'rect', x: -40, y: scene.ground, w: W + 80, h: H - scene.ground + 40, r: 0, fill: 'ground', role: 'base', shade: false }, 'ground', frame));
    setItems('front');
    return items;
  }

  // Where a cast member stands when its track's move keys say nothing, and which way it faces to begin with.
  function homeOf(c, scene) {
    return { x: c.x, y: c.y === undefined ? scene.ground : c.y, flip: c.facing === 'left' ? -1 : c.facing === 'right' ? 1 : c.flip === undefined ? 1 : c.flip };
  }

  function captionAt(scene, t) {
    const c = (scene.captions || []).find((k) => t >= k.from && t < k.to);
    return c ? c.text : '';
  }

  // Where a character is on screen: the box round everything it draws (rods and speed lines are not part of it).
  function boxOf(items) {
    let b = null;
    items.forEach((it) => {
      if (it.kind !== 'path' || it.part === 'fx' || it.part === 'rod' || !it.d) return;
      const q = B.pathBounds(B.mapPoints(it.d, (x, y) => [it.m[0] * x + it.m[2] * y + it.m[4], it.m[1] * x + it.m[3] * y + it.m[5]]));
      b = b ? { x0: Math.min(b.x0, q.x0), y0: Math.min(b.y0, q.y0), x1: Math.max(b.x1, q.x1), y1: Math.max(b.y1, q.y1) } : q;
    });
    return b;
  }

  const overlaps = (r, b) => b && r.x0 < b.x1 && r.x1 > b.x0 && r.y0 < b.y1 && r.y1 > b.y0;

  // The caption goes at the bottom of the frame, or at the top when it would cover a character.
  function defaultCaption(scene, text, boxes) {
    if (!text) return [];
    const W = scene.width, H = scene.height, w = Math.min(W - 160, 80 + text.length * 25), x = (W - w) / 2;
    const bottom = { x0: x, x1: x + w, y0: H - 150, y1: H - 66 }, top = { x0: x, x1: x + w, y0: 54, y1: 138 };
    const hit = (r) => boxes.filter((b) => overlaps(r, b)).length;
    const r = hit(bottom) > 0 && hit(top) < hit(bottom) ? top : bottom;
    return [{ kind: 'path', part: 'caption', m: IDENT, d: B.rectPath(r.x0, r.y0, w, 84, 18), fill: 'rgba(20,16,28,0.72)', stroke: null },
      { kind: 'text', part: 'caption', m: IDENT, x: W / 2, y: r.y0 + 58, text, align: 'center', font: '700 40px "Helvetica Neue", Arial, sans-serif', fill: '#ffffff' }];
  }

  function createStage(scene, cast) {
    const skin = B.SKINS[scene.skin];
    if (!skin) throw new Error('unknown skin "' + scene.skin + '". Skins: ' + Object.keys(B.SKINS).join(', '));
    const opts = { steps: skin.steps, smooth: !skin.steps };
    function items(t) {
      const ts = B.quantise(t, skin.steps), frame = skin.steps ? Math.round(ts * skin.steps) : 0;
      const out = backdrop(scene, skin, frame), text = captionAt(scene, t);
      const boxes = [], order = scene.cast.slice().sort((a, b) => (a.y === undefined ? scene.ground : a.y) - (b.y === undefined ? scene.ground : b.y));
      order.forEach((c) => {
        const ch = cast[c.character], home = homeOf(c, scene), posed = B.pose(ch, c.track, t, Object.assign({ home, scale: c.scale || 1 }, opts));
        const drawn = B.layout(ch, skin, posed, { x: home.x, y: home.y, scale: c.scale || 1 });
        out.push(...drawn);
        if (text) boxes.push(boxOf(drawn));
      });
      const over = skin.foreground ? skin.foreground({ W: scene.width, H: scene.height, caption: text, t, scene }) : [];
      return out.concat(over, skin.captions ? [] : defaultCaption(scene, text, boxes));
    }
    function draw(g2, t) {
      g2.setTransform(1, 0, 0, 1, 0, 0);
      g2.clearRect(0, 0, scene.width, scene.height);
      B.drawCanvas(g2, items(t));
    }
    return { items, draw, skin };
  }

  Object.assign(B, { createStage, homeOf });
  if (typeof module !== 'undefined' && module.exports) module.exports = B;
})(globalThis);
