# Brief 05: 2D explainer, "How a cache works"

Make a 20-second 2D explainer in the style of a YouTube or course video. Flat shapes, no 3D, no photos.

- Delivery: final.mp4, 1920x1080, 30 fps, exactly 20.0 s, H.264 + AAC.
- Look: background #F4F1EA, ink #1B1A17, one accent #2F6BFF for the thing that matters, a soft grey #B9B4A8 for secondary elements. Font: Inter, bold for headlines, regular for labels.
- 0.0 to 3.0 s (hook): the question "Why is the second visit faster?" types on, word by word, 110 px, centred.
- 3.0 to 8.0 s (setup): a diagram builds left to right: a "Browser" box, a long arrow drawn on to a "Server" box far right. A small clock label "800 ms" appears above the arrow.
- 8.0 to 14.0 s (idea): a "Cache" box appears between them in the accent colour. The arrow is redrawn so it stops at the cache. The clock label counts down from 800 to 12 and ends on "12 ms".
- 14.0 to 18.0 s (example): three labels appear one by one under the diagram, each 44 px: "First visit: fetch and store", "Second visit: read the copy", "Stale? Fetch again".
- 18.0 to 20.0 s (takeaway): everything except the cache box fades to the soft grey and the line "Keep a copy close." lands below it, 96 px, held still to the end.
- Sound: a quiet bed with soft clicks at 3.0, 8.0 and 14.0 s.
- Done when: every word above is spelled exactly; the final number reads "12 ms"; at 13.9 s and at 19.5 s no text overlaps any box or arrow other than a box's own label inside it; headlines are set at a font-size of at least 90 px and labels at least 40 px (font-size, as set in the CSS, not the measured glyph height); every line of text stays inside 96 px side and 54 px top and bottom margins.
