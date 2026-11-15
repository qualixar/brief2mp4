"""Shared fixtures for the 3D pack tests.

The pack is tested against an installed copy: B2M3D_HOME (default ~/.brief2mp4/3d) must hold the
`core` component. Run through tests/run_tests.sh, which picks that venv's Python. Tests that need
an optional piece (CadQuery, Blender, network) skip with a reason instead of failing.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin" / "skills" / "brief2mp4"
PACK = SKILL / "3d"
EXAMPLE = PACK / "examples" / "04-3d-product"
HYPERFRAMES = "hyperframes@0.8.216"

sys.path.insert(0, str(PACK))
from b2m3d import paths  # noqa: E402  (stdlib only, safe before the venv check)

HOME = Path(os.environ.get("B2M3D_HOME") or Path.home() / ".brief2mp4" / "3d")
os.environ["B2M3D_HOME"] = str(HOME)


def core_installed() -> bool:
    return paths.venv_python().exists() and (paths.node_modules() / "three").is_dir()


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


needs_core = pytest.mark.skipif(
    not (core_installed() and has_module("trimesh") and has_module("numpy")),
    reason="core component not installed or tests not run with its Python (use tests/run_tests.sh)")
needs_cadquery = pytest.mark.skipif(not has_module("cadquery"), reason="cad component not installed")
needs_blender = pytest.mark.skipif(paths.blender() is None, reason="Blender not found")
needs_npx = pytest.mark.skipif(shutil.which("npx") is None, reason="npx not found")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: renders or launches external tools (HyperFrames, Blender)")


def cli(*args: str, home: Path | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run `python -m b2m3d ...` the way an agent would."""
    env = {**os.environ, "B2M3D_HOME": str(home or HOME), "PYTHONPATH": str(PACK)}
    py = paths.venv_python() if (home is None and paths.venv_python().exists()) else Path(sys.executable)
    return subprocess.run([str(py), "-m", "b2m3d", *args], capture_output=True, text=True, env=env, cwd=cwd)


def cli_json(*args: str, **kw) -> dict:
    proc = cli(*args, **kw)
    assert proc.returncode == 0, f"b2m3d {' '.join(args)} failed:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(proc.stdout)


def online(host: str = "cdn.jsdelivr.net") -> bool:
    try:
        socket.create_connection((host, 443), timeout=5).close()
        return True
    except OSError:
        return False


def ffprobe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,width,height:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    return {**data["streams"][0], "duration": float(data["format"]["duration"])}


def hyperframes(*args: str, cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess:
    npx = shutil.which("npx")
    return subprocess.run([npx, "--yes", HYPERFRAMES, *args], capture_output=True, text=True,
                          cwd=cwd, timeout=timeout)


@pytest.fixture(scope="session")
def parts(tmp_path_factory) -> dict[str, Path]:
    """Raw GLBs for the example's five parts, built in-process (fast)."""
    from b2m3d import model
    out = tmp_path_factory.mktemp("parts")
    built = {}
    for name in ("shell", "cell", "board", "cover", "lens"):
        built[name] = out / f"{name}.glb"
        model.build(EXAMPLE / "device.py", built[name], {"part": name})
    return built
