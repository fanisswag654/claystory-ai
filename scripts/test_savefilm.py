from playwright.sync_api import sync_playwright
import json,subprocess
from pathlib import Path
info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json','videos/fish-nz-balanced.mp4']))
v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio')
assert (v['codec_name'],v['width'],v['height'],v['pix_fmt'])==('h264',540,960,'yuv420p')
assert a['codec_name']=='aac'
total=sum(json.loads(Path('audio/fish-nz-timing.json').read_text())['durations'])
assert abs(float(info['format']['duration'])-total)<.1
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page()
 page.goto('http://127.0.0.1:8000');page.wait_for_timeout(500)
 page.click('#savefilm');page.wait_for_function('preparedFilm!==null')
 assert page.evaluate("preparedFilm.type==='video/mp4' && preparedFilm.name==='fish-nz-balanced.mp4'")
 with page.expect_download() as d:page.click('#downloadfilm')
 assert d.value.suggested_filename=='fish-nz-balanced.mp4'
 assert Path(d.value.path()).stat().st_size==Path('videos/fish-nz-balanced.mp4').stat().st_size
 page.evaluate("Object.defineProperty(navigator,'canShare',{value:()=>true});Object.defineProperty(navigator,'share',{value:async(data)=>{window.sharedFile=data.files[0]}})")
 page.click('#savefilm');page.wait_for_function('preparedFilm!==null');page.click('#sharefilm')
 assert page.evaluate("sharedFile.name==='fish-nz-balanced.mp4' && sharedFile.type==='video/mp4'")
 page.evaluate("scenes[0].narration='An edited script'");page.click('#savefilm');assert page.evaluate('preparedFilm===null')
 print('PASS: H.264/AAC portrait MP4, full-length sound, real file download, share payload, edited-script guard.')
 b.close()
