"""Recipe: rigid bodies with constraints. A hinged chain swings; every joint must stay closed while it moves."""
from __future__ import annotations

import pytest

from blender_common import run_recipe
from conftest import needs_blender

pytestmark = needs_blender


@pytest.fixture(scope="module")
def chain():
    return run_recipe("rigid", "--links", "4", "--link-length", "0.5", "--frames", "80", "--release-angle", "75")


def test_every_joint_stays_closed_for_the_whole_swing(chain):
    assert chain["constraints"] == 4
    assert chain["max_joint_gap"] < 0.05 * 0.5          # no joint opens by more than 5% of a link


def test_the_chain_really_swings_and_a_hinge_keeps_it_in_one_plane(chain):
    assert chain["tip_travel_x"] > 0.8                  # the free end swings across, so the gap test is not vacuous
    assert chain["max_out_of_plane"] < 0.03             # hinge axis is Y: nothing drifts sideways


def test_a_single_link_is_a_pendulum_with_the_right_period():
    one = run_recipe("rigid", "--links", "1", "--link-length", "1.0", "--frames", "120", "--release-angle", "20",
                     "--link-width", "0.04")
    # a thin rod hinged at one end: T = 2*pi*sqrt(2L / 3g), about 1.64 s for L = 1 m
    assert one["period_s"] == pytest.approx(1.64, rel=0.05)


def test_a_ball_joint_chain_also_holds_together():
    ball = run_recipe("rigid", "--links", "3", "--joint", "point", "--frames", "60", "--release-angle", "60")
    assert ball["max_joint_gap"] < 0.05 * 0.5


def test_the_camera_keeps_the_whole_swing_in_frame(chain):
    assert chain["frame_margin"] > 0.02                 # every joint and the tip stay inside the picture, with a margin


def test_a_long_chain_released_near_level_also_stays_in_frame():
    long = run_recipe("rigid", "--links", "7", "--link-length", "0.45", "--release-angle", "85", "--anchor-height", "3.5",
                      "--damping", "0.01", "--frames", "120")
    assert long["tip_travel_x"] > 3.0                   # it really swings wide, so the margin is tested at the extremes
    assert long["frame_margin"] > 0.02
