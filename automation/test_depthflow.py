"""Offline adapter checks; actual OpenGL/model inference runs in the smoke job."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from depthflow_motion import camera_offset, validate_clip, render_scene


class DepthMotion(unittest.TestCase):
    def test_gentle_path_is_continuous_and_reversible(self):
        points=[camera_offset(i/100) for i in range(101)]
        self.assertTrue(all(abs(x)<=.14 and 0<=y<=.025 for x,y in points))
        self.assertTrue(all(b[0]>=a[0] for a,b in zip(points,points[1:])))
        self.assertLess(max(b[0]-a[0] for a,b in zip(points,points[1:])),.005)
        for i in range(101):
            normal=camera_offset(i/100)
            self.assertEqual(camera_offset(i/100,True),(-normal[0],normal[1]))

    def test_invalid_clock_and_stretched_output_rejected(self):
        for value in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError):camera_offset(value)
        with self.assertRaises(ValueError):render_scene('unused','unused',30,width=1080,height=1080)

    def test_incomplete_or_wrong_format_clip_rejected(self):
        v={'codec_type':'video','width':1080,'height':1920,'codec_name':'h264',
           'pix_fmt':'yuv420p','nb_read_frames':'60','r_frame_rate':'30/1'}
        with patch('depthflow_motion.subprocess.check_output',return_value=json.dumps({'streams':[v]})):
            validate_clip('test.mp4',60)
        for update in ({'nb_read_frames':'59'},{'width':1920},{'pix_fmt':'yuv444p'},{'r_frame_rate':'24/1'}):
            with self.subTest(update=update),patch('depthflow_motion.subprocess.check_output',
                 return_value=json.dumps({'streams':[{**v,**update}]})):
                with self.assertRaises(ValueError):validate_clip('test.mp4',60)
