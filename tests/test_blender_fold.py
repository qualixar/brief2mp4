"""Recipe: folding with shape keys. A sheet folds in half, again, and ends at the size the arithmetic says."""
from __future__ import annotations

import pytest

from blender_common import mean_abs_diff, run_recipe
from conftest import needs_blender

pytestmark = needs_blender


@pytest.fixture(scope="module")
def fold():
    return run_recipe("fold", "--folds", "2", "--sheet-width", "2.0", "--sheet-height", "1.2", "--fold-frames", "24")


def test_two_folds_quarter_the_width_and_keep_the_height(fold):
    assert fold["flat_width"] == pytest.approx(2.0, abs=1e-4)
    assert fold["final_width"] == pytest.approx(2.0 / 4, rel=0.08)
    assert fold["final_width"] == pytest.approx(fold["expected_width"], rel=0.08) and fold["ok"] is True
    assert fold["final_height"] == pytest.approx(1.2, abs=1e-4)


def test_the_layers_stack_without_interpenetrating(fold):
    assert fold["flat_thickness"] == pytest.approx(0.0, abs=1e-6)
    assert fold["layers"] == 4                                                        # two folds make four layers
    assert fold["final_thickness"] == pytest.approx(3 * fold["layer_gap"], rel=0.05)  # three gaps between four layers
    assert fold["min_layer_separation"] == pytest.approx(fold["layer_gap"], rel=0.05)


def test_the_fold_is_an_arc_not_a_squash(fold):
    # half way through the first fold the free edge has swung up to about the height of a quarter turn
    assert fold["half_fold_edge_z"] == pytest.approx(fold["half_fold_expected_z"], rel=0.03)


def test_the_sheet_keeps_its_area_and_its_shape_keys(fold):
    assert fold["area_ratio"] == pytest.approx(1.0, abs=0.06)   # the rounded creases stretch the sheet a little, nothing more
    assert fold["shape_keys"] == 1 + 2 * 6                                      # the basis and six slices per fold


def test_no_crease_dips_under_the_bottom_layer_or_the_floor_at_any_frame(fold):
    assert fold["min_local_z"] >= -1e-6 and fold["min_z"] >= 0.0


def test_three_folds_keep_their_width_layers_and_area():
    three = run_recipe("fold", "--folds", "3", "--fold-frames", "12", "--pause", "2")
    assert three["layers"] == 8 and three["ok"] is True, three["warnings"]
    assert three["final_width"] == pytest.approx(three["expected_width"], rel=0.08)   # 0.25 m plus half the stack's thickness
    assert three["expected_width"] == pytest.approx(0.25 + 7 * 0.01 / 2)
    assert three["area_ratio"] < 1.15 and three["min_local_z"] >= -1e-6


@pytest.mark.parametrize("args, message", [(("--fold-steps", "3"), "at least 6"), (("--layer-gap", "0"), "above 0"),
                                           (("--folds", "4"), "thicker than half")])
def test_settings_that_cannot_fold_cleanly_are_refused(args, message):
    with pytest.raises(AssertionError, match=message):
        run_recipe("fold", "--fold-frames", "6", *args)


def test_the_underside_colour_shows_without_thickness(tmp_path):
    tiny = ["--folds", "1", "--fold-frames", "12", "--pause", "0", "--render-frames", "13", "--width", "96", "--height", "54",
            "--samples", "1", "--fmt", "BMP", "--follow", "0"]
    run_recipe("fold", *tiny, "--out", str(tmp_path / "plain"))
    run_recipe("fold", *tiny, "--out", str(tmp_path / "back"), "--back", "#2040ff")
    assert mean_abs_diff(tmp_path / "plain" / "0013.bmp", tmp_path / "back" / "0013.bmp") > 1.0   # the turned flap shows blue
