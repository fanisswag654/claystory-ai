"""Voice selection and approval invariants, without model downloads."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cinematic_assets
import finalize_proposal
import approve_publish
import telegram_send
import voicestudio_voice as voice


class VoiceStudioNarration(unittest.TestCase):
    def test_natural_male_preset_and_telemetry_disabled(self):
        self.assertEqual(voice.PRESET,'expr-voice-3-m')
        self.assertEqual(voice.VOICE,cinematic_assets.VOICE)
        self.assertEqual(voice.SPEED,.92)
        self.assertEqual(os.environ['ORT_DISABLE_TELEMETRY'],'1')
        self.assertEqual(os.environ['OMNIVOICE_ANALYTICS_DISABLED'],'1')

    def test_empty_script_never_loads_model(self):
        with patch.object(voice,'get_engine') as engine:
            with self.assertRaises(ValueError):voice.synthesize('  ')
        engine.assert_not_called()
        self.assertEqual(voice.split_sentences('One story. Another journey!'),['One story.','Another journey!'])

    def test_unpinned_engine_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'backend/services';folder.mkdir(parents=True)
            (folder/'tts_backend.py').touch()
            with patch.dict(os.environ,{'VOICESTUDIO_SOURCE':tmp}),patch.object(voice.subprocess,'check_output',return_value='changed\n'):
                with self.assertRaisesRegex(RuntimeError,'revision'):voice.source_path()

    def test_selected_voice_passes_delivery_and_exact_file_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'purakau-review.mp4';video.write_bytes(b'video-and-new-voice'*10000)
            digest=hashlib.sha256(video.read_bytes()).hexdigest()
            proposal=finalize_proposal.build_proposal({'story_id':'mataora-niwareka-moko',
                'video_sha256':digest,'title':'Mataora and Niwareka','sources':['https://teara.govt.nz'],
                'narrator':voice.VOICE,'style':cinematic_assets.STYLE,'bytes':video.stat().st_size})
            telegram_send.verify_review(proposal,video)
            approve_publish.validate_original_file(proposal,video)
            proposal['narrator']='voicestudio:kittentts:expr-voice-3-f'
            with self.assertRaisesRegex(ValueError,'narrator'):telegram_send.verify_review(proposal,video)
            with self.assertRaisesRegex(ValueError,'narrator'):approve_publish.validate_original_file(proposal,video)
