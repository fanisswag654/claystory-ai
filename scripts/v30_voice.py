#!/usr/bin/env python3
"""ClayStory V30 narrator comparison: CPU Chatterbox Nano vs approved NZ voice.

Safe by design:
  * Reads the existing story and committed scene narration.
  * Writes ONLY to a separate preview directory, never to audio/ or Releases.
  * Does NOT modify timing.json, sound mixes, Instagram draft, or auto-publishing.
  * The current en-NZ-MitchellNeural narration is always available as baseline.
  * Chatterbox Nano is English-only. Māori names/words need fluent review.
  * Optional reference-voice cloning requires an explicit consent flag.
  * Heavy ML dependencies are imported only for --engine nano.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STORY_KEYS = {"fish": ("fish-nz", 8), "maui": ("maui-nz", 6)}
MAX_CHARS = 750
MAX_SCENE_DURATION = 65.0


def story_scenes(story: str, html_path: Path | None = None) -> list[dict]:
    if story not in STORY_KEYS:
        raise ValueError("Select 'fish' or 'maui'")
    text = (html_path or ROOT / "index.html").read_text(encoding="utf-8")
    name = story
    marker = f"const {name}Story="
    terminator = f";\nconst {name}Choice="
    if text.count(marker) != 1:
        raise ValueError(f"Cannot uniquely locate {story} story in index.html")
    source = text.split(marker, 1)[1]
    if terminator not in source:
        raise ValueError(f"Cannot locate {story} story terminator")
    scenes = json.loads(source.split(terminator, 1)[0])
    if len(scenes) != STORY_KEYS[story][1]:
        raise ValueError("Story scenes do not match the expected narration manifest")
    for scene in scenes:
        if not isinstance(scene.get("narration"), str) or not scene["narration"].strip():
            raise ValueError("Every scene must contain spoken narration")
        if len(scene["narration"]) > MAX_CHARS:
            raise ValueError("Split long narration before comparing models")
    return scenes


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    value = float(result.stdout.strip())
    if not math.isfinite(value) or not (0.5 <= value <= MAX_SCENE_DURATION):
        raise ValueError(f"Invalid narrator sample duration {value}: {path}")
    return value


def validate_reference(reference: Path | None, consent: bool) -> None:
    if reference is not None:
        if not consent:
            raise ValueError(
                "Voice reference requires --consent-confirmed. Use only a "
                "voice recording you own or have the speaker's permission to clone."
            )
        if not reference.is_file() or reference.stat().st_size < 20_000:
            raise ValueError("Provide a real, readable consenting speaker WAV")
        if audio_duration(reference) < 5.1:
            raise ValueError("Chatterbox voice reference must be longer than 5 seconds")


def sample_baseline(story_key: str, scene_num: int, output_dir: Path) -> dict:
    baseline = ROOT / "audio" / f"{story_key}-{scene_num}.mp3"
    if not baseline.is_file():
        raise FileNotFoundError(f"Approved Edge NZ narration is missing: {baseline}")
    output = output_dir / f"{story_key}-{scene_num}-current-nz.mp3"
    shutil.copyfile(baseline, output)
    return {
        "engine": "edge-nz-approved",
        "filename": output.name,
        "seconds": round(audio_duration(output), 2),
    }


def nano_model():
    # Import only in the opt-in Nano job; main ClayStory Actions stay lightweight.
    import torch
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    cpu_count = os.cpu_count() or 2
    torch.set_num_threads(min(4, cpu_count))
    torch.manual_seed(20261029)
    print("Loading optional Chatterbox Nano English-only narrator on CPU...", flush=True)
    return ChatterboxTurboTTS.from_pretrained(device="cpu", nano=True)


def sample_nano(
    model,
    story_key: str,
    scene_num: int,
    narration: str,
    output_dir: Path,
    reference: Path | None,
) -> dict:
    import torch
    import torchaudio

    if not narration.strip():
        raise ValueError("Narration may not be blank")
    wav_path = output_dir / f"{story_key}-{scene_num}-chatterbox-nano.wav"
    output = output_dir / f"{story_key}-{scene_num}-chatterbox-nano.mp3"
    kwargs = {"audio_prompt_path": str(reference)} if reference else {}
    with torch.inference_mode():
        speech = model.generate(narration, **kwargs)
    if speech is None or speech.numel() == 0:
        raise RuntimeError("Nano returned no audio")
    # torchaudio.save accepts (channels, frames), as used in upstream examples.
    if speech.ndim == 1:
        speech = speech.unsqueeze(0)
    torchaudio.save(str(wav_path), speech.detach().cpu(), model.sr)
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
             str(wav_path), "-af",
             "highpass=f=65,acompressor=threshold=0.1:ratio=1.6:attack=20:release=180,"
             "alimiter=limit=0.90:level=0:latency=1",
             "-c:a", "libmp3lame", "-q:a", "3", str(output)],
            check=True,
        )
        duration = audio_duration(output)
    finally:
        wav_path.unlink(missing_ok=True)
    return {
        "engine": "chatterbox-nano-cpu",
        "filename": output.name,
        "seconds": round(duration, 2),
        "reference_voice": "consented" if reference else "model-default",
    }


def comparison_page(story_name: str, entries: list[dict], output_dir: Path) -> None:
    """A portable review page bundled with the original MP3 comparison clips."""
    cards = []
    for item in entries:
        cards.append(
            f"<section><h2>Scene {int(item['scene'])}: "
            f"{html.escape(item['engine'])}</h2>"
            f"<audio controls preload='metadata' src='{html.escape(item['filename'], quote=True)}'></audio>"
            f"<p>Duration: {item['seconds']}s</p>"
            f"<p><b>Original narration:</b> {html.escape(item['text'])}</p></section>"
        )
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Pūrākau Pixels V30 voice comparison — {html.escape(story_name)}</title>"
        "<style>body{font:16px system-ui;background:#111b26;color:#f5f0e8;"
        "max-width:720px;margin:auto;padding:24px}section{border:1px solid #687c88;"
        "padding:18px;border-radius:14px;margin:18px 0}audio{width:100%}</style>"
        f"<h1>V30 voice comparison: {html.escape(story_name)}</h1>"
        "<p>Private preview only. No approved narration was replaced. "
        "Chatterbox Nano is an English-language model: its Māori pronunciation "
        "and accent must be checked before publication.</p>"
        + "".join(cards) + "</html>"
    )
    (output_dir / "listen.html").write_text(page, encoding="utf-8")


def run(args: argparse.Namespace) -> list[dict]:
    scenes = story_scenes(args.story)
    story_key, scene_count = STORY_KEYS[args.story]
    targets = args.scenes or ([1, 6] if args.story == "fish" else [1, 5])
    if len(set(targets)) != len(targets) or any(not 1 <= n <= scene_count for n in targets):
        raise ValueError(f"Scene numbers must be unique and between 1 and {scene_count}")

    validate_reference(args.reference_wav, args.consent_confirmed)
    if args.engine == "edge" and args.reference_wav:
        raise ValueError("A reference voice is only used with Chatterbox Nano")

    # Ensure outputs cannot be accidentally written into the production audio dir.
    output_dir = args.output_dir.resolve()
    prod_audio = (ROOT / "audio").resolve()
    if output_dir == prod_audio or prod_audio in output_dir.parents:
        raise ValueError("V30 voice previews must not overwrite production audio/")
    if args.dry_run:
        print(json.dumps({
            "story": story_key, "scenes": targets, "engine": args.engine,
            "output_dir": str(output_dir),
            "nano_requires": "CPU model download, English-only, may exceed runner budget",
            "production_audio_unchanged": True,
        }, indent=2))
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    model = None
    if args.engine == "nano":
        model = nano_model()  # Raises on failed model download; no silent substitute.

    result = []
    for number in targets:
        original = scenes[number - 1]["narration"]
        baseline = sample_baseline(story_key, number, output_dir)
        baseline.update(scene=number, text=original)
        result.append(baseline)
        if model:
            candidate = sample_nano(
                model, story_key, number, original, output_dir, args.reference_wav
            )
            candidate.update(scene=number, text=original)
            result.append(candidate)
        (output_dir / "comparison.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        comparison_page(story_key, result, output_dir)
        print(f"Saved V30 samples for scene {number}", flush=True)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare approved NZ narration with Chatterbox Nano")
    parser.add_argument("--story", choices=tuple(STORY_KEYS), default="fish")
    parser.add_argument("--scenes", type=int, nargs="+", metavar="N")
    parser.add_argument("--engine", choices=("edge", "nano"), default="edge")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "voice-previews")
    parser.add_argument("--reference-wav", type=Path, default=None,
                        help="Optional personally owned/consented voice recording; NOT required")
    parser.add_argument("--consent-confirmed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


if __name__ == "__main__":
    try:
        run(build_parser().parse_args())
    except Exception as exc:
        print(f"ClayStory V30 sample generation failed: {exc}", file=sys.stderr)
        raise
