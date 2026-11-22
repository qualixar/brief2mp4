"""Film mode docs and files: present, linked from SKILL.md, public-safe, small, runnable with --help, credits with licences."""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

import film_common as fc
from craft_common import REFS, SCRIPTS, SKILL

FILM_PY = ["film.py", "film_lib.py", "film_script.py", "film_story.py", "film_storyboard.py", "film_assets.py", "film_voice.py", "film_captions.py", "film_build.py",
           "film_render.py", "film_check.py", "film_report.py"]
NEW_PY = ["fetch_archive.py", "make_map.py", "map_projection.py", "build_map_data.py", "sfx_synth.py", "split_takes.py", "retime.py", "mix.py"]
CLI = ["film.py", "fetch_archive.py", "make_map.py", "build_map_data.py", "sfx_synth.py", "split_takes.py", "retime.py", "mix.py"]
FILES = ([SCRIPTS / n for n in FILM_PY + NEW_PY] + [fc.TEMPLATES / n for n in ("index.html", "film.css", "film.js", "README.md")]
         + [SKILL / "data" / "NATURAL-EARTH.md", REFS / "formats.md"])
SKILL_TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
# No home-folder paths and no "inspired by" credit. Maintainers add their private terms (names, channels) locally without committing
# them, as the other hygiene tests do: B2M_BANNED="a,b,c"
BANNED = ["ideas from", "inspired by"] + [t.strip().lower() for t in os.environ.get("B2M_BANNED", "").split(",") if t.strip()]
HOME_PATH = re.compile(r"(/us" r"ers/|/home/|[a-z]:\\us" r"ers\\)[a-z0-9]")     # a real home folder, not a pattern that hunts for one


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_files_are_public_safe(path):
    text = path.read_text(encoding="utf-8").lower().replace("github.com/qualixar/brief2mp4", "")
    for word in BANNED:
        assert word not in text, f"{path.name} mentions '{word}'"
    assert not HOME_PATH.search(text), f"{path.name} names a home folder"


@pytest.mark.parametrize("path", [SCRIPTS / n for n in FILM_PY + NEW_PY] + [fc.TEMPLATES / n for n in ("index.html", "film.css", "film.js", "README.md")], ids=lambda p: p.name)
def test_new_files_stay_under_400_lines_and_use_lf(path):
    raw = path.read_bytes()
    assert b"\r\n" not in raw and len(raw.splitlines()) <= 400


def test_formats_page_is_under_800_lines_and_the_film_section_has_its_beat_sheet_and_stage_list():
    text = (REFS / "formats.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 800
    section = text[text.index("## Explainer and documentary (film mode)"):text.index("## Maths and algorithms")]
    for part in ("Hook", "Setup", "Beat 1", "Beat 2", "Beat 3", "Turn", "Payoff"):
        assert f"| {part} |" in section
    for stage in ("story", "script", "storyboard", "assets", "voice", "retime", "build", "captions", "mix", "render", "check", "report"):
        assert f"| `{stage}` |" in section, stage
    for needle in ("archive desk", "UNVERIFIED", "never time-stretch", "CC BY-NC", "ShareAlike", "velocity", "four text blocks"):
        assert needle.lower() in section.lower(), needle
    assert "film mode" in text.split("## Choosing when the brief is vague")[1].lower()


def test_skill_md_has_a_short_film_mode_section_that_points_at_the_page():
    section = SKILL_TEXT[SKILL_TEXT.index("### Film mode"):SKILL_TEXT.index("For briefs that mix tools")]
    assert "references/formats.md" in section and "scripts/film.py" in section and len(section.split()) < 330


@pytest.mark.parametrize("name", FILM_PY + NEW_PY + ["data/", "templates/film/"])
def test_skill_md_points_at_every_new_file(name):
    assert name in SKILL_TEXT, f"SKILL.md never mentions {name}"


def test_every_reference_link_in_skill_md_still_resolves():
    for rel in re.findall(r"`(references/[A-Za-z0-9_./-]+\.md)`", SKILL_TEXT):
        assert (SKILL / rel).is_file(), rel


@pytest.mark.parametrize("name", CLI)
def test_scripts_print_help(name):
    proc = subprocess.run([sys.executable, str(SCRIPTS / name), "--help"], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0 and "usage" in proc.stdout.lower()


def test_tools_film_mode_calls_are_credited_with_licences_and_links():
    eco = (REFS / "ecosystem.md").read_text(encoding="utf-8")
    for tool, lic in [("Natural Earth", "Public domain"), ("Wikimedia Commons", "public domain, CC0 and CC BY"), ("whisper.cpp", "MIT"), ("Openverse", "MIT"),
                      ("F5-TTS", "CC BY-NC"), ("Audiocraft", "CC BY-NC 4.0")]:
        row = next((l for l in eco.splitlines() if tool in l and l.startswith("|")), None)
        assert row and lic in row and "https://" in row, tool



def test_map_data_note_says_why_it_ships_and_where_it_came_from():
    note = (SKILL / "data" / "NATURAL-EARTH.md").read_text(encoding="utf-8")
    assert "public domain" in note.lower() and "6866c877" in note and "offline" in note.lower()


def test_templates_readme_lists_the_layout_and_the_markup_contract():
    readme = (fc.TEMPLATES / "README.md").read_text(encoding="utf-8")
    for needle in ("data-t0", "data-dip-in", "window.__timelines", "four text blocks", "SIL OFL"):
        assert needle in readme, needle


def test_changelog_has_an_unreleased_film_mode_entry():
    text = (fc.REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in text and "Film mode" in text.split("## [0.7.0]")[0]
