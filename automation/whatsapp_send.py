#!/usr/bin/env python3
"""Send the ACTUAL completed MP4 to the user's WhatsApp for approval.

Requires approved Meta WhatsApp Business template with a VIDEO header,
BODY parameters {{1}} title and {{2}} proposal ID, and two QUICK_REPLY
buttons in this order: Approve, Reject. A WhatsApp webhook receives the
button payload and dispatches a signed GitHub decision; no WhatsApp button
response means no Instagram publication.

WhatsApp sends outside a live 24h chat require an approved template.
Never store phone numbers, bearer tokens or webhook secrets in the repo.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path


def template_payload(proposal: dict, phone_number: str, template_name: str) -> dict:
    tag=proposal["proposal_id"]
    if not re.fullmatch(r"auto-review-[a-z0-9-]+-[a-f0-9]{12}",tag):
        raise ValueError("Proposal ID is not an expected trusted GitHub Release tag")
    if not re.fullmatch(r"[0-9]{8,15}",phone_number):
        raise ValueError("WhatsApp destination must be an E.164 number without + or spaces")
    if not re.fullmatch(r"[a-z0-9_]{3,70}",template_name):
        raise ValueError("Meta template name must be registered and approved")
    url=proposal["video_url"]
    if not url.startswith(
        "https://github.com/fanisswag654/claystory-ai/releases/download/"+tag+"/"
    ):
        raise ValueError("Video is not the approved versioned ClayStory review URL")
    return {
        "messaging_product":"whatsapp",
        "to":phone_number,
        "type":"template",
        "template":{
            "name":template_name,
            "language":{"code":"en_US"},
            "components":[
                {"type":"header","parameters":[
                    {"type":"video","video":{"link":url}}
                ]},
                {"type":"body","parameters":[
                    {"type":"text","text":proposal["title"][:70]},
                    {"type":"text","text":tag[:95]},
                ]},
                {"type":"button","sub_type":"quick_reply","index":"0","parameters":[
                    {"type":"payload","payload":"approve:"+tag}
                ]},
                {"type":"button","sub_type":"quick_reply","index":"1","parameters":[
                    {"type":"payload","payload":"reject:"+tag}
                ]}
            ]
        }
    }


def send_review(proposal: dict) -> str:
    token=os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    recipient=os.getenv("WHATSAPP_REVIEW_TO")
    template=os.getenv("WHATSAPP_REVIEW_TEMPLATE","purakau_review_video_v1")
    if not token or not phone_id or not recipient:
        raise RuntimeError("WhatsApp API not connected: set all three WhatsApp secrets first")
    if not phone_id.isdecimal():
        raise RuntimeError("WhatsApp phone number ID must contain only digits")
    payload=template_payload(proposal,recipient,template)
    endpoint=f"https://graph.facebook.com/{os.getenv('WHATSAPP_GRAPH_VERSION','v23.0')}/{phone_id}/messages"
    request=urllib.request.Request(endpoint,method="POST",
         data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
         headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(request,timeout=60) as response:
            body=json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("WhatsApp video template delivery failed (HTTP "+str(exc.code)+"). Check approved template, conversation opt-in and video size.") from exc
    ids=body.get("messages",[])
    if not ids or not ids[0].get("id"):
        raise RuntimeError("Meta did not accept a WhatsApp message; do not allow publication")
    print("Submitted WhatsApp REVIEW video template (not Instagram):",ids[0]["id"])
    return ids[0]["id"]


def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: python automation/whatsapp_send.py automation/output/proposal.json")
    path=Path(sys.argv[1])
    proposal=json.loads(path.read_text(encoding="utf-8"))
    if proposal.get("status")!="pending" or not proposal.get("video_sha256"):
        raise RuntimeError("Refusing WhatsApp send without a pending video manifest")
    send_review(proposal)


if __name__=="__main__": main()
