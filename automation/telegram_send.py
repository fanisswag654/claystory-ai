#!/usr/bin/env python3
"""Deliver an exact, SHA-pinned ClayStory MP4 to one Telegram chat for review.

Uses Telegram's official sendVideo multipart API, not an external upload
service. Telegram bot/account setup is required and never hard-coded here.
No Instagram/Buffer APIs are called by this file.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys

import requests

REPO = "fanisswag654/claystory-ai"
PROPOSAL_PATTERN = re.compile(r"^auto-review-[a-z0-9-]+-[0-9a-f]{12}$")
SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")
MAX_VIDEO_BYTES = 48 * 1024 * 1024
VIDEO = Path("automation/output/purakau-review.mp4")


def valid_chat_id(value: str) -> str:
    if not re.fullmatch(r"-?[0-9]{5,20}", value):
        raise ValueError("TELEGRAM_REVIEW_CHAT_ID must be a numeric chat ID, not a username")
    return value


def review_keyboard(proposal_id: str) -> dict:
    if not PROPOSAL_PATTERN.fullmatch(proposal_id):
        raise ValueError("Invalid review proposal ID")
    labels = ["approve:" + proposal_id, "reject:" + proposal_id]
    if any(len(x.encode("utf-8")) > 64 for x in labels):
        raise ValueError("Review tag too long for Telegram inline buttons")
    return {"inline_keyboard": [[
        {"text": "✅ Approve for Instagram", "callback_data": labels[0]},
        {"text": "❌ Reject video", "callback_data": labels[1]},
    ]]}


def verify_review(proposal: dict, video: Path) -> None:
    pid = proposal.get("proposal_id", "")
    sha = proposal.get("video_sha256", "")
    if not PROPOSAL_PATTERN.fullmatch(pid) or not SHA_PATTERN.fullmatch(sha):
        raise ValueError("Invalid proposal/video signature")
    if not pid.endswith(sha[:12]) or proposal.get("status") != "pending":
        raise ValueError("Expected pending immutable reviewed video")
    expected = f"https://github.com/{REPO}/releases/download/{pid}/purakau-review.mp4"
    if proposal.get("video_url") != expected:
        raise ValueError("Video URL not in matching immutable source release")
    if not video.is_file() or video.name != "purakau-review.mp4":
        raise ValueError("Missing actual reviewed MP4")
    if not 100_000 < video.stat().st_size <= MAX_VIDEO_BYTES:
        raise ValueError("Reviewed video outside Telegram delivery limits")
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    if digest != sha:
        raise ValueError("Video bytes differ from the immutable approved-release SHA")
    if proposal.get("narrator") not in ("en-GB-RyanNeural", "en-US-ChristopherNeural"):
        raise ValueError("Wrong cinematic narrator selected")


def message_payload(proposal: dict, chat_id: str) -> dict:
    valid_chat_id(chat_id)
    title = str(proposal.get("title", "")).strip()
    if not 3 <= len(title) <= 160:
        raise ValueError("Invalid story title")
    return {
        "chat_id": chat_id,
        "caption": (
            f"🎬 NEW PŪRĀKAU PIXELS FILM\n{title}\n\n"
            "Watch the entire video and review the te reo Māori pronunciation, "
            "cultural details, visuals and soundtrack.\n\n"
            "Approve = publish THIS exact MP4 to @purakaupixel via Buffer.\n"
            "Reject = do NOT publish.\n"
            "No reply = nothing gets published.\n\n"
            f"Review ID: {proposal['proposal_id']}"
        )[:1000],
        "supports_streaming": "true",
        "reply_markup": json.dumps(review_keyboard(proposal["proposal_id"])),
    }


def send_video(proposal: dict, video: Path = VIDEO) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_REVIEW_CHAT_ID", "")
    if not token or not chat_id:
        raise RuntimeError("Telegram bot token or reviewer chat ID missing; no video was sent")
    if not re.fullmatch(r"[0-9]{5,16}:[A-Za-z0-9_-]{25,80}", token):
        raise ValueError("Invalid Telegram bot token format; check GitHub Actions Secret")
    verify_review(proposal, video)
    payload = message_payload(proposal, chat_id)
    with video.open("rb") as file:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideo",
            data=payload,
            files={"video": ("purakau-review.mp4", file, "video/mp4")},
            timeout=(20, 210),
        )
    if response.status_code != 200:
        raise RuntimeError(f"Telegram refused video delivery (HTTP {response.status_code}); "
                           "check bot /start, chat ID and file limits, without revealing the token")
    result = response.json()
    if not result.get("ok") or not result.get("result", {}).get("message_id"):
        raise RuntimeError("Telegram did not confirm the original review video")
    sent = result["result"]
    if str(sent.get("chat", {}).get("id")) != chat_id:
        raise RuntimeError("Telegram message went to an unexpected reviewer; stop automation")
    if not sent.get("video"):
        raise RuntimeError("Telegram did not return a video attachment")
    return {
        "telegram_message_id": sent["message_id"],
        "telegram_chat_id": str(sent["chat"]["id"]),
        "proposal_id": proposal["proposal_id"],
        "status": "delivered_for_review_not_approved",
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python automation/telegram_send.py automation/output/proposal.json")
    proposal = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = send_video(proposal)
    # Only public IDs are logged. Do not print token, private usernames or phone numbers.
    print("Review MP4 delivered to configured Telegram chat; message ID",
          result["telegram_message_id"], ". Not approved or published.", flush=True)


if __name__ == "__main__":
    main()
