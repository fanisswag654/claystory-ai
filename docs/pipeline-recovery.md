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

## Verified result — 4 November 2026 (NZ time)

- The upgraded render in Actions run `41728120929` completed successfully;
  its final step caught Telegram's missing/incorrect inferred display metadata.
  The full film had already passed decoding and content-clock checks. The
  renderer was not run again to repair delivery.
- Explicit `width=1080` and `height=1920` now accompany uploads. An accepted
  upload's public-safe message ID and returned dimensions are checkpointed
  **before** validation, so a validation failure cannot hide a sent message.
- Recovery run `41732435541` succeeded. It updated the known Rātā review
  message **23** in `@purakau_bot` with the new exact film, confirmed both
  callback buttons, then downloaded Telegram's stored original and matched its
  SHA-256 to the source MP4. A fresh reply notification points to that review.
- Release: `auto-review-rata-and-the-tree-1c138cc61edc`.
  SHA-256: `1c138cc61edcf10ccc6d9fb9046d609beefdbb1d188976ffe717c77eda34618b`.
  `telegram-delivery.json`, `quality-report.json`, captions and motion evidence
  are attached to that release. The film is 79.951 seconds, 1080×1920, 30fps,
  H.264/AAC, with 36 caption segments and seven narration-aligned dissolves.
- All eight scenes have authored movement evidence and distinct sampled video
  frames. The 89 local tests passed, including preserving upload evidence when
  Telegram returns bad dimensions. Existing approval and browser checks pass.
- Render deploy `dep-dbl64cnb9u1s739g9s3g` is live for source commit `06b23b5`.
  The callback is registered, the private reviewer matches, there were zero
  pending webhook updates, and unsigned callback requests returned HTTP 403.
- No production approval was forged or submitted. The publication ledger had
  no entry for this new film at verification. Actual Instagram publication is
  intentionally awaiting the owner's real Telegram approval, not exercised
  as a test. The reason the earlier message was not visible on the user's
  device remains unconfirmed; the earlier API receipt did confirm delivery.

The recovery workflow can re-validate an existing receipt without repeating
its delivery. Do not change its request casually or treat test fixtures as a
real Telegram approval. General scheduled story generation remains under its
existing enable switch; this recovery did not enable a new posting schedule.
