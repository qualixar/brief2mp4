"""The recipes' plain arithmetic (templates/recipes/b2m_math.py), tested without Blender, so it runs in CI on every OS."""
from __future__ import annotations

import importlib.util
import math

import pytest

from conftest import PACK

_spec = importlib.util.spec_from_file_location("b2m_math", PACK / "templates" / "recipes" / "b2m_math.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def test_b2m_math_never_imports_bpy():
    source = (PACK / "templates" / "recipes" / "b2m_math.py").read_text(encoding="utf-8")
    assert "import bpy" not in source and "mathutils" not in source


def test_frame_list_and_merged():
    assert m.frame_list("1,48,10-12", 1, 60) == [1, 10, 11, 12, 48]
    assert m.frame_list("", 3, 5) == [3, 4, 5]
    with pytest.raises(KeyError, match="loop_framez"):
        m.merged({"loop_frames": 73}, {"loop_framez": 2})


def test_hex_colours_take_three_or_six_digits():
    assert m.hex_rgba("#fff") == m.hex_rgba("#ffffff") == (1.0, 1.0, 1.0, 1.0)
    assert m.mix_hex("#000", "#ffffff", 0.5) == "#808080"
    with pytest.raises(ValueError):
        m.hex_rgba("#ffff")


def test_a_full_retime_maps_each_marker_and_shifts_outside_them():
    f = m.make_mapper({"start": 1, "hit": 25, "end": 49}, {"start": 1, "hit": 40, "end": 60})
    assert [f(x) for x in (1, 25, 49, 13, 61)] == [1, 40, 60, 20.5, 72]


def test_a_partial_retime_keeps_the_markers_it_does_not_name():
    f = m.make_mapper({"start": 1, "hit": 25, "end": 49}, {"hit": 40})
    assert [f(x) for x in (1, 25, 49, 55)] == [1, 40, 49, 55]      # end stays at 49; nothing past it moves


def test_retime_targets_must_be_whole_frames_and_keep_their_order():
    with pytest.raises(ValueError, match="whole frames"):
        m.make_mapper({"start": 1, "hit": 25}, {"hit": 40.5})
    with pytest.raises(ValueError, match="increase"):
        m.make_mapper({"start": 1, "hit": 25, "end": 49}, {"hit": 70})        # past the unnamed end marker
    with pytest.raises(KeyError, match="beat"):
        m.make_mapper({"start": 1}, {"beat": 4})


def test_two_bone_ik_reaches_a_point_in_range_and_reports_overshoot_out_of_range():
    t1, t2, over, reached = m.solve_leg((0.0, 0.8), (0.3, 0.0), 0.45, 0.45)
    knee = (0.45 * math.sin(t1), 0.8 - 0.45 * math.cos(t1))
    foot = (knee[0] + 0.45 * math.sin(t2), knee[1] - 0.45 * math.cos(t2))
    assert over == 0 and foot == pytest.approx((0.3, 0.0), abs=1e-6) and reached == pytest.approx((0.3, 0.0))
    assert m.solve_leg((0.0, 0.8), (1.0, 0.0), 0.45, 0.45)[2] > 0.3


def test_a_planted_foot_holds_its_place_through_the_stance():
    p = {"cycle_frames": 32, "duty": 0.6, "speed": 1.2, "fps": 30, "naive": False, "step_height": 0.12}
    hip_x = lambda k: 1.2 * k / 30  # noqa: E731
    stance = [m.foot_target(k, 0.0, p, hip_x) for k in range(0, 19)]       # the first 60 percent of the cycle
    assert len({x for x, _ in stance}) == 1 and all(z == 0.0 for _, z in stance)
    naive = [m.foot_target(k, 0.0, {**p, "naive": True}, hip_x)[0] for k in range(0, 3)]
    assert max(abs(b - a) for a, b in zip(naive, naive[1:])) > 0.01         # the control slides


def _strip(n=65, width=2.0, z=0.01):
    return [(-width / 2 + width * i / (n - 1), 0.0, z) for i in range(n)]


def test_a_fold_turns_the_right_half_onto_the_left_on_an_arc():
    cur = _strip()
    done, zone = m.fold_positions(cur, 0.0, 0.015, 1.0, 0.06)
    assert zone and max(x for x, _, _ in done) < 0.08                       # the right half now lies over the left
    edge = max(range(len(cur)), key=lambda i: cur[i][0])
    half, _ = m.fold_positions(cur, 0.0, 0.015, 0.5, 0.06)
    assert half[edge][2] == pytest.approx(1.0 + 0.015, abs=1e-6)            # a quarter turn: the edge straight up
    straight = [(a[2] + b[2]) / 2 for a, b in zip(cur, done)]               # the control: one key, a straight blend
    assert straight[edge] < 0.5 * half[edge][2]                             # squashes the edge to half the height


def test_no_point_of_a_crease_dips_under_where_it_started():
    cur = _strip()
    for frac in (0.1, 0.3, 0.5, 0.8, 1.0):
        out, _ = m.fold_positions(cur, 0.0, 0.015, frac, 0.06)
        assert min(z - z0 for (_, _, z), (_, _, z0) in zip(out, cur)) >= 0.0


def test_the_crease_radius_shrinks_with_the_stack():
    assert m.crease_radius(0.06, 2.0) == 0.06 and m.crease_radius(0.06, 1.0) == pytest.approx(0.06)
    assert m.crease_radius(0.06, 0.5) == pytest.approx(0.03) and m.crease_radius(0.06, 0.25) == pytest.approx(0.015)
