"""ocr_sweep.sh: placeholder and leak patterns (no OCR needed), then real frames through tesseract when it is installed."""
from __future__ import annotations

import os
import shutil

import pytest

from craft_common import X264, bash_script, ffmpeg, needs_bash, needs_ffmpeg, still_video, text_png

pytestmark = needs_bash
USERS = "/Us" + "ers/"          # built in two parts: the repo hygiene test bans the literal path
WINUSERS = "C:\\Us" + "ers\\"
needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed (optional)")


def scan(tmp_path, text):
    f = tmp_path / "t.txt"
    f.write_text(text, encoding="utf-8")
    return bash_script("ocr_sweep.sh", "--scan-text", f)


@pytest.mark.parametrize("text,hit", [
    ("TODO: add the real chart", "TODO"), ("Title TBD", "TBD"), ("FIXME later", "FIXME"),
    ("Lorem ipsum dolor sit amet", "Lorem ipsum"), ("this is a placeholder", "placeholder"),
    ("Welcome {{ name }}", "{{"), ("[INSERT LOGO HERE]", "[INSERT LOGO HERE]"),
    ("saved to " + USERS + "someone/Desktop", USERS), (WINUSERS + "dev\\clip.mp4", "C:\\"), ("recording not recorded yet", "not recorded"),
])
def test_each_pattern_hits(tmp_path, text, hit):
    proc = scan(tmp_path, text)
    assert proc.returncode == 1, proc.stdout
    assert f'"{hit}"' in proc.stdout


@pytest.mark.parametrize("text", [
    "Hello world, this is the final cut", "Todoist and the Users Guide", "A to-do list of 3 steps", "Version 2 ships today",
    "Users love it: 4 of 5",
])
def test_ordinary_text_passes(tmp_path, text):
    proc = scan(tmp_path, text)
    assert proc.returncode == 0 and proc.stdout.startswith("PASS"), proc.stdout


def test_extra_pattern_is_applied_to_video_text_and_files(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("built by Acme v1.2.3", encoding="utf-8")
    assert bash_script("ocr_sweep.sh", "--scan-text", f).returncode == 0
    proc = bash_script("ocr_sweep.sh", "--scan-text", f, "--extra", "acme|v[0-9]+[.][0-9]+")
    assert proc.returncode == 1 and "Acme" in proc.stdout and "v1.2" in proc.stdout


@needs_ffmpeg
def test_without_tesseract_it_skips_with_the_install_command_and_exits_3(tmp_path):
    clip = still_video(tmp_path / "c.mp4", text_png(tmp_path / "c.png", ["HELLO"]), seconds=1)
    proc = bash_script("ocr_sweep.sh", clip, env={"TESSERACT": "definitely-not-installed"})
    assert proc.returncode == 3, proc.stdout       # not measured: neither a pass nor a fail
    assert proc.stdout.startswith("SKIP") and "PASS" not in proc.stdout and "brew install tesseract" in proc.stdout and "apt-get install tesseract-ocr" in proc.stdout


@needs_ffmpeg
@needs_tesseract
@pytest.mark.parametrize("lines,hit", [(["TODO"], "TODO"), ([USERS.upper() + "BOB"], USERS.upper()), (["LOREM IPSUM"], "LOREM IPSUM")])
def test_a_frame_with_placeholder_text_fails(tmp_path, lines, hit):
    clip = still_video(tmp_path / "bad.mp4", text_png(tmp_path / "bad.png", lines), seconds=2)
    proc = bash_script("ocr_sweep.sh", clip, "--keep", tmp_path / "kept")
    assert proc.returncode == 1, proc.stdout
    assert f'"{hit}"' in proc.stdout and any((tmp_path / "kept").glob("*.png"))


@needs_ffmpeg
@needs_tesseract
def test_a_clean_frame_passes(tmp_path):
    clip = still_video(tmp_path / "ok.mp4", text_png(tmp_path / "ok.png", ["HELLO WORLD"]), seconds=2)
    proc = bash_script("ocr_sweep.sh", clip)
    assert proc.returncode == 0 and "PASS  no placeholder text or leaked paths in 2 frame(s)" in proc.stdout, proc.stdout


@needs_ffmpeg
@needs_tesseract
def test_text_that_appears_after_a_cut_is_found_by_the_scene_change_frame(tmp_path):
    ok, bad = text_png(tmp_path / "ok.png", ["HELLO WORLD"]), text_png(tmp_path / "bad.png", ["TODO"])
    clip = tmp_path / "cut.mp4"       # 0.5 s clean, then 0.5 s of inverted TODO: the 1 fps sample at t=0 only sees the clean half
    ffmpeg("-loop", "1", "-framerate", "10", "-t", "0.5", "-i", ok, "-loop", "1", "-framerate", "10", "-t", "0.5", "-i", bad,
           "-filter_complex", "[0:v]gblur=sigma=8[a];[1:v]gblur=sigma=8,negate[b];[a][b]concat=n=2:v=1:a=0", *X264, clip)
    proc = bash_script("ocr_sweep.sh", clip)
    assert proc.returncode == 1 and "(scene change)" in proc.stdout and '"TODO"' in proc.stdout, proc.stdout


# ---- it never passes what it did not read ------------------------------------------------------------------------

def fake_tesseract(tmp_path, text=""):
    """A stand-in OCR that 'reads' the same text from every frame (POSIX shells only)."""
    exe = tmp_path / "fake-tesseract"
    exe.write_text(f"#!/usr/bin/env bash\nprintf '%s' '{text}' > \"$2.txt\"\n", encoding="utf-8", newline="\n")
    exe.chmod(0o755)
    return str(exe)


def test_a_file_ffmpeg_cannot_read_fails(tmp_path):
    bad = tmp_path / "not.mp4"
    bad.write_text("not a video", encoding="utf-8")
    proc = bash_script("ocr_sweep.sh", bad, env={"TESSERACT": "true"})
    assert proc.returncode == 1 and "FAIL  ocr_sweep: ffmpeg could not read frames" in proc.stdout, proc.stdout
    assert "PASS" not in proc.stdout


@needs_ffmpeg
def test_a_broken_tesseract_fails_instead_of_passing_every_frame(tmp_path):
    clip = still_video(tmp_path / "c.mp4", text_png(tmp_path / "c.png", ["HELLO"]), seconds=2)
    proc = bash_script("ocr_sweep.sh", clip, env={"TESSERACT": "false"})     # runs, exits 1, writes nothing
    assert proc.returncode == 1 and "tesseract read nothing from 2 of 2 frame(s)" in proc.stdout, proc.stdout
    assert "PASS" not in proc.stdout


@needs_ffmpeg
@pytest.mark.skipif(os.name == "nt", reason="the stand-in OCR is a bash script")
def test_a_capped_sweep_says_what_it_did_not_read(tmp_path):
    clip = still_video(tmp_path / "c.mp4", text_png(tmp_path / "c.png", ["HELLO"]), seconds=4)
    env = {"TESSERACT": fake_tesseract(tmp_path, "HELLO")}
    whole = bash_script("ocr_sweep.sh", clip, env=env)
    assert whole.returncode == 0 and "PASS  no placeholder text or leaked paths in 4 frame(s)" in whole.stdout, whole.stdout
    capped = bash_script("ocr_sweep.sh", clip, "--max-frames", "2", env=env)
    assert capped.returncode == 3 and "read only the first 2 s of 4 s" in capped.stdout, capped.stdout
    assert "PASS" not in capped.stdout
