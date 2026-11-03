"""A portrait shot list and small, readable three-word caption groups."""
from pathlib import Path
import subprocess

# Normalized focal positions of the existing source illustrations. Crops only
# use uniform magnification; they never rescale one axis independently.
FOCUS={
 'rata-and-the-tree':[(.25,.46),(.40,.48),(.45,.36),(.30,.48),(.48,.53),(.40,.51),(.46,.52),(.38,.48)]
}


def subtitle_groups(text):
    words=text.split()
    return [words[i:i+3] for i in range(0,len(words),3)]


def shot_plan(topic,scene_index,frames):
    if frames<90:raise ValueError('Scene too short for three readable shots')
    focus=FOCUS.get(topic,[(.5,.5)]*8)[scene_index]
    boundaries=[0,frames//3,2*frames//3,frames]
    return [{'start_frame':boundaries[i],'frames':boundaries[i+1]-boundaries[i],
             'framing':name,'zoom':zoom,'focus':focus}
            for i,(name,zoom) in enumerate([('wide',1.0),('medium',1.12),('detail',1.28)])]


def render_shot(source,output,plan):
    # All three windows remain exactly 9:16. Scale them proportionally back to
    # 1080x1920 and explicitly store square-pixel display metadata.
    zoom=plan['zoom']; fx,fy=plan['focus']
    # A 9k x 16k crop preserves the exact ratio even at chroma-even dimensions.
    unit=max(2,int(120/zoom)//2*2)
    cw,ch=9*unit,16*unit
    x=round(max(0,min(1080-cw,fx*1080-cw/2))/2)*2
    y=round(max(0,min(1920-ch,fy*1920-ch/2))/2)*2
    start=plan['start_frame'];end=start+plan['frames']
    filters=(f'trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS,'
             f'crop={cw}:{ch}:{x}:{y},scale=1080:1920:flags=lanczos,setsar=1,setdar=9/16,format=yuv420p')
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                    '-i',str(source),'-vf',filters,'-frames:v',str(plan['frames']),
                    '-an','-c:v','libx264','-crf','22','-preset','veryfast','-threads','2',
                    '-aspect','9:16','-movflags','+faststart',str(output)],check=True)
    return Path(output)
