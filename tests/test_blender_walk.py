"""Recipe: walk forward. A cycle plus root travel, with each planted foot staying put on the ground."""
from __future__ import annotations

import pytest

from blender_common import run_recipe
from conftest import needs_blender

pytestmark = needs_blender
ARGS = ["--frames", "96", "--speed", "1.2", "--cycle-frames", "32"]


@pytest.fixture(scope="module")
def walk():
    return run_recipe("walk", *ARGS)


def test_the_root_travels_the_distance_speed_times_time(walk):
    assert walk["root_distance"] == pytest.approx(1.2 * 95 / 30, rel=0.01)


def test_planted_feet_do_not_slide(walk):
    assert walk["contact_frames"] > 40                   # both feet were on the ground for a good share of the walk
    assert walk["max_slide_per_frame"] < 0.002           # a planted foot moves less than 2 mm a frame
    assert walk["min_foot_z"] > -0.005                   # and never goes through the floor
    assert walk["max_leg_stretch"] < 1e-4                # the leg never had to be longer than it is


def test_the_feet_actually_step(walk):
    assert walk["max_foot_lift"] > 0.08                  # the swing foot clears the ground
    assert walk["step_length"] == pytest.approx(1.2 * 32 / 30 / 2, rel=0.05)     # plants alternate feet: half a stride apart
    assert walk["max_ik_error"] < 1e-3                                         # the legs really reach the planted points


def test_a_walk_without_planting_does_slide_so_the_check_is_not_vacuous():
    naive = run_recipe("walk", *ARGS, "--naive")
    assert naive["max_slide_per_frame"] > 0.02           # the foot drags along the floor at the speed of the body


def test_the_walk_reports_ok_when_the_legs_reach(walk):
    assert walk["ok"] is True and walk["warnings"] == [] and walk["max_leg_stretch"] == 0


def test_a_stride_the_legs_cannot_reach_is_flagged_not_reported_as_slide_free():
    fast = run_recipe("walk", "--frames", "40", "--speed", "3.0")
    assert fast["ok"] is False and "cannot reach" in fast["warnings"][0]


def test_hips_too_high_for_the_legs_are_refused():
    with pytest.raises(AssertionError, match="never reach the ground"):
        run_recipe("walk", "--frames", "10", "--hip-height", "0.95")
