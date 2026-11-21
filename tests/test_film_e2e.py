"""Film mode end to end: a 20 s brief, the stand-in voice, no network. The fast test runs every stage up to the mix and the page;
the slow test renders through HyperFrames (skipped when npx or the vendored libraries are not available) and runs the checks."""
from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import sys

import pytest

import film_common as fc
import film
import film_build
import film_captions
from film_lib import load_json

BRIEF = """# How undersea cables carry the internet

Make a 20-second explainer on how undersea cables carry the internet, documentary look, stand-in voice for the draft.

audience: people who use the internet every day
takeaway: nearly all intercontinental data travels under the sea
"""

SCRIPT = """# Script
pace: 150
format: documentary

## L01
say: Nearly all intercontinental data swims.
screen: UNDER THE SEA
source: https://example.org/cables
asset: assets/archive/ship.png
date: MARCH 1931

## L02
say: One cable runs from Alexandria to Aswan.
screen: ALEXANDRIA TO ASWAN
source: https://example.org/egypt
visual: map
region: Egypt
point: Alexandria=31.20,29.92
point: Aswan=24.09,32.90
route: Alexandria>Aswan

## L03
say: About one point four million kilometres lie on the seabed.
screen: ON THE SEABED
source: https://example.org/length
count: 0 -> 1400000 | km of cable
asset: assets/archive/ship2.png

## L04
say: That is how the internet crosses an ocean.
screen: HOW IT CROSSES
source: https://example.org/summary
"""


def project(tmp_path, script=SCRIPT):
    root = tmp_path / "film"
    (root / "assets" / "archive").mkdir(parents=True)
    for name, color in (("ship.png", "0x3b4a5a"), ("ship2.png", "0x5a4a3b")):
        fc.ffmpeg("-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:d=1", "-vf", "noise=alls=30:allf=t+u,drawgrid=w=160:h=160:t=2:c=white@0.15", "-frames:v", "1", root / "assets" / "archive" / name)
    (root / "BRIEF.md").write_text(BRIEF, encoding="utf-8")
    (root / "SCRIPT.md").write_text(script, encoding="utf-8")
    return root


def run(root, *args):
    return film.main(["run", "--project", str(root), "--voice", "standin", "--no-fetch", "--acts", "2", *args])


@pytest.fixture
def offline(monkeypatch):
    """No network at all, and a stand-in for the vendoring step (the real one needs npm and its cache)."""
    def no_net(*a, **k):
        raise AssertionError("film mode touched the network")
    monkeypatch.setattr(socket.socket, "connect", no_net)

    def stub_vendor(out_dir):
        (out_dir / "vendor" / "fonts").mkdir(parents=True, exist_ok=True)
        (out_dir / "vendor" / "gsap.min.js").write_text("/* stub */", encoding="utf-8")
        (out_dir / "vendor" / "fonts" / "fonts.css").write_text("", encoding="utf-8")
    monkeypatch.setattr(film_build, "vendor", stub_vendor)
    monkeypatch.setattr(film, "lint_projects", lambda p, jobs: "skipped in the fast test")


def test_every_stage_up_to_the_mix_runs_offline_and_writes_its_file(tmp_path, offline, capsys):
    root = project(tmp_path)
    assert run(root, "--to", "mix") == 0, capsys.readouterr().out
    out = capsys.readouterr().out
    for stage in film.STAGES[:film.STAGES.index("mix") + 1]:
        assert f"== {stage}" in out
    for name in ("STORY.md", "STORYBOARD.json", "ASSETS.json", "TIMINGS.json", "BUILD.json", "final.srt", "captions.json"):
        assert (root / name).is_file(), name
    assert (root / "audio" / "mix.wav").is_file() and (root / "project_acts" / "A1" / "index.html").is_file() and (root / "project_acts" / "A2" / "index.html").is_file()
    sb = load_json(root / "STORYBOARD.json")
    assert sb["retimed"] and 17.0 <= sb["duration"] <= 23.0 and len(sb["acts"]) == 2 and sb["beats"][0]["line_starts"]["L01"] == pytest.approx(0.3, abs=0.01)
    story = (root / "STORY.md").read_text(encoding="utf-8")
    assert "takeaway: nearly all intercontinental" in story and "0-5 s" in story
    mix = load_json(root / "audio" / "mix_report.json")
    assert mix["lufs"] == pytest.approx(-14, abs=1.0) and mix["true_peak"] <= -1.0
    cues = film_captions.parse_srt((root / "final.srt").read_text(encoding="utf-8"))
    assert " ".join(c["text"] for c in cues).split() == " ".join(re.findall(r"^say: (.+)$", SCRIPT, re.M)).split()


def test_assets_are_all_licence_recorded_and_the_map_and_sound_are_synthesised_here(tmp_path, offline):
    root = project(tmp_path)
    assert run(root, "--to", "assets") == 0
    assets = load_json(root / "ASSETS.json")["assets"]
    assert {a["kind"] for a in assets} == {"archive", "map", "sfx"} and all(a["licence"] and a["sha256"] for a in assets)
    assert (root / "assets" / "maps" / "B02.svg").is_file() and (root / "assets" / "sfx" / "sfx.json").is_file()


def test_stages_can_be_skipped_and_run_again_alone(tmp_path, offline, capsys):
    root = project(tmp_path)
    assert run(root, "--to", "retime") == 0
    first = (root / "STORYBOARD.json").read_bytes()
    capsys.readouterr()
    assert film.main(["retime", "--project", str(root)]) == 0
    assert (root / "STORYBOARD.json").read_bytes() == first                                   # re-running a stage is safe and gives the same file
    assert run(root, "--from", "retime", "--to", "build", "--skip", "voice") == 0
    out = capsys.readouterr().out
    assert "== retime" in out and "== build" in out and "== voice" not in out and "== story" not in out


def test_an_edited_story_survives_a_second_run(tmp_path, offline):
    root = project(tmp_path)
    assert run(root, "--to", "story") == 0
    (root / "STORY.md").write_text("my own story\nvoice: standin\nlength: 20 s\n", encoding="utf-8")
    assert run(root, "--to", "script") == 0
    assert (root / "STORY.md").read_text(encoding="utf-8").startswith("my own story")


def test_render_refuses_an_unverified_line_and_the_report_lists_it(tmp_path, offline, capsys):
    root = project(tmp_path, SCRIPT.replace("source: https://example.org/length\n", ""))
    assert run(root, "--to", "mix") == 0
    capsys.readouterr()
    assert film.main(["render", "--project", str(root), "--quality", "draft"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("FAIL") and "L03" in out and "--allow-unverified" in out
    assert film.main(["report", "--project", str(root)]) == 0
    report = (root / "REPORT.md").read_text(encoding="utf-8")
    assert "## Unverified lines" in report and "- L03:" in report and "## Credits and licences" in report and "Natural Earth" in report


def test_missing_script_and_other_mistakes_give_one_fail_line(tmp_path, offline, capsys):
    root = tmp_path / "empty"
    root.mkdir()
    (root / "BRIEF.md").write_text(BRIEF, encoding="utf-8")
    assert film.main(["run", "--project", str(root), "--to", "script"]) == 1
    out = capsys.readouterr().out
    assert out.count("FAIL") == 1 and "SCRIPT.md not found" in out
    assert film.main(["run", "--project", str(root), "--skip", "bogus"]) == 1 and "bogus" in capsys.readouterr().out


def test_voice_take_needs_the_take(tmp_path, offline, capsys):
    root = project(tmp_path)
    assert film.main(["voice", "--project", str(root), "--voice", "take"]) == 1
    assert "--take" in capsys.readouterr().out


def test_list_and_help_work_without_a_project(capsys):
    assert film.main(["--list"]) == 0 and capsys.readouterr().out.split() == film.STAGES
    proc = fc.py_script("film.py", "--help")
    assert proc.returncode == 0 and "usage" in proc.stdout.lower()


# ---- the real render ---------------------------------------------------------------------------------------------------

@pytest.mark.slow
def test_a_20_second_film_renders_through_hyperframes_and_passes_the_delivery_checks(tmp_path):
    if shutil.which("npx") is None or shutil.which("ffmpeg") is None:
        pytest.skip("npx or ffmpeg not found: the film stops at the composition (see the fast test)")
    root = project(tmp_path)
    proc = subprocess.run([sys.executable, str(fc.SCRIPTS / "film.py"), "run", "--project", str(root), "--voice", "standin", "--no-fetch", "--acts", "2",
                           "--quality", "draft", "--skip", "check,report"], capture_output=True, text=True, encoding="utf-8")
    if "vendoring GSAP and the fonts failed" in proc.stdout:
        pytest.skip("npm and its cache are not available to vendor GSAP and the fonts once")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    final = root / "final.mp4"
    info = fc.ffprobe(final)
    sb = load_json(root / "STORYBOARD.json")
    assert (info["width"], info["height"]) == (1920, 1080) and info["duration"] == pytest.approx(sb["duration"], abs=1 / 30 + 0.01)
    check = fc.bash_script("check_delivery.sh", final, "--seconds", f"{sb['duration']:.4f}", "--joins", f"{sb['acts'][1]['start']:.4f}")
    assert "RESULT: PASS" in check.stdout, check.stdout
    assert film.main(["check", "--project", str(root)]) == 0
    assert film.main(["report", "--project", str(root)]) == 0
    assert "## Checks" in (root / "REPORT.md").read_text(encoding="utf-8")
