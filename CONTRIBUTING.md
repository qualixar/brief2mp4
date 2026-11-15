# Contributing to brief2mp4

Thanks for helping. The most useful contributions are, in order: a brief that the skill got wrong (with the brief and what came out), a fix to a script or reference that makes the self-check catch more, and new example briefs with a passing report.

## Report a bad result

Open an issue with the **Brief result** template. Include the brief exactly as you sent it, your OS, the app and model (Claude Code or Codex), the doctor output (`bash plugin/skills/brief2mp4/scripts/doctor.sh`) and the `REPORT.md` the skill wrote. A still from `contact_sheet.sh` showing the miss helps most.

## Change the code

1. Fork, then branch from `main`.
2. Make the change. Keep files under 800 lines and scripts working from any folder.
3. Run the tests:
   ```bash
   bash tests/run_tests.sh          # fast checks
   bash tests/run_tests.sh --slow   # also renders, needs Node 22+, ffmpeg and the 3D pack
   ```
4. If you changed the skill's behaviour, update `SKILL.md`, the matching reference and `CHANGELOG.md` under an "Unreleased" heading at the top (add it if it is not there).
5. Open a pull request using the template.

## Rules for the skill itself

- **Determinism.** Every frame is a pure function of time. No wall clock, unseeded randomness or network at render time.
- **Optional stays optional.** The skill must work with only Node and ffmpeg. Blender and the 3D pack are detected, never assumed.
- **Cross-platform.** Scripts are bash and must run in macOS bash 3.2, Linux bash and Git Bash on Windows. Installers have a PowerShell twin.
- **Licences.** Only add dependencies under MIT, Apache-2.0, BSD, Zlib or similar. GPL tools may be used as external programs (like Blender), never bundled.
- **No personal data.** No absolute paths from your machine, tokens or private names in commits.

## Example briefs

A new example goes in `examples/NN-name/BRIEF.md`, in the format the README describes, with a "Done when" list. Add `SAMPLE-REPORT.md` from a real run if you can.

By contributing you agree that your work is released under the MIT licence of this repository.
