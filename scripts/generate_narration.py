"""Generate narrated scene audio from the existing curated JavaScript stories."""
import asyncio
import json
import os
import re
import subprocess
from pathlib import Path
import edge_tts

html = Path("index.html").read_text(encoding="utf-8")
# The app's curated library has 3 topics x 6 scenes, with the Sun story first.
start = html.index("const story=[")
end = html.index("let chosen=library[0];")
section = html[start:end]
narrations = re.findall(r'narration:"((?:[^"\\]|\\.)*)"', section)
if len(narrations) != 18:
    raise RuntimeError(f"Expected 18 narration scenes, found {len(narrations)}")
out = Path("audio")
out.mkdir(exist_ok=True)
# Read the six dedicated Māui pūrākau scenes from the app.
maui_section = html.split("const mauiStory=",1)[1].split(";\nconst mauiChoice=",1)[0]
maui_scenes = json.loads(maui_section)
if len(maui_scenes) != 6:
    raise RuntimeError("Expected six Māui scenes")
# Scene-by-scene performance direction: subtle variations sound less robotic
# than forcing the same slow rate and low pitch onto every line.
DELIVERY = [
    ("-2%", "-1Hz"),   # curious, intimate hook
    ("+1%", "+0Hz"),   # discovery, brighter and quicker
    ("-4%", "-2Hz"),   # give the reveal room
    ("+0%", "+0Hz"),   # confident explanation
    ("-3%", "-1Hz"),   # reflective moment
    ("-1%", "+0Hz"),   # reassuring conclusion
]

# Punctuation gives the TTS engine natural places to breathe and emphasize.
# Keep the factual content unchanged; only refine spoken delivery.
def perform(text: str, scene: int) -> str:
    text = text.replace("Not quite!", "Actually, not quite.")
    text = text.replace("The consequences would be enormous.", "And the consequences? They'd be enormous.")
    text = text.replace("What would change?", "So what would actually change?")
    text = text.replace("Would Earth freeze instantly?", "Would Earth freeze instantly?")
    text = text.replace("But Earth would not instantly be destroyed.", "But here's the thing: Earth wouldn't instantly be destroyed.")
    text = text.replace("Thankfully, this is just a thought experiment!", "Thankfully, this is only a thought experiment.")
    return text

async def main():
    for story_index, name in enumerate(("sun", "moon", "ocean")):
        for i, raw in enumerate(narrations[story_index*6:(story_index+1)*6]):
            phrase = json.loads('"' + raw + '"')
            destination = out / f"{name}-{i+1}.mp3"
            print(f"Generating {destination}")
            rate, pitch = DELIVERY[i]
            spoken = perform(phrase, i)
            await edge_tts.Communicate(spoken, voice="en-US-GuyNeural", rate=rate, pitch=pitch).save(str(destination))
asyncio.run(main())
# Speedier, more conversational delivery with restrained scene-specific variation.
# These are New Zealand English voices, not certified te reo Māori pronunciation.
MAUI_DELIVERY = [
    ("+8%", "+0Hz"),   # conversational setup
    ("+10%", "+1Hz"),  # curious, purposeful discovery
    ("+7%", "-1Hz"),   # scepticism, preparation
    ("+11%", "+0Hz"),  # a journey that builds suspense
    ("+9%", "+1Hz"),   # lively confrontation
    ("+5%", "-1Hz"),   # warm conclusion
]

def media_duration(path):
    output = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True)
    return float(output.strip())

async def maui_voice():
    for i, scene in enumerate(maui_scenes):
        rate, pitch = MAUI_DELIVERY[i]
        file = out / f"maui-nz-{i+1}.mp3"
        temp = out / f"maui-nz-{i+1}-raw.mp3"
        # Preserve Māori spelling and wording in the spoken text. A fluent
        # human narrator is preferable to synthetic pronunciation if possible.
        await edge_tts.Communicate(
            scene["narration"], voice="en-NZ-MitchellNeural", rate=rate, pitch=pitch
        ).save(str(temp))
        # Remove ONLY silence at the start and end of the clip. Reverse between
        # passes to retain the natural pauses between spoken sentences.
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(temp),
            "-af", "silenceremove=start_periods=1:start_duration=0.06:start_threshold=-55dB,"
                   "areverse,"
                   "silenceremove=start_periods=1:start_duration=0.06:start_threshold=-55dB,"
                   "areverse",
            "-c:a", "libmp3lame", "-q:a", "3", str(file)
        ], check=True)
        temp.unlink(missing_ok=True)
        if media_duration(file) < 2:
            raise RuntimeError(f"Unusually short narration for scene {i+1}")

asyncio.run(maui_voice())

# Record narration-accurate cut points rather than leaving 22 seconds per scene.
# A very small transition pause feels natural without seconds of dead air.
maui_gap = 0.16
maui_clip_durations = [media_duration(out / f"maui-nz-{i}.mp3") for i in range(1, 7)]
maui_timing = [round(d + (maui_gap if i < 5 else 0.25), 3)
               for i, d in enumerate(maui_clip_durations)]
(out / "maui-nz-timing.json").write_text(json.dumps({
    "durations": maui_timing,
    "voice": "en-NZ-MitchellNeural",
    "description": "Clip-length-driven scene timing with 0.16 second gaps",
    "revision": 14
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("Māui timing:", maui_timing, "total", round(sum(maui_timing), 2), "seconds")

# Optional script supplied in GitHub Actions: split into six storyboard scenes.
custom = os.environ.get("CUSTOM_SCRIPT", "").strip()
if custom:
    paragraphs = [p.strip() for p in re.split(r"\\n\\s*\\n|\\s*\\|\\s*", custom.replace("\\n", "\n")) if p.strip()]
    if len(paragraphs) == 1:
        sentences = re.split(r"(?<=[.!?])\\s+", paragraphs[0])
        paragraphs = [" ".join(sentences[i::6]) for i in range(6)]
    if len(paragraphs) > 6:
        paragraphs = paragraphs[:5] + [" ".join(paragraphs[5:])]
    while len(paragraphs) < 6:
        paragraphs.append("")
    scenes = []
    for i, paragraph in enumerate(paragraphs):
        text = paragraph or " "
        scenes.append({"title": f"Scene {i+1}", "caption": " ".join(paragraph.split()[:6]).upper() or "THE STORY CONTINUES", "narration": paragraph, "color": "#293451"})
    Path("custom-story.json").write_text(json.dumps({"scenes": scenes}, ensure_ascii=False), encoding="utf-8")
    async def custom_voice():
        for i, paragraph in enumerate(paragraphs):
            text = paragraph or " "
            rate, pitch = DELIVERY[i]
            await edge_tts.Communicate(text, voice="en-US-GuyNeural", rate=rate, pitch=pitch).save(str(out / f"custom-{i+1}.mp3"))
    asyncio.run(custom_voice())

# Mix each scene into one continuous track, respecting its actual duration.
# Built-in library stories retain their existing 8-second staging.
for name in (("sun", "moon", "ocean", "maui-nz", "custom") if custom else
             ("sun", "moon", "ocean", "maui-nz")):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for i in range(1, 7):
        args += ["-i", str(out / f"{name}-{i}.mp3")]
    filters = []
    if name == "maui-nz":
        start_ms = 0
        for i in range(6):
            filters.append(f"[{i}:a]adelay={start_ms}|{start_ms}[a{i}]")
            start_ms += round(maui_timing[i] * 1000)
        total_duration = round(sum(maui_timing), 3)
    else:
        for i in range(6):
            filters.append(f"[{i}:a]adelay={i*8000}|{i*8000}[a{i}]")
        total_duration = 48
    filters.append("".join(f"[a{i}]" for i in range(6)) +
                   f"amix=inputs=6:duration=longest:normalize=0,"
                   f"highpass=f=72,acompressor=threshold=0.15:ratio=1.4:"
                   f"attack=25:release=190,alimiter=limit=0.96,"
                   f"apad,atrim=duration={total_duration}[out]")
    args += ["-filter_complex", ";".join(filters),
             "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3",
             str(out / f"{name}-full.mp3")]
    subprocess.run(args, check=True)
    print(f"Created {name}-full.mp3 (duration {total_duration:.2f}s)")


# V16 reliable soundscape: bake cinematic ambience and retro action effects into
# normal MP3 audio rather than relying on iOS Safari's separate Web Audio engine.
# All sounds are synthesized, not copied from any videogame or recording.
import array
import math
import random
import sys
import wave

SFX_RATE = 22050
SFX_TOTAL = sum(maui_timing)
sfx_samples = array.array("f", [0.0]) * (math.ceil(SFX_TOTAL * SFX_RATE) + SFX_RATE // 4)
sfx_random = random.Random(54721)

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

scene_positions = []
position = 0.0
for dur in maui_timing:
    scene_positions.append(position)
    position += dur

# Layered, lower-level ambiance underneath the narration, with dynamic cues.
for i, (scene_start, duration) in enumerate(zip(scene_positions, maui_timing)):
    body = max(.1, duration - .2)
    add_sfx_noise(scene_start, body, (.060 if i == 4 else .032), "wind")
    add_sfx_tone(scene_start, body, [125,190,145,110,98,175][i],
                 [136,220,153,117,91,196][i], (.027 if i != 4 else .045))
    if i == 0:
        for sec in (1.0, 2.6, 4.5, 6.1, 8.0): add_sfx_fire(scene_start + sec)
        add_sfx_chime(scene_start + duration * .53, 520, .105)
    elif i == 1:
        add_sfx_tone(scene_start + .5, 1.1, 200, 360, .09)
        add_sfx_chime(scene_start + duration * .32, 620, .16)
        add_sfx_chime(scene_start + duration * .72, 470, .1)
    elif i == 2:
        for sec in (1.5,3.0,4.4,6.2,8.1,9.7):
            add_sfx_noise(scene_start + sec, .20, .13, "crackle")
            add_sfx_tone(scene_start + sec, .14, 170, 135, .065)
        add_sfx_rope(scene_start + duration * .7)
    elif i == 3:
        for sec in (1.0,2.5,3.8,5.1):
            add_sfx_noise(scene_start + sec, .12, .11, "crackle")
        for sec in (1.3,3.3,5.2,6.8): add_sfx_tone(scene_start + sec, .22, 940, 1180, .095)
        add_sfx_tone(scene_start + duration * .79, 1.15, 260, 580, .13)
        add_sfx_chime(scene_start + duration * .84, 585, .12)
    elif i == 4:
        add_sfx_rope(scene_start + duration * .11)
        add_sfx_tone(scene_start + duration * .34, .8, 110, 280, .19, "retro")
        add_sfx_impact(scene_start + duration * .55)
        add_sfx_rope(scene_start + duration * .75)
        add_sfx_tone(scene_start + duration * .80, .65, 490, 240, .12)
    elif i == 5:
        for sec in (1.0,3.0,5.2,7.8,9.8): add_sfx_birds(scene_start + sec)
        add_sfx_chime(scene_start + duration * .39, 392, .14)
        add_sfx_chime(scene_start + duration * .58, 524, .11)

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

sfx_wav = out / "maui-nz-sfx.wav"
sfx_mp3 = out / "maui-nz-sfx.mp3"
write_pcm_wave(sfx_wav, sfx_samples)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(sfx_wav), "-c:a", "libmp3lame", "-q:a", "4",
                str(sfx_mp3)], check=True)
sfx_wav.unlink(missing_ok=True)

# Three different strengths for the slider, plus the original narration-only file.
# With a single MP3 per preview, iOS plays the voice and FX together reliably.
for mix_name, fx_gain in (("soft", .45), ("balanced", 1.0), ("bold", 1.55)):
    destination = out / f"maui-nz-mix-{mix_name}.mp3"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(out / "maui-nz-full.mp3"),
        "-i", str(sfx_mp3),
        "-filter_complex",
        "[0:a]volume=0.90[voice];"
        f"[1:a]volume={fx_gain}[effects];"
        "[voice][effects]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95[out]",
        "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3",
        str(destination)
    ], check=True)
    seconds = media_duration(destination)
    if abs(seconds - SFX_TOTAL) > .6 or destination.stat().st_size < 10000:
        raise RuntimeError(f"Mixed effects track invalid: {destination}")
    print(f"Created {destination} ({seconds:.2f}s; FX multiplier {fx_gain})")

# Audible three-second effects sampler for checking audio playback on iPad.
test_wave = out / "maui-nz-fx-test.wav"
test_length = 3.3
test_samples = array.array("f", [0.0]) * round(test_length * SFX_RATE)
original_samples = sfx_samples
sfx_samples = test_samples
add_sfx_chime(.12, 490, .34)
add_sfx_noise(.8, .65, .30, "crackle")
add_sfx_impact(1.55)
add_sfx_birds(2.45)
write_pcm_wave(test_wave, test_samples)
sfx_samples = original_samples
subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-i", str(test_wave), "-c:a", "libmp3lame", "-q:a", "3",
    str(out / "maui-nz-fx-test.mp3")
], check=True)
test_wave.unlink(missing_ok=True)
print("V16 reliable soundscape published: 3 voice+FX strengths and a test track.")
