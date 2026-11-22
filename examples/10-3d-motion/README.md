# Example 10: five motions, one film

A 20-second film with five acts of 4 seconds, each made by one of the Blender motion recipes from the 3D pack: a cloth drop, a hinged chain, a sheet folding three times, a figure walking with its feet planted, and a seamless loop played twice. Every act is rendered headless; ffmpeg joins them.

## What is in this folder

| File | What it is |
|---|---|
| [BRIEF.md](BRIEF.md) | The brief, as it was written. Copy this. |
| [SPEC.md](SPEC.md) | The spec the build follows: delivery, exact text, look, beat sheet, done-when list. |
| [build.sh](build.sh) | Renders the five acts with the recipes, joins them, lays the soundtrack, finishes and runs `check_delivery.sh`. `--preview` renders three small stills per act. |

The MP4 is not in the repository. Build it yourself.

## Make it

You need Blender 4.2 or newer and ffmpeg. The recipes use only Blender's own Python, so the 3D pack's virtual environment is not needed to render.

```bash
cd examples/10-3d-motion
bash build.sh --preview     # a minute: three stills per act in build/preview, look at them first
bash build.sh               # the full film: build/final.mp4
```

Set `B2M3D_BLENDER` if Blender is not on your PATH (on macOS: `/Applications/Blender.app/Contents/MacOS/Blender`). The script prints each act's own measurement as it goes, and ends with `check_delivery.sh`.

## What each act uses

| Act | Recipe | The options it runs with | What it measures |
|---|---|---|---|
| 1 Cloth drop | `cloth` | `--object sphere --cloth-res 48 --drop-height 2.2 --delay 24` | where the sheet ended up |
| 2 Hinged chain | `rigid` | `--links 7 --release-angle 85 --anchor-height 3.5` | the largest gap at any joint |
| 3 Folding | `fold` | `--folds 3 --fold-frames 29` | the final width |
| 4 Walking, feet planted | `walk` | `--speed 1.2 --cycle-frames 32` | how far a planted foot moves in a frame |
| 5 Seamless loop | `loop` | `--loop-frames 61 --turns 1`, frames 1-60 played twice | the slope across the seam |

The options and what each recipe reports are in [references/blender-recipes.md](../../plugin/skills/brief2mp4/references/blender-recipes.md). To change the look of the whole film, change the palette line at the top of `build.sh`; to change one act, change its line and rerun the script (`bash build.sh` re-renders every act, so for one act, run that act's Blender line by hand).

## Check it

```bash
bash ../../plugin/skills/brief2mp4/scripts/contact_sheet.sh build/final.mp4 --at 1.5,5.5,9.5,13.5,17.5 --out build/checks
bash ../../plugin/skills/brief2mp4/scripts/check_delivery.sh build/final.mp4 --seconds 20 --joins 4,8,12,16
```

Run `python3 ../08-brief-becomes-world/hue_scan.py ../../plugin/skills/brief2mp4/scripts/bounds.py build/checks/t_0*.png` to confirm no teal or mint (it found 0 of 1,036,800 sampled pixels on the build described here). Open the stills: each caption should be spelled as in [SPEC.md](SPEC.md) and clear of the subject. The soundtrack is the skill's generated bed (a sine pad and a soft pulse, with a low accent where the cloth lands and a click at each act start); swap in music you have the rights to and run `scripts/finish.sh` again.
