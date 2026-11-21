# Brief 09: a story scene with talking characters

Make a 14-second animated story scene with two characters who walk, move and talk, and render it twice from the same animation: once as paper cut-out, once as anime. Use the brief2mp4 character kit (`characters/README-CHARACTERS.md`).

- Delivery: final.mp4 for each look, 1920x1080, 30 fps, exactly 14.0 s, H.264 + AAC.
- Cast: a child and a crow (both from the starter cast). The crow faces left and stands at the right; a kite lies at its feet.
- Look 1: paper cut-out (flat layers, tight shadows, paper grain, drawings held 12 times a second). Look 2: anime and cel shading (outlines, hard shadows, redrawn eyes and hair). Same track, same timing, same words.
- 0.0 to 3.0 s: the child walks in from the left edge to the middle of the frame, with the walk cycle at the speed that keeps its feet on the ground (a `walk: true` key). The crow idles, then turns its head to think.
- 3.0 to 6.0 s: the child stops, points at the crow and says "Hey crow, that is my kite!" The mouth follows the words. The crow startles at 4.9 s.
- 6.0 to 10.0 s: the crow laughs and says "Finders keepers, little one." The child turns sad and stays sad.
- 10.0 to 14.0 s: the crow waves a wing goodbye. The last 1.5 s hold still.
- Captions: each line, word for word, on screen while it is spoken.
- Voice: the words are timed in `words.json` (the format `npx hyperframes transcribe` writes). The video here carries a stand-in voice made from those timings; record your own and run `npx hyperframes transcribe voice.wav` to replace both.
- Done when: the file is exactly 14.0 s; at 3.9 s, 4.6 s, 5.4 s and 8.0 s the speaker's mouth shows at least three different shapes across the four frames; the mouth is closed (rest) between "crow," and "that"; no caption is cut off at the frame edge; the child's feet do not slide on the ground while it walks; the same frame at the same time renders to the same pixels twice.
