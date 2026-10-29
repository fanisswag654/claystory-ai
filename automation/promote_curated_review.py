#!/usr/bin/env python3
"""One-time promotion of the EXACT previously previewed Māui and Mahuika MP4.

This never renders/generates or calls any OpenAI API. It only checks a pinned
GitHub Actions artifact's bytes, manifests and original source script, then
creates a review proposal for authenticated Telegram owner approval.

The Instagram decision is NOT made here. A second GitHub workflow checks the
owner's HMAC-signed Telegram click, original GitHub Release SHA, review ledger
and the exact @purakaupixel Buffer channel before posting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "automation"))
from prepare_story import source_briefs
from telegram_free_preview import verify_curated_film
from finalize_proposal import build_proposal
from telegram_send import verify_review

SOURCE_RUN_ID = 40819103075
SOURCE_ARTIFACT_NAME = "purakau-free-curated-preview"
SOURCE_STORY_ID = "maui-mahuika-fire"
SOURCE_SHA256 = "ddb8318a9296de8418643294e82dec8d7f52056278185bd470ceb3ec72ed107c"
PROPOSAL_ID = f"auto-review-{SOURCE_STORY_ID}-{SOURCE_SHA256[:12]}"
REQUEST_PATH = (
    ROOT / "automation" / "post_requests"
    / f"maui-mahuika-{SOURCE_SHA256[:12]}.json"
)


def verify_operator_request(request_file: Path = REQUEST_PATH) -> dict:
    """Fail closed if a push is not the exact owner-authorized one-time task."""
    request = json.loads(request_file.read_text(encoding="utf-8"))
    expected = {
        "workflow": "promote_existing_curated_preview_for_signed_telegram_approval",
        "source_run_id": SOURCE_RUN_ID,
        "artifact_name": SOURCE_ARTIFACT_NAME,
        "story_id": SOURCE_STORY_ID,
        "original_mp4_sha256": SOURCE_SHA256,
        "target_instagram": "@purakaupixel",
        "review_required": True,
        "publish_before_telegram_approval": False,
    }
    if request != expected:
        raise ValueError("Only the exact consented, SHA-locked original review request is allowed")
    return request


def prepare_review_from_original_artifact(folder: Path) -> dict:
    """Load and cryptographically verify the real MP4 and editorial metadata."""
    video = folder / "purakau-review.mp4"
    storyboard = folder / "story.json"
    manifest_path = folder / "manifest.json"
    if not video.exists() or not storyboard.exists() or not manifest_path.exists():
        raise ValueError("The exact existing curated preview archive is incomplete")
    metadata = verify_curated_film(video, storyboard, manifest_path)
    if metadata["key"] != SOURCE_STORY_ID or metadata["sha256"] != SOURCE_SHA256:
        raise ValueError("The downloaded artifact was not the user-reviewed original MP4")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("video_sha256") != SOURCE_SHA256:
        raise ValueError("Original film SHA in its source manifest does not match")
    if manifest.get("story_id") != SOURCE_STORY_ID:
        raise ValueError("Unexpected source story was downloaded")
    proposal = build_proposal(manifest)
    if proposal["proposal_id"] != PROPOSAL_ID:
        raise ValueError("The source MP4 does not produce the expected immutable review release tag")
    verify_review(proposal, video)
    return proposal


def create_proposal(folder: Path) -> dict:
    verify_operator_request()
    proposal = prepare_review_from_original_artifact(folder)
    output = folder / "proposal.json"
    if output.exists():
        raise RuntimeError("Refusing to overwrite an existing Telegram review proposal")
    output.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Provenance: existing successful free run", SOURCE_RUN_ID)
    print("Original reviewed MP4 SHA-256:", SOURCE_SHA256)
    print("Pending Telegram review release:", PROPOSAL_ID)
    print("This has NOT published anything to Instagram.")
    return proposal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--verify-request-only", action="store_true")
    args = parser.parse_args()
    if args.verify_request_only:
        verify_operator_request()
        print("Owner's one-time request is for exactly the pinned pre-existing video.")
        return
    create_proposal(args.artifact_dir)


if __name__ == "__main__":
    main()
