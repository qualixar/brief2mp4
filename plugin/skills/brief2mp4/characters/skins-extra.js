/*
 * skins-extra.js: four more skins on the same rig, written like the first two (see skins.js for the contract).
 *
 *   line-art         strokes only: one weight of line on a plain ground, the line boils on every held drawing
 *   shadow-puppet    black leather silhouettes with punched holes, visible rods, a warm lamp behind
 *   motion-comic     flat colour, a bold ink line, halftone dots for shadow, a panel border and a caption box
 *   flat-explainer   clean flat vector: fills only, smooth motion, no outline and no shadow
 *
 * A skin may also give the stage `sky(ctx)` (the background) and `foreground(ctx)` (anything drawn over everything).
 */
(function (g) {
  'use strict';
  if (typeof require === 'function' && !(g.B2M && g.B2M.SKINS)) require('./skins.js');
  const B = (g.B2M = g.B2M || {});
  const { roleOf, lineOf } = B.skinKit;
  const SKINS = B.SKINS;
  const lum = (hex) => B.toRgb(hex).reduce((a, b) => a + b, 0);

  // ---- line art ----
  const LINE_INK = '#151515', LINE_BG = '#fffdf8';
  SKINS['line-art'] = {
    id: 'line-art', name: 'Line art', steps: 10, bg: LINE_BG, ink: LINE_INK, jitter: 1.3,
    shape(ctx) {
      const role = roleOf(ctx.shape), s = ctx.shape;
      if (role === 'cel' || role === 'hole' || s.fill === 'blush') return [];
      const d = B.jitterPath(ctx.d, ctx.seed, ctx.frame, role === 'line' ? 0.7 : this.jitter);
      if (role === 'line' || !s.fill) return [{ d, fill: null, stroke: LINE_INK, sw: 3, cap: 'round' }];
      const size = Math.min(ctx.bounds().w, ctx.bounds().h), dot = size < 14 && lum(ctx.color(s.fill)) < 200;
      return [{ d, fill: dot ? LINE_INK : LINE_BG, stroke: LINE_INK, sw: role === 'detail' || role === 'mouth' ? 1.6 : Math.min(3.2, Math.max(1.5, size * 0.09)) }];
    },
    sky: (c) => [{ d: c.rect, fill: LINE_BG, stroke: null }],
  };

  // ---- shadow puppet ----
  const LEATHER = '#150b06', LAMP = '#f4b862', ROD = '#2c180a';
  const screenPoint = (m, p) => [m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5]];
  function rods(ctx) {
    const ix = ctx.character.parts.reduce((o, p) => { o[p.id] = p; return o; }, {}), out = [];
    const rod = (from, to, w) => out.push({ kind: 'path', part: 'rod', m: [1, 0, 0, 1, 0, 0], d: 'M' + B.fmt(from[0]) + ' ' + B.fmt(from[1]) + 'L' + B.fmt(to[0]) + ' ' + B.fmt(to[1]), fill: null, stroke: ROD, sw: w, cap: 'butt' });
    if (ix.torso) { const a = screenPoint(ctx.matrices.torso, ix.torso.pivot); rod([a[0], a[1] - 30], [a[0], 1400], 6); }
    ['handN', 'handF'].forEach((h) => {
      if (!ix[h]) return;
      const a = screenPoint(ctx.matrices[h], ix[h].pivot), dir = ctx.posed.move.flip;
      rod(a, [a[0] + 70 * dir, a[1] + 420], 3.5);
    });
    out.reverse().forEach((it) => ctx.under(it));
  }

  SKINS['shadow-puppet'] = {
    id: 'shadow-puppet', name: 'Shadow puppetry', steps: 12, bg: '#e8a24e', ink: LEATHER,
    shape(ctx) {
      const role = roleOf(ctx.shape), s = ctx.shape;
      if (role === 'cel') return [];
      if (role === 'line') return [lineOf(ctx, 1.25, { stroke: LEATHER })];
      if (!s.fill) return [];
      // light colours, an open mouth and the small decorative shapes (pockets, plackets, stripes) are punched out of the leather
      const punched = lum(ctx.color(s.fill)) > 690 || (role === 'mouth' && s.fill === 'mouth') || (role === 'detail' && s.fill !== 'blush' && s.fill !== 'skin3');
      return [{ d: ctx.d, fill: punched ? LAMP : LEATHER, stroke: null }];
    },
    character: rods,
    sky: (c) => [{ d: c.rect, fill: { grad: 'radial', cx: c.W / 2, cy: c.H * 0.55, r0: 40, r: c.W * 0.62, stops: [[0, '#ffd27a'], [0.55, '#e08a3a'], [1, '#4a210a']] }, stroke: null }],
  };

  // ---- motion comic ----
  const HALFTONE = { pattern: 'halftone', id: 'b2m-halftone', size: 8, dots: [[2, 2, 1.7, 0, 'rgba(16,16,16,0.6)'], [6, 6, 1.7, 0, 'rgba(16,16,16,0.6)']] };
  const COMIC_INK = '#101010';
  SKINS['motion-comic'] = {
    id: 'motion-comic', name: 'Motion comic', steps: null, bg: '#f0ead8', ink: COMIC_INK, captions: true,
    shape(ctx) {
      const role = roleOf(ctx.shape), s = ctx.shape;
      if (role === 'cel') return [{ d: ctx.d, fill: HALFTONE, stroke: null }];
      if (role === 'line' || !s.fill) return [lineOf(ctx, 1.1, { stroke: COMIC_INK })];
      if (role === 'hole') return [{ d: ctx.d, fill: '#ffffff', stroke: COMIC_INK, sw: 2 }];
      const small = Math.min(ctx.bounds().w, ctx.bounds().h);
      const sw = ctx.color(s.fill) === ctx.color('ink') || small < 7 ? 0 : Math.min(3.6, Math.max(1.5, small * 0.07));
      return [{ d: ctx.d, fill: ctx.color(s.fill), stroke: sw ? COMIC_INK : null, sw: role === 'detail' || role === 'mouth' ? Math.min(sw, 1.8) : sw }];
    },
    sky: (c) => [{ d: c.rect, fill: c.color('sky'), stroke: null }, { d: c.rect, fill: HALFTONE, stroke: null, alpha: 0.18 }],
    foreground(c) {
      const out = [{ kind: 'path', part: 'panel', m: [1, 0, 0, 1, 0, 0], d: B.rectPath(36, 36, c.W - 72, c.H - 72, 0), fill: null, stroke: COMIC_INK, sw: 14, join: 'miter' }];
      if (c.caption) {
        const w = Math.min(c.W - 200, 60 + c.caption.length * 26);
        out.push({ kind: 'path', part: 'caption', m: [1, 0, 0, 1, 0, 0], d: B.rectPath(80, 80, w, 84, 0), fill: '#ffd23f', stroke: COMIC_INK, sw: 6, join: 'miter' },
          { kind: 'text', part: 'caption', m: [1, 0, 0, 1, 0, 0], x: 104, y: 138, text: c.caption, font: '800 40px "Helvetica Neue", Arial, sans-serif', fill: COMIC_INK });
      }
      return out;
    },
  };

  // ---- flat explainer ----
  SKINS['flat-explainer'] = {
    id: 'flat-explainer', name: 'Flat vector explainer', steps: null, bg: '#f5f7fb', ink: '#1f2a44',
    shape(ctx) {
      const role = roleOf(ctx.shape), s = ctx.shape;
      if (role === 'cel') return [];
      if (role === 'line' || !s.fill) return [lineOf(ctx, 0.9, { stroke: B.mix(ctx.color(s.stroke || 'ink'), '#1f2a44', 0.4) })];
      if (role === 'hole') return [{ d: ctx.d, fill: '#ffffff', stroke: null }];
      return [{ d: ctx.d, fill: ctx.color(s.fill), stroke: null }];
    },
    sky: (c) => [{ d: c.rect, fill: c.color('sky'), stroke: null }],
  };

  B.HALFTONE = HALFTONE;
  if (typeof module !== 'undefined' && module.exports) module.exports = B;
})(globalThis);
