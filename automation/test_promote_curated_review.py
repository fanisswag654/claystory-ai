"""Tests for SHA-locked reuse of the already-reviewed free Māui MP4.

Never contacts GitHub, Buffer, Telegram, paid AI or Instagram; tests only
operator consent, exact video identity, release tag and nonpublishing steps.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))

import promote_curated_review


class PromoteExistingVideoTests(unittest.TestCase):
    def test_one_exact_original_preview_and_account(self):
        self.assertEqual(promote_curated_review.SOURCE_RUN_ID, 40819103075)
        self.assertEqual(
            promote_curated_review.SOURCE_SHA256,
            "ddb8318a9296de8418643294e82dec8d7f52056278185bd470ceb3ec72ed107c"
        )
        self.assertEqual(promote_curated_review.SOURCE_STORY_ID, "maui-mahuika-fire")
        self.assertEqual(
            promote_curated_review.PROPOSAL_ID,
            "auto-review-maui-mahuika-fire-ddb8318a9296",
        )

    def test_owner_request_is_exact_and_cannot_allow_other_video_or_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            request = Path(temp) / "authorization.json"
            original = {
                "workflow": "promote_existing_curated_preview_for_signed_telegram_approval",
                "source_run_id": 40819103075,
                "artifact_name": "purakau-free-curated-preview",
                "story_id": "maui-mahuika-fire",
                "original_mp4_sha256": promote_curated_review.SOURCE_SHA256,
                "target_instagram": "@purakaupixel",
                "review_required": True,
                "publish_before_telegram_approval": False,
            }
            request.write_text(json.dumps(original), encoding="utf-8")
            self.assertEqual(promote_curated_review.verify_operator_request(request), original)
            for field, changed in [
                ("source_run_id", 1),
                ("original_mp4_sha256", "f"*64),
                ("target_instagram", "@someoneelse"),
                ("review_required", False),
                ("publish_before_telegram_approval", True),
            ]:
                changed_request = {**original, field: changed}
                request.write_text(json.dumps(changed_request), encoding="utf-8")
                with self.subTest(field=field), self.assertRaises(ValueError):
                    promote_curated_review.verify_operator_request(request)

    def test_missing_or_tampered_artifact_is_rejected_before_release(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with self.assertRaisesRegex(ValueError, "incomplete"):
                promote_curated_review.prepare_review_from_original_artifact(folder)
            (folder / "purakau-review.mp4").write_bytes(b"x"*140000)
            (folder / "story.json").write_text("{}")
            (folder / "manifest.json").write_text("{}")
            with self.assertRaises(ValueError):
                promote_curated_review.prepare_review_from_original_artifact(folder)

    def test_exact_review_workflow_has_no_buffer_posting_step(self):
        yml = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/resend-original-for-instagram.yml"
        ).read_text()
        self.assertIn("40819103075", yml)
        self.assertIn(promote_curated_review.SOURCE_SHA256, yml)
        self.assertIn("gh run download", yml)
        self.assertIn("READ-ONLY verify real Buffer Instagram account", yml)
        self.assertIn("python automation/telegram_send.py", yml)
        self.assertNotIn("python automation/approve_publish_telegram.py", yml)
        self.assertNotIn("mode: shareNow", yml)
        self.assertNotIn("OPENAI_API_KEY", yml)

    def test_separate_publishing_workflow_only_accepts_exact_signed_mp4(self):
        yml = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/auto-purakau-decision.yml"
        ).read_text()
        self.assertIn(promote_curated_review.PROPOSAL_ID, yml)
        self.assertIn(promote_curated_review.SOURCE_SHA256, yml)
        self.assertIn("github.event.client_payload.platform == 'telegram'", yml)
        self.assertIn("automation/approve_publish_telegram.py", yml)
        self.assertIn("instagram-publish-history", yml)
        self.assertNotIn("vars.PURAKAU_TELEGRAM_ENABLED == 'true'", yml)


if __name__ == "__main__":
    unittest.main()
