# SPEC: five motions, one film

## Delivery
| Item | Value |
|---|---|
| File | final.mp4 |
| Frame | 1920x1080 |
| Frame rate | 30 fps |
| Duration | 20.0 s |
| Video | H.264, yuv420p |
| Audio | AAC 48 kHz stereo, -14 LUFS, true peak <= -1 dBTP (a quiet bed) |

## Exact text (character for character)
1. "Cloth drop"
2. "Hinged chain"
3. "Folding"
4. "Walking, feet planted"
5. "Seamless loop"

## Look
- Palette: stage #1a1d29, floor #262a3a, subject #f0b24a, accent #d9573b, ink #f3ecdd. No teal or mint.
- Type: Blender's built-in sans as flat 3D text, 54 px tall at 1080p, bottom left, 100 px from the left edge and 70 px from the bottom.
- Mood: calm, exact, a workshop.
- Art form: 3D product render look, smooth 30 fps motion.

## Beat sheet
| Time (s) | On screen | Motion |
|---|---|---|
| 0.0-4.0 | cloth sheet over a sphere, "Cloth drop" | hangs still for 0.8 s, falls from 2.2 m, touches at about 1.4 s, drapes and settles |
| 4.0-8.0 | seven-link chain, "Hinged chain" | released at 85 degrees, swings across and back |
| 8.0-12.0 | paper sheet, "Folding" | three folds at 29 frames each, each halving the width |
| 12.0-16.0 | figure on a ruled floor, "Walking, feet planted" | constant speed, camera follows, feet planted |
| 16.0-20.0 | gem and ring, "Seamless loop" | a 2 s loop played twice |

Hero moment: 1.4 s: the cloth lands on the sphere.

## Tool
Blender, headless, through the 3D pack's motion recipes (cloth, rigid, fold, walk, loop) because each act is a simulation or a measured cycle that a recipe already gets right; ffmpeg joins the acts.

## Decisions (choices the brief left open)
- Each act is rendered separately by `build.sh` and joined with stream copy, so one act can be re-rendered alone.
- The dips between acts are 6-frame fades to the stage colour at each side of a join.
- The soundtrack is the skill's generated bed (`scripts/sound_bed.sh`), not music: sine pad and soft pulse.

## Done when
- [ ] final.mp4 is 20.0 s, 1920x1080, 30 fps (check_delivery.sh PASS, joins at 4, 8, 12 and 16 s)
- [ ] at 1.5 s, 5.5 s, 9.5 s, 13.5 s and 17.5 s each caption is fully on screen, spelled exactly, nothing cut off
- [ ] act 4: planted feet move under 2 mm a frame (the recipe's own measurement, in the build log)
- [ ] act 5: the 60-frame loop's first and last frames match (the recipe's own pixel-level check passes in the test suite)
- [ ] no teal or mint anywhere in the frame
