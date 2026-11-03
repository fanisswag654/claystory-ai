"""Catch square playback and missing/duplicated words in the actual edit."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from fractions import Fraction

from video_geometry import validate_display,normalize_display
from reel_edit import subtitle_groups,shot_plan


class Recut(unittest.TestCase):
    def test_three_word_captions_preserve_the_exact_story(self):
        scripts=json.loads(Path(__file__).with_name('curated_scripts.json').read_text())
        for scenes in scripts['scripts'].values():
            for scene in scenes:
                text=scene['narration'];groups=subtitle_groups(text)
                self.assertTrue(all(1<=len(g)<=3 for g in groups))
                self.assertEqual([w for g in groups for w in g],text.split())

    def test_twenty_four_shots_cover_every_frame_once(self):
        for scene,frames in enumerate([301,270,289,311,290,301,307,330]):
            shots=shot_plan('rata-and-the-tree',scene,frames)
            self.assertEqual(len(shots),3)
            self.assertEqual(sum(s['frames'] for s in shots),frames)
            self.assertEqual(shots[0]['start_frame'],0)
            for a,b in zip(shots,shots[1:]):self.assertEqual(a['start_frame']+a['frames'],b['start_frame'])
            self.assertEqual(len(set(s['zoom'] for s in shots)),3)

    def test_square_playback_rejected_even_with_correct_pixel_dimensions(self):
        good={'width':1080,'height':1920,'sample_aspect_ratio':'1:1','display_aspect_ratio':'9:16'}
        validate_display(good)
        for bad in [{'sample_aspect_ratio':'16:9','display_aspect_ratio':'1:1'},
                    {'sample_aspect_ratio':'0:1'}, {'side_data_list':[{'rotation':90}]}]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_display({**good,**bad})
        missing={'width':1080,'height':1920}
        with self.assertRaises(ValueError):validate_display(missing)

    def test_real_h264_square_playback_fixed_without_resizing_the_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'display.mp4'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i',
                            'testsrc2=size=180x320:rate=30:duration=0.5',
                            '-vf','setsar=16/9','-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True)
            probe=lambda:json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))['streams'][0]
            self.assertEqual(probe()['display_aspect_ratio'],'1:1')
            decode=lambda:subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'])
            before=decode();normalize_display(path,180,320);after=decode()
            self.assertEqual(before,after)
            self.assertEqual(probe()['sample_aspect_ratio'],'1:1')
            self.assertEqual(probe()['display_aspect_ratio'],'9:16')


if __name__=='__main__':unittest.main()
