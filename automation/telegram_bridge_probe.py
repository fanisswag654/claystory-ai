#!/usr/bin/env python3
"""Safe signed diagnostic for Telegram -> Render -> GitHub.

A /check command in the owner's private Telegram chat triggers a separate
repository_dispatch event *without* any permission to publish to Instagram.
The same signing key is verified independently on a GitHub Actions runner.
No video or Buffer API is involved; automatic posting remains disabled.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time

import requests

_ID = re.compile(r"^[0-9]{5,20}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_BOT = re.compile(r"^[0-9]{5,16}:[A-Za-z0-9_-]{25,80}$")


def probe_content(review: dict) -> bytes:
    return "|".join((
        "telegram-probe-v1",
        review["telegram_user_id"],
        review["telegram_chat_id"],
        str(review["telegram_message_id"]),
        str(review["issued_at"]),
    )).encode("utf-8")


def make_probe(user_id: str, chat_id: str, message_id: int,
               secret: str, now: int | None = None) -> dict:
    if not _ID.fullmatch(user_id) or not _ID.fullmatch(chat_id):
        raise ValueError("Invalid Telegram reviewer identity")
    if user_id != chat_id:
        raise ValueError("Review bridge diagnostics require a private chat")
    if not isinstance(message_id, int) or message_id < 1:
        raise ValueError("Invalid Telegram message ID")
    if len(secret) < 32:
        raise ValueError("Approval signing key is missing or too short")
    result = {
        "platform": "telegram_probe",
        "telegram_user_id": user_id,
        "telegram_chat_id": chat_id,
        "telegram_message_id": message_id,
        "issued_at": int(time.time()) if now is None else now,
    }
    result["signature"] = hmac.new(
        secret.encode("utf-8"), probe_content(result), hashlib.sha256
    ).hexdigest()
    return result


def verify_probe(review: dict, secret: str, expected_user: str,
                 expected_chat: str, now: int | None = None) -> None:
    if review.get("platform") != "telegram_probe":
        raise ValueError("A normal publishing decision cannot be used as a diagnostics event")
    if not expected_user or not expected_chat or expected_user != expected_chat:
        raise ValueError("Trusted private reviewer not configured")
    if review.get("telegram_user_id") != expected_user or review.get("telegram_chat_id") != expected_chat:
        raise ValueError("Wrong Telegram reviewer or chat")
    message_id = review.get("telegram_message_id")
    if not isinstance(message_id, int) or message_id < 1:
        raise ValueError("Invalid Telegram message ID")
    issued = review.get("issued_at")
    timestamp = int(time.time()) if now is None else int(now)
    if not isinstance(issued, int) or not 0 <= timestamp - issued <= 600:
        raise ValueError("Diagnostic was delayed or timestamp invalid")
    if len(secret) < 32 or not _SHA.fullmatch(str(review.get("signature", ""))):
        raise ValueError("Missing valid diagnostic signature or signing key")
    digest = hmac.new(
        secret.encode("utf-8"), probe_content(review), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(digest, review["signature"]):
        raise ValueError("Diagnostic HMAC doesn't match the shared Render/GitHub key")


def report_success(review: dict, token: str) -> None:
    if not _BOT.fullmatch(token):
        raise RuntimeError("GitHub Telegram bot token unavailable or malformed")
    msg = (
        "✅ Pūrākau Pixels approval bridge verified!\n\n"
        "Your private Telegram /check reached Render, which securely "
        "notified GitHub. GitHub independently verified your identity "
        "and the approval signing key.\n\n"
        "This was a connection diagnostic ONLY. No new animation "
        "was generated, and nothing was uploaded to Instagram. "
        "Automatic publication is still OFF."
    )
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": review["telegram_chat_id"], "text": msg},
            timeout=(10, 30),
        )
    except requests.RequestException:
        raise RuntimeError("Telegram failed to receive GitHub bridge result") from None
    if response.status_code != 200 or not response.json().get("ok"):
        raise RuntimeError(f"Telegram bridge response failed: HTTP {response.status_code}")


def main() -> None:
    receipt = json.loads(os.environ["PURAKAU_TELEGRAM_PROBE_RECEIPT"])
    verify_probe(
        receipt,
        os.getenv("PURAKAU_APPROVAL_SIGNING_KEY", ""),
        os.getenv("TELEGRAM_APPROVER_USER_ID", ""),
        os.getenv("TELEGRAM_REVIEW_CHAT_ID", ""),
    )
    print("PASS: An authenticated private Telegram /check reached GitHub from Render.")
    print("PASS: The short-lived HMAC verified using GitHub's separate secret.")
    print("PASS: No Instagram publishing capability is present in this workflow.")
    report_success(receipt, os.getenv("TELEGRAM_BOT_TOKEN", ""))
    print("PASS: Telegram confirmed GitHub approval bridge test result.")


if __name__ == "__main__":
    main()
