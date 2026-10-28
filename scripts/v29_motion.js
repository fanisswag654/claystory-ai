/*
 * ClayStory V29 — Tween.js-powered timeline motion + frame-based pixel sprites.
 *
 * The actor/paddle cycles are authored as reusable named frames, so an artist
 * can later replace the procedural body art with sprite sheets from Pixelorama.
 * No wall-clock or random state: every pose is sampled from absolute film time,
 * giving identical frames in iPad Preview and headless MP4 export.
 *
 * Requires local MIT-licensed vendor/tween.umd.js v25.0.0.
 */
(function (root) {
  'use strict';

  if (!root.TWEEN || !root.TWEEN.Tween || !root.TWEEN.Easing) {
    throw new Error('ClayStory V29 requires vendor/tween.umd.js');
  }

  const easingMap = Object.freeze({
    linear: root.TWEEN.Easing.Linear.None,
    smooth: root.TWEEN.Easing.Cubic.InOut,
    cinematic: root.TWEEN.Easing.Quintic.InOut,
    out: root.TWEEN.Easing.Cubic.Out,
    back: root.TWEEN.Easing.Back.Out,
  });

  const registry = Object.freeze({
    paddle: Object.freeze({
      fps: 8,
      // Vertical blade dip, shoulder rotation, and ocean-surface interaction.
      frames: Object.freeze([
        {swing:-10,blade:-8,shoulder:-4,bob:0},
        {swing:-6,blade:-5,shoulder:-3,bob:-1},
        {swing:0,blade:0,shoulder:0,bob:-2},
        {swing:7,blade:8,shoulder:3,bob:-1},
        {swing:12,blade:12,shoulder:5,bob:0},
        {swing:7,blade:10,shoulder:3,bob:1},
        {swing:2,blade:5,shoulder:1,bob:1},
        {swing:-5,blade:0,shoulder:-2,bob:0},
      ]),
    }),
    walk: Object.freeze({
      fps: 9,
      frames: Object.freeze([
        {stride:0,arm:2,bob:0,lean:0},
        {stride:3,arm:4,bob:-1,lean:1},
        {stride:6,arm:7,bob:-2,lean:2},
        {stride:3,arm:5,bob:-1,lean:1},
        {stride:0,arm:0,bob:0,lean:0},
        {stride:-3,arm:-4,bob:-1,lean:-1},
        {stride:-6,arm:-7,bob:-2,lean:-2},
        {stride:-3,arm:-5,bob:-1,lean:-1},
      ]),
    }),
    pull: Object.freeze({
      fps: 7,
      frames: Object.freeze([
        {tug:0,arm:-3,leg:-2,bob:0,lean:0},
        {tug:-3,arm:-5,leg:-5,bob:1,lean:-2},
        {tug:-7,arm:-8,leg:-8,bob:3,lean:-5},
        {tug:-10,arm:-9,leg:-10,bob:4,lean:-6},
        {tug:-4,arm:-4,leg:-5,bob:2,lean:-3},
        {tug:2,arm:1,leg:0,bob:0,lean:1},
      ]),
    }),
    point: Object.freeze({
      fps: 5,
      frames: Object.freeze([
        {reach:0,bob:0},
        {reach:4,bob:-1},
        {reach:7,bob:-2},
        {reach:4,bob:-1},
      ]),
    }),
    surprise: Object.freeze({
      fps: 6,
      frames: Object.freeze([
        {reach:0,bob:0},
        {reach:4,bob:-2},
        {reach:9,bob:-4},
        {reach:6,bob:-3},
        {reach:2,bob:-1},
      ]),
    }),
    swim: Object.freeze({
      fps: 9,
      frames: Object.freeze([
        {tail:-9,fin:-3,bob:0,gill:0},
        {tail:-6,fin:0,bob:-1,gill:1},
        {tail:0,fin:4,bob:-2,gill:2},
        {tail:8,fin:7,bob:-2,gill:1},
        {tail:13,fin:5,bob:-1,gill:0},
        {tail:7,fin:1,bob:0,gill:1},
        {tail:0,fin:-3,bob:1,gill:2},
        {tail:-7,fin:-5,bob:1,gill:1},
      ]),
    }),
  });

  // Tween.js is evaluated against an explicit 0–1000ms timeline on every call.
  // Crucially, these tweens are never tied to Date.now, rAF or a mutable Group:
  // scrubbing backwards and out-of-order FFmpeg snapshots remain deterministic.
  function tween(from, to, progress, easing = 'smooth') {
    const current = Object.assign({}, from);
    const interpolator = new root.TWEEN.Tween(current)
      .to(to, 1000)
      .easing(easingMap[easing] || easingMap.smooth)
      .start(0);
    interpolator.update(Math.max(0, Math.min(1000, progress * 1000)));
    return current;
  }

  function spriteFrame(action, timeSeconds, phaseOffset = 0) {
    const animation = registry[action];
    if (!animation) throw new Error('Unknown ClayStory sprite action: ' + action);
    const frameCount = animation.frames.length;
    const frame = ((Math.floor((timeSeconds + phaseOffset) * animation.fps) %
      frameCount) + frameCount) % frameCount;
    return animation.frames[frame];
  }

  function frameIndex(action, timeSeconds, phaseOffset = 0) {
    const animation = registry[action];
    if (!animation) throw new Error('Unknown ClayStory sprite action: ' + action);
    return ((Math.floor((timeSeconds + phaseOffset) * animation.fps) %
      animation.frames.length) + animation.frames.length) % animation.frames.length;
  }

  root.ClayMotionV29 = Object.freeze({
    version: 29,
    tween,
    spriteFrame,
    frameIndex,
    registry,
    easing: easingMap,
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
