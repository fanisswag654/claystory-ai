# ClayStory AI V18

A static Canvas animation player for 9:16 short films. Open `index.html` through
an HTTP server; no JavaScript build is required. Great Fish is the default.

## Development

```sh
python -m venv --system-site-packages /workspace/.venv
/workspace/.venv/bin/pip install 'edge-tts>=7,<8'
python -m http.server 8000 --bind 127.0.0.1
```

FFmpeg and ffprobe must be on PATH. From the repository root, regenerate eight
Great Fish clips, the continuous narration, synthesized original effects, three
voice/effects mixes and duration manifest:

```sh
/workspace/.venv/bin/python scripts/generate_narration.py --story fish
```

The default `--story all` also regenerates Māui and the Sun, the three original
six-scene templates, and an optional `CUSTOM_SCRIPT`. `--reuse-voice` remixes
existing matching scene clips without contacting the speech service. Never use
six old fish clips as substitutes for the new eight-scene performance.

The narration workflow runs on player/generator changes and supports manual
dispatch. It commits audio before deploying the static site using GitHub Pages
Actions. The repository must permit Actions deployments to `github-pages`.
Generation requires access to `speech.platform.bing.com`. A failed audio run
prevents deployment of a partial soundtrack. The player rejects a fish timing
manifest unless it has eight durations and revision 18.

## Film and audio

The eight Great Fish scenes have their own underwater, shore, hiding, discovery,
hook, catch, rising-fish and island sequences. Scene cuts follow measured MP3
lengths with 0.15-second gaps; the narration targets 85–100 seconds. Playback
uses the audio clock, including the speed selector. Original synthesized effects
are baked into soft, balanced and bold MP3 mixes for iPad Safari. Disabling FX
selects narration only. The volume slider selects one of the three mixes on the
next preview. Recorded narration upload remains available; recordings should
match the scene timings. Uploaded recordings take precedence over mixed audio.

The New Zealand male synthetic voice is not verified te reo Māori pronunciation.
A fluent speaker should review the narration or supply a recording. No ritual
steps are illustrated or invented. This is one telling of the pūrākau, not a
claim to represent every iwi tradition. All pixel art and synthesized effects
are original; no Terraria assets are used.

Save film to Photos prepares a pre-rendered portrait H.264/AAC MP4 for either
featured story, with soft/balanced/bold effects or voice only. Tap Share video,
then Save Video on iPad. A download fallback supports Files → Share → Save Video.
The browser cannot write to Photos without this system share action. Finished
MP4s use the original story at normal speed; edits and uploaded audio affect
Preview only. Silent WebM recording remains available.

`python scripts/render_films.py` renders both featured films into ignored
`videos/` outputs. It requires Playwright Chromium and FFmpeg. The narration
workflow renders and deploys those MP4s after generating audio.
Physical iPad testing and fluent-speaker pronunciation review remain necessary.
