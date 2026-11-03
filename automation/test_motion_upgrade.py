"""Actual pixel and encoder checks for the 2.5D upgrade and delivery receipts."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import telegram_send
from deliver_cinematic import validate_receipt


class DeliveryEvidence(unittest.TestCase):
    def test_no_keyboard_or_wrong_frame_never_claimed_delivered(self):
        p={'proposal_id':'auto-review-rata-and-the-tree-'+'a'*12,'video_sha256':'a'*64}
        sent={'chat':{'id':12345678,'type':'private'},'video':{'width':1080,'height':1920},
              'caption':p['proposal_id'],'reply_markup':telegram_send.review_keyboard(p['proposal_id'])}
        telegram_send.validate_delivery_message(sent,p,'12345678')
        for broken in ({'reply_markup':{}},{'video':{'width':1920,'height':1080}},{'caption':'lost identifier'}):
            with self.subTest(broken=broken),self.assertRaises(RuntimeError):
                telegram_send.validate_delivery_message({**sent,**broken},p,'12345678')

    def test_release_without_exact_delivery_receipt_is_not_success(self):
        p={'proposal_id':'test','video_sha256':'a'*64}
        with self.assertRaises(RuntimeError):validate_receipt({},p)
        receipt={**p,'review_buttons_verified':True,'telegram_message_id':24,'status':'delivered_for_review_not_approved'}
        validate_receipt(receipt,p)
        with self.assertRaises(RuntimeError):validate_receipt({**receipt,'video_sha256':'b'*64},p)


class AuthoredMotion(unittest.TestCase):
    def test_character_moves_while_outside_support_stays_exact(self):
        import numpy as np
        from character_motion import for_artwork
        from PIL import Image
        path=Path(__file__).with_name('art')/'rata-and-the-tree'/'scene-03.jpg'
        animator=for_artwork(Image.open(path),path)
        self.assertIsNotNone(animator)
        start=animator.frame(0);later=animator.frame(.87)
        self.assertTrue(np.array_equal(start,animator.source))
        self.assertTrue(np.array_equal(start[:180],later[:180]))
        self.assertGreater(animator.audit()['changed_pixels'],1000)
        self.assertLess(float(np.abs(later.astype(float)-start).mean()),3)
        # Subframe displacement changes smoothly; source never mutates.
        a=animator.frame(.86);b=animator.frame(.87)
        self.assertLess(float(np.abs(a.astype(float)-b).mean()),.2)

    def test_unknown_art_retains_original_supported_camera_behavior(self):
        from character_motion import for_artwork
        self.assertIsNone(for_artwork(None,Path('unknown/scene-01.jpg')))

    def test_real_transition_preserves_frames_and_reaches_incoming_image(self):
        from cinematic_transitions import soften_entry
        from depthflow_motion import validate_clip
        import numpy as np
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,color in [('before','red'),('after','blue')]:
                subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i',
                                f'color={color}:s=180x320:r=30:d=2','-c:v','libx264',
                                '-pix_fmt','yuv420p',str(root/f'{name}.mp4')],check=True)
            result=soften_entry(root/'before.mp4',root/'after.mp4',root/'blend.mp4',60,60)
            validate_clip(result,60,180,320)
            raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(result),'-vf','scale=2:2','-pix_fmt','rgb24','-f','rawvideo','-'])
            frames=np.frombuffer(raw,dtype=np.uint8).reshape(60,2,2,3)
            self.assertGreater(frames[0,:,:,0].mean(),240)
            self.assertGreater(frames[15,:,:,2].mean(),240)
            self.assertLess(frames[59,:,:,0].mean(),5)


if __name__=='__main__':unittest.main()
