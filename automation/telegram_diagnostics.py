"""Check the existing bot destination and Render route without sending a post."""
import json
import os
import time
from pathlib import Path

import requests
from telegram_setup import telegram_api, CALLBACK_URL
from telegram_free_preview import verified_private_credentials

OUT = Path(__file__).with_name('output')


def check_connection():
    _, chat = verified_private_credentials(os.environ)
    bot = telegram_api('getMe', {})
    destination = telegram_api('getChat', {'chat_id':chat})
    if not bot.get('is_bot') or destination.get('type') != 'private' or str(destination.get('id')) != chat:
        raise RuntimeError('Telegram destination is not the configured private reviewer')
    before = telegram_api('getWebhookInfo', {})
    if before.get('url') != CALLBACK_URL:
        # Recover the existing route only when its matching stored secret is available.
        from telegram_setup import main as reconnect
        reconnect()
    health_url = CALLBACK_URL.removesuffix('/webhook/telegram')+'/'
    healthy = False
    for attempt in range(3):
        try:
            response = requests.get(health_url,timeout=60)
            healthy = response.ok and response.json().get('telegram_configured') is True
            if healthy:break
        except (requests.RequestException,ValueError):
            pass
    if not healthy:
        raise RuntimeError('Render Telegram approval route did not become ready')
    # Anonymous requests MUST fail before parsing or dispatching any decision.
    refused = requests.post(CALLBACK_URL,json={'diagnostic':True},timeout=25)
    if refused.status_code != 403:
        raise RuntimeError('Render did not refuse an unsigned Telegram request')
    info = telegram_api('getWebhookInfo', {})
    if 'callback_query' not in info.get('allowed_updates',['callback_query']):
        raise RuntimeError('Telegram webhook excludes review button updates')
    recovered = None
    if os.getenv('RECOVER_TELEGRAM_MESSAGE_ID'):
        from telegram_send import message_payload, validate_delivery_message
        from telegram_send import PROPOSAL_PATTERN
        tag = os.environ['RECOVER_TELEGRAM_PROPOSAL_ID']
        if not PROPOSAL_PATTERN.fullmatch(tag):raise ValueError('Invalid recovery proposal')
        proposal_response = requests.get('https://github.com/fanisswag654/claystory-ai/releases/download/'+tag+'/proposal.json',timeout=30)
        proposal_response.raise_for_status()
        proposal = proposal_response.json()
        if proposal.get('proposal_id') != tag or not tag.endswith(proposal['video_sha256'][:12]):
            raise ValueError('Recovery proposal identity mismatch')
        payload = message_payload(proposal,chat)
        payload['message_id'] = int(os.environ['RECOVER_TELEGRAM_MESSAGE_ID'])
        payload.pop('supports_streaming')
        payload['reply_markup'] = json.loads(payload['reply_markup'])
        payload['caption'] = 'RECOVERED REVIEW — original completed film.\n'+payload['caption']
        try:
            restored = telegram_api('editMessageCaption', payload)
            validate_delivery_message(restored,proposal,chat)
            recovered = {'message_id':restored['message_id'],'buttons_verified':True,
                         'proposal_id':proposal['proposal_id']}
        except RuntimeError as exc:
            recovered = {'message_id':payload['message_id'],'verified':False,'reason':str(exc)}
    result = {
        'recovered_review':recovered, 'bot_username':bot['username'], 'private_reviewer_verified':True,
        'webhook_url':info['url'], 'render_ready':True, 'unsigned_request_status':403,
        'pending_update_count':info.get('pending_update_count',0),
        'last_error_date':info.get('last_error_date'),
        'last_error_message':info.get('last_error_message'),
        'checked_at':int(time.time()), 'instagram_published':False,
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'telegram-diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    if info.get('pending_update_count',0) and info.get('last_error_date',0)>time.time()-300:
        raise RuntimeError('Telegram reports a current webhook delivery error; inspect diagnostics')
    return result


if __name__=='__main__':check_connection()
