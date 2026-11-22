# Changelog

All notable changes to brief2mp4. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.8.0] - Unreleased

### Added
- **3D pack upgrade.** Six tested Blender motion recipes in `3d/templates/recipes/` (`b2m3d recipe list` and `recipe run NAME`): a seamless loop (frame 1 equals the last frame, cyclic curves), retime between timeline markers (shape-preserving), cloth drop onto an object, rigid bodies with hinge or ball constraints (a chain or a pendulum), folding with shape keys, and a forward walk with planted feet and two-bone IK. Each reports measurements with an `ok` verdict and warnings, refuses settings that cannot work, and has a test that asserts its numbers with a real Blender (skipped when Blender is absent), with a control that must fail (a naive walk, a chain with its constraints deleted, a floor with no collider, a one-key fold). Their plain arithmetic is in `b2m_math.py`, which imports no Blender and is tested in CI on every system. `b2m3d recipe run` passes `--python-exit-code 1`, so a recipe error reaches the caller. If you installed the 3D pack before, run `install_3d.sh` again: the installed copy of the pack does not know `recipe` until then.
- **Live Blender route** through blender-mcp, next to the headless route, which stays the default for rendering: `references/blender-live.md` (live or headless, install, safety, sending a recipe) and a `stage` option so recipes run politely inside an open scene.
- **Optional generators, never bundled**: `scripts/gen3d.py` calls Hunyuan3D-2 or TRELLIS when you have installed them (image or text to a GLB, with a credit and licence sidecar), and `b2m_flip_bake.py` bakes and renders a FLIP Fluids liquid. Licence notes, with the project's own text quoted, in `references/generators-3d.md` and `references/ecosystem.md`. TRELLIS's GLB export runs components licensed for research or evaluation only (nvdiffrast, a Gaussian rasterizer), so `gen3d.py` runs it only with `--non-commercial` and prints their install line only on request; Hunyuan3D-2's Acceptable Use Policy (label published output as machine-generated) is in its note and sidecar.
- **One look for the recipes.** `--look studio` (a seamless backdrop with no horizon, soft key, fill, rim and wall wash, ray-traced light), `--orbit` (a constant camera turn), captions as small lower thirds that fade in and out (`--caption-px`, `--caption-frames`, `--caption-fade`). Per recipe: a jointed mannequin with an upright walk (hips lowest in double support, arm swing, chest twist, lead room), a chain that frames its whole swing (`frame_margin` reported and tested) with a stand and rounded links, two-colour paper with thickness and a follow camera for folds, cloth thickness and sheen.
- `examples/10-3d-motion`: a 24-second film in one studio, five recipes, dissolves on the bar lines of a CC0 track.
- **Film mode**: one brief in a project folder, a finished explainer or documentary out, with every stage's file on disk (`scripts/film.py`: story, script, storyboard, assets, voice, retime, build, captions, mix, render, check, report; each stage skippable and re-runnable). New reference section "Explainer and documentary (film mode)" in `references/formats.md`.
- `scripts/fetch_archive.py`: archive photos, maps and documents from Wikimedia Commons and Openverse, public domain, CC0 and CC BY only (ShareAlike, NonCommercial, NoDerivatives and unknown are rejected in the request and again on every answer), with `ASSETS.json` credits.
- `scripts/make_map.py`: a country or region map as SVG with markers, labels and routes, from Natural Earth (public domain), shipped as a 54 KB subset so it works offline; the projection is chosen for the region.
- `scripts/sfx_synth.py`: whoosh (without white noise), tick, thud, paper, typewriter, riser and hit made in code, seeded, held under -1 dBTP.
- `scripts/split_takes.py`: one recording cut into per-line WAVs by pauses and, when available, word timings (a words file or whisper.cpp); the voice is never stretched.
- `scripts/retime.py`: the picture re-timed to the measured voice, with beat-grid snapping and resolved sound cues.
- `scripts/mix.py`: voice, music ducked 15 dB under the voice with an exact envelope, effects pinned by their peak, -14 LUFS.
- `templates/film/`: the archive desk documentary look for HyperFrames (dark editorial layout, slow push-ins at one velocity, typeset captions, map overlays, date stamps, a ledger counter).
- Optional routes for F5-TTS (voice) and MusicGen (music), with their non-commercial model licence notes; credits for Natural Earth, Wikimedia Commons and whisper.cpp in `references/ecosystem.md`.
- Craft checks: `scripts/check_seams.py` (one-frame flicker, pops at act joins, hard and soft cuts, true freezes; run by `check_delivery.sh`), `scripts/check_clutter.py` with `scripts/dom_boxes.js` (no card on card, 24 px between text, at most 4 text blocks, nothing clipped), `scripts/ocr_sweep.sh` (placeholder text and leaked paths in the finished frames), `scripts/beat_grid.py` and `scripts/cut_points.sh` (beats and scene cuts), and `scripts/fetch_music.py` (CC0 and CC BY audio from Openverse with ATTRIBUTION.md).
- References: `motion-doctrine.md`, `render-traps.md`, `review-checklist.md` and `sound.md`.

### Changed
- A check that could not measure never passes. Decode errors, truncated files, a broken tesseract, a page with no timeline or an empty box file are FAILs; a missing optional tool is a SKIP with exit 3, and `check_delivery.sh` then ends `RESULT: INCOMPLETE` (exit 3) instead of `RESULT: PASS`.
- `check_seams.py` reads frames at a constant rate, so times in variable-frame-rate recordings are real seconds.
- `fetch_music.py` streams downloads under a size cap, downloads only from https:// links, and counts `--pick` from 1.

## [0.7.0] - 2026-11-22

### Added
- **24 new art forms, 82 in all**, each with a researched record, a tested demo and a generated reference page:
  - 3D looks: stylised 3D cartoon, toon 3D, point cloud, tilt-shift miniature diorama, 2.5D parallax;
  - screens and cinema (a new family): synthwave, cyberpunk night city, ASCII art, 1-bit dither, CRT terminal, hologram HUD, thermal camera, silent film, newsreel, film noir, archive documentary (pan and zoom over stills);
  - information: maths diagram, sticker explainer, Memphis design;
  - abstract and generative (a new family): particles, liquid metaball, flow-field generative, psychedelic, Bauhaus geometric.
- **LightCraft in the edit pack** (`light`, v0.21.1): pinned like the other five apps, with SHA-256 checked against the release's SHA256SUMS and the hash pinned here, and the signature checked against the same key. New recipe `edit/recipes/light_grade.sh` grades a still with a built-in preset and leaves the original untouched. The edit pack now installs six free editors.
- The art forms guide (`docs/art-forms-guide/`, PDF) is rebuilt for all 82 forms: 87 pages, with lead pages for the new families and counts taken from the data.

### Changed
- The README picture shows one frame of all 82 forms.

### Fixed
- `docs/art-forms-guide/build.py` had a syntax error on its last lines.

## [0.6.0] - 2026-11-22

### Added
- **28 new art forms, 58 in all**, each with a researched record, a tested demo and a generated reference page:
  - painting and drawing: pencil sketch, charcoal, oil painting and impasto, gouache storybook, crayon and oil pastel, chalkboard, one continuous line, paint-on-glass, sand animation;
  - folk and print traditions (a new family): Madhubani, Warli, Pattachitra, Gond, Indian miniature, engraving, silkscreen poster, art deco, stained glass, ukiyo-e;
  - anime and cartoon: retro anime, manga, chibi, modern TV cartoon, gothic cartoon;
  - craft: pop-up book, papercut and sanjhi, brick toy, string puppet and kathputli.
- Folk records name the region and community each tradition comes from, and say the demo is a code study of the visual rules, not the craft itself.
- `art-forms/looks-files.json` lists the demo files; the gallery, the browser check and the page builder all read it, so new looks go in their own file.
- `tests/art_forms/contact_sheet.mjs`: renders chosen looks at chosen times into one PNG for review, and router cases for the new forms.

### Changed
- Chalkboard is its own form; whiteboard keeps the marker look. Whiteboard and line art drop the keywords that now belong to chalkboard and one continuous line.
- The README picture shows one frame of every form.

## [0.5.0] - 2026-11-21

### Added
- **Character kit** (`plugin/skills/brief2mp4/characters/`): characters that hold poses, walk, blink and talk, in plain JavaScript and JSON with no new dependency. Every frame is a pure function of time.
  - `rig.js`, `poses.js`: 15 named poses, walk, run, talk and blink cycles, steps per second for held drawings.
  - Six skins on the same rig: `paper-cutout`, `cel-shaded`, `line-art`, `shadow-puppet` (hinged jaw, rods, light set pieces), `motion-comic`, `flat-explainer`.
  - A starter cast (child, adult, crow, tomato chef), a character schema and validator, and image parts so PNG or WebP art can be rigged (`image-demo/`).
  - Scenes: `schema/scene.schema.json` and `validate_scene.py`; moves to absolute positions with `walk` and `facing`; off-screen and low-contrast warnings; captions that wrap, scale and stay clear of the characters.
- `scripts/lipsync.py`: word timings to nine mouth shapes, for English and Devanagari Hindi, with a WAV loudness fallback.
- `scripts/standin_voice.py` (a preview voice from word timings), `scripts/character_sheet.py` (PNG sheets), `scripts/character_project.py` (a scene, or the 2D-in-3D starter, to a HyperFrames project; `--character-file` for your own characters).
- `templates/threejs/characters-stage.html`: rigged 2D characters as camera-facing cards in a Three.js set.
- `scripts/vendor_libs.ps1`: library vendoring on Windows, pinned to the same versions as `vendor_libs.sh`.
- `examples/09-story-characters/`: a boy and a crow argue over a kite, rendered in three skins from one scene.

### Changed
- Briefs with characters, dialogue or a short story now route to the character kit (`references/formats.md`, `art_route.py`).

### Fixed
- `.gitattributes` pins LF for every text file and marks fonts, PDFs and videos as binary, so Windows checkouts no longer turn HTML templates into CRLF.

## [0.4.0] - 2026-11-18

### Added
- **Art forms.** Thirty looks for animated video, each with its own reference page: what makes it read as that form, its timing, how to build it in HyperFrames, canvas, SVG or Three.js, the assets it needs, the sound that fits, what makes it look wrong, and sources. Craft and handmade (claymation, stop-motion, paper cut-out, felt, origami, shadow puppetry, collage, risograph), drawn and painted (anime and cel shading, flat explainer, whiteboard and chalkboard, watercolour, ink wash, line art, rotoscope, motion comic, UPA mid-century, rubber-hose, linocut), geometry and 3D (isometric, low-poly, voxel, pixel art, product render), type, data and retro (kinetic typography, infographic, lyric video, VHS and glitch, blueprint, neon sign).
- `art-forms/looks.js`: 31 small demos, one per look, each a pure function of time, with `art-forms/gallery.html` to view them.
- `scripts/art_route.py`: proposes an art form from a brief and says why, or says that none fits.
- `scripts/build_art_forms.py`: generates the index and the 30 pages from `references/art-forms.json` and the demo code, so they cannot drift apart.
- Tests: `tests/test_art_forms.py` (data, generated pages, router, and a ban on clocks and unseeded randomness in the demos) and `tests/art_forms/check_looks.mjs`, which draws every look in headless Chrome and checks that it paints, changes over time and gives identical pixels when the same time is drawn twice.

- `docs/art-forms-guide/`: a 35-page companion guide as a PDF, with its editable HTML, CSS and Python source.

### Changed
- **brief2motion comes with brief2mp4.** The plugin now lists brief2motion 1.0.0 as a dependency, so installing or updating brief2mp4 in Claude Code installs brief2motion too: briefs for websites and briefs for videos, one install. The marketplace entry for brief2motion moves to 1.0.0.

### Notes
- Tested on macOS with Chrome 157. The demos are checked as browser pictures; no art-form video was rendered through HyperFrames for this change.

## [0.3.0] - 2026-11-15

### Added
- **Optional 3D pack** (`plugin/skills/brief2mp4/3d/`): CAD and mesh models to GLB, material presets, deterministic Jolt physics bakes, shot JSON to a frame-seekable HyperFrames project, and a Blender hero-render route. Installs per component (`core`, `cad`, `blender`) with `install.sh --with-3d` or `install.ps1 -With3D`. The skill detects it and falls back to the Three.js template when it is missing.
- **Optional edit pack** (`plugin/skills/brief2mp4/edit/`): installs the command-line tools of five free ArtCraft editors by storytold (FilmCraft, SoundCraft, EffectCraft, PhotoCraft, VectorCraft; MIT or Apache-2.0) at pinned versions, on macOS, Windows and Linux. Each download must match both the release's SHA256SUMS.txt and the hash pinned in this repository, and the release signature is verified against a pinned key fingerprint when gpg is present. One tested recipe per app: a timeline cut with a dissolve and title, a voice-over mix with ducking, an animated title, a thumbnail and an SVG lower third. `install.sh --with-edit`, `install.ps1 -WithEdit`, `scripts/detect_edit.sh`, example 07.
- **SETUP.md**: step-by-step instructions an agent follows to set up a machine on macOS, Windows or Linux, ending with a two-minute first render.
- **Windows support**: `install.ps1` (PowerShell 5.1 and 7, optional winget install of Node, ffmpeg and Git), Git Bash guidance in the skill.
- `scripts/doctor.sh` (with `--json`): checks every tool and prints the install command for this OS. `scripts/detect_3d.sh`. `scripts/bounds.py`: measures where content sits in a still and checks margins and safe zones, standard library only. `scripts/vendor_libs.sh`: pinned GSAP, three.js and fonts copied into a project. `sound_bed.sh --ticks` for click accents.
- `references/formats.md`: beat sheets, tool routes and checks for 2D explainers, maths and algorithms, tutorial intros, stories and skits, vertical Shorts and Reels (with safe zones), data stories, product launches, logo stings, kinetic type and captions.
- Examples 05 (a 20 s 2D explainer) and 06 (a 15 s vertical Short), each with a sample report from a real run.
- `references/pipelines.md`: architecture diagram, route per beat, recipes for mixed pipelines.
- `references/ecosystem.md`: 45+ open-source motion, 3D, capture and agent-skill repos with licences, when each beats the default, and how to bring its output in frame-exact.
- Example 04: a 3D product brief (parts drop and settle, exploded view, title).
- `docs/`: getting started (per OS, with a flow diagram), architecture (the loop, routing, determinism, the 3D pack) and a 3D walkthrough of example 04.
- Tests (`tests/`, 97: 76 fast, 21 that render or download, run with `--slow`) and CI on macOS, Ubuntu and Windows, including Windows PowerShell 5.1.
- `AGENTS.md` and `CLAUDE.md` so an agent opened in a clone knows what to do; CONTRIBUTING, SECURITY, code of conduct, issue and PR templates.

### Fixed (from an independent pre-release audit)
- Windows: a `.gitattributes` keeps bash scripts on LF line endings, so they run under Git Bash after a Windows checkout.
- The 3D pack installs its own copy into `~/.brief2mp4/3d/pack`, so moving or deleting the clone or plugin cache no longer breaks it; `detect_3d` now checks that the pack actually imports, and understands the Windows venv layout.
- The 3D pack needs Python 3.12 or 3.13 (its pinned numpy and scipy do); docs and checks no longer claim 3.11. `B2M3D_PYTHON` picks a specific interpreter (for example from `uv` on Debian 12).
- `install_3d.ps1 -Components core,cad` works when typed in a PowerShell window as well as with `-File`.
- Text files in the 3D pack are read and written as UTF-8, so accented titles survive on Windows.
- The Three.js template loads GSAP and three.js from `vendor/` (new `scripts/vendor_libs.sh`), so renders never touch the network.
- `finish.sh` handles a silent soundtrack shorter than the video; `check_delivery.sh` no longer reports a dark designed background as black.
- Uninstall: `install.sh --uninstall --uninstall-3d` (or `install.ps1 -Uninstall -Uninstall3D`, `install_3d.sh --uninstall`) removes the 3D pack, only if the installer created it. On Windows a junctioned skill folder is unlinked, never emptied.
- Vertical safe zones in the formats guide and example 06 are now conservative (top 288, bottom 672, left 64, right 192 px at 1080x1920).
- `references/formats.md`: MathJax (SVG) vs KaTeX (HTML), Manim's LaTeX requirement, word timing with `hyperframes transcribe`, and holds vs loops for Shorts.

### Changed
- `finish.sh` now normalises loudness in two passes behind a soft limiter. Single-pass normalisation undershot on short clips with sharp hits (example 04 measured -16.0 LUFS against -14; it now measures -14.2).
- `install.sh` runs the doctor instead of its own checks, and accepts `--with-3d[=components]`.
- SKILL.md: doctor first, OS notes, 3D routing, links to the new references.

## [0.2.0] - 2026-11-14

### Added
- Claude Code and Codex plugin manifests and a marketplace entry; logo; README with the contest video and showcase.

## [0.1.0] - 2026-11-14

### Added
- First release: the spec, build, self-check, fix, deliver loop; HyperFrames, Three.js and Blender references; `finish.sh`, `check_delivery.sh`, `contact_sheet.sh`, `sound_bed.sh`; three example briefs and a sample report.

[0.3.0]: https://github.com/qualixar/brief2mp4/releases/tag/v0.3.0
[0.2.0]: https://github.com/qualixar/brief2mp4/compare/4b17df4...fda69b5
[0.1.0]: https://github.com/qualixar/brief2mp4/commit/4b17df4
