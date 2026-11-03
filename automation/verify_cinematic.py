"""Decode and measure a completed film before proposing it to Telegram."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

OUT=Path(__file__).with_name('output')


def main():
    from render_cinematic import validate_reel
    from cinematic_assets import VOICE
    import numpy as np
    meta=json.loads((OUT/'manifest.json').read_text())
    timing=json.loads((OUT/'timing.json').read_text())
    video=OUT/'purakau-review.mp4'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(video)]))
    validate_reel(probe,sum(timing['durations']))
    visual=next(s for s in probe['streams'] if s['codec_type']=='video')
    if int(visual['nb_read_frames']) != round(sum(timing['durations'])*30):
        raise RuntimeError('Film has missing frames')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(video),'-f','null','-'],check=True)
    volume=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-i',str(video),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,text=True,check=True).stderr
    level=re.search(r'mean_volume: (-?[0-9.]+) dB',volume)
    if not level or not -45<float(level[1])<-4:
        raise RuntimeError('Narration/soundtrack is silent or has an unexpected level')
    captions=(OUT/'captions.ass').read_text()
    caption_events=[line for line in captions.splitlines() if line.startswith('Dialogue: 0,')]
    if len(caption_events)<24 or 'PŪRĀKAU PIXELS' not in captions:
        raise RuntimeError('Missing narration captions or branding')
    if timing['voice']!=VOICE or timing['narration_engine']['pitch_hz']!=0:
        raise RuntimeError('Accepted narrator changed')
    if meta['story_id']=='rata-and-the-tree' and meta['motion_renderer']=='depthflow':
        audit=meta['character_motion']
        if len(audit)!=8 or any(a['changed_pixels']<100 or a['mean_pixel_change']<=0 for a in audit):
            raise RuntimeError('Authored character movement missing from a Rātā scene')
    changes=[];start=0
    for duration in timing['durations']:
        frames=[]
        for when in (start+duration*.25,start+duration*.7):
            raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-ss',str(when),'-i',str(video),'-frames:v','1','-vf','scale=180:320','-pix_fmt','rgb24','-f','rawvideo','-'])
            frames.append(np.frombuffer(raw,dtype=np.uint8).astype(np.float32))
        if frames[0].size!=180*320*3 or frames[1].size!=frames[0].size:
            raise RuntimeError('Unable to sample rendered scene')
        difference=float(np.abs(frames[0]-frames[1]).mean())
        if difference<.1:raise RuntimeError('Rendered scene appears frozen')
        changes.append(round(difference,4));start+=duration
    report={'status':'passed','video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
            'duration_seconds':sum(timing['durations']),'width':1080,'height':1920,'fps':30,
            'video_codec':'h264','audio_codec':'aac','full_decode':'passed',
            'caption_events':len(caption_events),'mean_audio_db':float(level[1]),
            'scene_frame_differences':changes,'character_motion_scenes':len(meta['character_motion']),
            'transitions':meta['transition_count'],'narrator':timing['voice'],
            'instagram_published':False}
    (OUT/'quality-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
