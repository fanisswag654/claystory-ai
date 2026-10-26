"""Check featured subtitle safety, wrapping, cue completeness and canvas state."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('CLAYSTORY_TEST_URL', 'http://127.0.0.1:8000'))
    for story, count in [('Fish', 8), ('Maui', 6)]:
        page.evaluate(f'open{story}Story()')
        page.wait_for_function('cloudAudioAvailable && mixedFxReady')
        result = page.evaluate('''() => {
            const originalFill = ctx.fillText, originalFillPath = ctx.fill;
            let labels = [], boxes = [];
            ctx.fillText = function(text,x,y) {
                labels.push({text,x,y,width:this.measureText(text).width});
                return originalFill.call(this,text,x,y);
            };
            ctx.fill = function(...args) { boxes.push(this.fillStyle);return originalFillPath.apply(this,args); };
            let checked = 0, start = 0;
            try {
                for(let scene=0;scene<scenes.length;scene++) {
                    for(const phase of [.05,.5,.95]) {
                        const t = start + timelineDurations()[scene]*phase;
                        draw(t);
                        // Isolate the subtitle calls from the rest of the artwork.
                        labels=[];boxes=[];
                        const font=ctx.font, baseline=ctx.textBaseline;
                        drawFeaturedSubtitle(scene,t);
                        if(ctx.font!==font || ctx.textBaseline!==baseline)throw Error('Canvas state leaked');
                        if(!labels.length || labels.length>2)throw Error('Caption missing or exceeds two lines');
                        if(labels.map(l=>l.text).join(' ')!==scenes[scene].caption)throw Error('Caption text lost');
                        for(const l of labels) {
                            if(l.width>428 || l.x-l.width/2<56 || l.x+l.width/2>484 || l.y<864 || l.y>911)
                                throw Error('Subtitle outside safe area: '+JSON.stringify(l));
                        }
                        if(boxes.length!==1 || !boxes[0].startsWith('rgba('))throw Error('Missing translucent box');
                        checked++;
                    }
                    start+=timelineDurations()[scene];
                }
                const original=scenes[0].caption;
                const long='Māui and his brothers work together. '.repeat(12)+'X'.repeat(90);
                scenes[0].caption=long;
                ctx.save();ctx.font='500 21px system-ui, -apple-system, sans-serif';
                const lines=subtitleLines(long,428);ctx.restore();
                let shown=[];
                const cues=Math.ceil(lines.length/2);
                for(let i=0;i<cues;i++) {
                    labels=[];drawFeaturedSubtitle(0,timelineDurations()[0]*(i+.5)/cues);
                    if(labels.length>2 || labels.some(l=>l.width>428))throw Error('Long caption overflow');
                    shown.push(...labels.map(l=>l.text));
                }
                if(shown.join('').replace(/\\s/g,'')!==long.replace(/\\s/g,''))throw Error('Long caption truncated');
                scenes[0].caption='';labels=[];boxes=[];drawFeaturedSubtitle(0,0);
                if(labels.length || boxes.length)throw Error('Empty caption box');
                scenes[0].caption=original;
                return checked;
            } finally {ctx.fillText=originalFill;ctx.fill=originalFillPath;}
        }''')
        assert result == count * 3
        # Every scene at mid-action, for visual review on a mobile-size canvas.
        for scene in range(count):
            page.evaluate('''i=>draw(timelineDurations().slice(0,i).reduce((a,b)=>a+b,0)+timelineDurations()[i]*.5)''', scene)
            page.locator('#stage').screenshot(path=f'/tmp/subtitle-{story.lower()}-{scene+1}.png')
        print(f'PASS: {story}, {result} scene/phase checks; full captions, safe bounds, two-line cues, empty caption and canvas state.')
    assert not errors, errors
    browser.close()
