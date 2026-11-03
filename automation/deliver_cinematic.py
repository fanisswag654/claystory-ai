"""Persist release delivery receipts; never confuse an upload with Telegram delivery."""
import json
import subprocess
import sys
from pathlib import Path
from telegram_send import REPO, VIDEO, verify_review

OUT = VIDEO.parent


def validate_receipt(receipt,proposal):
    if (receipt.get('proposal_id') != proposal['proposal_id'] or
        receipt.get('video_sha256') != proposal['video_sha256'] or
        receipt.get('review_buttons_verified') is not True or
        receipt.get('status') != 'delivered_for_review_not_approved' or
        not isinstance(receipt.get('telegram_message_id'),int)):
        raise RuntimeError('Stored Telegram delivery receipt does not match this film')


def main():
    proposal=json.loads((OUT/'proposal.json').read_text())
    verify_review(proposal,VIDEO)
    tag=proposal['proposal_id']
    existing=subprocess.run(['gh','release','view',tag,'--repo',REPO],capture_output=True)
    if existing.returncode == 0:
        # A GitHub release alone says nothing about sendVideo. Never silently
        # succeed on a crashed/failed upload without a verified receipt.
        with __import__('tempfile').TemporaryDirectory() as tmp:
            got=subprocess.run(['gh','release','download',tag,'--repo',REPO,
                                '-p','telegram-delivery.json','-D',tmp],capture_output=True)
            if got.returncode:
                raise RuntimeError('Release exists WITHOUT a verified Telegram receipt. Inspect the earlier run; delivery is unconfirmed, not skipped as successful.')
            receipt=json.loads((Path(tmp)/'telegram-delivery.json').read_text())
        validate_receipt(receipt,proposal)
        (OUT/'telegram-delivery.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('Verified existing delivery receipt; Telegram message',receipt['telegram_message_id'])
        return
    assets=[OUT/n for n in ('purakau-review.mp4','proposal.json','story.json','manifest.json','timing.json','captions.ass','motion-audit.json','quality-report.json')]
    subprocess.run(['gh','release','create',tag,*map(str,assets),'--repo',REPO,
                    '--latest=false','--title','Pūrākau Pixels — awaiting Telegram approval',
                    '--notes','Original portrait artwork, VoiceStudio Bruno narration, authored character breathing/sway, DepthFlow parallax and narration-aligned dissolves. Telegram approval authorizes only these exact SHA-256-verified bytes.'],check=True)
    # Keep the direct, independently tested sender and its confirmation logic.
    subprocess.run([sys.executable,'automation/telegram_send.py',str(OUT/'proposal.json')],check=True)
    receipt=json.loads((OUT/'telegram-delivery.json').read_text())
    validate_receipt(receipt,proposal)
    subprocess.run(['gh','release','upload',tag,str(OUT/'telegram-delivery.json'),
                    '--repo',REPO],check=True)
    print('Telegram delivery and BOTH review buttons confirmed; receipt saved with the exact release. Instagram not published.')


if __name__=='__main__':main()
