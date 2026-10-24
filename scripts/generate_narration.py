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
async def maui_voice():
    for i, scene in enumerate(maui_scenes):
        rate, pitch = DELIVERY[i]
        await edge_tts.Communicate(scene["narration"], voice="en-US-GuyNeural", rate=rate, pitch=pitch).save(str(out / f"maui-{i+1}.mp3"))
asyncio.run(maui_voice())

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

# Build a single continuous 48-second timeline: each scene starts at 0,8,16... seconds.
# Mix instead of concatenating so speech is not cut off at scene boundaries.
for name in (("sun", "moon", "ocean", "maui", "custom") if custom else ("sun", "moon", "ocean", "maui")):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for i in range(1, 7):
        args += ["-i", str(out / f"{name}-{i}.mp3")]
    filters = []
    seconds = 22 if name == "maui" else 8
    for i in range(6):
        filters.append(f"[{i}:a]adelay={i*seconds*1000}|{i*seconds*1000}[a{i}]")
    filters.append("".join(f"[a{i}]" for i in range(6)) + "amix=inputs=6:duration=longest:normalize=0,highpass=f=75,equalizer=f=2800:t=q:w=1.2:g=-1.5,acompressor=threshold=0.12:ratio=1.6:attack=20:release=180,alimiter=limit=0.95,apad,atrim=duration={seconds*6}[out]")
    args += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3", str(out / f"{name}-full.mp3")]
    subprocess.run(args, check=True)
    print(f"Created {name}-full.mp3")

