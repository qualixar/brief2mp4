# AGENTS.md

This repository is the brief2mp4 skill for Claude Code and Codex: a written video brief goes in, a checked `final.mp4` comes out.

If the user asked you to install or set up brief2mp4, follow [SETUP.md](SETUP.md) step by step. It detects the operating system (macOS, Windows, Linux), installs what is missing with the user's permission, installs the skill, runs the doctor and does a two-minute first render.

If the user asked you to make a video, the skill itself is in [plugin/skills/brief2mp4/SKILL.md](plugin/skills/brief2mp4/SKILL.md). Read it and follow it.

If you are changing this repository:

- Run `bash tests/run_tests.sh` before you finish (add `--slow` for the render tests).
- Keep the skill self-contained: no personal paths, no network calls at render time, every script works from any folder.
- The 3D pack (`plugin/skills/brief2mp4/3d/`) is optional. The skill must keep working when it is not installed.
