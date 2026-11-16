# REPORT: Brief 08, one brief, five worlds

`final.mp4`: 25.0 s, 1920x1080, 30 fps, H.264 + AAC. One camera move through the page, the city, the chart world, the galaxy and the title, looping back to the first frame. Brief used exactly as written (`BRIEF.md`, the upgraded 25 s version). Every number below is in `checks.txt`, produced by `bash run_checks.sh <skill>/scripts`.

## Delivery check
`check_delivery.sh final.mp4 --seconds 25 --size 1920x1080 --fps 30` ends with `RESULT: PASS (final.mp4)` (12 PASS lines, no WARN, no FAIL).

## Done when (from the brief)
| Line | Result | Evidence |
|---|---|---|
| ffprobe reports 1920x1080, 30 fps, 25.0 s, H.264 + AAC | met | `codec_name=h264 width=1920 height=1080 r_frame_rate=30/1 nb_frames=750`, `codec_name=aac sample_rate=48000 channels=2`, `duration=25.000000` |
| Still at 1.8 s shows a word of line 2 off the page | met | `checks/t_001.80s.png`: "A", "city", "of", "light", "rises" are lifted tiles with saffron side walls and a glow under them; "out of these words." still flat on the page |
| Stills at 6.0, 11.5, 17.0, 22.0 s show city, chart, galaxy, title in palette colours | met | `checks/t_006.00s.png` (saffron towers, violet sky, magenta haze, coral street lights), `t_011.50s.png` (paper, coral/violet/saffron bars, ink line), `t_017.00s.png` (magenta arms, violet dust, saffron core, sky-blue stars on deep space), `t_022.00s.png` (paper title on indigo, saffron-to-coral underline) |
| scdet finds no cut | met | `scdet=threshold=10` (ffmpeg default): 0 cuts. Highest per-frame score in the whole file 4.249 at 8.87 s (the flight through the window); next 2.926 at 16.17 s |
| First and last frames match, SSIM >= 0.90 | met | frame 0 vs frame 749: `SSIM All:0.972693`. Command: `ffmpeg -i checks/first.png -i checks/last.png -lavfi ssim -f null -` |
| Title at least 150 px tall, still and readable 20.5-23.5 s | met | `bounds.py` on the binarised still (underline excluded): ink box 1604 x 290 px (clipped at the underline; font-size 320 px), identical box `x 164-1767, y 335-624` at 20.5, 22.0 and 23.5 s. SSIM of the binarised title area 20.5 vs 23.5 s: 0.998592 |
| All five chip texts exact, each readable in a still | met | `2D type · HyperFrames` in `t_001.80s.png`; `3D city · Three.js` in `t_006.00s.png`; `2D charts · HyperFrames + GSAP` in `t_011.50s.png`; `20,000 particles · Three.js` in `t_017.00s.png`; `finished · ffmpeg` in `t_022.00s.png`. Text comes from the `CHIPS` array in `city-layout.js`, copied from the brief |
| No pixel region reads as teal or mint | met | `hue_scan.py` over all 21 stills (hue 140-190 degrees, saturation > 0.35, value > 0.3): worst still 0.0009 % of sampled pixels (a handful of single compressed pixels at star edges, no region). I also looked at every still |
| Integrated loudness -16 LUFS within 1 LU | met | `I: -15.3 LUFS`, true peak -1.5 dBTP. See the loudness note below |

## Other lines of the brief
| Line | Result | Evidence |
|---|---|---|
| Frame 0: three lines, 56 px, paper, blinking saffron cursor | met | `t_000.00s.png`; CSS 112 px at 0.5 scale; cursor on for half of every second |
| Words peel from 1.0 s, first off the page by 1.8 s | met | first word starts 1.0 s, fully lifted 1.7 s |
| At least 60 towers, seeded | met | `node check_layout.mjs`: 67 city towers + 1 end tower, seed 20261116, second run identical |
| Bloom only on lit windows and street lights | mostly met | bloom threshold 0.9 in the city; walls, edges, sky and sun are under it. The coral beacon masts on some roofs also bloom |
| Five bars in sequence (coral, violet, saffron, coral, violet), a drawn line, three icons | met | `t_011.50s.png`, `t_013.50s.png`, `t_014.00s.png` |
| Chart is flat 2D on a plane inside the scene | met | HTML/SVG sheet placed with the camera matrix on the wall behind the window; camera stops square-on at 1 unit = 1 px |
| Tallest bar grows, camera rides it into space | met | `t_015.20s.png`, `t_016.20s.png`, `t_017.00s.png` |
| At least 20,000 particles | met | 27,000 (14,000 arm, 7,000 dust, 2,500 core, 3,500 stars), seeded |
| Galaxy shrinks to a saffron point that becomes the full stop | met | `t_019.60s.png`, `t_020.00s.png` (point sits where the full stop is in `t_020.50s.png`) |
| Subtitle 48 px, underline saffron to coral | met | CSS 48 px Space Grotesk Bold; ink box 491 x 44 px |
| One continuous move, no cuts, no fades to black | met | scdet above; `check_delivery`: no black stretch |
| Text at least 64 px from the frame edge | met | title still: all bright type inside the 64 px zone (`inside: true`, box x 91-1767, y 335-998); chips are CSS `left: 64px; bottom: 64px` |
| Chips 32 px Space Grotesk on a dark pill, cross-fading | met | CSS; cross-fades are 0.4 s wide and centred on 3.0, 9.0, 14.0, 20.0 s |
| Sound: rise per world, accent 1.2 s, whooshes 3.0 / 9.0 / 14.0 s, low accent 20.0 s | met by construction | `make_audio.sh`. Levels measured, not listened to (see open points) |

## Loudness note
`finish.sh` defaults to -14 LUFS. I ran it with `--lufs -15.3`. That lands at -15.3 LUFS, which is inside the brief's -16 +/- 1 window (-17 to -15) and also inside the default window of `check_delivery.sh` (-14 +/- 1.5), so the check command passes as written without `--lufs`. With `--lufs -16` the same check also passes.

## Stills I opened and looked at
`checks/sheet.png` (all 21) and, at half size or larger, 0, 1.8, 3, 6, 8.7, 9, 11.5, 14, 17, 20, 22, 24.9 s. Also 13.5, 15.2, 16.2, 18.5, 19.6, 20.5, 23.5, 24.2 s on the sheet. Spelling of every line, chip and title checked against the brief.

## Render settings
- HyperFrames 0.8.216: `npx hyperframes render . -o render.mp4 --quality delivery --workers 8 --fps 30`. Render time 10.6 s (12 s wall) on the M5 Pro.
- three 0.170.0 and GSAP 3.15.0 vendored by `vendor_libs.sh`; UnrealBloomPass, EffectComposer and ShaderPass copied from the same three 0.170.0 package into `vendor/three-addons/`. Fonts vendored (JetBrains Mono, Space Grotesk). No network at render time.
- Determinism: `draw(t)` is the only source of a frame; mulberry32 seeds 20261116 (city), 77 (embers), 4242 (galaxy); no `Math.random`, no wall clock (the composer is called with a fixed delta).
- Finish: `finish.sh --in render.mp4 --out final.mp4 --seconds 25 --audio bed.wav --lufs -15.3` (H.264 CRF 18 slow, AAC 192k).
- Fix rounds used: 1 after the first full render (chart starts 0.3 s sooner). Before that, stills-only rounds fixed bloom strength, the wall top and the galaxy entry speed.
- The 3D pack was not used; all 3D is hand-built Three.js.

## Open points
1. The still at exactly 9.0 s is plain paper with the two chips mid cross-fade: the camera has just come through the window and the chart starts drawing at 9.1 s.
2. During each 0.4 s chip cross-fade the two texts overlap and are not readable. The brief asks for a cross-fade in one place, so I kept it.
3. Lines 1 and 3 of the brief leave the first page between 2.05 and 3.4 s, before the page beat ends at 3.0 s, because an HTML word cannot be hidden behind a 3D block.
4. During the title hold the type is still, but the faint ruled lines behind it drift slowly with the camera.
5. I judged stills and measurements only. Nobody has watched it in motion or listened to the soundtrack yet.
6. `hyperframes lint`: 0 errors, warnings only (one large composition file, nested timeline element).
