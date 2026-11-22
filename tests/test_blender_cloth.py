"""Recipe: cloth drop. A sheet falls onto an object and the floor; check where it ends up, not that a modifier exists."""
from __future__ import annotations

import pytest

from blender_common import run_recipe
from conftest import needs_blender

pytestmark = needs_blender


@pytest.fixture(scope="module")
def drop():
    return run_recipe("cloth", "--frames", "60", "--cloth-res", "20", "--drop-height", "1.6")


def test_the_cloth_fell_and_stays_above_the_floor(drop):
    assert drop["start_mean_z"] == pytest.approx(1.6, abs=1e-3)
    assert drop["final_max_z"] < drop["start_mean_z"] - 0.3          # it came down
    assert drop["final_min_z"] > drop["floor_z"] - 0.02               # and never went through the floor
    assert drop["nan_vertices"] == 0


def test_the_cloth_rests_on_the_object_and_drapes_over_the_sides(drop):
    assert abs(drop["centre_z"] - drop["object_top_z"]) < 0.08       # the middle sits on top of the object
    assert drop["edge_mean_z"] < drop["centre_z"] - 0.2              # the edges hang lower: it draped, not slid off
    assert drop["motion_last_10_frames"] < 0.05                      # nearly at rest at the end


def test_a_cloth_without_the_collision_object_falls_to_the_floor():
    free = run_recipe("cloth", "--frames", "60", "--cloth-res", "20", "--object", "none")
    assert free["final_max_z"] < 0.15                                 # no object: it lies on the floor


def test_a_delayed_sheet_hangs_still_until_released_and_still_lands():
    late = run_recipe("cloth", "--frames", "70", "--cloth-res", "20", "--delay", "20")
    assert late["moved_before_release"] < 1e-6
    assert late["final_max_z"] < late["start_mean_z"] - 0.3


def test_the_render_only_smoothing_does_not_change_the_simulation():
    plain = run_recipe("cloth", "--frames", "40", "--cloth-res", "20")
    smooth = run_recipe("cloth", "--frames", "40", "--cloth-res", "20", "--smooth-levels", "1")
    # Blender's threaded cloth solver differs between runs by about 3e-5 m on this grid (seen with the same options
    # twice), so the tolerance sits above that noise and far below what a simulated subdivision would move.
    assert smooth["centre_z"] == pytest.approx(plain["centre_z"], abs=2e-4)
    assert smooth["vertices"] == plain["vertices"] == 441
