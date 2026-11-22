"""The live route: the same recipes imported inside a running Blender (what blender-mcp's execute_blender_code does)
and the `b2m3d recipe` command. Tested with a headless Blender standing in for the live one."""
from __future__ import annotations

import json
import subprocess

import pytest

from b2m3d import paths
from blender_common import RECIPES, MARKER
from conftest import cli, cli_json, needs_blender

SNIPPET = f'''
import sys, json
sys.path.insert(0, {str(RECIPES)!r})
import bpy
bpy.ops.mesh.primitive_cube_add(location=(9, 9, 9))          # the user's own object
bpy.context.object.name = "users_cube"
import b2m_loop
first = b2m_loop.build({{"loop_frames": 13, "stage": False}}, clear=False)
count_one = len([o for o in bpy.data.objects if o.name.startswith("b2m_")])
second = b2m_loop.build({{"loop_frames": 13, "stage": False}}, clear=False)       # run it twice, as an agent would
count_two = len([o for o in bpy.data.objects if o.name.startswith("b2m_")])
try:
    b2m_loop.build({{"loop_framez": 13}}, clear=False)
    typo = "accepted"
except KeyError as exc:
    typo = str(exc)
print({MARKER!r}, json.dumps({{"user_cube_kept": "users_cube" in bpy.data.objects, "objects_after_one": count_one,
      "objects_after_two": count_two, "camera_added": any(o.name.startswith("b2m_cam") or o.name.startswith("b2m_key") for o in bpy.data.objects), "typo": typo,
      "measure": b2m_loop.measure(second)}}))
'''


@needs_blender
def test_a_recipe_runs_inside_an_existing_scene_without_taking_it_over():
    proc = subprocess.run([paths.blender(), "-b", "--factory-startup", "--python-expr", SNIPPET], capture_output=True, text=True, timeout=300)
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith(MARKER)), None)
    assert line, proc.stdout[-1500:] + proc.stderr[-800:]
    res = json.loads(line[len(MARKER) + 1:])
    assert res["user_cube_kept"] is True
    assert res["camera_added"] is False                      # stage=False leaves the camera, lights and floor to the user
    assert res["objects_after_two"] == res["objects_after_one"]   # the second run replaced the first
    assert "loop_framez" in res["typo"]
    assert res["measure"]["cyclic_curves"] == res["measure"]["curves"] == 3


def test_recipe_list_names_every_recipe_without_needing_blender():
    out = cli_json("recipe", "list")
    names = {r["name"] for r in out["recipes"]}
    assert names == {"loop", "retime", "cloth", "rigid", "fold", "walk", "flip_bake"}
    assert all(r["summary"] for r in out["recipes"])


@needs_blender
def test_recipe_run_passes_arguments_through_and_returns_the_result_line(tmp_path):
    out = cli_json("recipe", "run", "fold", "--", "--folds", "1", "--fold-frames", "12")
    assert out["recipe"] == "fold" and out["final_width"] == pytest.approx(1.0, rel=0.08)


def test_recipe_run_with_an_unknown_name_says_which_exist():
    proc = cli("recipe", "run", "juggle")
    assert proc.returncode == 1 and "loop" in proc.stderr and "juggle" in proc.stderr


def test_only_the_flip_recipe_asks_for_the_users_own_add_ons():
    from b2m3d import recipes
    flags = {r["name"]: r["factory_startup"] for r in recipes.available()}
    assert flags.pop("flip_bake") is False and all(flags.values())


@needs_blender
def test_flip_bake_skips_cleanly_when_the_add_on_is_absent(tmp_path):
    # --factory-startup guarantees no add-on is enabled, whatever this machine has installed
    proc = subprocess.run([paths.blender(), "-b", "--factory-startup", "-P", str(RECIPES / "b2m_flip_bake.py"), "--", "--out", str(tmp_path / "f")],
                          capture_output=True, text=True, timeout=300)
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith(MARKER))
    res = json.loads(line[len(MARKER) + 1:])
    assert res["skipped"] is True and "FLIP Fluids" in res["reason"] and not (tmp_path / "f").exists()


MAKE_BLEND = '''
import sys, bpy
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples, scene.cycles.use_denoising = 128, False
scene.view_settings.view_transform = "AgX"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 32, 18, 100
scene.frame_start, scene.frame_end = 1, 2
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
'''

STUB_ADDON = '''
import bpy
class Bake(bpy.types.Operator):                      # stands in for the FLIP Fluids add-on's command-line bake
    bl_idname = "flip_fluid_operators.bake_fluid_simulation_cmd"
    bl_label = "stub bake"
    def execute(self, context):
        print("STUB_BAKE ran")
        return {"FINISHED"}
bpy.utils.register_class(Bake)
def seen(scene, *_):
    print("RENDER_SETTINGS", scene.render.engine, scene.cycles.samples, scene.view_settings.view_transform)
bpy.app.handlers.render_pre.append(seen)
'''


@needs_blender
def test_flip_bake_keeps_the_files_own_render_settings_and_renders_the_whole_range(tmp_path):
    blend, out = tmp_path / "liquid.blend", tmp_path / "frames"
    subprocess.run([paths.blender(), "-b", "--factory-startup", "--python-expr", MAKE_BLEND, "--", str(blend)],
                   capture_output=True, text=True, timeout=300, check=True)
    proc = subprocess.run([paths.blender(), "-b", "--factory-startup", str(blend), "--python-expr", STUB_ADDON,
                           "--python-exit-code", "1", "-P", str(RECIPES / "b2m_flip_bake.py"), "--", "--out", str(out)],
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout[-1500:] + proc.stderr[-800:]
    settings = {ln for ln in proc.stdout.splitlines() if ln.startswith("RENDER_SETTINGS")}
    assert settings == {"RENDER_SETTINGS CYCLES 128 AgX"}             # the person's engine, samples and view transform
    assert "STUB_BAKE ran" in proc.stdout
    assert sorted(p.name for p in out.iterdir()) == ["0001.png", "0002.png"]


RETIME_OTHER_KEYS = f'''
import sys, json
sys.path.insert(0, {str(RECIPES)!r})
import bpy
import b2m_retime as r
scene = bpy.context.scene
bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.object
mat = bpy.data.materials.new("users_mat")
mat.use_nodes = True
cube.data.materials.append(mat)
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
for f, v in ((1, 0.0), (25, 1.0)):
    bsdf.inputs["Alpha"].default_value = v
    bsdf.inputs["Alpha"].keyframe_insert("default_value", frame=f)
scene.world = scene.world or bpy.data.worlds.new("users_world")
scene.world.use_nodes = True
bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
for f, v in ((1, 0.2), (25, 1.0)):
    bg.inputs["Strength"].default_value = v
    bg.inputs["Strength"].keyframe_insert("default_value", frame=f)
scene.timeline_markers.new("start", frame=1)
scene.timeline_markers.new("hit", frame=25)
r.retime_between_markers(scene, {{"hit": 40}})
keys = lambda idb: sorted(kp.co.x for fc in r.c.fcurves(idb) for kp in fc.keyframe_points)
print({MARKER!r}, json.dumps({{"material_keys": keys(mat.node_tree), "world_keys": keys(scene.world.node_tree)}}))
'''


@needs_blender
def test_retime_also_moves_material_and_world_keys():
    proc = subprocess.run([paths.blender(), "-b", "--factory-startup", "--python-expr", RETIME_OTHER_KEYS],
                          capture_output=True, text=True, timeout=300)
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith(MARKER)), None)
    assert line, proc.stdout[-1500:] + proc.stderr[-800:]
    res = json.loads(line[len(MARKER) + 1:])
    assert res["material_keys"] == [1.0, 40.0] and res["world_keys"] == [1.0, 40.0]


POLITE_DEFAULTS = f'''
import sys, json
sys.path.insert(0, {str(RECIPES)!r})
import bpy
bpy.ops.mesh.primitive_cube_add(location=(9, 9, 9))
cube = bpy.context.object
cube.name = "users_cube"
import b2m_loop, b2m_rigid
b2m_loop.build({{"loop_frames": 13}})                       # no clear argument: the default must keep the open scene
data = lambda: sorted((k, len([d for d in getattr(bpy.data, k) if d.name.startswith("b2m_")])) for k in ("meshes", "materials", "actions"))
once = data()
b2m_loop.build({{"loop_frames": 13}})
twice = data()
cube.select_set(True)
bpy.context.view_layer.objects.active = cube
b2m_rigid.build({{"links": 2, "frames": 5}})
print({MARKER!r}, json.dumps({{"cube_kept": "users_cube" in bpy.data.objects, "once": once, "twice": twice,
      "active": bpy.context.view_layer.objects.active.name, "selected": sorted(o.name for o in bpy.context.selected_objects)}}))
'''


@needs_blender
def test_the_default_build_keeps_the_open_scene_leaves_no_orphans_and_gives_the_selection_back():
    proc = subprocess.run([paths.blender(), "-b", "--factory-startup", "--python-expr", POLITE_DEFAULTS],
                          capture_output=True, text=True, timeout=300)
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith(MARKER)), None)
    assert line, proc.stdout[-1500:] + proc.stderr[-800:]
    res = json.loads(line[len(MARKER) + 1:])
    assert res["cube_kept"] is True                         # build() without clear never empties the file
    assert res["twice"] == res["once"]                      # a second run leaves no orphan meshes, materials or actions
    assert res["active"] == "users_cube" and res["selected"] == ["users_cube"]


def test_the_recipe_command_line_follows_each_recipes_startup_flag_and_fails_loudly(monkeypatch):
    from b2m3d import recipes
    seen = []
    monkeypatch.setattr(recipes.paths, "blender", lambda: "/bin/blender")
    monkeypatch.setattr(recipes, "run", lambda cmd, timeout: seen.append(cmd) or 'B2M3D_RECIPE {"ok": true}')
    recipes.run_recipe("fold", ["--", "--caption", "a", "--", "b"])
    recipes.run_recipe("flip_bake", ["--out", "f"])
    fold, flip = seen
    assert "--factory-startup" in fold and "--factory-startup" not in flip       # flip needs the person's add-ons
    for cmd in seen:
        assert cmd[cmd.index("--python-exit-code") + 1] == "1"                  # a recipe that raises exits 1
    assert fold[fold.index("--") + 1:] == ["--caption", "a", "--", "b"]          # only the leading separator is dropped


@needs_blender
def test_a_recipe_error_reaches_the_caller_with_its_message():
    proc = cli("recipe", "run", "retime", "--", "--targets", "start=1,hit=70,end=60")
    assert proc.returncode == 1 and "increase" in proc.stderr
