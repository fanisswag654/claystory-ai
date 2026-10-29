# Pūrākau Pixels — Telegram approval bot setup (iPad)

**Status:** The source, GitHub Actions workflows, and Telegram HTTPS
webhook are implemented. GitHub automatic story generation and Instagram
publication stay **OFF** until owner setup and real end-to-end testing.

Telegram uses a normal personal Telegram account to **receive** MP4 videos
from a separate bot. No Meta WhatsApp Business Account, company
registration, Facebook business verification, or personal phone registration
as a business sender is required. Telegram's standard bot functions are
free, but OpenAI API generation is billed separately, and GitHub/Render
usage may have costs/limits.

## 1. Make the free Telegram bot (iPad)

1. Install Telegram from the App Store if necessary and sign in normally.
2. Open **https://t.me/BotFather** (official verified Telegram bot).
3. Tap **Start** and send **/newbot**.
4. Choose display name **Pūrākau Pixels Reviews**.
5. Choose an available username ending in **bot**, e.g. **PurakauPixelsReviewBot**.
6. BotFather sends a **bot access token**. This is like a password. Never
   paste it in ChatGPT, a screenshot, a GitHub commit, or a public URL.
   If exposed, send **/revoke** in BotFather to rotate it.

**Important:** The new bot is a sender to your personal account. You do
not need WhatsApp or Telegram Business. The bot cannot message you until
you open the bot's private chat and tap **Start**.

## 2. Enter the token safely in GitHub and Render

GitHub repository:
https://github.com/fanisswag654/claystory-ai/settings/secrets/actions

In **Repository secrets**, add:

- `TELEGRAM_BOT_TOKEN`: exact token BotFather gave you.
- `TELEGRAM_WEBHOOK_SECRET`: **new random 32–128 character** string with
  letters, digits, hyphens, underscores. Use a password generator.
  Do not use your BotFather token for this second secret.

Render dashboard:
https://dashboard.render.com/web/srv-dbhahoec6qcc73ervv20

Under **Environment**, add the **exact same two values**:
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`.
Choose **Save, deploy**. The already-connected service keeps its existing
Flask/Gunicorn settings, location and free plan.

This does not activate weekly stories and does not publish to Instagram.

## 3. Connect the bot to the existing Render webhook

Open the GitHub workflow:
https://github.com/fanisswag654/claystory-ai/actions/workflows/telegram-connect.yml

Tap **Run workflow**. When the run is green, it confirms the real BotFather
token and registers Telegram callbacks at:

`https://claystory-whatsapp-approval.onrender.com/webhook/telegram`

Even though the Render service's name includes "whatsapp" from the
previous prototype, this URL accepts *Telegram* bot callbacks securely.
The older Meta route is unused by Telegram workflows.

No token appears in logs, and this setup workflow never posts videos.

## 4. Obtain your own Telegram IDs without a third-party bot

In Telegram, open the new bot and tap **Start** (or send `/id`).
The secured Render bot replies privately with two numbers:

- **Telegram user ID** — your personal account identity.
- **Telegram private chat ID** — the conversation to receive MP4s.

You can then copy these numbers to **GitHub Actions → Repository Secrets**:

- `TELEGRAM_APPROVER_USER_ID`
- `TELEGRAM_REVIEW_CHAT_ID`

Set these same two numbers under **Render → Environment**. On an ordinary
personal bot chat, the numbers will normally be equal.

No one else can use their Telegram account to approve your videos: the
Render webhook and GitHub publication gate each independently verify
the configured IDs, webhook secret and exact video fingerprint.

## FREE curated original stories (NO OpenAI API key)

The owner can now create a **brand-new eight-scene pixel-animated film**
using four hand-written, source-backed scripts and the existing free
Ryan narrator/foley mixer.

On an iPad, open:
https://github.com/fanisswag654/claystory-ai/actions/workflows/free-curated-purakau.yml

Tap **Run workflow**, choose a story from the four options, then wait for
a new MP4 in your private Telegram bot chat. Preview-only buttons respond
inside Telegram, but **never** trigger Instagram or Buffer.

This uses **no OpenAI API script generation** and does not need the
production `PURAKAU_TELEGRAM_ENABLED` switch. Leave that switch OFF.
Free external Edge TTS still needs network access, and GitHub Actions
has platform/account usage quotas. Full details in
[FREE_CURATED_PURAKAU_SETUP.md](FREE_CURATED_PURAKAU_SETUP.md).

## 5. Connect the approval dispatch and Instagram gate (advanced)

Further secrets needed — **do not share them in chat**:

GitHub Actions:
- `PURAKAU_APPROVAL_SIGNING_KEY` (random 32+ characters)
- `OPENAI_API_KEY` (separately billed for generating story scripts)
- existing `BUFFER_API_KEY` and `INSTAGRAM_CHANNEL_ID` for @purakaupixel.

Render Environment:
- `PURAKAU_APPROVAL_SIGNING_KEY` (exactly same as GitHub)
- `GITHUB_REVIEW_DISPATCH_TOKEN`: a fine-grained GitHub token restricted
  to **fanisswag654/claystory-ai** with permission to create repository
  dispatch events; no full-access personal account token.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`,
  `TELEGRAM_APPROVER_USER_ID`, `TELEGRAM_REVIEW_CHAT_ID` from steps 2–4.

The Telegram webhook doesn't have credentials to call Buffer. It only
sends a *signed proposal* to the independent GitHub Actions verifier.
Only an authenticated **Approve** on that exact video can initiate a
Buffer post to @purakaupixel. Reject/no response = nothing posted.

## 6. Test a real video, THEN enable

- Offline tests: https://github.com/fanisswag654/claystory-ai/actions/workflows/auto-purakau-tests.yml
- Manual Telegram connection: https://github.com/fanisswag654/claystory-ai/actions/workflows/telegram-connect.yml
- Generate/preview/send: https://github.com/fanisswag654/claystory-ai/actions/workflows/auto-purakau-review.yml
- Signed approval/rejection: https://github.com/fanisswag654/claystory-ai/actions/workflows/auto-purakau-decision.yml

Before generating expensive stories, set `PURAKAU_TELEGRAM_ENABLED=true`
in **GitHub Actions → Variables** only *after* the Render bot, IDs,
dispatch signing keys, Telegram video send, OpenAI API and Buffer
secrets are configured and tested.

For now, leave that variable unset (or `false`). Nothing will be
scheduled, no surprise charges generated by story runs, and no
Instagram videos posted by the automatic pipeline.

To test after credentials are configured, run the generator manually
and select a source-backed topic. Open the MP4 Telegram sends you.
Tap **Reject** on the first test if you want to confirm no publishing.
Then create a separate candidate and use **Approve** when you are
ready to test actual Instagram publishing.

## Security and quality

- Actual video is sent to Telegram using sendVideo upload, with
  original MP4 SHA-256, rather than just a document link. The
  inline keyboard has Approve and Reject buttons.
- Only the intended private Telegram user/chat can authorize a post.
- The webhook uses `X-Telegram-Bot-Api-Secret-Token`; GitHub independently
  verifies a timestamped HMAC-signed decision.
- Video checksums, source provenance, narrator, approval expiration,
  prior decisions and duplicate Buffer history are checked again in
  the publishing workflow.
- An unapproved film can still be hosted as a public GitHub Release
  for review. Do not use this pipeline for private personal footage.
- New Māori pūrākau are generated from curated public-source briefs
  and **must be reviewed** for correct te reo and cultural context.
- The current storyboard artist uses a reusable V33 pixel-character
  system. Hand-painted unique characters are a separate future step.
