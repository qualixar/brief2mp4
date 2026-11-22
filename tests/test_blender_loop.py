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
