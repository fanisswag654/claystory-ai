# Pūrākau Pixels V33 — detailed animated characters

The Tāne and the First Light film now draws its atua using a dedicated, fully original, frame-sampled pixel-character renderer. This changes the actual character artwork, rather than applying a filter to the existing image.

## What's different

- **Tāne:** forest-green layered mantle, leaf highlights, dark hair, warm face, expressive hands and realistic bracing pose.
- **Tāwhirimātea:** dark storm-blue outfit, flowing scarf, blue-white accents and stronger animated wind gestures.
- **Three differently styled brothers:** earth, ochre and river palettes with individual movements, shapes and expressions.
- **Faces:** layered swaying hair, raised/furrowed eyebrows, highlights, blinking eyes, noses and different animated speaking, determined, surprised, angry and joyful mouth shapes.
- **Actions:** idle, listen, argue, reach, strain, push, wonder, storm. Each movement has several explicitly authored animation poses.
- **Better body mechanics:** Tāne lies along the earth with planted hands, bending knees and feet pushing up against the sky.
- **Larger character closeups:** debate, failed attempts and sky separation show more readable expressions and gestures.
- **Stable renders:** every pose is a function of absolute narration time; reverse scrubbing and frame-by-frame MP4 rendering remain deterministic.

## New/updated files

- scripts/tane_characters.js — original palettes, articulated movements and expressions.
- scripts/tane_animation.js — updated eight-scene choreography.
- tane.html — browser/iPad preview page, now loads detailed actors.
- scripts/test_tane_characters_browser.py — test that animation frames actually change and reverse scrubbing stays stable.
- scripts/render_tane.py — exports a large character-study PNG plus all eight stills and the fully narrated video.

## iPad review

1. Open the Tāne film workflow: https://github.com/fanisswag654/claystory-ai/actions/workflows/tane-first-light.yml
2. Once the **new** run shows green, download the **tane-first-light-review-film** artifact and extract it in Files.
3. Play **tane-nz-V33-detailed.mp4**. Inspect **tane-v33-character-studies.png** for enlarged facial, clothing and gesture details.
4. After the Pages deployment succeeds, preview interactive scenes at https://fanisswag654.github.io/claystory-ai/tane.html . The web preview may be silent until its soundtrack is separately deployed; the review MP4 includes narration and sound.
5. Review te reo Māori pronunciation and cultural interpretation before authorizing any public post.

## GitHub repositories that can improve the characters next

- **Pixelorama**: https://github.com/Orama-Interactive/Pixelorama — preferred next step for drawing professional layered, frame-by-frame sprites. It has a web version suitable to try on iPad. Export 48×64 or 64×96 transparent PNG frames/sprite sheets for each character.
- **LibreSprite**: https://github.com/LibreSprite/LibreSprite — free editor for traditional pixel-animation frames, mainly on desktop.
- **PixiJS**: https://github.com/pixijs/pixijs — for a more extensive later renderer upgrade: layered compositing, GPU effects and sprite batching. Not necessary for V33.
- **Tween.js**: https://github.com/tweenjs/tween.js — already included in ClayStory V29 for eased camera motion and transitions.

V33 does **not** claim Pixelorama, LibreSprite or PixiJS are installed in the player. It uses an original procedural sprite rig with a documented action/role API that can be swapped for future Pixelorama export assets. No borrowed or copyrighted game art has been added.

## Cultural design

These are symbolic imaginative illustrations, not representations of a specific iwi's customary attire. No tā moko or sacred carving patterns were invented. Māori names and story details should be reviewed by a fluent/culturally knowledgeable speaker prior to publication.

**Instagram safeguards:** The already-approved original Māui Reel remains unchanged. Tāne is review-only and is not added to Instagram's approval allowlist.
