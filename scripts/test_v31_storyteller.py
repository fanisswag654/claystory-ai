"""V31 alternate-narrator safety and delivery tests; no network or ML required."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v31_storyteller as voice


class V31NarrationTests(unittest.TestCase):
    def test_profiles_are_new_and_male_not_old_nz_voice(self):
        self.assertEqual(voice.PROFILES["cinematic"]["model"], "en-GB-RyanNeural")
        self.assertEqual(voice.PROFILES["warm"]["model"], "en-US-ChristopherNeural")
        self.assertNotEqual(
            voice.PROFILES["cinematic"]["model"],
            voice.PROFILES["warm"]["model"],
        )
        self.assertTrue(all(
            p["model"] != "en-NZ-MitchellNeural" for p in voice.PROFILES.values()
        ))
        for profile in voice.PROFILES.values():
            self.assertEqual(len(profile["rates"]), 8)
            self.assertEqual(len(profile["pitches"]), 8)
            self.assertEqual(len(profile["pauses"]), 8)
            self.assertGreater(len(set(profile["rates"])), 4)

    def test_sentences_preserve_original_maori_spelling(self):
        sample = "Māui waits. The waka rocks! The pūrākau continues."
        self.assertEqual(
            voice.sentences(sample),
            ["Māui waits.", "The waka rocks!", "The pūrākau continues."],
        )

    def test_join_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            voice.join_sentences([], .3, Path("/tmp/none.mp3"))
        with self.assertRaises(ValueError):
            voice.join_sentences([Path("/tmp/none.mp3")], -1, Path("/tmp/none.mp3"))

    def test_refuse_to_mislabel_same_file_as_new_voice(self):
        with tempfile.TemporaryDirectory() as root:
            a=Path(root)/"new.mp3"; b=Path(root)/"old.mp3"
            a.write_bytes(b"original");b.write_bytes(b"original")
            with self.assertRaisesRegex(RuntimeError,"byte-identical"):
                voice.validate_distinct(a,b)

    def test_dry_run_does_not_create_voice_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"no-output"
            args=argparse.Namespace(
                story="fish",voice="cinematic",output=target,
                full=True,stage_film=False,dry_run=True,
            )
            self.assertEqual(asyncio.run(voice.generate(args)),[])
            self.assertFalse(target.exists())

    def test_staging_forbidden_outside_ephemeral_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=argparse.Namespace(
                story="fish",voice="cinematic",output=Path(tmp)/"preview",
                full=True,stage_film=True,dry_run=True,
            )
            with patch.dict(os.environ,{"GITHUB_ACTIONS":"false",
                                        "CLAYSTORY_PREVIEW_WORKSPACE":"1"}):
                with self.assertRaisesRegex(ValueError,"temporary GitHub Actions"):
                    asyncio.run(voice.generate(args))

    def test_staging_cannot_write_in_production_audio_without_flag(self):
        args=argparse.Namespace(
            story="fish",voice="warm",output=voice.ROOT/"audio"/"oops",
            full=True,stage_film=False,dry_run=True,
        )
        with self.assertRaisesRegex(ValueError,"overwrite production"):
            asyncio.run(voice.generate(args))

    def test_story_has_all_eight_narrations(self):
        scenes=voice.story_scenes("fish")
        self.assertEqual(len(scenes),8)
        self.assertTrue(all(x["narration"].strip() for x in scenes))

    def test_review_page_escapes_script_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            voice.build_review_page(folder,[{
                "scene":1,"file":"safe.mp3",
                "narration":"<script>alert(1)</script>",
            }],"Cinematic British male")
            data=(folder/"LISTEN.html").read_text()
            self.assertNotIn("<script>",data)
            self.assertIn("&lt;script&gt;",data)
            self.assertIn("safe.mp3",data)


if __name__ == "__main__":
    unittest.main()
