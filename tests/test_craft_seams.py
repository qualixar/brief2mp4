"""check_seams.py: flicker, joins, cut classification and freeze, each proven on a clip that must pass AND one that must fail."""
from __future__ import annotations

import importlib.util
import sys

import pytest

from craft_common import SCRIPTS, bash_script, cut_clip, frozen_clip, joined_clip, moving_clip, needs_bash, needs_ffmpeg, pan_clip, py_script

spec = importlib.util.spec_from_file_location("check_seams", SCRIPTS / "check_seams.py")
seams = importlib.util.module_from_spec(spec)
sys.modules["check_seams"] = seams
spec.loader.exec_module(seams)

pytestmark = needs_ffmpeg


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("seams")
    return {
        "clean": moving_clip(d / "clean.mp4"),
        "flash1": moving_clip(d / "flash1.mp4", flash=(45, 45)),
        "flash3": moving_clip(d / "flash3.mp4", flash=(45, 47)),
        "cut": cut_clip(d / "cut.mp4"),
        "joined": joined_clip(d / "joined.mp4"),
        "pan": pan_clip(d / "pan.mp4"),
        "frozen": frozen_clip(d / "frozen.mp4"),
    }


def lines(proc):
    return proc.stdout.splitlines()


# ---- flicker ---------------------------------------------------------------------------------------------------

def test_clean_clip_passes(clips):
    proc = py_script("check_seams.py", clips["clean"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS  no one-frame pop or flicker" in proc.stdout and "FAIL" not in proc.stdout


@pytest.mark.parametrize("name,length", [("flash1", 1), ("flash3", 3)])
def test_a_white_flash_fails(clips, name, length):
    proc = py_script("check_seams.py", clips[name])
    assert proc.returncode == 1, proc.stdout
    assert any(l.startswith("FAIL  flicker at 1.50s") and f"{length} odd frame" in l for l in lines(proc)), proc.stdout


def test_a_flash_is_not_also_counted_as_a_cut(clips):
    out = py_script("check_seams.py", clips["flash1"]).stdout
    assert "hard cuts (scdet >= 6 and 2x its neighbours): 0" in out


def test_flicker_threshold_is_adjustable(clips):
    proc = py_script("check_seams.py", clips["flash1"], "--flicker-min", "250")
    assert proc.returncode == 0, "a change this small is below an absurd floor, so nothing should fire"


# ---- hard cut or soft ------------------------------------------------------------------------------------------

def test_a_real_cut_is_classified_as_hard_not_flicker(clips):
    proc = py_script("check_seams.py", clips["cut"])
    assert proc.returncode == 0, proc.stdout
    assert "hard cuts (scdet >= 6 and 2x its neighbours): 1 at 1.50s" in proc.stdout


def test_a_pan_has_no_hard_cut_and_is_not_frozen(clips):
    proc = py_script("check_seams.py", clips["pan"])
    assert proc.returncode == 0
    assert "hard cuts (scdet >= 6 and 2x its neighbours): 0" in proc.stdout
    assert "PASS  nothing frozen" in proc.stdout


def test_two_signals_are_needed_for_a_hard_cut():
    # scdet fired at frame 5 but the frame difference there is only like its neighbours (a fast pan): soft.
    diffs = [0.0] + [9.0] * 10
    hard, soft = seams.classify_changes(diffs, {5: 30.0}, skip=set())
    assert hard == [] and soft == [5]
    # a spike 10x its neighbours with a scdet hit is a hard cut
    diffs[5] = 90.0
    hard, soft = seams.classify_changes(diffs, {5: 30.0}, skip=set())
    assert hard == [5] and soft == []


# ---- joins -----------------------------------------------------------------------------------------------------

def test_a_clean_join_passes(clips):
    proc = py_script("check_seams.py", clips["joined"], "--joins", "1.5")
    assert proc.returncode == 0, proc.stdout
    assert "PASS  join at 1.50s SSIM" in proc.stdout


def test_a_mismatched_join_fails(clips):
    proc = py_script("check_seams.py", clips["cut"], "--joins", "1.5")
    assert proc.returncode == 1, proc.stdout
    assert any(l.startswith("FAIL  join at 1.50s") and "a pop" in l for l in lines(proc)), proc.stdout


def test_a_join_outside_the_video_is_a_warning(clips):
    proc = py_script("check_seams.py", clips["clean"], "--joins", "99")
    assert proc.returncode == 0 and "WARN  join at" in proc.stdout


# ---- freeze ----------------------------------------------------------------------------------------------------

def test_a_true_freeze_warns(clips):
    proc = py_script("check_seams.py", clips["frozen"])
    assert any(l.startswith("WARN  1 frozen stretch") and "1.00s for 3.0s" in l for l in lines(proc)), proc.stdout


def feed_all(frame_list):
    t = seams.FreezeTracker()
    for i in range(1, len(frame_list)):
        t.feed(i, frame_list[i - 1], frame_list[i])
    return t.finish(len(frame_list))


def test_a_slow_drift_is_not_a_freeze_but_identical_and_noisy_frames_are():
    n = seams.W * seams.H
    base = bytes((k * 7) % 200 for k in range(n))
    # every frame, a different fifth of the pixels gets 1 brighter: each step is only 0.2 (below the per-frame limit)
    # but the picture keeps moving away from where it started, like a very slow pan
    drifting = [bytes(base[k] + ((i - k % 5) // 5 + 1 if i >= k % 5 else 0) for k in range(n)) for i in range(60)]
    assert seams.mad(drifting[0], drifting[1]) == pytest.approx(0.2, abs=0.01)
    assert all(length < 12 for _, length in feed_all(drifting)), "a slow drift must not read as a long freeze"
    assert feed_all([base] * 60) == [(0, 60)]
    # sensor-style noise: 10% of pixels flip by 1 and back, with no drift at all: still frozen
    noisy = [bytes(base[k] + (1 if (k % 10 == 0 and i % 2) else 0) for k in range(n)) for i in range(60)]
    assert seams.mad(noisy[0], noisy[1]) == pytest.approx(0.1, abs=0.01)
    assert feed_all(noisy) == [(0, 60)]


def test_ssim_is_one_for_equal_frames_and_low_for_different_ones():
    a = bytes(range(256)) * (seams.W * seams.H // 256 + 1)
    a = a[:seams.W * seams.H]
    b = bytes(reversed(a))
    assert seams.ssim(a, a) == pytest.approx(1.0)
    assert seams.ssim(a, b) < 0.5


# ---- wired into check_delivery.sh -------------------------------------------------------------------------------

@needs_bash
def test_check_delivery_reports_the_flicker_and_fails(clips):
    proc = bash_script("check_delivery.sh", clips["flash1"], "--seconds", "3", "--size", "320x180", "--silent-ok")
    assert proc.returncode == 1
    assert "FAIL  flicker at 1.50s" in proc.stdout and "RESULT: FAIL" in proc.stdout


@needs_bash
def test_check_delivery_passes_the_seam_checks_on_a_clean_clip_and_passes_joins_through(clips):
    proc = bash_script("check_delivery.sh", clips["joined"], "--seconds", "3", "--size", "320x180", "--joins", "1.5")
    assert "PASS  no one-frame pop or flicker" in proc.stdout
    assert "PASS  join at 1.50s SSIM" in proc.stdout
    assert "nothing frozen" in proc.stdout
