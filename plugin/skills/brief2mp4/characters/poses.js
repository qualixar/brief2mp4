/*
 * poses.js: the pose and cycle library for the character kit. Data only, no logic that reads a clock.
 *
 * Angles are degrees. For arms, hands and legs, a positive angle swings the limb FORWARD (the way the character
 * faces); for the torso, head, brows and feet a positive angle turns clockwise on screen (lean forward, toe down).
 * A joint can also be an object { r, x, y, sx, sy } (rotation, offset in units, scale). Joints a pose leaves out
 * stay at rest (0). `lift` moves the whole body up (negative) or down (positive) as a fraction of the leg length,
 * so one pose fits a child and an adult.
 */
(function (g) {
  'use strict';
  const B = (g.B2M = g.B2M || {});

  const VISEMES = ['rest', 'AI', 'E', 'O', 'U', 'MBP', 'FV', 'L', 'etc'];

  const POSES = {
    idle: { armN_up: 6, armN_lo: 14, handN: 8, armF_up: -6, armF_lo: 10, handF: 6, legN_up: 2, legN_lo: -2, legF_up: -3, legF_lo: -1 },
    wave: { torso: -3, head: -4, armN_up: 96, armN_lo: 52, handN: -6, armF_up: -6, armF_lo: 10, browN: { r: -6, y: -2 }, smile: 0.7, mouth: 'E' },
    point: { torso: 5, head: 5, armN_up: 86, armN_lo: 4, handN: 0, armF_up: -12, armF_lo: 12, legN_up: 6, legF_up: -6, smile: 0.2 },
    sit: { lift: 0.46, torso: 2, head: 2, armN_up: 28, armN_lo: 62, handN: 10, armF_up: 18, armF_lo: 70, legN_up: 88, legN_lo: -88, legF_up: 84, legF_lo: -86, footN: 0, footF: 0 },
    'run-ready': { lift: 0.14, torso: 22, head: -8, armN_up: -48, armN_lo: 82, handN: 10, armF_up: 42, armF_lo: 84, handF: 10, legN_up: 42, legN_lo: -52, legF_up: -34, legF_lo: -34, browN: { r: 4 } },
    jump: { lift: -0.28, torso: -4, head: -6, armN_up: 150, armN_lo: 12, armF_up: 138, armF_lo: 14, legN_up: 52, legN_lo: -72, legF_up: 24, legF_lo: -64, footN: 8, footF: 12, smile: 0.8, mouth: 'O' },
    surprised: { lift: -0.04, torso: -9, head: -7, armN_up: 44, armN_lo: 46, handN: -8, armF_up: 30, armF_lo: 56, browN: { r: -10, y: -7 }, browF: { r: -10, y: -7 }, eyeN: { sx: 1.25, sy: 1.25 }, eyeF: { sx: 1.25, sy: 1.25 }, mouth: 'O', gaze: [0.4, 0] },
    sad: { torso: 11, head: 20, armN_up: 5, armN_lo: 10, handN: 14, armF_up: -2, armF_lo: 8, handF: 12, browN: { r: 14, y: 1 }, browF: { r: 14, y: 1 }, eyeN: { sy: 0.8 }, eyeF: { sy: 0.8 }, smile: -1, gaze: [0.1, 0.6] },
    laugh: { lift: -0.02, torso: -13, head: -10, armN_up: 22, armN_lo: 44, handN: 10, armF_up: 12, armF_lo: 50, browN: { r: -6 }, eyeN: { sy: 0.45 }, eyeF: { sy: 0.45 }, mouth: 'AI', smile: 1 },
    think: { torso: 3, head: 8, armN_up: 52, armN_lo: 128, handN: 24, armF_up: 22, armF_lo: 96, handF: 8, browN: { r: -10, y: -3 }, browF: { r: 6 }, gaze: [0.5, -0.6], smile: -0.1 },
    'fight-ready': { lift: 0.18, torso: 12, head: 4, armN_up: 72, armN_lo: 96, handN: 14, armF_up: 54, armF_lo: 102, handF: 14, legN_up: 30, legN_lo: -36, legF_up: -30, legF_lo: -22, browN: { r: 8 }, browF: { r: 8 }, smile: -0.3, mouth: 'etc' },
    bow: { lift: 0.03, torso: 56, head: 24, armN_up: 16, armN_lo: 8, armF_up: 6, armF_lo: 10, eyeN: { sy: 0.18 }, eyeF: { sy: 0.18 }, smile: 0.4 },
    strike: { lift: 0.14, torso: 22, head: 8, armN_up: 102, armN_lo: -8, handN: 0, armF_up: -42, armF_lo: 40, legN_up: 46, legN_lo: -12, legF_up: -46, legF_lo: -16, browN: { r: 10 }, browF: { r: 10 }, mouth: 'AI', smile: -0.2 },
    hurt: { lift: -0.03, torso: -22, head: -16, armN_up: -42, armN_lo: 24, armF_up: -30, armF_lo: 30, legN_up: -12, legF_up: 18, eyeN: { sy: 0.3 }, eyeF: { sy: 0.3 }, browN: { r: 16 }, browF: { r: 16 }, mouth: 'O', smile: -1 },
    cheer: { lift: -0.1, torso: -5, head: -6, armN_up: 160, armN_lo: 10, armF_up: 150, armF_lo: 12, legN_up: 14, legF_up: -10, mouth: 'AI', smile: 1, eyeN: { sy: 0.6 }, eyeF: { sy: 0.6 } },
  };

  // Which way a positive angle turns each limb joint. Characters may override with a part's own "sign".
  const SIGN = { armN_up: -1, armN_lo: -1, handN: -1, armF_up: -1, armF_lo: -1, handF: -1, legN_up: -1, legN_lo: -1, legF_up: -1, legF_lo: -1 };

  const rad = (d) => (d * Math.PI) / 180;
  const pos = (x) => Math.max(0, x);

  // A cycle is N drawings. fn(phase) gives joint offsets (added to the pose) for phase 0..1.
  const CYCLES = {
    walk: {
      frames: 8, steps: 8, lean: 4, amp: 28,
      fn(p) {
        const a = 2 * Math.PI * p, s = Math.sin(a), c = Math.cos(a);
        return {
          legN_up: 28 * s, legF_up: -28 * s, legN_lo: -46 * pos(c), legF_lo: -46 * pos(-c),
          armN_up: -22 * s, armF_up: 22 * s, armN_lo: 8 + 8 * pos(-s), armF_lo: 8 + 8 * pos(s),
          footN: 8 * pos(-c) * s, footF: -8 * pos(c) * s, torso: 3, head: -1, tail: 4 * Math.sin(a * 2),
          hip: { y: -4 * Math.abs(c) },
        };
      },
    },
    run: {
      frames: 6, steps: 12, lean: 10, amp: 52,
      fn(p) {
        const a = 2 * Math.PI * p, s = Math.sin(a), c = Math.cos(a);
        return {
          legN_up: 52 * s, legF_up: -52 * s, legN_lo: -84 * pos(c), legF_lo: -84 * pos(-c),
          armN_up: -50 * s, armF_up: 50 * s, armN_lo: 70, armF_lo: 70,
          footN: 10 * pos(-c), footF: 10 * pos(c), torso: 10, head: -5, tail: 8 * Math.sin(a * 2),
          hip: { y: -16 * Math.abs(s) },
        };
      },
    },
    wave: {
      frames: 4, steps: 6,
      fn(p) { const s = Math.sin(2 * Math.PI * p); return { armN_lo: 26 * s, handN: 18 * s }; },
    },
    laugh: {
      frames: 4, steps: 8,
      fn(p) { const s = Math.sin(2 * Math.PI * p); return { torso: 4 * s, head: -3 * s, hip: { y: -5 * Math.abs(s) } }; },
    },
    breath: {
      frames: 8, steps: 4, smooth: true,
      fn(p) { const s = Math.sin(2 * Math.PI * p); return { torso: { sy: 0.012 * s }, head: 0.8 * s, hip: { y: 0.8 * s } }; },
    },
  };

  // Mouth shapes: w is the half width, open is how far the lips part (0 closed to 1 wide), round pulls the corners in.
  const VISEME_SHAPE = {
    rest: { w: 0.78, open: 0, round: 0, teeth: 0 },
    AI: { w: 1.0, open: 1.0, round: 0.1, teeth: 0.4, tongue: 1 },
    E: { w: 1.2, open: 0.34, round: 0, teeth: 1 },
    O: { w: 0.55, open: 0.86, round: 1, teeth: 0 },
    U: { w: 0.38, open: 0.42, round: 1, teeth: 0 },
    MBP: { w: 0.78, open: 0, round: 0, teeth: 0, press: 1 },
    FV: { w: 0.95, open: 0.2, round: 0, teeth: 1, lip: 1 },
    L: { w: 0.9, open: 0.55, round: 0, teeth: 1, tongue: 1 },
    etc: { w: 0.88, open: 0.3, round: 0, teeth: 0.7 },
  };

  Object.assign(B, { VISEMES, POSES, SIGN, CYCLES, VISEME_SHAPE, rad });
  if (typeof module !== 'undefined' && module.exports) module.exports = B;
})(globalThis);
