"""Publish the already-reviewed Māui and the Great Fish Instagram draft now.

Does not create a new post. Moves one existing Buffer draft to shareNow,
and records the action to prevent the scheduled job reposting it.
"""
import json
from pathlib import Path
import sys

from instagram_reels import buffer_api, instagram_channel

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
        " }) { id channelId status shareMode } }"
    )["post"]
    if not result or result.get("id") != post_id or result.get("channelId") != channel["id"]:
        raise RuntimeError("Could not verify the approved draft and its Instagram channel")

    current_status = str(result.get("status") or "").lower()
    print("Existing approved Buffer post status:", current_status)
    if current_status in {"sent", "published"}:
        print("Already posted; recording to prevent duplicates")
        outcome = result
    elif current_status not in {"draft"}:
        raise RuntimeError(
            f"Expected an unsent approved draft, got {current_status}; "
            "stopping rather than posting a duplicate"
        )
    else:
        mutation = (
            "mutation { editPost(input: {"
            + " id: " + json.dumps(post_id)
            + " mode: shareNow schedulingType: automatic saveToDraft: false"
            + " }) {"
            + " ... on PostActionSuccess { post { id status shareMode dueAt } }"
            + " ... on MutationError { message }"
            + " } }"
        )
        payload = buffer_api(mutation)["editPost"]
        outcome = payload.get("post")
        if not outcome or outcome.get("id") != post_id:
            raise RuntimeError("Buffer rejected Publish Now: " + str(payload))
        if str(outcome.get("status") or "").lower() == "draft":
            raise RuntimeError("Buffer left approved post in Drafts; publish not accepted")
        print("Buffer Publish Now accepted:", outcome)

    history[queue_key] = {
        "story": STORY,
        "source_fingerprint": fingerprint,
        "buffer_post_id": post_id,
        "channel_id": channel["id"],
        "mode": "queue",
        "share_mode": "shareNow",
        "video_url": draft.get("video_url"),
        "buffer_status": outcome.get("status"),
    }
    tmp = HISTORY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(HISTORY_PATH)
    print("Recorded approved Publish Now action, no new post was created")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Approved Instagram publication could not complete:", error, file=sys.stderr)
        raise
