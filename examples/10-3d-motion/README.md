# Example 10: five motions, one studio

A 24-second film in five acts, each made by one of the Blender motion recipes from the 3D pack: a cloth drop, a hinged chain, a sheet folding three times, a mannequin walking with its feet planted, and a seamless loop. All five play in one pale seamless studio with one palette and one camera language, and dissolve into each other on the bar lines of the music. Every act is rendered headless; the five render in parallel; ffmpeg joins them.

Everything in the picture comes from the recipes' own options (`--look studio`, `--orbit`, the caption fade, and each recipe's look knobs). Nothing is modelled or painted by hand.

## What is in this folder

| File | What it is |
|---|---|
| [BRIEF.md](BRIEF.md) | The brief, as it was written. Copy this. |
| [SPEC.md](SPEC.md) | The spec the build follows: delivery, exact text, look, the cut, beat sheet, done-when list. |
| [build.sh](build.sh) | Renders the five acts with the recipes, dissolves them together, lays the music, finishes and runs `check_delivery.sh`. `--preview` renders three small stills per act. |
| [ATTRIBUTION.md](ATTRIBUTION.md) | The music: a CC0 track from Openverse, downloaded by `build.sh`. |

The MP4 and the music file are not in the repository. Build them yourself.

## Make it

You need Blender 4.2 or newer, ffmpeg, python3, and a network connection the first time (for the music). The recipes use only Blender's own Python, so the 3D pack's virtual environment is not needed to render.

```bash
cd examples/10-3d-motion
bash build.sh --preview     # under a minute: three stills per act in build/preview, look at them first
bash build.sh               # the full film: build/final.mp4 (about half an hour on a laptop with the five acts in parallel)
```

Set `B2M3D_BLENDER` if Blender is not on your PATH (on macOS: `/Applications/Blender.app/Contents/MacOS/Blender`). The script prints each act's own measurement and ends with `check_delivery.sh`.

## What each act uses

Every act also gets the shared line: the palette, `--look studio`, `--caption-px 38` and `--caption-fade 9`, at 64 samples.

| Act | Recipe | The options it runs with | What it measures |
|---|---|---|---|
| 1 Cloth drop | `cloth` | `--cloth-res 56 --quality 10 --self-collision --smooth-levels 1 --thickness 0.012 --sheen 0.4 --drop-height 1.6 --orbit 4` | where the sheet ended up (`centre_z` on top of the sphere) |
| 2 Hinged chain | `rigid` | `--links 7 --link-length 0.45 --release-angle 85 --anchor-height 3.5 --orbit 3` | the closest any joint comes to the frame edge (`frame_margin`) and the largest joint gap |
| 3 Folding | `fold` | `--folds 3 --fold-frames 34 --pause 9 --back "#3358c8" --thickness 0.004 --orbit 4` | the final width |
| 4 Walking, feet planted | `walk` | `--speed 0.95 --cycle-frames 34 --thigh 0.47 --shin 0.47 --hip-height 0.9 --bob 0.024` | how far a planted foot moves in a frame |
| 5 Seamless loop | `loop` | `--loop-frames 77 --turns 1 --glow 0`, frames 1-158 (the loop twice) | the slope across the seam |

The options and what each recipe reports are in [references/blender-recipes.md](../../plugin/skills/brief2mp4/references/blender-recipes.md). To change the look of the whole film, change the palette line at the top of `build.sh`; to change one act, change its line. `bash build.sh` re-renders every act; for one act, run that act's Blender line by hand.

## The cut

The track runs at 95 BPM, so two bars last 5.05 s. The acts join on every second bar line (frames 114, 265, 416 and 568) and the film ends at frame 720. Each act renders 6 frames past each of its joins, and the neighbours dissolve over those 12 frames, centred on the bar line. The music is cut 8.89 s into the track so that its first big downbeat lands on the first join, as the chain is released.

## Check it

```bash
bash ../../plugin/skills/brief2mp4/scripts/contact_sheet.sh build/final.mp4 --out build/checks          # a frame every second
bash ../../plugin/skills/brief2mp4/scripts/contact_sheet.sh build/final.mp4 --at 2,6.3,11.3,16.4,21 --out build/captions
bash ../../plugin/skills/brief2mp4/scripts/check_delivery.sh build/final.mp4 --seconds 24 --joins 3.8,8.833,13.867,18.933 --strict-flicker
```

Run `python3 ../08-brief-becomes-world/hue_scan.py ../../plugin/skills/brief2mp4/scripts/bounds.py build/checks/t_0*.png` to confirm no teal or mint (0 of 1,036,800 sampled pixels in every still of the build described here). Open the stills: each caption should be spelled as in [SPEC.md](SPEC.md) and clear of the subject, and no act should crop its subject.
