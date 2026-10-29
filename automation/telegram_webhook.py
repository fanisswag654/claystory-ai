#!/usr/bin/env python3
"""Authenticated Telegram review buttons for the ClayStory Render web service.

No payment, Meta business account or personal-number registration required.
Only a trusted private Telegram user/chat can approve a specific MP4.
A webhook never posts to Instagram: it signs a request for a separate
GitHub workflow to verify the original video and enforce duplicate safety.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request

bot = Blueprint("telegram_review", __name__)
REPO = "fanisswag654/claystory-ai"
TAG = re.compile(r"^auto-review-[a-z0-9-]+-[a-f0-9]{12}$")
CALLBACK_ID = re.compile(r"^[A-Za-z0-9_:-]{7,128}$")
DECISION = {"approve": "approved", "reject": "rejected"}


def verify_secret_header(given: str, expected: str) -> bool:
    """Compare Telegram's X-Telegram-Bot-Api-Secret-Token in constant time."""
    if not expected or len(expected) < 16 or not given:
        return False
    return hmac.compare_digest(expected.encode("utf-8"), given.encode("utf-8"))


def parse_callback(payload: dict, user_id: str, chat_id: str) -> dict | None:
    """Reject all group messages, untrusted users and button-free replies."""
    if not user_id or not chat_id:
        return None
    query = payload.get("callback_query")
    if not isinstance(query, dict):
        return None
    sender = query.get("from", {})
    message = query.get("message", {})
    chat = message.get("chat", {}) if isinstance(message, dict) else {}
    if (
        str(sender.get("id", "")) != user_id
        or str(chat.get("id", "")) != chat_id
        or chat.get("type") != "private"
    ):
        return None
    if not message.get("video") or not message.get("message_id"):
        return None
    value = query.get("data", "")
    if not isinstance(value, str) or ":" not in value or len(value.encode("utf-8")) > 64:
        return None
    action, tag = value.split(":", 1)
    if action not in DECISION or not TAG.fullmatch(tag):
        return None
    if tag not in (message.get("caption") or ""):
        # A forwarded or unrelated message can never authorize a new story.
        return None
    callback_id = str(query.get("id", ""))
    if not CALLBACK_ID.fullmatch(callback_id):
        return None
    return {
        "proposal_id": tag,
        "decision": DECISION[action],
        "telegram_callback_id": callback_id,
        "telegram_user_id": user_id,
        "telegram_chat_id": chat_id,
        "telegram_message_id": message["message_id"],
    }


def pending_proposal(tag: str) -> dict:
    if not TAG.fullmatch(tag):
        raise ValueError("Malformed reviewed video tag")
    url = f"https://github.com/{REPO}/releases/download/{tag}/proposal.json"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "ClayStory-TelegramReview/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as reply:
        info = json.load(reply)
    sha = info.get("video_sha256", "")
    expected_url = (
        f"https://github.com/{REPO}/releases/download/{tag}/purakau-review.mp4"
    )
    if (
        info.get("proposal_id") != tag
        or info.get("status") != "pending"
        or info.get("video_url") != expected_url
        or not re.fullmatch(r"[0-9a-f]{64}", sha)
        or not tag.endswith(sha[:12])
    ):
        raise ValueError("Original immutable proposal mismatch")
    return info


def signature_content(review: dict, sha: str, timestamp: int) -> bytes:
    return "|".join((
        "telegram-v1",
        review["proposal_id"],
        review["decision"],
        review["telegram_callback_id"],
        review["telegram_user_id"],
        review["telegram_chat_id"],
        sha,
        str(timestamp),
    )).encode("utf-8")


def sign_review(review: dict, proposal: dict, secret: str, now: int | None = None) -> dict:
    if len(secret) < 32:
        raise ValueError("Missing sufficiently strong approval signing secret")
    when = int(time.time()) if now is None else int(now)
    sha = proposal["video_sha256"]
    digest = hmac.new(
        secret.encode("utf-8"), signature_content(review, sha, when),
        hashlib.sha256,
    ).hexdigest()
    return {
        **review,
        "platform": "telegram",
        "video_sha256": sha,
        "issued_at": when,
        "signature": digest,
    }


def dispatch_decision(signed: dict, token: str) -> None:
    if not token:
        raise RuntimeError("GitHub dispatch token not configured")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/dispatches",
        method="POST",
        data=json.dumps({
            "event_type": "purakau_telegram_decision", "client_payload": signed,
        }).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "ClayStory-TelegramReview/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status not in (200, 201, 202, 204):
            raise RuntimeError("GitHub refused the signed review dispatch")


def answer_callback(callback_id: str, bot_token: str, explanation: str) -> None:
    if not bot_token:
        return
    # Inform the reviewer that the decision was RECEIVED, not that Instagram
    # has finished publishing. The GitHub workflow still independently checks it.
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
        data=json.dumps({
            "callback_query_id": callback_id,
            "text": explanation[:190],
            "show_alert": False,
        }).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=12):
        pass


def identify_private_chat(update: dict) -> dict | None:
    """BotFather onboarding: /start tells each user their own IDs privately.

    A different user may learn their OWN Telegram numeric ID, but can never
    approve a film because the webhook/Actions enforce the configured IDs.
    """
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat", {})
    sender = message.get("from", {})
    words = str(message.get("text") or "").split()
    command = words[0].split("@")[0] if words else ""
    if (
        command not in ("/start", "/id")
        or chat.get("type") != "private"
        or not str(chat.get("id", "")).lstrip("-").isdigit()
        or not str(sender.get("id", "")).isdigit()
    ):
        return None
    return {"chat_id": str(chat["id"]), "user_id": str(sender["id"])}


def send_onboarding_reply(identity: dict, token: str) -> None:
    """Use HTTPS Telegram Bot API to respond ONLY within the caller's chat."""
    # Fail before constructing an HTTP URL: a pasted instruction rather
    # than a BotFather token must never appear in an exception or server log.
    if not re.fullmatch(r"[0-9]{5,16}:[A-Za-z0-9_-]{25,80}", token):
        raise RuntimeError("Render TELEGRAM_BOT_TOKEN is missing or invalid; use actual BotFather token")
    body = {
        "chat_id": identity["chat_id"],
        "text": (
            "🌿 Pūrākau Pixels review bot is connected!\n\n"
            f"Your Telegram user ID: {identity['user_id']}\n"
            f"Your private chat ID: {identity['chat_id']}\n\n"
            "Store these numbers in the private Telegram settings for your "
            "ClayStory automation. Never share your BotFather token or paste "
            "that token into chat.\n\n"
            "New films will arrive with Approve and Reject buttons once "
            "the owner turns on the review automation."
        ),
    }
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        method="POST", data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        payload = json.load(response)
    if not payload.get("ok"):
        raise RuntimeError("Telegram did not accept onboarding message")


@bot.post("/webhook/telegram")
def telegram_updates():
    if not verify_secret_header(
        request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""),
        os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
    ):
        return jsonify(error="Webhook token verification failed"), 403

    try:
        payload = request.get_json(force=True)
    except (ValueError, TypeError):
        return jsonify(error="Invalid Telegram JSON"), 400
    if not isinstance(payload, dict):
        return jsonify(error="Unexpected Telegram update"), 400

    # Allow the reviewer to discover their numeric private chat/user IDs
    # safely by sending /start to the bot after its webhook is registered.
    identity = identify_private_chat(payload)
    if identity is not None:
        try:
            send_onboarding_reply(identity, os.getenv("TELEGRAM_BOT_TOKEN", ""))
        except (RuntimeError, urllib.error.URLError, OSError):
            return jsonify(error="Bot token not ready to respond to /start"), 503
        return jsonify(onboarding_message_sent=True), 200

    trusted_user = os.getenv("TELEGRAM_APPROVER_USER_ID", "")
    trusted_chat = os.getenv("TELEGRAM_REVIEW_CHAT_ID", "")
    review = parse_callback(payload, trusted_user, trusted_chat)
    if review is None:
        # /start, unsolicited messages or other people's callbacks never
        # invoke the Instagram dispatch.
        return jsonify(ignored=True, reason="Not an authenticated review button"), 200

    if not all(os.getenv(key) for key in (
        "PURAKAU_APPROVAL_SIGNING_KEY", "GITHUB_REVIEW_DISPATCH_TOKEN",
    )):
        return jsonify(error="Review dispatch not fully configured"), 503

    try:
        proposal = pending_proposal(review["proposal_id"])
        signed = sign_review(
            review, proposal, os.getenv("PURAKAU_APPROVAL_SIGNING_KEY", "")
        )
        dispatch_decision(signed, os.getenv("GITHUB_REVIEW_DISPATCH_TOKEN", ""))
    except (ValueError, RuntimeError, urllib.error.URLError, OSError) as exc:
        # Telegram will retry failed webhooks; no approval is implied.
        app_error = type(exc).__name__
        return jsonify(error="Review not accepted", kind=app_error), 503

    try:
        answer_callback(
            review["telegram_callback_id"], os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "Approval sent for verification. Instagram is not yet confirmed."
            if review["decision"] == "approved" else
            "Rejection recorded for verification. This film will not be posted.",
        )
    except (urllib.error.URLError, OSError):
        # GitHub already has the signed event. Telegram may retry; the
        # GitHub ledger prevents duplicate publication.
        pass

    return jsonify(received=True, status="queued_for_independent_verification"), 200
