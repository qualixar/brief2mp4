"""The 3D pack upgrade's files: present, public-safe, small, linked from SKILL.md, with the licence notes in place."""
from __future__ import annotations

import re

import pytest

from conftest import PACK, SKILL

REFS = SKILL / "references"
RECIPES = PACK / "templates" / "recipes"
DOCS = [REFS / "blender-live.md", REFS / "blender-recipes.md", REFS / "generators-3d.md"]
CODE = sorted(RECIPES.glob("*.py")) + [SKILL / "scripts" / "gen3d.py", PACK / "b2m3d" / "recipes.py"]
ALL = DOCS + CODE
# Nothing personal, no private paths, and no "ideas from" credits: only tools that are called or installed get credit.
BANNED = ["varun", "qualixar", "diary", "my channel", "subscribers", "/us" + "ers/", "ideas from", "inspired by", "c:\\us" + "ers"]
SKILL_TEXT = (SKILL / "SKILL.md").read_text(encoding="utf-8")
ECO = (REFS / "ecosystem.md").read_text(encoding="utf-8")
GEN = (REFS / "generators-3d.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ALL, ids=lambda p: p.name)
def test_public_safe_small_and_lf(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8").lower().replace("github.com/qualixar/brief2mp4", "")
    assert b"\r\n" not in raw and len(raw.splitlines()) <= 400
    for word in BANNED:
        assert word not in text, f"{path.name} mentions {word!r}"


@pytest.mark.parametrize("name", [d.name for d in DOCS] + ["gen3d.py"])
def test_skill_md_points_at_every_new_file(name):
    assert name in SKILL_TEXT


def test_every_recipe_is_documented_and_has_a_docstring_and_a_test():
    recipes_doc = (REFS / "blender-recipes.md").read_text(encoding="utf-8")
    for path in sorted(RECIPES.glob("b2m_*.py")):
        name = path.stem.removeprefix("b2m_")
        if name in ("common", "math"):     # shared helpers, not recipes
            continue
        assert path.read_text(encoding="utf-8").lstrip().startswith('"""'), path.name
        assert f"`{name}`" in recipes_doc or name in GEN, f"{name} is not documented"
        assert (PACK.parent.parent.parent.parent / "tests" / f"test_blender_{name.split('_')[0]}.py").exists() or name == "flip_bake"


def test_the_licence_notes_are_in_the_ecosystem_credits():
    for needle in ("blender-mcp", "MIT", "Hunyuan3D-2", "European Union, United Kingdom and South Korea", "TRELLIS",
                   "diffoctreerast", "FLIP Fluids", "GPL", "Superhive", "never bundles", "DISABLE_TELEMETRY",
                   "Acceptable Use Policy", "machine-generated", "release date"):
        assert needle in ECO, needle
    trellis_row = next(line for line in ECO.splitlines() if line.startswith("| [TRELLIS]"))
    assert "non-commercial" in trellis_row and "nvdiffrast" in trellis_row and "--non-commercial" in trellis_row


def test_every_trellis_line_says_the_glb_export_is_non_commercial():
    readme3d = (PACK / "README-3D.md").read_text(encoding="utf-8")
    section = (PACK.parents[3] / "README.md").read_text(encoding="utf-8")
    for text in (GEN, readme3d, section):
        lines = [ln for ln in text.splitlines() if "TRELLIS" in ln and "MIT" in ln and (ln.startswith("|") or "[TRELLIS]" in ln)]
        assert lines and all("non-commercial" in ln.lower() for ln in lines), lines
    for quote in ('"non-commercially" means "for research or evaluation purposes only and not for any direct or indirect '
                  'monetary gain"', 'may be used "non-commercially", i.e., for research and/or evaluation purposes only.'):
        assert quote in GEN, quote


def test_the_hunyuan_note_carries_the_acceptable_use_policy_and_the_readme_as_it_is():
    assert "machine generated" in GEN and "For military purposes" in GEN and "release date" in GEN
    assert "supports Macos, Windows, Linux" in GEN and "CUDA GPU" not in GEN and "custom_rasterizer" in GEN


def test_the_live_doc_states_safe_mode_telemetry_and_auto_start_as_they_are():
    live = (REFS / "blender-live.md").read_text(encoding="utf-8")
    assert "safe mode is a good default" not in live and "It also refuses the recipes" in live
    assert "opt-in and off by default" not in live and "DISABLE_TELEMETRY=true" in live
    assert "-e DISABLE_TELEMETRY=true -- uvx" in live and "--env DISABLE_TELEMETRY=true -- uvx" in live
    assert "Auto-Start Server" in live and "clear=True" in live and "never pass it in a live session" in live


def test_the_hunyuan_licence_text_is_quoted_exactly():
    for quote in ("THIS LICENSE AGREEMENT DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA",
                  '"Territory" shall mean the worldwide territory, excluding the territory of the European Union, United Kingdom and South Korea.',
                  "TRELLIS models and the majority of the code are licensed under the MIT License. The following submodules may have different licenses:",
                  "The Blender addon code is licensed under the GPL."):
        assert quote in GEN, quote


def test_headless_is_stated_as_the_default_next_to_the_live_route():
    live = (REFS / "blender-live.md").read_text(encoding="utf-8")
    assert "decide live, render headless" in live.lower()
    assert "Headless stays the route" in (PACK / "README-3D.md").read_text(encoding="utf-8")


def test_no_vendored_third_party_code_or_weights():
    names = {p.name for p in RECIPES.iterdir()}
    assert all(n.startswith("b2m_") for n in names if n.endswith(".py")), names
    assert not [p for p in PACK.rglob("*") if p.suffix in (".safetensors", ".ckpt", ".pth", ".bin")]


def test_links_in_the_new_docs_point_at_real_files():
    for doc in DOCS:
        for rel in re.findall(r"`(references/[A-Za-z0-9_./-]+\.md)`", doc.read_text(encoding="utf-8")):
            assert (SKILL / rel).is_file(), f"{doc.name} -> {rel}"
