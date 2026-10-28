# ClayStory V31 — distinct cinematic narration and full video review

The previous V30 workflow could finish with a green checkmark even when
Chatterbox Nano did **not** generate its optional audio. The main animation
also kept playing the original en-NZ-MitchellNeural narrator. It could therefore
sound unchanged despite a successful workflow run.

V31 creates a genuinely different **review-only** full-length film using the
original Māui and the Great Fish animation and script.

## New voices

- **cinematic (default):** `en-GB-RyanNeural`, a male UK voice. More suspenseful
  pacing, scene-specific speed/pitch adjustments and longer pauses before
  major reveals. This is the first voice to review.
- **warm:** `en-US-ChristopherNeural`, a different male US voice with a warmer
  documentary-style pacing profile.
- **kokoro (optional):** the open-source
  [Kokoro](https://github.com/hexgrad/kokoro) 82M British male
  `bm_george` preset. CPU installation and model downloads can be slower and
  may require more memory; if it fails, the workflow turns **red** rather than
  providing only the old voice.

The chosen alternate voice is **not** represented as New Zealand English.
None of these voices guarantees an older man's timbre or reliable te reo
Māori pronunciation. Review with a fluent speaker before posting.

## What the new workflow produces

[**V31 cinematic narrator + full preview film**](https://github.com/fanisswag654/claystory-ai/actions/workflows/v31-narrator-film.yml)

The workflow generates **all eight scenes** of alternate narration; compares
the generated files with the old clips to reject identical output; rebuilds
the full narrated MP3, sound effects mixes, and timing metadata; and finally
renders a complete portrait 9:16 video using the unchanged ClayStory V29
animation code. Nothing is committed to the repository's production `audio/`
or posted to Buffer/Instagram. All audio changes occur in a disposable
GitHub Actions checkout without write credentials.

A successful run must generate **eight new clips and a usable MP4**. It
cannot silently fall back to the existing NZ narrator.

### How to watch on iPad

1. Open the V31 workflow link above and select the latest green run.
2. Scroll to **Artifacts** and download **claystory-v31-improved-narration-film**.
3. Unzip the folder in Files.
4. Play **fish-nz-V31-cinematic-REVIEW.mp4** (or the selected warm/Kokoro
   equivalent). This is a new fully synchronized narration/video.
5. You can compare the **scene-1-ORIGINAL-NZ.mp3** and
   **scene-6-ORIGINAL-NZ.mp3** files with the new files ending
   **-new-narration.mp3**.
6. Review the Māori pronunciations and story's cultural context before
   authorizing a different soundtrack for the Instagram account.

If the workflow is red, open its failed step's logs; do not interpret an
uploaded partial artifact as a completed new film.

### Why Chatterbox was not automatically made the default

Chatterbox Nano is an English-only, heavy CPU model and its default voice
does not guarantee a deeper storyteller or correct Māori pronunciation.
The earlier V30 workflow deliberately treated Nano failures as optional,
which could misleadingly leave only the original clips. V31 selects a
different voice **explicitly**, supports a second open-source engine, and
requires the full candidate generation and video export to succeed before
showing green.

## Files

- `scripts/v31_storyteller.py`: independent scene synthesis, scene-specific
  prosody and paragraph pauses, optional Kokoro, strict no-fallback checks.
- `scripts/test_v31_storyteller.py`: voice differentiation, Māori text
  integrity, output safety and duplicate-audio safeguards.
- `.github/workflows/v31-narrator-film.yml`: synthesis, remix, rendering
  and temporary seven-day audio/video artifact.
- `v31-voice-preview.trigger`: starts a single first comparison run.

Your **previously approved** Instagram Reel and its historical release
remain unchanged. New narration requires your review before publication.
