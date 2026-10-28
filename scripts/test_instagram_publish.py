"""Regression tests for Instagram Reel publishing payloads (no real API calls)."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instagram_reels as ig


class InstagramReelEditTests(unittest.TestCase):
    def setUp(self):
        self.url = (
            f"https://github.com/{ig.REPOSITORY}/releases/download/"
            "instagram-fish-nz-9ad7bd4f7221a9c0/fish-nz-balanced.mp4"
        )
        self.post_id = "approved-great-fish-draft"
        self.caption = "Māui and the Great Fish 🌊"

    def test_immediate_publish_supplies_complete_instagram_reel(self):
        response = {
            "editPost": {"post": {
                "id": self.post_id, "status": "sending", "shareMode": "shareNow",
            }}
        }
        with patch.object(ig, "buffer_api", return_value=response) as api:
            result = ig.edit_instagram_reel(
                self.post_id, self.url, self.caption, "shareNow"
            )
        self.assertEqual(result["id"], self.post_id)
        query = api.call_args.args[0]
        for required in (
            "editPost(input:",
            'id: "approved-great-fish-draft"',
            'text: "Māui and the Great Fish',
            "assets: [{ video: { url:",
            "metadata: { thumbnailOffset: 2000 }",
            "metadata: { instagram: { type: reel",
            "shouldShareToFeed: true",
            "isAiGenerated: true",
            "schedulingType: automatic",
            "mode: shareNow",
            "saveToDraft: false",
        ):
            self.assertIn(required, query)

    def test_queue_edit_has_same_required_fields(self):
        with patch.object(ig, "buffer_api", return_value={
            "editPost": {"post": {"id": self.post_id, "status": "scheduled"}}
        }) as api:
            ig.schedule_existing_draft(self.post_id, self.url, self.caption)
        query = api.call_args.args[0]
        self.assertIn("mode: addToQueue", query)
        self.assertIn("metadata: { instagram: { type: reel", query)
        self.assertIn("assets: [{ video:", query)
        self.assertIn('text: "Māui', query)

    def test_rejects_unapproved_media_host(self):
        with patch.object(ig, "buffer_api") as api:
            with self.assertRaises(ValueError):
                ig.edit_instagram_reel(
                    self.post_id, "https://unknown-host.example/film.mp4",
                    self.caption, "shareNow"
                )
            api.assert_not_called()

    def test_rejects_draft_status_or_api_errors(self):
        for reply in [
            {"editPost": {"post": {"id": self.post_id, "status": "draft"}}},
            {"editPost": {"message": "Invalid post"}},
        ]:
            with self.subTest(reply=reply):
                with patch.object(ig, "buffer_api", return_value=reply):
                    with self.assertRaises(RuntimeError):
                        ig.edit_instagram_reel(
                            self.post_id, self.url, self.caption, "shareNow"
                        )


if __name__ == "__main__":
    unittest.main()
