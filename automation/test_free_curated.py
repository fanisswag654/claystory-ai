"""Offline free-curated Pūrākau Pixels tests. Never call Edge, OpenAI or Telegram."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prepare_story
import telegram_free_preview
import telegram_webhook


class CuratedScriptTests(unittest.TestCase):
    def test_exactly_four_grounded_original_eight_scene_scripts(self):
        briefs = prepare_story.source_briefs()["topics"]
        self.assertEqual(len(briefs), 4)
        for topic in briefs:
            with self.subTest(topic=topic["id"]):
                scenes = prepare_story.curated_script(topic)
                self.assertEqual(len(scenes), 8)
                self.assertEqual([x["visual"] for x in scenes], topic["visuals"])
                self.assertEqual([x["action"] for x in scenes], topic["actions"])
                for scene in scenes:
                    self.assertTrue(85 <= len(scene["narration"]) <= 360)
                    self.assertLessEqual(len(scene["caption"]), 36)
                self.assertTrue(topic["sources"])

    def test_curated_cli_never_calls_openai_even_with_paid_api_key_available(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "candidate-story.json"
            with patch.object(sys, "argv", [
                "prepare_story.py", "--mode", "curated",
                "--topic", "maui-mahuika-fire", "--output", str(out)
            ]), patch.dict(os.environ, {"OPENAI_API_KEY": "do-not-use-paid-api"}), \
                 patch.object(prepare_story, "generate_script", side_effect=AssertionError(
                     "Paid API must not be contacted in curated mode"
                 )):
                prepare_story.main()
            story = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(story["script_origin"], "checked-in-curated-original")
            self.assertEqual(story["narrator"], "en-GB-RyanNeural")
            self.assertEqual(story["review_status"], "pending-human-approval")
            self.assertEqual(len(story["scenes"]), 8)

    def test_missing_curated_script_must_fail_not_use_fallback_ai(self):
        topic = prepare_story.source_briefs()["topics"][0]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text('{"version":1,"scripts":{}}', encoding="utf-8")
            with patch.object(prepare_story, "CURATED_SCRIPTS", path), \
                 patch.object(prepare_story, "generate_script", side_effect=AssertionError):
                with self.assertRaisesRegex(ValueError, "must match"):
                    prepare_story.curated_script(topic)

    def test_free_topic_cannot_be_unknown(self):
        with self.assertRaisesRegex(ValueError, "Unknown curated story topic"):
            prepare_story.next_topic([], "not-a-curated-story")


class FreeWorkflowDependencies(unittest.TestCase):
    def test_requests_installed_before_preview_preflight_import(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/free-curated-purakau.yml"
        ).read_text(encoding="utf-8")
        pip_step = workflow.index(
            "name: Install preflight dependency before importing Telegram preview code"
        )
        pip_command = workflow.index("python -m pip install 'requests>=2.32,<3'")
        preflight = workflow.index(
            "name: Check free-run identity and original curated script BEFORE rendering"
        )
        preview_import = workflow.index("from telegram_free_preview import verified_private_credentials")
        self.assertLess(pip_step, pip_command)
        self.assertLess(pip_command, preflight)
        self.assertLess(preflight, preview_import)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotIn("secrets.OPENAI_API_KEY", workflow)
        self.assertNotIn("secrets.BUFFER_API_KEY", workflow)


class FreePreviewDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.video = base / "purakau-review.mp4"
        self.video.write_bytes(b"original test bytes - no real MP4" * 5_000)
        self.story_path = base / "story.json"
        self.manifest_path = base / "manifest.json"
        topic = prepare_story.source_briefs()["topics"][0]
        self.story = {
            **prepare_story.build_candidate(topic, prepare_story.curated_script(topic)),
            "script_origin": "checked-in-curated-original",
        }
        self.story_path.write_text(json.dumps(self.story, ensure_ascii=False))
        self.manifest = {
            "story_id": topic["id"],
            "title": topic["title"],
            "narrator": "en-GB-RyanNeural",
            "status": "pending-human-approval",
            "sources": topic["sources"],
            "video_file": "purakau-review.mp4",
            "video_sha256": hashlib.sha256(self.video.read_bytes()).hexdigest(),
            "bytes": self.video.stat().st_size,
        }
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False))
        self.credentials = {
            "TELEGRAM_BOT_TOKEN": "1234567890:" + "A" * 40,
            "TELEGRAM_APPROVER_USER_ID": "1234567890",
            "TELEGRAM_REVIEW_CHAT_ID": "1234567890",
        }

    def test_preview_button_namespace_is_disjoint_from_live_publishing(self):
        self.assertEqual(
            telegram_free_preview.TEST_PREVIEW_MARKER,
            telegram_webhook.TEST_PREVIEW_MARKER,
        )
        callbacks = telegram_free_preview.preview_keyboard()["inline_keyboard"][0]
        self.assertEqual(len(callbacks), 2)
        for button in callbacks:
            tag = button["callback_data"]
            self.assertIn(tag, telegram_webhook.TEST_PREVIEW_ACTIONS)
            self.assertNotIn("auto-review-", tag)
            self.assertTrue(tag.startswith("test_preview:"))
            self.assertIn("PREVIEW", button["text"].upper())
        self.assertIn("NO POST", callbacks[0]["text"])

    def test_original_free_video_integrity(self):
        metadata = telegram_free_preview.verify_curated_film(
            self.video, self.story_path, self.manifest_path
        )
        self.assertEqual(metadata["key"], "maui-mahuika-fire")
        self.assertEqual(metadata["sha256"], self.manifest["video_sha256"])

    def test_tampered_video_refused_before_telegram_send(self):
        self.video.write_bytes(self.video.read_bytes() + b"evil")
        with patch.object(telegram_free_preview.requests, "post") as send:
            with self.assertRaisesRegex(ValueError, "differs"):
                telegram_free_preview.send_free_preview(
                    self.video, self.story_path, self.manifest_path, self.credentials
                )
            send.assert_not_called()

    def test_noncurated_script_refused_before_telegram_send(self):
        self.story["scenes"][0]["narration"] = "An altered script must not send"
        self.story_path.write_text(json.dumps(self.story, ensure_ascii=False))
        with patch.object(telegram_free_preview.requests, "post") as send:
            with self.assertRaisesRegex(ValueError, "exactly match"):
                telegram_free_preview.send_free_preview(
                    self.video, self.story_path, self.manifest_path, self.credentials
                )
            send.assert_not_called()

    def test_wrong_chat_is_not_sent_any_video(self):
        bad = {**self.credentials, "TELEGRAM_REVIEW_CHAT_ID": "1234567891"}
        with patch.object(telegram_free_preview.requests, "post") as send:
            with self.assertRaisesRegex(RuntimeError, "another user"):
                telegram_free_preview.send_free_preview(
                    self.video, self.story_path, self.manifest_path, bad
                )
            send.assert_not_called()

    def test_safe_telegram_delivery_contains_test_only_buttons(self):
        fake_result = {
            "ok": True,
            "result": {
                "chat": {"id": 1234567890, "type": "private"},
                "message_id": 678,
                "video": {"file_id": "fake-test-video"},
            }
        }
        class Response:
            status_code = 200
            def json(self):
                return fake_result
        with patch.object(telegram_free_preview.requests, "post", return_value=Response()) as send:
            outcome = telegram_free_preview.send_free_preview(
                self.video, self.story_path, self.manifest_path, self.credentials
            )
        self.assertFalse(outcome["instagram_published"])
        self.assertEqual(outcome["status"], "free_preview_delivered_only")
        self.assertIn(telegram_free_preview.TEST_PREVIEW_MARKER, send.call_args.kwargs["data"]["caption"])
        self.assertIn("NO POST", json.dumps(send.call_args.kwargs["data"]))
        markup = json.loads(send.call_args.kwargs["data"]["reply_markup"])
        self.assertEqual(markup, telegram_free_preview.preview_keyboard())


if __name__ == "__main__":
    unittest.main()
