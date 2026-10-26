"""ClayStory AI V25: expanded, distinct natural sounds for all Great Fish scenes for Te Ika-a-Māui.

No electronic drones, musical tones, retro bleeps, or endlessly repeated
sound effects. This is sparse, sound-event-based foley, designed to sit UNDER
the older male narrator and to become quieter whenever he speaks.

Only Python's standard library and the project's existing ffmpeg are needed.
"""
from array import array
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import wave

SAMPLE_RATE = 22050
rng = random.Random(108207)
audio = array("f")


def _add_noise(at, length, loudness=0.055, cutoff=950, character="wash",
               attack=0.11, decay=0.35):
    """Shaped, filtered naturalistic noise, not a continuous synth tone."""
    first = max(0, int(at * SAMPLE_RATE))
    n = min(int(length * SAMPLE_RATE), len(audio) - first)
    if n < 1:
        return
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / SAMPLE_RATE)
    slow = 0.0
    deep = 0.0
    filtered = 0.0
    a_slow = 1.0 - math.exp(-2.0 * math.pi * 190.0 / SAMPLE_RATE)
    a_deep = 1.0 - math.exp(-2.0 * math.pi * 55.0 / SAMPLE_RATE)
    for k in range(n):
        f = k / n
        white = rng.random() * 2.0 - 1.0
        slow += a_slow * (white - slow)
        deep += a_deep * (white - deep)
        filtered += alpha * (white - filtered)
        if character == "gravel":
            sound = filtered*1.3 + white*.27 + deep*.9
        elif character == "cloth":
            sound = filtered*.75 + slow*1.1 + deep*.95
        elif character == "scrape":
            sound = filtered*1.45 + slow*1.1 + deep*.65
        elif character == "foliage":
            sound = (white-filtered)*.55 + filtered*1.2 + slow*.65
        elif character == "underwater":
            sound = filtered*.2 + slow*.8 + deep*3.2
        elif character == "water":
            sound = white * .28 + slow * 1.35 + deep * 1.65
        elif character == "wood":
            sound = white * .13 + slow * 2.4 + deep * 2.25
        elif character == "strain":
            sound = white * .21 + slow * 2.15 + deep * 1.25
        elif character == "rumble":
            sound = deep * 3.8 + slow * .6
        elif character == "spray":
            sound = white * .78 + slow * .95
        else:
            sound = white * .22 + slow * 1.6 + deep * 1.45
        # Ease in/out: no hard cuts, clicks, or constant oscillating buzz.
        envelope_in = min(1.0, f / max(.006, attack))
        envelope_out = min(1.0, (1.0 - f) / max(.006, decay))
        envelope = max(0.0, envelope_in * envelope_out)
        if character == "water" or character == "wash":
            envelope *= .75 + .25 * math.sin(math.pi * f)
        audio[first + k] += max(-1.0, min(1.0, sound)) * loudness * envelope


def _low_knock(at, loudness=.075):
    """Tiny, rounded wooden hull knock; no synthetic arcade pitch sweep."""
    first = int(at * SAMPLE_RATE)
    end = min(len(audio), first + int(.13 * SAMPLE_RATE))
    if first < 0 or first >= end:
        return
    phase = rng.random() * 4.0
    for i in range(first, end):
        t = (i - first) / SAMPLE_RATE
        decay = math.exp(-35.0 * t)
        audio[i] += loudness * decay * (
            .64 * math.sin(2 * math.pi * 112 * t + phase)
            + .17 * math.sin(2 * math.pi * 185 * t)
        )
    _add_noise(at + .01, .14, .05, character="wood", attack=.02, decay=.75)


def _swell(at, loudness=.025, length=3.0):
    """Single gentle coast swell: a very low one-shot, never a loop."""
    _add_noise(at, length, loudness, character="water", attack=.46, decay=.52)


def _paddle(at, level=.065):
    _add_noise(at, .28, level * .65, character="wood", attack=.025, decay=.70)
    _add_noise(at + .12, .54, level, character="water", attack=.06, decay=.73)


def _hull(at, level=.09):
    _low_knock(at, level)
    _add_noise(at + .06, .45, level*.41, character="wood", attack=.07, decay=.70)


def _rope(at, level=.09):
    _add_noise(at, .84, level, character="strain", attack=.20, decay=.65)
    _add_noise(at + .16, .32, level*.4, character="wood", attack=.05, decay=.72)


def _splash(at, power=.18, length=1.45):
    """Brief layered wave crash with a low tail and escaping droplets."""
    _add_noise(at, length*.67, power*.84, character="spray", attack=.028, decay=.70)
    _add_noise(at+.075, length, power*.55, character="water", attack=.05, decay=.82)
    _add_noise(at+.31, length*.60, power*.36, character="water", attack=.14, decay=.77)
    for j in range(4):
        _add_noise(at+.18+j*.13, .055+j*.013, power*.15, character="spray",
                   attack=.02, decay=.80)


def _reef(at, level=.072, length=1.3):
    """Low, coarse land-forming grit instead of cinematic electronic drones."""
    _add_noise(at, length, level, character="rumble", attack=.13, decay=.80)
    _add_noise(at + .20, length*.65, level*.58, character="wood",
               attack=.12, decay=.82)


# V25 sound palette: quiet, unlooped accents, always paced to the narrator.
def _shingle(at,level=.07):
    _add_noise(at,.21,level,cutoff=1300,character="gravel",attack=.02,decay=.78)
    for k in range(4):
        _add_noise(at+.03+k*.049+rng.random()*.02,.035,level*.3,
                   cutoff=2200,character="gravel",attack=.015,decay=.8)

def _steps(at,level=.085):
    _add_noise(at,.16,level,cutoff=340,character="wood",attack=.02,decay=.83)
    _shingle(at+.055,level*.6)

def _woven_basket(at,level=.067):
    _add_noise(at,.34,level,cutoff=1000,character="scrape",attack=.14,decay=.77)
    _add_noise(at+.13,.16,level*.5,cutoff=700,character="cloth",attack=.06,decay=.8)

def _floorboard(at,level=.091):
    _add_noise(at,.6,level,cutoff=570,character="scrape",attack=.18,decay=.57)
    _low_knock(at+.3,level*.75)

def _clothes(at,level=.07):
    _add_noise(at,.45,level,cutoff=850,character="cloth",attack=.2,decay=.65)

def _bubbles(at,level=.068):
    _add_noise(at,.47,level*.52,cutoff=235,character="underwater",attack=.19,decay=.63)
    for k in range(5):
        _add_noise(at+.09+k*.102+rng.random()*.04,.044,
                   level*.5,cutoff=1200,character="water",attack=.03,decay=.85)

def _current(at,level=.046,length=1.6):
    _add_noise(at,length,level,cutoff=360,character="underwater",
               attack=.29,decay=.6)

def _jawbone(at,level=.098):
    _add_noise(at,.14,level,cutoff=1100,character="scrape",attack=.02,decay=.83)
    _low_knock(at+.05,level*.68)
    _add_noise(at+.23,.105,level*.52,cutoff=870,character="scrape",attack=.02,decay=.84)

def _sliding_line(at,level=.095):
    _add_noise(at,.63,level,cutoff=1040,character="scrape",attack=.13,decay=.67)
    _add_noise(at+.29,.18,level*.48,cutoff=340,character="strain",
               attack=.04,decay=.82)

def _tail(at,level=.18):
    _add_noise(at,.2,level,cutoff=225,character="underwater",attack=.03,decay=.84)
    _splash(at+.08,level*.81,.85)

def _cascading_water(at,level=.135):
    _add_noise(at,1.55,level,cutoff=1230,character="water",
               attack=.16,decay=.78)
    for k in range(5):
        _add_noise(at+.25+k*.19+rng.random()*.05,.09,level*.26,
                   cutoff=1800,character="spray",attack=.04,decay=.82)

def _cut(at,level=.084):
    _add_noise(at,.29,level,cutoff=1150,character="scrape",attack=.09,decay=.82)
    _add_noise(at+.17,.13,level*.42,cutoff=400,character="wood",
               attack=.02,decay=.85)

def _rocks(at,level=.105):
    _add_noise(at,.75,level,cutoff=530,character="gravel",attack=.17,decay=.68)
    for k in range(7):
        _add_noise(at+.14+k*.078+rng.random()*.04,.046,level*.34,
                   cutoff=1700,character="gravel",attack=.025,decay=.83)

def _leaves(at,level=.052):
    _add_noise(at,1.85,level,cutoff=1600,character="foliage",
               attack=.31,decay=.64)

def _schedule(durations):
    """Scene-specific accents; returns timing metadata for checking and reuse."""
    titles=[
      "Enormous fish beneath the sea","Brothers leave shore",
      "Māui hides in the waka","Māui is discovered",
      "The ancestral jawbone hook","The powerful catch",
      "The great fish rises","The North Island forms"
    ]
    if len(durations)!=len(titles):
        raise ValueError("The Great Fish soundtrack requires 8 scenes")
    cue_sheet=[]
    begin=0.0
    def cue(scene,duration,fraction,label,fn,*args):
        now=begin+duration*fraction
        fn(now,*args)
        cue_sheet.append({"scene":scene+1,"scene_title":titles[scene],
                          "time_seconds":round(now,3),"effect":label})
    for i,d in enumerate(durations):
        if i==0:
            cue(i,d,.13,"Deep ocean current",_current,.044,2.25)
            cue(i,d,.51,"Rising bubbles",_bubbles,.085)
            cue(i,d,.81,"Distant ocean swell",_swell,.027,1.5)
        elif i==1:
            cue(i,d,.09,"Footsteps on shoreline shingle",_steps,.110)
            cue(i,d,.27,"Woven fishing basket rustles",_woven_basket,.089)
            cue(i,d,.43,"Timber waka creaks",_hull,.103)
            cue(i,d,.66,"Wooden paddles enter sea",_paddle,.105)
            cue(i,d,.88,"A small wake",_swell,.043,1.1)
        elif i==2:
            cue(i,d,.08,"Sneaking across shingle",_steps,.069)
            cue(i,d,.29,"Floorboards lift",_floorboard,.110)
            cue(i,d,.49,"Clothing brushes the hull",_clothes,.085)
            cue(i,d,.68,"Floorboards settle",_floorboard,.071)
            cue(i,d,.90,"Paddle strokes carry waka away",_paddle,.088)
        elif i==3:
            cue(i,d,.13,"A board knocks as Māui emerges",_hull,.121)
            cue(i,d,.33,"Māui shifts his weight",_clothes,.078)
            cue(i,d,.55,"Canoe timbers strain",_floorboard,.096)
            cue(i,d,.75,"Urgent paddle strokes",_paddle,.106)
            cue(i,d,.91,"Open ocean water",_swell,.042,1.2)
        elif i==4:
            cue(i,d,.17,"The ancestral hook is handled",_jawbone,.119)
            cue(i,d,.43,"Fishing line slips over wood",_sliding_line,.10)
            cue(i,d,.70,"Small hook splash",_splash,.108,.72)
            cue(i,d,.89,"Bubbles trail behind the hook",_bubbles,.07)
        elif i==5:
            cue(i,d,.12,"The dark water moves",_current,.059,1.25)
            cue(i,d,.29,"Rope suddenly pulls tight",_rope,.175)
            cue(i,d,.45,"Fishing line scrapes the waka",_sliding_line,.12)
            cue(i,d,.56,"Hull creaks in protest",_hull,.122)
            cue(i,d,.73,"Powerful swell rocks the waka",_splash,.216,1.3)
            cue(i,d,.90,"A huge fish turns below",_current,.070,1.0)
        elif i==6:
            cue(i,d,.10,"Giant fish bursts from the ocean",_splash,.278,2.12)
            cue(i,d,.34,"The fish slaps the waves",_tail,.208)
            cue(i,d,.53,"Water cascades down scales",_cascading_water,.151)
            cue(i,d,.71,"First impatient cut",_cut,.108)
            cue(i,d,.89,"Second impatient cut",_cut,.078)
        else:
            cue(i,d,.12,"The great fish shudders",_reef,.12,1.25)
            cue(i,d,.32,"Stone mountains rise",_rocks,.13)
            cue(i,d,.51,"Water runs from the new coastline",_cascading_water,.118)
            cue(i,d,.70,"Leaves catch a coastal breeze",_leaves,.065)
            cue(i,d,.88,"Final gentle shore swell",_swell,.042,1.32)
        begin+=d
    return cue_sheet


def _write_wav(path):
    pcm = array("h", (max(-32768, min(32767, round(s * 32767))) for s in audio))
    if sys.byteorder == "big":
        pcm.byteswap()
    with wave.open(str(path), "wb") as fp:
        fp.setnchannels(1)
        fp.setsampwidth(2)
        fp.setframerate(SAMPLE_RATE)
        fp.writeframes(pcm.tobytes())


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    *[str(a) for a in args]], check=True)


def _seconds(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip())


def render_fish_foley(destination, durations, name="fish-nz"):
    """Publish 3 pre-ducked natural-foley mixes and the short iPad test clip."""
    global audio
    destination = Path(destination)
    if len(durations) != 8:
        raise ValueError("The Great Fish soundtrack requires 8 scene durations")
    total = sum(durations)
    audio = array("f", [0.0]) * (math.ceil((total+.1) * SAMPLE_RATE))
    rng.seed(108207)
    cue_sheet = _schedule(durations)
    (destination / f"{name}-sfx-cues.json").write_text(
        json.dumps({"version":25, "duration_seconds":round(total,3),
                    "cue_count":len(cue_sheet), "cues":cue_sheet},
                   indent=2, ensure_ascii=False)+"\n",
        encoding="utf-8")
    wav = destination / (name + "-foley-temp.wav")
    fx = destination / (name + "-sfx.mp3")
    _write_wav(wav)
    _ffmpeg("-i", wav, "-af", "highpass=f=50,lowpass=f=5900",
            "-c:a", "libmp3lame", "-q:a", "3", fx)
    wav.unlink()
    # Duck effects in real time underneath speech. Single MP3 is iPad-safe.
    # V21: restore presence to the natural foley without looping noises. Higher
    # base gain plus gentler voice-triggered ducking helps on iPad speakers.
    for mix, strength in (("soft", .95), ("balanced", 1.50), ("bold", 2.05)):
        output = destination / f"{name}-mix-{mix}.mp3"
        graph = (f"[1:a]volume={strength},highpass=f=70[foley];"
                 "[foley][0:a]sidechaincompress=threshold=0.060:ratio=3.8:"
                 "attack=18:release=230[ducked];"
                 "[0:a]volume=0.96[narrator];"
                 "[narrator][ducked]amix=inputs=2:duration=first:normalize=0,"
                 "alimiter=limit=0.92:level=0:latency=1[out]")
        _ffmpeg("-i", destination / f"{name}-full.mp3", "-i", fx,
                "-filter_complex", graph, "-map", "[out]",
                "-c:a", "libmp3lame", "-q:a", "3", output)
        if abs(_seconds(output) - total) > .17:
            raise RuntimeError(f"Foley and narration out of sync: {output}")
        print(f"Natural foley mix {mix}: {output.name} / {total:.1f}s", flush=True)

    # Test button: seven short, contrasting organic sounds.
    audio = array("f", [0.0]) * int(7.6*SAMPLE_RATE)
    rng.seed(108207)
    _steps(.08,.12)
    _floorboard(.99,.12)
    _jawbone(1.89,.13)
    _sliding_line(2.71,.12)
    _tail(3.63,.21)
    _rocks(5.09,.18)
    _leaves(6.03,.09)
    _write_wav(wav)
    _ffmpeg("-i", wav, "-af", "highpass=f=55,lowpass=f=6600",
            "-c:a", "libmp3lame", "-q:a", "3",
            destination / f"{name}-fx-test.mp3")
    wav.unlink()
    audio = array("f")
    print(f"V25: published {len(cue_sheet)} different timed Foley cues", flush=True)
