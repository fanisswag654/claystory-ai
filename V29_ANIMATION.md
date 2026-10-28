# ClayStory V29 — cinematic timing and frame-based animation

This upgrade integrates **the actual MIT-licensed @tweenjs/tween.js v25.0.0**
into the existing 2D Canvas animation player, and introduces an explicit
**frame-based sprite-action system** designed for later art replacement using
[Pixelorama](https://github.com/Orama-Interactive/Pixelorama) exports.

## What changed

- **Camera:** Smooth, deterministic zooms and subtle pans built from Tween.js
  `Cubic` / `Quintic` easing. The big fish reveal uses a quicker ease-out.
- **Māui / waka crew:** Reusable pixel-action cycles for walking, pointing,
  surprise, pulling and eight-frame paddle strokes. Character limbs, canoe
  paddles and reaction gestures change frame by frame.
- **Fish:** An eight-frame swimming cycle drives its tail, fins and vertical
  motion, while retaining the detailed V28 face/scales/gill artwork.
- **Scenes:** Eased waka departure, stowaway reveal, hook descent, approach,
  breach, island transformation and subtle cross-scene fades.
- **Deterministic export:** No `Date.now`, `Math.random`, requestAnimationFrame
  dependencies or mutable tween update groups are used for film frames.
  Every pose and camera value is sampled from **absolute narration time**.
  This preserves pause, seeking, iPad preview and Playwright/FFmpeg export.

## Files

| File | Purpose |
|---|---|
| `vendor/tween.umd.js` | Locally hosted, unmodified upstream Tween.js 25 UMD bundle with a brief license header |
| `vendor/TWEEN_LICENSE.txt` | Upstream MIT license and attribution |
| `scripts/v29_motion.js` | Six named sprite cycles, frame sampler and Tween.js time sampler |
| `index.html` | Scene and character renderer using the new animation engine |
| `scripts/test_v29_motion.py` | Browser tests for easing, sprite frames, reverse seeking and repeatable pixel frames |
| `.github/workflows/animation-quality.yml` | Automated JavaScript and browser regression checks |
| `.github/workflows/narration.yml` | Copies the local JS dependencies into GitHub Pages alongside the player |
| `scripts/instagram_reels.py` | Includes both new JS files when fingerprinting exported film versions |

## Preview on an iPad

1. Wait for [the narration/deployment workflow](https://github.com/fanisswag654/claystory-ai/actions/workflows/narration.yml)
   to finish successfully, so that all V29 JavaScript assets are served.
2. Open [ClayStory AI](https://fanisswag654.github.io/claystory-ai/) and reload
   the page; the heading should show **V29 TWEEN CAMERA & ANIMATED SPRITES**.
3. Tap **Load Great Fish story**, then **Preview with sound**.
4. See [animation-quality tests](https://github.com/fanisswag654/claystory-ai/actions/workflows/animation-quality.yml).
   If they fail, inspect the logs before treating V29 as ready.

## Pixelorama-compatible next step

Today's V29 animation cycles are **procedurally drawn poses**, not imported
Pixelorama PNG frames. They are indexed and organized like sprite sheets, which
makes it easier to substitute artwork later without changing the narration
timeline. In Pixelorama, author transparent frames for Māui in matching
walking/paddling/pulling/expressions poses, export the PNG sprite sheet, then
replace the corresponding render logic using the same
`ClayMotionV29.spriteFrame(action,time)` timing API. The full character
sheet and Pixelorama's native project file have **not** been generated yet.

## Instagram release safeguards

The previously approved Great Fish video remains a *versioned original
release*. V29 changes the source fingerprint, so it creates a new film version
rather than silently replacing the approved Reel. Only source hashes explicitly
listed in `config/instagram-approved.json` can be scheduled for public Instagram
publishing. Review the updated animation and te reo Māori narration before
approving a V29 release.

## Licensing

Tween.js is MIT licensed, copyright Tween.js authors; see
`vendor/TWEEN_LICENSE.txt`. This repository's original Māori storytelling,
animations and artwork remain separate from that dependency.
