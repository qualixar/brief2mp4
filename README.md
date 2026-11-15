<p align="center">
  <img src="assets/banner.png" alt="brief2mp4: write a brief, get a checked MP4" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-16130F"></a>
  <img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-FF5A1F">
  <img alt="Codex plugin" src="https://img.shields.io/badge/Codex-plugin-FF5A1F">
  <img alt="Version 0.2.0" src="https://img.shields.io/badge/version-0.2.0-16130F">
</p>

**brief2mp4 is a free skill for Claude Code and Codex. You paste a written video brief; the agent builds the video, renders it, measures the file, checks every line of your brief against real frames, fixes what fails, and hands you `final.mp4` with a report.**

It covers kinetic type and 2D motion (HyperFrames), stylised 3D (Three.js) and realistic product shots (Blender), and finishes every file with ffmpeg. Everything runs on your own machine.

## What it made from one brief

This is example brief 01, pasted as written. The agent wrote a spec, built it in HyperFrames, rendered, finished the file and checked it, with no edits by hand.

<p align="center">
  <img src="assets/demo-brief01.gif" alt="Kinetic type film: Ideas are cheap. Finished is rare. Finish something today." width="800">
</p>

The file it delivered measures 12.000 s, 1920x1080, 30 fps, H.264 with AAC 48 kHz stereo, and the delivery check passed. Its [report](examples/01-kinetic-type/SAMPLE-REPORT.md) lists each requirement of the brief with the evidence for it: which still shows which line, the measured headline height (126 px against a 120 px minimum), the text bounds against the safe margins, the loudness at each sound accent.

## Watch the video

The video that goes with this repo is on YouTube: [youtu.be/l9mEZQon6JM](https://youtu.be/l9mEZQon6JM).

## Install

There are two ways in each app. Pick one per app; installing both ways gives you two copies of the same skill.

### Claude Code

As a plugin, inside Claude Code:

```
/plugin marketplace add qualixar/brief2mp4
/plugin install brief2mp4@brief2mp4
```

On Claude Code 2.1.275 or later this also works in one line: `/plugin install brief2mp4 --marketplace qualixar/brief2mp4`.

### Codex

As a plugin, in a terminal:

```bash
codex plugin marketplace add qualixar/brief2mp4
codex plugin add brief2mp4@brief2mp4
```

The Codex desktop app reads the same settings, so the plugin shows up there too.

### Both apps at once, with the script

```bash
git clone https://github.com/qualixar/brief2mp4.git && bash brief2mp4/install.sh
```

This copies the skill into `~/.claude/skills/brief2mp4` and `~/.codex/skills/brief2mp4` and checks that Node, ffmpeg and Blender are on your machine. Use `--claude` or `--codex` for one app only.

### No terminal

Paste this into Claude Code or Codex and let the agent do it:

> Clone https://github.com/qualixar/brief2mp4 into a temporary folder and run its install.sh.

Whichever way you install, start a new session afterwards so the app loads the skill.

## Use it

Open a folder for the video, start a session and send:

> Use the brief2mp4 skill to make the video in this brief: *(paste your brief)*

When it says it is done, send one follow-up:

> Check it against the brief.

The skill reads that as an instruction to go back to your original brief, line by line, show the evidence for each line, fix anything that falls short and render again. In our test of brief 01 this follow-up caught a real miss: the headlines cleared the 120 px minimum by only a few pixels, so it enlarged them and rendered again, and the delivery check still passed.

## How it works

The skill gives the agent one loop and the scripts to run it.

1. **Spec.** Before any code it writes `SPEC.md`: size, frame rate, exact duration, codecs and loudness; every on-screen word copied exactly; the palette; a beat sheet with times; and a "done when" list with one checkable line per requirement.
2. **Build.** It picks the tool that fits the brief and starts from a template that already renders.
3. **Self-check.** It measures the file with `check_delivery.sh`, pulls stills at the important moments with `contact_sheet.sh`, looks at them, and marks every line of the list met or not met, with evidence.
4. **Fix.** It fixes the worst miss first and renders again, for up to three rounds.
5. **Deliver.** You get `final.mp4` and a `REPORT.md` that says what was checked, how, and what is still open.

| The brief asks for | The skill uses |
|---|---|
| Type, layouts, UI, charts, 2D motion | [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML, CSS and GSAP to MP4) |
| Stylised 3D, particles, camera moves | [Three.js](https://threejs.org) inside HyperFrames, driven by the timeline so every frame renders the same way twice |
| Realistic products, materials, soft light | [Blender](https://www.blender.org), scripted in Python and rendered without opening a window |
| Sound, joins, exact length, loudness, encoding | [ffmpeg](https://ffmpeg.org) |

## Example briefs

| Brief | Tool | Length |
|---|---|---|
| [01 kinetic type](examples/01-kinetic-type/BRIEF.md): "Finish something today" | HyperFrames | 12 s |
| [02 Three.js](examples/02-threejs-orbit/BRIEF.md): a low-poly planet, three moons, "ORBIT" | Three.js | 10 s |
| [03 Blender](examples/03-blender-product/BRIEF.md): a smart-speaker turntable, "LISTEN." | Blender | 8 s |

## Write your own brief

The agent guesses less when the brief says more. A brief that works well has these parts:

```markdown
Length and size: 15 s, 1920x1080, 30 fps.
Look: background #F2EDE4, text #16130F, one accent #FF5A1F. Font: Space Grotesk Bold.
Words on screen, exactly: "First line." / "Second line." / "Last line."
What happens when:
- 0.0 to 4.0 s: the first line types on, one word at a time.
- 4.0 s: a hard cut to the second line.
- 9.0 s: the last line lands and holds still until the end.
Sound: a quiet bed with a low hit at 4.0 s.
Done when: every line is readable, nothing touches the frame edge, headlines are at least 100 px tall.
```

The "done when" lines matter most, because they are what the self-check measures. The free guide at [qualixar.com/learn/guides/brief2mp4-guide](https://qualixar.com/learn/guides/brief2mp4-guide) goes through brief writing, each tool and the checks in more detail.

## Requirements

- Claude Code or Codex, desktop app or command line.
- Node.js 22 or newer and ffmpeg, for every brief.
- Blender, only for Blender briefs (tested with 5.2; 4.2 or newer should work).

HyperFrames runs through `npx`, so there is nothing else to install. The install script tells you what is missing.

## FAQ

**Does it cost anything?** The skill is free and MIT licensed. The agent runs on your own Claude Code or Codex plan, and the rendering happens on your machine.

**Which models has it been tested with?** Claude Code on Sonnet made brief 01 in 98 seconds, start to finish, with the delivery check passing. Stronger models handle harder briefs better, but the loop and the checks are the same for all of them.

**Does it upload my files anywhere?** No. Rendering, checks and the report all stay in your project folder. The only network traffic is what the tools themselves fetch: HyperFrames and Three.js packages through npm, and any web fonts your brief names.

**What about music?** `sound_bed.sh` makes a quiet original placeholder so the file is never silent. For a real soundtrack, pass your own licensed track to `finish.sh --audio`.

**Can I use the scripts without an agent?** Yes. They are plain bash and ffmpeg. For example, from a clone of this repo:

```bash
bash plugin/skills/brief2mp4/scripts/check_delivery.sh my-video.mp4 --seconds 30
```

**Does it work on Windows or Linux?** It is tested on macOS. The scripts are bash and ffmpeg, so Linux should work. On Windows, use WSL; that is untested.

**How do I update or remove it?** Claude Code plugin: `claude plugin update brief2mp4@brief2mp4`, or `claude plugin uninstall brief2mp4@brief2mp4`. Codex plugin: `codex plugin marketplace upgrade`, or `codex plugin remove brief2mp4@brief2mp4`. Script install: `git pull` then `bash install.sh` again, or `bash install.sh --uninstall`. The script only replaces or removes a folder it created; if you already had a `brief2mp4` folder in your skills, it is moved aside with a timestamp, never deleted.

## What is inside

```
.claude-plugin/marketplace.json    marketplace entry, read by Claude Code and Codex
plugin/
  .claude-plugin/plugin.json       Claude Code plugin manifest
  .codex-plugin/plugin.json        Codex plugin manifest
  skills/brief2mp4/
    SKILL.md                       the loop the agent follows
    references/                    HyperFrames, Three.js, Blender and ffmpeg notes
    scripts/
      finish.sh                    any render to a delivery MP4 (exact length, H.264/AAC, -14 LUFS)
      check_delivery.sh            PASS, WARN or FAIL against the delivery spec
      contact_sheet.sh             stills at chosen moments, plus a grid
      sound_bed.sh                 a quiet original placeholder soundtrack
    templates/
      SPEC.md                      the spec the agent fills in
      threejs/index.html           a Three.js scene that renders frame by frame
      blender/scene.py             a scripted Blender turntable
examples/                          three briefs and a sample report
install.sh                         script install, update or removal for both apps
```

## Licence

MIT. Use it, change it, ship videos with it. HyperFrames (Apache-2.0), Three.js (MIT), GSAP, Blender (GPL) and ffmpeg (LGPL/GPL) keep their own licences; this repo does not bundle them.

Made by [Varun Pratap Bhardwaj](https://github.com/qualixar).
