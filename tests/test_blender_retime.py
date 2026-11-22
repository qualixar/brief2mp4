"""Recipe: retime between timeline markers. The action keeps its shape; only the times of the beats move."""
from __future__ import annotations

import pytest

from blender_common import mean_abs_diff, run_recipe
from conftest import needs_blender

pytestmark = needs_blender
TINY = ["--width", "96", "--height", "54", "--samples", "1", "--fmt", "BMP"]


def test_poses_land_on_the_moved_markers_and_the_curve_shape_is_kept():
    res = run_recipe("retime", "--marks", "start=1,hit=25,end=49", "--targets", "start=1,hit=40,end=60")
    assert res["markers_after"] == {"start": 1, "hit": 40, "end": 60}
    assert res["frame_end"] == 60
    assert res["shape_error"] < 1e-4                   # the value at every probe time equals the old value at the mapped time
    assert res["probes"] >= 6
    assert res["moved_keys"] >= 9


def test_a_slower_hit_is_the_same_picture_later(tmp_path):
    before, after = tmp_path / "before", tmp_path / "after"
    run_recipe("retime", "--marks", "start=1,hit=25,end=49", "--targets", "", "--out", str(before), "--render-frames", "25,49", *TINY)
    run_recipe("retime", "--marks", "start=1,hit=25,end=49", "--targets", "start=1,hit=40,end=60", "--out", str(after),
               "--render-frames", "25,40,60", *TINY)
    assert mean_abs_diff(before / "0025.bmp", after / "0040.bmp") < 0.3       # the hit, at its new time
    assert mean_abs_diff(before / "0049.bmp", after / "0060.bmp") < 0.3       # the end, at its new time
    assert mean_abs_diff(before / "0025.bmp", after / "0025.bmp") > 1.0       # and the old time now shows something else


def test_markers_that_would_cross_are_refused():
    exe_fail = None
    try:
        run_recipe("retime", "--marks", "start=1,hit=25,end=49", "--targets", "start=1,hit=70,end=60")
    except AssertionError as exc:
        exe_fail = str(exc)
    assert exe_fail and "increase" in exe_fail


def test_a_partial_retime_moves_only_the_named_marker_and_keeps_the_others_in_sync():
    res = run_recipe("retime", "--marks", "start=1,hit=25,end=49", "--targets", "hit=40")
    assert res["markers_after"] == {"start": 1, "hit": 40, "end": 49}     # the unnamed markers stay where they are
    assert res["frame_end"] == 49                                          # nothing is cut off the end
    assert res["marker_pose_error"] < 1e-4                                 # each marker still shows its authored pose
    assert res["shape_error"] < 1e-4


def test_fractional_targets_are_refused_because_markers_sit_on_whole_frames():
    with pytest.raises(AssertionError, match="whole frames"):
        run_recipe("retime", "--targets", "start=1,hit=40.5,end=60")
