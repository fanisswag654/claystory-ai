"""Test the generated pixel stage in Chromium WITHOUT spending API credits."""
from __future__ import annotations
import functools
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright
from prepare_story import source_briefs,build_candidate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"automation"/"output"


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


def main():
    topic=source_briefs()["topics"][0]
    original=[
        "Long ago the people learned that some gifts require courage and patience in times of hardship.",
        "A determined visitor took a long journey and listened closely to the guardian of an ancient gift.",
        "A shining ember made its way from one place to another as the story gained greater meaning.",
        "Beside the rushing water the visitor faced an important test that would change the next step.",
        "An unexpected exchange left the characters worried about the choices they had already made.",
        "The trees and land became part of the challenge as the natural world stirred around them.",
        "Wind and rain passed across the landscape and the storyteller turned toward the final lesson.",
        "In one telling, this story reminds us to care for what is given and understand its meaning.",
    ]
    scenes=[
        {"title":f"ORIGINAL TEST SCENE {i+1}","caption":f"SCENE NUMBER {i+1}",
         "narration":word}
        for i,word in enumerate(original)
    ]
    candidate=build_candidate(topic,scenes)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"story.json").write_text(json.dumps(candidate,ensure_ascii=False))
    (OUT/"timing.json").write_text(json.dumps({
        "durations":[8.0,9.0,8.5,10,9.5,10.5,8.6,9.3],
        "voice":"en-GB-RyanNeural",
    }))
    server=ThreadingHTTPServer(
        ("127.0.0.1",0),functools.partial(Quiet,directory=str(ROOT))
    )
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(
                executable_path=shutil.which("chromium"),args=["--no-sandbox"]
            )
            page=browser.new_page(viewport={"width":540,"height":960})
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/automation/review.html",
                      wait_until="networkidle")
            page.wait_for_function(
                "() => window.AutoPurakau && window.AutoPurakau.getStory()",
                timeout=12000
            )
            durations=page.evaluate("() => AutoPurakau.getDurations()")
            if len(durations)!=8:raise RuntimeError("Not eight cinematic scenes")
            hashes=[]
            elapsed=0
            for i,d in enumerate(durations):
                t=elapsed+d*.56
                page.evaluate("(t)=>AutoPurakau.drawAt(t)",t)
                canvas=page.locator("#candidate-stage").screenshot()
                hashes.append(hashlib.sha256(canvas).hexdigest())
                elapsed+=d
            if len(set(hashes))!=8:
                raise RuntimeError("Generic film scenes are not visually differentiated")
            a=page.locator("#candidate-stage")
            page.evaluate("(t)=>AutoPurakau.drawAt(t)",durations[0]*.4)
            initial=hashlib.sha256(a.screenshot()).hexdigest()
            page.evaluate("(t)=>AutoPurakau.drawAt(t)",elapsed-durations[-1]*.5)
            page.evaluate("(t)=>AutoPurakau.drawAt(t)",durations[0]*.4)
            repeat=hashlib.sha256(a.screenshot()).hexdigest()
            if initial!=repeat:
                raise RuntimeError("Backward scrub changed deterministic film pixels")
            if errors:raise RuntimeError("Automated storyboard browser errors "+str(errors))
            print(json.dumps({"success":True,"eight_unique_scenes":len(set(hashes)),
                              "reverse_seek_deterministic":True,"errors":errors}))
            browser.close()
    finally:
        server.shutdown();server.server_close()


if __name__=="__main__":main()
