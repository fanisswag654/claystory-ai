#!/usr/bin/env python3
"""Send a brand-new free curated Pūrākau Pixels MP4 to Telegram for review.

This deliberately NEVER creates a production 'auto-review' release, never
calls GitHub repository_dispatch, and cannot publish anything to Instagram.
The test-only Telegram buttons have a separate namespace recognized by
the Render webhook; no Buffer keys are available to the workflow.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

import requests

from prepare_story import ROOT, source_briefs, curated_script, build_candidate
# Keep this sender independent of the Flask/Render publishing webhook.
# Offline tests compare these test-only strings to the webhook allowlist.
TEST_PREVIEW_MARKER = "PŪRĀKAU PIXELS VIDEO TEST ONLY — NO INSTAGRAM"
TEST_PREVIEW_ACTIONS = {
    "test_preview:approve:free": "approve",
    "test_preview:reject:free": "reject",
}

OUT = ROOT / "automation" / "output"
MAX_VIDEO_BYTES = 15 * 1024 * 1024
TOKEN_PATTERN = re.compile(r"^[0-9]{5,16}:[A-Za-z0-9_-]{25,80}$")
USER_PATTERN = re.compile(r"^[0-9]{5,20}$")


def verified_private_credentials(env: dict) -> tuple[str, str]:
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    user = env.get("TELEGRAM_APPROVER_USER_ID", "")
    chat = env.get("TELEGRAM_REVIEW_CHAT_ID", "")
    if not TOKEN_PATTERN.fullmatch(token):
        raise RuntimeError("GitHub Telegram bot token missing or malformed")
    if not USER_PATTERN.fullmatch(user) or not USER_PATTERN.fullmatch(chat):
        raise RuntimeError("Private Telegram approver and chat IDs must be numeric")
    if chat != user:
        raise RuntimeError("Refusing to send a free preview to a group or another user")
    return token, chat


def verify_curated_film(video: Path, story_path: Path, manifest_path: Path) -> dict:
    story = json.loads(story_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    topic = next((t for t in source_briefs()["topics"] if t["id"] == story.get("key")), None)
    if topic is None:
        raise ValueError("Unknown source-backed curated story")
    authoritative = build_candidate(topic, curated_script(topic))
    expected = {**authoritative, "script_origin": "checked-in-curated-original"}
    if story != expected:
        raise ValueError("Candidate does not exactly match the checked-in curated script")
    if (
        manifest.get("story_id") != topic["id"]
        or manifest.get("title") != topic["title"]
        or manifest.get("narrator") != "en-GB-RyanNeural"
        or manifest.get("status") != "pending-human-approval"
        or manifest.get("sources") != topic["sources"]
        or manifest.get("video_file") != "purakau-review.mp4"
    ):
        raise ValueError("Curated preview manifest identity, narrator or sources mismatch")
    if video.name != "purakau-review.mp4" or not video.is_file():
        raise ValueError("A real original MP4 is required")
    if not 100_000 < video.stat().st_size <= MAX_VIDEO_BYTES:
        raise ValueError("MP4 missing or outside the 15 MiB Telegram test limit")
    video_digest = hashlib.sha256(video.read_bytes()).hexdigest()
    if manifest.get("video_sha256") != video_digest or manifest.get("bytes") != video.stat().st_size:
        raise ValueError("MP4 differs from the one produced by the browser renderer")
    return {"title": story["title"], "key": story["key"], "sha256": video_digest}


def preview_keyboard() -> dict:
    return {"inline_keyboard": [[
        {"text": "✅ Approve preview (NO POST)", "callback_data": "test_preview:approve:free"},
        {"text": "❌ Reject preview", "callback_data": "test_preview:reject:free"},
    ]]}


def send_free_preview(video: Path = OUT / "purakau-review.mp4",
                      story_path: Path = OUT / "story.json",
                      manifest_path: Path = OUT / "manifest.json",
                      env: dict | None = None) -> dict:
    token, chat_id = verified_private_credentials(os.environ if env is None else env)
    story = verify_curated_film(video, story_path, manifest_path)
    if (
        TEST_PREVIEW_ACTIONS.get("test_preview:approve:free") != "approve"
        or TEST_PREVIEW_ACTIONS.get("test_preview:reject:free") != "reject"
    ):
        raise RuntimeError("Render test-only callback namespace unavailable")
    caption = (
        f"🧪 {TEST_PREVIEW_MARKER}\n\n"
        f"🎬 NEW FREE CURATED PŪRĀKAU\n{story['title']}\n\n"
        "This is a newly generated pixel-art film with the free "
        "prewritten, source-backed narration and original sound effects.\n"
        "Please check te reo Māori pronunciation, cultural details, visuals and audio.\n\n"
        "Both buttons are PREVIEW TESTS ONLY.\n"
        "APPROVE = confirm your preview choice in Telegram; it does NOT publish.\n"
        "REJECT = feedback only; it does NOT publish.\n"
        "No reply = no action. Instagram publishing remains OFF."
    )
    with video.open("rb") as media:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideo",
            data={
                "chat_id": chat_id,
                "caption": caption,
                "supports_streaming": "true",
                "reply_markup": json.dumps(preview_keyboard()),
            },
            files={"video": (video.name, media, "video/mp4")},
            timeout=(20, 210),
        )
    if response.status_code != 200:
        raise RuntimeError(f"Telegram refused the free preview (HTTP {response.status_code})")
    answer = response.json()
    message = answer.get("result", {}) if answer.get("ok") else {}
    if (
        str(message.get("chat", {}).get("id", "")) != chat_id
        or not message.get("video")
        or not isinstance(message.get("message_id"), int)
    ):
        raise RuntimeError("Telegram did not confirm delivery to the private reviewer")
    return {
        "status": "free_preview_delivered_only",
        "story": story["key"],
        "video_sha256": story["sha256"],
        "telegram_message_id": message["message_id"],
        "instagram_published": False,
    }


def main() -> None:
    info = send_free_preview()
    print("Successfully delivered NEW curated Telegram MP4 preview, story:", info["story"])
    print("Verified SHA-256:", info["video_sha256"])
    print("Telegram message ID:", info["telegram_message_id"])
    print("NO API script charge, NO approval for posting, NO Buffer/Instagram calls")


if __name__ == "__main__":
    main()
