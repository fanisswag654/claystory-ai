import unittest
from render_cinematic import validate_reel
class ReelsExport(unittest.TestCase):
 def setUp(self):
  self.probe={"streams":[{"codec_type":"video","codec_name":"h264","width":1080,"height":1920,"pix_fmt":"yuv420p","r_frame_rate":"30/1","duration":"67"},{"codec_type":"audio","codec_name":"aac","duration":"67"}]}
 def test_portrait_export(self):validate_reel(self.probe,67)
 def test_landscape_rejected(self):
  self.probe["streams"][0].update(width=1920,height=1080)
  with self.assertRaises(ValueError):validate_reel(self.probe,67)
 def test_missing_audio_rejected(self):
  self.probe["streams"].pop()
  with self.assertRaises(ValueError):validate_reel(self.probe,67)
 def test_incomplete_picture_rejected(self):
  self.probe["streams"][0]["duration"]="58"
  with self.assertRaises(ValueError):validate_reel(self.probe,67)
 def test_unsupported_pixel_format_rejected(self):
  self.probe["streams"][0]["pix_fmt"]="yuv444p"
  with self.assertRaises(ValueError):validate_reel(self.probe,67)
