"""Offline tests: never call OpenAI, WhatsApp, GitHub or Buffer."""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import prepare_story
import finalize_proposal
import whatsapp_send
import approval_webhook
import approve_publish


def example_story(topic):
    sentences=[
        "Long ago, people shared a story of the world and the atua who shaped it with care.",
        "An important visitor searched for the origin of the gift that changed many lives.",
        "The visitor asked questions and received a gift that carried great responsibility.",
        "A surprising choice created difficulty, and the answer was not immediately clear.",
        "The characters responded to the challenge in different ways, each with consequences.",
        "Suddenly the natural world changed, and the visitor faced unexpected danger.",
        "Help arrived as the land, water, winds, and living things became part of the tale.",
        "In one telling of this story, people remember the gift and the lesson it carries.",
    ]
    return [
        {"title":f"NEW BEAT {i+1}","caption":f"ORIGINAL SCENE {i+1}",
         "narration":sentence}
        for i,sentence in enumerate(sentences)
    ]


class StoryGenerationSafety(unittest.TestCase):
    def test_only_grounded_topics(self):
        data=prepare_story.source_briefs()
        self.assertGreaterEqual(len(data["topics"]),2)
        ids=[t["id"] for t in data["topics"]]
        self.assertNotIn("tane-nz",ids)
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(all(x["sources"] and x["facts"] for x in data["topics"]))

    def test_no_unbounded_story_generation_or_automatic_repeat(self):
        topics=prepare_story.source_briefs()["topics"]
        first=prepare_story.next_topic([])["id"]
        second=prepare_story.next_topic([first])["id"]
        self.assertNotEqual(first,second)
        with self.assertRaisesRegex(RuntimeError,"already been proposed"):
            prepare_story.next_topic([t["id"] for t in topics])

    def test_generated_story_only_reuses_authorized_visual_cues(self):
        topic=prepare_story.next_topic([])
        data=prepare_story.build_candidate(topic,example_story(topic))
        self.assertEqual(len(data["scenes"]),8)
        self.assertEqual([s["visual"] for s in data["scenes"]],topic["visuals"])
        self.assertEqual([s["action"] for s in data["scenes"]],topic["actions"])
        self.assertEqual(data["narrator"],"en-GB-RyanNeural")
        self.assertEqual(data["review_status"],"pending-human-approval")

    def test_invalid_scene_count_and_repeat_are_rejected(self):
        topic=prepare_story.next_topic([])
        with self.assertRaisesRegex(ValueError,"exactly eight"):
            prepare_story.validate_script(topic,example_story(topic)[:7])
        scenes=example_story(topic)
        scenes[2]["title"]=scenes[0]["title"]
        with self.assertRaisesRegex(ValueError,"repeated"):
            prepare_story.validate_script(topic,scenes)

    def test_no_openai_key_no_generation(self):
        with patch.dict(os.environ,{"OPENAI_API_KEY":""}):
            with self.assertRaisesRegex(RuntimeError,"OPENAI_API_KEY missing"):
                prepare_story.generate_script(prepare_story.next_topic([]))


class WhatsAppDeliverySafety(unittest.TestCase):
    def test_video_template_and_two_real_quick_reply_buttons(self):
        meta={
            "proposal_id":"auto-review-maui-mahuika-fire-"+"a"*12,
            "title":"Māui and Mahuika",
            "video_url":"https://github.com/fanisswag654/claystory-ai/releases/"
                        "download/auto-review-maui-mahuika-fire-"+("a"*12)+
                        "/purakau-review.mp4",
        }
        message=whatsapp_send.template_payload(meta,"64212345678","purakau_review_video_v1")
        self.assertEqual(message["type"],"template")
        components=message["template"]["components"]
        self.assertEqual(components[0]["parameters"][0]["type"],"video")
        self.assertEqual(components[2]["parameters"][0]["payload"]["payload"].split(":")[0],"approve")
        self.assertEqual(components[3]["parameters"][0]["payload"]["payload"].split(":")[0],"reject")

    def test_bad_destination_or_video_url_cannot_be_sent(self):
        meta={"proposal_id":"auto-review-test-"+("a"*12),"title":"Test",
              "video_url":"https://attacker.test/video.mp4"}
        with self.assertRaisesRegex(ValueError,"not the approved"):
            whatsapp_send.template_payload(meta,"64212345678","purakau_review_video_v1")
        with self.assertRaisesRegex(ValueError,"E.164"):
            whatsapp_send.template_payload(meta,"not-a-phone","purakau_review_video_v1")


class AuthenticatedWebhookSafety(unittest.TestCase):
    def test_invalid_webhook_signature_and_header_refused(self):
        body=b'{"entry":[]}'
        signature="sha256="+hmac.new(b"secret",body,hashlib.sha256).hexdigest()
        self.assertTrue(approval_webhook.verify_meta(body,signature,"secret"))
        self.assertFalse(approval_webhook.verify_meta(body+b"X",signature,"secret"))
        self.assertFalse(approval_webhook.verify_meta(body,signature,"wrong"))
        self.assertFalse(approval_webhook.verify_meta(body,"","secret"))

    def test_only_authorized_approver_and_real_button_response(self):
        tag="auto-review-maui-mahuika-fire-"+("a"*12)
        payload={"entry":[{"changes":[{"value":{
            "metadata":{"phone_number_id":"111222"},
            "messages":[{
                "from":"64212345678",
                "id":"wamid.HBgNAValidMessageId123=",
                "button":{"payload":"approve:"+tag},
            }]
        }}]}]}
        found=approval_webhook.parse_actions(payload,"64212345678","111222")
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["decision"],"approved")
        self.assertEqual(approval_webhook.parse_actions(payload,"64219998888","111222"),[])
        self.assertEqual(approval_webhook.parse_actions(payload,"64212345678","other"),[])

    def test_unverified_meta_webhook_cannot_dispatch(self):
        client=approval_webhook.app.test_client()
        with patch.dict(os.environ,{"WHATSAPP_APP_SECRET":"abc","WHATSAPP_APPROVER_NUMBER":"64212345678"}), \
             patch.object(approval_webhook,"dispatch_github") as dispatch:
            response=client.post("/webhook/whatsapp",json={"entry":[]})
            self.assertEqual(response.status_code,403)
            dispatch.assert_not_called()


class SignedApprovalSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.file=self.folder/"purakau-review.mp4"
        self.file.write_bytes(b"original-video-frames-with-cinematic-voice")
        self.sha=hashlib.sha256(self.file.read_bytes()).hexdigest()
        self.tag="auto-review-maui-mahuika-fire-"+self.sha[:12]
        self.proposal={
            "proposal_id":self.tag,"video_sha256":self.sha,
            "video_url":f"https://github.com/fanisswag654/claystory-ai/releases/download/{self.tag}/purakau-review.mp4",
            "status":"pending","title":"Māui and Mahuika","story_id":"maui-mahuika-fire",
            "narrator":"en-GB-RyanNeural",
            "sources":[{"url":"https://teara.govt.nz/en/1966/maui-legends-of/page-5"}],
            "created_at":datetime.now(timezone.utc).isoformat()
        }
        self.secret="unit-test-signing-key"
        self.now=int(time.time())

    def receipt(self,decision="approved"):
        mid="wamid.HBgNAValidMessageId123="
        core=approve_publish.canonical_receipt(
            self.tag,decision,mid,self.sha,self.now
        )
        return {"proposal_id":self.tag,"decision":decision,
                "whatsapp_message_id":mid,
                "video_sha256":self.sha,"issued_at":self.now,
                "signature":hmac.new(self.secret.encode(),core,hashlib.sha256).hexdigest()}

    def test_valid_signed_decision_and_tamper_detection(self):
        review=self.receipt()
        approve_publish.verify_decision(review,self.proposal,self.secret,self.now)
        review["decision"]="rejected"
        with self.assertRaisesRegex(ValueError,"not authenticated"):
            approve_publish.verify_decision(review,self.proposal,self.secret,self.now)

    def test_expired_whatsapp_decision_cannot_publish(self):
        with self.assertRaisesRegex(ValueError,"expired"):
            approve_publish.verify_decision(
                self.receipt(),self.proposal,self.secret,self.now+601
            )

    def test_video_must_be_identical_to_reviewed_sha(self):
        approve_publish.validate_original_file(self.proposal,self.file)
        self.file.write_bytes(b"modified-frames")
        with self.assertRaisesRegex(ValueError,"differs from WhatsApp"):
            approve_publish.validate_original_file(self.proposal,self.file)

    def test_reject_never_touches_buffer(self):
        with patch.object(approve_publish,"REVIEW",self.folder), \
             patch.dict(os.environ,{"PURAKAU_APPROVAL_SIGNING_KEY":self.secret}), \
             patch.object(approve_publish,"submit_approved") as upload:
            history=approve_publish.process(self.receipt("rejected"),self.proposal,{})
            self.assertEqual(history["review:"+self.tag]["decision"],"rejected")
            upload.assert_not_called()

    def test_no_reply_cannot_publish(self):
        with self.assertRaisesRegex(ValueError,"explicit"):
            approve_publish.verify_decision({
                "proposal_id":self.tag,"decision":"pending","video_sha256":self.sha
            },self.proposal,self.secret,self.now)

    def test_final_proposal_link_is_bound_to_video_sha(self):
        meta={"story_id":"maui-mahuika-fire","video_sha256":self.sha,
              "title":"Māui and Mahuika","sources":self.proposal["sources"],
              "narrator":"en-GB-RyanNeural","bytes":len(self.file.read_bytes())}
        candidate=finalize_proposal.build_proposal(meta)
        self.assertEqual(candidate["proposal_id"],self.tag)
        self.assertEqual(candidate["status"],"pending")
        self.assertNotIn("approved",candidate["status"])


if __name__=="__main__":
    unittest.main()
