from playwright.sync_api import sync_playwright
import json
import os
import shutil
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':820,'height':1180},is_mobile=True,has_touch=True)
 errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
 page.goto(os.environ.get('CLAYSTORY_TEST_URL','http://127.0.0.1:8000'));page.wait_for_timeout(800)
 assert page.locator('#scenes .scene').count()==8
 assert page.evaluate('chosen===fishChoice')
 manifest=page.request.get('http://127.0.0.1:8000/audio/fish-nz-timing.json').json()
 if manifest.get('revision') != 18 or len(manifest['durations']) != 8:
  assert not page.evaluate('cloudAudioAvailable'), 'Old six-scene soundtrack must be rejected'
 results=page.evaluate('''()=>{let result=[];for(let i=0;i<8;i++){let start=fishDurations.slice(0,i).reduce((a,b)=>a+b,0), hashes=[];for(let phase of [.2,.5,.8]){draw(start+fishDurations[i]*phase);let bytes=ctx.getImageData(0,70,540,780).data,hash=0;for(let k=0;k<bytes.length;k+=31)hash=(hash*31+bytes[k])|0;hashes.push(hash)}if(new Set(hashes).size!==3)throw Error('Static scene '+i);result.push(hashes)}return result}''')
 page.evaluate('draw(fishDurations.slice(0,7).reduce((a,b)=>a+b,0)+fishDurations[7]*.8)');page.locator('#stage').screenshot(path='/tmp/v18-island.png')
 page.click('#loadmaui');page.wait_for_timeout(500)
 assert page.locator('#scenes .scene').count()==6
 assert page.evaluate('cloudAudioAvailable')
 page.evaluate('''()=>{let cursor=0;for(let d of mauiDurations){draw(cursor+d*.5);cursor+=d}}''')
 page.click('#play');page.wait_for_timeout(1500)
 assert page.evaluate('continuousNarration && continuousNarration.currentTime>0')
 assert page.evaluate("selectedMixUrl().includes('mix-balanced')")
 page.click('#stop')
 for title in ['What if the Sun disappeared for 24 hours?','What if the Moon disappeared?','What if the oceans disappeared?']:
  page.locator('#topic').fill(title);page.evaluate('selectStory()');page.evaluate('for(let t=0;t<48;t+=4)draw(t)');page.click('#stop')
 assert not errors, errors
 print(json.dumps({'eightAnimatedScenes':len(results),'sunScenes':6,'sunAudioPlayback':True,'libraryStories':3,'errors':errors}))
 browser.close()
