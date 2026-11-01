"""Quiet original ambience for the Mataora and Niwareka story; no sampled music."""
import array,math,random,sys,wave,subprocess
from pathlib import Path

def make_soundscape(out,key,durations):
    out=Path(out);rate=22050;total=sum(durations);rng=random.Random(731941)
    data=array.array("f",[0.0])*int((total+.2)*rate)
    smooth=0.0
    # Subtle enclosed air / leaf movement throughout, with no storm climax.
    for n in range(len(data)):
        smooth=.985*smooth+.015*rng.uniform(-1,1)
        env=min(1,n/rate, max(0,total-n/rate))
        data[n]=smooth*.09*env
    starts=[];t=0
    for d in durations:starts.append(t);t+=d
    # Gentle original wooden tool sounds accompany the receiving-moko scene.
    for j in range(4):
        at=starts[4]+durations[4]*(.24+j*.16)
        for k in range(int(.09*rate)):
            n=int(at*rate)+k
            if n<len(data):
                data[n]+=.018*math.exp(-k/(rate*.018))*math.sin(2*math.pi*380*k/rate)
    # Quiet birds only in the world-above opening and closing.
    for scene in (0,7):
        for j in range(3):
            at=starts[scene]+durations[scene]*(.2+j*.23)
            for k in range(int(.19*rate)):
                u=k/(.19*rate);n=int(at*rate)+k
                if n<len(data):
                    data[n]+=.009*math.sin(math.pi*u)**2*math.sin(2*math.pi*(1300+200*u)*k/rate)
    pcm=array.array("h",(int(max(-1,min(1,x))*32767) for x in data))
    if sys.byteorder!="little":pcm.byteswap()
    wav=out/(key+"-moko-ambience.wav")
    with wave.open(str(wav),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y","-i",str(wav),"-c:a","libmp3lame","-q:a","4",str(out/(key+"-sfx.mp3"))],check=True)
    wav.unlink()
