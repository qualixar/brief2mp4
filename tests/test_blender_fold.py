"""Recipe: folding with shape keys. A sheet folds in half, again, and ends at the size the arithmetic says."""
from __future__ import annotations

import pytest

from blender_common import run_recipe
from conftest import needs_blender

pytestmark = needs_blender


@pytest.fixture(scope="module")
def fold():
    return run_recipe("fold", "--folds", "2", "--sheet-width", "2.0", "--sheet-height", "1.2", "--fold-frames", "24")


def test_two_folds_quarter_the_width_and_keep_the_height(fold):
    assert fold["flat_width"] == pytest.approx(2.0, abs=1e-4)
    assert fold["final_width"] == pytest.approx(2.0 / 4, rel=0.08)
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
    assert fold["area_ratio"] == pytest.approx(1.0, rel=0.15)   # the rounded creases stretch the sheet a little, nothing more
    assert fold["shape_keys"] == 1 + 2 * 6                                      # the basis and six slices per fold
