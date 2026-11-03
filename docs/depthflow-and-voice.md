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

## VoiceStudio

https://github.com/debpalash/VoiceStudio supports local speech generation,
voice design and voice cloning, plus a headless backend and automation APIs.
It is usable as a separate narration backend; it is not a hosted free TTS API.
Its server/model needs its own execution environment. CPU execution is
supported but may be slow. The repository also offers an iPad preview app
requiring signing/sideloading, which is optional for our cloud workflow.

The accepted `en-US-ChristopherNeural` narrator stays in production. Before
switching to VoiceStudio, choose a model and permitted voice, test a deep calm
male sample and Māori pronunciation, then integrate the measured scene audio
into `make_audio.py`. New timing must come from the actual generated files.
VoiceStudio app licensing is AGPL-3.0; each model and voice has separate terms.
No paid OpenAI API is needed. No voice is cloned automatically.

Inspected upstream sources: README.md, docs/speech-platform.md and the project's
current local speech platform documentation (2026-11-03).
