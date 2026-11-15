"""Slow tests: real renders. One heavy job at a time, HyperFrames with 4 workers."""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import (EXAMPLE, PACK, SKILL, cli, cli_json, ffprobe, hyperframes, needs_blender, needs_core,
                      needs_npx, online, paths)

pytestmark = pytest.mark.slow
BASH = None if os.name == "nt" else "bash"


@needs_core
@needs_npx
def test_example_04_lints_clean_and_renders_two_seconds(tmp_path):
    work = tmp_path / "work"
    build = subprocess.run([str(paths.venv_python()), str(EXAMPLE / "build.py"), str(work)],
                           capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(PACK)})
    assert build.returncode == 0, build.stderr
    lint = hyperframes("lint", str(work / "project"), cwd=work)
    assert lint.returncode == 0 and "0 errors" in lint.stdout, lint.stdout + lint.stderr

    shot = json.loads((work / "shot.json").read_text(encoding="utf-8"))
    shot["duration"] = 2
    (work / "short.json").write_text(json.dumps(shot), encoding="utf-8")
    cli_json("hf", str(work / "short.json"), str(work / "short"))
    out = work / "short.mp4"
    render = hyperframes("render", str(work / "short"), "--workers", "4", "--quality", "draft",
                         "-o", str(out), "--quiet", cwd=work)
    assert render.returncode == 0 and out.exists(), render.stdout + render.stderr
    info = ffprobe(out)
    assert (info["width"], info["height"]) == (1920, 1080)
    assert info["duration"] == pytest.approx(2.0, abs=0.15)


@needs_core
@needs_blender
def test_blender_renders_opaque_and_transparent(tmp_path, parts):
    from b2m3d import encode
    opaque = cli_json("blender", str(parts["cover"]), str(tmp_path / "f1"), "--frames", "2", "--width", "320",
                      "--height", "180", "--samples", "8", "--look", "dramatic", "--mp4", str(tmp_path / "o.mp4"))
    assert opaque["frames"] == 2 and len(list((tmp_path / "f1").glob("frame_*.png"))) == 2
    assert opaque["device"] in {"GPU", "CPU"}
    info = ffprobe(tmp_path / "o.mp4")
    expected = "hevc" if sys.platform == "darwin" and encode.has_encoder("hevc_videotoolbox") else "h264"
    assert (info["codec_name"], info["width"]) == (expected, 320)

    alpha = cli_json("blender", str(parts["cover"]), str(tmp_path / "f2"), "--frames", "2", "--width", "320",
                     "--height", "180", "--samples", "8", "--look", "studio", "--transparent",
                     "--mp4", str(tmp_path / "a.mp4"))
    assert alpha["video"]["encoder"] == "prores_ks" and alpha["video"]["path"].endswith(".mov")
    assert ffprobe(tmp_path / "a.mov")["codec_name"] == "prores"


@needs_npx
@pytest.mark.skipif(BASH is None, reason="uses detect_3d.sh")
def test_fallback_when_pack_is_hidden_plain_template_still_renders(tmp_path):
    hidden = tmp_path / "no-pack"
    hidden.mkdir()
    detect = subprocess.run([BASH, str(SKILL / "scripts" / "detect_3d.sh")], capture_output=True, text=True,
                            env={**os.environ, "B2M3D_HOME": str(hidden)})
    assert detect.stdout.strip() == "3d: not installed" and detect.returncode == 0
    doctor = json.loads(cli("doctor", home=hidden).stdout)
    assert doctor["ok"] is False

    if not online():
        pytest.skip("vendoring three.js and GSAP needs npm and the network once; offline")
    project = tmp_path / "plain"
    project.mkdir()
    html = (SKILL / "templates" / "threejs" / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'data-duration="\d+(\.\d+)?"', 'data-duration="2"', html)
    html = re.sub(r"const DURATION = \d+(\.\d+)?;", "const DURATION = 2;", html)
    (project / "index.html").write_text(html, encoding="utf-8")
    vendor = subprocess.run(["bash", str(SKILL / "scripts" / "vendor_libs.sh"), str(project), "--three"],
                            capture_output=True, text=True)
    assert vendor.returncode == 0, vendor.stderr
    out = tmp_path / "plain.mp4"
    render = hyperframes("render", str(project), "--workers", "4", "--quality", "draft", "-o", str(out),
                         "--quiet", cwd=tmp_path)
    assert render.returncode == 0 and out.exists(), render.stdout + render.stderr
    info = ffprobe(out)
    assert (info["width"], info["height"]) == (1920, 1080)
    assert info["duration"] == pytest.approx(2.0, abs=0.15)


def test_threejs_template_has_no_network_urls():
    """The plain template must render offline: libraries come from vendor/, never a CDN."""
    html = (SKILL / "templates" / "threejs" / "index.html").read_text(encoding="utf-8")
    assert "https://" not in html and "http://" not in html
