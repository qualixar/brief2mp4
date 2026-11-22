"""b2m_flip_bake: bake a FLIP Fluids liquid from the command line, then render frames. Optional add-on, you install it.

FLIP Fluids (a Blender add-on, GPL, sold on Superhive; a watermarked demo is free) simulates liquids. brief2mp4
does not include it. You build the liquid in Blender with the add-on (a Domain, a Fluid, Obstacles) and save the
.blend. This script opens that file, runs the add-on's own command-line bake operator, and renders PNG frames.
It does not set the liquid up for you: the add-on's scene setup is a UI workflow, and a bad guess here would
only look like a working simulation.

  blender -b scene.blend -P b2m_flip_bake.py -- --out frames --render-frames 1-90
  blender -b -P b2m_flip_bake.py -- --blend scene.blend --bake 0 --out frames     (render an existing cache)

Run it WITHOUT --factory-startup, so the add-on you enabled in Preferences is loaded. Without the add-on the script
prints a SKIP result and exits normally.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import b2m_common as c  # noqa: E402

FACTORY_STARTUP = False     # read by `b2m3d recipe run`: this recipe needs the user's enabled add-ons

DEFAULTS = {"blend": "", "bake": True, "width": 0, "height": 0}      # width and height 0: keep the file's own


def addon_ready() -> bool:
    try:
        bpy.ops.flip_fluid_operators.bake_fluid_simulation_cmd.get_rna_type()
        return True
    except (AttributeError, KeyError):
        return False


def main():
    p = c.parse_args(DEFAULTS, __doc__.split("\n")[0])
    if p["blend"]:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(p["blend"]))
    if not addon_ready():
        return c.emit({"recipe": "flip_bake", "skipped": True, "reason": "the FLIP Fluids add-on is not enabled in this Blender: "
                       "install it from https://github.com/rlguy/Blender-FLIP-Fluids (demo) or Superhive (full), enable it in "
                       "Preferences, and run this without --factory-startup"}, p["json"])
    scene = bpy.context.scene
    if p["bake"]:
        bpy.ops.flip_fluid_operators.bake_fluid_simulation_cmd()          # the add-on's documented command-line bake
    if p["width"] and p["height"]:
        scene.render.resolution_x, scene.render.resolution_y = int(p["width"]), int(p["height"])
    c.set_engine(scene, p["engine"], int(p["samples"]))
    result = {"recipe": "flip_bake", "skipped": False, "baked": bool(p["bake"]), "frame_start": scene.frame_start, "frame_end": scene.frame_end}
    if p["out"]:
        result["rendered"] = c.render_frames(scene, p["out"], c.frame_list(p["render_frames"], scene.frame_start, scene.frame_end), p["fmt"])
    return c.emit(result, p["json"])


if __name__ == "__main__":
    main()
