"""Recipe: seamless loop. Frame 1 and the last frame must be the same picture, and the curves must be cyclic."""
from __future__ import annotations

import pytest

from blender_common import mean_abs_diff, run_recipe
from conftest import needs_blender

pytestmark = needs_blender
TINY = ["--width", "96", "--height", "54", "--samples", "1", "--fmt", "BMP"]


@pytest.fixture(scope="module")
def loop(tmp_path_factory):
    out = tmp_path_factory.mktemp("loop")
    res = run_recipe("loop", "--loop-frames", "25", "--turns", "1", "--out", str(out), "--render-frames", "1,13,25", *TINY)
    return res, out


def test_every_curve_is_cyclic_and_the_seam_has_no_kink(loop):
    res, _ = loop
    assert res["curves"] == 3 and res["cyclic_curves"] == res["curves"]
    assert res["pose_gap"] < 1e-4                       # object transforms at frame 1 and at the last frame
    assert res["seam_slope_gap"] < 0.02                 # slope just before the seam vs just after, as a fraction of the amplitude


def test_first_and_last_frame_match_and_the_middle_does_not(loop):
    _, out = loop
    seam = mean_abs_diff(out / "0001.bmp", out / "0025.bmp")
    middle = mean_abs_diff(out / "0001.bmp", out / "0013.bmp")
    assert seam < 0.3, f"frame 1 and frame 25 differ by {seam}"
    assert middle > 5 * max(seam, 0.05), f"the animation barely moves: middle diff {middle}"


def test_a_caption_is_drawn_in_the_frame(tmp_path):
    big = ["--width", "320", "--height", "180", "--samples", "1", "--fmt", "BMP", "--render-frames", "1"]
    run_recipe("loop", "--out", str(tmp_path / "plain"), *big)
    run_recipe("loop", "--out", str(tmp_path / "titled"), "--caption", "seamless loop", *big)
    assert mean_abs_diff(tmp_path / "plain" / "0001.bmp", tmp_path / "titled" / "0001.bmp") > 0.3


def test_orbit_moves_the_camera_and_a_whole_turn_per_loop_keeps_the_seam(tmp_path):
    still, moving = tmp_path / "still", tmp_path / "moving"
    run_recipe("loop", "--loop-frames", "25", "--out", str(still), "--render-frames", "7", *TINY)
    run_recipe("loop", "--loop-frames", "25", "--orbit", "450", "--out", str(moving), "--render-frames", "1,7,25", *TINY)
    assert mean_abs_diff(still / "0007.bmp", moving / "0007.bmp") > 1.0       # a quarter turn of the camera by frame 7
    assert mean_abs_diff(moving / "0001.bmp", moving / "0025.bmp") < 0.3      # and back where it started at the seam


def test_a_fading_caption_is_absent_before_its_window_and_present_inside_it(tmp_path):
    big = ["--loop-frames", "25", "--width", "320", "--height", "180", "--samples", "1", "--fmt", "BMP", "--render-frames", "1,20"]
    run_recipe("loop", "--out", str(tmp_path / "plain"), *big)
    run_recipe("loop", "--out", str(tmp_path / "faded"), "--caption", "seamless loop", "--caption-frames", "10-25",
               "--caption-fade", "4", *big)
    assert mean_abs_diff(tmp_path / "plain" / "0001.bmp", tmp_path / "faded" / "0001.bmp") < 0.3
    assert mean_abs_diff(tmp_path / "plain" / "0020.bmp", tmp_path / "faded" / "0020.bmp") > 0.3


def test_the_studio_look_renders_a_different_set(tmp_path):
    run_recipe("loop", "--out", str(tmp_path / "plain"), "--render-frames", "1", *TINY)
    run_recipe("loop", "--out", str(tmp_path / "studio"), "--look", "studio", "--render-frames", "1", *TINY)
    assert mean_abs_diff(tmp_path / "plain" / "0001.bmp", tmp_path / "studio" / "0001.bmp") > 5.0


def test_an_orbit_that_does_not_turn_whole_turns_per_loop_is_refused():
    with pytest.raises(AssertionError, match="seam jumps"):
        run_recipe("loop", "--loop-frames", "25", "--orbit", "20")


def test_a_whole_turn_orbit_loops_and_too_few_frames_are_refused():
    assert run_recipe("loop", "--loop-frames", "25", "--orbit", "450")["pose_gap"] < 1e-4    # 450 deg/s x 0.8 s = one turn
    with pytest.raises(AssertionError, match="at least 4"):
        run_recipe("loop", "--loop-frames", "2")


CAMERA_MOVES = '''
import sys, json, math
sys.path.insert(0, sys.argv[sys.argv.index("--") + 1])
import bpy, b2m_loop as r
state = r.build({"loop_frames": 13}, clear=True)
pivot = bpy.data.objects["b2m_orbit"]
for f, z in ((1, 0.0), (13, 0.5)):                   # a camera move the curves of the gem and ring know nothing about
    pivot.rotation_euler[2] = z
    pivot.keyframe_insert("rotation_euler", index=2, frame=f)
print("B2M3D_RECIPE", json.dumps(r.measure(state)))
'''


def test_the_seam_measurement_includes_the_camera():
    import json
    import subprocess

    from b2m3d import paths
    from blender_common import RECIPES
    proc = subprocess.run([paths.blender(), "-b", "--factory-startup", "--python-expr", CAMERA_MOVES, "--", str(RECIPES)],
                          capture_output=True, text=True, timeout=300)
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("B2M3D_RECIPE"))
    assert json.loads(line.split(" ", 1)[1])["pose_gap"] > 0.1
