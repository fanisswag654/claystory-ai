"""Preflight tests for original Tāne / Te Ao Mārama eight-scene film."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

SCRIPTS=Path(__file__).resolve().parent
ROOT=SCRIPTS.parent
sys.path.insert(0,str(SCRIPTS))

from tane_sound import validate_story, KEY, SAMPLE_RATE
from v31_storyteller import PROFILES


class TaneFilmTests(unittest.TestCase):
    def test_own_original_story_has_eight_timed_scenes(self):
        story=validate_story()
        self.assertEqual(story["key"],"tane-nz")
        self.assertEqual(len(story["scenes"]),8)
        self.assertEqual(len({row["title"] for row in story["scenes"]}),8)
        self.assertTrue(all(row["caption"] and row["narration"] for row in story["scenes"]))
        self.assertTrue(all(len(row["narration"])>50 for row in story["scenes"]))

    def test_core_maori_names_preserved_with_macrons(self):
        story=validate_story()
        words=" ".join(x["narration"] for x in story["scenes"])
        for word in ["Tāne","Ranginui","Papatūānuku","Tāwhirimātea","Māori"]:
            if word=="Māori":
                continue
            with self.subTest(word=word):
                self.assertIn(word,words)

    def test_approved_cinematic_voice_profile_for_new_animation(self):
        self.assertEqual(PROFILES["cinematic"]["model"],"en-GB-RyanNeural")
        self.assertEqual(PROFILES["cinematic"]["engine"],"edge")
        self.assertEqual(len(PROFILES["cinematic"]["rates"]),8)
        self.assertEqual(SAMPLE_RATE,22050)

    def test_story_has_culturally_grounded_sources_and_no_auto_publish(self):
        story=validate_story()
        self.assertGreaterEqual(len(story.get("sources",[])),2)
        self.assertTrue(all(s["url"].startswith("https://") for s in story["sources"]))
        self.assertIn("Traditions differ",story["culturalNote"])
        approvals=json.loads((ROOT/"config/instagram-approved.json").read_text())
        self.assertNotIn(KEY,approvals.get("approved_reels",{}))

    def test_player_depends_only_on_original_source(self):
        player=(ROOT/"tane.html").read_text(encoding="utf-8")
        animation=(ROOT/"scripts/tane_animation.js").read_text(encoding="utf-8")
        self.assertIn("scripts/tane_animation.js",player)
        self.assertIn("scripts/tane_characters.js",player)
        self.assertIn("vendor/tween.umd.js",player)
        self.assertIn("TaneCharacters.draw(p,",animation)
        self.assertNotIn("function silhouette(",animation)
        self.assertIn("window.TaneFilm=",animation)
        self.assertIn("drawAt(t)",animation)
        self.assertIn("stories/tane.json",animation)
        self.assertNotIn("buffer_api",animation)

    def test_actor_rigs_are_detailed_and_culturally_respectful(self):
        actors=(ROOT/"scripts/tane_characters.js").read_text(encoding="utf-8")
        for pose in ("idle","listen","argue","reach","strain","push","wonder","storm"):
            self.assertIn(pose+": Object.freeze([",actors)
        for name in ("tane","tawhirimatea","earth","ochre","river"):
            self.assertIn(name+": Object.freeze({",actors)
        for item in ("function face(", "function drawBracing(", "function arms(",
                     "function costume(", "function legs("):
            self.assertIn(item,actors)
        self.assertIn("No moko",actors)

    def test_renderer_checks_audio_and_eight_distinct_scenes(self):
        renderer=(ROOT/"scripts/render_tane.py").read_text(encoding="utf-8")
        self.assertIn("len(durations)!=8",renderer)
        self.assertIn("len(set(checksums))!=8",renderer)
        self.assertIn("voice",renderer)
        self.assertIn("en-GB-RyanNeural",renderer)
        self.assertIn("540",renderer)
        self.assertIn("960",renderer)


if __name__=="__main__":
    unittest.main()
