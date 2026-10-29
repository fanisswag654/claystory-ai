# ClayStory AI V32

A static Canvas animation player for 9:16 short films. Open `index.html` through
an HTTP server; no JavaScript build is required. Great Fish is the default.

## Great Fish visual styles

Pixel remains the default and the main finished-film style. The **Great Fish
visual style** selector also offers **Woodblock — style test**: separate animated
canvas artwork with ink contours, parchment grain, carved waves, Aotearoa
headlands and a rising North Island. It keeps the Māori narrative and shares the
same narration, eight-scene timeline and spoken captions. You can switch while
Preview plays without restarting audio. The Sun story keeps its Pixel artwork.

Woodblock currently supports Preview and compatible browsers' silent WebM
recording. Photos MP4 downloads remain Pixel; select Pixel to enable that button.
The renderer is inline in `index.html`, uses standard Canvas 2D, and needs no
external artwork, fonts, network calls or additional deployment assets.


## Instagram Reels automation

This repository now owns the Instagram workflow directly. The [Instagram Reels
workflow](.github/workflows/instagram-reels.yml) checks the original animated
films produced by ClayStory, and (after an Instagram Professional account and
Buffer API key are configured) queues one new Reel at a time. It does not use
TikTok, the old clip-farmer repository or Minecraft footage. Content hashes
prevent repeated scheduling of unchanged videos. See
[INSTAGRAM_AUTOMATION.md](INSTAGRAM_AUTOMATION.md) for setup, safe tests and
cultural review requirements.

## New automation — WhatsApp video approval before Instagram

ClayStory now contains a **disabled-by-default** weekly workflow for
source-grounded new Māori pūrākau. It drafts new narration from a curated
source library through a separately billed OpenAI API, renders a fresh
cinematic V31-voice and V33-style 9:16 pixel animation, and sends the
**actual finished MP4** to the account owner's WhatsApp via Meta's approved
video-message template.

The owner can tap **Approve** or **Reject** in WhatsApp. An authenticated
webhook verifies the sender and template button response, signs the result
and triggers a separate GitHub workflow. **No reply or Reject means NO
Instagram upload.** Approve verifies the exact original MP4 SHA-256 and
posts it to @purakaupixel through the existing Buffer integration, with
duplicate prevention. The system only uses sourced briefs, not invented
sacred narratives, and the user must check cultural accuracy and pronunciation.

**External setup is not finished yet.** It needs Meta WhatsApp Business
credentials/template, a confirmed Render workspace for the webhook, and
GitHub Actions secrets. Until an end-to-end test and the explicit
`PURAKAU_AUTOMATION_ENABLED=true` switch, no scheduled posts occur.

Full setup: [WHATSAPP_AUTOMATION_SETUP.md](WHATSAPP_AUTOMATION_SETUP.md).
Workflows: [generate and request approval](.github/workflows/auto-purakau-review.yml),
[process WhatsApp decision](.github/workflows/auto-purakau-decision.yml),
[offline tests](.github/workflows/auto-purakau-tests.yml).

## New original film — Tāne and the First Light

**V33 detailed-character upgrade:** The Tāne film now features a separate
procedural character rig with distinct Tāne/Tāwhirimātea palettes, detailed
faces, blinking, expressive arms, a realistic bracing pose, clothing depth
and multiple keyed frames for all the main actions. The
[Tāne review workflow](.github/workflows/tane-first-light.yml) exports a
**tane-nz-V33-detailed.mp4** and an enlarged **character studies PNG**.
See [V33_DETAILED_CHARACTERS.md](V33_DETAILED_CHARACTERS.md) and the
[mobile-ready browser preview](tane.html). Hand-painted PNG sprite sheets
from Pixelorama are the next optional art step, not a dependency on V33.

A separate eight-scene **Tāne and the First Light** animation has been added
with original 9:16 pixel visuals: Ranginui and Papatūānuku's dark embrace,
the atua's debate, Tāne pushing the sky upward, an explosive dawn,
Tāwhirimātea's storm and forests flourishing afterward.

The [new film review workflow](.github/workflows/tane-first-light.yml)
synthesizes the approved V31 cinematic Ryan narrator for the new story,
creates an original nature soundscape, renders a synchronized H.264/AAC MP4
at 540×960 and 24fps, and attaches eight scene stills. No Instagram/Buffer
post is created, and only the existing approved fish Reel stays on the
Instagram allowlist. Review the video and te reo Māori pronunciation before
approving any public post. Story sources, full creative details and iPad
instructions are in [TANE_FIRST_LIGHT.md](TANE_FIRST_LIGHT.md).

## V32 production default — approved cinematic narrator

The storyteller voice you preferred in V31 is now the **default for future
ClayStory narration**: British male **en-GB-RyanNeural** with the same
scene-by-scene dramatic pacing, deliberate pauses, and gentle audio mastering
used in the reviewed V31 film. This applies to Great Fish, Māui and the Sun,
three template stories, and new scripts passed to the narration GitHub workflow.
Scene timings are calculated from the newly generated voice instead of fixed
eight-second assumptions, and the player refreshes audio URLs to avoid old
iPad Safari sound caches.

Run [Generate ClayStory neural narration](.github/workflows/narration.yml)
and select `story=all` for new custom scripts. The narrator defaults to
`cinematic`; `warm` and the previous `nz` voice are optional.
From the command line, use
`python scripts/generate_narration.py --story all --narrator cinematic`.
No narrator is silently substituted if the selected provider fails. Note that
Māori names and words still require pronunciation review.

Your previously approved Instagram Reel's versioned video is **not altered**.
As before, new source/video fingerprints are not automatically authorized for
Instagram publication. See [V32_NARRATION_DEFAULT.md](V32_NARRATION_DEFAULT.md)
for testing and fallback details.

## V31 distinctly new cinematic narrator + complete preview film

V31 generates a **genuinely different voice** (default: British male Ryan
Neural, with scene-by-scene expressive pacing), rebuilds the complete
narration and synchronized effects, and creates a **full-length 9:16 MP4**
for review. It also supports warm US male Christopher Neural and the
optional open-source Kokoro George male voice. Unlike the optional Nano
run, the V31 workflow **cannot show a green result while outputting only
the old NZ clips**: all 8 new scenes and the final video must succeed.
No production narration is committed and nothing is posted to Instagram.
Open the [V31 candidate film workflow](.github/workflows/v31-narrator-film.yml)
or read [V31_NARRATION.md](V31_NARRATION.md) for iPad instructions and
cultural pronunciation-review requirements.

## V30 optional Chatterbox Nano voice comparison

ClayStory now has a separate GitHub Actions workflow that compares its approved
en-NZ-MitchellNeural narrator with an experimental **Chatterbox Nano** CPU
narrator for selected Māori story scenes. The test reads the original story,
generates downloadable MP3 comparisons and a listening page, and does **not**
replace the live animation soundtrack, change scene timings or post to Instagram.
The model is English-only, so Māori names and pronunciation require fluent
review. If the model cannot run on GitHub's free runner, the NZ narrator remains
unchanged. See [V30_NARRATION.md](V30_NARRATION.md) and the
[voice-comparison workflow](.github/workflows/v30-voice-preview.yml) for setup,
iPad review and limitations.

## V29 animation system — Tween.js + frame-based pixel poses

ClayStory now loads a **local MIT-licensed Tween.js v25** engine and a deterministic
sprite-action library. The Great Fish film has eased cinematic camera motion,
frame-based Māui walking, point/pull/reaction poses, coordinated paddle strokes,
swimming fish tail/fin animation and smoother scene transitions. All movement
uses absolute narration time, so browser previews and Playwright/FFmpeg exports
remain synchronized. The procedural sprite frames can later be replaced with
transparent sprite sheets authored in Pixelorama; Pixelorama images have not
yet been imported. Read [V29_ANIMATION.md](V29_ANIMATION.md) for full
architecture, testing, integration details and iPad preview steps.

## V28 animation improvements (Great Fish)

The new pixel renderer adds visibly different facial reactions (panic, surprise,
awe and determined effort), stronger tugging arm/leg poses, animated fin rays,
shifting fish-scale highlights, moving gills, underwater caustics and cinematic
water/sunlight particles during the hook, breach and island transformation.
All effects are deterministic functions of film time and should render identically
in Preview and exported video. The original reviewed Instagram film remains
available as a versioned release; changes to this version require a new review
before public posting. The [animation quality workflow](.github/workflows/animation-quality.yml)
checks JavaScript syntax and the eight-scene browser playback tests.

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

Run browser checks from the repository root with the HTTP server on port 8000:

```sh
/workspace/.venv/bin/python scripts/test_player.py
/workspace/.venv/bin/python scripts/test_subtitles.py
/workspace/.venv/bin/python scripts/test_fish_film.py
/workspace/.venv/bin/python scripts/test_woodblock.py
```

The Woodblock test checks all eight compositions, deterministic frames, live
style switching without audio restart, the shared captions, and Sun isolation.
