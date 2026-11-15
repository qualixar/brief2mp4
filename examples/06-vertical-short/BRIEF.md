# Brief 06: vertical Short, "3 easing rules"

Make a 15-second vertical Short for YouTube Shorts, Instagram Reels and TikTok.

- Delivery: final.mp4, 1080x1920, 30 fps, exactly 15.0 s, H.264 + AAC.
- Look: background #101114, text #F7F5F0, accent #FFB224. Font: Space Grotesk Bold.
- Safe zones: no text or dot in the top 288 px, the bottom 672 px, the left 64 px or the right 192 px. That leaves a box from x 64 to 888 and y 288 to 1248; keep every line of text at most 824 px wide, centred in that box.
- 0.0 to 2.0 s (hook): "Your animations feel cheap?" at a font-size of 96 px, already on screen and moving in the first frame.
- 2.0 to 4.0 s: "3 rules. 15 seconds." at 80 px.
- 4.0 to 7.0 s: "1. Ease out to arrive". An accent dot (40 px) slides in from the left edge of the safe box and decelerates into place at the centre: power3.out over 1.2 s, starting at 4.2 s.
- 7.0 to 10.0 s: "2. Ease in to leave". The dot starts at the centre and accelerates off to the right edge of the safe box: power3.in over 1.2 s, starting at 7.4 s.
- 10.0 to 13.0 s: "3. Linear only for spins". The dot orbits a 160 px circle at a constant speed, one full turn every 2.0 s.
- 13.0 to 15.0 s: "Save this." at 120 px in the accent colour; it lands by 13.3 s and holds still to the end.
- Captions: none (the words on screen are the content).
- Sound: a quiet bed with a tick on each beat change at 2.0, 4.0, 7.0, 10.0 and 13.0 s.
- Done when:
  - every line is spelled exactly;
  - the first frame (0.0 s) already shows the hook text;
  - in stills at 1.0, 3.0, 5.5, 8.5, 11.5 and 14.5 s, all text and the dot sit inside the safe box (check with `scripts/bounds.py --safe top=288,bottom=672,left=64,right=192`);
  - rule 1 eases out: at 4.6 s (a third of the way through the move) the dot has covered more than half of its distance;
  - rule 2 eases in: at 7.8 s (a third of the way through) the dot has covered less than a fifth of its distance;
  - rule 3 is linear: stills at 10.5, 11.0 and 11.5 s show the dot advanced by the same angle (90 degrees, within 5) each time;
  - "Save this." is fully on screen and unmoving from 13.3 s to 15.0 s.
