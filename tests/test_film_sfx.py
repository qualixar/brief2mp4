"""sfx_synth.py: sound effects made in code. Deterministic, peaks held under -1 dBTP, no white-noise whooshes."""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

import film_common as fc
import sfx_synth as sx

NAMES = ["whoosh", "tick", "thud", "paper", "typewriter", "riser", "hit"]


def test_every_effect_in_the_spec_exists():
    assert set(NAMES) <= set(sx.EFFECTS)


@pytest.mark.parametrize("name", NAMES)
def test_same_seed_same_bytes_and_other_seed_other_bytes(name, tmp_path):
    a, b, c = (tmp_path / f"{n}.wav" for n in "abc")
    sx.write_effect(name, a, seed=7)
    sx.write_effect(name, b, seed=7)
    sx.write_effect(name, c, seed=8)
    assert a.read_bytes() == b.read_bytes()
    assert a.read_bytes() != c.read_bytes()


@pytest.mark.parametrize("name", NAMES)
def test_samples_are_in_range_and_not_silent_and_not_clipped(name):
    s = sx.synth(name, seed=1)
    assert len(s) > 0 and 0.9 <= max(abs(v) for v in s) / sx.peak_linear() <= 1.0001
    assert max(abs(v) for v in s) < 1.0


@pytest.mark.parametrize("name", NAMES)
def test_true_peak_is_at_or_under_minus_one_dbtp_as_ffmpeg_measures_it(name, tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not found")
    out = tmp_path / f"{name}.wav"
    sx.write_effect(name, out, seed=3)
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    peak = float(re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", err)[-1])
    assert -2.5 <= peak <= -1.0, peak


def test_own_true_peak_estimate_sees_an_intersample_peak():
    # two samples of 0.9 at +-phase: the waveform between them peaks above either sample
    import math
    s = [0.9 * math.sin(2 * math.pi * 0.25 * i + 0.785) for i in range(64)]
    assert sx.true_peak(s) > max(abs(v) for v in s) + 0.05


def test_peak_lag_is_where_the_loudest_sample_is():
    assert sx.peak_lag([0.0, 0.1, 0.9, 0.2, -0.3], rate=4) == pytest.approx(0.5)
    assert sx.peak_lag(sx.synth("riser", 1)) > 0.9 * len(sx.synth("riser", 1)) / sx.RATE      # a riser peaks at its end, which is why it is pinned
    assert sx.peak_lag(sx.synth("tick", 1)) < 0.02
    assert 0.15 < sx.peak_lag(sx.synth("whoosh", 1)) < 0.6


def test_whoosh_has_no_white_noise(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not found")
    out = tmp_path / "w.wav"
    sx.write_effect("whoosh", out, seed=5)

    def level(af):
        err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-af", af + ",volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(re.search(r"mean_volume: (-?[0-9.]+) dB", err).group(1))

    assert level("highpass=f=9000") < level("anull") - 25                       # almost nothing above 9 kHz


@pytest.mark.parametrize("name,low,high", [("whoosh", 0.3, 1.2), ("tick", 0.02, 0.15), ("thud", 0.3, 1.0), ("paper", 0.25, 1.0),
                                           ("typewriter", 0.8, 3.0), ("riser", 1.0, 4.0), ("hit", 0.5, 2.0)])
def test_lengths_are_usable(name, low, high):
    assert low <= len(sx.synth(name, 1)) / sx.RATE <= high


def test_seconds_option_changes_a_riser_length():
    assert len(sx.synth("riser", 1, seconds=3.0)) / sx.RATE == pytest.approx(3.0, abs=0.01)


def test_unknown_effect_names_the_choices():
    with pytest.raises(sx.SfxError, match="whoosh"):
        sx.synth("boing", 1)


def test_cli_all_writes_every_file_and_a_manifest_with_peak_lags(tmp_path):
    proc = fc.py_script("sfx_synth.py", "all", "--out-dir", tmp_path, "--seed", "11")
    assert proc.returncode == 0 and proc.stdout.count("PASS") == 1, proc.stdout + proc.stderr
    manifest = json.loads((tmp_path / "sfx.json").read_text(encoding="utf-8"))
    assert set(NAMES) <= set(manifest["effects"])
    for name in NAMES:
        entry = manifest["effects"][name]
        assert (tmp_path / entry["file"]).is_file() and entry["peak_lag"] >= 0 and entry["seconds"] > 0 and entry["seed"] == 11
    assert "license" in manifest["note"].lower() or "licen" in manifest["note"].lower()


def test_cli_make_one_and_bad_name(tmp_path):
    ok = fc.py_script("sfx_synth.py", "make", "tick", "--out", tmp_path / "t.wav")
    assert ok.returncode == 0 and (tmp_path / "t.wav").is_file()
    bad = fc.py_script("sfx_synth.py", "make", "boing", "--out", tmp_path / "b.wav")
    assert bad.returncode == 1 and bad.stdout.startswith("FAIL")


def test_no_random_module_state_leaks_between_calls():
    import random
    random.seed(99)
    first = random.random()
    sx.synth("paper", 4)
    random.seed(99)
    assert random.random() == first
    assert sx.synth("paper", 4) == sx.synth("paper", 4)
