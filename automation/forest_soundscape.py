"""Original forest air, birdlike calls and restrained wood foley for Rātā."""
import array
import math
from pathlib import Path
import random
import subprocess
import sys
import wave


def make_soundscape(out,key,durations):
    out=Path(out);rate=22050;total=sum(durations);rng=random.Random(91347)
    data=array.array('f',[0.0])*int((total+.2)*rate)
    starts=[];at=0
    for duration in durations:starts.append(at);at+=duration
    smooth=0.0
    for n in range(len(data)):
        smooth=.98*smooth+.02*rng.uniform(-1,1)
        fade=min(1,n/rate,max(0,total-n/rate))
        data[n]=smooth*.12*fade
    # Quiet invented birdlike calls, not recordings of a claimed species.
    for scene in range(8):
        for j in range(2 if scene<4 else 4):
            at=starts[scene]+durations[scene]*(.13+.19*j)
            length=.22+.04*(j%2);base=1250+scene*47+j*110
            for k in range(int(length*rate)):
                u=k/(length*rate);n=int(at*rate)+k
                if n<len(data):
                    phase=2*math.pi*(base*k/rate+180*length*u*u/2)
                    data[n]+=.012*math.sin(math.pi*u)**2*math.sin(phase)
    # Stone-on-wood work in scene two; no generic thunder or loud impact loop.
    for j in range(4):
        at=starts[1]+durations[1]*(.24+.16*j)
        for k in range(int(.12*rate)):
            n=int(at*rate)+k
            if n<len(data):
                decay=math.exp(-k/(rate*.022))
                data[n]+=.035*decay*(.7*math.sin(2*math.pi*240*k/rate)+.3*rng.uniform(-1,1))
    pcm=array.array('h',(round(max(-1,min(1,x))*32767) for x in data))
    if sys.byteorder!='little':pcm.byteswap()
    target=out/(key+'-forest-ambience.wav')
    with wave.open(str(target),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm.tobytes())
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-i',str(target),
                    '-c:a','libmp3lame','-q:a','4',str(out/(key+'-sfx.mp3'))],check=True)
    target.unlink()
