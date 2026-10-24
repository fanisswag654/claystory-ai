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
async def main():
    for story_index, name in enumerate(("sun", "moon", "ocean")):
        for i, raw in enumerate(narrations[story_index*6:(story_index+1)*6]):
            phrase = json.loads('"' + raw + '"')
            destination = out / f"{name}-{i+1}.mp3"
            print(f"Generating {destination}")
            await edge_tts.Communicate(phrase, voice="en-US-GuyNeural", rate="-12%", pitch="-12Hz").save(str(destination))
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

