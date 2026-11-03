"""Build a private style-comparison film from eight supplied stills and new Christopher narration."""
import json, math, os, subprocess, textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parent/"output"
from cinematic_assets import verify_assets, STYLE, VOICE
import hashlib
from fractions import Fraction
FPS=30

def image_fit_filter(frames=None,part=0,reverse=False):
    # One proportional fit first, then a uniform 31/30 enlargement supplies
    # 36px horizontal and 64px vertical travel. Never stretch either axis.
    fit=('setsar=1,scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,'
         'setsar=1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1')
    if frames is None:return fit+',format=yuv420p'
    if frames<2 or part not in (0,1):raise ValueError("Invalid pan clock")
    progress=f'({part}+n/{frames-1})/2'
    x=f'(iw-ow)*(1-({progress}))' if reverse else f'(iw-ow)*({progress})'
    y=f'(ih-oh)*(0.25+0.5*({progress}))'
    return fit+f",scale=1116:1984,setsar=1,crop=1080:1920:x='{x}':y='{y}',setsar=1,format=yuv420p"

def validate_reel(probe,total):
    visual=next((s for s in probe["streams"] if s["codec_type"]=="video"),None)
    audio=next((s for s in probe["streams"] if s["codec_type"]=="audio"),None)
    if not visual or not audio:raise ValueError("Reel requires video and narration audio")
    if (visual.get("width"),visual.get("height"))!=(1080,1920):raise ValueError("Reel must be full-screen 1080x1920 portrait")
    if visual.get("codec_name")!="h264" or visual.get("pix_fmt")!="yuv420p" or audio.get("codec_name")!="aac":raise ValueError("Reel requires H.264 yuv420p and AAC")
    if Fraction(visual.get("r_frame_rate","0"))!=30:raise ValueError("Reel requires 30fps")
    if total<3 or abs(float(visual["duration"])-total)>.1 or abs(float(audio["duration"])-total)>.1:raise ValueError("Incomplete Reel video/audio clock")

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
    motion=os.environ.get("PURAKAU_MOTION","gentle-pan")
    if motion not in ("gentle-pan","depthflow"):raise ValueError("Unknown motion renderer")
    clips=ROOT/('depthflow-clips' if motion=="depthflow" else 'cinematic-pan-v4-clips')
    clips.mkdir(exist_ok=True)
    clip_paths=[]
    start=0;events=[];frames=0
    for i,(scene,duration) in enumerate(zip(story['scenes'],durations)):
        words=scene['narration'].split()
        chunks=[words[j:j+6] for j in range(0,len(words),6)]
        consumed=0
        for chunk in chunks:
            a=start+duration*consumed/len(words)
            consumed+=len(chunk);b=start+duration*consumed/len(words)
            text='\\N'.join(textwrap.wrap(' '.join(chunk),24))
            events.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Caption,,0,0,0,,{text}')
        # Measured original narration timing, rounded on a continuous 30fps clock.
        end_frame=round((start+duration)*FPS)
        count=end_frame-frames;first=count//2
        if motion=="depthflow":
            from depthflow_motion import render_scene
            path=clips/f'{i:02}.mp4'
            render_scene(artwork[i],path,count,bool(i%2))
            clip_paths.append(path)
            print(f'Encoded depth scene {i+1}/8',flush=True)
        else:
            for j,n in enumerate((first,count-first)):
                path=clips/f'{i*2+j:02}.mp4'
                filt=image_fit_filter(n,j,bool(i%2))
                run(['-loop','1','-framerate',str(FPS),'-i',str(artwork[i]),'-vf',filt,
                     '-frames:v',str(n),'-an','-c:v','libx264','-preset','veryfast',
                     '-crf','24','-threads','2','-movflags','+faststart',str(path)])
                clip_paths.append(path)
                print(f'Encoded shot {i*2+j+1}/16',flush=True)
        frames=end_frame;start+=duration
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,DejaVu Sans,48,&H00FFFFFF,&H00FFFFFF,&H00100D09,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,96,200,390,1
Style: Brand,DejaVu Sans,26,&H0099C4E8,&H00FFFFFF,&H00100D09,&H90000000,0,0,0,0,100,100,3,0,1,1,0,8,96,200,210,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    events.append(f'Dialogue: 1,0:00:00.00,{stamp(start)},Brand,,0,0,0,,PŪRĀKAU PIXELS')
    (ROOT/'captions.ass').write_text(header+'\n'.join(events)+'\n')
    (ROOT/'concat.txt').write_text(''.join(f"file '{path.as_posix()}'\n" for path in clip_paths))
    run(['-f','concat','-safe','0','-i',str(ROOT/'concat.txt'),'-i',str(ROOT/'auto-review-mix-balanced.mp3'),
         '-map','0:v:0','-map','1:a:0','-vf',f"ass='{ROOT/'captions.ass'}'",
         '-c:v','libx264','-preset','veryfast','-crf','24','-threads','2','-pix_fmt','yuv420p','-c:a','aac',
         '-b:a','160k','-t',str(start),'-movflags','+faststart',
         str(ROOT/'purakau-review.mp4')])
    video=ROOT/'purakau-review.mp4'
    if video.stat().st_size>48*1024*1024:raise RuntimeError("Video exceeds Telegram review limit")
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(video)]))
    validate_reel(probe,start)
    metadata={"story_id":story["key"],"title":story["title"],"video_file":video.name,
      "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),"duration":round(start,3),
      "bytes":video.stat().st_size,"status":"pending-human-approval","sources":story["sources"],
      "width":1080,"height":1920,"layout":"portrait-depthflow-v1" if motion=="depthflow" else "portrait-gentle-pan-v4",
      "image_fit":"proportional-depth-parallax" if motion=="depthflow" else "proportional-pan",
      "motion_renderer":motion,"pan_overscan":0.033333 if motion=="gentle-pan" else None,
      "fps":FPS,"narrator":VOICE,"style":STYLE,"image_count":8,"shot_count":len(clip_paths),
      "warning":story["cultural_warning"]}
    (ROOT/'manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print('Finished cinematic film',start,'seconds',flush=True)
if __name__=='__main__':main()
