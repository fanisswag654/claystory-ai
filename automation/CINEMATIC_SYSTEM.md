# Pūrākau Pixels — current cinematic system

Default: eight detailed stills, sixteen shots, portrait 1080p, fresh en-US-ChristopherNeural speech at natural pitch, captions and separately generated original sound effects.

Run **Pūrākau Pixels — cinematic stills and Christopher to Telegram** in GitHub Actions. It uses curated scripts and Edge TTS; no OpenAI API key is read. The current installed image collection is `maui-mahuika-fire`.

The workflow verifies the private recipient and the exact @purakaupixel Buffer channel, renders the movie, creates a SHA-bound review release, and sends the actual MP4 with **Approve for Instagram** and **Reject video** buttons. It never creates a Buffer post. Only the separate decision workflow can submit the exact reviewed movie after authenticating the fresh HMAC receipt, Telegram owner/chat, approved style and narrator, immutable release URL and full file checksum. Duplicate video bytes are blocked. A Buffer acceptance is not proof of Instagram delivery.

The existing scheduled workflow delegates to the same renderer. Its schedule remains gated by PURAKAU_TELEGRAM_ENABLED; this integration does not enable that variable. Manual runs are available.

## Preparing another story

Prepare eight consistent cinematic images in ChatGPT, install them under `automation/art/STORY-ID/scene-01.jpg` through `scene-08.jpg`, and add their SHA-256 values to `automation/cinematic-system.json`. Use a story ID from the curated collection. Missing or changed artwork stops the workflow before voice generation. The system never substitutes unrelated images.

ChatGPT image generation is used to prepare assets here. GitHub Actions does not have access to that image-generation session or an unlimited free image API. New stories require their artwork prepared before running; existing images can be reused automatically.

Preview-only buttons in the older free preview workflow remain preview-only. Use the cinematic approval workflow when Instagram approval buttons are needed.
