"""scripts/gen3d.py: optional image/text to 3D generators (Hunyuan3D-2, TRELLIS) that the user installs.

The wrapper never ships their code. These tests use tiny stand-in packages with the documented entry points, so
the call shape, the output file, the licence note and the missing-tool message are all checked without a GPU.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from conftest import SKILL

SCRIPT = SKILL / "scripts" / "gen3d.py"


def gen3d(*args, env=None):
    import os
    proc = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True,
                          env={**os.environ, "HUNYUAN3D_HOME": "", "TRELLIS_HOME": "", **(env or {})})
    return proc


def fake_hunyuan(home):
    for rel, body in {
        "hy3dgen/__init__.py": "",
        "hy3dgen/shapegen/__init__.py": (
            "class _Mesh:\n    def export(self, path):\n        open(path, 'wb').write(b'glTF-stand-in')\n"
            "class Hunyuan3DDiTFlowMatchingPipeline:\n"
            "    @classmethod\n    def from_pretrained(cls, name, device='cuda'):\n"
            "        o = cls(); o.name = name; print('DEVICE', device); return o\n"
            "    def __call__(self, image=None):\n        assert isinstance(image, (str, tuple)), image\n        print('IMAGE', image)\n        return [_Mesh()]\n"),
        "hy3dgen/rembg.py": "class BackgroundRemover:\n    def __call__(self, image):\n        return ('cut-out', image)\n",
        "PIL/__init__.py": "",
        "PIL/Image.py": "class _I:\n    def __init__(self, p):\n        self.p = p\n    def convert(self, mode):\n        return self.p\n"
                        "def open(p):\n    return _I(p)\n",
    }.items():
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text(body)


def fake_trellis(home):
    files = {
        "PIL/__init__.py": "", "PIL/Image.py": "def open(p):\n    return ('image', p)\n",
        "trellis/__init__.py": "",
        "trellis/pipelines/__init__.py": (
            "class _P:\n    @classmethod\n    def from_pretrained(cls, n):\n        return cls()\n    def cuda(self):\n        return self\n"
            "    def run(self, x, seed=1):\n        return {'gaussian': ['g'], 'mesh': ['m']}\n"
            "TrellisImageTo3DPipeline = _P\nTrellisTextTo3DPipeline = _P\n"),
        "trellis/utils/__init__.py": "",
        "trellis/utils/postprocessing_utils.py": (
            "class _G:\n    def export(self, path):\n        open(path, 'wb').write(b'glTF-stand-in')\n"
            "def to_glb(g, m, simplify=0.95, texture_size=1024):\n    return _G()\n"),
    }
    for rel, body in files.items():
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text(body)


def test_doctor_lists_both_tools_with_their_licence_lines():
    out = json.loads(gen3d("doctor").stdout)
    hun, tre = out["hunyuan3d"], out["trellis"]
    assert hun["installed"] is False and tre["installed"] is False
    assert "European Union" in hun["licence"] and "South Korea" in hun["licence"] and "United Kingdom" in hun["licence"]
    assert "MIT" in tre["licence"] and "NON-COMMERCIAL" in tre["licence"] and "nvdiffrast" in tre["licence"]
    assert "Acceptable Use Policy" in hun["licence"] and "machine-generated" in hun["licence"] and "military" in hun["licence"]
    assert "release date" in hun["licence"] and "PyTorch" in hun["install"] and "custom_rasterizer" in hun["install"]
    assert "pip install" in hun["install"] and "setup.sh" in tre["install"]
    for flag in ("--nvdiffrast", "--mipgaussian", "--diffoctreerast"):         # research-only parts are opt-in
        assert flag not in tre["install"] and flag not in tre["install_noncommercial"]
    assert tre["noncommercial"].startswith("WARNING")


def test_the_non_commercial_install_line_is_printed_only_when_asked_and_after_its_warning():
    tre = json.loads(gen3d("doctor", "--non-commercial").stdout)["trellis"]
    assert "--nvdiffrast" in tre["install_noncommercial"] and "research or evaluation" in tre["noncommercial"]


def test_trellis_refuses_to_run_until_non_commercial_use_is_confirmed(tmp_path):
    home = tmp_path / "tr"
    fake_trellis(home)
    proc = gen3d("run", "trellis", "--prompt", "a lamp", "--out", str(tmp_path / "l.glb"), env={"TRELLIS_HOME": str(home)})
    assert proc.returncode == 2 and proc.stderr.startswith("WARNING") and "--non-commercial" in proc.stderr
    assert not (tmp_path / "l.glb").exists()


def test_a_missing_tool_prints_how_to_install_and_exits_zero_with_a_skip_line(tmp_path):
    img = tmp_path / "in.png"
    img.write_bytes(b"x")
    proc = gen3d("run", "hunyuan3d", "--image", str(img), "--out", str(tmp_path / "o.glb"))
    assert proc.returncode == 0 and proc.stdout.startswith("SKIP")
    assert "HUNYUAN3D_HOME" in proc.stdout and not (tmp_path / "o.glb").exists()


def test_hunyuan_runs_the_documented_entry_point_and_writes_a_credit_sidecar(tmp_path):
    home = tmp_path / "hy"
    fake_hunyuan(home)
    img = tmp_path / "in.png"
    img.write_bytes(b"x")
    out = tmp_path / "chair.glb"
    proc = gen3d("run", "hunyuan3d", "--image", str(img), "--out", str(out), env={"HUNYUAN3D_HOME": str(home)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert out.read_bytes() == b"glTF-stand-in"
    side = json.loads((tmp_path / "chair.glb.source.json").read_text())
    assert side["tool"] == "Hunyuan3D-2" and "European Union" in side["licence"]
    assert "not valid in the European Union" in proc.stdout     # the note is printed before the run
    assert "DEVICE cuda" in proc.stdout                           # no --device: the tool's own default


def test_hunyuan_background_removal_and_device_reach_the_tool(tmp_path):
    home = tmp_path / "hy"
    fake_hunyuan(home)
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"x")
    out = tmp_path / "thing.glb"
    proc = gen3d("run", "hunyuan3d", "--image", str(img), "--out", str(out), "--remove-background", "--device", "mps",
                 env={"HUNYUAN3D_HOME": str(home)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "DEVICE mps" in proc.stdout and out.read_bytes() == b"glTF-stand-in"
    assert "IMAGE ('cut-out'," in proc.stdout                    # the cut-out, not the photo, went into the pipeline


def test_trellis_image_and_text_routes(tmp_path):
    home = tmp_path / "tr"
    fake_trellis(home)
    img = tmp_path / "in.png"
    img.write_bytes(b"x")
    env = {"TRELLIS_HOME": str(home)}
    a = gen3d("run", "trellis", "--image", str(img), "--out", str(tmp_path / "a.glb"), "--non-commercial", env=env)
    b = gen3d("run", "trellis", "--prompt", "a chair like an avocado", "--out", str(tmp_path / "b.glb"), "--non-commercial", env=env)
    assert a.returncode == 0 and b.returncode == 0, a.stdout + a.stderr + b.stdout + b.stderr
    assert (tmp_path / "a.glb").exists() and (tmp_path / "b.glb").exists()
    assert json.loads((tmp_path / "b.glb.source.json").read_text())["tool"] == "TRELLIS"


def test_one_input_only_and_hunyuan_has_no_text_route(tmp_path):
    proc = gen3d("run", "hunyuan3d", "--prompt", "a chair", "--out", str(tmp_path / "o.glb"), env={"HUNYUAN3D_HOME": str(tmp_path)})
    assert proc.returncode == 2 and "image" in proc.stderr


def test_dry_run_shows_the_command_without_running_anything(tmp_path):
    home = tmp_path / "tr"
    fake_trellis(home)
    proc = gen3d("run", "trellis", "--prompt", "a lamp", "--out", str(tmp_path / "l.glb"), "--dry-run", "--non-commercial",
                 env={"TRELLIS_HOME": str(home)})
    assert proc.returncode == 0 and "TrellisTextTo3DPipeline" in proc.stdout and not (tmp_path / "l.glb").exists()
