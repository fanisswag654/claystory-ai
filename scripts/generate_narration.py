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
