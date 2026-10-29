#!/usr/bin/env python3
"""Create immutable review metadata for one finished original film.

Executed AFTER a verified 540x960 MP4 exists. An unlisted public GitHub Release
hosts the video; the user's WhatsApp template sends the actual MP4 plus buttons.
The release does NOT authorize Instagram publication.
"""
from __future__ import annotations
from datetime import datetime,timezone
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"automation"/"output"
REPO="fanisswag654/claystory-ai"


def build_proposal(meta: dict) -> dict:
    key=meta["story_id"]
    digest=meta["video_sha256"]
    if not re.fullmatch(r"[a-z0-9-]{5,80}",key):
        raise ValueError("Unexpected candidate source story key")
    if not re.fullmatch(r"[0-9a-f]{64}",digest):
        raise ValueError("Expected full SHA-256 of generated MP4")
    tag=f"auto-review-{key}-{digest[:12]}"
    if not re.fullmatch(r"auto-review-[a-z0-9-]+-[a-f0-9]{12}",tag):
        raise ValueError("Invalid approval release tag")
    source=f"https://github.com/{REPO}/releases/download/{tag}"
    return {
        "proposal_id":tag,
        "story_id":key,
        "title":meta["title"],
        "status":"pending",
        "video_sha256":digest,
        "video_url":source+"/purakau-review.mp4",
        "sources":meta["sources"],
        "narrator":meta["narrator"],
        "bytes":meta["bytes"],
        "created_at":datetime.now(timezone.utc).isoformat(),
        "required_review":["full video","cultural accuracy",
                           "te reo Māori pronunciation","Instagram publication"],
        "publication":"Never without verified WhatsApp approval."
    }


def main():
    metadata=json.loads((OUT/"manifest.json").read_text(encoding="utf-8"))
    video=OUT/"purakau-review.mp4"
    import hashlib
    digest=hashlib.sha256(video.read_bytes()).hexdigest()
    if digest!=metadata["video_sha256"]:
        raise RuntimeError("Animation changed since render, refusing WhatsApp send")
    proposal=build_proposal(metadata)
    (OUT/"proposal.json").write_text(
        json.dumps(proposal,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print(proposal["proposal_id"],flush=True)


if __name__=="__main__":main()
