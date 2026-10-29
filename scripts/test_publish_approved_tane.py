"""Offline safety checks for publishing one unchanged, approved Tāne V33 Reel."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_approved_tane as pub


class TanePublishingSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.file = self.dir / "tane-nz-V33-detailed.mp4"
        self.file.write_bytes(b"V33 exact media" * 9000)
        self.sha = hashlib.sha256(self.file.read_bytes()).hexdigest()
        (self.dir / "film-report.json").write_text(json.dumps({
            "story": "Tāne and the First Light",
            "animation_version": "V33 detailed articulated pixel actors",
            "narrator": "en-GB-RyanNeural",
            "scenes": 8,
            "fps": 24,
            "resolution": "540x960",
            "video": "tane-nz-balanced.mp4",
        }))
        self.config = self.dir / "approval.json"
        self.config.write_text(json.dumps({
            "story": "tane-nz",
            "source_build_run_id": 40794388100,
            "source_build_head_sha": "fbd9ac1cdb53f980527c2c439d567ae2572cc7ab",
            "source_artifact_id": 12862439809,
            "review_video_filename": "tane-nz-V33-detailed.mp4",
            "character_animation_version": "V33",
            "narrator": "en-GB-RyanNeural",
        }))
        self.history_path = self.dir / "posting-history.json"
        self.history_path.write_text("{}")

    def test_approved_file_has_exact_release_path_and_checksum(self):
        with patch.object(pub, "APPROVAL_PATH", self.config), \
             patch.dict(os.environ, {"TANE_APPROVED_MP4": str(self.file)}), \
             patch.object(pub, "validate_reel", return_value="540x960 24fps"):
            file,sha,url=pub.approved_asset()
        self.assertEqual(file,self.file)
        self.assertEqual(sha,self.sha)
        self.assertIn("instagram-tane-nz-v33-"+self.sha,url)
        self.assertTrue(url.endswith("/tane-nz-V33-detailed.mp4"))

    def test_wrong_artwork_metadata_rejected(self):
        report=self.dir/"film-report.json"
        data=json.loads(report.read_text())
        data["animation_version"]="V32"
        report.write_text(json.dumps(data))
        with patch.object(pub, "APPROVAL_PATH", self.config), \
             patch.dict(os.environ, {"TANE_APPROVED_MP4": str(self.file)}):
            with self.assertRaisesRegex(RuntimeError,"Video report"):
                pub.approved_asset()

    def test_unknown_source_build_id_rejected(self):
        config=json.loads(self.config.read_text())
        config["source_build_run_id"]=999999
        self.config.write_text(json.dumps(config))
        with patch.object(pub, "APPROVAL_PATH", self.config), \
             patch.dict(os.environ, {"TANE_APPROVED_MP4": str(self.file)}):
            with self.assertRaisesRegex(RuntimeError,"Approval does not identify"):
                pub.approved_asset()

    def test_already_published_refuses_duplicate_creation(self):
        key=f"tane-nz:{self.sha}:shareNow"
        self.history_path.write_text(json.dumps({
            key:{
                "buffer_post_id":"test-buffer-id",
                "video_url":f"https://github.com/{pub.REPO}/releases/"
                            f"download/instagram-tane-nz-v33-{self.sha}/"
                            "tane-nz-V33-detailed.mp4",
            }
        }))
        with patch.object(pub,"APPROVAL_PATH",self.config), \
             patch.object(pub,"HISTORY_PATH",self.history_path), \
             patch.object(pub,"validate_reel", return_value="540x960 24fps"), \
             patch.dict(os.environ,{
                 "IG_MODE":"draft",
                 "BUFFER_API_KEY":"fake-unit-test-key",
                 "INSTAGRAM_USERNAME":"purakaupixel",
                 "TANE_APPROVED_MP4":str(self.file),
             }), patch.object(pub,"create_post") as create, \
             patch.object(pub,"edit_instagram_reel") as edit:
            pub.main()
        create.assert_not_called()
        edit.assert_not_called()

    def test_refuse_wrong_instagram_handle(self):
        with patch.dict(os.environ,{
            "IG_MODE":"draft",
            "BUFFER_API_KEY":"fake-unit-test-key",
            "INSTAGRAM_USERNAME":"not-the-real-profile",
        }), patch.object(pub, "create_post") as create:
            with self.assertRaisesRegex(RuntimeError,"must be @purakaupixel"):
                pub.main()
            create.assert_not_called()

    def test_refuse_unapproved_copy_or_filename(self):
        bad=self.dir/"copy.mp4"
        bad.write_bytes(self.file.read_bytes())
        with patch.object(pub,"APPROVAL_PATH",self.config), \
             patch.dict(os.environ,{"TANE_APPROVED_MP4":str(bad)}), \
             patch.object(pub,"create_post") as create:
            with self.assertRaisesRegex(RuntimeError,"Cannot find exact approved file"):
                pub.approved_asset()
            create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
