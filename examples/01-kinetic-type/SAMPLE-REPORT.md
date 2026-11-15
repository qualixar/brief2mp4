# REPORT: Brief 01, "Finish something today"

Deliverable: `brief01-kinetic-type/final.mp4`. It runs 12.0 s at 1920x1080 and 30 fps, encoded as H.264 yuv420p with AAC 48 kHz stereo.

## Done when, checked against the original brief

| Requirement | Status | Evidence |
|---|---|---|
| final.mp4 1920x1080, 30 fps, exactly 12.0 s, H.264 + AAC | met | `check_delivery.sh`: h264, yuv420p, 1920x1080, 30/1, duration 12.000000s, aac 48 kHz stereo. Result: PASS |
| Paper #F2EDE4, ink #16130F, accent #FF5A1F, Space Grotesk Bold | met | CSS tokens in `index.html`. Snapshots show Space Grotesk loaded (its single-storey "y" and the shape of the "g"), not a fallback face |
| Line 1 "Ideas are cheap." from 0.3 to 3.5 s | met | `checks/t_000.30s.png` is empty paper as the first word starts; `t_001.50s.png` shows the full line, spelled exactly |
| Line 2 "Finished is rare." from 3.5 to 7.0 s, replacing line 1 | met | `t_005.00s.png` shows line 2 alone |
| Line 3 "Finish something today." from 7.0 to 12 s | met | `t_008.00s.png` and `t_011.90s.png`. Set on two rows ("Finish something" / "today."); see Decisions |
| Each word arrives with a masked rise, one word at a time | met | Snapshots at 0.45, 0.6 and 0.75 s show "Ideas" landed, "are" mid-rise and "cheap." starting, each clipped by its mask |
| Orange bar wipes at 3.5 s and 7.0 s | met | `t_003.35s.png` bar mid-wipe; `t_003.50s.png` frame fully orange; `t_006.85s.png` second wipe mid-way |
| After the last wipe the bar shrinks into an underline under "today." | met | `t_007.40s.png` bar mid-shrink; `t_008.00s.png` underline sits under "today." and clears the descender of the "y" |
| Hero lands by 8.0 s, holds still and readable until 12.0 s | met | Last word tween ends at 7.88 s. `freezedetect` (n=0.001) reports a freeze from 7.73 s to the end. The small pixel differences between held frames are encoder noise, because they do not shrink over time (10.0 s differs from 11.9 s more than 8.1 s does) |
| Quiet soundtrack with a low accent at 3.5 s and 7.0 s | met | Sub-80 Hz level: 2.9 s gives -21.8 dB, 3.5 s gives -10.9 dB, 5.5 s gives -29.6 dB, 7.0 s gives -11.1 dB. Mix is -18.0 LUFS, true peak -1.8 dBTP |
| Text never touches the frame edge | met | Ink spans x 277–1648 and y 380–728 at 11.9 s, x 300–1628 at 1.5 s and x 336–1592 at 5 s. All of it is inside the 96/54 px safe margins |
| Headlines at least 120 px tall | met | Measured capital height is 126 px on every line (font-size 180 px) |

## Decisions
- Line 3 does not fit on one row at a 120 px cap height inside the safe area, so it sets on two rows. The words, their order and the punctuation are unchanged.
- I read "quiet" as -18 LUFS rather than the skill's -14 default. The bed is the skill's original sine-wave pad and pulse, with low booms at 3.5 s and 7.0 s.
- The bar is a full-frame orange panel. It enters from the left, the text swaps underneath it, and then it either exits to the right (first wipe) or collapses into the underline (second wipe).

## Render settings
- Picture: `npx hyperframes render . -o render.mp4 --quality delivery --fps 30 --workers 8`, which rendered in 4.5 s.
- Sound: `sound_bed.sh bed.wav --seconds 12 --hits 3.5,7.0`
- Finish: `finish.sh --in render.mp4 --out final.mp4 --seconds 12 --audio bed.wav --lufs -18` (CRF 18, AAC 192k)

## Open
- `check_delivery.sh` WARNs about 3 frozen stretches. These are the three intended holds (line 1, line 2 and the hero), not dead air.
- Lint shows 3 warnings suggesting sub-compositions for each line. That is a Studio-organisation hint and has no effect on the render.
