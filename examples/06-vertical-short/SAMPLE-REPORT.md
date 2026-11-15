# REPORT: Brief 06, "3 easing rules"

Deliverable: `brief06-vertical-short/final.mp4`. It runs 15.0 s at 1080x1920 and 30 fps, encoded as H.264 yuv420p with AAC 48 kHz stereo.

## Done when, checked against the original brief

| Requirement | Status | Evidence |
|---|---|---|
| final.mp4 1080x1920, 30 fps, exactly 15.0 s, H.264 + AAC | met | `check_delivery.sh --size 1080x1920`: h264, yuv420p, 1080x1920, 30/1, duration 15.000000s, aac 48 kHz stereo, -14.0 LUFS, true peak -1.5 dBTP. Result: PASS |
| Background #101114, text #F7F5F0, accent #FFB224, Space Grotesk Bold | met | CSS tokens in `index.html`. Stills show Space Grotesk loaded from `vendor/fonts` (its flagged "1" and open "y" in `t_005.50s.png`, `t_003.00s.png`), not a fallback face |
| Every line spelled exactly | met | Read in `checks/t_001.00s.png` ("Your animations feel cheap?", set on three rows), `t_003.00s.png` ("3 rules." / "15 seconds."), `t_005.50s.png`, `t_008.50s.png`, `t_011.50s.png` (rules 1 to 3, one row each) and `t_014.50s.png` ("Save this.") |
| First frame (0.0 s) already shows the hook text, and it is moving | met | `checks/t_000.00s.png` shows the full hook (ink x 206-743, y 655-957). `t_000.10s.png` differs: y 651-953, so it has drifted 4 px up in 0.1 s (power2.out drift from t = 0) |
| Hook at 96 px, "3 rules. 15 seconds." at 80 px, "Save this." at 120 px | met | `index.html`: `#t1` 96 px, `#t2` 80 px, `#t6` 120 px. Rules are 60 px (the brief gives no size) |
| Stills at 1.0, 3.0, 5.5, 8.5, 11.5, 14.5 s: all text and the dot inside the safe box | met | `bounds.py --safe top=288,bottom=672,left=64,right=192`, inside = true on every one. Boxes: 1.0 s x 206-743, y 629-931; 3.0 s x 250-698, y 694-843; 5.5 s x 193-756, y 543-787; 8.5 s x 222-771, y 543-787; 11.5 s x 148-802, y 543-787; 14.5 s x 199-750, y 723-810. Also true at 0.0 s, 4.3 s, 8.6 s (dot right edge x 885 of the 887 limit) and 14.9 s |
| Every line at most 824 px wide, centred in the box | met | Ink widths (`bounds.py` per line): hook rows 204, 504, 538; "3 rules." block 449; rule lines 564, 508, 655; "Save this." 552. Widest is 655. Ink centres fall at x 474.5-475 against the box centre 476 |
| Rule 1 eases out: at 4.6 s the dot has covered more than half | met | `t_004.60s.png`: dot centre x 398.5. Start centre 86, rest centre 475.5, so it has covered 312.5 of 389.5 px = 80 % (power3.out at one third of the way predicts 80 %) |
| Rule 2 eases in: at 7.8 s the dot has covered less than a fifth | met | `t_007.80s.png`: dot centre x 480.5, rest 475.5, end 865.5. It has covered 5 of 390 px = 1.3 % (power3.in at one third predicts 1.2 %) |
| Rule 3 is linear: 10.5, 11.0 and 11.5 s show the same 90 degree step (within 5) | met | Dot centres (orbit centre 475.5, 767.5): 10.5 s (555.5, 767.5), 11.0 s (475.5, 847.5), 11.5 s (395.5, 767.5). Angles 0.0, 90.0, 180.0 degrees: each step 90.0. Orbit radius 80 px (a 160 px circle) |
| "Save this." fully on screen and unmoving from 13.3 s to 15.0 s | met | Ink box x 199-750, y 723-810 at 13.3, 14.0, 14.5 and 14.9 s, identical to the pixel. `freezedetect` reports a freeze from 13.13 s to the end. Fully on screen at 13.3 s (`t_013.30s.png`) |
| Captions: none | met | No caption layer in `index.html`; the only text is the six lines |
| Sound: quiet bed with a tick at 2.0, 4.0, 7.0, 10.0, 13.0 s | met | Level above 1.5 kHz in a 0.1 s window: 1.5 s -35.8 dB, 2.0 s -3.8, 3.0 s -37.9, 4.0 s -2.6, 5.5 s -21.1, 7.0 s -2.7, 8.5 s -14.0, 10.0 s -3.7, 11.5 s -11.9, 13.0 s -4.0, 14.0 s -21.2. Each tick is 10 dB or more above the bed around it |

## Decisions
- The hook sets on three rows and "3 rules. 15 seconds." on two. One row each would be about 1,400 and 930 px wide, over the 824 px limit. The words and punctuation are unchanged.
- The dot starts with its left edge at x 66 and ends with its right edge at x 886, 2 px inside the safe box, so antialiasing never touches the zone line. Both moves are 390 px.
- "A 160 px circle" is read as diameter 160 (radius 80), centred on the box centre (476, 768), clockwise, starting at the top at 10.0 s. No guide ring is drawn, so a still holds only text and the dot.
- The dot is off screen from 8.7 s to 10.0 s; it fades in at the top of the orbit at 10.0 s and fades out at 12.9 s.
- Rule lines are 60 px and sit above the dot lane (ink y 543-597); the dot stays at y 748-787 in all three rules.
- Quiet is read as the skill's -14 LUFS default with a soft pad and 2.4 kHz ticks. GSAP's `power3` is a quartic curve, which is what the brief's one-third thresholds assume (80 % and 1.2 %).

## Render settings
- Vendor: `vendor_libs.sh . --fonts space-grotesk` (GSAP 3.15.0, Space Grotesk 400 and 700). `index.html` has no http references, no `Math.random` and no `Date.now`.
- Picture: `npx hyperframes render . -o render.mp4 --quality delivery --fps 30 --workers 4`, which rendered in 5.8 s.
- Sound: `sound_bed.sh bed.wav --seconds 15 --ticks 2,4,7,10,13`. This run used a patched copy; the fix (clamping the exponent) is now in the shipped `sound_bed.sh`, which also refuses to report success on a silent result.
- Finish: `finish.sh --in render.mp4 --out final.mp4 --seconds 15 --size 1080x1920 --audio bed.wav` (CRF 18, AAC 192k).

## Fix rounds: 0 after the first full render
- Before rendering I had already met the same sound-bed fault as in Brief 05: with `--ticks` later than about 7.8 s, `sound_bed.sh` writes a silent file. I used a clamped copy from the start, so the first finished file had a real soundtrack. That fix is now in the shipped script.
- The first snapshot used two-row rule lines at 64 px. I changed them to one row at 60 px before the full render, so each line reads as one string.

## Open
- `check_delivery.sh` WARNs about 5 frozen stretches (2.2-3.9 s, 4.2-6.9 s, 7.2-10.0 s, 10.2-12.9 s, 13.1-15.0 s). These are the held beats; the dot's small motion is below the whole-frame noise threshold. The last one is the hold the brief asks for.
- `hyperframes check` says the closing line "Save this." is on screen 1.93 s and suggests 2 s. The brief gives the last beat 2.0 s and has the line land by 13.3 s, so the brief wins.
- The screen is sparse by design: all content sits in the upper-middle of the safe box because the brief reserves the bottom 672 px and the right 192 px.
