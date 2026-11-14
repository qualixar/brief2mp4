# brief2mp4

A free skill that teaches Claude Code and Codex to turn a written brief into a finished, checked MP4: kinetic type, 3D scenes, product shots. MIT licensed. No account, no paywall.

```bash
git clone https://github.com/qualixar/brief2mp4.git && bash brief2mp4/install.sh
```

That installs the skill into `~/.claude/skills/brief2mp4` and `~/.codex/skills/brief2mp4`. Start a new session in either app and ask:

> Use the brief2mp4 skill to make the video in this brief: *(paste one of the briefs below)*

When it says it is done, send one follow-up:

> Check it against the brief.

The skill treats that as an instruction to re-read your original brief line by line, show the evidence for each line, fix what fails, and render again.

## What it does

The skill gives the agent one working loop and the tools to run it:

1. **Spec.** Before writing code it writes `SPEC.md`: the delivery spec (size, frame rate, exact duration, codecs, loudness), every on-screen word copied exactly, the palette, a beat sheet with times, and a "done when" checklist with one checkable line per requirement.
2. **Build.** It picks the right tool for the brief and starts from a template that already renders.
3. **Self-check.** It measures the file (`check_delivery.sh`), pulls stills at the important moments (`contact_sheet.sh`), looks at them, and marks every checklist line met or not met with evidence.
4. **Fix.** It fixes the worst miss first and re-renders, up to three rounds.
5. **Deliver.** `final.mp4` plus a `REPORT.md` that says what was checked, how, and what is still open.

| The brief asks for | The skill uses |
|---|---|
| Type, layouts, UI, charts, 2D motion | [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML + CSS + GSAP to MP4) |
| Stylised 3D, particles, camera moves | [Three.js](https://threejs.org) inside HyperFrames, driven by the timeline so every frame is repeatable |
| Realistic products, materials, soft light | [Blender](https://www.blender.org), scripted in Python and rendered without opening a window |
| Sound, joins, exact length, loudness, encoding | [ffmpeg](https://ffmpeg.org) |

## Try it: three example briefs

| Brief | Tool | Length |
|---|---|---|
| [01 kinetic type](examples/01-kinetic-type/BRIEF.md): "Finish something today" | HyperFrames | 12 s |
| [02 Three.js](examples/02-threejs-orbit/BRIEF.md): a low-poly planet, three moons, "ORBIT" | Three.js | 10 s |
| [03 Blender](examples/03-blender-product/BRIEF.md): a smart-speaker turntable, "LISTEN." | Blender | 8 s |

Copy a brief, paste it after the request above, and let it run. Then write your own: say how long, what size, which colours, the exact words, and what should happen when. The more of that you write down, the less the agent has to guess.

## Requirements

- Claude Code or Codex (desktop app or CLI)
- Node.js 22 or newer and ffmpeg, for every brief
- Blender, only for Blender briefs (tested with 5.2; 4.2 or newer should work)

The installer checks these and tells you what is missing. HyperFrames runs through `npx`, so there is nothing else to install.

## What is inside

```
skill/brief2mp4/
  SKILL.md                 the loop the agent follows
  references/              HyperFrames, Three.js, Blender, ffmpeg notes
  scripts/
    finish.sh              any render -> delivery MP4 (exact length, H.264/AAC, -14 LUFS)
    check_delivery.sh      PASS/WARN/FAIL against the delivery spec
    contact_sheet.sh       stills at chosen moments, plus a grid
    sound_bed.sh           a quiet original placeholder soundtrack
  templates/
    SPEC.md                the spec the agent fills in
    threejs/index.html     a Three.js scene that renders frame by frame
    blender/scene.py       a scripted Blender turntable
examples/                  three briefs
install.sh                 install, update or remove
```

The scripts also work on their own, for any video:

```bash
bash ~/.claude/skills/brief2mp4/scripts/check_delivery.sh my-video.mp4 --seconds 30
```

## Update or remove

```bash
cd brief2mp4 && git pull && bash install.sh     # update
bash brief2mp4/install.sh --uninstall           # remove from both apps
bash brief2mp4/install.sh --claude              # only Claude Code (or --codex)
```

The installer only replaces or removes a folder it created itself. If you already had a folder called `brief2mp4` in your skills, it is moved aside with a timestamp, never deleted.

## Licence

MIT. Use it, change it, ship videos with it. HyperFrames (Apache-2.0), Three.js (MIT), GSAP, Blender (GPL) and ffmpeg (LGPL/GPL) keep their own licences; this repo does not bundle them.
