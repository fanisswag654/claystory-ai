# Pūrākau Pixels — Tāne and the First Light

An original eight-scene Māori pūrākau film depicting one telling of the
separation of Ranginui and Papatūānuku. This is **new visual animation**,
not a reskin of the previous Māui film.

## Storyline

1. Before the light — Ranginui and Papatūānuku are together; darkness covers the world.
2. Their children — the atua wish to stretch and see the light.
3. A hard choice — Tāwhirimātea objects to separating his parents.
4. The first attempts — brothers cannot part the embrace.
5. Tāne's strength — Tāne lies on the earth and pushes against the sky with his feet.
6. Te Ao Mārama — the sky rises and light floods the new space.
7. Tāwhirimātea's storm — winds and rain surge through the world.
8. Life beneath the sky — plants, forests, and birds flourish under Ranginui.

The sky and earth are represented symbolically through animated landscapes,
celestial layers, growing trees and flowing light. Character art is original
procedural pixel art, without copied assets, borrowed game imagery or
pretending to reproduce any specific iwi carving patterns.

## V33 expressive character upgrade

Characters now have individually animated arms, hands, legs, expressive
faces with blinking eyes, layered costumes, and multiple action frames.
Tāne's sky-lifting scene shows him lying on the earth with bent knees,
pushing with both feet. Tāwhirimātea wears a separate storm-blue mantle
with a moving scarf. The browser and MP4 export sample identical poses
from the narration timeline.

See [V33_DETAILED_CHARACTERS.md](V33_DETAILED_CHARACTERS.md) for the full
art workflow, recommended sprite editors, and iPad review instructions.

## How it works

- Story and scene narration: `stories/tane.json`
- Responsive interactive scene-preview page: `tane.html`
- Full procedural 24fps pixel animation: `scripts/tane_animation.js`
- Cinematic Ryan narrator and original environmental foley:
  `scripts/tane_sound.py`
- Synchronized 9:16 H.264/AAC video export:
  `scripts/render_tane.py`
- Story and workflow tests: `scripts/test_tane_film.py`
- Complete automated film build:
  [Tāne and the First Light workflow](https://github.com/fanisswag654/claystory-ai/actions/workflows/tane-first-light.yml)

The voice uses **exactly the V31 cinematic en-GB-RyanNeural delivery profile**
approved for future films, including scene-dependent dramatic pauses and
pacing. Sound effects are newly synthesized in Python and mixed with
sidechain ducking below the speech, so this film gets its own atmospheric
darkness, wind, storm, earth movement and forest sounds.

## Watching on your iPad

1. Open the [Tāne film workflow](https://github.com/fanisswag654/claystory-ai/actions/workflows/tane-first-light.yml).
2. Open the latest run with a **green checkmark**. A green checkmark means
   all eight scenes were synthesized and the MP4 was successfully rendered.
3. Scroll to **Artifacts**, download **tane-first-light-review-film** and
   unzip it in the Files app.
4. Open **tane-nz-V33-detailed.mp4**. The folder also contains an
   enlarged **tane-v33-character-studies.png**, eight scene screenshots,
   voice-only narration, the finished sound mix, and source
   script/timing files.
5. Review the narration, Māori words, colors and interpretation before
   granting any permission to publish.

If the run is red, read the failure logs; a partially uploaded artifact
**does not** imply a finished movie. The build can be retried manually
without affecting any previously published videos.

## Cultural reference material

- [Te Ara: Ranginui — the sky](https://teara.govt.nz/en/ranginui-the-sky)
- [Ministry for the Environment: Te tīmatanga o te ao Māori](https://environment.govt.nz/te-ao-maori/te-timatanga-o-te-ao-maori/)
- [Mātauranga Māori: Tāwhirimātea](https://eng.mataurangamaori.tki.org.nz/Support-materials/Te-Reo-Maori/Maori-Myths-Legends-and-Contemporary-Stories/Tawhirimatea)

This is one version of the narrative. Traditions differ between iwi,
and artificial narration may mispronounce te reo Māori. A fluent-speaker
review should take place before public promotion.

## Publishing safety

No Buffer calls or Instagram auto-posting occur in this film workflow.
The `config/instagram-approved.json` allowlist is unchanged, so this
new movie is not authorized for Instagram. The workflow has read-only
repository permissions and uploads only a temporary GitHub Actions
review artifact. GitHub Actions artifacts in a public repository may
be visible to people who can access the repository.

Build outputs are ignored by Git to avoid accidental commits.
