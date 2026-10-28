"""V32 tests: approved cinematic narrator must be the production default.

Unit tests never contact speech providers, overwrite audio, or publish videos.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))


def generator_with_args(*argv):
    """Load the CLI safely without synthesizing audio."""
    spec = importlib.util.spec_from_file_location(
        "claystory_narrator_under_test", SCRIPTS / "generate_narration.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "argv", ["generate_narration.py", *argv]):
        spec.loader.exec_module(module)
    return module


class CinematicNarratorTests(unittest.TestCase):
    def test_approved_v31_voice_is_new_default(self):
        with patch.dict("os.environ", {"CLAYSTORY_NARRATOR": "cinematic"}):
            module = generator_with_args()
        self.assertEqual(module.options.narrator, "cinematic")
        self.assertEqual(module.PROFILES["cinematic"]["model"], "en-GB-RyanNeural")

    def test_legacy_voice_is_still_optional(self):
        module = generator_with_args("--narrator", "nz")
        self.assertEqual(module.options.narrator, "nz")

    def test_generated_fish_and_future_custom_scenes_use_same_cinematic_engine(self):
        module = generator_with_args("--narrator", "cinematic")
        for key in ("fish-nz", "maui-nz", "custom", "ocean"):
            with self.subTest(story=key), tempfile.TemporaryDirectory() as folder:
                module.out = Path(folder)
                cinematic = AsyncMock()
                with patch.object(module, "generate_edge", cinematic), \
                     patch.object(module, "media_duration", return_value=8.1):
                    asyncio.run(module.voices(
                        key, [{"narration": "Māui paddles his waka."}],
                        "en-NZ-MitchellNeural", [("+0%", "+0Hz")],
                    ))
                cinematic.assert_awaited_once()
                call = cinematic.await_args.args
                self.assertEqual(call[2], "en-GB-RyanNeural")
                self.assertEqual(call[3], 0)
                self.assertEqual(call[0], "Māui paddles his waka.")

    def test_legacy_nz_uses_old_voice_only_if_requested(self):
        module = generator_with_args("--narrator", "nz")
        with tempfile.TemporaryDirectory() as folder:
            module.out = Path(folder)
            original = AsyncMock()
            with patch.object(module, "conversational_fish_voice", original):
                asyncio.run(module.voices(
                    "fish-nz", [{"narration": "Māui watches."}],
                    "en-NZ-MitchellNeural", [("+2%", "+0Hz")],
                ))
            original.assert_awaited_once()
            self.assertEqual(original.await_args.args[-1], "en-NZ-MitchellNeural")

    def test_manifest_records_production_voice_and_updated_duration(self):
        module = generator_with_args("--narrator", "cinematic")
        with tempfile.TemporaryDirectory() as folder:
            module.out = Path(folder)
            scenes = [{"narration": "Māui sees the great fish."} for _ in range(8)]
            with patch.object(module, "curated", return_value=scenes), \
                 patch.object(module, "voices", new_callable=AsyncMock), \
                 patch.object(module, "media_duration", return_value=10.5), \
                 patch.object(module, "continuous"), \
                 patch.object(module, "soundtrack"):
                module.generate_featured("fish")
            manifest = json.loads(
                (Path(folder) / "fish-nz-timing.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["voice"], "en-GB-RyanNeural")
            self.assertEqual(manifest["narrator_profile"], "cinematic")
            self.assertEqual(manifest["revision"], 32)
            self.assertEqual(len(manifest["durations"]), 8)

    def test_reuse_maintains_existing_voice_label_instead_of_lying(self):
        module = generator_with_args("--narrator", "cinematic", "--reuse-voice")
        with tempfile.TemporaryDirectory() as folder:
            module.out = Path(folder)
            manifest = Path(folder) / "fish-nz-timing.json"
            manifest.write_text(json.dumps({
                "voice": "en-NZ-MitchellNeural",
                "revision": 26,
                "description": "Original NZ voice",
                "durations": [11] * 8
            }))
            with patch.object(module, "curated", return_value=[{
                "narration": "Māui is here."
            } for _ in range(8)]), \
                 patch.object(module, "voices", new_callable=AsyncMock), \
                 patch.object(module, "media_duration", return_value=10.5), \
                 patch.object(module, "continuous"), \
                 patch.object(module, "soundtrack"):
                module.generate_featured("fish")
            reread = json.loads(manifest.read_text())
            self.assertEqual(reread["voice"], "en-NZ-MitchellNeural")
            self.assertEqual(reread["revision"], 26)
            self.assertEqual(reread["narrator_profile"], "existing")


if __name__ == "__main__":
    unittest.main()
