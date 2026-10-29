#!/usr/bin/env python3
"""A FREE, no-Instagram Telegram MP4 + buttons smoke test.

Downloads the owner's existing approved Tāne V33 film, checks the original
GitHub Release SHA-256, and sends it to the verified private chat. Buttons
have an isolated callback namespace and CAN NEVER authorize publication.
No AI generation, Buffer API, Instagram, or GitHub repository_dispatch.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import requests

ORIGINAL_RELEASE_TAG = (
    "instagram-tane-nz-v33-"
    "9e2e1f720ccc8b3f641a32e8fe668d9ff30824a1e2eef87bc65725d1815a4f52"
)
EXPECTED_SHA256 = "9e2e1f720ccc8b3f641a32e8fe668d9ff30824a1e2eef87bc65725d1815a4f52"
ORIGINAL_VIDEO_URL = (
    "https://github.com/fanisswag654/claystory-ai/releases/download/"
    + ORIGINAL_RELEASE_TAG + "/tane-nz-V33-detailed.mp4"
)
TEST_MARKER = "PŪRĀKAU PIXELS VIDEO TEST ONLY — NO INSTAGRAM"
TEST_CALLBACKS = {"approve": "test_preview:approve:v33", "reject": "test_preview:reject:v33"}
MAX_BYTES = 15 * 1024 * 1024


def secure_config(env: dict) -> tuple[str, str]:
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_REVIEW_CHAT_ID", "")
    user_id = env.get("TELEGRAM_APPROVER_USER_ID", "")
    if not re.fullmatch(r"[0-9]{5,16}:[A-Za-z0-9_-]{25,80}", token):
        raise RuntimeError("BotFather token missing or malformed in GitHub secret")
    if not re.fullmatch(r"[0-9]{5,20}", chat_id):
        raise RuntimeError("No valid private Telegram review chat ID configured")
    if user_id != chat_id:
        raise RuntimeError("Reviewer ID and private chat ID must match for a private bot conversation")
    return token, chat_id


def preview_keyboard() -> dict:
    return {"inline_keyboard": [[
        {"text": "✅ Approve (TEST ONLY)", "callback_data": TEST_CALLBACKS["approve"]},
        {"text": "❌ Reject (TEST ONLY)", "callback_data": TEST_CALLBACKS["reject"]},
    ]]}


def fetch_checked_video(destination: Path) -> None:
    digest = hashlib.sha256()
    size = 0
    with requests.get(ORIGINAL_VIDEO_URL, stream=True, timeout=(20, 120)) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Cannot retrieve existing approved V33 film (HTTP {response.status_code})")
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_BYTES:
                    raise RuntimeError("Video is too large for review test")
                digest.update(chunk)
                output.write(chunk)
    if size < 100_000 or digest.hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Received film differs from original approved V33 GitHub Release; will not send")
    print("Verified original previously approved V33 video: SHA-256 matches (no new story generated).")


def send_checked_preview(token: str, chat_id: str, video: Path) -> int:
    caption = (
        f"🧪 {TEST_MARKER}\n\n"
        "This is your previously approved Tāne and the First Light V33 video.\n\n"
        "Watch the video, then tap either button to check the "
        "Telegram review interface.\n\n"
        "IMPORTANT: Both buttons are TEST ONLY. "
        "Neither button can publish to Instagram. "
        "Your automated publishing remains DISABLED."
    )
    with video.open("rb") as stream:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideo",
            data={
                "chat_id": chat_id,
                "caption": caption,
                "supports_streaming": "true",
                "reply_markup": json.dumps(preview_keyboard()),
            },
            files={"video": ("tane-v33-preview-test.mp4", stream, "video/mp4")},
            timeout=(20, 200),
        )
    if response.status_code != 200:
        raise RuntimeError(
            f"Telegram video test failed (HTTP {response.status_code}); "
            "review bot token, chat ID, file size, or test rate limits."
        )
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError("Telegram rejected the video test (Bot token not exposed)")
    message = result.get("result", {})
    if (
        str(message.get("chat", {}).get("id", "")) != chat_id
        or not message.get("video")
        or not isinstance(message.get("message_id"), int)
    ):
        raise RuntimeError("Telegram did not confirm the verified MP4 sent to the intended private chat")
    print("SAFE TEST: Verified Tāne MP4 and two TEST ONLY buttons delivered to the private bot chat.")
    print("This workflow has no Instagram/Buffer/post-dispatch permissions or actions.")
    return message["message_id"]


def main() -> None:
    token, chat_id = secure_config(os.environ)
    with tempfile.TemporaryDirectory(prefix="purakau-preview-test-") as temp:
        video = Path(temp) / "tane-v33.mp4"
        fetch_checked_video(video)
        message_id = send_checked_preview(token, chat_id, video)
    print("Telegram test message ID:", message_id)


if __name__ == "__main__":
    main()
