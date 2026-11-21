/*
 * render.js: turns a posed character into a display list, and draws the list on a canvas or in SVG.
 *
 *   const items = B2M.layout(character, skin, B2M.pose(character, track, t, { steps: skin.steps }), { x, y, scale });
 *   B2M.drawCanvas(ctx, items);                    // canvas 2D
 *   const svg = B2M.createSVG(document, parent, w, h); svg.update(items);   // HyperFrames DOM / SVG
 *
 * An item is { kind: 'path' | 'text', m: [a, b, c, d, e, f], d, fill, stroke, sw, alpha, shadow, ... }. The list is a
 * plain array of numbers and strings, so the same frame can be compared, hashed or drawn by either backend.
 */
(function (g) {
  'use strict';
  if (typeof require === 'function' && !(g.B2M && g.B2M.shapePath)) require('./shapes.js');
  const B = (g.B2M = g.B2M || {});

  const IDENT = [1, 0, 0, 1, 0, 0];
  const mul = (p, q) => [p[0] * q[0] + p[2] * q[1], p[1] * q[0] + p[3] * q[1], p[0] * q[2] + p[2] * q[3], p[1] * q[2] + p[3] * q[3], p[0] * q[4] + p[2] * q[5] + p[4], p[1] * q[4] + p[3] * q[5] + p[5]];
  const translate = (x, y) => [1, 0, 0, 1, x, y];
  const rotate = (deg) => { const r = B.rad(deg), c = Math.cos(r), s = Math.sin(r); return [c, s, -s, c, 0, 0]; };
  const scaleM = (sx, sy) => [sx, 0, 0, sy, 0, 0];
  const round = (m) => m.map((v) => Math.round(v * 1000) / 1000);

  const INDEX = new WeakMap();
  function indexOf(character) {
    let ix = INDEX.get(character);
    if (ix) return ix;
    const byId = {};
    character.parts.forEach((p, i) => { byId[p.id] = Object.assign({ order: i }, p); });
    const topo = [];
    const seen = new Set();
    const visit = (p) => { if (seen.has(p.id)) return; seen.add(p.id); if (p.parent) visit(byId[p.parent]); topo.push(p); };
    Object.values(byId).forEach(visit);
    const draw = Object.values(byId).sort((a, b) => a.z - b.z || a.order - b.order);
    ix = { byId, topo, draw };
    INDEX.set(character, ix);
    return ix;
  }

  function partMatrices(character, posed, base) {
    const ix = indexOf(character), W = {};
    ix.topo.forEach((p) => {
      const ch = posed.parts[p.id], parent = p.parent ? W[p.parent] : base;
      const local = mul(translate(ch.x, ch.y), mul(translate(p.pivot[0], p.pivot[1]), mul(rotate(ch.r + (ch.jaw || 0)), mul(scaleM(ch.sx, ch.sy), translate(-p.pivot[0], -p.pivot[1])))));
      W[p.id] = mul(parent, local);
    });
    return W;
  }

  function mouthOpen(posed) { return (B.VISEME_SHAPE[posed.viseme] || B.VISEME_SHAPE.rest).open; }

  function shapesOf(character, part, posed) {
    const cfg = part.mouth;
    if (!cfg) return part.shapes;
    if (cfg.kind === 'jaw') return part.shapes;
    return B.lipShapes(cfg, part.pivot, posed.viseme, posed.smile);
  }

  /**
   * @param opts { x, y, scale } where the character stands (feet on the ground at x, y); the pose's own move track is added.
   */
  function layout(character, skin, posed, opts) {
    const o = opts || {}, ix = indexOf(character);
    const flip = posed.move.flip, sc = o.scale || 1;
    const base = mul(translate((o.x || 0) + posed.move.x, (o.y || 0) + posed.move.y), scaleM(sc * flip, sc));
    const work = { parts: {} };
    Object.keys(posed.parts).forEach((id) => {
      const part = ix.byId[id], jaw = part && part.mouth && part.mouth.kind === 'jaw' ? mouthOpen(posed) * (part.mouth.maxOpen || 28) * (part.sign || 1) : 0;
      work.parts[id] = Object.assign({}, posed.parts[id], { jaw });
    });
    const W = partMatrices(character, work, base);
    const items = [];
    const shown = new Set(posed.props);
    ix.draw.forEach((part) => {
      if (part.prop && !shown.has(part.id)) return;
      shapesOf(character, part, posed).forEach((shape, si) => {
        const d = B.shapePath(shape);
        const ctx = { character, part, shape, d, posed, skin, frame: posed.frame, seed: character.id + ':' + part.id + ':' + si, color: (k) => B.colorOf(character, k), bounds: () => B.pathBounds(d) };
        skin.shape(ctx).forEach((prim) => items.push(Object.assign({ kind: 'path', part: part.id, m: round(W[part.id]) }, prim)));
      });
    });
    if (skin.character) skin.character({ character, posed, items, matrices: W, base, push: (it) => items.push(it) });
    return items;
  }

  // Where a part sits on screen at this pose: used for captions, speech bubbles and tests.
  function partPoint(character, posed, opts, partId) {
    const o = opts || {}, flip = posed.move.flip, sc = o.scale || 1;
    const base = mul(translate((o.x || 0) + posed.move.x, (o.y || 0) + posed.move.y), scaleM(sc * flip, sc));
    const W = partMatrices(character, { parts: Object.fromEntries(Object.entries(posed.parts).map(([k, v]) => [k, Object.assign({ jaw: 0 }, v)])) }, base);
    const p = indexOf(character).byId[partId].pivot, m = W[partId];
    return [m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5]];
  }

  // ---- canvas backend ----
  function paint(g2, v, item) {
    if (v && typeof v === 'object') {
      const gr = v.grad === 'radial' ? g2.createRadialGradient(v.cx, v.cy, v.r0 || 0, v.cx, v.cy, v.r) : g2.createLinearGradient(v.x1, v.y1, v.x2, v.y2);
      v.stops.forEach((s) => gr.addColorStop(s[0], s[1]));
      return gr;
    }
    return v;
  }

  function drawCanvas(g2, items) {
    items.forEach((it) => {
      g2.save();
      g2.setTransform(it.m[0], it.m[1], it.m[2], it.m[3], it.m[4], it.m[5]);
      g2.globalAlpha = it.alpha === undefined ? 1 : it.alpha;
      if (it.shadow) { g2.shadowColor = it.shadow.color; g2.shadowBlur = it.shadow.blur; g2.shadowOffsetX = it.shadow.dx; g2.shadowOffsetY = it.shadow.dy; }
      if (it.kind === 'text') {
        g2.font = it.font; g2.textAlign = it.align || 'left'; g2.textBaseline = it.baseline || 'alphabetic';
        if (it.stroke) { g2.strokeStyle = it.stroke; g2.lineWidth = it.sw || 1; g2.lineJoin = 'round'; g2.strokeText(it.text, it.x, it.y); }
        g2.fillStyle = paint(g2, it.fill, it); g2.fillText(it.text, it.x, it.y);
      } else {
        const p = new Path2D(it.d);
        if (it.fill) { g2.fillStyle = paint(g2, it.fill, it); g2.fill(p, it.rule || 'nonzero'); }
        if (it.shadow && it.fill) { g2.shadowColor = 'rgba(0,0,0,0)'; }
        if (it.stroke) { g2.strokeStyle = it.stroke; g2.lineWidth = it.sw || 1; g2.lineCap = it.cap || 'round'; g2.lineJoin = it.join || 'round'; g2.stroke(p); }
      }
      g2.restore();
    });
  }

  // ---- SVG backend: a pool of elements, updated in place every frame ----
  const NS = 'http://www.w3.org/2000/svg';
  function createSVG(doc, parent, width, height) {
    const svg = doc.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height); svg.setAttribute('width', width); svg.setAttribute('height', height);
    const defs = doc.createElementNS(NS, 'defs'); svg.appendChild(defs); parent.appendChild(svg);
    const pool = [], gradients = new Map();
    const gradient = (v) => {
      const key = JSON.stringify(v);
      if (!gradients.has(key)) {
        const el = doc.createElementNS(NS, v.grad === 'radial' ? 'radialGradient' : 'linearGradient'), id = 'g' + gradients.size;
        el.setAttribute('id', id); el.setAttribute('gradientUnits', 'userSpaceOnUse');
        const attrs = v.grad === 'radial' ? { cx: v.cx, cy: v.cy, r: v.r } : { x1: v.x1, y1: v.y1, x2: v.x2, y2: v.y2 };
        Object.entries(attrs).forEach(([k, n]) => el.setAttribute(k, n));
        v.stops.forEach((s) => { const st = doc.createElementNS(NS, 'stop'); st.setAttribute('offset', s[0]); st.setAttribute('stop-color', s[1]); el.appendChild(st); });
        defs.appendChild(el); gradients.set(key, id);
      }
      return 'url(#' + gradients.get(key) + ')';
    };
    const paintAttr = (v) => (v && typeof v === 'object' ? gradient(v) : v || 'none');
    function update(items) {
      items.forEach((it, i) => {
        const tag = it.kind === 'text' ? 'text' : 'path';
        let el = pool[i];
        if (!el || el.tagName !== tag) { const n = doc.createElementNS(NS, tag); if (el) svg.replaceChild(n, el); else svg.appendChild(n); pool[i] = el = n; }
        el.style.display = '';
        el.setAttribute('transform', 'matrix(' + it.m.join(' ') + ')');
        el.setAttribute('fill', paintAttr(it.fill)); el.setAttribute('stroke', it.stroke || 'none');
        el.setAttribute('stroke-width', it.sw || 1); el.setAttribute('stroke-linecap', it.cap || 'round'); el.setAttribute('stroke-linejoin', it.join || 'round');
        el.setAttribute('opacity', it.alpha === undefined ? 1 : it.alpha); el.setAttribute('fill-rule', it.rule || 'nonzero');
        el.style.filter = it.shadow ? 'drop-shadow(' + it.shadow.dx + 'px ' + it.shadow.dy + 'px ' + it.shadow.blur / 2 + 'px ' + it.shadow.color + ')' : '';
        if (tag === 'path') el.setAttribute('d', it.d);
        else { el.setAttribute('x', it.x); el.setAttribute('y', it.y); el.setAttribute('style', 'font:' + it.font + ';text-anchor:' + ({ center: 'middle', right: 'end' }[it.align] || 'start')); el.textContent = it.text; }
      });
      for (let i = items.length; i < pool.length; i++) pool[i].style.display = 'none';
    }
    return { svg, update };
  }

  Object.assign(B, { layout, partPoint, drawCanvas, createSVG, matrix: { mul, translate, rotate, scale: scaleM, IDENT } });
  if (typeof module !== 'undefined' && module.exports) module.exports = B;
})(globalThis);
