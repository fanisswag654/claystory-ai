import unittest,json,tempfile,hashlib,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cinematic_assets,approve_publish
class CinematicSafety(unittest.TestCase):
 def test_real_asset_set_and_voice(self):
  self.assertEqual(len(cinematic_assets.verify_assets("maui-mahuika-fire")),8)
  self.assertEqual(cinematic_assets.VOICE,"en-US-ChristopherNeural")
 def test_unknown_story_never_uses_wrong_art(self):
  with self.assertRaisesRegex(ValueError,"artwork needed"):
   cinematic_assets.verify_assets("rata-and-the-tree")
 def test_tampered_art_fails_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);key="maui-mahuika-fire";folder=root/"art"/key;folder.mkdir(parents=True)
   config={"artwork":{key:{f"scene-{i:02}.jpg":"0"*64 for i in range(1,9)}}}
   (root/"cinematic-system.json").write_text(json.dumps(config))
   (folder/"scene-01.jpg").write_bytes(b"changed-art")
   with patch.object(cinematic_assets,"ROOT",root),self.assertRaisesRegex(ValueError,"modified"):
    cinematic_assets.verify_assets(key)
 def test_same_bytes_under_different_tag_never_call_buffer(self):
  p={"proposal_id":"auto-review-other-"+"a"*12,"video_sha256":"a"*64,"video_url":"url"}
  with patch.object(approve_publish,"buffer_api") as api,self.assertRaisesRegex(ValueError,"no duplicate"):
   approve_publish.submit_approved(p,{"old":{"video_sha256":"a"*64,"mode":"shareNow"}})
  api.assert_not_called()
