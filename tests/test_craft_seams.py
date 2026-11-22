"""check_seams.py: flicker, joins, cut classification and freeze, each proven on a clip that must pass AND one that must fail."""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

from craft_common import (SCRIPTS, BASH, bash_script, with_silent_audio, cut_clip, frozen_clip, joined_clip, moving_clip, needs_bash, needs_ffmpeg, pan_clip,
                          py_script, truncated_clip, vfr_clip)

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
        "vfr": vfr_clip(d / "vfr.mp4"),
        "trunc": truncated_clip(d / "trunc.mp4"),
    }


def lines(proc):
    return proc.stdout.splitlines()


# ---- flicker ---------------------------------------------------------------------------------------------------

def test_clean_clip_passes(clips):
    proc = py_script("check_seams.py", clips["clean"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS  no one-frame pop or flicker" in proc.stdout and "FAIL" not in proc.stdout


@pytest.mark.parametrize("name,length", [("flash1", 1), ("flash3", 3)])
def test_a_white_flash_warns_by_default(clips, name, length):
    proc = py_script("check_seams.py", clips[name])
    assert proc.returncode == 0, proc.stdout
    assert any(l.startswith("WARN  flicker at 1.50s") and f"{length} odd frame" in l for l in lines(proc)), proc.stdout
    assert "PASS  no one-frame pop or flicker" not in proc.stdout


@pytest.mark.parametrize("name,length", [("flash1", 1), ("flash3", 3)])
def test_a_white_flash_fails_when_strict(clips, name, length):
    proc = py_script("check_seams.py", clips[name], "--strict")
    assert proc.returncode == 1, proc.stdout
    assert any(l.startswith("FAIL  flicker at 1.50s") and f"{length} odd frame" in l for l in lines(proc)), proc.stdout


def test_a_planned_flash_is_info_even_when_strict(clips):
    proc = py_script("check_seams.py", clips["flash1"], "--strict", "--flash-ok", "1.5")
    assert proc.returncode == 0, proc.stdout
    assert any(l.startswith("INFO  planned flash at 1.50s") for l in lines(proc)), proc.stdout
    assert "PASS  no one-frame pop or flicker" in proc.stdout


def test_a_planned_flash_elsewhere_does_not_excuse_this_one(clips):
    proc = py_script("check_seams.py", clips["flash1"], "--strict", "--flash-ok", "0.5")
    assert proc.returncode == 1, proc.stdout


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


# ---- a check that could not measure never passes ---------------------------------------------------------------

def test_a_truncated_file_fails_instead_of_passing_the_frames_it_could_read(clips):
    proc = py_script("check_seams.py", clips["trunc"])
    assert proc.returncode == 1, proc.stdout
    assert "FAIL  seams not measured: read" in proc.stdout and "holds 180" in proc.stdout
    assert "PASS" not in proc.stdout


def test_a_file_that_is_not_video_fails_with_a_fail_line(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_text("not a video", encoding="utf-8")
    proc = py_script("check_seams.py", bad)
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL  seams not measured"), proc.stdout + proc.stderr


def test_fewer_than_four_frames_is_a_fail_not_a_skip(tmp_path):
    from craft_common import X264, ffmpeg
    tiny = tmp_path / "tiny.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180:r=30", "-frames:v", "2", *X264, tiny)
    proc = py_script("check_seams.py", tiny)
    assert proc.returncode == 1 and "only 2 frame(s) could be read" in proc.stdout, proc.stdout
    assert "PASS" not in proc.stdout


@pytest.mark.parametrize("flag", ["--joins", "--flash-ok"])
def test_bad_time_lists_are_usage_errors(clips, flag):
    proc = py_script("check_seams.py", clips["clean"], flag, "1.5,abc")
    assert proc.returncode == 2 and "comma-separated list of seconds" in proc.stderr


def test_variable_frame_rate_times_are_real_seconds(clips):
    # 15 frames at 10 fps then 30 fps: the cut is at 1.5 s. Counting raw frames at the average rate puts it near 0.8 s.
    proc = py_script("check_seams.py", clips["vfr"])
    assert proc.returncode == 0, proc.stdout
    assert "hard cuts (scdet >= 6 and 2x its neighbours): 1 at 1.5" in proc.stdout, proc.stdout


# ---- wired into check_delivery.sh -------------------------------------------------------------------------------

@needs_bash
def test_check_delivery_reports_the_flicker_and_fails_when_strict(clips):
    proc = bash_script("check_delivery.sh", clips["flash1"], "--seconds", "3", "--size", "320x180", "--silent-ok",
                       "--strict-flicker")
    assert proc.returncode == 1
    assert "FAIL  flicker at 1.50s" in proc.stdout and "RESULT: FAIL" in proc.stdout


@needs_bash
def test_check_delivery_passes_the_seam_checks_on_a_clean_clip_and_passes_joins_through(clips):
    proc = bash_script("check_delivery.sh", clips["joined"], "--seconds", "3", "--size", "320x180", "--joins", "1.5")
    assert "PASS  no one-frame pop or flicker" in proc.stdout
    assert "PASS  join at 1.50s SSIM" in proc.stdout
    assert "nothing frozen" in proc.stdout


def delivery(clip, *extra, env=None):
    return bash_script("check_delivery.sh", clip, "--seconds", "3", "--size", "320x180", "--silent-ok", *extra, env=env or {})


@pytest.fixture(scope="module")
def sound_clips(clips, tmp_path_factory):
    d = tmp_path_factory.mktemp("delivery")
    return {k: with_silent_audio(clips[k], d / f"{k}.mp4") for k in ("clean", "flash1")}


@needs_bash
def test_check_delivery_passes_a_clean_clip_with_sound(sound_clips):
    proc = delivery(sound_clips["clean"])
    assert proc.returncode == 0 and "RESULT: PASS" in proc.stdout, proc.stdout


@needs_bash
def test_check_delivery_counts_a_seam_fail_as_its_own_fail(sound_clips):
    # everything else about this clip passes, so the only FAIL that can end the run is check_seams' flicker
    proc = delivery(sound_clips["flash1"], "--strict-flicker")
    assert proc.returncode == 1 and "RESULT: FAIL, 1 check(s)" in proc.stdout, proc.stdout


def fake_python(tmp_path, body):
    """A python3 first on PATH that runs `body` (bash) and otherwise hands over to the real interpreter."""
    d = tmp_path / "fakebin"
    d.mkdir()
    exe = d / "python3"
    exe.write_text(f"#!/usr/bin/env bash\n{body}\nexec '{sys.executable}' \"$@\"\n", encoding="utf-8", newline="\n")
    exe.chmod(0o755)
    return {"PATH": f"{d}{os.pathsep}{os.environ['PATH']}"}


@needs_bash
@pytest.mark.skipif(os.name == "nt", reason="a fake interpreter on PATH needs a POSIX shell")
def test_check_delivery_fails_when_check_seams_crashes(sound_clips, tmp_path):
    env = fake_python(tmp_path, 'for a in "$@"; do case "$a" in *check_seams.py) echo "Traceback (most recent call last):"; '
                                'echo "ZeroDivisionError: float division by zero" >&2; exit 1;; esac; done')
    proc = delivery(sound_clips["clean"], env=env)
    assert proc.returncode == 1, proc.stdout
    assert "FAIL  seam and freeze checks could not run (check_seams.py exit 1)" in proc.stdout and "RESULT: FAIL" in proc.stdout


@needs_bash
@pytest.mark.skipif(os.name == "nt", reason="a fake interpreter on PATH needs a POSIX shell")
def test_check_delivery_without_python_is_incomplete_not_pass(sound_clips, tmp_path):
    env = fake_python(tmp_path, "exit 1")
    proc = delivery(sound_clips["clean"], env=env)
    assert proc.returncode == 3, proc.stdout
    assert "SKIP  seam and freeze checks" in proc.stdout and "RESULT: INCOMPLETE" in proc.stdout and "RESULT: PASS" not in proc.stdout


@needs_bash
@pytest.mark.parametrize("flag,value", [("--joins", "1.5,abc"), ("--flash-ok", "x"), ("--seconds", "three"), ("--fps", "fast")])
def test_check_delivery_rejects_bad_numbers_before_measuring(sound_clips, flag, value):
    args = ["check_delivery.sh", sound_clips["clean"], "--seconds", "3", "--size", "320x180", "--silent-ok", flag, value]
    proc = bash_script(*args)
    assert proc.returncode == 2 and "RESULT" not in proc.stdout, proc.stdout + proc.stderr
