# ClayStory AI → Instagram Reels

This repository creates the original Pūrākau Pixels animations. The Instagram
workflow uses the **finished film MP4 files** already rendered by this repo, not
the TikTok clip-farmer.

## How it works

1. `.github/workflows/narration.yml` generates narration and deploys two
   portrait animated films (with captions and original sound) to GitHub Pages.
2. `.github/workflows/instagram-reels.yml` checks ClayStory's committed film source and soundtrack daily.
3. `scripts/instagram_reels.py` fingerprints each story's artwork code and audio. For each new version, it renders the portrait MP4 directly using `scripts/render_films.py --story <name> --mix balanced`, validates the Reel's duration, aspect ratio, FPS and audio, and hosts the film as a versioned public GitHub Release asset. This avoids GitHub Pages video URL 404s.
4. If enabled, the workflow sends **one new Reel per day** to the selected
   **Instagram** Buffer channel. Buffer schedules it into the posting queue.
   It never uses the TikTok channel or the old clip-farmer repository.
5. Posting history is saved in the dedicated `instagram-publish-history`
   branch. A successful draft test does not block subsequently scheduling
   that same film as a Reel.

**Available original films today:** Māui and the Great Fish and Māui and the
Sun. After these two have been scheduled, daily checks find no new films and
do **not** recycle the same content. Creating additional illustrated stories
requires adding and rendering additional stories in ClayStory; this workflow
does not invent culturally sensitive pūrākau automatically.

## Required Instagram setup

- Instagram must be a **Professional (Creator or Business)** account for
  automatic publishing through Buffer. Personal accounts require manual
  notification publishing.
- Connect **@purakaupixel** to Buffer via
  https://publish.buffer.com/channels . Confirm its Buffer queue is not paused.
- In this repository's **Settings → Secrets and variables → Actions → Secrets**,
  add `BUFFER_API_KEY` using the key already available in your Buffer account.
  GitHub secrets do **not** transfer automatically between repositories.
  Never paste a secret into source code, issues, chat, or workflow inputs.
- The Instagram account is already locked to **@purakaupixel** in the workflow;
  there is no need to add a username variable. The code checks both the
  platform and matching handle before creating any Instagram post.
  If Buffer cannot match the account by its display name, we can add
  `INSTAGRAM_CHANNEL_ID` as an Actions secret after confirming its ID.
- Automatic queueing is now enabled by default following approval of the first
  Instagram test draft. An Actions variable `IG_AUTO_PUBLISH=false` immediately
  disables new automatic scheduling on subsequent runs. The scheduled workflow
  targets only @purakaupixel, with a limit of one newly scheduled film per day.
  Check each film's cultural accuracy and narration before or after scheduling;
  publishing queued posts remains subject to Buffer's posting schedule.

## Test safely on iPad

Open the [Instagram Reels workflow](https://github.com/fanisswag654/claystory-ai/actions/workflows/instagram-reels.yml).

1. Tap **Run workflow**, leave `mode=check`, and run. The workflow renders and publicly hosts a versioned MP4 using the repository's GitHub Actions token, without using Buffer or publishing to Instagram.
2. Once Buffer and Instagram are connected, run `mode=draft`. Confirm the
   original video appears under **Buffer → Instagram → Drafts**.
3. Following approval of the first test draft, the workflow queues the first
   unscheduled film during its next daily run, unless `IG_AUTO_PUBLISH=false`
   has been set. If you want to queue it immediately instead, choose `mode=queue`
   in a manual workflow run. Buffer determines the public publishing time.
4. A queued film that already has a matching Buffer draft is promoted to the
   queue rather than creating a second copy; other newly rendered films receive
   their own queue posts. Existing history prevents resubmission on later runs.

Current daily cron: `20:30 UTC` (9:30am NZ daylight time / 8:30am NZ standard
time). Buffer decides the actual publication time from the Instagram channel's
queue schedule.

## Important quality and hosting notes

- Media are served from immutable, versioned **public GitHub Releases** in the ClayStory repo. The workflow creates the MP4 when needed, checks that it is downloadable and reuses unchanged assets. GitHub Pages remains useful for the site but is not needed to deliver Instagram videos.
- On the very first draft test, rendering and hosting the original film can take substantially longer than checking an existing release. This does not publish to Instagram.
- Review AI-generated pronunciations of te reo Māori and the chosen telling of
  each pūrākau with an appropriate fluent reviewer before allowing unattended
  posting.
- Reels use 9:16 MP4 with an audio track, supported frame rate and acceptable
  length; validation fails instead of queuing noncompliant media.
- Buffer may switch to notification publishing if account or media requirements
  are not met. Check the actual post status in Buffer; a queued API success
  does not itself prove that Instagram posted it.
- To stop automatic submissions immediately, set `IG_AUTO_PUBLISH=false`
  under repository Actions variables, or disable the Instagram workflow in
  GitHub Actions. This does not cancel posts already queued in Buffer.
