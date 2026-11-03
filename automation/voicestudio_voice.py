"""CPU narration through a pinned VoiceStudio checkout; no hosted API or cloning."""
from __future__ import annotations
import argparse
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

# ONNX 1DS uploader must be disabled BEFORE importing onnxruntime/KittenTTS.
os.environ['ORT_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['OMNIVOICE_ANALYTICS_DISABLED'] = '1'

UPSTREAM_COMMIT = '429f1e5bb2703ac5b928ab8ba6f60159167e9c44'
MODEL = 'KittenML/kitten-tts-mini-0.8'
PRESET = 'expr-voice-3-m'
VOICE = 'voicestudio:kittentts:' + PRESET
SPEED = 0.92
PAUSE = 0.35
SAMPLE_RATE = 24000


def source_path():
    path = Path(os.environ.get('VOICESTUDIO_SOURCE', '.voicestudio')).resolve()
    if not (path/'backend/services/tts_backend.py').is_file():
        raise RuntimeError('Pinned VoiceStudio checkout is missing; run the cinematic GitHub workflow')
    revision = subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    if revision != UPSTREAM_COMMIT:
        raise RuntimeError('Unexpected VoiceStudio source revision')
    return path


@lru_cache(maxsize=1)
def get_engine():
    path = source_path()
    sys.path.insert(0,str(path/'backend'))
    import onnxruntime as ort
    ort.disable_telemetry_events()
    import torch
    torch.set_num_threads(2)
    os.environ['OMNIVOICE_KITTENTTS_MODEL'] = MODEL
    from services.tts_backend import KittenTTSBackend
    engine = KittenTTSBackend()
    if PRESET not in engine.PRESET_VOICES or not PRESET.endswith('-m'):
        raise RuntimeError('Required male narrator is unavailable; refusing a fallback voice')
    engine._ensure_loaded()
    onnx = engine._model.model
    if PRESET not in onnx.available_voices:
        raise RuntimeError('Model does not contain the selected male narrator')
    # Bound CPU work instead of allowing ONNX to oversubscribe every host core.
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    onnx.session = ort.InferenceSession(onnx.model_path,sess_options=options,
                                      providers=['CPUExecutionProvider'])
    return engine


def validate_samples(samples):
    import numpy as np
    values = np.asarray(samples,dtype=np.float32).reshape(-1)
    if not values.size or not np.isfinite(values).all() or np.max(np.abs(values)) < 1e-5:
        raise RuntimeError('VoiceStudio returned empty, silent or invalid speech')
    if not 0.1 <= values.size/SAMPLE_RATE <= 45:
        raise RuntimeError('VoiceStudio speech duration is outside the scene budget')
    return values


def split_sentences(text):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+',text.strip()) if s.strip()]
    if not sentences:
        raise ValueError('Narration text is empty')
    return sentences


def synthesize(text):
    sentences = split_sentences(text)
    import numpy as np
    engine = get_engine()
    from services.watermark import mark_synthetic
    pieces = []
    for sentence in sentences:
        audio = engine.generate(sentence,voice=PRESET,speed=SPEED)
        audio = mark_synthetic(audio,engine.sample_rate,context='purakau.scene')
        pieces.append(validate_samples(audio.detach().cpu().numpy()))
        pieces.append(np.zeros(round(PAUSE*SAMPLE_RATE),dtype=np.float32))
    return validate_samples(np.concatenate(pieces[:-1]))


def generate_scene(text,target):
    import soundfile as sf
    audio = synthesize(text)
    target = Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='purakau-voicestudio-') as tmp:
        wav = Path(tmp)/'narration.wav'
        sf.write(wav,audio,SAMPLE_RATE,subtype='PCM_16')
        # Encode only. No pitch, sample-rate or tempo-shifting filters.
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                        '-i',str(wav),'-c:a','libmp3lame','-b:a','160k',str(target)],check=True)
    return {'model':VOICE,'engine':'VoiceStudio/KittenTTS','checkpoint':MODEL,
            'source_commit':UPSTREAM_COMMIT,'preset':PRESET,'speed':SPEED,
            'pitch_hz':0,'sentence_pause':PAUSE}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('automation/output/voicestudio-narrator-preview.mp3'))
    args=parser.parse_args()
    metadata=generate_scene('Every line carries a story. A story of love, loss, and the journey home.',args.output)
    args.output.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('VoiceStudio male narrator preview generated:',args.output,flush=True)


if __name__=='__main__':main()
