# brief2mp4 docs

Guides for people. The agent reads the skill's own files (`plugin/skills/brief2mp4/SKILL.md` and its `references/`); these pages are for you, to understand what it does and to get more out of it.

| Guide | Read it when |
|---|---|
| [Getting started](getting-started.md) | You are installing brief2mp4 on macOS, Windows or Linux and want your first video |
| [Architecture](architecture.md) | You want to know how the loop, the routing and the checks work, what is in the repository, or how to extend it |
| [Film mode](film-mode.md) | Your brief is a narrated explainer or documentary of one to ten minutes, with sourced lines, licensed pictures, maps and your own voice |
| [3D walkthrough](3d-walkthrough.md) | Your brief has a 3D product, physics, an exploded view or a turntable; or you want the Blender motion recipes, a live Blender, or an image-to-3D generator and its licence |
| [Edit pack](edit-pack.md) | Your video is cut from footage or needs a voice-over mix, a composited title, a thumbnail or a graded still |
| [Art forms guide](art-forms-guide/brief2mp4-art-forms.pdf) (PDF, 87 pages) | You want a look by name, from claymation and Madhubani to synthwave and silent film; its sources are in [art-forms-guide/](art-forms-guide/README.md) |

## Reference pages in the skill

These are written for the agent, and they are the most detailed source for each topic.

| Topic | Page |
|---|---|
| Every video format: beat sheets, routes and checks | [references/formats.md](../plugin/skills/brief2mp4/references/formats.md) |
| The 82 art forms, one page each | [references/art-forms.md](../plugin/skills/brief2mp4/references/art-forms.md) |
| Characters that walk and talk | [characters/README-CHARACTERS.md](../plugin/skills/brief2mp4/characters/README-CHARACTERS.md) |
| The 3D pack's commands and shot JSON | [3d/README-3D.md](../plugin/skills/brief2mp4/3d/README-3D.md) |
| The edit pack's apps, recipes and MCP servers | [edit/README-EDIT.md](../plugin/skills/brief2mp4/edit/README-EDIT.md) |
| Motion that looks finished, and timelines that render wrong | [references/motion-doctrine.md](../plugin/skills/brief2mp4/references/motion-doctrine.md), [references/render-traps.md](../plugin/skills/brief2mp4/references/render-traps.md) |
| Sound, music and loudness | [references/sound.md](../plugin/skills/brief2mp4/references/sound.md) |
| Other open-source motion and 3D projects, with licences | [references/ecosystem.md](../plugin/skills/brief2mp4/references/ecosystem.md) |

## Beyond this repo

- [Free 104-page field guide](https://qualixar.com/learn/guides/brief2mp4-guide): writing briefs, every format, the optional packs, the checks, and every brief and setting from the contest in the video, as a PDF.
- [Technical deep dive](https://qualixar.com/research/blog/brief2mp4-deep-dive): how the spec, routing, baked physics, loudness correction and self-check work, with diagrams.
- [The video](https://youtu.be/l9mEZQon6JM): Fable 5.2 vs Opus 5.5 vs GPT-6.1 on the same motion-graphics briefs, and the skill at the end.
