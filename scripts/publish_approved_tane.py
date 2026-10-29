#!/usr/bin/env python3
"""Publish exactly the user-approved V33 Tāne film to @purakaupixel via Buffer.

Do not regenerate or edit the animation. Takes a previously rendered GitHub
Actions artifact, checks exact SHA-256 video identity and release URL, uses
one Buffer draft/post id, and saves durable duplicate-protection history.

Publication acceptance by Buffer is not proof of a visible Instagram post.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from instagram_reels import (
    buffer_api,
    create_post,
    edit_instagram_reel,
    instagram_channel,
    persist_history,
    validate_reel,
    verify_public_release,
)

REPO = "fanisswag654/claystory-ai"
KEY = "tane-nz"
TARGET_CHANNEL = "6ae277352f1f5ed648046667"
APPROVAL_PATH = Path("config/instagram-approved-tane.json")
HISTORY_PATH = Path("instagram-post-history.json")

CAPTION = (
    "Tāne and the First Light 🌿☀️\n\n"
    "In one telling of this pūrākau, Tāne separates Ranginui and "
    "Papatūānuku, allowing light to enter the world. But Tāwhirimātea "
    "grieves their separation and sends storms across the land.\n\n"
    "An original pixel-animated retelling with cinematic AI narration "
    "and original environmental sound effects. Different iwi preserve "
    "different traditions and details.\n\n"
    "Pūrākau Pixels | Stories of Aotearoa\n"
    "#PurakauPixels #Tane #Ranginui #Papatuanuku "
    "#MaoriStories #PixelArt #Aotearoa"
)


def approved_asset() -> tuple[Path, str, str]:
    approved = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    if (
        approved["story"] != KEY
        or approved["source_build_run_id"] != 40794388100
        or approved["source_build_head_sha"] != "fbd9ac1cdb53f980527c2c439d567ae2572cc7ab"
        or approved["source_artifact_id"] != 12862439809
        or approved["review_video_filename"] != "tane-nz-V33-detailed.mp4"
        or approved["character_animation_version"] != "V33"
        or approved["narrator"] != "en-GB-RyanNeural"
    ):
        raise RuntimeError("Approval does not identify the exact V33 rendered film")

    file = Path(os.environ.get("TANE_APPROVED_MP4", "")).resolve()
    expected = approved["review_video_filename"]
    if not file.is_file() or file.name != expected:
        raise RuntimeError(f"Cannot find exact approved file {expected}")
    if file.stat().st_size < 100_000:
        raise RuntimeError("Tāne film is unexpectedly small")
    sha = hashlib.sha256(file.read_bytes()).hexdigest()
    if len(sha) != 64:
        raise RuntimeError("Cannot fingerprint approved original film")

    report_file = file.parent / "film-report.json"
    if not report_file.is_file():
        raise RuntimeError("Missing original MP4 render report")
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if (
        report.get("story") != "Tāne and the First Light"
        or report.get("animation_version") != "V33 detailed articulated pixel actors"
        or report.get("narrator") != "en-GB-RyanNeural"
        or report.get("scenes") != 8
        or report.get("resolution") != "540x960"
        or report.get("fps") != 24
        or report.get("video") != "tane-nz-balanced.mp4"
    ):
        raise RuntimeError("Video report does not match the approved V33 film")
    print("Approved unchanged video:", file.name, "SHA-256", sha, flush=True)
    print("Instagram-compatible specs:", validate_reel(file), flush=True)
    tag = f"instagram-tane-nz-v33-{sha}"
    url = f"https://github.com/{REPO}/releases/download/{tag}/{expected}"
    return file, sha, url


def read_history() -> dict:
    if not HISTORY_PATH.is_file():
        raise RuntimeError("Instagram posting history branch was not restored")
    data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Posting history must be a JSON object")
    return data


def confirm_existing_post(post_id: str, channel_id: str) -> dict:
    post = buffer_api(
        "query { post(input: { id: " + json.dumps(post_id) +
        " }) { id channelId status shareMode } }"
    ).get("post")
    if (
        not post
        or post.get("id") != post_id
        or post.get("channelId") != channel_id
    ):
        raise RuntimeError("Existing Buffer draft belongs to an unexpected account")
    return post


def main() -> None:
    if os.getenv("IG_MODE") != "draft":
        raise RuntimeError("Use the safe draft-to-Publish-Now path only")
    if not os.getenv("BUFFER_API_KEY"):
        raise RuntimeError("Missing BUFFER_API_KEY; cannot publish to Buffer")
    if os.getenv("INSTAGRAM_USERNAME", "").lstrip("@").lower() != "purakaupixel":
        raise RuntimeError("Instagram destination must be @purakaupixel")

    video, sha, url = approved_asset()
    history = read_history()
    draft_key = f"{KEY}:{sha}:draft"
    published_key = f"{KEY}:{sha}:shareNow"

    if published_key in history:
        record = history[published_key]
        if record.get("video_url") != url:
            raise RuntimeError("Historical post URL does not match approved media")
        print("Exact Tāne V33 video already submitted to Buffer; duplicate refused.")
        print("Original Buffer post id:", record["buffer_post_id"])
        return

    # Verify the approved GitHub Release asset is public and contains audio.
    # Hosting was performed in the preceding workflow step without re-encoding.
    verify_public_release(url)
    channel = instagram_channel()
    if channel["id"] != TARGET_CHANNEL:
        raise RuntimeError(
            "The selected Instagram channel is not the previously verified "
            "@purakaupixel account. Refusing to upload elsewhere."
        )

    if draft_key in history:
        draft = history[draft_key]
        if draft.get("video_url") != url or draft.get("channel_id") != channel["id"]:
            raise RuntimeError("Unrecognized existing Tāne draft; avoid duplicate")
        post_id = draft["buffer_post_id"]
        prior = confirm_existing_post(post_id, channel["id"])
        status = (prior.get("status") or "").lower()
        print("Reusing existing Tāne Buffer post:", post_id, status)
        if status in {"sent", "scheduled", "sending"}:
            # The earlier request was accepted; don't duplicate or re-submit.
            published = prior
        elif status == "draft":
            published = edit_instagram_reel(post_id, url, CAPTION, "shareNow")
        else:
            raise RuntimeError(
                f"Existing Buffer post has unexpected status {status}; do not retry"
            )
    else:
        # Save the first post ID BEFORE moving it out of drafts. The workflow
        # persists this history even if Buffer rejects the subsequent mutation.
        draft = create_post(channel["id"], url, CAPTION)
        post_id = draft["id"]
        history[draft_key] = {
            "story": KEY,
            "source_fingerprint": sha,
            "buffer_post_id": post_id,
            "channel_id": channel["id"],
            "mode": "draft",
            "video_url": url,
            "video_sha256": sha,
            "source_workflow_run": 40794388100,
        }
        persist_history(history)
        print("Created exactly one Tāne draft:", post_id, flush=True)
        published = edit_instagram_reel(post_id, url, CAPTION, "shareNow")

    if published.get("id") != post_id:
        raise RuntimeError("Buffer returned a different Instagram post ID")

    history[published_key] = {
        "story": KEY,
        "source_fingerprint": sha,
        "buffer_post_id": post_id,
        "channel_id": channel["id"],
        "mode": "shareNow",
        "share_mode": "shareNow",
        "video_url": url,
        "video_sha256": sha,
        "buffer_status": published.get("status"),
        "source_workflow_run": 40794388100,
        "notes": "Accepted by Buffer; confirm sent status on Instagram",
    }
    persist_history(history)
    print("Submitted approved unchanged Tāne V33 Reel to Buffer Publish Now.")
    print("Existing/new post id:", post_id, flush=True)
    print("Buffer API status:", published.get("status"), flush=True)
    print("Final publication on Instagram not yet independently verified.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Approved Tāne Instagram upload failed:", exc, file=sys.stderr)
        raise
