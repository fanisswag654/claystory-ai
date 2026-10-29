"""Fast offline regression coverage for a finished curated film's metadata.

Specifically catches the old end-of-render bug where render() referenced
a nonexistent 'story' variable instead of the loaded 'storyboard' variable.
No network, expensive narration, Chromium, or FFmpeg render is performed.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_story
import render_candidate


class RenderManifestSafety(unittest.TestCase):
    def test_metadata_from_actual_loaded_storyboard(self):
        topic = prepare_story.source_briefs()["topics"][0]
        storyboard = prepare_story.build_candidate(
            topic, prepare_story.curated_script(topic)
        )
        storyboard["script_origin"] = "checked-in-curated-original"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "purakau-review.mp4"
            output.write_bytes(b"short synthetic test bytes; not an MP4")
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            timing = {"voice": "en-GB-RyanNeural", "story": topic["id"]}
            meta = render_candidate.build_manifest(
                storyboard, timing, output, 66.291, digest
            )
            self.assertEqual(meta["story_id"], topic["id"])
            self.assertEqual(meta["title"], topic["title"])
            self.assertEqual(meta["sources"], topic["sources"])
            self.assertEqual(meta["narrator"], "en-GB-RyanNeural")
            self.assertEqual(meta["video_sha256"], digest)
            self.assertEqual(meta["bytes"], output.stat().st_size)
            self.assertEqual(meta["duration"], 66.29)
            self.assertEqual(meta["status"], "pending-human-approval")
            self.assertEqual(meta["video_file"], "purakau-review.mp4")
            self.assertIn("cultural_warning", storyboard)
            self.assertEqual(meta["warning"], storyboard["cultural_warning"])
            json.dumps(meta, ensure_ascii=False)

    def test_render_never_reads_undefined_story_identifier(self):
        source = inspect.getsource(render_candidate.render)
        tree = ast.parse(textwrap.dedent(source))
        load_names = [
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        ]
        self.assertIn("storyboard", load_names)
        self.assertIn("build_manifest", load_names)
        self.assertNotIn(
            "story", load_names,
            "render() must use the loaded 'storyboard' variable, not 'story'",
        )

    def test_missing_story_field_fails_fast_in_metadata_helper(self):
        topic = prepare_story.source_briefs()["topics"][0]
        script = prepare_story.curated_script(topic)
        story = prepare_story.build_candidate(topic, script)
        story.pop("title")
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "purakau-review.mp4"
            video.write_bytes(b"x")
            with self.assertRaises(KeyError):
                render_candidate.build_manifest(
                    story, {"voice": "en-GB-RyanNeural"}, video, 10, "a" * 64
                )


if __name__ == "__main__":
    unittest.main()
