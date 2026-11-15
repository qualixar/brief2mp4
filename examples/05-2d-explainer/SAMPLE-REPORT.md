# REPORT: Brief 05, "How a cache works"

Deliverable: `brief05-2d-explainer/final.mp4`. It runs 20.0 s at 1920x1080 and 30 fps, encoded as H.264 yuv420p with AAC 48 kHz stereo.

## Done when, checked against the original brief

| Requirement | Status | Evidence |
|---|---|---|
| final.mp4 1920x1080, 30 fps, exactly 20.0 s, H.264 + AAC | met | `check_delivery.sh`: h264, yuv420p, 1920x1080, 30/1, duration 20.000000s, aac 48 kHz stereo, -14.0 LUFS, true peak -1.4 dBTP. Result: PASS |
| Background #F4F1EA, ink #1B1A17, accent #2F6BFF, grey #B9B4A8, Inter bold headlines and regular labels | met | CSS tokens in `index.html`. Stills show Inter loaded from `vendor/fonts` (the "y" and "a" shapes of Inter, not a fallback face). Accent is used only on the Cache box |
| Hook "Why is the second visit faster?" types on word by word, 110 px, centred, 0.0 to 3.0 s | met | `font-size:110px` bold. `checks/t_000.00s.png` shows "Why" only; `t_001.50s.png` is mid-sentence; `t_002.50s.png` shows the full line on two rows, ink x 461-1454 (centre 957.5 of 960). Words arrive 0.0, 0.3, 0.6, 0.9, 1.2, 1.5 s; the hook fades out 2.7-3.0 s |
| 3.0-8.0 s: Browser box, long arrow drawn on to Server box far right, "800 ms" above the arrow | met | `checks/t_006.00s.png`: Browser x 120-479, arrow to x 1428, Server x 1440-1799, "800 ms" centred over the arrow. Build order in the timeline: Browser 3.0 s, Server 3.6 s, arrow draw-on 4.2-5.6 s, label 5.8 s |
| 8.0-14.0 s: Cache box in accent between them, arrow redrawn to stop at the cache | met | `checks/t_011.00s.png` and `t_013.90s.png`: Cache (accent) at x 780-1139, arrow measured x 492-767 stops 13 px before the cache's left edge |
| Clock counts down from 800 to 12 and ends on "12 ms" | met | `t_011.00s.png` reads "652 ms" mid-count; `t_013.90s.png` reads "12 ms". Count runs 9.7-13.3 s |
| 14.0-18.0 s: three 44 px labels appear one by one under the diagram | met | `font-size:44px`. Labels land at 14.2, 15.4 and 16.6 s. `checks/t_015.00s.png` shows the first, `t_016.90s.png` all three. Measured rows: y 570-604, 639-681, 708-750 |
| 18.0-20.0 s: everything except the cache box fades to grey, "Keep a copy close." lands below, 96 px, still to the end | met | `checks/t_019.50s.png` and `t_019.90s.png`: Browser, Server, arrow, "12 ms" and the three labels are grey, Cache stays blue. Line is `font-size:96px`, ink x 526-1392, y 840-929, below the cache (bottom y 439) and the labels (bottom y 749). It lands 18.2-18.7 s. `freezedetect` reports a freeze from 18.47 s to the end |
| Sound: quiet bed with soft clicks at 3.0, 8.0 and 14.0 s | met | Level above 1.5 kHz in a 0.1 s window: 2.5 s -17.5 dB, 3.0 s -2.0 dB, 5.0 s -11.6 dB, 8.0 s -3.7 dB, 11.0 s -19.1 dB, 14.0 s -2.3 dB, 16.0 s -16.9 dB. Each click stands 10 dB or more above the bed |
| Every word spelled exactly | met | Read in `t_002.50s.png` (hook), `t_006.00s.png` (Browser, Server, 800 ms), `t_013.90s.png` (Cache, 12 ms), `t_016.90s.png` (three labels), `t_019.50s.png` (takeaway) |
| Final number reads "12 ms" | met | `checks/t_013.90s.png`; also `t_016.90s.png` and `t_019.50s.png` |
| At 13.9 s no text overlaps any box or arrow except a box's own label | met | `scripts/bounds.py` on regions of `t_013.90s.png`: "12 ms" box x 556-702, y 258-300; arrow x 492-767, y 326-353; Browser x 120-479; Cache x 780-1139. The label sits 26 px above the arrow and 77 px right of the Browser box. The three boxes' own labels sit inside them |
| At 19.5 s no text overlaps any box or arrow except a box's own label | met | `bounds.py` on `t_019.50s.png`: "12 ms" x 557-702, y 259-300, arrow y 326-353, labels y 570-749, takeaway y 840-929, cache y 240-439. All separate rows, no shared pixels |
| Headlines at least 90 px and labels at least 40 px (CSS font-size) | met | `index.html`: hook 110 px, takeaway 96 px, box labels 56 px, clock 56 px, example labels 44 px |
| All text inside 96 px side and 54 px top and bottom margins | met | `bounds.py --margin 96,54` on full stills at 0.0, 1.5, 2.5, 6.0, 13.9, 16.9 and 19.5 s: inside = true every time. Widest extent x 120-1799, y 240-929 |

## Decisions
- The hook sets on two rows ("Why is the second" / "visit faster?"). One row at 110 px bold is about 1,980 px wide, more than the 1,728 px between margins. Words and order are unchanged.
- "Everything except the cache box fades to the soft grey" is read literally: Browser, Server, arrow, clock and the three labels go grey and stay. The takeaway sits below them.
- The "800 ms" label glides from over the middle of the long arrow to over the short arrow (8.0-8.4 s) before the Cache box appears, so it never overlaps the Cache box. Server stays in place; only the Browser-to-Cache arrow remains.
- The first word "Why" is already on screen at frame 0 so the cover frame is not empty; the other five arrive one by one.
- Quiet is read as a soft pad at the skill's -14 LUFS default. The clicks are 2.4 kHz ticks.

## Render settings
- Vendor: `vendor_libs.sh . --fonts inter` (GSAP 3.15.0, Inter 400 and 700). `index.html` has no http references, no `Math.random` and no `Date.now`.
- Picture: `npx hyperframes render . -o render.mp4 --quality delivery --fps 30 --workers 4`, which rendered in 8.2 s.
- Sound: `sound_bed.sh bed.wav --seconds 20 --ticks 3.0,8.0,14.0`. This run used a patched copy; the fix (clamping the exponent) is now in the shipped `sound_bed.sh`, which also refuses to report success on a silent result.
- Finish: `finish.sh --in render.mp4 --out final.mp4 --seconds 20 --audio bed.wav` (CRF 18, AAC 192k).

## Fix rounds: 1
- Round 1: the first finished file measured -70 LUFS (silent) although `sound_bed.sh` printed success. With `--ticks` later than about 7.8 s the aevalsrc expression overflows (`exp(-90*(t-k))` at t=0 is infinite, times the zero gate is NaN) and the whole bed goes silent. I clamped the exponent in a local copy (`exp(-90*max(t-k,0))`), rebuilt the bed and finished again. `check_delivery.sh` then read -14.0 LUFS. This run found the bug; the clamp is now in the shipped `sound_bed.sh`, `sound_bed.sh` now fails on a silent result, and `check_delivery.sh` now FAILs a silent soundtrack unless `--silent-ok` is passed.
- Before the first full render, `hyperframes check` showed that `tl.set(..., 0)` hidden states are not applied at frame 0 and that frame 0 was empty. Initial states moved to CSS, first word visible at 0.0 s.

## Open
- `check_delivery.sh` WARNs about 3 frozen stretches (5.9-8.4 s, 10.4-14.3 s, 18.5-20.0 s). They are the intended holds. The count-down changes only digits inside the label, which is below `freezedetect`'s noise threshold, so the second stretch contains the count-down.
- `hyperframes check` reports contrast 1.83:1 on the grey (#B9B4A8 on #F4F1EA) for the final fade. The brief names that colour, so it stays.
- `hyperframes check` says the closing line is on screen 1.5 s and suggests 2 s. The brief gives the final beat 2.0 s and the line must land inside it, so the brief wins.
- Lint warns three times that nested elements want sub-compositions. This is an editor-organisation hint with no effect on the render.
