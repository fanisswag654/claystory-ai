# FREE Pūrākau Pixels pixel animation — iPad setup

This separate workflow creates **brand-new** pixel-animated eight-scene Māori
pūrākau videos from four **original checked-in editorial scripts**, without
requesting or reading a paid OpenAI API key.

**Run it:** https://github.com/fanisswag654/claystory-ai/actions/workflows/free-curated-purakau.yml

## What works

- **Script source:** Original English narrations in `automation/curated_scripts.json`,
  grounded in `automation/story_briefs.json` and accompanied by links for review.
  These are *drafts*, not claims of cultural authority.
- **Animation:** Reuses the V33 pixel stage, varied characters and scene motion.
- **Male narrator:** Reuses the existing Ryan `en-GB-RyanNeural` voice through
  the free Edge TTS endpoint; no OpenAI API call. The service depends on
  outside network access and is not guaranteed to remain free/available.
- **Audio:** Original programmatically made environmental SFX plus narration,
  mixed with the existing audio ducking system; no copyrighted music.
- **Delivery:** Uploads the exact SHA-256-verified MP4 to your private
  Telegram account, alongside safe preview-only buttons.
- **Backup:** Saves a short-lived GitHub Actions artifact containing the
  MP4, approved editorial data, timing and manifest (three days).

## Run your first video on an iPad

1. Open the **Run it** link above while signed in as repository owner.
2. Choose **Run workflow**, keep branch `main`.
3. Pick one of four curated stories:
   - `maui-mahuika-fire` — Māui and Mahuika: The Secret of Fire
   - `ruaumoko-earthquakes` — Rūaumoko: The Earth Beneath Our Feet
   - `rata-and-the-tree` — Rātā and the Tree That Returned
   - `tane-three-kete` — Tāne and the Three Baskets of Knowledge
4. Tap the green **Run workflow** button.
5. Wait while GitHub generates scene-by-scene narration, background sounds
   and the 540 × 960 portrait animated MP4. This may take some time.
6. Open your Pūrākau Pixels Telegram bot and watch the film.
7. Check the Māori names, macrons, narrator pronunciation, imagery, facts,
   iwi variations and whether the story feels right before sharing anywhere.

The Telegram buttons are intentionally **Approve preview (NO POST)**
and **Reject preview**. They acknowledge your review inside Telegram but
**NEVER post to Instagram**. No live approval/rejection dispatch is created,
no GitHub Release is published, and the Instagram API/Buffer keys are not
available to this workflow. This is different from the real publishing flow.

## Requirements and cost

Already configured from the Telegram setup:

- GitHub repository secrets: `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_REVIEW_CHAT_ID`, `TELEGRAM_APPROVER_USER_ID`.
- Render webhook and the Telegram bot, already tested with `/check`.
- **No** `OPENAI_API_KEY`, Buffer key, Instagram channel ID, GitHub PAT,
  approval signing key or paid account is needed for this new preview workflow.

This path makes **zero paid OpenAI script-generation calls**. GitHub Actions
minutes/storage have plan-specific quotas and may incur charges beyond
included allowances. The free Edge voice endpoint is third-party and
may throttle or fail; retry if it has a temporary outage. For future
long-term reliable narration, we could use a locally hosted open-source
voice model rather than relying on Edge service availability.

## Safety and next stage

The production GitHub switch `PURAKAU_TELEGRAM_ENABLED` stays **unset/false**.
Do **not** turn it on merely to use this free preview workflow: the existing
production switch also enables the real Instagram publishing review gate.

The first free film is a **private preview**, not a published Reel. Once you
have watched and accepted the quality, we can separately design an
opt-in publishing workflow with final human approval and a weekly free
story rotation. Do not enable unattended publishing.

To edit original story narration, change `automation/curated_scripts.json`
using exactly eight scenes per story and maintain the word-length,
originality, source and cultural-review requirements. GitHub tests validate
all four scripts on each commit.

## Troubleshooting

- **Run workflow button missing:** Open the workflow under the repository
  Actions tab, confirm the workflow exists on `main`, and use Safari's
  desktop view if the mobile UI hides the button.
- **Missing secrets:** Confirm the private Telegram BotFather token and both
  numerical IDs in GitHub Actions secrets; do not paste secrets into chat.
- **Edge voice service failed:** The external free narration endpoint may
  be unavailable. No video is sent if voice generation fails.
- **Very long render / action timeout:** Open the workflow run and expand
  the audio/render step to see which stage stopped.
- **Failed verification or file >15 MiB:** Delivery stops rather than
  sending a wrong or truncated video. The artifact is saved only after
  successful delivery.

There are no background jobs from ChatGPT: each run is started manually in
GitHub Actions until you deliberately opt in to a scheduled workflow.
