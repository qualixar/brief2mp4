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
    assert names == {"loop", "retime", "cloth", "rigid", "fold", "walk"}
    assert all(r["summary"] for r in out["recipes"])


@needs_blender
def test_recipe_run_passes_arguments_through_and_returns_the_result_line(tmp_path):
    out = cli_json("recipe", "run", "fold", "--", "--folds", "1", "--fold-frames", "12")
    assert out["recipe"] == "fold" and out["final_width"] == pytest.approx(1.0, rel=0.08)


def test_recipe_run_with_an_unknown_name_says_which_exist():
    proc = cli("recipe", "run", "juggle")
    assert proc.returncode == 1 and "loop" in proc.stderr and "juggle" in proc.stderr
