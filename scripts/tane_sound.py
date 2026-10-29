"""Generate original Tāne and the First Light film narration and soundscape.

The narrator is the approved V31 cinematic male profile (en-GB-RyanNeural).
Outputs only in the Actions workspace. No Git push / Releases / Instagram API.
"""
from __future__ import annotations

import argparse
import array
import asyncio
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import wave

from v31_storyteller import PROFILES, generate_edge

ROOT=Path(__file__).resolve().parents[1]
STORY_PATH=ROOT/"stories/tane.json"
SAMPLE_RATE=22050
KEY="tane-nz"
NOISE_SEED=319582
out=ROOT/"audio"


def ffmpeg(*args):
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                    *[str(x) for x in args]],check=True)


def seconds(path):
    n=float(subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)
    ],text=True).strip())
    if not 1<=n<=50:
        raise ValueError(f"Invalid scene duration {n:.3f}s: {path}")
    return n


def validate_story():
    story=json.loads(STORY_PATH.read_text(encoding="utf-8"))
    if story.get("key")!=KEY or len(story.get("scenes",[]))!=8:
        raise ValueError("Expected exact eight-scene Tāne storyboard")
    for scene in story["scenes"]:
        if not isinstance(scene.get("narration"),str) or len(scene["narration"])<30:
            raise ValueError("Empty or invalid narrative scene")
    return story


async def narrator(story):
    profile=PROFILES["cinematic"]
    for i,scene in enumerate(story["scenes"]):
        output=out/f"{KEY}-{i+1}.mp3"
        print(f"Voice scene {i+1}/8 — cinematic Ryan: {scene['title']}",flush=True)
        with tempfile.TemporaryDirectory(prefix="tane-narration-") as scratch:
            await generate_edge(scene["narration"],output,profile["model"],i,
                                profile,Path(scratch))
        if not output.is_file() or seconds(output)<2:
            raise RuntimeError(f"Narration failed for scene {i+1}")
    return profile


def merge_voice(durations):
    # Scene-aligned audio clock; every scene has a small 0.17-second
    # breath between lines, and video uses the same measured durations.
    args=[];pieces=[];t=0.
    for i,dt in enumerate(durations):
        args+=["-i",out/f"{KEY}-{i+1}.mp3"]
        pieces.append(f"[{i}:a]adelay={round(t*1000)}:all=1[v{i}]")
        t+=dt
    graph=";".join(pieces)+ ";" + "".join(f"[v{i}]" for i in range(8))+ (
        "amix=inputs=8:duration=longest:normalize=0,"
        "highpass=f=72,acompressor=threshold=0.16:ratio=1.5:"
        "attack=20:release=180,alimiter=limit=0.90:level=0:latency=1,"
        f"apad,atrim=duration={t:.3f}[out]"
    )
    ffmpeg(*args,"-filter_complex",graph,"-map","[out]",
           "-c:a","libmp3lame","-q:a","3",out/f"{KEY}-full.mp3")


def original_soundscape(durations):
    """Deterministic, low-volume nature foley — no copyrighted music/samples."""
    total=sum(durations)
    frames=int((total+.2)*SAMPLE_RATE)
    values=array.array("f",[0.0])*frames
    rng=random.Random(NOISE_SEED)
    starts=[];cursor=0.
    for d in durations:
        starts.append(cursor);cursor+=d

    def add_noise(at,length,gain,lowpass=.97,fade=.08):
        a=max(0,int(at*SAMPLE_RATE))
        n=max(0,min(int(length*SAMPLE_RATE),frames-a))
        if n<=0:return
        smooth=0.0
        for k in range(n):
            white=rng.random()*2-1
            smooth=lowpass*smooth+(1-lowpass)*white
            part=k/max(1,n-1)
            env=min(1,part/max(fade,.001),(1-part)/max(fade,.001))
            values[a+k]+=(smooth*3.5+white*.12)*gain*max(0,env)

    def bird(at,shift=0):
        a=max(0,int(at*SAMPLE_RATE));length=int(.25*SAMPLE_RATE)
        for k in range(min(length,frames-a)):
            u=k/length
            tone=900+shift+u*390+40*math.sin(u*9)
            value=math.sin(2*math.pi*(tone*u*.25))
            envelope=math.sin(math.pi*u)**2
            values[a+k]+=value*envelope*.012

    def rumble(at,length=1.5,gain=.065):
        a=max(0,int(at*SAMPLE_RATE));length=int(length*SAMPLE_RATE)
        for k in range(min(length,frames-a)):
            u=k/length
            tone=47+30*(1-u)
            env=math.sin(math.pi*u)**2
            values[a+k]+=math.sin(2*math.pi*tone*(k/SAMPLE_RATE))*env*gain

    # First darkness and growing tension: quiet, enclosed air.
    add_noise(starts[0],durations[0],.013,.993)
    add_noise(starts[1],durations[1],.018,.987)
    add_noise(starts[2],durations[2],.032,.971)
    add_noise(starts[3],durations[3],.029,.982)
    for n in range(4):
        rumble(starts[3]+durations[3]*(.17+n*.22),.28,.025)
    # Tāne's push: throbbing earth, then luminous opening.
    add_noise(starts[4],durations[4],.040,.984)
    for n in range(3):rumble(starts[4]+durations[4]*(.38+n*.17),.5,.045)
    add_noise(starts[5]+durations[5]*.28,durations[5]*.7,.024,.974)
    # Tāwhirimātea's wind and thunder; still underneath spoken narration.
    add_noise(starts[6],durations[6],.058,.961)
    add_noise(starts[6]+durations[6]*.30,durations[6]*.6,.042,.95)
    rumble(starts[6]+durations[6]*.50,1.8,.09)
    # The world breathes and bird calls return at the end.
    add_noise(starts[7],durations[7],.023,.991)
    for i in range(7):
        bird(starts[7]+.7+i*1.55,shift=(i%3)*75)
    wav=out/f"{KEY}-foley-temporary.wav"
    pcm=array.array("h",(max(-32768,min(32767,int(v*32767))) for v in values))
    if sys.byteorder!="little":pcm.byteswap()
    with wave.open(str(wav),"wb") as target:
        target.setnchannels(1);target.setsampwidth(2)
        target.setframerate(SAMPLE_RATE);target.writeframes(pcm.tobytes())
    ffmpeg("-i",wav,"-af","highpass=f=45,lowpass=f=5200",
           "-c:a","libmp3lame","-q:a","4",out/f"{KEY}-sfx.mp3")
    wav.unlink()


def master_mix(durations):
    total=sum(durations)
    for flavor,level in (("soft",.75),("balanced",1.35),("bold",1.95)):
        output=out/f"{KEY}-mix-{flavor}.mp3"
        graph=(
            f"[1:a]volume={level},highpass=f=65[ambience];"
            "[ambience][0:a]sidechaincompress=threshold=0.045:ratio=3.3:"
            "attack=20:release=250[ducked];"
            "[0:a]volume=0.96[voice];"
            "[voice][ducked]amix=inputs=2:duration=first:normalize=0,"
            "alimiter=limit=0.91:level=0:latency=1[out]"
        )
        ffmpeg("-i",out/f"{KEY}-full.mp3","-i",out/f"{KEY}-sfx.mp3",
               "-filter_complex",graph,"-map","[out]","-c:a","libmp3lame",
               "-q:a","3",output)
        actual=float(subprocess.check_output([
            "ffprobe","-v","error","-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1",str(output)
        ],text=True).strip())
        if abs(actual-total)>.45:
            raise RuntimeError(f"{flavor} mix length {actual:.2f}s differs from film {total:.2f}s")
    print(f"Original Tāne soundscape prepared: {total:.2f}s",flush=True)


def main():
    parser=argparse.ArgumentParser(description="Make original cinematic Tāne soundtrack")
    parser.add_argument("--reuse-voice",action="store_true",
                        help="Reuse this film's existing scene clips without re-synthesizing")
    args=parser.parse_args()
    story=validate_story()
    out.mkdir(exist_ok=True)
    if not args.reuse_voice:
        profile=asyncio.run(narrator(story))
    else:
        profile=PROFILES["cinematic"]
        if any(not (out/f"{KEY}-{n}.mp3").exists() for n in range(1,9)):
            raise RuntimeError("All eight existing Tāne scene clips must exist for reuse")
    durations=[round(seconds(out/f"{KEY}-{i+1}.mp3")+(.17 if i<7 else .28),3)
               for i in range(8)]
    if any(x<4 or x>42 for x in durations):
        raise RuntimeError("Narration scene outside allowed animation timing range")
    merge_voice(durations)
    original_soundscape(durations)
    master_mix(durations)
    (out/f"{KEY}-timing.json").write_text(json.dumps({
        "story":KEY,
        "revision":1,
        "durations":durations,
        "voice":profile["model"],
        "profile":"cinematic",
        "description":"V31-approved Ryan cinematic English narration; Māori pronunciation unverified",
        "source":"stories/tane.json",
        "approval":"review-only; not authorized for Instagram"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Finished 8-scene original audio; total time",sum(durations),flush=True)


if __name__=="__main__":
    main()
