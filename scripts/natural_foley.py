"""ClayStory AI V20: restrained, original acoustic-style foley for Te Ika-a-Māui.

No electronic drones, musical tones, retro bleeps, or endlessly repeated
sound effects. This is sparse, sound-event-based foley, designed to sit UNDER
the older male narrator and to become quieter whenever he speaks.

Only Python's standard library and the project's existing ffmpeg are needed.
"""
from array import array
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
    a_slow = 1.0 - math.exp(-2.0 * math.pi * 190.0 / SAMPLE_RATE)
    a_deep = 1.0 - math.exp(-2.0 * math.pi * 55.0 / SAMPLE_RATE)
    for k in range(n):
        f = k / n
        white = rng.random() * 2.0 - 1.0
        slow += a_slow * (white - slow)
        deep += a_deep * (white - deep)
        if character == "water":
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


def _schedule(durations):
    start = 0.0
    for scene, duration in enumerate(durations):
        b = start
        start += duration
        # Intentionally NO full-scene continuous tone or constant noise bed.
        # Intermittent, airy coast wash is low-level and leaves breathing space.
        if scene in (0, 1, 2, 3, 4, 7):
            _swell(b + duration*.12, .020, min(2.9, duration*.36))
        if scene == 0:
            # A subtle underwater introduction; fish itself has no robot voice.
            _swell(b + duration*.63, .016, 2.1)
        elif scene == 1:
            # Brothers prepare and depart; only two distinct launch actions.
            _hull(b + duration*.21, .075)
            _paddle(b + duration*.72, .065)
        elif scene == 2:
            # Māui sneaks under the floorboards.
            _hull(b + duration*.25, .070)
            _hull(b + duration*.59, .060)
            _paddle(b + duration*.81, .06)
        elif scene == 3:
            # Brothers spot their stowaway; rocking waka, one paddle.
            _hull(b + duration*.23, .075)
            _paddle(b + duration*.59, .071)
        elif scene == 4:
            # Preparing the hook, then its small entry into the sea.
            _rope(b + duration*.29, .067)
            _splash(b + duration*.77, power=.095, length=.61)
        elif scene == 5:
            # The line snags, creaks, snaps taut; a big single wave.
            _rope(b + duration*.27, .12)
            _hull(b + duration*.49, .10)
            _splash(b + duration*.68, power=.17, length=1.15)
        elif scene == 6:
            # The huge fish breaches; this gets the strongest but brief foley.
            _splash(b + duration*.28, power=.235, length=2.0)
            _hull(b + duration*.45, .085)
            _reef(b + duration*.79, level=.077, length=.8)
        elif scene == 7:
            # Quiet gritty earth shifting into a final coastal wash.
            _reef(b + duration*.27, level=.095, length=1.85)
            _swell(b + duration*.73, loudness=.025, length=2.25)


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
    _schedule(durations)
    wav = destination / (name + "-foley-temp.wav")
    fx = destination / (name + "-sfx.mp3")
    _write_wav(wav)
    _ffmpeg("-i", wav, "-af", "highpass=f=50,lowpass=f=5900",
            "-c:a", "libmp3lame", "-q:a", "3", fx)
    wav.unlink()
    # Duck effects in real time underneath speech. Single MP3 is iPad-safe.
    for mix, strength in (("soft", .72), ("balanced", 1.15), ("bold", 1.60)):
        output = destination / f"{name}-mix-{mix}.mp3"
        graph = (f"[1:a]volume={strength},highpass=f=70[foley];"
                 "[foley][0:a]sidechaincompress=threshold=0.028:ratio=6:"
                 "attack=18:release=260[ducked];"
                 "[0:a]volume=0.96[narrator];"
                 "[narrator][ducked]amix=inputs=2:duration=first:normalize=0,"
                 "alimiter=limit=0.92:level=0:latency=1[out]")
        _ffmpeg("-i", destination / f"{name}-full.mp3", "-i", fx,
                "-filter_complex", graph, "-map", "[out]",
                "-c:a", "libmp3lame", "-q:a", "3", output)
        if abs(_seconds(output) - total) > .17:
            raise RuntimeError(f"Foley and narration out of sync: {output}")
        print(f"Natural foley mix {mix}: {output.name} / {total:.1f}s", flush=True)

    # The test button now plays WAV-style Foley (paddle, splash, rope, boat),
    # never synthesizer bleeps / whistles / chimes.
    audio = array("f", [0.0]) * int(3.45 * SAMPLE_RATE)
    _paddle(.08, .105)
    _hull(.82, .11)
    _rope(1.30, .12)
    _splash(2.18, .19, .84)
    _write_wav(wav)
    _ffmpeg("-i", wav, "-af", "highpass=f=55,lowpass=f=6100",
            "-c:a", "libmp3lame", "-q:a", "3",
            destination / f"{name}-fx-test.mp3")
    wav.unlink()
    audio = array("f")
    print("V20: Great Fish uses sparse acoustic foley; no electronic background.", flush=True)
