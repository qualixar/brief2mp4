---
name: brief2mp4
description: Turn a written brief into a finished, checked MP4 motion graphic. Use when asked to make an animation, motion graphic, kinetic typography, title sequence, logo sting, 3D scene, product turntable or short explainer clip as a video file. Builds with HyperFrames (HTML + GSAP), Three.js or Blender, finishes with ffmpeg, then checks the video against the brief and fixes what fails before handing it over.
---

# brief2mp4

A brief goes in. `final.mp4` comes out, and for every line of the brief you can point to the frame or the command output that shows the video meets it.

Work in this order every time: **spec, build, self-check, fix, deliver.** Do not skip the self-check. A render that finished is not a video that is right.

## 0. Before you start

Check the tools the job needs and say what is missing:

```bash
node -v            # 22 or newer (HyperFrames and Three.js paths)
ffmpeg -version    # every path
blender --version  # only for the Blender path
```

On macOS Blender is often not on the PATH: use `/Applications/Blender.app/Contents/MacOS/Blender`. If a tool is missing, tell the user the install command (`brew install node ffmpeg`, `brew install --cask blender`, or the Linux equivalent) and stop, unless the brief allows another tool.

Work inside one project folder. Never write outside it.

The scripts and templates named below sit next to this SKILL.md. Call them by their full path, for example `<this skill's folder>/scripts/finish.sh`; use the folder this SKILL.md was loaded from. A script install puts it in `~/.claude/skills/brief2mp4/` or `~/.codex/skills/brief2mp4/`; a plugin install puts it in the app's plugin cache.

## 1. Spec: write SPEC.md before any code

SPEC.md is the contract you will check against. It has six parts:

1. **Delivery**, as a table. If the brief is silent, use these defaults and say so:

   | Item | Default |
   |---|---|
   | File | `final.mp4` in the project root |
   | Frame | 1920x1080 (16:9). Vertical briefs: 1080x1920 |
   | Frame rate | 30 fps |
   | Duration | exactly what the brief says, to the frame |
   | Video | H.264, yuv420p |
   | Audio | AAC, 48 kHz, stereo, -14 LUFS integrated, true peak at or below -1 dBTP. Silent only if the brief says silent (still include a silent track) |

2. **Exact text.** Every word that appears on screen, copied character for character from the brief. Spelling, capitals and punctuation are part of the spec.
3. **Look.** Palette as hex codes, one or two typefaces, background, the mood in five words or fewer.
4. **Beat sheet.** Time ranges (`0.0-2.0 s`), what is on screen, what moves, and where the one hero moment lands. Something must be visible by 0.3 s. The final message holds for the last 1.5-2.5 s.
5. **Tool choice** (section 2) and one sentence on why.
6. **Done when.** One checklist line per requirement in the brief, each one checkable by a command or by looking at a named frame: "`final.mp4` is 12.0 s", "at 9.5 s the words FINISH SOMETHING TODAY are fully on screen, nothing cut off".

If the brief leaves a choice open, make it, write it under **Decisions** in SPEC.md, and continue. Ask the user only when the gap makes the video impossible.

A blank spec to copy is in `templates/SPEC.md`.

## 2. Pick the tool

| The brief asks for | Use | Reference |
|---|---|---|
| Type, layouts, UI, charts, icons, 2D shapes, captions | HyperFrames (HTML + CSS + GSAP) | `references/hyperframes.md` |
| Stylised 3D, particles, many objects, flying cameras | Three.js inside HyperFrames | `references/threejs.md` |
| Realistic products, materials, soft light and shadows | Blender, scripted with Python, run headless | `references/blender.md` |
| Joining clips, adding sound, exact duration, loudness, encoding | ffmpeg (`scripts/finish.sh`) | `references/ffmpeg.md` |

Mixing is normal: render a Blender shot to frames, then use it as a video layer under HyperFrames type, or join HyperFrames and Blender clips with ffmpeg. Every path ends with `scripts/finish.sh` and `scripts/check_delivery.sh`.

Starters that already render: `templates/threejs/index.html` and `templates/blender/scene.py`. Copy one into the project and change it, rather than starting from an empty file.

## 3. Build

Rules for every tool:

- **The picture is a pure function of time.** No wall clock, no `Math.random()` (use a seeded generator), no network calls while rendering. Render the same frame twice and you must get the same pixels.
- **Every element has a job in the beat sheet.** If you cannot say which beat it serves, cut it.
- **Text is readable.** Body text at least 40 px tall at 1080p, headlines 90 px or more. Keep 5% safe margins (96 px left and right, 54 px top and bottom at 1920x1080). No text touches or crosses the frame edge. Hold any line on screen for at least (words / 3) + 0.5 seconds.
- **Motion is eased.** Use ease-out for things arriving and ease-in for things leaving; linear only for constant spins and turntables. Most UI moves take 0.3-0.8 s. One clear hero moment beats ten small effects.
- **Draft small first.** Render 2-3 seconds at draft quality, look at it, then build the rest.
- **Edit files with your file-editing tool, not `sed -i`.** `sed -i` behaves differently on macOS and Linux and can fail silently; if an edit did not apply, the next render shows the old file.

## 4. Self-check: look before you say done

After every full render, do all three:

1. **Measure.** `scripts/check_delivery.sh final.mp4 --seconds <N> [--size WxH] [--fps N] [--silent-ok]` must end with `RESULT: PASS`. A FAIL is a fix, not a footnote.
2. **Look.** `scripts/contact_sheet.sh final.mp4 --at <beat starts, hero moment, last second>` writes one PNG per moment. Open and view each image. For every frame ask: is the text spelled exactly as the spec says? Is anything cut off or overlapping? Are the colours from the palette? Is the beat that should be on screen at this time actually there?
3. **Walk the list.** Go through **Done when** line by line and mark each **met** or **not met**, with the evidence: the command output line, or the frame file name.

If you cannot view images in this environment, say so plainly in the report. Never claim a visual check you did not do.

## 5. Fix

Fix the worst miss first, re-render, and run section 4 again. To save time, re-render only what changed where the tool allows it (`hyperframes render --start/--end`, a Blender frame range). Stop after three fix rounds; if something still fails, deliver and list it honestly.

## 6. Deliver

- `final.mp4` in the project root.
- `REPORT.md`: the Done-when list with met / not met and evidence, the render settings you used, render time, and anything still open.
- In chat: the path, the duration, one line on what is in it, and any open issue. Keep it short.

## Render settings

| Path | While iterating | Final |
|---|---|---|
| HyperFrames | `npx hyperframes render . -o draft.mp4 --quality draft --workers 4` | `npx hyperframes render . -o render.mp4 --quality delivery --fps 30` |
| Three.js (in HyperFrames) | same as above; renderer pixel ratio 1, `preserveDrawingBuffer: true` | same as above |
| Blender | `--preview` (3 stills) with EEVEE, 16-32 samples | EEVEE 32-64 samples; Cycles 64-128 with denoising only when the brief asks for realism. Render PNG frames |
| ffmpeg finish | n/a | `scripts/finish.sh`: H.264 CRF 18 preset slow, yuv420p, AAC 192k 48 kHz, -14 LUFS, true peak -1.5 dBTP, exact duration |

Run one heavy render at a time. Two renders side by side are slower than two in a row.

## When the user says "check it against the brief"

That message means: re-read the **original brief** (not your spec), go through it line by line, and for each line show the evidence that `final.mp4` meets it. Fix every miss, re-render, run section 4 again, and update REPORT.md. Do this without asking first.

## Files in this skill

- `references/hyperframes.md`: composition rules, commands, audio, sub-compositions, common failures
- `references/threejs.md`: time-driven 3D, seeded randomness, text over 3D, performance
- `references/blender.md`: headless Blender, engines, light, camera, text, frames
- `references/ffmpeg.md`: finishing, joining, overlays, sound, loudness, inspection
- `scripts/finish.sh`, `scripts/check_delivery.sh`, `scripts/contact_sheet.sh`, `scripts/sound_bed.sh`
- `templates/SPEC.md`, `templates/threejs/index.html`, `templates/blender/scene.py`
