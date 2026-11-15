"""Edit pack, fast tests: versions.json, installer arguments, detect, uninstall, recipes' guard rails, hygiene.

Nothing here downloads anything. The slow tests (test_edit_slow.py) install the pinned apps and run the recipes.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat

import pytest

from test_edit_common import (APPS, BASH, EDIT, PLATFORMS, RECIPES, REPO, SCRIPTS, SKILL, VERSIONS, make_stub_cli,
                              needs_node, posix_only, run)

INSTALL_SH = EDIT / "install_edit.sh"
INSTALL_PS1 = EDIT / "install_edit.ps1"
DETECT_SH = SCRIPTS / "detect_edit.sh"
DETECT_PS1 = SCRIPTS / "detect_edit.ps1"
RECIPE_FILES = sorted(p for p in RECIPES.glob("*.sh"))
EDIT_FILES = [p for p in EDIT.rglob("*") if p.is_file()] + [DETECT_SH, DETECT_PS1]


# ---- versions.json ---------------------------------------------------------------------------------------------

def test_versions_json_schema():
    v = VERSIONS
    assert v["schema"] == 1 and v["license"] == "Apache-2.0" and v["source"] == "https://github.com/storytold"
    assert re.fullmatch(r"[0-9A-F]{40}", v["signing"]["fingerprint"]) and v["signing"]["key_asset"] == "release-signing-key.asc"
    assert set(v["apps"]) == set(APPS)
    for short, app in v["apps"].items():
        assert app["name"] == f"{short}craft" and app["cli"] == f"{app['name']}-cli"
        assert re.fullmatch(r"\d+\.\d+\.\d+", app["version"]) and app["tag"] == "v" + app["version"]
        assert set(app["assets"]) == set(PLATFORMS), short
        for plat, asset in app["assets"].items():
            assert re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]), (short, plat)
            assert isinstance(asset["bytes"], int) and asset["bytes"] > 1_000_000
            assert app["version"] in asset["file"] and asset["file"].startswith(app["name"])


def test_asset_names_follow_each_platforms_convention():
    for app in VERSIONS["apps"].values():
        n, ver = app["name"], app["version"]
        a = app["assets"]
        assert a["macos-universal"]["file"] == f"{n}-cli-{ver}-macos-universal.zip"
        assert a["windows-x64"]["file"] == f"{n}-{ver}-windows-x64-portable.zip"
        assert a["windows-arm64"]["file"] == f"{n}-{ver}-windows-arm64-portable.zip"
        assert a["linux-x86_64"]["file"] == f"{n}-{ver}-linux-x86_64.tar.gz"
        assert a["linux-aarch64"]["file"] == f"{n}-{ver}-linux-aarch64.tar.gz"


# ---- installer arguments ---------------------------------------------------------------------------------------

@posix_only
@needs_node
@pytest.mark.parametrize("plat,suffix", [("macos-universal", "-cli-"), ("linux-x86_64", "linux-x86_64.tar.gz"),
                                          ("linux-aarch64", "linux-aarch64.tar.gz"), ("windows-x64", "windows-x64-portable.zip")])
def test_dry_run_plans_every_component_per_platform_and_changes_nothing(tmp_path, plat, suffix):
    home = tmp_path / "home"
    proc = run([BASH, INSTALL_SH, "--components", "all", "--dry-run"], {"B2M_EDIT_HOME": str(home), "B2M_EDIT_PLATFORM": plat})
    assert proc.returncode == 0, proc.stderr
    lines = [l for l in proc.stdout.splitlines() if "would download" in l]
    assert len(lines) == 5 and all(suffix in l and " MB, from https://github.com/storytold/" in l for l in lines)
    assert not home.exists()


@posix_only
@needs_node
def test_default_components_are_film_and_sound_and_spaces_work(tmp_path):
    env = {"B2M_EDIT_HOME": str(tmp_path / "h")}
    default = run([BASH, INSTALL_SH, "--dry-run"], env)
    assert [l.split(":")[0] for l in default.stdout.splitlines() if "would download" in l] == ["film", "sound"]
    spaced = run([BASH, INSTALL_SH, "--components", "photo vector", "--dry-run"], env)
    assert [l.split(":")[0] for l in spaced.stdout.splitlines() if "would download" in l] == ["photo", "vector"]


@posix_only
def test_installer_rejects_bad_arguments(tmp_path):
    env = {"B2M_EDIT_HOME": str(tmp_path / "h")}
    bad = run([BASH, INSTALL_SH, "--components", "film,bogus"], env)
    assert bad.returncode == 2 and "unknown component 'bogus'" in bad.stderr
    assert run([BASH, INSTALL_SH, "--nonsense"], env).returncode == 2
    assert run([BASH, INSTALL_SH, "--components", ""], env).returncode == 2
    assert not (tmp_path / "h").exists()
    helped = run([BASH, INSTALL_SH, "--help"], env)
    assert helped.returncode == 0 and "--uninstall" in helped.stdout and "SHA256SUMS" in helped.stdout


@posix_only
def test_installer_has_no_sudo_and_never_edits_shell_profiles():
    for installer in (INSTALL_SH, INSTALL_PS1):
        code = "\n".join(l for l in installer.read_text(encoding="utf-8").splitlines()
                         if not l.lstrip().startswith(("#", "say ", "Write-Output")))
        assert "sudo" not in code and ".bashrc" not in code and ".zshrc" not in code and "setx" not in code.lower()


# ---- detect ----------------------------------------------------------------------------------------------------

@posix_only
def test_detect_branches_on_a_cli_that_actually_runs(tmp_path):
    env = {"B2M_EDIT_HOME": str(tmp_path / "none")}
    empty = run([BASH, DETECT_SH], env)
    assert empty.returncode == 0 and empty.stdout.strip() == "edit: not installed"

    home = tmp_path / "home"
    make_stub_cli(home / "filmcraft" / "filmcraft-cli")                 # macOS layout
    make_stub_cli(home / "soundcraft" / "bin" / "soundcraft-cli")       # Linux layout
    make_stub_cli(home / "effectcraft" / "effectcraft-cli.exe")         # Windows layout
    make_stub_cli(home / "photocraft" / "photocraft-cli", exit_code=1)  # present but broken
    (home / "vectorcraft").mkdir(parents=True)
    (home / "vectorcraft" / "vectorcraft-cli").write_text("not a program")  # present, not executable
    out = run([BASH, DETECT_SH], {"B2M_EDIT_HOME": str(home)})
    assert out.returncode == 0 and out.stdout.strip() == "edit: ready (film,sound,effect)"


@posix_only
def test_detect_needs_only_the_install_folder(tmp_path):
    """Run from a copy of the script with no repository around it, with a stub install."""
    lone = tmp_path / "elsewhere" / "detect_edit.sh"
    lone.parent.mkdir()
    shutil.copy(DETECT_SH, lone)
    home = tmp_path / "home"
    make_stub_cli(home / "vectorcraft" / "vectorcraft-cli")
    out = run([BASH, lone], {"B2M_EDIT_HOME": str(home)}, cwd=tmp_path)
    assert out.stdout.strip() == "edit: ready (vector)"


# ---- uninstall -------------------------------------------------------------------------------------------------

def _fake_install(home, apps=("sound", "photo")):
    manifest = ["versions.json", "recipes", ".components"]
    (home / "recipes").mkdir(parents=True)
    (home / "recipes" / "x.sh").write_text("#!/bin/sh\n")
    (home / "versions.json").write_text("{}")
    (home / ".components").write_text("\n".join(sorted(apps)) + "\n")
    for a in apps:
        make_stub_cli(home / f"{a}craft" / f"{a}craft-cli")
        make_stub_cli(home / "bin" / f"{a}craft-cli")
        manifest += [f"{a}craft", f"bin/{a}craft-cli"]
    (home / ".b2m-edit-manifest").write_text("\n".join(manifest) + "\n")


@posix_only
@needs_node
def test_uninstall_removes_only_what_the_manifest_lists(tmp_path):
    home = tmp_path / "home"
    _fake_install(home)
    (home / "my-notes.txt").write_text("keep me")
    (home / "bin" / "my-tool").write_text("keep me too")
    proc = run([BASH, INSTALL_SH, "--uninstall"], {"B2M_EDIT_HOME": str(home)})
    assert proc.returncode == 0, proc.stderr
    assert sorted(p.name for p in home.iterdir()) == ["bin", "my-notes.txt"]
    assert [p.name for p in (home / "bin").iterdir()] == ["my-tool"]
    assert "left alone" in proc.stdout


@posix_only
@needs_node
def test_uninstall_one_component_keeps_the_rest_then_removes_shared_files(tmp_path):
    home = tmp_path / "home"
    _fake_install(home)
    env = {"B2M_EDIT_HOME": str(home)}
    assert run([BASH, INSTALL_SH, "--uninstall", "--components", "photo"], env).returncode == 0
    assert not (home / "photocraft").exists() and not (home / "bin" / "photocraft-cli").exists()
    assert (home / "soundcraft").is_dir() and (home / "recipes").is_dir()
    assert (home / ".components").read_text().split() == ["sound"]
    assert run([BASH, INSTALL_SH, "--uninstall", "--components", "sound"], env).returncode == 0
    assert not home.exists()   # nothing of ours left, and the empty folder went too


@posix_only
@needs_node
def test_uninstall_skips_unsafe_manifest_entries_and_missing_manifest(tmp_path):
    home = tmp_path / "home"
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "file").write_text("x")
    home.mkdir()
    (home / ".b2m-edit-manifest").write_text("../victim\n/etc\nsoundcraft/../../victim\n")
    proc = run([BASH, INSTALL_SH, "--uninstall"], {"B2M_EDIT_HOME": str(home)})
    assert proc.returncode == 0 and (victim / "file").exists() and proc.stdout.count("skipping unsafe") == 3
    other = run([BASH, INSTALL_SH, "--uninstall"], {"B2M_EDIT_HOME": str(tmp_path / "never-installed")})
    assert other.returncode == 0 and "nothing to remove" in other.stdout


# ---- recipes: guard rails --------------------------------------------------------------------------------------

def test_there_is_one_recipe_per_app():
    assert sorted(p.name for p in RECIPE_FILES if p.name != "_lib.sh") == [
        "effect_title.sh", "film_timeline.sh", "photo_thumbnail.sh", "sound_mix.sh", "vector_lower_third.sh"]


@posix_only
@pytest.mark.parametrize("recipe", [p for p in RECIPE_FILES if p.name != "_lib.sh"], ids=lambda p: p.name)
def test_recipe_help_and_missing_cli_message(recipe, tmp_path):
    helped = run([BASH, recipe, "--help"])
    assert helped.returncode == 0 and "--out" in helped.stdout and "Command ids used" in helped.stdout
    assert run([BASH, recipe, "--bogus"]).returncode == 2
    # A pinned CLI that is not installed is a clear error, and an older copy on the PATH is never used.
    name = {"film": "filmcraft", "sound": "soundcraft", "effect": "effectcraft", "photo": "photocraft", "vector": "vectorcraft"}[
        recipe.name.split("_")[0]]
    make_stub_cli(tmp_path / "pathbin" / f"{name}-cli")
    proc = run([BASH, recipe, "--out", str(tmp_path / "o.out")],
               {"B2M_EDIT_HOME": str(tmp_path / "empty"), "PATH": f"{tmp_path / 'pathbin'}{os.pathsep}{os.environ['PATH']}"})
    assert proc.returncode == 3 and "install_edit.sh --components" in proc.stderr and not (tmp_path / "o.out").exists()


@posix_only
@needs_node
def test_lib_json_string_escaping_and_output_picking():
    script = 'source "' + str(RECIPES / "_lib.sh") + '"; b2m_str "$1"; printf "%s\\n" "$2" | b2m_pick "$3"'
    tricky = 'He said "hi" \\ back\nline two \u00e9'
    proc = run([BASH, "-c", script, "x", tricky, '{"id":"a","result":{"items":[8,9]}}\nnoise\n{"id":"b","result":{"n":3}}',
                'L.find(x => x.id === "a").result.items'])
    first, second = proc.stdout.split("\n", 1) if "\n" in proc.stdout else (proc.stdout, "")
    assert json.loads(first) == tricky and second.strip() == "8 9"


@posix_only
def test_lib_finds_every_cli_layout(tmp_path):
    home = tmp_path / "home"
    make_stub_cli(home / "filmcraft" / "filmcraft-cli")
    make_stub_cli(home / "soundcraft" / "bin" / "soundcraft-cli")
    make_stub_cli(home / "effectcraft" / "effectcraft-cli.exe")
    for name, rel in (("filmcraft", "filmcraft/filmcraft-cli"), ("soundcraft", "soundcraft/bin/soundcraft-cli"),
                      ("effectcraft", "effectcraft/effectcraft-cli.exe")):
        proc = run([BASH, "-c", f'source "{RECIPES / "_lib.sh"}"; b2m_cli {name}'], {"B2M_EDIT_HOME": str(home)})
        assert proc.stdout == str(home / rel), proc.stderr


def test_example_brief_exists_and_needs_real_editing():
    brief = (REPO / "examples" / "07-edit-tutorial" / "BRIEF.md").read_text(encoding="utf-8")
    for word in ("two separately generated clips", "cross dissolve", "title", "ducked", "final.mp4"):
        assert word in brief.lower() or word in brief, word


# ---- script hygiene --------------------------------------------------------------------------------------------

def test_scripts_are_lf_utf8_and_executable_where_needed():
    for path in EDIT_FILES:
        if path.suffix in {".sh", ".ps1", ".json", ".md"}:
            data = path.read_bytes()
            data.decode("utf-8")
            if path.suffix != ".ps1":   # .gitattributes checks .ps1 out as CRLF on purpose; the others stay LF
                assert b"\r" not in data, f"{path.name} has CRLF line endings"
            if path.suffix == ".ps1":
                data.decode("ascii")    # Windows PowerShell 5.1 reads BOM-less files as ANSI: keep them pure ASCII
    for path in RECIPE_FILES + [INSTALL_SH, DETECT_SH]:
        assert path.stat().st_mode & stat.S_IXUSR, f"{path.name} is not executable"
        assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")


def test_powershell_scripts_follow_the_known_pitfalls():
    text = INSTALL_PS1.read_text(encoding="utf-8")
    assert "[string[]]$Components" in text and '-split "[,\\s]+"' in text          # both -Components forms
    assert "2>$null" not in text and "2>&1" not in text                              # no native stderr redirects
    assert "UTF8Encoding" in text and "Set-Content" not in text and "Out-File" not in text   # explicit UTF-8 only
    assert "-Uninstall" in text and ".b2m-edit-manifest" in text and "-DryRun" in text
    assert "2>$null" not in DETECT_PS1.read_text(encoding="utf-8")


def test_powershell_parses_and_dry_runs_when_pwsh_is_available(tmp_path):
    pwsh = os.environ.get("B2M_PWSH") or shutil.which("pwsh")
    if not pwsh:
        pytest.skip("no PowerShell available (set B2M_PWSH to a pwsh binary to run this)")
    for script in (INSTALL_PS1, DETECT_PS1):
        parse = run([pwsh, "-NoProfile", "-Command",
                     f"$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('{script}',[ref]$t,[ref]$e);if($e){{$e|%{{$_.Message}};exit 1}}"])
        assert parse.returncode == 0, parse.stdout + parse.stderr
    env = {"B2M_EDIT_HOME": str(tmp_path / "h"), "B2M_EDIT_PLATFORM": "windows-x64"}
    for args in (["-File", INSTALL_PS1, "-Components", "film,sound", "-DryRun"],
                 ["-Command", f"& '{INSTALL_PS1}' -Components film,vector -DryRun"]):
        proc = run([pwsh, "-NoProfile", *args], env)
        assert proc.returncode == 0 and proc.stdout.count("would download") == 2 and "windows-x64-portable.zip" in proc.stdout, proc.stdout + proc.stderr
    assert not (tmp_path / "h").exists()
    bad = run([pwsh, "-NoProfile", "-File", INSTALL_PS1, "-Components", "bogus", "-DryRun"], env)
    assert bad.returncode != 0 and "unknown component" in (bad.stdout + bad.stderr)


def test_recipes_make_no_network_calls_and_stay_small():
    for path in RECIPE_FILES:
        code = "\n".join(l for l in path.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
        assert not re.search(r"\b(curl|wget|Invoke-WebRequest)\b", code), path.name
        assert len(path.read_text(encoding="utf-8").splitlines()) < 200


def test_edit_pack_public_repo_hygiene():
    """No personal paths, private names or credentials in anything the edit pack ships."""
    banned = ["/Us" + "ers/", "C:\\Us" + "ers\\", "api_" + "key", "sec" + "ret", "/private/" + "tmp"]
    banned += [t for t in os.environ.get("B2M_BANNED", "").split(",") if t]
    hits = []
    for path in EDIT_FILES + [REPO / "examples" / "07-edit-tutorial" / "BRIEF.md"]:
        text = path.read_text(encoding="utf-8")
        hits += [f"{path.relative_to(REPO)}: {b}" for b in banned if b.lower() in text.lower()]
        assert len(text.splitlines()) < 800, path.name
    assert not hits, hits


def test_readme_matches_the_pins():
    text = (EDIT / "README-EDIT.md").read_text(encoding="utf-8")
    for app in VERSIONS["apps"].values():
        assert app["name"] in text.lower() or app["name"].capitalize() in text
        assert app["version"] in text, f"README-EDIT.md does not mention {app['name']} {app['version']}"
    for recipe in ("film_timeline.sh", "sound_mix.sh", "effect_title.sh", "photo_thumbnail.sh", "vector_lower_third.sh"):
        assert recipe in text
    for must in ("storytold", "Apache-2.0", "alpha", "finish.sh", "check_delivery.sh", "B2M_EDIT_HOME", "--uninstall",
                 "untested", "automation-read-root"):
        assert must.lower() in text.lower(), must
