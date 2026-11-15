"""Helpers shared by the edit-pack tests (no tests here)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin" / "skills" / "brief2mp4"
EDIT = SKILL / "edit"
RECIPES = EDIT / "recipes"
SCRIPTS = SKILL / "scripts"
VERSIONS = json.loads((EDIT / "versions.json").read_text(encoding="utf-8"))
APPS = ("film", "sound", "effect", "photo", "vector")
PLATFORMS = ("macos-universal", "windows-x64", "windows-arm64", "linux-x86_64", "linux-aarch64")

BASH = None if os.name == "nt" else "bash"
posix_only = pytest.mark.skipif(BASH is None, reason="bash scripts (Git Bash on Windows runs the recipes, not this installer)")


def run(cmd: list, env: dict | None = None, cwd: Path | None = None, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, **(env or {})}, cwd=cwd)


def make_stub_cli(path: Path, exit_code: int = 0) -> Path:
    """A fake pinned CLI: answers --version with the given exit code."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho stub 0.0.0\nexit {exit_code}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def ffprobe(path: Path, entries: str, stream: str = "v:0") -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", entries,
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def frame_hash(path: Path, seconds: float, crop: str | None = None) -> str:
    """md5 of one decoded frame (optionally a crop WxH+X+Y given as ffmpeg crop=w:h:x:y)."""
    vf = f"crop={crop}," if crop else ""
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(path), "-frames:v", "1",
                          "-vf", vf + "format=rgb24", "-f", "md5", "-"], capture_output=True, text=True, check=True).stdout
    return out.strip()


def tone_peak_db(path: Path, start: float, dur: float, freq: int) -> float:
    """Peak level (dB) of one sine tone in a time window of a WAV, isolated with a band-pass filter."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(start), "-t", str(dur), "-i", str(path), "-af",
                          f"bandpass=f={freq}:width_type=h:w=40,volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True, check=True).stderr
    line = next(l for l in err.splitlines() if "max_volume" in l)
    return float(line.split("max_volume:")[1].split("dB")[0])


needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="ffmpeg/ffprobe not found")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not found")
