# Recovery and authored motion

The 3 November Rātā run 41556258597 completed at 01:18 UTC. Its logs report
Telegram message 23, and its released MP4 is 80.43 seconds, 1080×1920,
30fps H.264/AAC. Render serves the approval webhook; GitHub Actions renders
films. A crashed Work conversation does not by itself establish that either
external service stopped.

## Changes

- Preserve original eight source-backed Rātā scenes, Bruno voice, pronunciation
  text processing, soundtrack mixer, captions and approval signatures.
- Author compact regions for restrained breathing, head/hand sway and bird
  movement. Keep rigid region interiors and stationary unrelated scenery.
  These are 2.5D movements, not full-body acting, generated performance or lip sync.
- Upload animated image textures to the existing DepthFlow renderer; add an
  eased push-in to its existing continuous camera path. Keep proportional fit.
- Dissolve the first ten frames of each incoming scene from the outgoing
  final frame, preserving every narration boundary and total frame count.
- Preflight the actual bot, private reviewer, registered callback, Render
  readiness and rejection of unsigned requests. Never print credentials.
- Fully decode the completed video, check formats/clocks/audio level/captions,
  compare sampled frames in every scene, and record authored motion evidence.
- Validate Telegram's returned private chat, 1080×1920 video, caption identity
  and both exact review callbacks. Save a public-safe delivery receipt with the
  release and Actions artifact. A release without a receipt now fails clearly;
  the earlier workflow skipped delivery and reported success in that case.

## Review and recovery

Use the latest `telegram-delivery.json` for the actual message ID and exact
video SHA. A confirmed Telegram API delivery is not proof the user opened it.
`telegram-diagnostics.json` identifies the bot username and callback condition.
A network timeout after an upload is ambiguous: inspect the existing run and
chat before resending. Do not blindly rerun publishing or forge a review.

The standard workflow still requires the owner's real private Telegram button.
Render verifies its webhook token and owner identity; Actions independently
verifies HMAC, timestamp, original SHA, original source release and durable
publication history. Reject/no response cannot call Buffer. Never click or
simulate a production Approve callback as a connectivity test.

Run local checks with the existing test dependencies plus
`automation/requirements-motion.txt`, then `python -m unittest discover -s
automation -p 'test_*.py'`. OpenGL/model inference is checked by the small real
DepthFlow render in the production workflow before the full film begins.
