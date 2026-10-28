"""Tests for V30 narrator comparison without installing any ML packages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v30_voice as voice


class VoicePreviewTests(unittest.TestCase):
    def test_existing_fish_and_maui_stories_are_parseable(self):
        for name, count in (("fish", 8), ("maui", 6)):
            with self.subTest(story=name):
                scenes = voice.story_scenes(name)
                self.assertEqual(len(scenes), count)
                self.assertTrue(all(isinstance(x["narration"], str) for x in scenes))

    def test_story_reader_refuses_missing_or_empty_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "player.html"
            story = [{"narration": "Valid text."} for _ in range(8)]
            story[4] = {"narration": ""}
            fake.write_text(
                "const fishStory=" + json.dumps(story) +
                ";\nconst fishChoice={};", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "spoken narration"):
                voice.story_scenes("fish", fake)

    def test_dry_run_does_not_modify_production_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preview"
            args = voice.build_parser().parse_args(
                ["--story", "fish", "--scenes", "1", "6",
                 "--engine", "nano", "--output-dir", str(output), "--dry-run"]
            )
            with patch.object(voice, "nano_model") as nano:
                output_items = voice.run(args)
                nano.assert_not_called()
            self.assertEqual(output_items, [])
            self.assertFalse(output.exists())

    def test_cannot_write_preview_into_production_audio(self):
        args = voice.build_parser().parse_args(
            ["--engine", "edge", "--output-dir", str(voice.ROOT / "audio"),
             "--dry-run"]
        )
        with self.assertRaisesRegex(ValueError, "overwrite production"):
            voice.run(args)

    def test_voice_cloning_requires_explicit_consent(self):
        with self.assertRaisesRegex(ValueError, "consent-confirmed"):
            voice.validate_reference(Path("any.wav"), consent=False)

    def test_reference_not_allowed_for_edge_baseline(self):
        with patch.object(voice, "validate_reference"):
            args = voice.build_parser().parse_args(
                ["--engine", "edge", "--reference-wav", "/tmp/voice.wav", "--dry-run"]
            )
            with self.assertRaisesRegex(ValueError, "only used with Chatterbox"):
                voice.run(args)

    def test_output_html_escapes_untrusted_story_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            voice.comparison_page(
                "fish-nz",
                [{
                    "scene": 1, "engine": "approved NZ voice", "filename": "clip.mp3",
                    "seconds": 9.4, "text": "<script>alert(1)</script>",
                }],
                Path(tmp),
            )
            page = (Path(tmp) / "listen.html").read_text(encoding="utf-8")
            self.assertNotIn("<script>", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertIn("<audio controls", page)

    def test_baseline_preview_is_only_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            source = work / "audio"
            source.mkdir()
            original = source / "fish-nz-1.mp3"
            original.write_bytes(b"mock-approved-voice")
            dest = work / "preview"
            dest.mkdir()
            with patch.object(voice, "ROOT", work), patch.object(
                voice, "audio_duration", return_value=7.2
            ):
                metadata = voice.sample_baseline("fish-nz", 1, dest)
            self.assertEqual(original.read_bytes(), b"mock-approved-voice")
            self.assertEqual(metadata["engine"], "edge-nz-approved")
            self.assertEqual(
                (dest / metadata["filename"]).read_bytes(), b"mock-approved-voice"
            )


if __name__ == "__main__":
    unittest.main()
