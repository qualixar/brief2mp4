"""Edit pack, slow tests: install the pinned apps for real and run every recipe against them.

The pinned CLIs go into a temp B2M_EDIT_HOME (set B2M_EDIT_TEST_HOME to reuse one between runs and skip the
~450 MB download). Needs network on the first run, ffmpeg, node and bash. Run with: bash tests/run_tests.sh --slow
"""
from __future__ import annotations

import json
import re
import shutil
import socket
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from test_edit_common import (APPS, BASH, EDIT, RECIPES, SCRIPTS, VERSIONS, frame_hash, ffprobe, needs_ffmpeg, needs_node,
                              posix_only, run, tone_peak_db)

pytestmark = [pytest.mark.slow, posix_only, needs_ffmpeg, needs_node]
INSTALL = EDIT / "install_edit.sh"
NAMES = {a: VERSIONS["apps"][a]["name"] for a in APPS}


def _online() -> bool:
    try:
        socket.create_connection(("github.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def home(tmp_path_factory) -> Path:
    import os
    reuse = os.environ.get("B2M_EDIT_TEST_HOME")
    path = Path(reuse) if reuse else tmp_path_factory.mktemp("edit-home") / "home"
    if not _online() and not (path / "filmcraft").exists():
        pytest.skip("github.com not reachable and no preinstalled B2M_EDIT_TEST_HOME")
    proc = run([BASH, INSTALL, "--components", "all"], {"B2M_EDIT_HOME": str(path)})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return path


@pytest.fixture(scope="module")
def env(home) -> dict:
    return {"B2M_EDIT_HOME": str(home)}


def recipe(env: dict, name: str, *args) -> subprocess.CompletedProcess:
    proc = run([BASH, RECIPES / name, *args], env)
    assert proc.returncode == 0, f"{name} failed:\n{proc.stdout}\n{proc.stderr}"
    assert proc.stdout.startswith("ok: ")
    return proc


# ---- the installer, for real -----------------------------------------------------------------------------------

def test_every_pinned_cli_runs_with_its_pinned_version(home):
    for short, app in VERSIONS["apps"].items():
        launcher = home / "bin" / app["cli"]
        out = run([launcher, "--version"])
        assert out.returncode == 0 and app["version"] in out.stdout, (short, out.stdout, out.stderr)
        assert (home / app["name"] / ".b2m-version").read_text().strip() == app["version"]


def test_second_install_is_a_no_op_and_detect_sees_everything(home):
    again = run([BASH, INSTALL, "--components", "film,sound"], {"B2M_EDIT_HOME": str(home)})
    assert again.returncode == 0 and again.stdout.count("already installed") == 2 and "downloading" not in again.stdout
    out = run([BASH, SCRIPTS / "detect_edit.sh"], {"B2M_EDIT_HOME": str(home)})
    assert out.stdout.strip() == "edit: ready (film,sound,effect,photo,vector,light)"


def test_installed_pack_does_not_depend_on_the_repository(home, tmp_path):
    assert (home / "versions.json").exists() and (home / "recipes" / "_lib.sh").exists()
    out = run([BASH, home / "recipes" / "photo_thumbnail.sh", "--out", tmp_path / "t.png"], {"B2M_EDIT_HOME": str(home)})
    assert out.returncode == 0, out.stderr
    moved = tmp_path / "moved"
    shutil.copytree(home, moved, symlinks=True)    # a copied folder still launches: launchers use relative paths
    assert run([moved / "bin" / "photocraft-cli", "--version"]).returncode == 0


def test_a_changed_hash_pin_is_refused_and_installs_nothing(tmp_path):
    clone = tmp_path / "edit"
    shutil.copytree(EDIT, clone)
    pins = json.loads((clone / "versions.json").read_text())
    pins["apps"]["sound"]["assets"]["macos-universal"]["sha256"] = "0" * 64
    pins["apps"]["sound"]["assets"]["linux-x86_64"]["sha256"] = "0" * 64
    pins["apps"]["sound"]["assets"]["linux-aarch64"]["sha256"] = "0" * 64
    (clone / "versions.json").write_text(json.dumps(pins))
    home = tmp_path / "home"
    proc = run([BASH, clone / "install_edit.sh", "--components", "sound"], {"B2M_EDIT_HOME": str(home)})
    assert proc.returncode == 1 and "differs from the one pinned" in proc.stderr
    assert not (home / "soundcraft").exists() and not list(home.glob(".stage-*"))


def test_the_release_checksums_still_match_the_pins():
    """Catches a re-uploaded release: every pinned hash must equal the live SHA256SUMS.txt entry."""
    import urllib.request
    for app in VERSIONS["apps"].values():
        url = f"{VERSIONS['source']}/{app['name']}/releases/download/{app['tag']}/SHA256SUMS.txt"
        sums = dict(reversed(l.split()) for l in urllib.request.urlopen(url, timeout=30).read().decode().splitlines() if l.strip())
        for plat, asset in app["assets"].items():
            assert sums[asset["file"]] == asset["sha256"], (app["name"], plat)


# ---- the recipes -----------------------------------------------------------------------------------------------

def test_film_recipe_cuts_dissolves_and_titles(env, tmp_path):
    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    for out, src in ((a, "testsrc2"), (b, "gradients")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{src}=size=1280x720:rate=30:duration=4", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    one, two = tmp_path / "one.mp4", tmp_path / "two.mp4"
    recipe(env, "film_timeline.sh", "--clip-a", str(a), "--clip-b", str(b), "--title", "AAA", "--out", str(one),
           "--save-project", str(tmp_path / "p.fcproj"))
    recipe(env, "film_timeline.sh", "--clip-a", str(a), "--clip-b", str(b), "--title", "WWWWWWWWWW", "--out", str(two))
    v = ffprobe(one, "stream=codec_name,width,height,pix_fmt,nb_frames")["streams"][0]
    assert (v["codec_name"], v["width"], v["height"], v["pix_fmt"]) == ("h264", 1280, 720, "yuv420p")
    assert abs(float(ffprobe(one, "format=duration")["format"]["duration"]) - 5.0) < 0.1
    assert ffprobe(one, "stream=codec_name", "a:0")["streams"][0]["codec_name"] == "aac"
    assert (tmp_path / "p.fcproj").stat().st_size > 1000
    # Before the title (0.2 s) both cuts are identical; with the title on screen (1.0 s) they differ.
    assert frame_hash(one, 0.2) == frame_hash(two, 0.2) and frame_hash(one, 1.0) != frame_hash(two, 1.0)
    # The dissolve: the frame at the cut is neither of the frames either side of it.
    assert len({frame_hash(one, 1.9), frame_hash(one, 2.5), frame_hash(one, 3.1)}) == 3
    # The clean-clip frame just after the dissolve ends is B's picture: it differs from the frame inside the dissolve.
    assert frame_hash(one, 2.5) != frame_hash(one, 3.5)


def test_film_recipe_default_inputs_and_bad_input(env, tmp_path):
    recipe(env, "film_timeline.sh", "--out", tmp_path / "d.mp4", "--size", "640x360", "--fps", "25")
    assert ffprobe(tmp_path / "d.mp4", "stream=width,height")["streams"][0]["width"] == 640
    short = tmp_path / "short.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=1", "-f", "lavfi", "-i",
                    "sine=duration=1", "-shortest", str(short)], check=True)
    bad = run([BASH, RECIPES / "film_timeline.sh", "--clip-a", short, "--out", tmp_path / "x.mp4"], env)
    assert bad.returncode == 2 and "shorter than" in bad.stderr


def test_sound_recipe_mixes_and_ducks(env, tmp_path):
    voice, music = tmp_path / "voice.wav", tmp_path / "bed.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=150:duration=5,volume=4", str(voice)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=10,volume=4", str(music)], check=True)
    out = tmp_path / "mix.wav"
    recipe(env, "sound_mix.sh", "--voice", str(voice), "--music", str(music), "--voice-start", "2", "--out", str(out))
    a = ffprobe(out, "stream=codec_name,channels,sample_rate", "a:0")["streams"][0]
    assert (a["codec_name"], a["channels"], a["sample_rate"]) == ("pcm_s24le", 2, "48000")
    assert abs(float(ffprobe(out, "format=duration")["format"]["duration"]) - 10.0) < 0.05
    bed_before, bed_after = tone_peak_db(out, 0.2, 1.2, 880), tone_peak_db(out, 9.0, 0.8, 880)
    bed_under_voice, voice = tone_peak_db(out, 3.0, 3.5, 880), tone_peak_db(out, 3.0, 3.5, 150)
    assert bed_before - bed_under_voice >= 10 and bed_after - bed_under_voice >= 10      # ducked by about 12 dB
    assert voice > bed_under_voice + 10                                                  # the voice sits above the bed
    assert tone_peak_db(out, 0.2, 1.2, 150) < voice - 20                                # nothing of the voice before it starts


def test_sound_recipe_with_generated_inputs(env, tmp_path):
    recipe(env, "sound_mix.sh", "--out", tmp_path / "g.wav", "--duck-db", "-24")
    assert ffprobe(tmp_path / "g.wav", "stream=codec_name", "a:0")["streams"][0]["codec_name"] == "pcm_s24le"


def test_effect_recipe_renders_an_animated_title(env, tmp_path):
    out = tmp_path / "t.mp4"
    recipe(env, "effect_title.sh", "--text", "Chapter one", "--seconds", "3", "--out", str(out), "--save-project", str(tmp_path / "t.ecproj"))
    v = ffprobe(out, "stream=codec_name,width,height,pix_fmt,r_frame_rate")["streams"][0]
    assert (v["codec_name"], v["width"], v["height"], v["pix_fmt"], v["r_frame_rate"]) == ("h264", 1280, 720, "yuv420p", "30/1")
    assert abs(float(ffprobe(out, "format=duration")["format"]["duration"]) - 3.0) < 0.05
    assert ffprobe(out, "stream=codec_name", "a:0")["streams"] == []
    assert (tmp_path / "t.ecproj").stat().st_size > 500
    # Animated: the title is invisible at 0 s, there at 2.5 s, and the bar has grown by then.
    assert len({frame_hash(out, 0.0), frame_hash(out, 0.5), frame_hash(out, 2.5)}) == 3


def test_photo_recipe_makes_a_thumbnail(env, tmp_path):
    out = tmp_path / "t.png"
    recipe(env, "photo_thumbnail.sh", "--title", "Cut faster", "--subtitle", "three habits", "--out", str(out))
    head = out.read_bytes()[:33]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", head[16:24]) == (1280, 720)
    other = tmp_path / "u.png"
    recipe(env, "photo_thumbnail.sh", "--title", "Something else", "--subtitle", "three habits", "--out", str(other))
    # Title zone (left, upper middle) differs between the two cards; the bottom strip (no text) is identical.
    assert frame_hash(out, 0, "900:200:80:260") != frame_hash(other, 0, "900:200:80:260")
    assert frame_hash(out, 0, "1200:80:40:600") == frame_hash(other, 0, "1200:80:40:600")
    # The title is bright text on a dark gradient.
    stats = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out), "-vf", "crop=900:200:80:260,signalstats,metadata=print", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    assert float(re.search(r"YMAX=(\d+)", stats).group(1)) > 220


def test_photo_recipe_other_size(env, tmp_path):
    recipe(env, "photo_thumbnail.sh", "--size", "1920x1080", "--out", tmp_path / "big.png")
    assert struct.unpack(">II", (tmp_path / "big.png").read_bytes()[16:24]) == (1920, 1080)


def test_vector_recipe_exports_a_lower_third_svg(env, tmp_path):
    out = tmp_path / "lt.svg"
    recipe(env, "vector_lower_third.sh", "--name", "Alex & Doe", "--role", "Video <editor>", "--out", str(out))
    root = ET.parse(out).getroot()                                  # parses: special characters were escaped
    assert root.tag.endswith("svg") and root.get("width") == "1280" and root.get("height") == "200"
    texts = ["".join(t.itertext()).strip() for t in root.iter() if t.tag.endswith("text")]
    assert texts == ["Alex & Doe", "Video <editor>"]
    shapes = [t.tag.split("}")[1] for t in root.iter() if t.tag.split("}")[1] in {"rect", "path"}]
    assert len(shapes) == 2
    assert 'stroke="#000000"' not in out.read_text()                # strokes were switched off
    recipe(env, "vector_lower_third.sh", "--width", "1920", "--height", "300", "--out", tmp_path / "big.svg")
    assert ET.parse(tmp_path / "big.svg").getroot().get("width") == "1920"


def _mean_rgb(path: Path) -> list[int]:
    """The average colour of an image, from ffmpeg scaling it to one pixel."""
    return list(subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               capture_output=True, check=True).stdout)


def test_light_recipe_grades_a_still_warm_and_leaves_the_original(env, tmp_path):
    src = tmp_path / "in.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "gradients=s=640x360:c0=0x3c6e9e:c1=0xe6e6dc:seed=4,format=rgb24",
                    "-frames:v", "1", str(src)], check=True)
    before = src.read_bytes()
    out = tmp_path / "graded.jpg"
    recipe(env, "light_grade.sh", "--in", str(src), "--out", str(out))
    assert src.read_bytes() == before                                        # the original is untouched
    stream = ffprobe(out, "stream=width,height")["streams"][0]
    assert (stream["width"], stream["height"]) == (640, 360)
    r0, _, b0 = _mean_rgb(src)
    r1, _, b1 = _mean_rgb(out)
    assert (r1 - b1) - (r0 - b0) >= 4, ((r0, b0), (r1, b1))                  # warmer: red went up against blue
    strong = tmp_path / "strong.jpg"
    recipe(env, "light_grade.sh", "--in", str(src), "--amount", "200", "--out", str(strong))
    r2, _, b2 = _mean_rgb(strong)
    assert (r2 - b2) > (r1 - b1)                                             # a bigger amount warms more


def test_light_recipe_default_input_size_option_and_bad_preset(env, tmp_path):
    recipe(env, "light_grade.sh", "--out", tmp_path / "d.png")
    assert ffprobe(tmp_path / "d.png", "stream=width,height")["streams"][0]["width"] == 1280
    recipe(env, "light_grade.sh", "--size", "320", "--out", tmp_path / "small.jpg")
    assert ffprobe(tmp_path / "small.jpg", "stream=width,height")["streams"][0]["width"] == 320
    bad = run([BASH, RECIPES / "light_grade.sh", "--preset", "lc.no-such-preset", "--out", tmp_path / "bad.jpg"], env)
    assert bad.returncode != 0 and "unknown preset" in bad.stderr and not (tmp_path / "bad.jpg").exists()
    assert run([BASH, RECIPES / "light_grade.sh", "--amount", "300", "--out", tmp_path / "x.jpg"], env).returncode == 2


# ---- what README-EDIT.md tells agents --------------------------------------------------------------------------

def _cli(home: Path, short: str) -> str:
    return str(home / "bin" / VERSIONS["apps"][short]["cli"])


def test_command_ids_named_in_recipe_headers_exist_in_the_pinned_cli(home):
    for recipe_name, short in (("film_timeline.sh", "film"), ("sound_mix.sh", "sound"), ("effect_title.sh", "effect"),
                               ("photo_thumbnail.sh", "photo"), ("vector_lower_third.sh", "vector"),
                               ("light_grade.sh", "light")):
        header = (RECIPES / recipe_name).read_text(encoding="utf-8").split("set -euo")[0]
        block = header.split("Command ids used", 1)[1]
        ids = re.findall(r"\b([a-z]+\.[A-Za-z_.]+[A-Za-z_])\b", block)
        assert ids, recipe_name
        listing = run([_cli(home, short), "commands"] + (["--json"] if short in {"photo"} else []))
        assert listing.returncode == 0
        for command_id in ids:
            assert re.search(rf'(?m)^\s*(?:"id": ")?{re.escape(command_id)}\b|"id":\s*"{re.escape(command_id)}"', listing.stdout), (recipe_name, command_id)


def test_each_cli_serves_mcp_over_stdio_at_its_pinned_version(home):
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
    messages = [init, {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
    for short, app in VERSIONS["apps"].items():
        args = [_cli(home, short), "mcp"] + (["--headless"] if short == "vector" else [])
        proc = subprocess.run(args, input="\n".join(json.dumps(m) for m in messages) + "\n", capture_output=True, text=True, timeout=60)
        replies = [json.loads(l) for l in proc.stdout.splitlines() if l.startswith("{")]
        assert replies[0]["result"]["serverInfo"]["version"] == app["version"], short
        assert len(replies[1]["result"]["tools"]) > 5, short


def test_file_confinement_flags_exist_exactly_where_the_readme_says(home):
    for short in ("sound", "effect", "photo", "vector"):
        helped = run([_cli(home, short), "mcp", "--help"])
        assert "--automation-read-root" in helped.stdout + helped.stderr and "--automation-write-root" in helped.stdout + helped.stderr, short
    film = run([_cli(home, "film"), "mcp", "--automation-read-root", str(home)], cwd=home)
    assert "unknown mcp option" in film.stdout + film.stderr
    light = run([_cli(home, "light"), "mcp", "--automation-read-root", str(home)], cwd=home)
    assert "unknown option" in light.stdout + light.stderr   # LightCraft has no confinement flags either


def test_uninstall_really_removes_the_install(tmp_path):
    """Uses a small throwaway install (sound only) so the shared home stays intact for the other tests."""
    h = tmp_path / "home"
    e = {"B2M_EDIT_HOME": str(h)}
    assert run([BASH, INSTALL, "--components", "sound"], e).returncode == 0
    (h / "keep.txt").write_text("mine")
    proc = run([BASH, INSTALL, "--uninstall"], e)
    assert proc.returncode == 0 and sorted(p.name for p in h.iterdir()) == ["keep.txt"]
    assert run([BASH, SCRIPTS / "detect_edit.sh"], e).stdout.strip() == "edit: not installed"
