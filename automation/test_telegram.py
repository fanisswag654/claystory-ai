"""Offline Telegram integration checks: no network, no real posts, no bot token.

Both server and GitHub verify the exact user/chat and SHA-pinned
Approve/Reject callback before Buffer could be reached.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approval_webhook
import telegram_send
# Patch the same module that Flask registered on its Blueprint. Importing
# telegram_webhook at the top level would construct a SECOND module object.
from automation import telegram_webhook
import approve_publish_telegram

USER = "123456789"
CHAT = "123456789"
WEBHOOK_SECRET = "A-strong-valid-Telegram-Webhook-Secret_123"
SIGN_KEY = "genuine-independent-review-signing-key-example-123456"


def fake_proposal(sha: str) -> dict:
    tag = "auto-review-maui-mahuika-fire-" + sha[:12]
    return {
        "proposal_id": tag,
        "video_sha256": sha,
        "video_url": f"https://github.com/fanisswag654/claystory-ai/releases/download/{tag}/purakau-review.mp4",
        "title": "Māui and Mahuika: The Secret of Fire",
        "story_id": "maui-mahuika-fire",
        "status": "pending",
        "narrator": "en-GB-RyanNeural",
        "sources": [{"url": "https://teara.govt.nz/en/1966/maui-legends-of/page-5"}],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def button_payload(proposal: dict, action="approve") -> dict:
    return {
        "update_id": 555,
        "callback_query": {
            "id": "572023659838662",
            "from": {"id": int(USER), "is_bot": False},
            "message": {
                "message_id": 101,
                "date": 1700000000,
                "chat": {"id": int(CHAT), "type": "private"},
                "video": {"file_id": "BAACAgQAAxkBA", "file_size": 500000},
                "caption": "Review ID: " + proposal["proposal_id"],
            },
            "data": action + ":" + proposal["proposal_id"],
        }
    }


class TelegramSender(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.file = Path(self.t.name) / "purakau-review.mp4"
        self.file.write_bytes(b"original-frames-and-narration" * 7500)
        self.sha = hashlib.sha256(self.file.read_bytes()).hexdigest()
        self.proposal = fake_proposal(self.sha)

    def test_actual_mp4_and_approval_keyboard(self):
        telegram_send.verify_review(self.proposal, self.file)
        payload = telegram_send.message_payload(self.proposal, CHAT)
        keys = json.loads(payload["reply_markup"])["inline_keyboard"][0]
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0]["callback_data"], "approve:" + self.proposal["proposal_id"])
        self.assertEqual(keys[1]["callback_data"], "reject:" + self.proposal["proposal_id"])
        self.assertTrue(all(len(k["callback_data"].encode()) <= 64 for k in keys))
        self.assertIn("No reply", payload["caption"])

    def test_modified_video_never_sent(self):
        self.file.write_bytes(self.file.read_bytes() + b"-tampered")
        with self.assertRaisesRegex(ValueError, "differ"):
            telegram_send.verify_review(self.proposal, self.file)

    def test_no_bot_token_refuses_delivery(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_REVIEW_CHAT_ID": CHAT}):
            with self.assertRaisesRegex(RuntimeError, "missing"):
                telegram_send.send_video(self.proposal, self.file)

    def test_correct_user_receives_original_video(self):
        mock_reply = MagicMock()
        mock_reply.status_code = 200
        mock_reply.json.return_value = {
            "ok": True,
            "result": {"message_id": 100, "chat": {"id": int(CHAT)},
                       "video": {"file_id": "BAACAgQABotExample"}},
        }
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "1234567890:" + "a" * 35,
            "TELEGRAM_REVIEW_CHAT_ID": CHAT,
        }), patch.object(telegram_send.requests, "post", return_value=mock_reply) as api:
            result = telegram_send.send_video(self.proposal, self.file)
        self.assertEqual(result["status"], "delivered_for_review_not_approved")
        self.assertEqual(result["telegram_message_id"], 100)
        self.assertEqual(api.call_args.kwargs["files"]["video"][0], "purakau-review.mp4")


class TelegramWebhook(unittest.TestCase):
    def setUp(self):
        self.sha = hashlib.sha256(b"sample original MP4").hexdigest()
        self.proposal = fake_proposal(self.sha)
        self.payload = button_payload(self.proposal)

    def test_invalid_render_bot_token_does_not_make_network_request(self):
        with patch.object(telegram_webhook.urllib.request, "urlopen") as call:
            with self.assertRaisesRegex(RuntimeError, "missing or invalid"):
                telegram_webhook.send_onboarding_reply(
                    {"user_id": USER, "chat_id": CHAT},
                    "Paste the same token BotFather gave you, which you saved in GitHub.",
                )
        call.assert_not_called()

    def test_start_onboarding_replies_to_private_caller(self):
        data = {
            "message": {
                "text": "/start",
                "chat": {"id": int(CHAT), "type": "private"},
                "from": {"id": int(USER)},
            }
        }
        self.assertEqual(
            telegram_webhook.identify_private_chat(data),
            {"chat_id": CHAT, "user_id": USER},
        )
        with patch.dict(os.environ, {
            "TELEGRAM_WEBHOOK_SECRET": WEBHOOK_SECRET,
            "TELEGRAM_BOT_TOKEN": "1234567890:" + "a" * 40,
        }), patch.object(telegram_webhook, "send_onboarding_reply") as send:
            reply = approval_webhook.app.test_client().post(
                "/webhook/telegram", json=data,
                headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
            )
        self.assertEqual(reply.status_code, 200, reply.get_json())
        send.assert_called_once()

    def test_valid_header_only(self):
        self.assertTrue(telegram_webhook.verify_secret_header(WEBHOOK_SECRET, WEBHOOK_SECRET))
        self.assertFalse(telegram_webhook.verify_secret_header("incorrect", WEBHOOK_SECRET))
        self.assertFalse(telegram_webhook.verify_secret_header("", WEBHOOK_SECRET))
        self.assertFalse(telegram_webhook.verify_secret_header("weak", "weak"))

    def test_exclusive_private_reviewer_and_video_caption(self):
        action = telegram_webhook.parse_callback(self.payload, USER, CHAT)
        self.assertEqual(action["decision"], "approved")
        self.assertIsNone(telegram_webhook.parse_callback(self.payload, "99999999", CHAT))
        self.assertIsNone(telegram_webhook.parse_callback(self.payload, USER, "99999999"))
        other = json.loads(json.dumps(self.payload))
        other["callback_query"]["message"]["chat"]["type"] = "group"
        self.assertIsNone(telegram_webhook.parse_callback(other, USER, CHAT))
        other = json.loads(json.dumps(self.payload))
        other["callback_query"]["message"].pop("video")
        self.assertIsNone(telegram_webhook.parse_callback(other, USER, CHAT))
        other = json.loads(json.dumps(self.payload))
        other["callback_query"]["message"]["caption"] = "Different review ID"
        self.assertIsNone(telegram_webhook.parse_callback(other, USER, CHAT))

    def test_signed_callback_matches_independent_git_verifier(self):
        action = telegram_webhook.parse_callback(self.payload, USER, CHAT)
        signed = telegram_webhook.sign_review(action, self.proposal, SIGN_KEY, now=1700000000)
        approve_publish_telegram.verify_telegram_approval(
            signed, self.proposal, SIGN_KEY, USER, CHAT, now=1700000001
        )
        tampered = {**signed, "decision": "rejected"}
        with self.assertRaisesRegex(ValueError, "cryptographic"):
            approve_publish_telegram.verify_telegram_approval(
                tampered, self.proposal, SIGN_KEY, USER, CHAT, now=1700000001
            )

    def test_wrong_user_chat_and_expired_signature_fail_in_git(self):
        action = telegram_webhook.parse_callback(self.payload, USER, CHAT)
        signed = telegram_webhook.sign_review(action, self.proposal, SIGN_KEY, now=1700000000)
        with self.assertRaisesRegex(ValueError, "wrong user"):
            approve_publish_telegram.verify_telegram_approval(
                signed, self.proposal, SIGN_KEY, "456789011", CHAT, now=1700000001
            )
        with self.assertRaisesRegex(ValueError, "expired"):
            approve_publish_telegram.verify_telegram_approval(
                signed, self.proposal, SIGN_KEY, USER, CHAT, now=1700000602
            )

    def test_webhook_rejects_unauthenticated_external_posts(self):
        client = approval_webhook.app.test_client()
        with patch.dict(os.environ, {"TELEGRAM_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            reply = client.post("/webhook/telegram", json=self.payload)
        self.assertEqual(reply.status_code, 403)

    def test_webhook_sends_signed_dispatch_not_instagram(self):
        client = approval_webhook.app.test_client()
        with patch.dict(os.environ, {
            "TELEGRAM_WEBHOOK_SECRET": WEBHOOK_SECRET,
            "TELEGRAM_APPROVER_USER_ID": USER,
            "TELEGRAM_REVIEW_CHAT_ID": CHAT,
            "PURAKAU_APPROVAL_SIGNING_KEY": SIGN_KEY,
            "GITHUB_REVIEW_DISPATCH_TOKEN": "test-token-no-network",
            "TELEGRAM_BOT_TOKEN": "",
        }), patch.object(telegram_webhook, "pending_proposal", return_value=self.proposal), \
             patch.object(telegram_webhook, "dispatch_decision") as dispatch:
            reply = client.post("/webhook/telegram", json=self.payload, headers={
                "X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET,
            })
        self.assertEqual(reply.status_code, 200, reply.get_json())
        receipt = dispatch.call_args.args[0]
        self.assertEqual(receipt["platform"], "telegram")
        self.assertEqual(receipt["decision"], "approved")


class InstagramApprovalIsAlwaysSeparate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.video = self.dir / "purakau-review.mp4"
        self.video.write_bytes(b"exact reviewed MP4" * 7200)
        self.sha = hashlib.sha256(self.video.read_bytes()).hexdigest()
        self.proposal = fake_proposal(self.sha)
        self.receipt = telegram_webhook.sign_review(
            telegram_webhook.parse_callback(
                button_payload(self.proposal, "reject"), USER, CHAT
            ), self.proposal, SIGN_KEY,
        )

    def test_reject_never_contacts_buffer(self):
        with patch.object(approve_publish_telegram, "REVIEW", self.dir), \
             patch.dict(os.environ, {
                 "PURAKAU_APPROVAL_SIGNING_KEY": SIGN_KEY,
                 "TELEGRAM_APPROVER_USER_ID": USER,
                 "TELEGRAM_REVIEW_CHAT_ID": CHAT,
             }), patch.object(approve_publish_telegram, "submit_approved") as publisher:
            result = approve_publish_telegram.process_telegram(
                self.receipt, self.proposal, {}
            )
        publisher.assert_not_called()
        self.assertEqual(result["review:" + self.proposal["proposal_id"]]["decision"], "rejected")

    def test_approval_disallowed_after_rejection(self):
        signed = telegram_webhook.sign_review(
            telegram_webhook.parse_callback(button_payload(self.proposal), USER, CHAT),
            self.proposal, SIGN_KEY,
        )
        history = {"review:" + self.proposal["proposal_id"]: {"decision": "rejected"}}
        with patch.object(approve_publish_telegram, "REVIEW", self.dir), \
             patch.dict(os.environ, {
                 "PURAKAU_APPROVAL_SIGNING_KEY": SIGN_KEY,
                 "TELEGRAM_APPROVER_USER_ID": USER,
                 "TELEGRAM_REVIEW_CHAT_ID": CHAT,
             }), patch.object(approve_publish_telegram, "submit_approved") as publisher:
            with self.assertRaisesRegex(RuntimeError, "opposite final decision"):
                approve_publish_telegram.process_telegram(
                    signed, self.proposal, history
                )
        publisher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
