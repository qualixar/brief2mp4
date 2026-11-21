"""The craft references and scripts: present, linked from SKILL.md, public-safe, sane in size, runnable with --help."""
from __future__ import annotations

import re
import subprocess
import sys

import pytest

from craft_common import BASH, REFS, SCRIPTS, SKILL, needs_bash

NEW_REFS = ["motion-doctrine.md", "render-traps.md", "review-checklist.md", "sound.md"]
NEW_PY = ["check_seams.py", "check_clutter.py", "beat_grid.py", "fetch_music.py"]
NEW_SH = ["ocr_sweep.sh", "cut_points.sh"]
NEW_FILES = [REFS / n for n in NEW_REFS] + [SCRIPTS / n for n in NEW_PY + NEW_SH + ["dom_boxes.js"]]
SKILL_TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")

# Nothing personal, no private paths or channels, and no "ideas from" credits: only tools that are called or installed get credit.
BANNED = ["varun", "qualixar", "diary", "my channel", "subscribers", "/us" + "ers/v", "ideas from", "inspired by", "reanimate", "lottiefiles"]


@pytest.mark.parametrize("path", NEW_FILES, ids=lambda p: p.name)
def test_new_files_are_public_safe(path):
    text = path.read_text(encoding="utf-8").lower().replace("github.com/qualixar/brief2mp4", "")   # the repo's own address is fine
    for word in BANNED:
        assert word not in text, f"{path.name} mentions '{word}'"


@pytest.mark.parametrize("path", NEW_FILES, ids=lambda p: p.name)
def test_new_files_stay_under_400_lines_and_use_lf(path):
    raw = path.read_bytes()
    assert b"\r\n" not in raw
    assert len(raw.splitlines()) <= 400


@pytest.mark.parametrize("name", NEW_REFS + [f"scripts/{n}" for n in NEW_PY + NEW_SH + ["dom_boxes.js"]])
def test_skill_md_points_at_every_new_file(name):
    assert name.split("/")[-1] in SKILL_TEXT, f"SKILL.md never mentions {name}"


def test_every_reference_link_in_skill_md_resolves():
    for rel in re.findall(r"`(references/[A-Za-z0-9_./-]+\.md)`", SKILL_TEXT):
        assert (SKILL / rel).is_file(), rel


def test_the_old_one_render_at_a_time_advice_is_gone_and_replaced_by_measured_advice():
    assert "Run one heavy render at a time" not in SKILL_TEXT
    for needle in ("--workers 8", "acts", "stream copy", "--resume", "one continuous music bed"):
        assert needle in SKILL_TEXT, needle


def test_every_new_reference_ends_up_in_the_doctrine_numbers():
    doctrine = (REFS / "motion-doctrine.md").read_text(encoding="utf-8")
    for needle in ("power3", "0.4 s", "0.25 s", "about 10 px", "18-20 px", "every 1.5-3 s", "build, breathe, resolve"):
        assert needle in doctrine.lower(), needle
    traps = (REFS / "render-traps.md").read_text(encoding="utf-8")
    for needle in ("immediateRender", "whole frames", "getTotalLength", "about 24 per composition", "device pixel ratio", "glob"):
        assert needle.lower() in traps.lower(), needle


def test_optional_tools_are_credited_with_licences_in_the_ecosystem_page():
    eco = (REFS / "ecosystem.md").read_text(encoding="utf-8")
    for tool, lic in [("librosa", "ISC"), ("PySceneDetect", "BSD-3-Clause"), ("Tesseract", "Apache-2.0"), ("Openverse", "MIT"),
                      ("Audiocraft", "CC BY-NC 4.0"), ("F5-TTS", "CC BY-NC"), ("Demucs", "MIT")]:
        row = next((l for l in eco.splitlines() if tool in l and l.startswith("|")), None)
        assert row and lic in row and "github.com" in row, tool


@pytest.mark.parametrize("name", NEW_PY)
def test_python_scripts_print_help(name):
    proc = subprocess.run([sys.executable, str(SCRIPTS / name), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0 and "usage" in proc.stdout.lower()


@needs_bash
@pytest.mark.parametrize("name", NEW_SH + ["check_delivery.sh"])
def test_shell_scripts_parse(name):
    assert subprocess.run([BASH, "-n", str(SCRIPTS / name)], capture_output=True).returncode == 0
