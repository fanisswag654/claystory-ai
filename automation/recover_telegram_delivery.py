"""Repair one known Telegram review using the already rendered exact release.

Does not render, dispatch an approval, or access Buffer. Explicit sender video
metadata avoids Telegram guessing dimensions from an upload. Download the
returned Telegram file and verify its SHA before claiming exact delivery.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import requests
from telegram_free_preview import verified_private_credentials
from telegram_send import VIDEO, REPO, verify_review, message_payload, validate_delivery_message
from telegram_setup import telegram_api
from telegram_diagnostics import check_connection

OUT=VIDEO.parent


def main():
    check_connection()
    request=json.loads(Path('automation/delivery-recovery.json').read_text())
    proposal=json.loads((OUT/'proposal.json').read_text())
    if proposal['proposal_id']!=request['proposal_id']:
        raise RuntimeError('Recovery release does not match its explicit request')
    verify_review(proposal,VIDEO)
    token,chat=verified_private_credentials(os.environ)
    mid=request['replace_message_id']
    if not isinstance(mid,int) or mid<=0:raise ValueError('Known prior review message ID required')
    caption=message_payload(proposal,chat)
    media={'type':'video','media':'attach://video','width':1080,'height':1920,
           'duration':round(json.loads((OUT/'manifest.json').read_text())['duration']),
           'supports_streaming':True,'caption':caption['caption']}
    try:
        with VIDEO.open('rb') as video:
            response=requests.post('https://api.telegram.org/bot'+token+'/editMessageMedia',
                data={'chat_id':chat,'message_id':mid,'media':json.dumps(media),
                      'reply_markup':caption['reply_markup']},
                files={'video':(VIDEO.name,video,'video/mp4')},timeout=(20,210))
    except requests.RequestException:
        raise RuntimeError('Telegram repair response unavailable; inspect checkpoint before retrying') from None
    if not response.ok or not response.json().get('ok'):
        raise RuntimeError('Telegram media repair was refused (HTTP '+str(response.status_code)+')')
    sent=response.json()['result']
    checkpoint={'proposal_id':proposal['proposal_id'],'telegram_message_id':sent['message_id'],
                'video_sha256':proposal['video_sha256'],
                'width':sent.get('video',{}).get('width'),'height':sent.get('video',{}).get('height')}
    (OUT/'telegram-upload-checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
    print('Telegram repair checkpoint:',json.dumps(checkpoint),flush=True)
    validate_delivery_message(sent,proposal,chat)
    # This release is below Telegram's 20MB getFile limit. Verify the actual
    # stored original, not only the multipart bytes we intended to upload.
    info=telegram_api('getFile',{'file_id':sent['video']['file_id']})
    path=info.get('file_path','')
    if not path or '..' in path:raise RuntimeError('No retrievable Telegram original')
    try:
        downloaded=requests.get('https://api.telegram.org/file/bot'+token+'/'+path,timeout=90)
        if not downloaded.ok:raise RuntimeError('Unable to retrieve Telegram original')
    except requests.RequestException:
        raise RuntimeError('Telegram original download unavailable') from None
    if hashlib.sha256(downloaded.content).hexdigest()!=proposal['video_sha256']:
        raise RuntimeError('Telegram original differs from the reviewed release bytes')
    receipt={**checkpoint,'video_bytes':len(downloaded.content),'review_buttons_verified':True,
             'telegram_original_sha256_verified':True,'private_reviewer_verified':True,
             'status':'delivered_for_review_not_approved','verified_at':int(time.time()),
             'bot_username':'purakau_bot','delivery_method':'editMessageMedia-known-review'}
    (OUT/'telegram-delivery.json').write_text(json.dumps(receipt,indent=2)+'\n')
    subprocess.run(['gh','release','upload',proposal['proposal_id'],str(OUT/'telegram-delivery.json'),
                    '--repo',REPO,'--clobber'],check=True)
    # One new notification points to the repaired review; no second MP4 or
    # publishing decision is created. Reruns are prevented by the receipt gate
    # in the recovery workflow before reaching this script.
    telegram_api('sendMessage',{'chat_id':chat,'reply_parameters':{'message_id':mid},
        'text':'🎬 Your upgraded Rātā film is ready in the video above this reply. The exact 1080×1920 MP4 and both review buttons have been verified. Please review the story, movement, captions and pronunciation. Instagram waits for your Approve button.'})
    print('VERIFIED exact upgraded MP4 stored in Telegram; both buttons confirmed; message',mid,'. No approval or Instagram publication was performed.')


if __name__=='__main__':main()
