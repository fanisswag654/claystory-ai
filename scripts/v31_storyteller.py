#!/usr/bin/env python3
"""V31 distinctly new storytelling narrators for ClayStory's original scripts.

Review-only output by default. Never silently uses the approved NZ narrator as
a substitute for an unavailable candidate. When --stage-film is set, scene
MP3s are copied into production filenames only in an explicitly acknowledged
ephemeral GitHub Actions checkout, so existing remix/render programs can export
an *unpublished* candidate MP4 as a workflow artifact. No git push occurs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from v30_voice import ROOT, STORY_KEYS, story_scenes, audio_duration

PROFILES = {
    "cinematic": {
        "engine": "edge",
        "model": "en-GB-RyanNeural",
        "label": "Cinematic British male storyteller",
        # Dramatic dynamics, not a robotic constant-speed reading.
        "rates": (-13, -5, -10, 2, -15, 3, -5, -15),
        "pitches": (-2, -2, -3, 0, -3, 1, -1, -3),
        "pauses": (.39, .25, .30, .21, .48, .17, .32, .48),
    },
    "warm": {
        "engine": "edge",
        "model": "en-US-ChristopherNeural",
        "label": "Warm documentary male storyteller",
        "rates": (-8, -3, -5, 1, -12, 4, -2, -9),
        "pitches": (-2, -1, -2, 0, -3, 1, -1, -2),
        "pauses": (.32, .22, .29, .19, .40, .16, .31, .41),
    },
    "kokoro": {
        "engine": "kokoro",
        "model": "bm_george",
        "label": "Kokoro George British male",
        "rates": (-12, -5, -8, 1, -13, 3, -4, -12),
        "pitches": (0,) * 8,
        "pauses": (.31, .23, .25, .17, .40, .16, .29, .35),
    },
}


def sentences(text: str) -> list[str]:
    """Split at punctuation only: preserve Māori spelling and narration text."""
    import re
    phrases = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip())]
    phrases = [part for part in phrases if part]
    if not phrases or "".join(phrases).strip() == "":
        raise ValueError("Narration cannot be empty")
    return phrases


def run_ffmpeg(*args: object) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    *map(str, args)], check=True)


def join_sentences(input_audio: list[Path], gap: float, target: Path) -> None:
    """Concat normalized mono segments with intentional quiet dramatic pauses."""
    if not 0 <= gap <= 1.2 or not input_audio:
        raise ValueError("Invalid dramatic pause or empty narration")
    with tempfile.TemporaryDirectory(prefix="claystory-voice-") as tmp:
        directory = Path(tmp)
        wavs = []
        for i, audio in enumerate(input_audio):
            p = directory / f"phrase-{i}.wav"
            run_ffmpeg("-i", audio, "-ar", "24000", "-ac", "1",
                       "-af", "silenceremove=start_periods=1:start_duration=0.04:"
                       "start_threshold=-62dB,areverse,"
                       "silenceremove=start_periods=1:start_duration=0.04:"
                       "start_threshold=-62dB,areverse",
                       "-c:a", "pcm_s16le", p)
            wavs.append(p)
        silence = directory / "silence.wav"
        if len(wavs) > 1 and gap > 0:
            run_ffmpeg("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                       "-t", f"{gap:.3f}", "-c:a", "pcm_s16le", silence)
        sequence = []
        for i, path in enumerate(wavs):
            if i and gap > 0:
                sequence.append(silence)
            sequence.append(path)
        listing = directory / "files.txt"
        listing.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in sequence),
            encoding="utf-8",
        )
        run_ffmpeg("-f", "concat", "-safe", "0", "-i", listing,
                   "-af", "highpass=f=70,"
                   "acompressor=threshold=0.14:ratio=1.5:attack=22:release=190,"
                   "alimiter=limit=0.9:level=0:latency=1",
                   "-c:a", "libmp3lame", "-q:a", "3", target)
    return audio_duration(target)


async def generate_edge(
    text: str, target: Path, voice: str, scene_index: int,
    profile: dict, workspace: Path,
) -> None:
    import edge_tts

    phrases = sentences(text)
    source_clips = []
    for j, phrase in enumerate(phrases):
        # Suspense scenes deliberately slow down; discovery scenes rise in energy.
        rate_base = profile["rates"][scene_index % len(profile["rates"])]
        rate = rate_base + (2 if j == len(phrases) - 1 and scene_index in (3, 5, 6) else 0)
        pitch = profile["pitches"][scene_index % len(profile["pitches"])]
        sample = workspace / f"edge-{scene_index}-{j}.mp3"
        await edge_tts.Communicate(
            phrase,
            voice=voice,
            rate=f"{rate:+d}%",
            pitch=f"{pitch:+d}Hz",
            proxy=os.getenv("HTTPS_PROXY"),
        ).save(str(sample))
        if not sample.is_file() or sample.stat().st_size < 2_000:
            raise RuntimeError(f"Edge voice {voice} failed scene {scene_index+1}")
        source_clips.append(sample)
    join_sentences(source_clips, profile["pauses"][scene_index], target)


def generate_kokoro(
    text: str, target: Path, scene_index: int, profile: dict, pipeline,
    workspace: Path,
) -> None:
    import numpy as np
    import soundfile as sf

    phrases = sentences(text)
    voice = profile["model"]
    source_clips = []
    for j, phrase in enumerate(phrases):
        # Kokoro speed parameter is a true speech-speed control.
        speed = max(.82, min(1.08, 1 + profile["rates"][scene_index] / 100))
        chunks = list(pipeline(phrase, voice=voice, speed=speed, split_pattern=r"\n+"))
        if not chunks:
            raise RuntimeError(f"Kokoro returned no speech for scene {scene_index+1}")
        data = np.concatenate([np.asarray(chunk[2], dtype=np.float32)
                               for chunk in chunks])
        if data.size < 2400 or not np.isfinite(data).all():
            raise RuntimeError("Kokoro generated empty or invalid PCM")
        wav = workspace / f"kokoro-{scene_index}-{j}.wav"
        sf.write(str(wav), data, 24000)
        source_clips.append(wav)
    join_sentences(source_clips, profile["pauses"][scene_index], target)


def validate_distinct(new: Path, original: Path) -> None:
    """Make it impossible to mark baseline copies as a new storyteller."""
    import hashlib

    if not original.is_file():
        raise FileNotFoundError(f"Missing existing approved voice: {original}")
    a = hashlib.sha256(new.read_bytes()).digest()
    b = hashlib.sha256(original.read_bytes()).digest()
    if a == b:
        raise RuntimeError(
            f"New narrator clip {new.name} is byte-identical to the NZ voice"
        )
    if audio_duration(new) < 1:
        raise RuntimeError(f"No audible narrator clip generated: {new}")


def build_review_page(output: Path, info: list[dict], voice_label: str) -> None:
    import html

    cards = []
    for row in info:
        if row["scene"] not in (1, 6):
            continue
        cards.append(
            "<section>"
            f"<h2>Scene {row['scene']} — {html.escape(voice_label)}</h2>"
            f"<audio controls src='{html.escape(row['file'], quote=True)}'></audio>"
            f"<p>{html.escape(row['narration'])}</p>"
            "</section>"
        )
    (output / "LISTEN.html").write_text(
        "<!doctype html><html><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta charset='utf-8'><title>Pūrākau Pixels V31 narrator</title>"
        "<style>body{background:#15171f;color:#f5f0df;padding:1.5rem;"
        "font:16px system-ui;max-width:730px;margin:auto}"
        "section{background:#222b35;border-radius:14px;padding:16px;margin:1rem 0}"
        "audio{width:100%}</style>"
        f"<h1>{html.escape(voice_label)}</h1>"
        "<p>New experimental narrator. The original NZ narration and Instagram"
        " video have not been replaced. Check Māori pronunciation before use.</p>"
        + "".join(cards) + "</html>",
        encoding="utf-8",
    )


async def generate(args: argparse.Namespace) -> list[dict]:
    profile = PROFILES[args.voice]
    key, count = STORY_KEYS[args.story]
    scenes = story_scenes(args.story)
    targets = list(range(1, count + 1)) if args.full else ([1, 6] if args.story == "fish" else [1, 5])
    target = args.output.resolve()
    approved_audio = (ROOT / "audio").resolve()
    if target == approved_audio or approved_audio in target.parents:
        raise ValueError("Candidate samples cannot overwrite production audio/")
    if args.stage_film and (
        not args.full
        or args.story != "fish"
        or os.getenv("CLAYSTORY_PREVIEW_WORKSPACE") != "1"
        or os.getenv("GITHUB_ACTIONS") != "true"
    ):
        raise ValueError(
            "Staging may only occur for a full Great Fish preview in an explicitly"
            " marked temporary GitHub Actions checkout"
        )
    if args.dry_run:
        print(json.dumps({
            "profile": args.voice, "model": profile["model"],
            "candidate_only": True, "scenes": targets,
            "stage_film": args.stage_film,
        }, indent=2))
        return []
    target.mkdir(parents=True, exist_ok=True)
    model = None
    if profile["engine"] == "kokoro":
        from kokoro import KPipeline
        model = KPipeline(lang_code="b")
    manifest = []
    for number in targets:
        scene = scenes[number - 1]
        output = target / f"{key}-{number}-{args.voice}-new-narration.mp3"
        print(f"Generating scene {number} with {profile['model']}", flush=True)
        with tempfile.TemporaryDirectory(prefix="claystory-voice-") as scratch:
            folder = Path(scratch)
            if profile["engine"] == "edge":
                await generate_edge(
                    scene["narration"], output, profile["model"], number - 1,
                    profile, folder,
                )
            else:
                generate_kokoro(
                    scene["narration"], output, number - 1, profile, model, folder,
                )
        validate_distinct(output, ROOT / "audio" / f"{key}-{number}.mp3")
        entry = {
            "scene": number,
            "file": output.name,
            "voice": args.voice,
            "engine": profile["engine"],
            "model": profile["model"],
            "label": profile["label"],
            "seconds": round(audio_duration(output), 3),
            "narration": scene["narration"],
        }
        manifest.append(entry)
        if args.stage_film:
            # This copy happens ONLY inside the ephemeral Actions runner.
            shutil.copyfile(output, ROOT / "audio" / f"{key}-{number}.mp3")
        (target / "comparison.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        build_review_page(target, manifest, profile["label"])
    if len(manifest) != len(targets):
        raise RuntimeError("Requested voice was incomplete. Refusing to pass.")
    (target / "VOICE_STATUS.txt").write_text(
        f"Generated: {len(manifest)}/{len(targets)} genuinely NEW scenes\n"
        f"Profile: {args.voice}\nModel: {profile['model']}\n"
        "Production Instagram Reel: unchanged\n"
        "Māori pronunciation: not verified, needs fluent review\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a genuinely new, expressive narrator")
    p.add_argument("--story", choices=tuple(STORY_KEYS), default="fish")
    p.add_argument("--voice", choices=tuple(PROFILES), default="cinematic")
    p.add_argument("--output", type=Path, default=ROOT / "voice-previews" / "v31")
    p.add_argument("--full", action="store_true")
    p.add_argument("--stage-film", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    try:
        asyncio.run(generate(parse_args()))
    except Exception as exc:
        print("V31 alternative narration FAILED:", exc, file=sys.stderr)
        raise
