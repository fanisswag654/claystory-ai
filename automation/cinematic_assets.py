"""Fail closed on absent or changed story artwork before generating speech."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STYLE="cinematic-stills-v1"
VOICE="en-US-ChristopherNeural"
def verify_assets(key):
    config=json.loads((ROOT/"cinematic-system.json").read_text())
    entries=config["artwork"].get(key)
    if not re.fullmatch(r"[a-z0-9-]+",key) or not entries or len(entries)!=8:
        raise ValueError("Cinematic artwork needed for "+str(key)+". Prepare eight images in ChatGPT before running this story.")
    paths=[]
    for i in range(1,9):
        name=f"scene-{i:02}.jpg";p=ROOT/"art"/key/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=entries.get(name):
            raise ValueError("Missing or modified cinematic art: "+name)
        paths.append(p)
    return paths
