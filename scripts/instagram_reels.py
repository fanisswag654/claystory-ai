"""Publish original ClayStory films to Instagram Reels via Buffer.

Uses the ClayStory GitHub Pages MP4 URLs. There is no dependency on
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
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from fractions import Fraction
from urllib.parse import urljoin

import requests

PAGES_BASE = os.getenv(
    "CLAYSTORY_PAGES_BASE", "https://fanisswag654.github.io/claystory-ai/"
).rstrip("/") + "/"
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


def download_public_video(url: str, output: Path) -> str:
    """Download the rendered video and return an SHA-256 content fingerprint."""
    digest = hashlib.sha256()
    length = 0
    try:
        with SESSION.get(url, stream=True, timeout=(20, 150), allow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "html" in content_type:
                raise RuntimeError(f"Expected a public MP4 but received HTML at {url}")
            with output.open("wb") as target:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    length += len(chunk)
                    if length > 300 * 1024 * 1024:
                        raise RuntimeError(f"Instagram Reel exceeds 300MB: {url}")
                    digest.update(chunk)
                    target.write(chunk)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Cannot download {url}. Check that ClayStory GitHub Pages deployment "
            "is active and videos are public."
        ) from exc
    if length < 50_000:
        raise RuntimeError(f"Video is unexpectedly small: {url} ({length} bytes)")
    return digest.hexdigest()


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
    if mode != "check" and not os.environ.get("BUFFER_API_KEY"):
        raise RuntimeError("Add BUFFER_API_KEY as an Actions secret in the ClayStory repo")

    history = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {}
    if not isinstance(history, dict):
        raise RuntimeError("Invalid Instagram posting history")
    created = 0
    with tempfile.TemporaryDirectory(prefix="claystory-instagram-") as folder:
        for story in STORIES:
            if created >= LIMIT:
                break
            key = story["key"]
            url = urljoin(PAGES_BASE, f"videos/{key}-balanced.mp4")
            film = Path(folder) / f"{key}.mp4"
            fingerprint = download_public_video(url, film)
            validation = validate_reel(film)
            unique_key = f"{key}:{fingerprint}"
            if unique_key in history:
                print(f"Already submitted {story['name']}, {fingerprint[:12]}; skipping")
                continue
            print(f"New Instagram Reel: {story['name']} ({validation})")
            if mode == "check":
                created += 1
                continue
            # Resolve channel only when a genuinely new film needs posting.
            channel = instagram_channel()
            post = create_post(channel["id"], url, story["caption"])
            history[unique_key] = {
                "story": key,
                "buffer_post_id": post["id"],
                "channel_id": channel["id"],
                "mode": mode,
                "video_url": url,
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
