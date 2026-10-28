# ClayStory V30 — Chatterbox Nano narrator comparison

**Status: experimental and review-only.** The existing NZ narrator continues to power production preview, rendered film, Instagram scheduling and the approved Reel.

This upgrade integrates open-source Chatterbox Nano from https://github.com/resemble-ai/chatterbox as an **optional CPU text-to-speech candidate**. The existing en-NZ-MitchellNeural / Edge TTS remains the working default.

## Implemented

- scripts/v30_voice.py reads all original spoken story passages directly from index.html (8 Great Fish scenes, 6 Sun scenes).
- Existing NZ voice MP3s are copied unmodified for comparison. The optional model uses ChatterboxTurboTTS.from_pretrained(device="cpu", nano=True), a built-in voice, and light audio leveling.
- The GitHub Actions workflow produces MP3 samples for Great Fish scenes 1 and 6 (or Sun scenes 1 and 5), a local audio review page called listen.html, and comparison.json with measured durations.
- The model is only installed in the **voice-comparison workflow**, not the normal animation, narration or Instagram posting workflows.
- No production voice, voice manifests, captions, effects mixes, videos or Instagram posts are replaced or created.
- Optional voice cloning is supported only with --reference-wav **and** --consent-confirmed for an authorized speaker. No private voice sample is included with this project.

## Listen on iPad

1. Open https://github.com/fanisswag654/claystory-ai/actions/workflows/v30-voice-preview.yml
2. Tap **Run workflow**, choose fish and nano. The default opt-in model selection will try Chatterbox Nano on the GitHub runner's CPU.
3. Open the finished workflow run, scroll to **Artifacts**, and download **claystory-v30-voice-comparison**.
4. Unzip the artifact in Files on iPad and play the MP3s. The optional listen.html page will display both samples if its adjacent relative audio files load.
5. Compare naturalness, storytelling emotion, consistency, Māori names and pronunciation. Do not approve a synthetic voice without a fluent te reo Māori review.

**Important:** Chatterbox Nano is English-only and does not guarantee a New Zealand accent or correct Māori pronunciation. Its built-in voice is not guaranteed to sound like an older man. The CPU setup downloads substantial ML dependencies and may be slow or fail on a free GitHub runner. The workflow preserves the original NZ voice and reports model failure without changing live outputs.

**Artifact visibility:** This repository is public; GitHub Actions artifacts may be visible/downloadable to others with repo access. Do not upload confidential speaker recordings. Artifacts expire after 7 days.

## Local tests (no model required)

    python scripts/v30_voice.py --story fish --engine nano --dry-run
    python -m unittest discover -s scripts -p 'test_v30_voice.py' -v

## Optional local CPU inference

    python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 torchaudio==2.6.0
    python -m pip install chatterbox-tts==0.1.7
    python scripts/v30_voice.py --story fish --scenes 1 6 --engine nano --output-dir voice-previews

Upstream Chatterbox code uses MIT licensing. Check the selected model weights and any reference speaker's authorization before using it commercially.

## After review

Once a candidate voice is approved, the next phase is producing all scene narrations separately, rebuilding timing and mixed soundtracks, rendering a complete candidate MP4, and reviewing it before authorizing a new Instagram version. This comparison workflow does not automatically promote anything.
