"""physics bake and hf project generation: determinism, offline project, validation."""
import json
import re
import shutil

import pytest

from conftest import EXAMPLE, needs_core

pytestmark = needs_core

FORBIDDEN_RUNTIME = ["Date.now", "performance.now", "Math.random", "setAnimationLoop", "requestAnimationFrame"]


def drop_scene(tmp_path, parts, names=("shell", "lens")):
    """A small drop: the shell falls onto the floor, the lens falls onto the shell."""
    bodies = [{"name": "floor", "shape": "box", "size": [3, 0.2, 3], "position": [0, -0.1, 0],
               "motion": "static", "friction": 1.0}]
    for i, name in enumerate(names):
        shutil.copy(parts[name], tmp_path / f"{name}.glb")
        bodies.append({"name": name, "shape": "hull", "glb": f"{name}.glb", "position": [0, 0.15 + 0.2 * i, 0],
                       "restitution": 0.05, "friction": 1.0, "linearDamping": 0.6, "angularDamping": 0.9})
    scene = tmp_path / "scene.json"
    scene.write_text(json.dumps({"fps": 30, "duration": 3, "substeps": 4, "gravity": [0, -3, 0], "bodies": bodies}))
    return scene


def test_physics_is_deterministic_and_settles(tmp_path, parts):
    from b2m3d import physics
    scene = drop_scene(tmp_path, parts)
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    res = physics.bake(scene, a)
    physics.bake(scene, b)
    assert a.read_bytes() == b.read_bytes(), "two bakes of one scene must be byte-identical"
    tracks = json.loads(a.read_text())["tracks"]
    assert res["frames"] == 90 and len(tracks["shell"]) == 90 and res["settled"] is True
    assert tracks["shell"][0][1] == pytest.approx(0.15)
    assert tracks["shell"][-1][1] == pytest.approx(0.005, abs=0.002)  # 10 mm tall, resting on the floor
    assert tracks["floor"][0] == tracks["floor"][-1]


def test_physics_hulls_read_compressed_glb(tmp_path, parts):
    from b2m3d import physics
    from conftest import cli
    packed = tmp_path / "packed.glb"
    assert cli("optimize", str(parts["cell"]), str(packed)).returncode == 0
    pts = physics.hull_points(packed, None)
    assert 8 <= len(pts) <= 200


def test_physics_unknown_node_raises(parts):
    from b2m3d import physics
    with pytest.raises(KeyError):
        physics.hull_points(parts["shell"], "no-such-node")


def make_shot(tmp_path, parts, **extra):
    shutil.copy(parts["shell"], tmp_path / "shell.glb")
    shot = {"duration": 3, "models": [{"src": "shell.glb", "spin": 20}],
            "titles": [{"text": "Hello <world> </script>", "start": 0.5, "duration": 2}], **extra}
    path = tmp_path / "shot.json"
    path.write_text(json.dumps(shot))
    return path


def test_hf_project_is_offline_and_seekable(tmp_path, parts):
    from b2m3d import hf
    res = hf.scaffold(make_shot(tmp_path, parts), tmp_path / "proj")
    assert res["warnings"] == [] and res["models"] == 1
    html = (tmp_path / "proj" / "index.html").read_text()
    assert 'data-duration="3"' in html and 'data-composition-id="b2m3d"' in html
    assert "Hello &lt;world&gt; &lt;/script&gt;" in html          # titles are escaped
    assert not re.search(r'(src|href)="https?://', html)           # no network at render time
    assert "/Us" + "ers/" not in html and "C:\\Us" + "ers" not in html
    for rel in ["vendor/three/build/three.module.js", "vendor/three/addons/loaders/GLTFLoader.js",
                "vendor/three/addons/environments/RoomEnvironment.js", "vendor/gsap.min.js",
                "b2m3d-runtime.js", "assets/shell.glb", "fonts/inter-latin-wght-normal.woff2"]:
        assert (tmp_path / "proj" / rel).exists(), rel
    runtime = (tmp_path / "proj" / "b2m3d-runtime.js").read_text()
    for token in FORBIDDEN_RUNTIME:
        assert token not in runtime, f"{token} breaks frame seeking"
    assert 'tonemapping ?? "neutral"' in runtime and "envIntensity ?? 0.35" in runtime
    assert "buildReady" in runtime


def test_hf_defaults_are_neutral_and_kicker_is_empty(tmp_path, parts):
    from b2m3d import hf
    hf.scaffold(make_shot(tmp_path, parts), tmp_path / "proj")
    html = (tmp_path / "proj" / "index.html").read_text()
    assert "b2m3d-kick-" not in html.split("<body>")[1]            # no kicker element unless asked for
    assert "teal" not in html.lower() and "mint" not in html.lower()
    hf.scaffold(make_shot(tmp_path, parts, titles=[{"kicker": "Part one", "text": "T", "start": 0, "duration": 2}]),
                tmp_path / "proj2")
    assert "b2m3d-kick-0" in (tmp_path / "proj2" / "index.html").read_text().split("<body>")[1]


def test_hf_generation_is_deterministic(tmp_path, parts):
    from b2m3d import hf
    shot = make_shot(tmp_path, parts)
    hf.scaffold(shot, tmp_path / "p1")
    hf.scaffold(shot, tmp_path / "p2")
    assert (tmp_path / "p1" / "index.html").read_bytes() == (tmp_path / "p2" / "index.html").read_bytes()


def test_hf_warns_on_unknown_keys(tmp_path, parts):
    from b2m3d import hf
    res = hf.scaffold(make_shot(tmp_path, parts, camra={"fov": 30}), tmp_path / "proj")
    assert any("camra" in w for w in res["warnings"])


@pytest.mark.parametrize("patch,message", [
    ({"duration": 0}, "duration"),
    ({"models": []}, "models"),
    ({"models": [{"src": "shell.glb", "track": "ghost"}]}, "physics bake"),
    ({"titles": [{"text": "x"}]}, "titles[0]"),
])
def test_hf_rejects_invalid_shots(tmp_path, parts, patch, message):
    from b2m3d import hf
    with pytest.raises(ValueError, match=re.escape(message)):
        hf.scaffold(make_shot(tmp_path, parts, **patch), tmp_path / "proj")


def test_hf_missing_model_file(tmp_path, parts):
    from b2m3d import hf
    shot = make_shot(tmp_path, parts, models=[{"src": "missing.glb"}])
    with pytest.raises(FileNotFoundError):
        hf.scaffold(shot, tmp_path / "proj")


def test_hf_same_file_name_in_two_folders_gets_two_assets(tmp_path, parts):
    from b2m3d import hf
    for sub, part in (("a", "shell"), ("b", "cell")):
        (tmp_path / sub).mkdir()
        shutil.copy(parts[part], tmp_path / sub / "part.glb")
    shot = tmp_path / "shot.json"
    shot.write_text(json.dumps({"duration": 2, "models": [{"src": "a/part.glb"}, {"src": "b/part.glb"}]}))
    hf.scaffold(shot, tmp_path / "proj")
    assert sorted(p.name for p in (tmp_path / "proj" / "assets").iterdir()) == ["part-2.glb", "part.glb"]


def test_hf_without_core_explains_how_to_install(tmp_path, parts, monkeypatch):
    from b2m3d import hf
    from b2m3d.run import B2M3DError
    shot = make_shot(tmp_path, parts)
    monkeypatch.setenv("B2M3D_HOME", str(tmp_path / "empty"))
    with pytest.raises(B2M3DError, match="install_3d"):
        hf.scaffold(shot, tmp_path / "proj")


def test_example_shot_matches_example_scene():
    """The shipped example is self-consistent: every tracked model has a body in the scene."""
    shot = json.loads((EXAMPLE / "shot.json").read_text())
    scene = json.loads((EXAMPLE / "scene.json").read_text())
    bodies = {b["name"] for b in scene["bodies"]}
    assert {m["track"] for m in shot["models"]} <= bodies


def test_hf_keeps_non_ascii_titles(tmp_path, parts):
    """A UTF-8 shot with accents and dashes must reach index.html intact (Windows defaults to cp1252)."""
    from b2m3d import hf
    shot_path = make_shot(tmp_path, parts, titles=[{"text": "Café — déjà vu", "start": 0, "duration": 2}])
    shot = json.loads(shot_path.read_text(encoding="utf-8"))
    shot_path.write_text(json.dumps(shot, ensure_ascii=False), encoding="utf-8")
    hf.scaffold(shot_path, tmp_path / "proj")
    html = (tmp_path / "proj" / "index.html").read_text(encoding="utf-8")
    assert "Café — déjà vu" in html or json.dumps("Café — déjà vu")[1:-1] in html


def test_text_io_always_names_utf8():
    """Every read_text/write_text/text open in the pack passes an explicit encoding."""
    from conftest import PACK
    offenders = []
    for src in (PACK / "b2m3d").glob("*.py"):
        for n, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.(read_text|write_text)\(|NamedTemporaryFile\(\"w\"", line) and "encoding=" not in line:
                offenders.append(f"{src.name}:{n}")
    assert not offenders, offenders
