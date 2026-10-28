# ClayStory V32 — approved cinematic narrator as the production default

**Selected voice:** British male en-GB-RyanNeural, using exactly the voice
and story-delivery settings previously tested in V31. You approved that
narration for future animations. This integration makes it the **default
for new audio**, not merely an optional downloadable comparison.

## What changes

- The normal `scripts/generate_narration.py` pipeline imports V31's
  `generate_edge` and `PROFILES["cinematic"]`, including its dramatic
  per-scene tempo, emphasis, sentence breaks and quiet pauses.
- Newly generated scenes in **Māui and the Great Fish**, **Māui and the Sun**,
  **the three six-scene templates**, and **new custom scripts** all use the
  same cinematic narrator by default.
- Existing narration mixers recalculate segment durations from the actual
  MP3 clips, rebuild voice/effects mixes, and save timing manifests for
  featured and custom/template stories.
- The website fetches those measured timing manifests and refreshes its
  audio URL when the player checks for narration. This avoids the previous
  situation where Safari could replay an old cached NZ voice.
- `--reuse-voice` still deliberately retains existing audio; metadata
  will not falsely claim that remixed old audio is a new Ryan performance.
- No silent fallback: a failure of the selected voice causes the build
  to fail rather than producing the old narrator under a success label.

## How to generate future animations on iPad

1. Open [Generate ClayStory neural narration](https://github.com/fanisswag654/claystory-ai/actions/workflows/narration.yml).
2. Tap **Run workflow**. Select **cinematic** in the Narrator dropdown (the default).
3. Choose `fish` for the original Great Fish, or `all` to regenerate
   both featured stories and other templates, or to add a **custom_script**.
4. When GitHub Actions finishes, load the
   [ClayStory player](https://fanisswag654.github.io/claystory-ai/), tap
   **Check narration** and preview. The new narrated film should use the
   approved voice with synchronized visual scene timing.
5. Review each new story's te reo Māori pronunciation, narration, captions
   and cultural accuracy before posting anything publicly.

## Voice options

- `cinematic`: **default**, en-GB-RyanNeural, exactly the approved V31 voice.
- `warm`: optional, en-US-ChristopherNeural, documentary male narrator.
- `nz`: optional legacy en-NZ-MitchellNeural for featured stories; legacy
  en-US-GuyNeural for existing template/custom story paths.

Command line example:

    python scripts/generate_narration.py --story all --narrator cinematic

Set `CLAYSTORY_NARRATOR=warm` or `nz` only if you explicitly want to
change the default in a non-Action local script. The GitHub Actions narrator
choice is explicit.

## Instagram and cultural safeguards

The earlier approved Instagram video is held at its immutable original
GitHub Release URL and remains unchanged. Re-rendering a new cinematic
version produces a **new fingerprint**. The
`config/instagram-approved.json` allowlist hasn't been modified, so
the new version cannot automatically be queued or posted until reviewed
and separately approved.

The voice is a British-English model, not a trained Māori-language narrator.
A fluent te reo Māori speaker should check names and culturally specific
words; none of the settings guarantee correct pronunciation.

## Tests and validation

- `scripts/test_v32_narration_default.py` checks the default cinematic
  selection, all story types including custom scripts, metadata recording,
  and explicit legacy voice fallback without making network requests.
- The [narration workflow](https://github.com/fanisswag654/claystory-ai/actions/workflows/narration.yml)
  runs these regression tests before synthesizing audio.
- The [animation quality workflow](https://github.com/fanisswag654/claystory-ai/actions/workflows/animation-quality.yml)
  verifies scene rendering and deterministic frames after a rebuild.

If a run fails, inspect the logs and don't interpret new narration as live
until the deploy job completes successfully.
