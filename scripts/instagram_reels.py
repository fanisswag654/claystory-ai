"""Publish original ClayStory films to Instagram Reels via Buffer.

Renders finished films from the checked-out original animation source and
hosts them as immutable GitHub Release assets. Never depends on GitHub Pages,
TikTok-auto-clipper, Cloudinary credentials, or TikTok channels.

Modes:
  check - validate publicly hosted MP4 files, no Buffer access
  draft - create Instagram-only Buffer drafts
  queue - queue Instagram Reels for automatic publishing via Buffer

Queue mode requires explicit IG_AUTO_PUBLISH=true in repository variables.
History is persisted by GitHub Actions in a separate private-to-workflow branch.
"""
from __future__ import annotations

import hashlib
import json
import time
import os
from pathlib import Path
import subprocess
import sys
from fractions import Fraction

import requests

REPOSITORY = os.getenv("GITHUB_REPOSITORY", "fanisswag654/claystory-ai")
HISTORY_FILE = Path(os.getenv("IG_HISTORY_PATH", "instagram-post-history.json"))
MODE = os.getenv("IG_MODE", "check").strip().lower()
LIMIT = max(1, min(2, int(os.getenv("IG_MAX_POSTS", "1"))))
TARGET_USERNAME = os.getenv("INSTAGRAM_USERNAME", "").strip().lstrip("@").lower()
TARGET_CHANNEL_ID = os.getenv("INSTAGRAM_CHANNEL_ID", "").strip()

STORIES = [
    {
        "key": "fish-nz",
        "name": "Māui and the Great Fish",
        "caption": (
            "How did Māui pull up a great fish from the ocean? 🌊\n\n"
            "A pixel-animated telling of the pūrākau of Māui and the Great Fish, "
            "with narration and original sound effects.\n\n"
            "This is one telling; details differ across iwi traditions.\n\n"
            "Pūrākau Pixels | Stories of Aotearoa\n"
            "#PurakauPixels #Maui #MaoriStories #PixelArt #Aotearoa"
        ),
    },
    {
        "key": "maui-nz",
        "name": "Māui and the Sun",
        "caption": (
            "Why does the sun travel slowly across the sky? ☀️\n\n"
            "A pixel-animated telling of the pūrākau of Māui and the Sun, "
            "featuring original artwork, narration and sound effects.\n\n"
            "This is one telling; details differ across iwi traditions.\n\n"
            "Pūrākau Pixels | Stories of Aotearoa\n"
            "#PurakauPixels #Maui #MaoriStories #PixelArt #Aotearoa"
        ),
    },
]

SESSION = requests.Session()


def fingerprint_source(story_key: str) -> str:
    """Fingerprint animation code + complete narration/mix to avoid reposts."""
    digest = hashlib.sha256()
    paths = [
        Path("index.html"),
        Path("scripts/v29_motion.js"),
        Path("vendor/tween.umd.js"),
        Path("scripts/render_films.py"),
        Path(f"audio/{story_key}-timing.json"),
        Path(f"audio/{story_key}-mix-balanced.mp3"),
    ]
    for file in paths:
        if not file.is_file():
            raise RuntimeError(f"Missing ClayStory render input: {file}")
        digest.update(str(file).encode("utf-8"))
        with file.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def github_release_asset(story_key: str, source_hash: str) -> tuple[str, Path | None]:
    """Create a versioned, public MP4 if missing, using original renderer.

    This avoids the GitHub Pages 404 entirely. GitHub Releases are public
    in this public repository; the versioned URL remains stable for Buffer.
    """
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("GITHUB_TOKEN is not available for GitHub Releases")
    tag = f"instagram-{story_key}-{source_hash[:16]}"
    filename = f"{story_key}-balanced.mp4"
    url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{filename}"
    lookup = subprocess.run(
        ["gh", "release", "view", tag, "--repo", REPOSITORY,
         "--json", "assets", "--jq", ".assets[].name"],
        capture_output=True, text=True,
    )
    found = lookup.returncode == 0 and filename in lookup.stdout.splitlines()
    if found:
        print(f"Reusing existing original ClayStory Reel asset: {tag}/{filename}", flush=True)
        return url, None

    print(f"Rendering original ClayStory film for GitHub Release {tag}", flush=True)
    subprocess.run(
        [sys.executable, "scripts/render_films.py",
         "--story", story_key.removesuffix("-nz"), "--mix", "balanced"],
        check=True,
    )
    video = Path("videos") / filename
    if not video.is_file():
        raise RuntimeError(f"Original film renderer did not create {video}")
    print("New film validated:", validate_reel(video), flush=True)

    if lookup.returncode == 0:
        # The versioned release exists, but the requested file is missing.
        command = ["gh", "release", "upload", tag, str(video),
                   "--repo", REPOSITORY]
    else:
        command = ["gh", "release", "create", tag, str(video),
                   "--repo", REPOSITORY, "--target",
                   os.getenv("GITHUB_SHA", "main"),
                   "--title", f"ClayStory original animation {story_key} ({source_hash[:12]})",
                   "--notes", "Versioned original pixel-animated film for Pūrākau Pixels Instagram Reels. This public asset is hosted for Buffer media delivery."]
    subprocess.run(command, check=True)
    print("Hosted original film:", url, flush=True)
    return url, video


def verify_public_release(url: str) -> None:
    """Wait for the GitHub Releases CDN to make the MP4 publicly readable."""
    for attempt in range(1, 9):
        try:
            with SESSION.get(url, headers={"Range": "bytes=0-1023"},
                             stream=True, timeout=(20, 60),
                             allow_redirects=True) as response:
                response.raise_for_status()
                iterator = response.iter_content(chunk_size=1024)
                first = next(iterator, b"")
                if not first:
                    raise RuntimeError("Public video asset is empty")
                mime = response.headers.get("content-type", "").lower()
                if "html" in mime:
                    raise RuntimeError(f"Public asset returned HTML, not MP4: {url}")
                print(f"Public Reel URL verified (HTTP {response.status_code})", flush=True)
                return
        except (requests.RequestException, RuntimeError) as error:
            if attempt == 8:
                raise RuntimeError(
                    "GitHub Releases did not provide a public MP4. "
                    "Instagram draft was not created; retry when the release is accessible."
                ) from error
            print(f"Release delivery not yet ready ({attempt}/8): {error}", flush=True)
            time.sleep(5)


def validate_reel(video: Path) -> str:
    """Prevent knowingly sending unsupported media to Instagram."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
         str(video)],
        text=True, capture_output=True, check=True,
    )
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    visual = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not visual or not audio:
        raise RuntimeError("Instagram Reel needs both video and narration audio")
    width, height = visual["width"], visual["height"]
    ratio = width / height
    fps = float(Fraction(visual["r_frame_rate"]))
    duration = float(data["format"]["duration"])
    if not (0.54 <= ratio <= 0.58 and width <= 1920 and height > width):
        raise RuntimeError(f"Video must be portrait 9:16; got {width}x{height}")
    if not (23.0 <= fps <= 60.1):
        raise RuntimeError(f"Video FPS must be 24–60; got {fps}")
    if not (3 <= duration <= 900):
        raise RuntimeError(f"Reel must be 3 sec–15 min; got {duration}s")
    return f"{width}x{height}, {fps:.1f} fps, {duration:.1f}s"


def buffer_api(query: str) -> dict:
    response = SESSION.post(
        "https://api.buffer.com",
        json={"query": query},
        headers={
            "Authorization": "Bearer " + os.environ["BUFFER_API_KEY"],
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError("Buffer API rejected query: " + json.dumps(body["errors"]))
    return body["data"]


def instagram_channel() -> dict:
    if TARGET_CHANNEL_ID:
        selected = buffer_api(
            "query { channel(input: { id: " + json.dumps(TARGET_CHANNEL_ID) +
            " }) { id name displayName service isQueuePaused } }"
        )["channel"]
        candidates = [selected] if selected else []
    else:
        orgs = buffer_api(
            "query { account { organizations { id name } } }"
        )["account"]["organizations"]
        candidates = []
        for org in orgs:
            channels = buffer_api(
                "query { channels(input: { organizationId: " + json.dumps(org["id"]) +
                " }) { id name displayName service isQueuePaused } }"
            )["channels"]
            candidates.extend(
                c for c in channels if "instagram" in (c.get("service") or "").lower()
            )

    candidates = [
        c for c in candidates if c and "instagram" in (c.get("service") or "").lower()
    ]
    if TARGET_USERNAME:
        candidates = [
            c for c in candidates if TARGET_USERNAME in
            {
                (c.get("name") or "").lstrip("@").lower(),
                (c.get("displayName") or "").lstrip("@").lower(),
            }
        ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"Found {len(candidates)} matching Instagram channels. Connect your "
            "Instagram Professional account in Buffer, then set repository "
            "variable INSTAGRAM_USERNAME to the exact handle (without @), "
            "or add the INSTAGRAM_CHANNEL_ID secret."
        )
    channel = candidates[0]
    if channel.get("isQueuePaused") and MODE == "queue":
        raise RuntimeError("Instagram Buffer queue is paused; resuming it requires user action")
    print("Confirmed Instagram-only channel:", channel["name"], flush=True)
    return channel


def create_post(channel_id: str, video_url: str, caption: str) -> dict:
    save_to_draft = "true" if MODE == "draft" else "false"
    query = (
        "mutation { createPost(input: { "
        "text: " + json.dumps(caption, ensure_ascii=False)
        + " channelId: " + json.dumps(channel_id)
        + " schedulingType: automatic"
        + " mode: addToQueue"
        + " metadata: { instagram: { type: reel, shouldShareToFeed: true, isAiGenerated: true } }"
        + " saveToDraft: " + save_to_draft
        + " assets: [{ video: { url: " + json.dumps(video_url)
        + " metadata: { thumbnailOffset: 2000 } } }]"
        + " }) {"
        + " ... on PostActionSuccess { post { id status dueAt } }"
        + " ... on MutationError { message }"
        + " } }"
    )
    result = buffer_api(query)["createPost"]
    post = result.get("post")
    if not post:
        raise RuntimeError("Instagram Buffer post failed: " + str(result))
    return post


def edit_instagram_reel(post_id: str, video_url: str, caption: str,
                        share_mode: str) -> dict:
    """Edit an existing Instagram Reel with *complete* valid post content.

    Buffer validates the edited post in full when it moves out of Drafts.
    Explicitly supply caption, video asset and Instagram type rather than
    relying on a partial edit being merged with the existing draft.
    """
    if share_mode not in ("shareNow", "addToQueue"):
        raise ValueError("Only immediate or queued Instagram Reel publishing is supported")
    if not post_id or not video_url or not caption.strip():
        raise ValueError("Buffer Reel edits require the reviewed ID, video and caption")
    if not video_url.startswith(
        "https://github.com/" + REPOSITORY + "/releases/download/"
    ):
        raise ValueError("Refusing to publish a video outside the approved ClayStory Releases")
    query = (
        "mutation { editPost(input: {"
        + " id: " + json.dumps(post_id)
        + " text: " + json.dumps(caption, ensure_ascii=False)
        + " assets: [{ video: { url: " + json.dumps(video_url)
        + " metadata: { thumbnailOffset: 2000 } } }]"
        + " metadata: { instagram: { type: reel shouldShareToFeed: true isAiGenerated: true } }"
        + " schedulingType: automatic"
        + " mode: " + share_mode
        + " saveToDraft: false"
        + " }) {"
        + " ... on PostActionSuccess { post { id status shareMode dueAt } }"
        + " ... on MutationError { message }"
        + " } }"
    )
    result = buffer_api(query)["editPost"]
    post = result.get("post")
    if not post or post.get("id") != post_id:
        raise RuntimeError(
            f"Buffer rejected complete Instagram Reel edit ({share_mode}): {result}"
        )
    if str(post.get("status") or "").lower() == "draft":
        raise RuntimeError("Buffer did not move the Instagram Reel out of Drafts")
    return post


def schedule_existing_draft(post_id: str, video_url: str, caption: str) -> dict:
    """Queue a reviewed Reel with the complete media and Instagram metadata."""
    return edit_instagram_reel(post_id, video_url, caption, "addToQueue")


def persist_history(data: dict) -> None:
    tmp = HISTORY_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(HISTORY_FILE)


def main() -> None:
    if MODE not in ("check", "draft", "queue"):
        raise RuntimeError("IG_MODE must be check, draft, or queue")
    if MODE == "queue" and os.getenv("IG_AUTO_PUBLISH", "").lower() != "true":
        print("Automatic Instagram publishing is not enabled; running check-only mode.")
        mode = "check"
    else:
        mode = MODE
    if mode != "check" and not (TARGET_USERNAME or TARGET_CHANNEL_ID):
        raise RuntimeError("Set INSTAGRAM_USERNAME as a ClayStory Actions variable before creating drafts or queued Reels")
    if mode != "check" and not os.environ.get("BUFFER_API_KEY"):
        raise RuntimeError("Add BUFFER_API_KEY as an Actions secret in the ClayStory repo")

    history = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {}
    if not isinstance(history, dict):
        raise RuntimeError("Invalid Instagram posting history")
    created = 0
    channel = None
    for story in STORIES:
        if created >= LIMIT:
            break
        key = story["key"]
        fingerprint = fingerprint_source(key)
        unique_key = f"{key}:{fingerprint}:{mode}"
        if unique_key in history:
            print(f"Already submitted {story['name']}, {fingerprint[:12]}; skipping")
            continue
        if mode == "queue":
            approval_file = Path("config/instagram-approved.json")
            approved = (json.loads(approval_file.read_text(encoding="utf-8"))
                        if approval_file.exists() else {})
            permitted = approved.get("approved_reels", {}).get(key, [])
            if fingerprint not in permitted:
                print(f"Skipping unreviewed film: {story['name']} ({fingerprint[:12]})")
                continue

        print(f"New Instagram Reel source: {story['name']}, {fingerprint[:12]}", flush=True)
        # Release assets replace the old Pages /videos/ URL that returned 404.
        video_url, local_video = github_release_asset(key, fingerprint)
        if local_video:
            print("Instagram video specs:", validate_reel(local_video))
        verify_public_release(video_url)

        if mode == "check":
            created += 1
            continue
        if channel is None:
            channel = instagram_channel()
        original_draft = history.get(f"{key}:{fingerprint}:draft") if mode == "queue" else None
        if original_draft and original_draft.get("buffer_post_id"):
            if original_draft.get("channel_id") != channel["id"]:
                raise RuntimeError("Existing draft belongs to a different Buffer channel")
            post = schedule_existing_draft(original_draft["buffer_post_id"], video_url, story["caption"])
            print("Moved reviewed Buffer draft into Instagram queue without duplicating it")
        else:
            post = create_post(channel["id"], video_url, story["caption"])
        if mode == "queue" and str(post.get("status", "")).lower() == "draft":
            raise RuntimeError("Buffer returned draft status; refusing to mark it scheduled")
        history[unique_key] = {
            "story": key,
            "source_fingerprint": fingerprint,
            "buffer_post_id": post["id"],
            "channel_id": channel["id"],
            "mode": mode,
            "video_url": video_url,
        }
        persist_history(history)
        print(f"Instagram {mode} successful: {story['name']}, Buffer ID {post['id']}")
        created += 1
    print(
        f"Completed: {created} new {'eligible video(s)' if mode == 'check' else 'Instagram item(s)'}. "
        "No TikTok account was used."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ClayStory Instagram automation failed:", exc, file=sys.stderr)
        raise
