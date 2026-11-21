"""beat_grid.py: the grid maths and snap helper run anywhere; the librosa analysis runs when librosa is installed."""
from __future__ import annotations

import importlib.util
import json
import sys

import pytest

from craft_common import SCRIPTS, ffmpeg, needs_ffmpeg, py_script, run

spec = importlib.util.spec_from_file_location("beat_grid", SCRIPTS / "beat_grid.py")
bg = importlib.util.module_from_spec(spec)
sys.modules["beat_grid"] = bg
spec.loader.exec_module(bg)

needs_librosa = pytest.mark.skipif(importlib.util.find_spec("librosa") is None, reason="librosa not installed (optional)")


# ---- the maths (no librosa) ------------------------------------------------------------------------------------

def test_fit_grid_recovers_period_and_offset_from_jittered_beats():
    jitter = [0.004, -0.006, 0.003, -0.002, 0.005, -0.004, 0.0, 0.002]
    beats = [0.3 + i * 0.5 + j for i, j in enumerate(jitter)]
    t0, period, resid = bg.fit_grid(beats)
    assert period == pytest.approx(0.5, abs=0.003) and t0 == pytest.approx(0.3, abs=0.01)
    assert resid < 15, "a good fit stays under about 15 ms"


def test_fit_grid_survives_a_missed_beat():
    beats = [0.0, 0.5, 1.0, 2.0, 2.5, 3.0]          # the beat at 1.5 was missed
    _, period, resid = bg.fit_grid(beats)
    assert period == pytest.approx(0.5, abs=1e-6) and resid < 1


def test_fit_grid_rejects_too_few_beats():
    with pytest.raises(ValueError, match="fewer than 3 beats"):
        bg.fit_grid([0.5, 1.0])


def test_a_bad_fit_shows_in_the_residual():
    _, _, resid = bg.fit_grid([0.0, 0.5, 1.07, 1.5, 2.12, 2.5, 3.1])
    assert resid > 15


def test_grid_points_include_beats_before_the_first_one_found():
    pts = bg.grid_points(1.02, 0.5, 3.0)
    assert pts[0] == pytest.approx(0.02) and pts[-1] == pytest.approx(2.52) and len(pts) == 6


def test_half_or_double_speed_is_corrected_by_the_onsets():
    onsets = [i * 1.0 for i in range(10)]                          # real pulse: one per second
    factor, scores = bg.pick_speed(0.0, 0.5, 9.0, onsets, 0.04)     # tracker said 0.5 s (double speed)
    assert factor == 0.5 and scores[0.5] > scores[1.0]
    factor, _ = bg.pick_speed(0.0, 1.0, 9.0, onsets, 0.04)          # tracker was right
    assert factor == 1.0
    onsets = [i * 0.25 for i in range(37)]                          # real pulse: 4 per second, tracker said 0.5
    factor, _ = bg.pick_speed(0.0, 0.5, 9.0, onsets, 0.04)
    assert factor == 2.0


# ---- snap (no librosa) -----------------------------------------------------------------------------------------

@pytest.fixture
def grid_file(tmp_path):
    f = tmp_path / "grid.json"
    f.write_text(json.dumps({"beats": [0.0, 0.5, 1.0, 1.5, 2.0], "downbeats": [0.0, 2.0], "onsets": [0.02, 0.97]}), encoding="utf-8")
    return f


def test_snap_moves_close_times_and_leaves_far_ones(grid_file):
    proc = py_script("beat_grid.py", "snap", grid_file, "--times", "1.04,0.76", "--max-shift", "0.1")
    rows = json.loads(proc.stdout)
    assert rows[0] == {"in": 1.04, "out": 1.0, "shift_ms": -40.0, "snapped": True}
    assert rows[1]["snapped"] is False and rows[1]["out"] == 0.76, "0.24 s from the nearest beat is more than 0.1 s: it must not move"


def test_snap_to_downbeats_and_rounds_to_frames_last(grid_file):
    rows = json.loads(py_script("beat_grid.py", "snap", grid_file, "--times", "1.95", "--to", "downbeats", "--fps", "30").stdout)
    assert rows[0]["out"] == 2.0
    rows = json.loads(py_script("beat_grid.py", "snap", grid_file, "--times", "0.2", "--fps", "30").stdout)   # not snapped, still a whole frame
    assert rows[0]["out"] == pytest.approx(round(0.2 * 30) / 30, abs=1e-4)


def test_snap_emits_a_javascript_helper(grid_file):
    out = py_script("beat_grid.py", "snap", grid_file, "--emit", "js", "--times", "1.03").stdout
    assert "const GRID = [0.0, 0.5, 1.0, 1.5, 2.0];" in out and "const snap = (t, maxShift = 0.12)" in out
    assert out.strip().endswith("// snapped: [1.0]")


def test_snap_with_a_missing_list_fails(tmp_path):
    f = tmp_path / "g.json"
    f.write_text("{}", encoding="utf-8")
    proc = py_script("beat_grid.py", "snap", f, "--times", "1")
    assert proc.returncode == 1 and "has no 'beats' list" in proc.stderr


# ---- analysis ---------------------------------------------------------------------------------------------------

def test_without_librosa_analyze_skips_with_the_install_line_and_exits_0(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    code = ("import sys, runpy; sys.modules['librosa'] = None; sys.argv = ['beat_grid.py', 'analyze', %r]; "
            "runpy.run_path(%r, run_name='__main__')" % (str(wav), str(SCRIPTS / "beat_grid.py")))
    proc = run([sys.executable, "-c", code])
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("SKIP") and "python3 -m pip install --user librosa" in proc.stdout


def click_track(path, bpm=120, seconds=8):
    """Short 1 kHz clicks on every beat, louder on the first beat of each 4-beat bar."""
    period = 60.0 / bpm
    expr = f"(0.4+0.6*eq(mod(floor(t/{period}),4),0))*sin(2*PI*1000*t)*lt(mod(t,{period}),0.03)"
    ffmpeg("-f", "lavfi", "-i", f"aevalsrc='{expr}':s=22050:d={seconds}", "-ac", "1", path)
    return path


@needs_ffmpeg
@needs_librosa
def test_a_click_track_gives_its_tempo_a_tight_fit_and_the_accented_downbeats(tmp_path):
    wav = click_track(tmp_path / "c.wav", bpm=120)
    out = tmp_path / "grid.json"
    proc = py_script("beat_grid.py", "analyze", wav, "--out", out)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    grid = json.loads(out.read_text(encoding="utf-8"))
    assert grid["bpm"] == pytest.approx(120, abs=1.0) and grid["residual_ms"] < 15
    assert len(grid["beats"]) == 16 and grid["beats"][0] == pytest.approx(0.0, abs=0.04)
    expected = [0.0, 2.0, 4.0, 6.0]
    assert len(grid["downbeats"]) == 4 and all(abs(a - b) < 0.05 for a, b in zip(grid["downbeats"], expected))
    assert len(grid["onsets"]) >= 12


@needs_ffmpeg
@needs_librosa
def test_another_tempo_is_found_too(tmp_path):
    out = tmp_path / "grid.json"
    py_script("beat_grid.py", "analyze", click_track(tmp_path / "c.wav", bpm=90, seconds=10), "--out", out)
    assert json.loads(out.read_text(encoding="utf-8"))["bpm"] == pytest.approx(90, abs=1.5)


@needs_ffmpeg
@needs_librosa
def test_silence_fails_instead_of_inventing_a_grid(tmp_path):
    wav = tmp_path / "s.wav"
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", "-t", "5", wav)
    proc = py_script("beat_grid.py", "analyze", wav, "--out", tmp_path / "g.json")
    assert proc.returncode == 1 and "FAIL  beat_grid: fewer than 3 beats" in proc.stdout
    assert not (tmp_path / "g.json").exists()
