"""model, material and optimize: determinism, units, normals, linear colour, error paths."""
import json
import sys

import pytest

from conftest import EXAMPLE, cli, needs_cadquery, needs_core

pytestmark = needs_core


def gltf(path):
    from b2m3d.glbio import gltf_json
    return gltf_json(path)


def test_manifold_part_is_metres_y_up_with_normals(parts):
    meta = gltf(parts["shell"])
    prim = meta["meshes"][0]["primitives"][0]
    assert "NORMAL" in prim["attributes"], "normals must be exported or three.js renders flat-shaded"
    import trimesh
    lo, hi = trimesh.load(parts["shell"], force="scene").bounds
    size = (hi - lo).round(4)
    assert size.tolist() == [0.06, 0.01, 0.04]  # 60 x 40 x 10 mm, Z-up in the spec, Y-up in the file


def test_model_bake_is_byte_identical(tmp_path):
    from b2m3d import model
    a, b = tmp_path / "a.glb", tmp_path / "b.glb"
    model.build(EXAMPLE / "device.py", a, {"part": "board"})
    model.build(EXAMPLE / "device.py", b, {"part": "board"})
    assert a.read_bytes() == b.read_bytes()


def test_trimesh_spec_uses_its_own_units_and_params(tmp_path):
    from b2m3d import model
    from conftest import REPO
    out = tmp_path / "box.glb"
    res = model.build(REPO / "tests" / "data" / "trimesh_spec.py", out, {"size": 4.0})
    assert res["bounds_m"][1][0] - res["bounds_m"][0][0] == pytest.approx(0.04, abs=1e-4)  # 4 cm


def test_all_parts_in_one_glb_have_named_nodes(tmp_path):
    from b2m3d import model
    out = tmp_path / "all.glb"
    res = model.build(EXAMPLE / "device.py", out, {"part": "all"})
    names = {n.get("name") for n in gltf(out)["nodes"]}
    assert res["parts"] == 5 and {"shell", "cell", "board", "cover", "lens"} <= names


def test_parse_params_json_and_strings():
    from b2m3d.model import parse_params
    assert parse_params(["n=3", "s=abc", "f=[1,2]"]) == {"n": 3, "s": "abc", "f": [1, 2]}
    with pytest.raises(ValueError):
        parse_params(["novalue"])


def test_unknown_part_is_a_json_error(tmp_path):
    proc = cli("model", str(EXAMPLE / "device.py"), str(tmp_path / "x.glb"), "--param", "part=nope")
    assert proc.returncode == 1
    assert json.loads(proc.stderr)["ok"] is False and "unknown part" in proc.stderr


def test_missing_cadquery_gives_install_hint(monkeypatch):
    from b2m3d import model
    from b2m3d.run import B2M3DError
    monkeypatch.setitem(sys.modules, "cadquery", None)
    with pytest.raises(B2M3DError, match="cad"):
        model._cq_to_parts(object(), "x", 0.05)


@needs_cadquery
def test_cadquery_assembly_keeps_parts_and_colours(tmp_path):
    from b2m3d import model
    from conftest import REPO
    out = tmp_path / "cad.glb"
    res = model.build(REPO / "tests" / "data" / "cad_spec.py", out)
    assert res["parts"] == 2
    mats = gltf(out)["materials"]
    assert len(mats) == 2 and mats[0]["pbrMetallicRoughness"]["baseColorFactor"][3] == 1.0


def test_presets_are_valid_and_linear():
    from b2m3d import material
    presets = material.load_presets()
    assert len(presets) == 16
    for name, p in presets.items():
        assert p["name"] == name and p["colorSpace"] == "linear"
        assert len(p["baseColor"]) == 3 and all(0 <= c <= 1 for c in p["baseColor"])
        assert 0 <= p["metallic"] <= 1 and 0 <= p["roughness"] <= 1


def test_srgb_to_linear_uses_power_2_2():
    from b2m3d.material import srgb_to_linear
    assert srgb_to_linear("#808080")[0] == pytest.approx((128 / 255) ** 2.2, abs=1e-4)
    assert srgb_to_linear("#ffffff") == [1.0, 1.0, 1.0]
    with pytest.raises(ValueError):
        srgb_to_linear("teal")


def test_to_gltf_maps_extensions():
    from b2m3d import material
    presets = material.load_presets()
    glass = material.to_gltf(presets["smoked_glass"])["extensions"]
    assert {"KHR_materials_transmission", "KHR_materials_volume", "KHR_materials_ior"} <= set(glass)
    neon = material.to_gltf(presets["neon_emissive"])
    assert neon["emissiveFactor"] == [1.0, 0.35, 0.1]
    assert neon["extensions"]["KHR_materials_emissive_strength"]["emissiveStrength"] == 8.0
    assert "KHR_materials_clearcoat" in material.to_gltf(presets["car_paint_red"])["extensions"]


def test_material_assign_is_linear_exact_and_byte_identical(parts, tmp_path):
    from b2m3d import material
    a, b = tmp_path / "a.glb", tmp_path / "b.glb"
    res = material.assign(parts["board"], a, {"*": "pcb_green"})
    material.assign(parts["board"], b, {"*": "pcb_green"})
    assert a.read_bytes() == b.read_bytes()
    assert res["assigned"] == {"board": "pcb_green"}
    mats = gltf(a)["materials"]
    assert len(mats) == 1, "the replaced material must not ship as dead weight"
    assert mats[0]["pbrMetallicRoughness"]["baseColorFactor"] == [0.006, 0.045, 0.02, 1.0]


def test_material_assign_by_node_name(parts, tmp_path):
    from b2m3d import material
    out = tmp_path / "named.glb"
    res = material.assign(parts["shell"], out, {"shell": "gold"})
    assert res["assigned"] == {"shell": "gold"}


def test_material_assign_errors(parts, tmp_path):
    from b2m3d import material
    from b2m3d.run import B2M3DError
    with pytest.raises(KeyError, match="unknown material"):
        material.assign(parts["shell"], tmp_path / "o.glb", {"*": "unobtainium"})
    with pytest.raises(B2M3DError, match="nothing to assign"):
        material.assign(parts["shell"], tmp_path / "o.glb", {})
    with pytest.raises(ValueError):
        material.parse_assignments(["noequals"])


def test_optimize_keeps_names_compresses_and_stays_readable(parts, tmp_path):
    from b2m3d import glbio
    out = tmp_path / "opt.glb"
    proc = cli("optimize", str(parts["board"]), str(out))
    assert proc.returncode == 0, proc.stderr
    assert glbio.is_compressed(out)
    assert any(n.get("name") == "board" for n in gltf(out)["nodes"])
    import trimesh
    assert len(trimesh.load(glbio.readable(out), force="scene").geometry) == 1


def test_optimize_rejects_bad_ratio(parts, tmp_path):
    proc = cli("optimize", str(parts["board"]), str(tmp_path / "o.glb"), "--simplify", "2")
    assert proc.returncode == 1
