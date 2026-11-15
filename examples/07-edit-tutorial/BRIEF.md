# Brief 07: tutorial clip that needs real editing, "Tidy your layers"

Make a 14-second tutorial-style video from two separately generated clips, cut together on a timeline with a cross dissolve, a title and a mixed soundtrack. This brief needs the optional edit pack (`scripts/detect_edit.sh` should print `edit: ready (film,sound,photo,...)`; if it does not, install it from `edit/README-EDIT.md`). Without it, say so and stop: ffmpeg alone is not an editor for this brief.

- Delivery: final.mp4, 1920x1080, 30 fps, exactly 14.0 s, H.264 + AAC, -14 LUFS. Plus thumb.png, 1280x720.
- Look: background #14213D, text #F5F5F0, accent #FCA311. One typeface, bold, for everything. Flat shapes, no gradients inside the clips.
- Clip A, "before" (build it with HyperFrames, 8 s long, use the first 7.5 s): about a dozen rounded rectangles drift and overlap in a messy pile, each a slightly different size, all in the palette.
- Clip B, "after" (HyperFrames, 8 s long, use 0.5 s to 7.5 s of it): the same rectangles settled into three neat aligned rows, with a slow push-in on the camera.
- Edit (FilmCraft, `recipes/film_timeline.sh` is the pattern): clip A from 0.0 s, clip B from 7.0 s, a 1.0 s cross dissolve centred on the cut at 7.0 s. Title "Tidy your layers" in 96 px, lower left, in the accent colour, on screen from 1.0 s to 4.0 s.
- Sound (SoundCraft, `recipes/sound_mix.sh` is the pattern): a quiet bed from `scripts/sound_bed.sh` under the whole video, plus a short chime at 1.0 s (the title) and another at 7.0 s (the cut). The bed is ducked by 12 dB for 1.5 s under each chime and comes back up smoothly.
- Thumbnail (PhotoCraft, `recipes/photo_thumbnail.sh` is the pattern): thumb.png, 1280x720, the words "Tidy your layers" large, one rectangle from the clips as the picture, no other text.
- Done when: final.mp4 is 14.0 s and `check_delivery.sh` passes; in a still at 7.0 s both the messy and the tidy rectangles are visible at the same time (the dissolve); the words "Tidy your layers" are spelled exactly in stills at 2.0 s and are gone at 5.0 s; the bed is at least 10 dB lower in the 1.0 to 2.5 s window than at 5.0 s; thumb.png is 1280x720 and the title is readable at 320 px wide.
