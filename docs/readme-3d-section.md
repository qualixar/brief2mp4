<!-- Draft for the README "3D" section (release 0.8.0). Text only: paste it in, adjust the links, then delete this file. -->

## 3D

There are three routes, lightest first. Three.js inside HyperFrames covers stylised scenes, particles and flying cameras. The optional 3D pack adds parametric models (code or CAD), material presets, a baked rigid-body drop, exploded views, and a short JSON shot that becomes a HyperFrames project. Blender, run headless, is for shots that should look physically real: glass, metal, soft shadows.

New in 0.8.0: six Blender motion recipes, for motion that is slow to get right by hand. A seamless loop (the first frame equals the last), retiming between timeline markers, a cloth drop, a hinged or ball-jointed chain, folding with shape keys, and a walk forward with the feet planted. Each is a script you can change, each prints numbers that show it worked (how far a planted foot moved, whether a joint opened, whether the swing stayed in frame), and each has a test that checks them with a real Blender. They share one look: `--look studio` puts any recipe in a seamless studio with soft light and no horizon, `--orbit` moves the camera, and captions fade in as small lower thirds. [Example 10](examples/10-3d-motion/) is a 24-second film made with five of them, in one studio, cut to music: every frame of it comes from the recipes.

```bash
b2m3d recipe list
b2m3d recipe run cloth -- --object sphere --frames 90 --out frames
```

A running Blender can be driven live through [blender-mcp](https://github.com/ahujasid/mcp-for-blender) (MIT). Use it to decide a look by eye. Renders stay headless, so they repeat on any machine.

Three optional tools are called, never bundled, and each has its own terms. [Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) (Tencent) turns an image into a mesh; its licence does not apply in the EU, UK or South Korea. [TRELLIS](https://github.com/microsoft/TRELLIS) (Microsoft, MIT) turns an image or text into a mesh. The [FLIP Fluids](https://github.com/rlguy/Blender-FLIP-Fluids) add-on (GPL, paid; a free demo adds a watermark) bakes liquids. You install them; `scripts/gen3d.py` and a Blender recipe call them.

Read next: [3d/README-3D.md](plugin/skills/brief2mp4/3d/README-3D.md), [Blender recipes](plugin/skills/brief2mp4/references/blender-recipes.md), [live Blender](plugin/skills/brief2mp4/references/blender-live.md), [generators and licences](plugin/skills/brief2mp4/references/generators-3d.md).
