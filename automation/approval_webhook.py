#!/usr/bin/env python3
"""Receive *authenticated* Meta WhatsApp approval/rejection webhooks.

Deploy as a Render Flask web service after selecting the correct workspace.
Security:
 - verify Meta's X-Hub-Signature-256 against exact raw request bytes
 - require exact WhatsApp sender number AND business phone number ID
 - accept only the tagged APPROVE/REJECT quick-reply button payload
 - confirm the pending GitHub Release proposal before dispatching
 - HMAC-sign the review decision for a second verification inside Actions
 - never publish here; only GitHub's independent approval workflow can do it
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import urllib.request
from flask import Flask, request, jsonify

app=Flask(__name__)
REPO="fanisswag654/claystory-ai"
TAG_REGEX=re.compile(r"^auto-review-[a-z0-9-]+-[0-9a-f]{12}$")
DECISIONS={"approve":"approved","reject":"rejected"}


def verify_meta(raw: bytes, header: str, app_secret: str) -> bool:
    if not app_secret or not header.startswith("sha256="):
        return False
    expected="sha256="+hmac.new(
        app_secret.encode("utf-8"),raw,hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected,header)


def parse_actions(payload: dict, sender: str, business_number_id: str) -> list[dict]:
    results=[]
    for entry in payload.get("entry",[]):
        for change in entry.get("changes",[]):
            value=change.get("value",{})
            if str(value.get("metadata",{}).get("phone_number_id",""))!=business_number_id:
                continue
            for msg in value.get("messages",[]):
                if str(msg.get("from",""))!=sender:
                    continue
                button=msg.get("button",{}).get("payload")
                if not button:
                    button=msg.get("interactive",{}).get("button_reply",{}).get("id")
                if not isinstance(button,str) or ":" not in button:
                    continue
                action,tag=button.split(":",1)
                if action not in DECISIONS or not TAG_REGEX.fullmatch(tag):
                    continue
                message_id=str(msg.get("id",""))
                if not re.fullmatch(r"wamid[.][A-Za-z0-9_.=-]{5,240}",message_id):
                    continue
                results.append({"proposal_id":tag,"decision":DECISIONS[action],
                                "whatsapp_message_id":message_id})
    return results


def pending_proposal(tag: str) -> dict:
    if not TAG_REGEX.fullmatch(tag):
        raise ValueError("Not a valid review proposal ID")
    url=f"https://github.com/{REPO}/releases/download/{tag}/proposal.json"
    req=urllib.request.Request(url,headers={
        "Accept":"application/json",
        "User-Agent":"ClayStory-ReviewWebhook/1.0",
    })
    with urllib.request.urlopen(req,timeout=15) as response:
        data=json.load(response)
    expected=f"https://github.com/{REPO}/releases/download/{tag}/purakau-review.mp4"
    if (
        data.get("proposal_id")!=tag
        or data.get("video_url")!=expected
        or data.get("status")!="pending"
        or not re.fullmatch(r"[a-f0-9]{64}",data.get("video_sha256",""))
        or not tag.endswith(data["video_sha256"][:12])
    ):
        raise RuntimeError("Pending proposal does not match the original release")
    return data


def signature_content(proposal_id: str, decision: str, message_id: str,
                      video_sha256: str, issued_at: int) -> bytes:
    return "|".join((proposal_id,decision,message_id,video_sha256,str(issued_at))).encode("utf-8")


def signed_decision(review: dict, proposal: dict, secret: str) -> dict:
    if not secret:
        raise RuntimeError("Review approval signing key missing")
    now=int(time.time())
    core=signature_content(
        review["proposal_id"],review["decision"],review["whatsapp_message_id"],
        proposal["video_sha256"],now
    )
    sig=hmac.new(secret.encode("utf-8"),core,hashlib.sha256).hexdigest()
    return {**review,"video_sha256":proposal["video_sha256"],
            "issued_at":now,"signature":sig}


def dispatch_github(decision: dict, token: str) -> None:
    if not token:
        raise RuntimeError("Missing scoped GitHub repository dispatch token")
    url=f"https://api.github.com/repos/{REPO}/dispatches"
    body=json.dumps({
        "event_type":"purakau_whatsapp_decision",
        "client_payload":decision
    }).encode("utf-8")
    req=urllib.request.Request(url,data=body,method="POST",headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "Content-Type":"application/json",
        "User-Agent":"ClayStory-ReviewWebhook/1.0",
    })
    with urllib.request.urlopen(req,timeout=15) as response:
        if response.status not in (200,201,202,204):
            raise RuntimeError("GitHub did not accept the review dispatch")


@app.get("/")
def health():
    # No secret information is revealed to anonymous requests.
    configured=all(os.getenv(k) for k in (
        "WHATSAPP_APP_SECRET","WHATSAPP_VERIFY_TOKEN","WHATSAPP_APPROVER_NUMBER",
        "WHATSAPP_PHONE_NUMBER_ID","GITHUB_REVIEW_DISPATCH_TOKEN",
        "PURAKAU_APPROVAL_SIGNING_KEY"
    ))
    return jsonify(service="claystory-whatsapp-review",configured=configured)


@app.get("/webhook/whatsapp")
def verify_endpoint():
    expected=os.getenv("WHATSAPP_VERIFY_TOKEN","")
    if (
        expected and request.args.get("hub.mode")=="subscribe"
        and hmac.compare_digest(request.args.get("hub.verify_token",""),expected)
    ):
        return request.args.get("hub.challenge",""),200,{"Content-Type":"text/plain"}
    return "not verified",403


@app.post("/webhook/whatsapp")
def incoming_decision():
    raw=request.get_data(cache=False)
    secret=os.getenv("WHATSAPP_APP_SECRET","")
    if not verify_meta(raw,request.headers.get("X-Hub-Signature-256",""),secret):
        return jsonify(error="invalid Meta webhook signature"),403
    try:
        payload=json.loads(raw)
    except (ValueError,TypeError):
        return jsonify(error="invalid JSON"),400
    sender=os.getenv("WHATSAPP_APPROVER_NUMBER","")
    number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID","")
    if not sender or not number_id:
        return jsonify(error="reviewer not configured"),503
    requests=parse_actions(payload,sender,number_id)
    if not requests:
        # Status events and unsolicited messages cannot approve anything.
        return jsonify(ignored=True),200
    signing=os.getenv("PURAKAU_APPROVAL_SIGNING_KEY","")
    dispatch_token=os.getenv("GITHUB_REVIEW_DISPATCH_TOKEN","")
    for action in requests:
        proposal=pending_proposal(action["proposal_id"])
        receipt=signed_decision(action,proposal,signing)
        dispatch_github(receipt,dispatch_token)
    return jsonify(dispatched=len(requests)),200


if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
