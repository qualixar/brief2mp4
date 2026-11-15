"""CLI, doctor, detect_3d, installer arguments, Blender lookup, encoder choice, public-repo hygiene."""
import json
import os
import subprocess
import sys

import pytest

from conftest import EXAMPLE, PACK, REPO, SKILL, cli, needs_core

BASH = None if os.name == "nt" else "bash"
posix_only = pytest.mark.skipif(BASH is None, reason="bash scripts")


def test_doctor_reports_components_as_json():
    proc = cli("doctor")
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert set(report["components"]) == {"core", "cad", "blender"}
    for comp in report["components"].values():
        assert "ok" in comp and "install" in comp
    assert "install_3d" in report["components"]["core"]["install"]


def test_doctor_on_empty_home_lists_what_is_missing(tmp_path):
    home = tmp_path / "empty"
    home.mkdir()
    proc = cli("doctor", home=home)
    report = json.loads(proc.stdout)
    assert proc.returncode == 0 and report["ok"] is False
    core = report["components"]["core"]
    assert core["ok"] is False and any(m.startswith("npm:three") for m in core["missing"])
    assert "--components core" in core["install"] or "-Components core" in core["install"]


@needs_core
def test_doctor_ok_when_core_installed():
    report = json.loads(cli("doctor").stdout)
    assert report["ok"] is True and report["components"]["core"]["missing"] == []


@needs_core
def test_material_presets_command_lists_sixteen():
    out = json.loads(cli("material", "presets").stdout)
    assert len(out["presets"]) == 16 and "gold" in out["presets"]


def test_errors_are_one_json_line_on_stderr(tmp_path):
    proc = cli("hf", str(tmp_path / "missing.json"), str(tmp_path / "out"), home=tmp_path)
    assert proc.returncode == 1
    assert json.loads(proc.stderr)["ok"] is False


@posix_only
def test_detect_3d_branches_on_installed_state(tmp_path):
    script = SKILL / "scripts" / "detect_3d.sh"
    empty = subprocess.run([BASH, str(script)], capture_output=True, text=True,
                           env={**os.environ, "B2M3D_HOME": str(tmp_path / "none")})
    assert empty.returncode == 0 and empty.stdout.strip() == "3d: not installed"
    home = tmp_path / "fake"
    (home / "venv" / "bin").mkdir(parents=True)
    (home / "venv" / "bin" / "python").write_text("#!/bin/sh\n")
    (home / "venv" / "bin" / "python").chmod(0o755)
    (home / "node_modules" / "three").mkdir(parents=True)
    (home / "node_modules" / "jolt-physics").mkdir()
    ready = subprocess.run([BASH, str(script)], capture_output=True, text=True,
                           env={**os.environ, "B2M3D_HOME": str(home), "B2M3D_BLENDER": ""})
    assert ready.returncode == 0 and ready.stdout.startswith("3d: ready (components: core")


@posix_only
def test_installer_rejects_unknown_component_and_never_uses_sudo(tmp_path):
    script = PACK / "install_3d.sh"
    proc = subprocess.run([BASH, str(script), "--components", "bogus"], capture_output=True, text=True,
                          env={**os.environ, "B2M3D_HOME": str(tmp_path / "h")})
    assert proc.returncode == 2 and "unknown component" in proc.stderr
    for installer in (script, PACK / "install_3d.ps1"):
        code = "\n".join(l for l in installer.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith(("#", "say ", "Write-Output")))
        assert "sudo" not in code


def test_pins_exist_for_every_component():
    for name in ("requirements-core.txt", "requirements-cad.txt", "requirements-dev.txt"):
        lines = [l for l in (PACK / name).read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
        assert lines and all("==" in l for l in lines), name
    deps = json.loads((PACK / "package.json").read_text(encoding="utf-8"))["dependencies"]
    assert deps and all(v[0].isdigit() for v in deps.values()), "node versions must be exact"
    assert (PACK / "package-lock.json").exists()


def test_blender_lookup_prefers_override_then_picks_newest_windows_install(tmp_path, monkeypatch):
    from b2m3d import paths
    fake = tmp_path / "my-blender"
    fake.write_text("")
    monkeypatch.setenv("B2M3D_BLENDER", str(fake))
    assert paths.blender() == str(fake)
    monkeypatch.delenv("B2M3D_BLENDER")
    monkeypatch.setenv("PATH", str(tmp_path))
    ordered = sorted(["C:/P/Blender Foundation/Blender 4.2/blender.exe", "C:/P/Blender Foundation/Blender 5.1/blender.exe",
                      "C:/P/Blender Foundation/Blender 4.10/blender.exe"], key=paths._version_key, reverse=True)
    assert ordered[0].endswith("Blender 5.1/blender.exe") and ordered[1].endswith("4.10/blender.exe")


def test_encoder_choice_per_platform():
    from b2m3d.encode import pick_encoder
    yes, no = (lambda n: True), (lambda n: False)
    assert pick_encoder(True, "darwin", yes)[0] == "prores_ks"
    assert "4444" in pick_encoder(True, "linux", yes)[1]
    assert pick_encoder(False, "darwin", yes)[0] == "hevc_videotoolbox"
    assert pick_encoder(False, "darwin", no)[0] == "libx264"
    assert pick_encoder(False, "win32", yes)[0] == "libx264"
    assert pick_encoder(False, "linux", yes)[0] == "libx264"


def test_blender_script_gpu_order_covers_every_platform():
    text = (PACK / "templates" / "blender_shot.py").read_text(encoding="utf-8")
    assert '["METAL"] if sys.platform == "darwin"' in text
    for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
        assert backend in text
    assert 'scene.cycles.device = "CPU"' in text


def test_public_repo_hygiene():
    """No personal paths, private names or secrets in anything the pack ships."""
    banned = ["/Us" + "ers/", "C:\\Us" + "ers\\", "api_key", "secret"]
    # Maintainers can add private terms locally without committing them: B2M_BANNED="a,b,c"
    banned += [t for t in os.environ.get("B2M_BANNED", "").split(",") if t]
    files = [p for root in (PACK, REPO / "examples" / "04-3d-product", SKILL / "scripts") for p in root.rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc"} and p.name != "package-lock.json"  # integrity hashes can contain any letters

             and (root != SKILL / "scripts" or p.name.startswith("detect_3d"))]
    files += [p for p in (REPO / "tests").rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != "test_cli_detect.py"]
    hits = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits += [f"{path.relative_to(REPO)}: {b}" for b in banned if b.lower() in text.lower()]
    assert not hits, hits
    assert max(len(p.read_text(encoding="utf-8").splitlines()) for p in files if p.suffix in {".py", ".js", ".mjs", ".sh", ".md"}) < 800


@posix_only
def test_3d_installer_never_adopts_or_deletes_a_users_folder(tmp_path):
    """An existing folder with the user's files must be refused at install and left alone at uninstall."""
    folder = tmp_path / "myproj"
    folder.mkdir()
    (folder / "thesis.txt").write_text("precious", encoding="utf-8")
    env = {**os.environ, "B2M3D_HOME": str(folder)}
    installer = str(PACK / "install_3d.sh")
    inst = subprocess.run([BASH, installer, "--components", "core"], env=env, capture_output=True, text=True)
    assert inst.returncode != 0 and "not created by this installer" in inst.stderr
    assert not (folder / ".installed-by-brief2mp4-3d").exists()
    unin = subprocess.run([BASH, installer, "--uninstall"], env=env, capture_output=True, text=True)
    assert unin.returncode != 0
    assert (folder / "thesis.txt").read_text(encoding="utf-8") == "precious"


@posix_only
def test_3d_uninstall_keeps_files_it_did_not_create(tmp_path):
    """Uninstall removes only the pack's own entries; a file the user added stays, and so does the folder."""
    home = tmp_path / "home"
    (home / "venv").mkdir(parents=True)
    (home / ".installed-by-brief2mp4-3d").write_text("x", encoding="utf-8")
    (home / "notes.txt").write_text("mine", encoding="utf-8")
    env = {**os.environ, "B2M3D_HOME": str(home)}
    run = subprocess.run([BASH, str(PACK / "install_3d.sh"), "--uninstall"], env=env, capture_output=True, text=True)
    assert run.returncode == 0
    assert not (home / "venv").exists() and (home / "notes.txt").read_text(encoding="utf-8") == "mine"
