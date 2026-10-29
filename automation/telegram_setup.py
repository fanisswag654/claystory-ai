#!/usr/bin/env python3
"""Manually connect a Telegram bot to the already deployed Render HTTPS route.

Requires GitHub Actions Secrets TELEGRAM_BOT_TOKEN and
TELEGRAM_WEBHOOK_SECRET, and the EXACT SAME webhook secret already set in
Render environment variables. Never prints or saves the bot access token.
No story generation, WhatsApp request or Instagram publication occurs.
"""
from __future__ import annotations

import json
import os
import re

import requests

CALLBACK_URL = "https://claystory-whatsapp-approval.onrender.com/webhook/telegram"


def telegram_api(method: str, payload: dict) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not re.fullmatch(r"[0-9]{5,16}:[A-Za-z0-9_-]{25,80}", token):
        raise RuntimeError("Telegram bot token is not configured in GitHub Actions Secrets")
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=payload,
            timeout=30,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Telegram request to {method} failed; check bot connectivity") from None
    if response.status_code != 200:
        raise RuntimeError(f"Telegram {method} refused the request, HTTP {response.status_code}")
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} returned an error; token not printed")
    return data["result"] if isinstance(data.get("result"), dict) else {"value": data.get("result")}


def main() -> None:
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", secret):
        raise RuntimeError("TELEGRAM_WEBHOOK_SECRET must be a private 32–128-character secret")
    bot = telegram_api("getMe", {})
    username = bot.get("username", "")
    if not username.lower().endswith("bot") or not bot.get("is_bot"):
        raise RuntimeError("BotFather token does not identify a valid Telegram bot")
    print("Connected to your Telegram bot. Username:", "@" + username)
    result = telegram_api("setWebhook", {
        "url": CALLBACK_URL,
        "secret_token": secret,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": False,
    })
    if result.get("value") is not True:
        raise RuntimeError("Telegram did not accept the HTTPS callback address")
    info = telegram_api("getWebhookInfo", {})
    if info.get("url") != CALLBACK_URL:
        raise RuntimeError("Webhook URL not confirmed by Telegram")
    print("Webhook successfully registered at:", CALLBACK_URL)
    print("Pending Telegram updates:", info.get("pending_update_count", 0))
    print("Now open Telegram, message @" + username + " and tap START.")
    print("Once the bot replies with your two numeric IDs, save them privately.")
    print("Instagram automation remains disabled until explicitly enabled.")


if __name__ == "__main__":
    main()
