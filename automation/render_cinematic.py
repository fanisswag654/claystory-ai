"""Build a private style-comparison film from eight supplied stills and new Christopher narration."""
import json, math, subprocess, textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parent/"output"
from cinematic_assets import verify_assets, STYLE, VOICE
import hashlib
FPS=30
def run(args):
    for attempt in range(2):
        subprocess.run(['ffmpeg','-nostdin','-xerror','-hide_banner','-loglevel','error','-y',*args],check=True)
        target=Path(args[-1])
        if target.suffix!='.mp4':return
        check=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',str(target)],capture_output=True)
        if check.returncode==0:return
        target.unlink(missing_ok=True)
    raise RuntimeError('Encoder produced an incomplete MP4')
def stamp(t):
    cs=round(t*100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
def main():
    story=json.loads((ROOT/'story.json').read_text())
    durations=json.loads((ROOT/'timing.json').read_text())['durations']
    artwork=verify_assets(story["key"])
    timing=json.loads((ROOT/"timing.json").read_text())
    if timing["voice"]!=VOICE or len(durations)!=8:raise ValueError("Wrong voice or scene clock")
    clips=ROOT/'cinematic-clips';clips.mkdir(exist_ok=True)
    start=0;events=[];frames=0
    for i,(scene,duration) in enumerate(zip(story['scenes'],durations)):
        words=scene['narration'].split()
        chunks=[words[j:j+7] for j in range(0,len(words),7)]
        consumed=0
        for chunk in chunks:
            a=start+duration*consumed/len(words)
            consumed+=len(chunk);b=start+duration*consumed/len(words)
            text='\\N'.join(textwrap.wrap(' '.join(chunk),29))
            events.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Caption,,0,0,0,,{text}')
        # Measured original narration timing, rounded on a continuous 30fps clock.
        end_frame=round((start+duration)*FPS)
        count=end_frame-frames;first=count//2
        for j,n in enumerate((first,count-first)):
            path=clips/f'{i*2+j:02}.mp4'
            if path.exists():
                check=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',str(path)],capture_output=True)
                if check.returncode==0:continue
                path.unlink()
            z=(f'1.01+0.045*on/{n}' if j==0 else f'1.16-0.035*on/{n}')
            filt=(f'scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,'
                  f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps={FPS},"
                  'setsar=1,format=yuv420p')
            run(['-loop','1','-framerate',str(FPS),'-i',str(artwork[i]),'-vf',filt,
                 '-frames:v',str(n),'-an','-c:v','libx264','-preset','veryfast',
                 '-crf','24','-threads','2','-movflags','+faststart',str(path)])
            print(f'Encoded shot {i*2+j+1}/16',flush=True)
        frames=end_frame;start+=duration
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,DejaVu Sans,53,&H00FFFFFF,&H00FFFFFF,&H00100D09,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,90,90,265,1
Style: Brand,DejaVu Sans,29,&H0099C4E8,&H00FFFFFF,&H00100D09,&H90000000,0,0,0,0,100,100,3,0,1,1,0,8,70,70,120,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    events.append(f'Dialogue: 1,0:00:00.00,{stamp(start)},Brand,,0,0,0,,PŪRĀKAU PIXELS  /  STORIES OF AOTEAROA')
    (ROOT/'captions.ass').write_text(header+'\n'.join(events)+'\n')
    (ROOT/'concat.txt').write_text(''.join(f"file '{(clips/f'{i:02}.mp4').as_posix()}'\n" for i in range(16)))
    run(['-f','concat','-safe','0','-i',str(ROOT/'concat.txt'),'-i',str(ROOT/'auto-review-mix-balanced.mp3'),
         '-map','0:v:0','-map','1:a:0','-vf',f"ass='{ROOT/'captions.ass'}'",
         '-c:v','libx264','-preset','veryfast','-crf','24','-threads','2','-c:a','aac',
         '-b:a','160k','-t',str(start),'-movflags','+faststart',
         str(ROOT/'purakau-review.mp4')])
    video=ROOT/'purakau-review.mp4'
    if video.stat().st_size>48*1024*1024:raise RuntimeError("Video exceeds Telegram review limit")
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(video)]))
    visual=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    if abs(float(visual['duration'])-start)>.1 or abs(float(audio['duration'])-start)>.1:
        raise RuntimeError("Incomplete video/audio clock")
    metadata={"story_id":story["key"],"title":story["title"],"video_file":video.name,
      "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),"duration":round(start,3),
      "bytes":video.stat().st_size,"status":"pending-human-approval","sources":story["sources"],
      "fps":FPS,"narrator":VOICE,"style":STYLE,"image_count":8,"shot_count":16,
      "warning":story["cultural_warning"]}
    (ROOT/'manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print('Finished cinematic film',start,'seconds',flush=True)
if __name__=='__main__':main()
