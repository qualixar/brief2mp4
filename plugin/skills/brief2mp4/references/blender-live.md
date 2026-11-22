# Blender, live: working in a running Blender through blender-mcp

The default Blender route in brief2mp4 is headless: a script builds the scene, renders PNG frames and exits (`references/blender.md`). That stays the route for every render that ships. This page covers the second route, a Blender window that is already open, which the agent drives through [blender-mcp](https://github.com/ahujasid/mcp-for-blender) (author Siddharth Ahuja, MIT). It is optional and you install it yourself. brief2mp4 does not bundle it.

## Live or headless?

| You need | Use | Why |
|---|---|---|
| The final frames of a film | Headless | Same result on every machine and in CI; no window, no stray user setting (`--factory-startup`), nothing to click |
| A render you may repeat tomorrow, or on another machine | Headless | A script plus its parameters is the whole record |
| A first look at a set: where things stand, what the camera sees, whether the light works | Live | Seconds per try, and the person can watch and say "left a bit" |
| Placing or posing something by eye, then keeping the numbers | Live, then copy the numbers into the script | The window is for deciding, the script is for rendering |
| Importing an asset or a generated mesh and checking its scale and floor contact | Live | You see the problem at once |
| Debugging a recipe that does something odd | Live | Step it, look at it, query the objects |

The rule is one line: decide live, render headless. A live session carries whatever the person changed by hand, so its output is not repeatable. When a live session settles on a look, write the parameters down and run the same recipe headless with `b2m3d recipe run` (see below).

## Install and connect

Read the project's own README first; the steps below were read from it on 22 Nov 2026 and the project moves quickly. It was renamed: the repository is `ahujasid/mcp-for-blender` (the old `blender-mcp` address redirects), the PyPI package is `mcp-for-blender`, and `uvx blender-mcp` still runs the server.

It has two parts. A Blender add-on (`addon.py`) opens a socket server inside Blender (default port 9876). An MCP server, started by your agent through `uvx`, talks to that socket. Both are needed.

```bash
# 1. uv provides uvx. Use uv's own installer from https://docs.astral.sh/uv/ (not pip install uv).
# 2. Register the server with your agent. Claude Code:
claude mcp add blender uvx mcp-for-blender
#    Codex:
codex mcp add blender -- uvx mcp-for-blender
# 3. Install the add-on into Blender and enable it:
uvx mcp-for-blender install-addon
# 4. In Blender: press N in the 3D viewport, open the "MCP for Blender" tab, click "Start MCP Server".
```

The project also offers `uvx mcp-for-blender setup`, which does the client and add-on steps together and keeps a `.bak` of each file it changes. Its README also shows a `curl ... | sh` one-liner; the commands above avoid piping a download into a shell. Client apps started from the Dock or Start menu may not find `uvx` on their PATH: use its full path from `which uvx`.

Check the connection by asking the agent for the add-on status and the scene summary before anything else. The tool list in your client is the truth for the version you installed. The README lists nine tools: `execute_blender_code` (run Python in the live Blender), `look` (see the viewport, camera or an angles sheet), `get_scene_info`, `get_addon_status`, `search_assets` and `import_asset` (Poly Haven, Sketchfab, Poly Pizza), `generate_3d` and `generate_gaussian_world` (hosted generators, some paid), and two telemetry controls. Older releases named some tools differently (`get_object_info`, `get_viewport_screenshot`), so read the list rather than assuming.

## Safety, in four lines

- `execute_blender_code` runs any Python the agent sends. Save the `.blend` first, every time.
- The add-on's socket has no password or encryption: keep it on `localhost`. Do not point `BLENDER_HOST` at another machine without an SSH tunnel.
- `BLENDER_MCP_SAFE_MODE=1` makes the server screen each script and refuse file, network and process access. The recipes here need none of those, so safe mode is a good default.
- Telemetry is opt-in and off by default (Preferences, Add-ons, MCP for Blender). Leave it off for client work.

## Sending a recipe to the live Blender

The motion recipes (`templates/recipes/b2m_*.py`, next to `b2m3d`) work in both places. Headless they are scripts. Live they are modules: import one and call `build`. The agent sends this through `execute_blender_code`, with the folder of the installed skill filled in:

```python
import sys
sys.path.insert(0, "<skill folder>/3d/templates/recipes")   # the folder holding b2m_common.py
import importlib, b2m_cloth
importlib.reload(b2m_cloth)                                   # picks up edits to the recipe file
state = b2m_cloth.build({"object": "sphere", "cloth_res": 24, "stage": False}, clear=False)
print(b2m_cloth.measure(state))                               # the numbers that say whether it worked
```

Three settings make a recipe polite in someone else's scene:

- `clear=False` keeps the open file. The recipe only replaces its own collection (`b2m_cloth`), so running it twice does not pile up objects.
- `"stage": False` skips the floor, lights, camera and world, so the scene's own are used. Without it the recipe sets up a studio and takes over the active camera. A cloth recipe with `stage: False` expects a floor object of your own to land on; give it a Collision modifier.
- Every key in a recipe's `DEFAULTS` can be overridden; an unknown key raises a `KeyError`, so a typo does not silently do nothing.

What a recipe still changes in a live file: the scene's frame range, the timeline markers (`retime`), and the keyframes of the objects it made. `retime_between_markers(scene, {...})` remaps every animated object in the scene unless you pass `objs=[...]`; pass the list when the file holds other animation.

A live window shows each frame the simulation has reached, so for cloth and rigid bodies step through the timeline once, in order, before judging the result. Looking is what `look` is for: `look` with the camera view, or an animation strip of frames.

## Hand-off to the headless route

When the look is right, the record of it is the recipe name and its parameters:

```bash
b2m3d recipe run cloth -- --object sphere --cloth-res 32 --frames 90 --width 1920 --height 1080 --out frames
```

Frames, finishing and checks then go the usual way (`scripts/finish.sh`, `scripts/check_delivery.sh`). If the person moved things by hand in the live scene and wants those positions kept, read them back (`get_scene_info`) and put the numbers into a recipe parameter or a small script of your own.

## What was tested

The recipes were tested by importing them in a headless Blender with no command-line arguments, which is what `execute_blender_code` does inside a live one: the user's own objects stay, a second run replaces the first, `stage: False` adds no camera or lights, and a mistyped key is refused. A real blender-mcp connection was not part of the automated tests, because CI has no Blender and the add-on needs a window.

## Credit and licence

blender-mcp / MCP for Blender: Siddharth Ahuja, MIT licence (the LICENSE file reads "MIT License, Copyright (c) 2025 Siddharth Ahuja"). Its README says it is "a third-party integration and not made by Blender". It also offers paid hosted features (generators, a "Premium" service); none of them is needed here.
