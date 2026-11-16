# Brief 08: one brief, five worlds

Make a 25-second shot in which the words of a brief turn into the worlds they describe. The camera never cuts. It travels from a flat page of text, through a 3D city, into a 2D chart world, out into a galaxy and back to the page. Each world shows a different thing the skill can do, and the last frame loops back to the first.

- Delivery: final.mp4, 1920x1080, 30 fps, exactly 25.0 s, H.264 + AAC.
- Typefaces: JetBrains Mono for the brief text, Space Grotesk Bold for every other word (both Google Fonts).
- Route: HyperFrames for the 2D type and charts, Three.js for the 3D worlds, all in one composition, so the camera can pass from one world into the next without a cut. ffmpeg finishes the file.
- Never use teal or mint anywhere, not even as a shade.

## Palette

Each world has its own colour key. Use only these hex codes, their shades and their mixes.

| World | Dominant | Accents |
|---|---|---|
| 1. The page | midnight indigo #14112B | paper #F2EDE4 text, saffron #FFB000 cursor |
| 2. The city of light | dusk violet #2A1B5C sky | saffron #FFB000 towers, coral #FF5A1F street lights, magenta #E0338A haze |
| 3. The chart world | paper #F2EDE4 | ink #16130F, coral #FF5A1F, violet #7B5CFF, saffron #FFB000 |
| 4. The galaxy | deep space #07060F | magenta #E0338A arms, violet #7B5CFF dust, saffron #FFB000 core, sky blue #3FA9F5 stars |
| 5. The title | midnight indigo #14112B | paper #F2EDE4 title, saffron-to-coral gradient on the underline |

## What happens when

1. **The page, 0.0-3.0 s (2D type).** A dark page fills the frame. From the first frame it shows three lines in paper colour, 56 px, with a blinking saffron cursor after the last one:
   - `# brief.md`
   - `A city of light rises out of these words.`
   - `Camera: one move, no cuts.`

   From 1.0 s the words of the second line peel off the page one at a time and extrude into glowing saffron 3D blocks. The first word has left the page plane by 1.8 s.
2. **The city of light, 3.0-9.0 s (3D).** The blocks drop and stack into a city of at least 60 glowing towers under a violet dusk sky with magenta haze and soft fog. Place the towers with a seeded random generator so every render is identical. The camera tilts down from the page and flies low down the main street between the towers. Bloom only on the lit windows and street lights.
3. **The chart world, 9.0-14.0 s (2D motion graphics).** The camera flies into one lit window, and the window opens into a flat paper-coloured world: an animated bar chart of five bars growing in sequence (coral, violet, saffron, coral, violet), a line that draws itself across them, and three flat icons that pop in (a play button, a frame, a speaker). Everything is crisp flat 2D, on a plane inside the scene.
4. **The galaxy, 14.0-20.0 s (3D particles).** The tallest bar keeps growing upwards, and the camera rides it up through the top of the frame into deep space. The camera pulls back through a spiral galaxy of at least 20,000 particles (magenta arms, violet dust, saffron core, sky-blue stars), turning slowly.
5. **The title, 20.0-23.5 s.** The galaxy shrinks to a single saffron point, which becomes the dot of the full stop in "brief2mp4." in Space Grotesk Bold, at least 150 px tall, paper colour. Under it, at 48 px: "paste a brief, get this". A saffron-to-coral underline draws in under the title. The title holds still and fully readable from 20.5 to 23.5 s.
6. **Back to the page, 23.5-25.0 s.** The title fades, the camera settles to the exact framing of the first frame, and the three brief lines are back, so the video loops with no visible jump.

## Capability chips

A small chip in the bottom-left corner names what each world is made with, so a viewer learns the routes while watching. Chips are 32 px Space Grotesk on a dark rounded pill, at least 64 px from the frame edges, each cross-fading into the next:

| Time | Chip text, exactly |
|---|---|
| 0.3-3.0 s | `2D type · HyperFrames` |
| 3.0-9.0 s | `3D city · Three.js` |
| 9.0-14.0 s | `2D charts · HyperFrames + GSAP` |
| 14.0-20.0 s | `20,000 particles · Three.js` |
| 20.0-23.5 s | `finished · ffmpeg` |

## Rules

- One continuous camera move from the first frame to the last. No cuts and no fades to black.
- Text never touches the frame edge (at least 64 px margin). Nothing important is cut off at any time.
- Sound: a soundtrack with a soft rise in each world, a light accent when the first word lifts (about 1.2 s), a whoosh into each new world (3.0, 9.0 and 14.0 s) and a low accent when the title lands (20.0 s). Loudness -16 LUFS integrated.

## Done when

- ffprobe reports 1920x1080, 30 fps, 25.0 s, H.264 + AAC.
- A still at 1.8 s shows at least one word of the second line off the page plane.
- Stills at 6.0, 11.5, 17.0 and 22.0 s show the city, the chart world, the galaxy and the title, in the colours of the palette table.
- ffmpeg scene-cut detection (`scdet`) finds no cut anywhere in the video.
- The first and last frames match: SSIM at least 0.90.
- The title is at least 150 px tall, and still and readable from 20.5 to 23.5 s.
- All five chip texts appear exactly as written, each readable in at least one still.
- No pixel region reads as teal or mint in any still.
- Integrated loudness is -16 LUFS, within 1 LU.
