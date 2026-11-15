# Changelog

All notable changes to brief2mp4. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-11-15

### Added
- **Optional 3D pack** (`plugin/skills/brief2mp4/3d/`): CAD and mesh models to GLB, material presets, deterministic Jolt physics bakes, shot JSON to a frame-seekable HyperFrames project, and a Blender hero-render route. Installs per component (`core`, `cad`, `blender`) with `install.sh --with-3d` or `install.ps1 -With3D`. The skill detects it and falls back to the Three.js template when it is missing.
- **SETUP.md**: step-by-step instructions an agent follows to set up a machine on macOS, Windows or Linux, ending with a two-minute first render.
- **Windows support**: `install.ps1` (PowerShell 5.1 and 7, optional winget install of Node, ffmpeg and Git), Git Bash guidance in the skill.
- `scripts/doctor.sh` (with `--json`): checks every tool and prints the install command for this OS. `scripts/detect_3d.sh`. `scripts/bounds.py`: measures where content sits in a still and checks margins and safe zones, standard library only. `scripts/vendor_libs.sh`: pinned GSAP, three.js and fonts copied into a project. `sound_bed.sh --ticks` for click accents.
- `references/formats.md`: beat sheets, tool routes and checks for 2D explainers, maths and algorithms, tutorial intros, stories and skits, vertical Shorts and Reels (with safe zones), data stories, product launches, logo stings, kinetic type and captions.
- Examples 05 (a 20 s 2D explainer) and 06 (a 15 s vertical Short), each with a sample report from a real run.
- `references/pipelines.md`: architecture diagram, route per beat, recipes for mixed pipelines.
- `references/ecosystem.md`: 45+ open-source motion, 3D, capture and agent-skill repos with licences, when each beats the default, and how to bring its output in frame-exact.
- Example 04: a 3D product brief (parts drop and settle, exploded view, title).
- `docs/`: getting started (per OS, with a flow diagram), architecture (the loop, routing, determinism, the 3D pack) and a 3D walkthrough of example 04.
- Tests (`tests/`, 46 including render tests) and CI on macOS, Ubuntu and Windows.
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
