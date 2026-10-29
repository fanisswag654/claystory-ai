#!/usr/bin/env python3
"""Create one source-grounded, eight-scene storyboard for HUMAN review.

An OpenAI API key is required for automatic new narration. A curated topic
brief supplies all allowed factual plot points, source URLs, visual beats and
actions. The LLM writes fresh English narration rather than inventing cultural
details. Cultural/te reo correctness still requires the user's approval.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = ROOT / "automation" / "story_briefs.json"
OUTPUT = ROOT / "automation" / "candidate-story.json"


def source_briefs() -> dict:
    data = json.loads(BRIEFS.read_text(encoding="utf-8"))
    topics = data["topics"]
    assert len({x["id"] for x in topics}) == len(topics)
    for topic in topics:
        assert len(topic["visuals"]) == len(topic["actions"]) == 8
        assert topic["facts"] and topic["sources"]
        assert all(s["url"].startswith("https://") for s in topic["sources"])
    return data


def next_topic(used: list[str], requested: str | None = None) -> dict:
    topics = source_briefs()["topics"]
    if requested:
        choices = [t for t in topics if t["id"] == requested]
        if len(choices) != 1:
            raise ValueError("Unknown curated story topic: " + requested)
        if requested in used:
            raise ValueError("The selected story was already proposed; refusing an accidental duplicate")
        return choices[0]
    for topic in topics:
        if topic["id"] not in used:
            return topic
    raise RuntimeError("All sourced stories have already been proposed. Expand the reviewed topic library before generating another.")


def extract_text(result: dict) -> str:
    for item in result.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    return part["text"]
    raise RuntimeError("AI service did not return story text; nothing will be published")


def generate_script(topic: dict) -> list[dict]:
    token = os.getenv("OPENAI_API_KEY")
    if not token:
        raise RuntimeError("OPENAI_API_KEY missing. Automated story generation is OFF; no WhatsApp video or Instagram post will be sent.")
    schema = {
        "type": "object",
        "properties": {
            "scenes": {
                "type": "array", "minItems": 8, "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "caption": {"type": "string"},
                        "narration": {"type": "string"},
                    },
                    "required": ["title", "caption", "narration"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["scenes"],
        "additionalProperties": False,
    }
    instruction = (
        "You are an editorial assistant drafting a faithful, accessible "
        "eight-scene English-language Māori pūrākau for human cultural review. "
        "Only use the supplied curated factual statements. Do not invent events, "
        "traditional quotes, whakapapa, names, karakia, iwi claims, rituals, "
        "moko or other cultural details. Do not copy copyrighted source wording. "
        "Accurately preserve te reo Māori macrons. Each scene has 1–2 original "
        "sentences of 85–230 characters, one unique title (max 44 chars), "
        "and a simple uppercase caption (max 36 chars). "
        "Use the provided fact and visual sequence, spread the facts across "
        "eight scenes, and close with 'In one telling...' or similarly signal "
        "that iwi traditions can differ. No fabricated spoken dialogue. "
        "Your output is for review and is never automatically authoritative."
    )
    data = {
        "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        "input": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps({
                "title": topic["title"],
                "facts_to_use_only": topic["facts"],
                "scene_order": list(enumerate(topic["visuals"], 1)),
                "names_with_exact_spelling": topic["known_names"],
                "sources_for_editorial_review": topic["sources"],
            }, ensure_ascii=False)},
        ],
        "text": {"format": {"type": "json_schema", "name": "curated_purakau", "strict": True, "schema": schema}},
        "max_output_tokens": 3500,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        method="POST", headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            output = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Story generation request failed with HTTP " + str(exc.code)) from exc
    text = extract_text(output)
    return json.loads(text)["scenes"]


def validate_script(topic: dict, script: list[dict]) -> list[dict]:
    if not isinstance(script, list) or len(script) != 8:
        raise ValueError("Expected exactly eight scenes")
    seen = set()
    scenes = []
    for i, item in enumerate(script):
        if not isinstance(item, dict):
            raise ValueError("Invalid scene object")
        title = item.get("title", "").strip()
        caption = item.get("caption", "").strip()
        words = item.get("narration", "").strip()
        if not 3 <= len(title) <= 44 or title.lower() in seen:
            raise ValueError("Invalid or repeated scene title")
        seen.add(title.lower())
        if not 3 <= len(caption) <= 36 or caption != caption.upper():
            raise ValueError("Scene caption must be short and uppercase")
        if not 85 <= len(words) <= 360:
            raise ValueError(f"Narration scene {i + 1} is outside safe duration range")
        if re.search(r"https?://|<script", words, flags=re.I):
            raise ValueError("Unexpected markup or URLs in narration")
        scenes.append({
            "title": title, "caption": caption, "narration": words,
            "visual": topic["visuals"][i], "action": topic["actions"][i],
        })
    return scenes


def build_candidate(topic: dict, script: list[dict]) -> dict:
    return {
        "key": topic["id"],
        "title": topic["title"],
        "theme": topic["theme"],
        "hero_role": topic["hero_role"],
        "support_role": topic["support_role"],
        "scenes": validate_script(topic, script),
        "source_facts": topic["facts"],
        "sources": topic["sources"],
        "narrator": "en-GB-RyanNeural",
        "review_status": "pending-human-approval",
        "cultural_warning": "One public-facing retelling; Māori pronunciation, cultural accuracy and storytelling require human review.",
    }


def main():
    parser = argparse.ArgumentParser(description="Generate a culturally reviewable short pūrākau from source-backed topics")
    parser.add_argument("--topic")
    parser.add_argument("--used", type=Path, help="JSON array of previously proposed topic IDs")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    used = json.loads(args.used.read_text()) if args.used and args.used.exists() else []
    topic = next_topic(used, args.topic)
    if args.dry_run:
        print(json.dumps({
            "topic": topic["id"], "title": topic["title"],
            "facts": topic["facts"], "sources": topic["sources"],
            "status": "Ready; no API call or file change"
        }, ensure_ascii=False, indent=2))
        return
    candidate = build_candidate(topic, generate_script(topic))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Generated NEW review-only storyboard:", candidate["title"])


if __name__ == "__main__":
    main()
