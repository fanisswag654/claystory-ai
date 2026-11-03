"""Dissolve into each incoming scene without shortening the narration clock."""
import subprocess
from pathlib import Path

FPS = 30
TRANSITION_FRAMES = 10


def soften_entry(previous, incoming, output, previous_frames, frames):
    if min(previous_frames, frames) <= TRANSITION_FRAMES:
        raise ValueError('Scenes too short for a restrained dissolve')
    duration = TRANSITION_FRAMES/FPS
    # Hold the last outgoing frame behind the first 10 incoming frames.
    # Incoming frame 0 remains at the original narration boundary: no overlap
    # is subtracted from the film, captions or audio.
    filters = (
        '[0:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=0.5,'
        'trim=end_frame=11,settb=AVTB,setsar=1,format=yuv420p[hold];'
        '[1:v]setpts=PTS-STARTPTS,settb=AVTB,setsar=1,format=yuv420p[next];'
        f'[hold][next]xfade=transition=fade:duration={duration}:offset=0,'
        f'trim=end_frame={frames},setpts=N/({FPS}*TB),setsar=1,setdar=9/16,format=yuv420p[v]'
    )
    subprocess.run([
        'ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
        '-ss',str((previous_frames-1)/FPS),'-i',str(previous),'-i',str(incoming),
        '-filter_complex_threads','1','-filter_complex',filters,'-map','[v]',
        '-frames:v',str(frames),'-r',str(FPS),'-an','-c:v','libx264',
        '-preset','veryfast','-crf','22','-threads','2','-movflags','+faststart',str(output)
    ],check=True)
    return Path(output)
