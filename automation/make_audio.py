#!/usr/bin/env python3
"""Generate VoiceStudio male narration for one NEW source-backed story.

VoiceStudio synthesizes fresh scene text; the original sound mixer uses the
measured timings. No previous film soundtrack is copied.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import tane_sound

ROOT_OUT=ROOT/"automation"/"output"
KEY="auto-review"


def make_voice(story):
    from voicestudio_voice import generate_scene
    profile=None
    for i,scene in enumerate(story["scenes"]):
        target=ROOT_OUT/f"{KEY}-{i+1}.mp3"
        print(f"Generating VoiceStudio male narration scene {i+1}/8",flush=True)
        profile=generate_scene(scene["narration"],target)
        if tane_sound.seconds(target)<3:
            raise RuntimeError("Narration scene was too short; refusing candidate")
    return profile


def main():
    story_path=ROOT/"automation"/"candidate-story.json"
    story=json.loads(story_path.read_text(encoding="utf-8"))
    if len(story["scenes"])!=8 or story["review_status"]!="pending-human-approval":
        raise ValueError("Only a pending, eight-scene review candidate can be rendered")
    ROOT_OUT.mkdir(parents=True,exist_ok=True)
    from cinematic_assets import verify_assets
    verify_assets(story["key"])
    profile=make_voice(story)
    story["narrator"]=profile["model"]
    durations=[round(tane_sound.seconds(ROOT_OUT/f"{KEY}-{i+1}.mp3")+
                     (.17 if i<7 else .28),3) for i in range(8)]
    if any(not 4<=x<=42 for x in durations):
        raise RuntimeError("Candidate narration has an unsafe length")

    # Use the existing deterministic natural-effects + ducking mixer, but with
    # a story-specific key, new narration and per-scene timing.
    tane_sound.KEY=KEY
    tane_sound.out=ROOT_OUT
    tane_sound.merge_voice(durations)
    if story["key"]=="mataora-niwareka-moko":
        from moko_soundscape import make_soundscape
        make_soundscape(ROOT_OUT,KEY,durations)
    else:
        tane_sound.original_soundscape(durations)
    tane_sound.master_mix(durations)

    timing={"story":story["key"],"durations":durations,
            "voice":profile["model"],"revision":"VoiceStudio1","pitch_hz":0,"narration_engine":profile,
            "approval":"pending; never publish without verified Telegram approval"}
    (ROOT_OUT/"timing.json").write_text(
        json.dumps(timing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    (ROOT_OUT/"story.json").write_text(
        json.dumps(story,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print("Rendered 8 NEW cinematic narration clips:",round(sum(durations),2),"seconds")


if __name__=="__main__":
    main()
