# Example 09: a story scene with talking characters

A 14-second scene made with the character kit: a child walks in, points at a crow and says a line; the crow laughs and answers. It is one animation rendered in two looks, paper cut-out and anime, from the same scene file.

## What is in this folder

| File | What it is |
|---|---|
| [BRIEF.md](BRIEF.md) | The brief, exactly as it was written. Copy this. |
| [scene.json](scene.json) | The scene: cast, tracks, backdrop, captions. Works in any skin |
| [words.json](words.json) | The word timestamps for the two spoken lines, in the format `npx hyperframes transcribe` writes. The mouth tracks come from this file, so the example needs no audio and no network to build |
| [make_standin_voice.py](make_standin_voice.py) | Makes a buzz that follows the word timings, so the render has sound to measure. It is not speech: record your own voice and replace it |

## Make it

```bash
cd examples/09-story-characters
python3 ../../plugin/skills/brief2mp4/scripts/character_project.py --scene scene.json --skin paper-cutout --out ../../.tmp/ex09-paper
python3 ../../plugin/skills/brief2mp4/scripts/character_project.py --scene scene.json --skin cel-shaded --out ../../.tmp/ex09-anime
python3 make_standin_voice.py words.json voice.wav 14
for look in paper anime; do
  (cd ../../.tmp/ex09-$look && npx hyperframes render . -o raw.mp4 --quality delivery --fps 30)
  bash ../../plugin/skills/brief2mp4/scripts/finish.sh --in ../../.tmp/ex09-$look/raw.mp4 --out ../../.tmp/ex09-$look.mp4 --seconds 14 --audio voice.wav
  bash ../../plugin/skills/brief2mp4/scripts/check_delivery.sh ../../.tmp/ex09-$look.mp4 --seconds 14
done
```

The first build needs the network once for GSAP. Then check the mouth: pull four frames from the first line (`scripts/contact_sheet.sh final.mp4 --at 3.9,4.6,5.4,8.0`) and look at the speaker's mouth; it should show at least three different shapes, and be closed between "crow," and "that".

## Make your own version

Change the cast (`"character": "adult"` or `"tomato"`), the words (record a line, run `npx hyperframes transcribe`, point `visemesFrom` at the new file) or the skin. To use your own art, rig it as part images (`characters/README-CHARACTERS.md`, "Bring your own art") and give the scene its `character` id.
