# SPEC: five motions, one studio

## Delivery
| Item | Value |
|---|---|
| File | final.mp4 |
| Frame | 1920x1080 |
| Frame rate | 30 fps |
| Duration | 24.0 s (720 frames) |
| Video | H.264, yuv420p |
| Audio | AAC 48 kHz stereo, -14 LUFS, true peak <= -1 dBTP |

## Exact text (character for character)
1. "Cloth drop"
2. "Hinged chain"
3. "Folding"
4. "Walking, feet planted"
5. "Seamless loop"

## Look
- One studio for every act: `--look studio` on each recipe. A seamless backdrop (the floor curves up into the wall, so there is no horizon), a soft key from the upper left, a weak fill, a rim from behind and a wash on the wall; ray-traced reflections and bounce light; Eevee at 64 samples.
- Palette, the same line for every act: backdrop #c4beb6 (world) and #cdc7bf (set), subject #e0632f (vermilion), accent #3358c8 (cobalt), ink #24212a (charcoal). No teal or mint.
- Materials: lacquered links and gem (clear coat), fabric sheen and 12 mm thickness on the cloth, paper 4 mm thick with a cobalt underside, a vermilion mannequin with cobalt joints and charcoal feet.
- Type: Blender's built-in sans as flat 3D text, 38 px tall at 1080p, bottom left, 100 px from the left edge and 70 px from the bottom, after a short vermilion bar. Each caption fades in over 9 frames while rising 10 px, and fades out before the next dissolve.
- Camera: every move drifts the same way (the backdrop slides left): a 4, 3 and 4 degrees-a-second orbit on the cloth, chain and fold, the follow on the walk, and a still camera on the loop, so its seam has nothing to hide behind.
- Mood: calm, exact, a well-lit workshop.

## The cut
The music is 95 BPM, so a bar is 2.524 s (75.7 frames). Acts join on every second bar line, at frames 114, 265, 416 and 568. Each act renders 6 frames past each of its joins, and neighbours dissolve into each other over those 12 frames (0.4 s), centred on the bar line. The last 0.6 s eases into the backdrop colour while the music fades.

## Beat sheet
| Time (s) | On screen | Motion |
|---|---|---|
| 0.0-3.8 | a sheet above a cobalt sphere, "Cloth drop" | the sheet is already falling at frame 1, lands on the sphere at about 0.3 s, drapes into folds and settles; the camera orbits slowly |
| 3.8-8.83 | a seven-link chain on a post, "Hinged chain" | the first big downbeat of the music lands on the dissolve; the chain, released at 85 degrees, whips across and back; the whole arc stays in frame |
| 8.83-13.87 | a vermilion sheet, "Folding" | three folds of 34 frames, 9 frames apart; each turns the cobalt underside up; the camera eases to the stack and closes in |
| 13.87-18.93 | a mannequin on a ruled floor, "Walking, feet planted" | walks right at 0.95 m/s, one step every 17 frames, the camera following with room ahead |
| 18.93-24.0 | a gem and ring, "Seamless loop" | one turn per bar (a 76-frame loop) played twice; the camera holds; the picture eases out at the end |

Hero moment: 3.8 s, the music's beat comes in as the chain is released.

## Tool
Blender, headless, through the 3D pack's motion recipes (cloth, rigid, fold, walk, loop), because each act is a simulation or a measured cycle that a recipe already gets right. The five acts render in parallel. ffmpeg dissolves them together; `scripts/finish.sh` lays the music and sets the loudness.

## Decisions (choices the brief left open)
- The music is a CC0 track from Openverse (see ATTRIBUTION.md), chosen for its tempo: a 95 BPM bar lets each act run two bars. It is cut so its first big downbeat (12.69 s into the track) lands on the first join.
- Dissolves, not cuts: the five acts happen in one studio, so the join says "this continues". The dissolve is centred on the bar line, so the beat and the change land together.
- No depth of field: the captions are 3D text 1 m from the lens, and depth of field would blur them. The shots are wide enough that it would add little.
- The loop act renders frames 1-158 in one go; the gem's curves are cyclic, so frames past 77 keep looping.

## Done when
- [ ] final.mp4 is 24.0 s, 1920x1080, 30 fps (`check_delivery.sh` PASS with `--joins 3.8,8.833,13.867,18.933 --strict-flicker`)
- [ ] at 2.0, 6.3, 11.3, 16.4 and 21.0 s each caption is fully on screen, spelled exactly, nothing cut off
- [ ] act 2: `frame_margin` above 0 (the recipe's own measurement: no joint leaves the frame)
- [ ] act 4: planted feet move under 2 mm a frame (`max_slide_per_frame` in build/act4.json)
- [ ] act 5: the loop's seam slope gap under 0.02 (`seam_slope_gap` in build/act5.json)
- [ ] no teal or mint anywhere in the frame
