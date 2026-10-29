# Pūrākau Pixels — WhatsApp-approval automation (prototype, OFF until connected)

**Current status:** Source files and GitHub Actions workflows are in place;
automatic WhatsApp delivery and Instagram publication are intentionally
**DISABLED** by default. The owner must first set up WhatsApp Business, choose
a Render workspace for the webhook, configure API secrets, test a real
Approve/Reject round trip, and turn on the repository variable
PURAKAU_AUTOMATION_ENABLED=true.

The project does not have a native personal WhatsApp connector. It uses the
official Meta WhatsApp Business Cloud API. Business-initiated outbound video
messages generally require a Meta-approved WhatsApp message template,
recipient opt-in, and may incur Meta messaging charges.

## Intended system

1. A scheduled GitHub Action runs once a week and chooses a **never-before-
   used** source-backed Māori story brief. The initial library includes four unique traditions: Māui/Mahuika
   (fire), Rūaumoko (earthquakes), Rātā and the forest tree, and Tāne's
   three kete. They are grounded in Te Ara, government education and DOC
   references. Previously animated Tāne and Māui/Giant Fish stories are not
   silently recycled.
2. An OpenAI API call writes **fresh, short English narration** based only
   on vetted plot facts, rather than inventing whakapapa or custom practices.
   Outputs are explicitly not authoritative. The model cannot supply new
   characters, rituals or visual cues. The story is not published by this step.
3. The established V31 Ryan cinematic narrator creates eight new scene
   clips. The V33 original procedural pixel-art actor system generates
   eight themed environments (e.g. fire, river, forest, storm or earth).
   Playwright and FFmpeg export one 540x960 MP4 with synchronized sound,
   measured clip timings, visual stills and a SHA-256 fingerprint.
4. The finished video is stored at a unique GitHub Releases URL as
   **review-only**. It is publicly accessible to anyone holding the URL:
   GitHub public Releases are not private storage. A WhatsApp video-header
   template sends the actual MP4 to the chosen reviewer number, with two
   quick-reply buttons: **Approve** and **Reject**.
5. A Render-hosted HTTPS webhook authenticates Meta's callback signature,
   the sending WhatsApp number, the business phone number ID and the exact
   proposal ID; then sends a separate HMAC-signed GitHub review event.
6. **Reject** saves a rejection record and makes no Buffer/Instagram calls.
   **Approve** verifies the HMAC, original release URL, exact video SHA-256,
   review expiry and recipient channel. Only then does the publisher send
   the unchanged film to **@purakaupixel** through the existing Buffer
   Instagram API and record the post ID to prevent duplicates.
7. **No response** means nothing is published. The next scheduled generation
   pauses while a review is still pending. The review expires after 14 days.
   A submitted Buffer post may report *scheduled*, not yet *sent*. Check
   the actual Instagram account before assuming publication.

**Important limitation:** The reusable pixel character system is an initial
auto-animation template, not an AI system that automatically creates
hand-painted bespoke characters for every Māori story. Each output must be
watched and approved for visual quality and cultural accuracy. To improve
the art further, add Pixelorama sprite packs by story/character type.

## Meta WhatsApp Business setup (user action required)

- Set up a Meta Developer app containing WhatsApp, a connected
  WhatsApp Business Account, and its registered business phone number.
  Obtain the **permanent/system user access token** appropriate to your
  business (not a temporary test token) and its **Phone Number ID**.
- Explicitly opt in the reviewer WhatsApp number. Store its international
  digits (for example a New Zealand number begins with 64, without a +).
- Create and have Meta **approve** a template named
  purakau_review_video_v1, language en_US, with:

  **HEADER:** VIDEO (provide a sample review MP4 for Meta).
  
  **BODY:** New Pūrākau Pixels video: {{1}}. Review code: {{2}}.
  Watch the full animation, check te reo Māori pronunciation and cultural
  details, then choose Approve to post to Instagram or Reject to stop it.
  
  **FOOTER:** Approval is required before Instagram publication.
  
  **BUTTON 0:** QUICK_REPLY, text "Approve".
  
  **BUTTON 1:** QUICK_REPLY, text "Reject".

  The action will supply the actual video URL and variable parameters,
  including a unique quick-reply payload for each proposal.
  Meta may classify this as marketing and charge accordingly. The exact
  template name, language, structure, video URL/format and opt-in must match
  Meta's approved configuration. WhatsApp messaging limits apply: the
  renderer refuses review MP4s above ~15 MiB.
- Configure a **webhook callback URL**:
  https://YOUR-RENDER-SERVICE.onrender.com/webhook/whatsapp
  and subscribe to WhatsApp **messages** events. Use the same randomly
  generated WHATSAPP_VERIFY_TOKEN on Render and the Meta verification page.

## Render deployment (requires user's selected workspace)

The connected Render account currently has a workspace named **My Workspace**,
but an assistant must obtain user confirmation before creating a service.

Suggested webhook service settings:
- Repo: https://github.com/fanisswag654/claystory-ai
- Runtime: Python 3
- Service: claystory-whatsapp-approval
- Build: pip install -r automation/requirements-webhook.txt
- Start: gunicorn --bind 0.0.0.0:$PORT automation.approval_webhook:app
- Expose HTTPS URL from Render.

For time-sensitive WhatsApp webhooks, an always-on service is more reliable.
Free hosted services may spin down and delay or miss the response window.

Configure these secrets **inside Render** (never in chat or Git source):
- WHATSAPP_APP_SECRET — from your Meta developer app.
- WHATSAPP_VERIFY_TOKEN — random secret chosen for webhook verification.
- WHATSAPP_APPROVER_NUMBER — your WhatsApp number in E.164 digits.
- WHATSAPP_PHONE_NUMBER_ID — same business phone number ID as in GitHub.
- GITHUB_REVIEW_DISPATCH_TOKEN — fine-grained token with Contents
  read/write restricted to this repository (needed for repository_dispatch).
- PURAKAU_APPROVAL_SIGNING_KEY — long random signing secret shared ONLY
  between Render and GitHub Actions; used to certify the approval result.

The Render POST endpoint rejects all unknown senders, invalid Meta signatures,
wrong phone-number IDs, invalid button payloads and unknown video tags.
It does not send any Instagram messages directly.

## GitHub Actions secrets and settings

Under the ClayStory repository's **Settings > Secrets and variables >
Actions > Secrets**, set:
- OPENAI_API_KEY — separate, usage-billed OpenAI API key for fresh scripts.
- WHATSAPP_ACCESS_TOKEN — Meta WhatsApp Cloud API permanent token.
- WHATSAPP_PHONE_NUMBER_ID — WhatsApp Business phone number ID.
- WHATSAPP_REVIEW_TO — your international WhatsApp mobile digits.
- PURAKAU_APPROVAL_SIGNING_KEY — EXACT same random value stored on Render.
- BUFFER_API_KEY and INSTAGRAM_CHANNEL_ID — existing working Instagram
  secrets can be reused. Never paste tokens into chat.

Under **Actions > Variables**, set:
- WHATSAPP_REVIEW_TEMPLATE=purakau_review_video_v1 (optional default).
- PURAKAU_OPENAI_MODEL=gpt-5-mini (optional default; must be available to
  your OpenAI API account).
- PURAKAU_AUTOMATION_ENABLED=false until the webhook and templates are
  tested. **Only turn true after the real approval round-trip passes.**

OpenAI API usage is billed separately from ChatGPT subscriptions.
GitHub Actions, Render and Meta also have their own usage limits and
potential charges.

## Repository components

- automation/story_briefs.json: public source/fact/scene library.
- automation/prepare_story.py: structured API generation, local validation
  and no-repeat selection.
- automation/scene_stage.js and automation/review.html: original pixel
  visual stage for new themes and V33 articulated actors.
- automation/make_audio.py and automation/render_candidate.py:
  cinematic narration, foley, 24fps MP4 and SHA validation.
- automation/finalize_proposal.py and automation/whatsapp_send.py:
  reviewed Release URL and approved WhatsApp video template.
- automation/approval_webhook.py: Render Flask app verifying sender and Meta
  signature, signing receipt and dispatching GitHub decision.
- automation/approve_publish.py: isolated SHA-validated Buffer publisher.
- .github/workflows/auto-purakau-review.yml: weekly generator and review send;
  disabled until PURAKAU_AUTOMATION_ENABLED=true.
- .github/workflows/auto-purakau-decision.yml: ONLY signed decisions can
  trigger Buffer publication; same global kill switch.
- .github/workflows/auto-purakau-tests.yml: offline Python and live Chromium
  checks, requiring NO WhatsApp/OpenAI/Buffer credentials.

## Safety, failure modes and next stages

- Each story must be a new, source-backed **retelling**, not fabricated
  mythology. There is no claim that one iwi's account represents all iwi.
- A user should inspect the script, pronunciation, imagery, caption and
  culturally sensitive details in the video before approving.
- Four curated briefs are available initially. After all four have been
  proposed, generation stops instead of recycling or inventing lore.
  Add more fact-checked source briefs over time for sustainable automation.
- Never mix an Instagram authorization into the OpenAI story-generation
  stage; approvals are separate and cryptographically validated.
- No WhatsApp delivery confirmation implies Instagram permission.
- Don't enable the weekly schedule until testing the actual WhatsApp
  delivery, button callback and GitHub receipt. Initial testing can
  occur by manually triggering the creation workflow AFTER setup.
- Current automatic artwork reuses a procedural V33 rig. Better bespoke
  art requires another character-asset production phase.
