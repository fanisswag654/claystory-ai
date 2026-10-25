"""V18 narration and original synthesized audio. Run from the repository root.

--story fish regenerates only the eight Great Fish clips; default preserves the
full built-in/custom generation workflow. --reuse-voice remixes existing clips.
NZ English synthesis requires fluent te reo Māori pronunciation review.
"""
import argparse
import array
import asyncio
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import wave
import edge_tts

parser = argparse.ArgumentParser()
parser.add_argument("--story", choices=("all", "fish"), default="all")
parser.add_argument("--reuse-voice", action="store_true")
options = parser.parse_args()
html = Path("index.html").read_text(encoding="utf-8")
out = Path("audio")
out.mkdir(exist_ok=True)
SFX_RATE = 22050
sfx_random = random.Random(54721)
sfx_samples = array.array("f")


def curated(name):
    section = html.split(f"const {name}Story=", 1)[1].split(f";\nconst {name}Choice=", 1)[0]
    scenes = json.loads(section)
    expected = 8 if name == "fish" else 6
    if len(scenes) != expected:
        raise RuntimeError(f"{name}: expected {expected} scenes, found {len(scenes)}")
    return scenes


def media_duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip())


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


# V21: retain the natural NZ male neural voice without artificial octave-like
# lowering. A small scene-to-scene change in rate/pitch gives expressive delivery.
# Allow the native voice's natural rhythm and articulation to come through.
FISH_DELIVERY = [
    ("+5%", "-4Hz"),   # curious opening
    ("+9%", "-2Hz"),   # active brothers leaving
    ("+7%", "-3Hz"),   # conspiratorial hiding
    ("+9%", "-2Hz"),   # surprise at sea
    ("+4%", "-4Hz"),   # deliberate ancestral hook
    ("+10%", "-3Hz"),  # urgency when the line takes
    ("+8%", "-4Hz"),   # powerful fish reveal
    ("+3%", "-5Hz"),   # warm, considered moral
]
MAUI_DELIVERY = [("+8%", "+0Hz"), ("+10%", "+1Hz"), ("+7%", "-1Hz"),
                 ("+11%", "+0Hz"), ("+9%", "+1Hz"), ("+5%", "-1Hz")]


async def voices(name, scenes, voice, delivery):
    for i, scene in enumerate(scenes):
        destination = out / f"{name}-{i+1}.mp3"
        if options.reuse_voice:
            if not destination.exists():
                raise RuntimeError(f"Missing reusable voice: {destination}")
            continue
        temporary = out / f"{name}-{i+1}-raw.mp3"
        rate, pitch = delivery[i % len(delivery)]
        print(f"Generating {destination}", flush=True)
        await edge_tts.Communicate(scene["narration"], voice=voice, rate=rate, pitch=pitch, proxy=os.environ.get("HTTPS_PROXY")).save(str(temporary))
        # Trim only outer silence; preserve storytelling pauses.
        voice_filter = (
            "silenceremove=start_periods=1:start_duration=0.06:start_threshold=-55dB,"
            "areverse,silenceremove=start_periods=1:start_duration=0.06:start_threshold=-55dB,areverse"
        )
        if name == "fish-nz":
            # V21: remove rubberband pitch lowering that made the narrator sound
            # artificially elderly/processed. Very subtle EQ only.
            voice_filter += ",equalizer=f=155:t=q:w=1.0:g=0.5"
        ffmpeg("-i", temporary, "-af", voice_filter,
               "-c:a", "libmp3lame", "-q:a", "3", destination)
        temporary.unlink()
        if media_duration(destination) < 1:
            raise RuntimeError(f"Empty narration: {destination}")


def continuous(name, durations):
    args = []
    parts = []
    cursor = 0
    for i, duration in enumerate(durations):
        args += ["-i", out / f"{name}-{i+1}.mp3"]
        parts.append(f"[{i}:a]adelay={round(cursor*1000)}:all=1[a{i}]")
        cursor += duration
    parts.append("".join(f"[a{i}]" for i in range(len(durations))) +
                 f"amix=inputs={len(durations)}:duration=longest:normalize=0,"
                 "highpass=f=72,acompressor=threshold=0.15:ratio=1.4:attack=25:release=190,"
                 f"alimiter=limit=0.90:level=0:latency=1,apad,atrim=duration={cursor}[out]")
    ffmpeg(*args, "-filter_complex", ";".join(parts), "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3", out / f"{name}-full.mp3")


def add_sfx_tone(at, length, start_hz, end_hz, amp=0.15, style="sine"):
    first = max(0, round(at * SFX_RATE))
    count = min(round(length * SFX_RATE), len(sfx_samples) - first)
    if count <= 0:
        return
    for k in range(count):
        fraction = k / count
        phase = 2 * math.pi * length * (start_hz * fraction + (end_hz - start_hz) * fraction * fraction * .5)
        wave_value = math.sin(phase)
        if style == "retro":
            wave_value = math.copysign(1, wave_value) * .75 + .25 * wave_value
        envelope = min(1, fraction * 24) * (1 - fraction) ** 1.25
        sfx_samples[first + k] += wave_value * envelope * amp

def add_sfx_noise(at, length, amp=.07, color="soft"):
    first = max(0, round(at * SFX_RATE))
    count = min(round(length * SFX_RATE), len(sfx_samples) - first)
    if count <= 0:
        return
    low = 0.0
    for k in range(count):
        fraction = k / count
        white = sfx_random.random() * 2 - 1
        low = .975 * low + .025 * white
        wave_value = low * 4 if color == "wind" else (white * .74 + low * 1.8)
        envelope = min(1, fraction * 14, (1 - fraction) * 11)
        sfx_samples[first + k] += wave_value * amp * envelope

def add_sfx_chime(at, root=520, amp=.14):
    add_sfx_tone(at, .39, root, root * 1.14, amp)
    add_sfx_tone(at + .07, .23, root * 1.5, root * 1.65, amp * .5)
    add_sfx_tone(at + .13, .11, root * 2.1, root * 1.8, amp * .25)

def add_sfx_fire(at):
    for j in range(5):
        add_sfx_noise(at + j * .13, .06 + j % 2 * .025, .12, "crackle")

def add_sfx_rope(at):
    add_sfx_noise(at, .5, .115, "crackle")
    add_sfx_tone(at, .41, 136, 79, .14, "retro")

def add_sfx_impact(at):
    add_sfx_noise(at, .41, .25, "crackle")
    add_sfx_tone(at, .48, 185, 55, .31, "retro")
    add_sfx_tone(at + .07, .34, 470, 110, .12, "sine")

def add_sfx_birds(at):
    for j in range(3):
        add_sfx_tone(at + j * .23, .16, 830 + j * 65, 1100 + j * 45, .14)
        add_sfx_tone(at + j * .23 + .14, .12, 1040 + j * 90, 720, .095)

def write_pcm_wave(path, data):
    pcm = array.array("h", [max(-32768, min(32767, int(s * 32767)))
                             for s in data])
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SFX_RATE)
        output.writeframes(pcm.tobytes())

def fish_seabird(at):
    for j in range(3):
        add_sfx_tone(at + j * .16, .18, 930 + j * 65, 680 + j * 45, .12)
        add_sfx_tone(at + j * .16 + .15, .1, 690, 950 + j * 25, .07)

def fish_water(at, duration=.6, level=.11):
    add_sfx_noise(at, duration, level, "wind")
    add_sfx_tone(at, duration, 142, 118, level * .22)

def fish_paddle(at):
    add_sfx_noise(at, .19, .22, "crackle")
    add_sfx_tone(at, .33, 215, 128, .11)

def fish_wood(at):
    add_sfx_tone(at, .23, 162, 103, .13, "retro")
    add_sfx_noise(at + .04, .09, .08, "crackle")


def soundtrack(name, durations):
    # V20 uses an entirely new restrained acoustic foley track for the Great Fish.
    # No continuous synth drones, beeps, chiming melodies, or repetitive bird calls.
    if name == "fish-nz":
        from natural_foley import render_fish_foley
        render_fish_foley(out, durations, name)
        return
    global sfx_samples
    total = sum(durations)
    sfx_samples = array.array("f", [0.0]) * math.ceil(total * SFX_RATE)
    cursor = 0
    for i, duration in enumerate(durations):
        base = cursor
        cursor += duration
        add_sfx_noise(base, duration, .045 if i in (5, 6) else .03, "wind")
        add_sfx_tone(base, duration, 75 if i == 0 or i == 5 else 145, 90 if i == 5 else 160, .025)
        if name == "fish-nz":
            if i == 0:
                for f in (.15, .4, .7):
                    add_sfx_tone(base+duration*f, .6, 230, 410, .07)
                fish_water(base+.1, 2, .09)
            elif i in (1, 2, 3):
                for f in (.1, .3, .5, .7, .9):
                    fish_paddle(base+duration*f)
                fish_wood(base+duration*.45)
                fish_seabird(base+duration*.7)
                if i == 2:
                    for f in (.1, .2, .3): fish_wood(base+duration*f)
                if i == 3: add_sfx_chime(base+duration*.15, 370, .12)
            elif i == 4:
                fish_wood(base+duration*.2)
                add_sfx_chime(base+duration*.55, 440, .10)
            elif i == 5:
                fish_water(base+duration*.12, .65, .25)
                add_sfx_tone(base+duration*.3, 1.5, 120, 48, .20, "retro")
                for f in (.45, .65, .85):
                    add_sfx_rope(base+duration*f)
                    fish_wood(base+duration*f)
                    fish_water(base+duration*f, .5, .18)
            elif i == 6:
                add_sfx_tone(base, 2, 65, 180, .22)
                fish_water(base+duration*.24, 1.8, .30)
                add_sfx_impact(base+duration*.3)
                for f in (.74, .84, .93):
                    fish_wood(base+duration*f)
                    add_sfx_noise(base+duration*f, .2, .17)
            else:
                add_sfx_tone(base+.1, 3, 65, 210, .20)
                add_sfx_impact(base+duration*.12)
                for f in (.4, .6, .8): add_sfx_chime(base+duration*f, 392+f*180, .10)
                fish_seabird(base+duration*.75)
        else:
            # Preserve the sun story's fire, weaving, rope, confrontation and birds.
            if i == 0:
                for f in (.1, .3, .5, .7): add_sfx_fire(base+duration*f)
            elif i in (2, 3):
                for f in (.2, .4, .6): add_sfx_rope(base+duration*f)
            elif i == 4:
                add_sfx_impact(base+duration*.55)
                add_sfx_rope(base+duration*.75)
            else:
                add_sfx_chime(base+duration*.4)
                add_sfx_birds(base+duration*.7)
    wav = out / f"{name}-sfx.wav"
    write_pcm_wave(wav, sfx_samples)
    effects = out / f"{name}-sfx.mp3"
    ffmpeg("-i", wav, "-c:a", "libmp3lame", "-q:a", "4", effects)
    wav.unlink()
    for mix, gain in (("soft", .45), ("balanced", 1), ("bold", 1.55)):
        destination = out / f"{name}-mix-{mix}.mp3"
        ffmpeg("-i", out / f"{name}-full.mp3", "-i", effects,
               "-filter_complex", f"[0:a]volume=0.9[v];[1:a]volume={gain}[s];"
               "[v][s]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.85:level=0:latency=1[out]",
               "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3", destination)
        if abs(media_duration(destination)-total) > .15:
            raise RuntimeError(f"Mix timing mismatch: {destination}")
    sfx_samples = array.array("f", [0.0]) * round(3.3*SFX_RATE)
    fish_water(.05, .7, .25)
    fish_paddle(1)
    add_sfx_rope(1.55)
    add_sfx_impact(2.3)
    write_pcm_wave(wav, sfx_samples)
    ffmpeg("-i", wav, "-c:a", "libmp3lame", "-q:a", "3", out / f"{name}-fx-test.mp3")
    wav.unlink()


def generate_featured(key):
    scenes = curated(key)
    name = f"{key}-nz"
    asyncio.run(voices(name, scenes, "en-NZ-MitchellNeural", FISH_DELIVERY if key == "fish" else MAUI_DELIVERY))
    durations = [round(media_duration(out / f"{name}-{i+1}.mp3") + (.15 if i < len(scenes)-1 else .22), 3) for i in range(len(scenes))]
    continuous(name, durations)
    soundtrack(name, durations)
    # Publish timing last: a partially generated set must never advertise readiness.
    (out / f"{name}-timing.json").write_text(json.dumps({
        "durations": durations, "voice": "en-NZ-MitchellNeural", "revision": 18,
        "description": "Narration-length cuts; 0.15-second transitions; pronunciation requires human review"
    }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(name, durations, "total", round(sum(durations), 3), flush=True)
    if key == "fish" and not 85 <= sum(durations) <= 100:
        print("WARNING: Great Fish runtime outside 85–100 second target; review natural delivery.", flush=True)


if __name__ == "__main__":
    generate_featured("fish")
    if options.story == "all":
        generate_featured("maui")
        section = html[html.index("const story=["):html.index("let chosen=library[0];")]
        narrations = re.findall(r'narration:"((?:[^"\\]|\\.)*)"', section)
        if len(narrations) != 18:
            raise RuntimeError(f"Expected 18 library narrations, found {len(narrations)}")
        for j, name in enumerate(("sun", "moon", "ocean")):
            scenes = [{"narration": json.loads('"'+n+'"')} for n in narrations[j*6:(j+1)*6]]
            asyncio.run(voices(name, scenes, "en-US-GuyNeural", [("+0%", "+0Hz")]*6))
            continuous(name, [8]*6)
        custom = os.environ.get("CUSTOM_SCRIPT", "").strip()
        if custom:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\s*\|\s*", custom.replace("\\n", "\n")) if p.strip()]
            if len(paragraphs) == 1:
                sentences = re.split(r"(?<=[.!?])\s+", paragraphs[0])
                paragraphs = [" ".join(sentences[i*len(sentences)//6:(i+1)*len(sentences)//6]) for i in range(6)]
            paragraphs = paragraphs[:5]+[" ".join(paragraphs[5:])] if len(paragraphs)>6 else paragraphs
            paragraphs += [""]*(6-len(paragraphs))
            scenes = [{"title":f"Scene {i+1}","caption":" ".join(p.split()[:6]).upper(),"narration":p or "The story continues.","color":"#293451"} for i,p in enumerate(paragraphs)]
            Path("custom-story.json").write_text(json.dumps({"scenes":scenes},ensure_ascii=False),encoding="utf-8")
            asyncio.run(voices("custom", scenes, "en-US-GuyNeural", [("+0%", "+0Hz")]*6))
            continuous("custom", [8]*6)
