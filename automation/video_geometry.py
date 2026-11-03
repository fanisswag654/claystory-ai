"""Validate displayed portrait geometry, including H.264 and MP4 aspect metadata."""
from fractions import Fraction
from pathlib import Path
import json
import subprocess
import os


def ratio(value):
    return Fraction(str(value).replace(':','/'))


def validate_display(video, width=1080, height=1920):
    if (video.get('width'),video.get('height')) != (width,height):
        raise ValueError('Incorrect encoded portrait dimensions')
    try:
        sar=ratio(video.get('sample_aspect_ratio','0:1'))
        dar=ratio(video.get('display_aspect_ratio','0:1'))
    except (ValueError,ZeroDivisionError):
        raise ValueError('Missing or invalid video display aspect metadata') from None
    if sar!=1 or dar!=Fraction(9,16):
        raise ValueError('Reel requires square pixels and explicit 9:16 display aspect')
    for side in video.get('side_data_list',[]):
        if float(side.get('rotation',0))%360:
            raise ValueError('Reel must not depend on player rotation metadata')


def normalize_display(path,width=1080,height=1920):
    path=Path(path)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    if (video['width'],video['height'])!=(width,height):
        raise ValueError('Do not relabel stretched or wrongly sized video pixels')
    output=path.with_name(path.stem+'-display-fixed.mp4')
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                    '-i',str(path),'-map','0:v:0','-c:v','copy',
                    '-bsf:v','h264_metadata=sample_aspect_ratio=1/1',
                    '-aspect','9:16','-movflags','+faststart',str(output)],check=True)
    fixed=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output)]))
    validate_display(next(s for s in fixed['streams'] if s['codec_type']=='video'),width,height)
    os.replace(output,path)
