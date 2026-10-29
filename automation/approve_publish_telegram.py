#!/usr/bin/env python3
"""Independent Telegram human-approval gate for Instagram publishing.

Even if a Telegram webhook is compromised or a different proposal is
substituted, the GitHub workflow independently verifies the timestamped
HMAC, configured Telegram user/chat, original MP4 SHA256 and Buffer channel.
Reject/no reply never calls Buffer. Video bytes are never changed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time

from approve_publish import (
    HISTORY, REVIEW, validate_original_file, submit_approved,
)

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
CALLBACK_RE = re.compile(r"^[A-Za-z0-9_:-]{7,128}$")


def receipt_content(receipt: dict) -> bytes:
    return "|".join((
        "telegram-v1",
        receipt["proposal_id"], receipt["decision"],
        receipt["telegram_callback_id"], receipt["telegram_user_id"],
        receipt["telegram_chat_id"], receipt["video_sha256"],
        str(receipt["issued_at"]),
    )).encode("utf-8")


def verify_telegram_approval(
    receipt: dict, proposal: dict, signing_key: str,
    authorized_user: str, authorized_chat: str, now: int | None = None
) -> None:
    if receipt.get("platform") != "telegram":
        raise ValueError("Only direct Telegram approval callbacks are authorized")
    if receipt.get("decision") not in ("approved", "rejected"):
        raise ValueError("The action must be a positive Approve or Reject button")
    if receipt.get("proposal_id") != proposal.get("proposal_id"):
        raise ValueError("Telegram button approved a different proposed film")
    if receipt.get("video_sha256") != proposal.get("video_sha256"):
        raise ValueError("Telegram button refers to different MP4 bytes")
    if not authorized_user or not authorized_chat:
        raise ValueError("Trusted Telegram reviewer has not been configured")
    if (
        receipt.get("telegram_user_id") != authorized_user
        or receipt.get("telegram_chat_id") != authorized_chat
    ):
        raise ValueError("Telegram approval from wrong user or private chat")
    if not CALLBACK_RE.fullmatch(str(receipt.get("telegram_callback_id", ""))):
        raise ValueError("Invalid Telegram callback ID")
    if not SHA_RE.fullmatch(str(receipt.get("video_sha256", ""))):
        raise ValueError("Invalid reviewed video SHA")
    issued = receipt.get("issued_at")
    now = int(time.time()) if now is None else now
    if not isinstance(issued, int) or not 0 <= now - issued <= 600:
        raise ValueError("Telegram approval signature expired or from the future")
    if len(signing_key) < 32:
        raise ValueError("Signing key unavailable; halt all Instagram publishing")
    signature = receipt.get("signature", "")
    if not isinstance(signature, str) or not SHA_RE.fullmatch(signature):
        raise ValueError("Telegram approval signature missing")
    expected = hmac.new(
        signing_key.encode("utf-8"), receipt_content(receipt),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid cryptographic Telegram approval signature")


def process_telegram(receipt: dict, proposal: dict, history: dict) -> dict:
    verify_telegram_approval(
        receipt, proposal,
        os.getenv("PURAKAU_APPROVAL_SIGNING_KEY", ""),
        os.getenv("TELEGRAM_APPROVER_USER_ID", ""),
        os.getenv("TELEGRAM_REVIEW_CHAT_ID", ""),
    )
    validate_original_file(proposal, REVIEW / "purakau-review.mp4")
    key = "review:" + proposal["proposal_id"]
    already = history.get(key)
    if already:
        if already.get("decision") != receipt["decision"]:
            raise RuntimeError("This video already has an opposite final decision")
        print("Telegram decision already recorded. Refusing duplicate publication.")
        return history

    if receipt["decision"] == "rejected":
        history[key] = {
            "platform": "telegram",
            "decision": "rejected",
            "telegram_callback_id": receipt["telegram_callback_id"],
            "video_sha256": proposal["video_sha256"],
        }
        print("REJECTED on Telegram. Nothing submitted to Instagram.")
        return history

    history = submit_approved(proposal, history)
    reference = (
        "auto:" + proposal["proposal_id"] + ":" +
        proposal["video_sha256"] + ":shareNow"
    )
    record = history.get(reference)
    if not record or not record.get("buffer_post_id"):
        raise RuntimeError("Buffer did not confirm a post ID; approval not recorded")
    history[key] = {
        "platform": "telegram",
        "decision": "approved",
        "telegram_callback_id": receipt["telegram_callback_id"],
        "video_sha256": proposal["video_sha256"],
        "buffer_post_id": record["buffer_post_id"],
    }
    print("Approved original MP4 submitted to Buffer. Final Instagram delivery unconfirmed.")
    return history


def main() -> None:
    receipt = json.loads(os.environ["PURAKAU_TELEGRAM_RECEIPT"])
    proposal = json.loads((REVIEW / "proposal.json").read_text(encoding="utf-8"))
    if not HISTORY.is_file():
        raise RuntimeError("Missing durable post history; publishing disabled")
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    if not isinstance(history, dict):
        raise RuntimeError("Invalid post history")
    try:
        result = process_telegram(receipt, proposal, history)
    finally:
        if isinstance(history, dict):
            HISTORY.write_text(
                json.dumps(history, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    HISTORY.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
