"""Reuse the exact accepted narrator and sound mix when making a visual recut."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'


def main():
    candidate=json.loads((ROOT/'candidate-story.json').read_text())
    cfg=json.loads((ROOT/'cinematic-system.json').read_text())
    reuse=cfg.get('reuse_audio_review',{})
    if reuse.get('story_id')!=candidate['key']:
        from make_audio import main as make_fresh_audio
        make_fresh_audio();return
    from telegram_send import PROPOSAL_PATTERN,REPO
    tag=reuse['proposal_id']
    if not PROPOSAL_PATTERN.fullmatch(tag):raise ValueError('Invalid original audio source release')
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['gh','release','download',tag,'--repo',REPO,'-D',tmp,
                        '-p','purakau-review.mp4','-p','story.json','-p','timing.json','-p','proposal.json'],check=True)
        src=Path(tmp);proposal=json.loads((src/'proposal.json').read_text())
        story=json.loads((src/'story.json').read_text());timing=json.loads((src/'timing.json').read_text())
        digest=hashlib.sha256((src/'purakau-review.mp4').read_bytes()).hexdigest()
        if digest!=reuse['video_sha256'] or proposal['video_sha256']!=digest or proposal['proposal_id']!=tag:
            raise RuntimeError('Original narration source is not the pinned exact film')
        for field in ['key','title','scenes','sources']:
            if story[field]!=candidate[field]:raise RuntimeError('Do not reuse narration for a different story or script')
        from cinematic_assets import VOICE
        if timing['voice']!=VOICE or story['narrator']!=VOICE:raise RuntimeError('Accepted narrator changed')
        OUT.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                        '-i',str(src/'purakau-review.mp4'),'-map','0:a:0','-c:a','copy',
                        str(OUT/'auto-review-mix-balanced.m4a')],check=True)
        (OUT/'story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2)+'\n')
        timing['audio_source_review']={'proposal_id':tag,'video_sha256':digest,'audio_stream_copy':True}
        (OUT/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2)+'\n')
        print('Preserved the exact existing Bruno narration and sound mix for the visual recut.',flush=True)


if __name__=='__main__':main()
