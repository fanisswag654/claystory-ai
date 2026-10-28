"""V29 integration checks for local Tween.js, frame sprites, and MP4-safe timing."""
import json
import os
import shutil

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CLAYSTORY_TEST_URL", "http://127.0.0.1:8000").rstrip("/")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=shutil.which("chromium"), args=["--no-sandbox"]
    )
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    for path in ("vendor/tween.umd.js", "scripts/v29_motion.js"):
        response = page.request.get(f"{BASE}/{path}")
        assert response.status == 200, f"{path} HTTP {response.status}"

    page.goto(BASE)
    page.wait_for_function(
        "() => window.TWEEN && window.ClayMotionV29 && "
        "window.ClayMotionV29.version === 29 && typeof draw === 'function'"
    )

    result = page.evaluate("""() => {
      const motion=window.ClayMotionV29;
      if(!window.TWEEN || !motion)throw Error('V29 motion engine missing');
      const a=motion.tween({x:0,y:10},{x:100,y:50},0,'smooth');
      const mid=motion.tween({x:0,y:10},{x:100,y:50},.5,'smooth');
      const b=motion.tween({x:0,y:10},{x:100,y:50},1,'smooth');
      const back=motion.tween({x:0,y:10},{x:100,y:50},.5,'smooth');
      if(a.x!==0 || a.y!==10 || b.x!==100 || b.y!==50 ||
         Math.abs(mid.x-50)>.000001 || mid.x!==back.x)
        throw Error('Tween.js interpolation not deterministic');

      const actions=['walk','paddle','pull','point','surprise','swim'];
      for(const action of actions){
        const def=motion.registry[action];
        if(!def || def.frames.length<4)throw Error('Incomplete sprite '+action);
        const initial=JSON.stringify(motion.spriteFrame(action,0));
        if(initial===JSON.stringify(motion.spriteFrame(action,1/def.fps)))
          throw Error('Missing sprite-frame movement in '+action);
        if(initial!==JSON.stringify(motion.spriteFrame(action,0)))
          throw Error('Nondeterministic sprite '+action);
      }

      const bytes=ctx.getImageData.bind(ctx);
      function imageHash(t){
        draw(t);
        const data=bytes(0,60,540,792).data;
        let h=2166136261>>>0;
        for(let i=0;i<data.length;i+=47)h=Math.imul(h ^ data[i],16777619)>>>0;
        return h;
      }
      const samples=[1.25, 12.6, 27.3, 39.8, 63.7, 82.5];
      const first=samples.map(imageHash);
      // Deliberately scrub backward to catch mutable tween state.
      for(const time of [...samples].reverse()) imageHash(time);
      const second=samples.map(imageHash);
      if(first.some((hash,i)=>hash!==second[i]))
        throw Error('V29 frame changed after backward scrub');
      if(new Set(first).size < 4)
        throw Error('Motion-rendered scenes look unexpectedly identical');
      return {version:motion.version,tween:'@tweenjs/tween.js v25',
        actions,checkedFrames:samples.length,scrubDeterminism:true,
        frameHash:first};
    }""")
    assert not errors, errors
    print(json.dumps({"result": result, "browserErrors": errors}))
    browser.close()
