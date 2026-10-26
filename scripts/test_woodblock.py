"""Compare the Great Fish style test against the same narration and caption clock."""
import json
import os
import shutil
from playwright.sync_api import sync_playwright

base = os.environ.get('CLAYSTORY_TEST_URL', 'http://127.0.0.1:8000')
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(base)
    page.wait_for_function('cloudAudioAvailable && mixedFxReady')
    timing = page.request.get(base+'/audio/fish-nz-timing.json').json()['durations']
    page.wait_for_function('d=>JSON.stringify(timelineDurations())===JSON.stringify(d)', arg=timing)
    assert page.locator('#visualstyle').input_value() == 'pixel'
    assert page.locator('#captionsenabled').is_checked()
    assert page.locator('#savefilm').is_enabled()
    result = page.evaluate('''()=>{
        const style=document.querySelector('#visualstyle'),original=ctx.fillText;
        const narration=JSON.stringify(scenes),durations=JSON.stringify(timelineDurations()),mix=selectedMixUrl();
        let captions=[];
        ctx.fillText=function(text,x,y){if(y>852)captions.push(text);return original.call(this,text,x,y)};
        function frame(styleName,t){
            style.value=styleName;captions=[];draw(t);
            const bytes=ctx.getImageData(0,74,540,760).data;let hash=0;
            for(let i=0;i<bytes.length;i+=19)hash=(hash*31+bytes[i])|0;
            return {hash,captions:captions.join(' ')};
        }
        let start=0,ms=0;
        try {
            for(let scene=0;scene<8;scene++){
                const t=start+timelineDurations()[scene]*.55;
                const pixel=frame('pixel',t),wood=frame('woodblock',t);
                if(pixel.hash===wood.hash)throw Error('Style did not change scene '+scene);
                if(!wood.captions||pixel.captions!==wood.captions)throw Error('Caption clock changed');
                if(wood.hash!==frame('woodblock',t).hash)throw Error('Nondeterministic paper or motion');
                if(wood.hash===frame('woodblock',t+.3).hash)throw Error('Static artwork');
                if(pixel.hash!==frame('pixel',t).hash)throw Error('Pixel artwork was changed by Woodblock');
                style.value='woodblock';const before=performance.now();
                for(let j=0;j<12;j++)draw(t+j/24);ms+=performance.now()-before;
                start+=timelineDurations()[scene];
            }
            if(narration!==JSON.stringify(scenes)||durations!==JSON.stringify(timelineDurations())||mix!==selectedMixUrl())throw Error('Story or audio changed');
            document.querySelector('#captionsenabled').checked=false;
            captions=[];draw(3);if(captions.length)throw Error('CC toggle broken');
            document.querySelector('#captionsenabled').checked=true;
            style.value='pixel';
            return {scenes:8,sameCaptions:true,sameNarration:true,pixelPreserved:true,deterministic:true,averageRenderMs:ms/96};
        } finally {ctx.fillText=original;}
    }''')
    page.select_option('#visualstyle', 'woodblock')
    assert page.locator('#savefilm').is_disabled()
    for scene in range(8):
        page.evaluate('''i=>draw(timelineDurations().slice(0,i).reduce((a,b)=>a+b,0)+timelineDurations()[i]*.55)''', scene)
        page.locator('#stage').screenshot(path=f'/tmp/v24-woodblock-{scene+1}.png')
    page.click('#play')
    page.wait_for_function('continuousNarration && continuousNarration.currentTime>.4')
    page.evaluate('window.styleTestAudio=continuousNarration')
    before = page.evaluate('continuousNarration.currentTime')
    for style in ['pixel', 'woodblock', 'pixel', 'woodblock']:
        page.select_option('#visualstyle', style)
        assert page.evaluate('continuousNarration===window.styleTestAudio && !continuousNarration.paused')
    page.wait_for_timeout(300)
    assert page.evaluate('continuousNarration.currentTime') > before
    page.click('#stop')
    page.click('#loadmaui')
    page.wait_for_function('chosen===mauiChoice && cloudAudioAvailable && mixedFxReady')
    assert page.locator('#visualstyle').is_disabled()
    assert page.locator('#savefilm').is_enabled()
    assert not page.evaluate('isWoodblockStyle()')
    page.click('#play')
    page.wait_for_function('continuousNarration && continuousNarration.currentTime>.3')
    page.click('#stop')
    page.click('#loadfish')
    assert page.locator('#visualstyle').is_enabled()
    assert page.locator('#visualstyle').input_value() == 'woodblock'
    page.select_option('#visualstyle', 'pixel')
    assert page.locator('#savefilm').is_enabled()
    assert not errors, errors
    print(json.dumps(dict(result, liveStyleSwitching=True, sunPlayback=True, errors=errors)))
    browser.close()
