# DepthFlow motion and VoiceStudio assessment

The cinematic workflow now offers `depthflow` (default) and `gentle-pan`.
DepthFlow estimates depth from each verified original still and renders a
continuous, restrained camera move per scene. Narration timing determines the
exact frame count. Captions, original sound, 1080×1920 H.264/AAC export,
SHA-verified Telegram review and approval-only Instagram publication still use
the existing pipeline. DepthFlow does not generate character movement.

## Free CPU test

`DepthFlow — free CPU parallax test` runs on a standard Ubuntu Actions runner
with Mesa software OpenGL, CPU PyTorch and Depth Anything V2 Small. It needs no
secrets and cannot publish or message Telegram. Its two-second 1080×1920 preview
checks model downloads, headless OpenGL, encoding and the exact frame count.
Each scene renders in an isolated process to avoid upstream shader-state reuse errors.
Software rendering can be slow; check the measured test result before relying
on full-resolution production. The production workflow allows 90 minutes and
fails if DepthFlow fails; it never silently substitutes a static image.

On an iPad: GitHub → Actions → cinematic stills and Christopher → Run workflow
→ choose the story and `depthflow`. `gentle-pan` remains available if needed.
Only approve the new finished MP4 after watching it, especially faces and moko.
A rendering upgrade never transfers approval from an older video.

Dependencies: Python 3.12; `automation/requirements-depthflow.txt`; CPU torch
installed first from the official PyTorch CPU index. DepthFlow and ShaderFlow
are pinned. DepthFlow uses AGPL-3.0; the Small depth model uses Apache-2.0.
Sources: https://github.com/BrokenSource/DepthFlow and
https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf .

## VoiceStudio narrator (active)

New films use **Bruno**, the built-in male preset `expr-voice-3-m`, through
VoiceStudio's actual `KittenTTSBackend`. The application source is checked out
at `429f1e5bb2703ac5b928ab8ba6f60159167e9c44`. The 80 MB
`KittenML/kitten-tts-mini-0.8` model runs on CPU inside GitHub Actions;
no hosted backend, credential, paid API, voice clone or iPad installation is
required. Model weights are Apache-2.0; VoiceStudio is AGPL-3.0.

We compared the same passage across all four male presets: Bruno had the
lowest median voiced pitch in that test (about 117 Hz). This is a measured
property of the generated sample, not a guarantee of perceived quality.
Speed is 0.92 with 0.35-second sentence pauses. No pitch-shift filter is used.
Every scene's duration is measured from its new MP3 before captions and film
rendering. The previous Christopher narrator remains eligible only as a known
narrator for SHA-bound private reviews already issued.

KittenTTS is English-only; Māori words still require fluent human review.
Do not infer cultural pronunciation accuracy from successful rendering.
Telegram Approve still authorizes only the exact new MP4. Earlier approvals
never authorize an updated soundtrack or a newly rendered video.

ONNX Runtime telemetry is disabled before process/library initialization with
`ORT_DISABLE_TELEMETRY=1`, and through its API. VoiceStudio analytics and HF
telemetry are also disabled. Only the selected public model downloads are
needed for speech generation. Output routes through VoiceStudio's
`mark_synthetic` hook; its optional AudioSeal behavior remains upstream's.

The `VoiceStudio — free CPU male narrator test` workflow creates a short real
Bruno sample without Telegram, Buffer, publishing permissions or secrets.
The cinematic workflow installs this same pinned backend for all eight scenes.

Sources:
- https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/kittentts.md
- https://huggingface.co/KittenML/kitten-tts-mini-0.8
- https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md
