#!/usr/bin/env python3
"""Generate exact cinematic Ryan narration for one NEW source-backed story.

The original V31 voice renderer and sound mixer are reused with fresh scene
text and measured timings; no previous film soundtrack is copied.
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import tane_sound
from v31_storyteller import PROFILES, generate_edge

ROOT_OUT=ROOT/"automation"/"output"
KEY="auto-review"


async def make_voice(story):
    profile=PROFILES["cinematic"]
    for i,scene in enumerate(story["scenes"]):
        target=ROOT_OUT/f"{KEY}-{i+1}.mp3"
        with tempfile.TemporaryDirectory(prefix="purakau-new-") as tmp:
            print(f"Generating cinematic NEW narration scene {i+1}/8",flush=True)
            await generate_edge(scene["narration"],target,profile["model"],i,
                                profile,Path(tmp))
        if tane_sound.seconds(target)<3:
            raise RuntimeError("Narration scene was too short; refusing candidate")
    return profile


def main():
    story_path=ROOT/"automation"/"candidate-story.json"
    story=json.loads(story_path.read_text(encoding="utf-8"))
    if len(story["scenes"])!=8 or story["review_status"]!="pending-human-approval":
        raise ValueError("Only a pending, eight-scene review candidate can be rendered")
    ROOT_OUT.mkdir(parents=True,exist_ok=True)
    profile=asyncio.run(make_voice(story))
    durations=[round(tane_sound.seconds(ROOT_OUT/f"{KEY}-{i+1}.mp3")+
                     (.17 if i<7 else .28),3) for i in range(8)]
    if any(not 4<=x<=42 for x in durations):
        raise RuntimeError("Candidate narration has an unsafe length")

    # Use the existing deterministic natural-effects + ducking mixer, but with
    # a story-specific key, new narration and per-scene timing.
    tane_sound.KEY=KEY
    tane_sound.out=ROOT_OUT
    tane_sound.merge_voice(durations)
    tane_sound.original_soundscape(durations)
    tane_sound.master_mix(durations)

    timing={"story":story["key"],"durations":durations,
            "voice":profile["model"],"revision":"AutoReview1",
            "approval":"pending; never publish without WhatsApp approval"}
    (ROOT_OUT/"timing.json").write_text(
        json.dumps(timing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    (ROOT_OUT/"story.json").write_text(
        json.dumps(story,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print("Rendered 8 NEW cinematic narration clips:",round(sum(durations),2),"seconds")


if __name__=="__main__":
    main()
