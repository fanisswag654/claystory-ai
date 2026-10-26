"""Exercise cinematic motion, deterministic export frames, and fish sound preview."""
import json
import os
import shutil
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(os.environ.get('CLAYSTORY_TEST_URL', 'http://127.0.0.1:8000'))
    page.wait_for_function('cloudAudioAvailable && mixedFxReady')
    timing = page.request.get(os.environ.get('CLAYSTORY_TEST_URL', 'http://127.0.0.1:8000') + '/audio/fish-nz-timing.json').json()
    page.wait_for_function('durations=>JSON.stringify(timelineDurations())===JSON.stringify(durations)', arg=timing['durations'])
    result = page.evaluate('''() => {
        function hash(t){
            draw(t);let h=0;const b=ctx.getImageData(0,60,540,792).data;
            for(let j=0;j<b.length;j+=29)h=(h*31+b[j])|0;return h;
        }
        let start=0,frames=0,renderMs=0;
        for(let i=0;i<8;i++){
            const duration=timelineDurations()[i];
            const samples=[.08,.3,.55,.85].map(f=>hash(start+duration*f));
            if(new Set(samples).size!==4)throw Error('Static scene '+i);
            const time=start+duration*.5,first=hash(time);
            if(first===hash(time+.15))throw Error('No continuous motion in scene '+i);
            if(first!==hash(time))throw Error('Nondeterministic export frame '+i);
            const before=performance.now();for(let j=0;j<10;j++)draw(time+j/24);
            renderMs+=performance.now()-before;frames+=10;start+=duration;
        }
        return {scenes:8,continuousMotion:true,deterministic:true,averageRenderMs:renderMs/frames};
    }''')
    for i in range(8):
        page.evaluate('''i=>draw(timelineDurations().slice(0,i).reduce((a,b)=>a+b,0)+timelineDurations()[i]*.6)''', i)
        page.locator('#stage').screenshot(path=f'/tmp/v23-fish-{i+1}.png')
    page.click('#play')
    page.wait_for_function('continuousNarration && continuousNarration.currentTime>.8')
    assert page.evaluate("selectedMixUrl().includes('mix-balanced')")
    # Python's simple HTTP server has no byte-range support (seekable=[0,0]).
    # Use the complete, already verified mix as a Blob for clock/seek validation.
    page.evaluate('''async()=>{
        const blob=await (await fetch(selectedMixUrl())).blob();
        continuousNarration.pause();continuousNarration.src=URL.createObjectURL(blob);
        await continuousNarration.play();
    }''')
    page.wait_for_function('continuousNarration.seekable.length && continuousNarration.seekable.end(0)>80')
    # Every scene can be reached through the same narration clock used in preview.
    for i in range(8):
        page.evaluate('''i=>{continuousNarration.currentTime=timelineDurations().slice(0,i).reduce((a,b)=>a+b,0)+.8}''', i)
        page.wait_for_timeout(180)
        assert page.evaluate('timelineAt(continuousNarration.currentTime).index') == i, page.evaluate('({time:continuousNarration.currentTime,duration:continuousNarration.duration,seekable:Array.from({length:continuousNarration.seekable.length},(_,i)=>[continuousNarration.seekable.start(i),continuousNarration.seekable.end(i)])})')
    page.click('#stop')
    page.locator('#sfxenabled').uncheck()
    page.click('#play')
    page.wait_for_function('continuousNarration && continuousNarration.currentTime>.3')
    assert page.evaluate("continuousNarration.src.includes('fish-nz-full.mp3')")
    page.click('#stop')
    page.locator('#sfxenabled').check()
    page.select_option('#pace', '1.15')
    page.click('#play')
    page.wait_for_function('continuousNarration && continuousNarration.currentTime>.3')
    assert page.evaluate('continuousNarration.playbackRate') == 1.15
    page.click('#stop')
    page.click('#testfx')
    page.wait_for_function('testFxAudio && testFxAudio.currentTime>.2')
    page.evaluate('stopFxTest()')
    assert not errors, errors
    print(json.dumps(dict(result, fishAudioPreview=True, audioSceneSeeking=True, voiceOnly=True, speedControl=True, errors=errors)))
    browser.close()
