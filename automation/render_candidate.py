#!/usr/bin/env python3
"""Render an automatically drafted film solely for WhatsApp HUMAN review.

Consumes the separate original storyboard + measured V31 narration + V33
actor stage. A signed WhatsApp approval is REQUIRED in a distinct workflow.
This renderer has no Instagram/Buffer publish code.
"""
from __future__ import annotations
import base64
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import threading

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"automation"/"output"
FPS=24
MAX_SIZE=15*1024*1024


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


def render():
    storyboard=json.loads((OUT/"story.json").read_text(encoding="utf-8"))
    timing=json.loads((OUT/"timing.json").read_text(encoding="utf-8"))
    durations=timing["durations"]
    if storyboard["key"]!=timing["story"] or len(durations)!=8:
        raise ValueError("Story/audio mismatch or missing scenes")
    if timing["voice"]!="en-GB-RyanNeural":
        raise ValueError("Approved cinematic narrator missing")
    total=sum(durations)
    server=ThreadingHTTPServer(
        ("127.0.0.1",0),functools.partial(Quiet,directory=str(ROOT))
    )
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as browser_tool:
            browser=browser_tool.chromium.launch(
                executable_path=shutil.which("chromium"),args=["--no-sandbox"]
            )
            page=browser.new_page(viewport={"width":540,"height":960})
            errors=[];page.on("pageerror",lambda err:errors.append(str(err)))
            page.goto(f"http://127.0.0.1:{server.server_port}/automation/review.html",
                      wait_until="networkidle")
            page.wait_for_function(
                "() => window.AutoPurakau && window.AutoPurakau.getStory()",timeout=15000
            )
            loaded=page.evaluate("() => AutoPurakau.getDurations()")
            if len(loaded)!=8 or any(abs(a-b)>.001 for a,b in zip(loaded,durations)):
                raise RuntimeError("Browser animation not aligned to cinematic narration")
            stills=OUT/"stills";stills.mkdir(exist_ok=True)
            elapsed=0;hashes=[]
            for i,secs in enumerate(durations):
                page.evaluate("(t) => AutoPurakau.drawAt(t)",elapsed+.5*secs)
                path=stills/f"scene-{i+1:02}.png"
                page.locator("#candidate-stage").screenshot(path=str(path))
                hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
                elapsed+=secs
            if len(set(hashes))!=8:
                raise RuntimeError("At least two auto-animated scenes look identical")
            if errors:raise RuntimeError("Pixel-stage errors: "+repr(errors))
            silent=OUT/"auto-silent.mp4"
            video=OUT/"purakau-review.mp4"
            pipe=subprocess.Popen([
                "ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","image2pipe","-framerate",str(FPS),"-i","-",
                "-an","-c:v","libx264","-preset","veryfast","-crf","25",
                "-pix_fmt","yuv420p",str(silent)
            ],stdin=subprocess.PIPE)
            try:
                for i in range(math.ceil(total*FPS)):
                    frame=min(total-.001,i/FPS)
                    png=page.evaluate(
                        "(t) => {AutoPurakau.drawAt(t); return "
                        "document.getElementById('candidate-stage').toDataURL('image/png').split(',')[1]}",
                        frame
                    )
                    pipe.stdin.write(base64.b64decode(png))
                    if i%250==0:print("Generated automated review frames",i,flush=True)
                pipe.stdin.close()
                if pipe.wait()!=0:raise RuntimeError("Animated pixel-frame encoding failed")
            except BaseException:
                pipe.kill();pipe.wait();raise
            audio=OUT/"auto-review-mix-balanced.mp3"
            subprocess.run([
                "ffmpeg","-hide_banner","-loglevel","error","-y",
                "-i",str(silent),"-i",str(audio),
                "-map","0:v:0","-map","1:a:0","-c:v","copy",
                "-c:a","aac","-b:a","128k","-t",str(total),
                "-movflags","+faststart",str(video)
            ],check=True)
            silent.unlink(missing_ok=True)
            if video.stat().st_size>MAX_SIZE:
                raise RuntimeError("WhatsApp video exceeds safe 15 MiB limit; don't send a broken template")
            report=json.loads(subprocess.check_output([
                "ffprobe","-v","error","-print_format","json",
                "-show_entries","stream=codec_type,width,height,r_frame_rate:"
                "format=duration,size",str(video)
            ],text=True))
            visual=next((s for s in report["streams"] if s["codec_type"]=="video"),None)
            audio_stream=next((s for s in report["streams"] if s["codec_type"]=="audio"),None)
            if not visual or not audio_stream or (visual["width"],visual["height"])!=(540,960):
                raise RuntimeError("Review needs portrait H.264 with AAC narration")
            if abs(float(report["format"]["duration"])-total)>.65:
                raise RuntimeError("Narration and picture lengths differ")
            sha=hashlib.sha256(video.read_bytes()).hexdigest()
            metadata={"story_id":story["key"],"title":story["title"],
                      "video_file":video.name,"video_sha256":sha,
                      "duration":round(total,2),"bytes":video.stat().st_size,
                      "status":"pending-human-approval",
                      "sources":story["sources"],"fps":FPS,
                      "narrator":timing["voice"],
                      "warning":story["cultural_warning"]}
            (OUT/"manifest.json").write_text(
                json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
            )
            print("Ready for WhatsApp human review:",story["title"],sha,flush=True)
            browser.close()
            return video
    finally:
        server.shutdown();server.server_close()


if __name__=="__main__":render()
