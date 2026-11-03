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

## Portrait and subtitle revision — 4 November 2026

The owner reported a visibly squashed player view. The previous check only
required encoded width/height; it did not require explicit sample/display
aspect metadata. The previous H.264 stream had no VUI aspect-ratio field.
The revised pipeline now requires square pixels (`1:1` SAR), explicit `9:16`
DAR and no rotation dependency, in addition to 1080×1920. It normalizes the
base clip's H.264 and MP4 display metadata, uses only proportional portrait
crops, and writes explicit aspect metadata again in the final export.
Telegram receives a fresh upload with width/height explicitly supplied.

The new edit contains **24 shots**: wide, medium and closer framing of each
of the eight existing source illustrations. It preserves every narration
frame, with 16 internal cuts and the seven existing scene dissolves. Captions
are now 67 groups of at most three words, in a larger 64px font within the
existing lower safe area. Original artwork, character motion and parallax
are retained.

The exact previous Bruno narration and forest sound mix were copied from the
pinned source film, with an exact script/source check before audio reuse.
Decoded audio SHA-256 is identical before and after the edit:
`7a1cc87a2484cd4c74e0b7a93a56af49aa4530832553649f888e19309d666621`.

Verified result:

- Render/review run `41733993331` succeeded. The setup delay cleared before
  the conditional retry ran; retry controller `41735328439` therefore did
  not cancel the original job or start a duplicate. Future setup commands
  have separate labels and bounded network waits.
- Release `auto-review-rata-and-the-tree-ec20fc790e23`.
- MP4 SHA-256 `ec20fc790e2356346f6e545c7c5b12656c32b4164430ba8871a91665acb1cd4d`.
- 79.951 seconds, 17,926,632 bytes, 1080×1920, square pixels, 9:16 display,
  30fps H.264/AAC. Full decode, 24-shot clock, 67 caption groups (max 3 words),
  audio level and movement checks passed. Visual contact-sheet review showed
  normal portrait proportions and the intended wider/closer reframing.
- Telegram confirmed fresh review message **26**, 1080×1920 video and both
  exact Approve/Reject callbacks. Receipt and quality report are release assets.
- All 93 offline tests passed in CI, including a real H.264 fixture that has
  9:16 pixel dimensions but incorrectly displays square. Fixing its aspect
  metadata is verified not to alter its decoded pixels.
- The earlier `1c138cc61edc` film was rejected by the owner and is now marked
  superseded. The new `ec20fc790e23` film had no publishing decision at final
  verification. Actual Instagram publishing still requires the owner's new
  Telegram approval. No test approval was submitted.
