"""Browser regression: V33 characters must visibly animate and seek deterministically.

Run before the expensive cinematic voice synthesis. Uses existing Playwright
Chromium in the read-only Tāne film workflow.
"""
from __future__ import annotations
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


class QuietHTTP(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def main():
    server=ThreadingHTTPServer(
        ("127.0.0.1",0),functools.partial(QuietHTTP,directory=str(ROOT))
    )
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(
                executable_path=shutil.which("chromium"),args=["--no-sandbox"])
            page=browser.new_page(viewport={"width":480,"height":850})
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/tane.html",
                      wait_until="networkidle")
            page.wait_for_function(
                "() => window.TaneFilm && window.TaneFilm.getStory() && "
                "window.TaneCharacters && window.TaneFilm.version === 33"
            )
            result=page.evaluate("""() => {
              const ch=window.TaneCharacters,film=window.TaneFilm;
              const actions=['idle','listen','argue','reach','strain','push','wonder','storm'];
              if(ch.version!==33)throw new Error('Wrong character rig version');
              if(Object.keys(ch.palette).length<5)throw new Error('Missing distinct role palettes');
              for(const a of actions){
                if(ch.actions[a].length<4)throw new Error('Too few poses for '+a);
                const one=JSON.stringify(ch.sample(a,0.12));
                const two=JSON.stringify(ch.sample(a,.32));
                if(one===two)throw new Error('Sprite frame does not animate: '+a);
                if(one!==JSON.stringify(ch.sample(a,.12)))
                  throw new Error('Nondeterministic sprite track: '+a);
              }
              function checksum(bytes){
                let h=2166136261>>>0;
                for(let i=0;i<bytes.length;i+=11)h=Math.imul(h^bytes[i],16777619)>>>0;
                return h;
              }
              const art=document.createElement('canvas');
              art.width=240;art.height=240;const ctx=art.getContext('2d');
              const roles=[
                ['tane','strain','push'],
                ['tawhirimatea','angry','storm'],
                ['earth','calm','reach'],
                ['river','wonder','wonder'],
                ['ochre','fear','argue'],
              ];
              const poses={};
              for(const [role,emotion,action] of roles){
                const hashes=[];
                for(const at of [1.11,1.35,1.61]){
                  ctx.clearRect(0,0,240,240);
                  ch.draw(ctx,{x:120,y:202,scale:2,t:at,role,
                               expression:emotion,action,phase:.55});
                  hashes.push(checksum(ctx.getImageData(0,0,240,240).data));
                }
                if(new Set(hashes).size<2)
                  throw new Error('Character art did not visibly change: '+role);
                poses[role]=hashes;
              }
              const d=film.getDurations();
              if(d.length!==8)throw new Error('Storyboard has wrong count');
              const snapshots=[];
              let start=0;
              for(let i=0;i<8;i++){
                const at=start+d[i]*.51;
                const scene=film.drawAt(at);
                if(scene.index!==i)throw new Error('Wrong scene '+i);
                const data=document.getElementById('tane-stage')
                                   .getContext('2d').getImageData(0,90,540,680).data;
                snapshots.push(checksum(data));
                start+=d[i];
              }
              if(new Set(snapshots).size!==8)
                throw new Error('All eight scenes need different visual artwork');
              for(let i=7;i>=0;i--){
                const at=d.slice(0,i).reduce((a,b)=>a+b,0)+d[i]*.51;
                film.drawAt(at);
              }
              let startAgain=0;
              const reread=[];
              for(let i=0;i<8;i++){
                film.drawAt(startAgain+d[i]*.51);
                reread.push(checksum(document.getElementById('tane-stage')
                  .getContext('2d').getImageData(0,90,540,680).data));
                startAgain+=d[i];
              }
              if(JSON.stringify(reread)!==JSON.stringify(snapshots))
                throw new Error('Backwards seek changed previously rendered frames');
              return {version:ch.version,distinctRolePalettes:Object.keys(ch.palette).length,
                      animatedActionCycles:actions.length,animatedRoles:Object.keys(poses),
                      sceneHashes:snapshots,backwardsScrub:true};
            }""")
            if errors:raise RuntimeError("V33 browser errors "+json.dumps(errors))
            print("V33 character-motion quality checks",json.dumps(result),flush=True)
            browser.close()
    finally:
        server.shutdown();server.server_close()


if __name__=="__main__":
    main()
