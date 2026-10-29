#!/usr/bin/env python3
"""Only a verified, signed WhatsApp approval may publish a new Reel.

This runs INSIDE a separate GitHub Actions workflow, never inside the
WhatsApp webhook. The original MP4 is downloaded and validated by SHA-256.
Unapproved, ignored, expired or rejected proposals cannot call Buffer.

History is persisted to the existing instagram-publish-history Git branch
by the enclosing workflow, including partial draft IDs after API errors.
"""
from __future__ import annotations

from datetime import datetime,timezone,timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from instagram_reels import (
    buffer_api, create_post, edit_instagram_reel,
    instagram_channel, validate_reel, verify_public_release,
)

REPO="fanisswag654/claystory-ai"
REVIEW=Path("automation/review-upload")
HISTORY=Path("instagram-post-history.json")
TRUSTED_CHANNEL="6ae277352f1f5ed648046667"


def canonical_receipt(proposal_id: str, decision: str, message_id: str,
                      video_sha256: str, issued_at: int) -> bytes:
    return "|".join((proposal_id,decision,message_id,video_sha256,str(issued_at))).encode("utf-8")


def verify_decision(receipt: dict, proposal: dict, secret: str, now: int | None=None) -> None:
    now=int(time.time()) if now is None else now
    if not secret:
        raise ValueError("Approval signing secret missing")
    if receipt.get("decision") not in ("approved","rejected"):
        raise ValueError("No explicit WhatsApp approval/rejection")
    if receipt.get("proposal_id") != proposal.get("proposal_id"):
        raise ValueError("Signed approval refers to another story")
    if receipt.get("video_sha256") != proposal.get("video_sha256"):
        raise ValueError("Approval refers to a different video")
    issued=receipt.get("issued_at")
    if not isinstance(issued,int) or abs(now-issued)>600:
        raise ValueError("Approval signature is expired or too far in the future")
    msg_id=receipt.get("whatsapp_message_id","")
    if not re.fullmatch(r"wamid[.][A-Za-z0-9_.=/+-]{5,240}",msg_id):
        raise ValueError("Review was not an actual WhatsApp message ID")
    if not re.fullmatch(r"[a-f0-9]{64}",receipt.get("signature","")):
        raise ValueError("Missing signed WhatsApp decision")
    digest=hmac.new(secret.encode("utf-8"),canonical_receipt(
        receipt["proposal_id"],receipt["decision"],msg_id,
        receipt["video_sha256"],issued
    ),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest,receipt["signature"]):
        raise ValueError("Review was not authenticated by the WhatsApp webhook")


def validate_original_file(proposal: dict, file: Path) -> None:
    tag=proposal.get("proposal_id","")
    sha=proposal.get("video_sha256","")
    if not re.fullmatch(r"auto-review-[a-z0-9-]+-[a-f0-9]{12}",tag):
        raise ValueError("Invalid review video tag")
    if not re.fullmatch(r"[a-f0-9]{64}",sha) or not tag.endswith(sha[:12]):
        raise ValueError("Video fingerprint does not match the original release")
    url=f"https://github.com/{REPO}/releases/download/{tag}/purakau-review.mp4"
    if proposal.get("video_url")!=url or proposal.get("status")!="pending":
        raise ValueError("Proposal URL or review state does not match immutable release")
    if proposal.get("narrator")not in ("en-GB-RyanNeural","en-US-ChristopherNeural"):
        raise ValueError("Cinematic narrator identity changed")
    legacy=(tag=="auto-review-maui-mahuika-fire-ddb8318a9296" and sha=="ddb8318a9296de8418643294e82dec8d7f52056278185bd470ceb3ec72ed107c")
    if not legacy:
        from cinematic_assets import verify_assets,STYLE,VOICE
        if proposal.get("narrator")!=VOICE or proposal.get("style")!=STYLE:
            raise ValueError("Only the installed cinematic Christopher system may publish new films")
        verify_assets(proposal.get("story_id",""))
    created=datetime.fromisoformat(proposal["created_at"])
    if created.tzinfo is None or datetime.now(timezone.utc)-created>timedelta(days=14):
        raise ValueError("WhatsApp review expired after 14 days")
    if len(proposal.get("sources",[]))<1:
        raise ValueError("Every proposed story must have a documented source")
    if not file.is_file() or file.name!="purakau-review.mp4":
        raise ValueError("Missing original video to approve")
    if hashlib.sha256(file.read_bytes()).hexdigest()!=sha:
        raise ValueError("Downloaded review MP4 differs from WhatsApp approved video")


def caption(proposal: dict) -> str:
    name=proposal["title"].strip()
    if not name or len(name)>120:raise ValueError("Invalid caption title")
    return (name+" 🌿✨\n\nAn original cinematic illustrated retelling "
            "of a Māori pūrākau, with cinematic AI narration and "
            "original environmental sounds.\n\n"
            "This reflects one telling; traditions may differ between iwi. "
            "Pronunciation and story reviewed by the account owner.\n\n"
            "Pūrākau Pixels | Stories of Aotearoa\n"
            "#PurakauPixels #Purakau #MaoriStories #CinematicStories #Aotearoa")


def submit_approved(proposal: dict, history: dict) -> dict:
    tag=proposal["proposal_id"]
    sha=proposal["video_sha256"]
    url=proposal["video_url"]
    base=f"auto:{tag}:{sha}"
    draft_key=base+":draft"
    published_key=base+":shareNow"
    if published_key in history:
        print("Already submitted to Buffer (no duplicate)",history[published_key]["buffer_post_id"])
        return history
    if any(isinstance(v,dict) and v.get("video_sha256")==sha and v.get("mode")=="shareNow" for v in history.values()):
        raise ValueError("These exact video bytes were already submitted; no duplicate")
    verify_public_release(url)
    channel=instagram_channel()
    if channel["id"]!=TRUSTED_CHANNEL:
        raise RuntimeError("Incorrect Instagram account; only @purakaupixel is permitted")
    text=caption(proposal)
    if draft_key in history:
        draft=history[draft_key]
        if draft["video_url"]!=url or draft["channel_id"]!=TRUSTED_CHANNEL:
            raise RuntimeError("Existing draft belongs to a different video/account")
        post_id=draft["buffer_post_id"]
        post=buffer_api("query { post(input: { id: "+json.dumps(post_id)+
                       " }) { id channelId status shareMode } }")["post"]
        if not post or post.get("channelId")!=TRUSTED_CHANNEL:
            raise RuntimeError("Cannot verify existing Buffer draft")
        status=(post.get("status") or "").lower()
        if status in ("sent","scheduled","sending"):
            outcome=post
        elif status=="draft":
            outcome=edit_instagram_reel(post_id,url,text,"shareNow")
        else:
            raise RuntimeError("Unexpected previous Buffer post state: "+status)
    else:
        # Persist a draft before moving to Publish Now, so interrupted tasks
        # can recover without creating a second Instagram post.
        post=create_post(channel["id"],url,text)
        post_id=post["id"]
        history[draft_key]={
            "story":proposal["story_id"],"video_url":url,"channel_id":TRUSTED_CHANNEL,
            "buffer_post_id":post_id,"mode":"draft","video_sha256":sha,
        }
        HISTORY.write_text(json.dumps(history,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
        outcome=edit_instagram_reel(post_id,url,text,"shareNow")
    if outcome.get("id")!=post_id:
        raise RuntimeError("Buffer returned unexpected post ID")
    history[published_key]={
        "story":proposal["story_id"],"video_url":url,"channel_id":TRUSTED_CHANNEL,
        "buffer_post_id":post_id,"mode":"shareNow",
        "buffer_status":outcome.get("status"),"video_sha256":sha,
    }
    return history


def process(receipt: dict, proposal: dict, history: dict) -> dict:
    verify_decision(receipt,proposal,os.getenv("PURAKAU_APPROVAL_SIGNING_KEY",""))
    validate_original_file(proposal,REVIEW/"purakau-review.mp4")
    key="review:"+proposal["proposal_id"]
    decision=receipt["decision"]
    old=history.get(key)
    if old:
        if old.get("decision")!=decision:
            raise RuntimeError("A prior WhatsApp decision cannot be overturned by a second button tap")
        print("Decision already recorded; no action repeated")
        return history
    if decision=="rejected":
        history[key]={"decision":"rejected","whatsapp_message_id":receipt["whatsapp_message_id"],
                      "video_sha256":proposal["video_sha256"]}
        print("STORY REJECTED: No Instagram upload will occur.")
        return history
    history=submit_approved(proposal,history)
    history[key]={"decision":"approved","whatsapp_message_id":receipt["whatsapp_message_id"],
                  "video_sha256":proposal["video_sha256"],
                  "buffer_post_id":history[f"auto:{proposal['proposal_id']}:{proposal['video_sha256']}:shareNow"]["buffer_post_id"]}
    print("EXPLICITLY APPROVED: Buffer Publish Now accepted. Verify final Instagram delivery.")
    return history


def main():
    receipt=json.loads(os.environ["PURAKAU_REVIEW_RECEIPT"])
    proposal=json.loads((REVIEW/"proposal.json").read_text(encoding="utf-8"))
    if not HISTORY.is_file():
        raise RuntimeError("Posting history branch must be restored before approving")
    history=json.loads(HISTORY.read_text(encoding="utf-8"))
    if not isinstance(history,dict):
        raise RuntimeError("Invalid posting history")
    try:
        result=process(receipt,proposal,history)
    finally:
        # Even a failure after Buffer draft creation should retain that ID
        # so the workflow can persist partial success and avoid duplicates.
        if isinstance(history,dict):
            HISTORY.write_text(json.dumps(history,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    HISTORY.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n")


if __name__=="__main__":
    main()
