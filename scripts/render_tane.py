"""Render original Tāne and the First Light pixel film to portrait H.264/AAC MP4.

The narrator, measured 8-scene timeline and atmospheric mix come from
scripts/tane_sound.py. No public upload or social post occurs here.
"""
from __future__ import annotations

import argparse
import base64
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import shutil
import subprocess
import threading

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
KEY="tane-nz"
FPS=24
VIDEO=ROOT/"videos"
REVIEW=ROOT/"tane-review"


class QuietHTTP(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def validate_inputs():
    timing=json.loads((ROOT/"audio"/f"{KEY}-timing.json").read_text(encoding="utf-8"))
    if timing.get("story")!=KEY or timing.get("voice")!="en-GB-RyanNeural":
        raise RuntimeError("Only the approved V31 cinematic Ryan narrator is allowed")
    durations=timing.get("durations")
    if not isinstance(durations,list) or len(durations)!=8 or not all(
        isinstance(x,(float,int)) and math.isfinite(x) and 4<=x<=42 for x in durations
    ):
        raise RuntimeError("Missing eight measured valid narration durations")
    soundtrack=ROOT/"audio"/f"{KEY}-mix-balanced.mp3"
    if not soundtrack.is_file() or soundtrack.stat().st_size<40_000:
        raise RuntimeError("Missing finished cinematic narration + effects MP3")
    return durations


def render():
    durations=validate_inputs()
    total=sum(durations)
    VIDEO.mkdir(exist_ok=True)
    (REVIEW/"stills").mkdir(parents=True,exist_ok=True)
    service=ThreadingHTTPServer(
        ("127.0.0.1",0),functools.partial(QuietHTTP,directory=str(ROOT))
    )
    thread=threading.Thread(target=service.serve_forever,daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(
                executable_path=shutil.which("chromium"),
                args=["--no-sandbox"]
            )
            page=browser.new_page(viewport={"width":540,"height":960},device_scale_factor=1)
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{service.server_port}/tane.html",
                      wait_until="networkidle")
            page.wait_for_function(
                "() => window.TaneFilm && window.TaneFilm.getStory() && "
                "window.TaneFilm.getDurations().length === 8",
                timeout=15000,
            )
            manifest=page.evaluate("() => window.TaneFilm.getDurations()")
            if any(abs(manifest[i]-durations[i])>.001 for i in range(8)):
                raise RuntimeError("Browser story timings do not match cinematic MP3")
            if errors:
                raise RuntimeError("Storyboard crashed: "+repr(errors))
            # V33: an enlarged actor look-book gives iPad reviewers a readable
            # view of faces, outfit layers, hands and the bracing silhouette.
            # This is a character study, not a source of culturally authentic
            # garments or a public-approved representation.
            actor_board=page.evaluate("""() => {
              if(!window.TaneCharacters || TaneCharacters.version!==33)
                throw new Error('Detailed V33 actors missing');
              const canvas=document.createElement('canvas');
              canvas.width=540;canvas.height=950;
              const c=canvas.getContext('2d');
              c.fillStyle='#111b2c';c.fillRect(0,0,540,950);
              c.textAlign='left';c.fillStyle='#e8ca90';
              c.font='bold 25px system-ui';
              c.fillText('TĀNE • CHARACTER STUDIES',18,38);
              c.font='14px system-ui';c.fillStyle='#bdd4d5';
              c.fillText('V33 articulated original pixel actors • preview only',18,61);
              const cards=[
                ['Tāne','tane','wonder','wonder',.85],
                ['Tāne pushing sky','tane','push','strain',1.2],
                ['Tāwhirimātea','tawhirimatea','storm','angry',.8],
                ['Atua of the earth','earth','reach','fear',.84],
                ['Brother • ochre','ochre','strain','strain',.9],
                ['Brother • river','river','argue','surprise',1.0]
              ];
              for(let i=0;i<cards.length;i++){
                const [title,role,action,emotion,time]=cards[i];
                const col=i%2,row=Math.floor(i/2),
                      x=14+col*267,y=82+row*277;
                c.fillStyle='#233343';c.fillRect(x,y,252,262);
                c.strokeStyle='#8d8c69';c.lineWidth=1;c.strokeRect(x,y,252,262);
                c.fillStyle='#d5e1d4';c.font='bold 15px system-ui';
                c.fillText(title,x+10,y+23);
                c.font='12px system-ui';c.fillStyle='#e4c791';
                c.fillText('Action: '+action+' • '+emotion,x+10,y+42);
                c.fillStyle='#33483e';c.fillRect(x+1,y+228,250,32);
                c.strokeStyle='#667d75';c.beginPath();
                c.moveTo(x+14,y+231);c.lineTo(x+239,y+231);c.stroke();
                const size=role==='tane'&&action==='push'?2.25:2.30;
                TaneCharacters.draw(c,{role,action,expression:emotion,
                  x:x+120,y:y+228,scale:size,t:time,phase:.7});
                c.font='11px system-ui';c.fillStyle='#9cadaa';
                c.fillText('New original pixels',x+10,y+254);
              }
              c.fillStyle='#92a7a3';c.font='12px system-ui';
              c.fillText('No borrowed game sprites or invented customary symbols',18,934);
              return canvas.toDataURL('image/png').split(',')[1];
            }""")
            (REVIEW/"tane-v33-character-studies.png").write_bytes(
                base64.b64decode(actor_board)
            )
            # Eight stills let the creator inspect the visual sequence first.
            scene_start=0.
            for i,d in enumerate(durations):
                timestamp=scene_start+d*.54
                page.evaluate("(t) => TaneFilm.drawAt(t)",timestamp)
                page.locator("#tane-stage").screenshot(
                    path=str(REVIEW/"stills"/f"tane-scene-{i+1:02}.png")
                )
                scene_start+=d
            # Ensure each visual scene actually differs.
            checksums=[]
            import hashlib
            for shot in sorted((REVIEW/"stills").glob("*.png")):
                checksums.append(hashlib.sha256(shot.read_bytes()).hexdigest())
            if len(set(checksums))!=8:
                raise RuntimeError("At least two rendered scenes look identical")
            silent=VIDEO/f"{KEY}-picture.mp4"
            output=VIDEO/f"{KEY}-balanced.mp4"
            command=[
                "ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","image2pipe","-framerate",str(FPS),
                "-i","-","-an",
                "-c:v","libx264","-preset","faster",
                "-crf","19","-pix_fmt","yuv420p",
                str(silent)
            ]
            process=subprocess.Popen(command,stdin=subprocess.PIPE)
            try:
                if process.stdin is None:raise RuntimeError("Cannot stream PNGs to FFmpeg")
                frames=math.ceil(total*FPS)
                for frame in range(frames):
                    timestamp=min(total-.001,frame/FPS)
                    b64=page.evaluate(
                        "(t) => {TaneFilm.drawAt(t);return "
                        "document.getElementById('tane-stage').toDataURL('image/png').split(',')[1]}",
                        timestamp
                    )
                    process.stdin.write(base64.b64decode(b64))
                    if frame%240==0:print(f"Pixel frames: {frame}/{frames}",flush=True)
                process.stdin.close()
                if process.wait()!=0:
                    raise RuntimeError("Tāne pixel frame H.264 encode failed")
            except BaseException:
                process.kill();process.wait()
                raise
            finally:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
            soundtrack=ROOT/"audio"/f"{KEY}-mix-balanced.mp3"
            subprocess.run([
                "ffmpeg","-hide_banner","-loglevel","error","-y",
                "-i",str(silent),"-i",str(soundtrack),
                "-map","0:v:0","-map","1:a:0",
                "-c:v","copy","-c:a","aac","-b:a","160k",
                "-t",str(total),"-movflags","+faststart",str(output)
            ],check=True)
            silent.unlink(missing_ok=True)
            if errors:raise RuntimeError("Browser errors: "+repr(errors))
            probe=json.loads(subprocess.check_output([
                "ffprobe","-v","error","-print_format","json",
                "-show_entries","stream=codec_type,width,height,r_frame_rate:"
                "format=duration,size",str(output)
            ],text=True))
            streams=probe.get("streams",[])
            visual=next((x for x in streams if x.get("codec_type")=="video"),None)
            speech=next((x for x in streams if x.get("codec_type")=="audio"),None)
            if not visual or not speech or visual["width"]!=540 or visual["height"]!=960:
                raise RuntimeError("Final film must be playable portrait H.264/AAC with sound")
            if abs(float(probe["format"]["duration"])-total)>.6:
                raise RuntimeError("Final film does not match new narration timeline")
            report={
                "story":"Tāne and the First Light",
                "animation_version":"V33 detailed articulated pixel actors",
                "character_study":"tane-v33-character-studies.png",
                "video":output.name,
                "duration_seconds":round(total,2),
                "scenes":len(durations),
                "fps":FPS,
                "resolution":"540x960",
                "narrator":"en-GB-RyanNeural",
                "status":"review-only (not posted to Instagram)",
                "scene_durations":durations,
                "scene_still_checksums":checksums
            }
            (REVIEW/"film-report.json").write_text(
                json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
            )
            print(json.dumps(report,ensure_ascii=False),flush=True)
            browser.close()
            return output
    finally:
        service.shutdown()
        service.server_close()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Render original Tāne pixel film with narration")
    parser.parse_args()
    render()
