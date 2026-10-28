"""Publish the already-reviewed Māui and the Great Fish Instagram draft now.

Does not create a new post. Moves one existing Buffer draft to shareNow,
and records the action to prevent the scheduled job reposting it.
"""
import json
from pathlib import Path
import sys

from instagram_reels import STORIES, buffer_api, edit_instagram_reel, instagram_channel, verify_public_release

HISTORY_PATH = Path("instagram-post-history.json")
APPROVALS_PATH = Path("config/instagram-approved.json")
STORY = "fish-nz"


def main():
    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    approved = json.loads(APPROVALS_PATH.read_text(encoding="utf-8"))
    permitted = approved.get("approved_reels", {}).get(STORY, [])
    if len(permitted) != 1:
        raise RuntimeError("Exactly one reviewed Great Fish version must be approved")

    fingerprint = permitted[0]
    draft_key = f"{STORY}:{fingerprint}:draft"
    queue_key = f"{STORY}:{fingerprint}:queue"

    if queue_key in history:
        print("Already submitted the reviewed Great Fish post; no duplicate action")
        return
    draft = history.get(draft_key)
    if not draft:
        raise RuntimeError("No matching approved Great Fish draft in posting history")

    channel = instagram_channel()
    if draft.get("channel_id") != channel["id"]:
        raise RuntimeError("The approved draft does not belong to @purakaupixel")

    post_id = draft["buffer_post_id"]
    result = buffer_api(
        "query { post(input: { id: " + json.dumps(post_id) +
        " }) { id channelId status shareMode text assets { type source } } }"
    )["post"]
    if not result or result.get("id") != post_id or result.get("channelId") != channel["id"]:
        raise RuntimeError("Could not verify the approved draft and its Instagram channel")

    current_status = str(result.get("status") or "").lower()
    print("Existing approved Buffer post status:", current_status)
    video_url = draft.get("video_url", "")
    expected_tag = f"/instagram-{STORY}-{fingerprint[:16]}/"
    if expected_tag not in video_url:
        raise RuntimeError("Reviewed draft's video URL does not match the approved film")
    original_caption = next(s["caption"] for s in STORIES if s["key"] == STORY)
    caption = result.get("text") or original_caption
    # Preserve any caption edits the account owner made to the reviewed Buffer draft.
    if current_status in {"sent", "scheduled", "sending"}:
        print("Approved post was already submitted to Buffer; no second publish request")
        outcome = result
    elif current_status != "draft":
        raise RuntimeError(
            f"Expected a draft or already-submitted approved post, got {current_status}; "
            "stopping rather than risking a duplicate"
        )
    else:
        # The previous implementation submitted only mode/saveToDraft and Buffer
        # rejected it because its edit validator lacked text, media and Reel type.
        # Validate the exact publicly hosted reviewed film before editing the post.
        verify_public_release(video_url)
        outcome = edit_instagram_reel(post_id, video_url, caption, "shareNow")
        print("Buffer accepted Publish Now for the existing Reel:", outcome)

    history[queue_key] = {
        "story": STORY,
        "source_fingerprint": fingerprint,
        "buffer_post_id": post_id,
        "channel_id": channel["id"],
        "mode": "queue",
        "share_mode": "shareNow",
        "video_url": video_url,
        "buffer_status": outcome.get("status"),
    }
    tmp = HISTORY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(HISTORY_PATH)
    print("Recorded approved Buffer submission, no duplicate was created; confirm final Instagram status separately")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Approved Instagram publication could not complete:", error, file=sys.stderr)
        raise
