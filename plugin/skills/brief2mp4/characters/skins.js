/*
 * skins.js: the same rig in different art forms. A skin is a style map plus per-frame effect hooks:
 *
 *   id, name      the art-form page it follows (references/art-forms/<id>.md)
 *   steps         drawings per second for handmade looks, null for smooth looks (pass it to B2M.pose as opts.steps)
 *   shape(ctx)    turns one shape of one part into 1..n drawing primitives (fill, outline, shadow, wobble)
 *   character(ctx) optional: adds primitives for the whole character after its parts (rods, speed lines)
 *
 * Every wobble comes from B2M.jitterPath, which is seeded by (shape, drawing number): two renders match.
 */
(function (g) {
  'use strict';
  if (typeof require === 'function' && !(g.B2M && g.B2M.layout)) require('./render.js');
  const B = (g.B2M = g.B2M || {});
  const SKINS = {};

  const roleOf = (shape) => shape.role || 'base';
  const lineOf = (ctx, sw, extra) => Object.assign({ d: ctx.d, fill: null, stroke: ctx.color(ctx.shape.stroke || 'ink'), sw: (ctx.shape.sw || 2) * sw, cap: 'round' }, extra);

  // Paper cut-out: flat fills, a tight shadow under every layer, edges that wobble a little on every held drawing.
  const PAPER = '#f3e6c8';
  SKINS['paper-cutout'] = {
    id: 'paper-cutout', name: 'Paper cut-out', steps: 12, bg: '#f3e6c8', ink: '#4a3320', jitter: 0.9,
    shape(ctx) {
      const role = roleOf(ctx.shape), s = ctx.shape;
      const wobble = (d) => B.jitterPath(d, ctx.seed, ctx.frame, role === 'line' ? 0.5 : this.jitter);
      if (role === 'line' || !s.fill) return [lineOf(ctx, 0.9, { d: wobble(ctx.d), stroke: B.mix(ctx.color(s.stroke || 'ink'), '#4a3320', 0.35) })];
      if (role === 'hole') return [{ d: ctx.d, fill: '#fbf5e4', stroke: null }];
      const col = B.mix(ctx.color(s.fill), PAPER, 0.12);
      const shadow = role === 'base' ? { dx: 3, dy: 4, blur: 5, color: 'rgba(70,40,10,0.38)' } : undefined;
      return [{ d: wobble(ctx.d), fill: col, stroke: null, shadow }];
    },
  };

  // Anime / cel shading: an ink outline round every form, light in two hard tones, shadows tinted blue-violet.
  SKINS['cel-shaded'] = {
    id: 'cel-shaded', name: 'Anime and cel shading', steps: 12, bg: '#ffe0b0', ink: '#1b1530',
    shape(ctx) {
      const role = roleOf(ctx.shape), s = ctx.shape, ink = ctx.color('ink');
      if (role === 'line' || !s.fill) return [lineOf(ctx, 1.15)];
      const base = ctx.color(s.fill), b = ctx.bounds(), small = Math.min(b.w, b.h);
      // outline weight follows the size of the shape, so an eye gets a fine line and a torso a bold one
      const sw = base === ink || small < 7 ? 0 : Math.min(3.4, Math.max(1.5, small * 0.07));
      const stroke = sw ? ink : null;
      if (role === 'hole') return [{ d: ctx.d, fill: '#ffffff', stroke: ink, sw: 2 }];
      if (role === 'detail' || role === 'mouth') return [{ d: ctx.d, fill: base, stroke: role === 'mouth' && s.fill !== 'mouth' ? null : stroke, sw: Math.min(sw, 1.8) }];
      if (s.shade === false || small < 12) return [{ d: ctx.d, fill: base, stroke, sw }];
      const shade = B.mix(B.mix(base, '#2b2170', 0.38), '#000000', 0.1), lit = B.mix(base, '#ffffff', 0.1);
      const litD = B.mapPoints(ctx.d, (x, y) => [b.cx + (x - b.cx) * 0.8 - b.w * 0.08, b.cy + (y - b.cy) * 0.8 - b.h * 0.1]);
      return [{ d: ctx.d, fill: shade, stroke, sw }, { d: litD, fill: lit, stroke: null }];
    },
  };

  Object.assign(B, { SKINS });
  if (typeof module !== 'undefined' && module.exports) module.exports = B;
})(globalThis);
