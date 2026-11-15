# REPORT: Brief 07, "Tidy your layers"

Deliverables in `brief07-edit-tutorial/`: `final.mp4` (14.0 s, 1920x1080, 30 fps, H.264 yuv420p, AAC 48 kHz stereo), `thumb.png` (1280x720), `SPEC.md`, `checks/` stills. Edit pack ready (`detect_edit.sh`: film,sound,effect,photo,vector). Cut in FilmCraft, mix in SoundCraft, thumbnail in PhotoCraft; clips from HyperFrames.

## Done when, checked against the original brief

| Requirement | Status | Evidence |
|---|---|---|
| final.mp4 is 14.0 s, 1920x1080, 30 fps, H.264 + AAC, -14 LUFS; `check_delivery.sh` passes | met | `checks/delivery.txt`: duration 14.000000 s, h264, yuv420p, 1920x1080, 30/1, aac 48 kHz stereo, loudness -14.4 LUFS, true peak -2.0 dBTP, no black, nothing frozen. `RESULT: PASS` |
| Clip A and B are 8 s HyperFrames clips; A used from 0.0 s, B from 0.5 to 7.5 s | met | `clipA/render.mp4` and `clipB/render.mp4` both 8.000000 s (ffprobe). FilmCraft timeline: A source 0-7.0 at 0.0 s, B source 0.5-7.5 at 7.0 s |
| Clip A: about a dozen overlapping rounded rectangles, different sizes, palette colours | met | `checks/t_000.10s.png` and `t_005.00s.png`: 12 rectangles, widths 262-348 px, heights 128-168 px, overlaps visible, cream and accent only on #14213D |
| Clip B: same rectangles in three aligned rows, slow push-in | met | `checks/t_010.00s.png`: 3 rows of 4. Painted-pixel width grows 1420 px (7.6 s) to 1480 px (10.0 s) to 1523 px (13.9 s) by `bounds.py`, so the camera pushes in |
| Cross dissolve 1.0 s centred on the cut at 7.0 s | met | `checks/t_007.00s.png` shows messy and tidy rectangles at the same time at half strength; `t_007.60s.png` shows rows only (box x 250-1669) |
| Title "Tidy your layers", 96 px, lower left, accent, on screen 1.0 to 4.0 s | met | `checks/t_002.00s.png`: spelled exactly, accent colour, `bounds.py` box x 96-815, y 890-977 (88 px from top of "T" and "d" to the foot of "y"; the font size is 96), inside the 96/54 margins. Title clip placed at 1.0 s for 3.0 s; `t_005.00s.png` has nothing in the title region (`bounds.py` box null) |
| Sound: quiet bed, chime at 1.0 s and 7.0 s | met | SoundCraft session with tracks `bed`, `chime1` (at 1.0 s), `chime2` (at 7.0 s). In `final.mp4` the max level jumps to -1.5 dB in 1.0-2.5 s and -1.3 dB at 6.9-7.1 s, against -3.9 dB at 4.8-5.3 s |
| Bed ducked 12 dB for 1.5 s under each chime, smooth return | met | Automation points on `bed`: -6 dB to 0.75 s, ramp to -18 dB at 1.0 s, hold to 2.5 s, ramp back to -6 dB at 3.0 s; same at 6.75-9.0 s. Bed-only bounce `work/snd/bedonly.wav` |
| Bed at least 10 dB lower in 1.0-2.5 s than at 5.0 s | met | Bed stem mean volume: -41.1 dB over 1.0-2.5 s, -28.5 dB over 4.5-5.5 s: 12.6 dB lower. (In the full mix the window holds the chime, so the measure is on the bed stem.) |
| thumb.png 1280x720, "Tidy your layers" large, one rectangle, no other text | met | ffprobe 1280x720; `thumb.png` shows only the title (150 pt, cream) and one accent rounded rectangle |
| Title readable at 320 px wide | met | `checks/thumb_320.png` (thumb scaled to 320 px): the whole title reads clearly, letters about 30 px tall |
| One typeface, bold, for everything | met | Helvetica Neue Bold in the title (FilmCraft) and thumbnail (PhotoCraft); clips have no text. Confirmed visually in the stills |
| Flat shapes, no gradients inside clips | met | Solid fills (accent, cream) at 0.94 opacity with a 3 px outline in the background colour so overlaps read; no gradients |
| Something visible by 0.3 s | met | `t_000.10s.png` has the pile in frame |

## Decisions
- Clip B is fully tidy from its first frame so both states are visible through the dissolve; only a push-in (scale 1.00 to 1.10, power1.out) moves.
- The messy pile stays in y 76-760 so the lower-left title never sits on a rectangle.
- Rectangles in B keep their widths from A but share one height (150 px) so the rows align.
- The chimes are two sine bursts (880 and 1320 Hz, exponential decay) made with ffmpeg; the bed is `sound_bed.sh` with no accents.
- The finish stage laid `work/snd/mix.wav` under the FilmCraft cut.

## Render settings and timing
- Clips: `hyperframes render . -o render.mp4 --quality delivery --fps 30 --workers 8`: 2.6 s and 2.4 s (7 s for both including start-up).
- Cut: `filmcraft-cli run` in three stages, then export H.264 CRF 14, 2.0 s render time, 420 frames.
- Mix: `soundcraft-cli run` with `--bounce`, under 1 s for the mix and the bed-only check.
- Thumbnail: `photocraft-cli run --new ... --out`, under 1 s.
- Finish: `finish.sh --in cut.mp4 --out final.mp4 --seconds 14 --audio work/snd/mix.wav`, 1 s.

## Open
- Loudness first landed at -15.2 LUFS, 1.2 dB below the -14 target (inside the check's tolerance). The quiet bed plus loud chimes leave too little peak headroom for loudnorm's linear mode, so it fell back to dynamic mode and undershot. This run led to a fix in `finish.sh` (it now measures the result and closes the gap through a limiter); re-finishing the same cut and mix gives -14.4 LUFS with true peak -2.0 dBTP, the numbers in the table above.
- `hyperframes check` on clip A warned "first_frame_empty", but the snapshot at 0 s shows the full pile; the rectangles are added by script, which the static check misses.
