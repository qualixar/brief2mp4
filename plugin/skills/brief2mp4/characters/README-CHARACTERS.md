# The character kit

A brief that says "two characters talk, walk or fight" needs characters that hold poses, move between them, blink, and move their mouths in time with a voice. The kit gives you that without any dependency: a rig that runs in a HyperFrames page, on a canvas or in Node, a pose and cycle library, a character file format, and art-form skins so the same character can be paper, anime or something else. A character stays recognisable across skins because every skin draws the same parts.

Everything is plain JavaScript and JSON. Nothing is fetched at render time.

## Files

| File | What it is |
|---|---|
| `rig.js` | `B2M.pose(character, track, t [, opts])`: the transform of every part at time `t`. A pure function of its inputs |
| `poses.js` | 15 named poses, the cycles (walk, run, wave, laugh, breath) and the nine mouth shapes |
| `shapes.js` | Turns shape records into paths; path tools for skins; the lip-sync mouth drawings |
| `render.js` | `B2M.layout(...)` gives a display list; `drawCanvas` and `createSVG` draw it |
| `skins.js`, `skins-extra.js` | The six skins (`B2M.SKINS`) |
| `stage.js`, `stage.html` | A 2D stage: backdrop, cast, captions; the page that plays a scene |
| `sheet.js`, `sheet.html` | The character sheet page |
| `cast/*.json` | The starter cast: `child`, `adult`, `crow`, `tomato` |
| `schema/character.schema.json`, `validate.py` | The format, and a standard-library validator |
| `image-demo/` | A robot rigged from PNG part images that a script draws: the worked example for your own art |

Scripts next to the skill's others: `scripts/lipsync.py` (mouth track), `scripts/character_sheet.py` (a PNG sheet), `scripts/character_project.py` (a scene, or the 2D-in-3D starter, to a HyperFrames project). The runnable example is `examples/09-story-characters/`.

In a page, load the scripts in this order: `poses.js`, `rig.js`, `shapes.js`, `render.js`, `skins.js`, `skins-extra.js`, `stage.js`. In Node, `require("<kit>/index.js")` loads them all. `character_project.py` copies the runtime into a HyperFrames project and inlines the cast as `characters/cast.js`.

## The starter cast

A child, an adult man in a kurta and dhoti-style outline (culturally neutral, no real person), a crow, and a tomato chef (an object character). Each is drawn from the same part list, in a three-quarter side view facing right, so poses, a walk and a fight read; each has a front-facing head drawing for close-ups, an anime redraw of the eyes, hair or crest, hard shadow shapes for the cel skin, and the hands, arms or wings it needs for open palms, pointing and a raised arm. The child holds a kite, the man a sword, the chef a ladle (`props: ["prop_kite"]` in a track). The crow's beak is a jaw that opens with the mouth shape.

## Look at a character first

```bash
python3 scripts/character_sheet.py --character child --skin all --out sheets/
python3 scripts/character_sheet.py --file my-art/hero.json --skin paper-cutout --out sheets/
```

Each sheet is a 1920x1080 PNG: the standing view, the front view close-up (if the character has one), six poses and the nine mouth shapes. Look at it before you build a scene. It is also the quickest way to check that a character still reads in every skin, and a source for thumbnails. One call renders every sheet through one HyperFrames snapshot run; it needs Node and, once, the network for GSAP.

## The pose function

```js
const posed = B2M.pose(child, track, t, { steps: skin.steps, smooth: !skin.steps });
const items = B2M.layout(child, skin, posed, { x: 600, y: 900, scale: 1.2 });   // feet at (600, 900)
B2M.drawCanvas(ctx, items);                                                    // or B2M.createSVG(document, parent, 1920, 1080).update(items)
```

It reads no clock and no unseeded randomness. Blinks and talk gestures come from a seeded hash of (character id, time bucket), so the same frame renders the same on every run. Call it from the paused GSAP timeline the way `references/threejs.md` shows.

A **track** is a list of keys, or an object:

```js
{ keys:   [{ t: 0, pose: "idle" }, { t: 1.2, pose: "wave", ease: "out" }],
  move:   [{ t: 0, x: 300 }, { t: 4, x: 900, flip: 1 }],           // where it stands; flip -1 faces left
  layers: [{ cycle: "walk", from: 0, to: 4, steps: 8 }, { cycle: "talk", from: 4, to: 9 }],
  visemes: [{ t: 4.1, v: "AI" }, { t: 4.3, v: "rest" }],            // the lip-sync track
  props: ["prop_kite"], view: "front", fx: { speedLines: [[2, 3]] } }
```

The ease on a key shapes the move **into** that key: `linear`, `in`, `out`, `inOut` (the default), `sine`, `backOut`, or `hold` (stay on the last pose until the key's time).

Angles are degrees. For arms, hands and legs a positive angle swings the limb forward, the way the character faces; for the torso, head, brows and feet it turns clockwise on screen. `lift` moves the whole body up or down as a fraction of leg length, so one pose fits a child and an adult.

### Cycles hold drawings

`steps` is the number of new drawings per second. A walk has 8 drawings; at `steps: 8` one stride takes a second. Handmade skins pass `steps: 12` to `pose`, so nothing changes more than 12 times a second whatever the cycles say. A smooth skin passes `smooth: true` and the cycles blend. To keep a walking character's feet planted, move it at `B2M.strideSpeed(character, "walk", steps)` units per second.

## Skins

A skin is a style map plus hooks: `shape(ctx)` turns one shape into drawing primitives, `character(ctx)` adds primitives for the whole figure, `sky(ctx)` and `foreground(ctx)` style the stage. All wobble is seeded by the shape and the drawing number. Each skin follows the rules of its page in `references/art-forms/`.

| Skin | Look |
|---|---|
| `line-art` | Strokes only, one weight, the line boils 10 times a second; the ground's colour inside a shape only hides lines behind it |
| `paper-cutout` | Flat fills, a thin lighter cut edge, paper grain, a tight shadow under each layer, edges that wobble on every held drawing |
| `shadow-puppet` | Black leather silhouette, eyes, mouths and decorative shapes punched out to the lamp, visible rods from the torso and hands, a warm backlight on the stage |
| `cel-shaded` | The anime redesign: parts with an `anime` variant are redrawn (large eyes with two highlights, spiky hair with a shine band, a tick for a nose), hard shadow shapes (`role: "cel"`) in a tinted tone, an ink outline sized to each shape, speed lines on a jump, a run, or `fx.speedLines` |
| `motion-comic` | Flat colour with a bold ink line, halftone dots for shadow, a panel border and a yellow caption box that carries the spoken line |
| `flat-explainer` | Clean flat vector: fills only, smooth motion, no outline and no shadow |

The handmade skins pass `steps: 12` (line art 10) to `pose`, so nothing changes more than that many times a second. The smooth skins pass `smooth: true` and cycles blend.

## Variants: one part, several drawings

A part can carry `variants`, each replacing the part's own `shapes`, `image`, `pivot`, `mouth` or `z`. Which one draws is decided, in this order, by the pose (`variants: { handN: "open" }`: an open palm for a wave, a pointing finger for a point), then the view and skin together (`front+anime`), then the view (`front`: a close-up that faces the camera, set with `track.view`), then the skin (`anime`). The child uses them for hands, a raised arm that draws over the head (`over`), the front-facing head, and the anime eyes and hair.

## The character format

```json
{ "id": "child", "palette": { "skin": "#f0b48a", "ink": "#231b2a" },
  "proportions": { "height": 232, "legLength": 78 },
  "parts": [
    { "id": "hip", "parent": null, "pivot": [0, -78], "z": 10, "shapes": [ ... ] },
    { "id": "legN_up", "parent": "hip", "pivot": [0, -78], "z": 10, "shapes": [ ... ] } ] }
```

Everything is drawn in one rest-pose coordinate system: feet on `y = 0`, the character facing `+x`, up is negative `y`. A part's `pivot` is where it hinges, in that same system; its children hang from it. Standard part ids are `hip` (the root), `torso`, `head`, `eyeN`, `eyeF`, `pupilN`, `pupilF`, `browN`, `browF`, `mouth`, `armN_up`, `armN_lo`, `handN`, the same with `F` for the far side, `legN_up`, `legN_lo`, `footN`, and props such as `prop_kite` (`"prop": true`, drawn only when the track lists them). `N` is the near side, `F` the far side. A pose that names a joint the character does not have skips it.

Shapes are `path` (absolute `M L C Q Z` only, so skins can wobble every point), `ellipse`, `circle`, `capsule` (a tapered limb), `rect` and `poly` (straight or a smooth curve through the points). `fill` and `stroke` name palette keys. `role` is `base`, `detail`, `hole`, `line`, `mouth` or `cel`. Validate with `python3 characters/validate.py cast/child.json`.

The mouth part has a `mouth` block: `lips` (drawn from the nine-shape table, `size` scales it), `jaw` (a lower jaw that rotates open) or `images` (below).

## Lip sync

```bash
npx hyperframes transcribe voice.wav                     # writes word timestamps (transcript.json)
python3 scripts/lipsync.py transcript.json --fps 30      # -> [{ "t": 3.45, "v": "etc" }, { "t": 3.5, "v": "E" }, ...]
python3 scripts/lipsync.py transcript.json --from 3.3 --to 6 --out kid-visemes.json    # one speaker's words
python3 scripts/lipsync.py --wav voice.wav               # no timestamps: open, half-open, closed from loudness
```

Put the result in a track as `visemes`. The nine shapes are `rest`, `AI`, `E`, `O`, `U`, `MBP`, `FV`, `L` and `etc` (every other consonant). Words become shapes by letter rules with a small exceptions table, spread over the word's time in proportion to how long each sound takes. The mouth closes in any pause longer than 150 ms, no shape is held for less than one frame at `--fps`, and every key sits on the frame grid. `--lang hi` reads romanised Hindi (aa, ee, oo, kh, bh); it is a best-effort mapping, approximate by nature, and meant for a mouth that looks right, not a phonetic transcript. The picture follows the voice: never stretch the audio to fit the mouth.

## A scene

`stage.js` composes a frame: a backdrop in the skin's style, the cast, captions. A scene file names it all and the same file renders in any skin:

```bash
python3 scripts/character_project.py --scene examples/09-story-characters/scene.json --skin cel-shaded --out project/
npx hyperframes render project -o raw.mp4 --quality delivery --fps 30
bash scripts/finish.sh --in raw.mp4 --out final.mp4 --seconds 14 --audio voice.wav
```

A scene has `width`, `height`, `duration`, `ground` (the y where feet stand), a `palette` for the backdrop, optional `hills` and `set` shapes (`layer: "back"` draws behind the hills), the `cast` (`character`, `x`, `scale`, `track`) and `captions`. A track may hold `"visemesFrom": { "words": "words.json", "from": 3.3, "to": 6, "lang": "en" }`; the builder turns it into the mouth track. `examples/09-story-characters/` is a 14-second scene with a walk, a point, two spoken lines, a laugh and a wave, built once and rendered as paper cut-out and as anime.

For feet that do not slide on a walk, give the move track `B2M.strideSpeed(character, "walk", steps) * scale` units per second.

### Characters in a 3D set

```bash
python3 scripts/character_project.py --stage3d --cast child,crow --seconds 6 --out project/
```

`templates/threejs/characters-stage.html` puts each character on its own canvas, uses that canvas as the texture of a plane that faces the camera, and stands the planes in a Three.js set: a ground, four trees, a rock, a hut, a sun and a camera that moves. The frame is deterministic like the 2D stage. Edit the `ACTORS` list for who stands where and what they do.

## Known limits

- The cast is in a side view; a character that turns to face the camera mid-scene uses the front drawing for a close-up only (`view: "front"`), not a continuous turn.
- Skins style vector shapes. A part picture is drawn as it is, with a drop shadow in the paper skin only.
- Lip sync is letter rules, not a speech model: it is right for the mouth and wrong for pronunciation, and Hindi is approximate.
- The walk and run are side-view cycles; stairs, slopes and turning on the spot are not built in.
- A crow's beak and a robot's picture mouth open by amount, so some shapes (`rest` and `MBP`) look alike there.
- Shadow puppets are jointless in the tradition; here they keep the rig's joints. The skin makes the look, not the movement.

## Bring your own art: image parts

A part can show a PNG or WebP picture instead of vector shapes. That way art from any image model or drawing app can be rigged and animated. Prepare it like this:

1. **One image per part.** Cut the head, torso, upper arm, lower arm, hand, thigh, shin and foot into separate files, plus the eyes and brows if they should move. Keep the far arm and far leg as their own pictures (darker is fine).
2. **Transparent background**, 8-bit RGBA, saved as PNG or WebP. Trim extra margin, but keep the part whole: the overlap where a limb tucks under the body must be drawn, or a gap shows when the joint turns.
3. **The same scale for every part.** Pick one size for the character (the demo is 226 units tall at 2 pixels per unit) and size every picture to it. Draw at twice the size you will show, so it stays sharp at 1080p and 4K.
4. **A pivot for every part.** Write each picture's rectangle in the shared coordinate system (`image: { "src", "x", "y", "w", "h" }`, `y = 0` at the feet, facing right) and set the part's `pivot` to the joint, in the same coordinates. Read both off your drawing app: the top-left of the layer, and the point the joint turns about.
5. **Mouth shapes as separate images.** Draw nine, one per shape: `rest`, `AI`, `E`, `O`, `U`, `MBP`, `FV`, `L`, `etc`. Use `"mouth": { "kind": "images", "images": { "rest": { ... }, "AI": { ... } } }`; `rest` is required and stands in for any missing shape.
6. **Set parents and order.** `parent` links each part to the one it hangs from; `z` is the draw order (far limbs lowest, the head and near arm above the torso).

`src` is a path relative to the character file, or a `data:image/png;base64,` URI. `scripts/character_project.py` inlines pictures as data URIs when it builds a page, so a render needs no file. Run `validate.py` on the file: it checks that every picture exists, is a PNG or WebP, and that an image mouth has `rest`. Then render a sheet with `character_sheet.py --file`.

`image-demo/make_tin_bot.py` is a complete example: it draws every part and every mouth with the Python standard library and writes `tin-bot.json`. Run it, open the sheet, and swap its pictures for yours. Skins style vector shapes; a picture is drawn as it is, with a drop shadow in the paper skin. For a flat silhouette or an ink outline, prepare the picture that way.
