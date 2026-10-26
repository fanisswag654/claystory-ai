"""Validate spoken captions and the dedicated safe area for both featured films."""
import os
import shutil
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page.goto(os.environ.get('CLAYSTORY_TEST_URL', 'http://127.0.0.1:8000'))
    assert page.locator('#captionsenabled').is_checked()
    for story, count in [('Fish', 8), ('Maui', 6)]:
        page.evaluate(f'open{story}Story()')
        page.wait_for_function('cloudAudioAvailable && mixedFxReady')
        timing = page.request.get(os.environ.get('CLAYSTORY_TEST_URL', 'http://127.0.0.1:8000') + f'/audio/{story.lower() if story == "Fish" else "maui"}-nz-timing.json').json()
        page.wait_for_function('durations=>JSON.stringify(timelineDurations())===JSON.stringify(durations)', arg=timing['durations'])
        checked = page.evaluate('''() => {
            const original=ctx.fillText;let labels=[];let checked=0,start=0;
            ctx.fillText=function(text,x,y){labels.push({text,x,y,width:this.measureText(text).width});return original.call(this,text,x,y)};
            try {
                for(let i=0;i<scenes.length;i++) {
                    const cues=captionCues(i),sum=cues.reduce((n,c)=>n+c.weight,0);
                    if(cues.flatMap(c=>c.lines).join(' ')!==scenes[i].narration)throw Error('Narration lost');
                    let weight=0;
                    for(const cue of cues){
                        labels=[];
                        const t=start+timelineDurations()[i]*(weight+cue.weight/2)/sum;
                        drawFeaturedSubtitle(i,t);weight+=cue.weight;
                        if(labels.length<1||labels.length>2)throw Error('Two-line limit');
                        if(labels.map(l=>l.text).join(' ')!==cue.lines.join(' '))throw Error('Wrong timed cue');
                        if(labels.some(l=>l.width>452||l.y<870||l.y>940))throw Error('Subtitle outside safe area');
                        checked++;
                    }
                    start+=timelineDurations()[i];
                }
                // CC toggles the subtitle region without changing story or audio selection.
                for(const enabled of [false,true]){
                    document.querySelector('#captionsenabled').checked=enabled;labels=[];draw(.5);
                    if(Boolean(labels.length)!==enabled)throw Error('CC toggle broken');
                }
                return checked;
            } finally {ctx.fillText=original;}
        }''')
        assert checked >= count
        print(f'PASS: {story}: {checked} spoken cues, two-line safe area, narration completeness and CC toggle.')
    browser.close()
