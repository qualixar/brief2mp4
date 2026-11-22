"""cut_points.sh: scene cuts as JSON (PySceneDetect, optional)."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from craft_common import bash_script, cut_clip, moving_clip, needs_bash, needs_ffmpeg

pytestmark = [needs_bash, needs_ffmpeg]
HAS_SCENEDETECT = importlib.util.find_spec("scenedetect") is not None or shutil.which("scenedetect") is not None
needs_scenedetect = pytest.mark.skipif(not HAS_SCENEDETECT, reason="PySceneDetect not installed (optional)")


def env_with_this_python():
    """Put the running Python's folder first on PATH so `scenedetect` and `python3` resolve to the same install."""
    return {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]}


@needs_scenedetect
def test_a_clip_with_one_cut_gives_one_cut_point(tmp_path):
    clip = cut_clip(tmp_path / "cut.mp4")
    out = tmp_path / "cuts.json"
    proc = bash_script("cut_points.sh", clip, "--out", out, env=env_with_this_python())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    assert data["detector"] == "content" and len(data["cuts"]) == 1 and data["cuts"][0] == pytest.approx(1.5, abs=0.07)
    assert [round(s["start"], 1) for s in data["scenes"]] == [0.0, 1.5]
    assert json.loads(out.read_text(encoding="utf-8")) == data


@needs_scenedetect
def test_continuous_motion_gives_no_cut_points(tmp_path):
    proc = bash_script("cut_points.sh", moving_clip(tmp_path / "m.mp4", seconds=3), env=env_with_this_python())
    data = json.loads(proc.stdout)
    assert proc.returncode == 0 and data["cuts"] == [] and len(data["scenes"]) == 1


@needs_scenedetect
def test_min_scene_drops_a_cut_that_comes_too_soon(tmp_path):
    clip = cut_clip(tmp_path / "cut.mp4")                                   # the cut is 1.5 s in
    data = json.loads(bash_script("cut_points.sh", clip, "--min-scene", "2.0", env=env_with_this_python()).stdout)
    assert data["cuts"] == []


def test_without_scenedetect_it_skips_with_the_install_command_and_exits_3(tmp_path):
    clip = cut_clip(tmp_path / "cut.mp4")
    proc = bash_script("cut_points.sh", clip, env={"SCENEDETECT": "definitely-not-installed"})
    assert proc.returncode == 3
    assert proc.stdout.startswith("SKIP") and "python3 -m pip install --user scenedetect opencv-python-headless" in proc.stdout


def test_bad_arguments_are_rejected(tmp_path):
    assert bash_script("cut_points.sh", tmp_path / "missing.mp4").returncode == 2
    clip = cut_clip(tmp_path / "cut.mp4")
    assert bash_script("cut_points.sh", clip, "--detector", "magic").returncode == 2
