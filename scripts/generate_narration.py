"""Generate narrated scene audio from the existing curated JavaScript stories."""
import asyncio
import json
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
# Scene-by-scene performance direction: subtle variations sound less robotic
# than forcing the same slow rate and low pitch onto every line.
DELIVERY = [
    ("-3%", "-4Hz"),   # intriguing hook
    ("+2%", "-2Hz"),   # engaging discovery
    ("-2%", "-5Hz"),   # dramatic reveal
    ("-1%", "-3Hz"),   # confident explanation
    ("-5%", "-5Hz"),   # reflective moment
    ("-2%", "-3Hz"),   # warm conclusion
]

# Punctuation gives the TTS engine natural places to breathe and emphasize.
# Keep the factual content unchanged; only refine spoken delivery.
def perform(text: str, scene: int) -> str:
    text = text.replace("Not quite!", "Well... not quite!")
    text = text.replace("The consequences would be enormous.", "And the consequences? They'd be enormous.")
    text = text.replace("What would change?", "So... what would actually change?")
    text = text.replace("Would Earth freeze instantly?", "Would Earth freeze... instantly?")
    text = text.replace("But Earth would not instantly be destroyed.", "But here's the thing: Earth wouldn't instantly be destroyed.")
    text = text.replace("Thankfully, this is just a thought experiment!", "And thankfully... this is only a thought experiment.")
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
# Build a single continuous 48-second timeline: each scene starts at 0,8,16... seconds.
# Mix instead of concatenating so speech is not cut off at scene boundaries.
for name in ("sun", "moon", "ocean"):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for i in range(1, 7):
        args += ["-i", str(out / f"{name}-{i}.mp3")]
    filters = []
    for i in range(6):
        filters.append(f"[{i}:a]adelay={i*8000}|{i*8000}[a{i}]")
    filters.append("".join(f"[a{i}]" for i in range(6)) + "amix=inputs=6:duration=longest:normalize=0,apad,atrim=duration=48[out]")
    args += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3", str(out / f"{name}-full.mp3")]
    subprocess.run(args, check=True)
    print(f"Created {name}-full.mp3")

