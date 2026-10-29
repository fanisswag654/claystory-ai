"""Prevent Telegram preview confirmations from flooding the owner's chat.

Regresses 2026-10-29: expired answerCallbackQuery caused an HTTP 503 after
sendMessage had already succeeded. Telegram retried the same update,
generating duplicate confirmation messages indefinitely.
"""
from __future__ import annotations

import io
import json
import os
import urllib.error
import unittest
from unittest.mock import patch

from automation import approval_webhook, telegram_webhook

USER = "1234567890"
SECRET = "test-very-long-telegram-secret-A_987654321"
BOT_TOKEN = "1234567890:" + "a" * 40


def preview_update(action: str = "approve", tag: str = "free") -> dict:
    return {
        "update_id": 56789,
        "callback_query": {
            "id": "98765432109876543",
            "from": {"id": int(USER), "is_bot": False},
            "message": {
                "message_id": 27,
                "chat": {"id": int(USER), "type": "private"},
                "video": {"file_id": "mocked-video"},
                "caption": (
                    "🧪 " + telegram_webhook.TEST_PREVIEW_MARKER +
                    "\n\nMāui and Mahuika: The Secret of Fire"
                ),
            },
            "data": f"test_preview:{action}:{tag}",
        },
    }


class TelegramPreviewNoFloodTests(unittest.TestCase):
    def test_preview_edits_existing_video_instead_of_sending_chat_message(self):
        review = telegram_webhook.parse_preview_test(
            preview_update(), USER, USER
        )
        self.assertEqual(review["message_id"], 27)
        self.assertEqual(review["action"], "approve")
        self.assertIn("Mahuika", review["caption"])
        success_reply = io.BytesIO(b'{"ok":true,"result":{"message_id":27}}')
        with patch.object(
            telegram_webhook.urllib.request, "urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value = success_reply
            telegram_webhook.acknowledge_preview_test(review, BOT_TOKEN)
        self.assertEqual(urlopen.call_count, 1)
        request = urlopen.call_args.args[0]
        self.assertIn("/editMessageCaption", request.full_url)
        self.assertNotIn("/sendMessage", request.full_url)
        body = json.loads(request.data)
        self.assertEqual(body["message_id"], 27)
        self.assertEqual(body["chat_id"], USER)
        self.assertIn("Mahuika", body["caption"])
        self.assertIn("PREVIEW APPROVED", body["caption"])
        self.assertIn("NOT PUBLISHED", body["caption"])
        self.assertEqual(body["reply_markup"], {"inline_keyboard": []})
        self.assertLessEqual(len(body["caption"]), 1024)

    def test_expired_button_does_not_make_webhook_retry_even_if_edit_already_done(self):
        # Both Telegram endpoints can return 400 if Render had to wake
        # up after Telegram's callback query expired.
        expired = urllib.error.HTTPError(
            "https://api.telegram.org", 400, "query is too old",
            None, io.BytesIO(b"{}")
        )
        data = preview_update()
        with patch.dict(os.environ, {
            "TELEGRAM_WEBHOOK_SECRET": SECRET,
            "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
            "TELEGRAM_APPROVER_USER_ID": USER,
            "TELEGRAM_REVIEW_CHAT_ID": USER,
        }), patch.object(
            telegram_webhook, "acknowledge_preview_test",
            side_effect=expired,
        ) as edit, patch.object(
            telegram_webhook, "answer_callback", side_effect=expired
        ) as toast, patch.object(
            telegram_webhook, "dispatch_decision"
        ) as publish, patch.object(
            telegram_webhook, "dispatch_bridge_probe"
        ) as bridge:
            with approval_webhook.app.test_client() as client:
                response = client.post(
                    "/webhook/telegram", json=data,
                    headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
                )
                # A redelivered identical update also gets HTTP 200.
                repeated = client.post(
                    "/webhook/telegram", json=data,
                    headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
                )
        for result in (response, repeated):
            self.assertEqual(result.status_code, 200, result.get_json())
            self.assertFalse(result.get_json()["instagram_publication"])
        self.assertEqual(edit.call_count, 2)
        self.assertEqual(toast.call_count, 2)
        publish.assert_not_called()
        bridge.assert_not_called()

    def test_telegram_unreachable_cannot_cause_infinite_preview_retry(self):
        with patch.dict(os.environ, {
            "TELEGRAM_WEBHOOK_SECRET": SECRET,
            "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
            "TELEGRAM_APPROVER_USER_ID": USER,
            "TELEGRAM_REVIEW_CHAT_ID": USER,
        }), patch.object(
            telegram_webhook, "acknowledge_preview_test",
            side_effect=urllib.error.URLError("offline"),
        ), patch.object(
            telegram_webhook, "answer_callback",
            side_effect=urllib.error.URLError("offline"),
        ):
            response = approval_webhook.app.test_client().post(
                "/webhook/telegram", json=preview_update("reject"),
                headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
            )
        self.assertEqual(response.status_code, 200, response.get_json())

    def test_duplicate_video_caption_does_not_append_status_more_than_once(self):
        original = preview_update()
        original["callback_query"]["message"]["caption"] += (
            "\n\n✅ PREVIEW APPROVED — NOT PUBLISHED."
        )
        test = telegram_webhook.parse_preview_test(original, USER, USER)
        with patch.object(telegram_webhook.urllib.request, "urlopen") as caller:
            caller.return_value.__enter__.return_value = io.BytesIO(b'{"ok":true}')
            telegram_webhook.acknowledge_preview_test(test, BOT_TOKEN)
        edited = json.loads(caller.call_args.args[0].data)
        self.assertEqual(edited["caption"].count("PREVIEW APPROVED"), 1)

    def test_real_publishing_callbacks_remain_separate(self):
        free = preview_update()
        self.assertIsNone(telegram_webhook.parse_callback(free, USER, USER))
        self.assertEqual(
            telegram_webhook.parse_preview_test(free, USER, USER)["action"],
            "approve",
        )


if __name__ == "__main__":
    unittest.main()
