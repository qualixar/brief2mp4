"""Character kit: schema, rig determinism, skins, poses, files. Fast tests need Node (the skill already requires it)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin" / "skills" / "brief2mp4"
KIT = SKILL / "characters"
CAST = sorted((KIT / "cast").glob("*.json"))
NODE = shutil.which("node")
sys.path.insert(0, str(KIT))
import validate  # noqa: E402

needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")
REQUIRED_POSES = ["idle", "wave", "point", "sit", "run-ready", "jump", "surprised", "sad", "laugh", "think", "fight-ready", "bow"]
SKIN_IDS = ["paper-cutout", "cel-shaded"]


def js(code: str):
    """Run JS against the kit (loaded through characters/index.js) and return its JSON result."""
    prog = "const B2M = require(process.argv[1]);\n" + code
    out = subprocess.run([NODE, "-e", prog, str(KIT / "index.js")], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert out.returncode == 0, out.stderr[-1500:]
    return json.loads(out.stdout)


def load(name: str) -> dict:
    return json.loads((KIT / "cast" / f"{name}.json").read_text(encoding="utf-8"))


# ---- files -------------------------------------------------------------------------------------------------------

def kit_files() -> list[Path]:
    return [p for p in KIT.rglob("*") if p.is_file() and p.suffix in {".js", ".json", ".md", ".py", ".sh", ".html"}]


def test_the_kit_exists_with_its_parts():
    for name in ("README-CHARACTERS.md", "rig.js", "poses.js", "shapes.js", "render.js", "skins.js", "sheet.js", "index.js", "validate.py", "schema/character.schema.json",
                 "image-demo/make_tin_bot.py", "image-demo/tin-bot.json"):
        assert (KIT / name).is_file(), name
    assert CAST, "at least one cast file"


@pytest.mark.parametrize("path", kit_files(), ids=lambda p: str(p.relative_to(KIT)))
def test_files_are_utf8_with_lf_endings_and_under_800_lines(path):
    raw = path.read_bytes()
    raw.decode("utf-8")
    assert b"\r" not in raw, "LF endings only (Windows CI)"
    assert raw.count(b"\n") <= 800


def test_no_personal_paths_or_internal_names_in_the_kit():
    banned = ["/Us" + "ers/", "va" + "run", "quali" + "xar-", "claude-" + "hooks", "C:\\" + "Users"]
    for path in kit_files() + [REPO / "tests" / "test_characters.py"]:
        text = path.read_text(encoding="utf-8").lower()
        for word in banned:
            assert word not in text, f"{word} found in {path.name}"


# ---- schema ------------------------------------------------------------------------------------------------------

def test_schema_is_valid_json_schema_shaped():
    schema = json.loads((KIT / "schema" / "character.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"].startswith("https://json-schema.org/")
    assert {"id", "palette", "proportions", "parts"} <= set(schema["required"])


@pytest.mark.parametrize("path", CAST, ids=lambda p: p.stem)
def test_every_cast_file_validates(path):
    errors = validate.validate_character(json.loads(path.read_text(encoding="utf-8")))
    assert errors == []


def test_validation_catches_broken_characters():
    good = load(CAST[0].stem)
    cases = {
        "missing palette": {k: v for k, v in good.items() if k != "palette"},
        "bad parent": {**good, "parts": [{**good["parts"][0], "parent": "nope"}, *good["parts"][1:]]},
        "unknown colour key": {**good, "parts": [{**good["parts"][0], "shapes": [{"type": "circle", "c": [0, 0], "r": 5, "fill": "no-such-colour"}]}, *good["parts"][1:]]},
        "relative path command": {**good, "parts": [{**good["parts"][0], "shapes": [{"type": "path", "d": "m0 0 l5 5", "fill": "ink"}]}, *good["parts"][1:]]},
        "duplicate id": {**good, "parts": [good["parts"][0], good["parts"][0], *good["parts"][2:]]},
    }
    for label, bad in cases.items():
        assert validate.validate_character(bad), f"{label} should fail validation"


def test_validation_catches_a_parent_cycle():
    good = load(CAST[0].stem)
    parts = [dict(p) for p in good["parts"]]
    root = next(p for p in parts if p["parent"] is None)
    leaf = next(p for p in parts if p["parent"] == root["id"])
    root["parent"] = leaf["id"]
    assert any("cycle" in e or "root" in e for e in validate.validate_character({**good, "parts": parts}))


# ---- the rig is a pure function of time --------------------------------------------------------------------------

def code_without_comments(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(^|[^:])//.*", r"\1", text)


@pytest.mark.parametrize("name", ["rig.js", "poses.js", "shapes.js", "render.js", "skins.js", "sheet.js", "index.js"])
def test_runtime_files_read_no_clock_and_no_unseeded_randomness(name):
    code = code_without_comments(KIT / name)
    for banned in ("Math.random", "Date", "performance.now", "setInterval", "setTimeout", "requestAnimationFrame", "fetch("):
        assert banned not in code, f"{name} must be a pure function of time: found {banned}"
    code = code.replace("http://www.w3.org/2000/svg", "")   # the SVG namespace is a name, not a download
    assert "http://" not in code and "https://" not in code


def test_rig_js_has_no_banned_words_even_in_comments():
    text = (KIT / "rig.js").read_text(encoding="utf-8")
    for banned in ("Math.random", "Date", "performance.now"):
        assert banned not in text


@needs_node
def test_pose_is_identical_for_the_same_time_and_differs_across_time():
    result = js("""
const kid = require(process.argv[1] + '/../cast/' + 'child.json');
const track = { keys: [{ t: 0, pose: 'idle' }, { t: 1, pose: 'wave', ease: 'inOut' }], layers: [{ cycle: 'talk', from: 0, to: 4 }] };
const a = JSON.stringify(B2M.pose(kid, track, 0.37)), b = JSON.stringify(B2M.pose(kid, track, 0.37));
const c = JSON.stringify(B2M.pose(kid, track, 0.9));
console.log(JSON.stringify({ same: a === b, differs: a !== c }));
""")
    assert result == {"same": True, "differs": True}


@needs_node
def test_pose_eases_between_keys_and_holds_outside_them():
    r = js("""
const kid = require(process.argv[1] + '/../cast/child.json');
const track = [{ t: 1, pose: 'idle' }, { t: 2, pose: 'wave', ease: 'linear' }];
const at = (t) => B2M.pose(kid, track, t).parts.armN_up.r;
console.log(JSON.stringify({ before: at(0), start: at(1), mid: at(1.5), end: at(2), after: at(5), idle: B2M.POSES.idle.armN_up, wave: B2M.POSES.wave.armN_up }));
""")
    assert abs(r["before"] - r["start"]) < 1e-9
    assert r["end"] == r["after"]
    assert min(r["start"], r["end"]) < r["mid"] < max(r["start"], r["end"])


@needs_node
def test_hold_ease_snaps_at_the_key_time():
    r = js("""
const kid = require(process.argv[1] + '/../cast/child.json');
const track = [{ t: 0, pose: 'idle' }, { t: 1, pose: 'jump', ease: 'hold' }];
const at = (t) => B2M.pose(kid, track, t).parts.armN_up.r;
console.log(JSON.stringify([at(0), at(0.99), at(1)]));
""")
    assert r[0] == r[1] and r[2] != r[1]


@needs_node
def test_required_poses_exist_and_resolve_on_every_character():
    names = js("console.log(JSON.stringify(Object.keys(B2M.POSES)))")
    assert set(REQUIRED_POSES) <= set(names)
    for path in CAST:
        out = js(f"""
const ch = require({json.dumps(str(path))});
const bad = [];
for (const name of Object.keys(B2M.POSES)) {{
  const p = B2M.pose(ch, [{{ t: 0, pose: name }}], 0);
  for (const [id, v] of Object.entries(p.parts)) for (const k of ['r', 'x', 'y', 'sx', 'sy']) if (!Number.isFinite(v[k])) bad.push(name + ':' + id + ':' + k);
}}
console.log(JSON.stringify(bad));
""")
        assert out == [], f"{path.stem}: {out[:5]}"


@needs_node
def test_unknown_pose_is_a_clear_error():
    out = subprocess.run([NODE, "-e", "const B2M=require(process.argv[1]); const c=require(process.argv[2]); B2M.pose(c,[{t:0,pose:'nope'}],0)", str(KIT / "index.js"), str(CAST[0])],
                         capture_output=True, text=True, encoding="utf-8")
    assert out.returncode != 0 and "nope" in out.stderr


@needs_node
def test_blinks_are_seeded_and_happen():
    r = js("""
const kid = require(process.argv[1] + '/../cast/child.json');
const closed = []; for (let i = 0; i < 2400; i++) { const t = i / 100; if (B2M.pose(kid, [{ t: 0, pose: 'idle' }], t).blink > 0.5) closed.push(t); }
const again = []; for (let i = 0; i < 2400; i++) { const t = i / 100; if (B2M.pose(kid, [{ t: 0, pose: 'idle' }], t).blink > 0.5) again.push(t); }
console.log(JSON.stringify({ n: closed.length, same: JSON.stringify(closed) === JSON.stringify(again) }));
""")
    assert r["same"] and 10 < r["n"] < 400


@needs_node
def test_cycles_hold_drawings_at_the_steps_per_second():
    r = js("""
const kid = require(process.argv[1] + '/../cast/child.json');
const track = { keys: [{ t: 0, pose: 'idle' }], blink: false, breath: false, layers: [{ cycle: 'walk', from: 0, to: 4, steps: 8 }] };
let changes = 0, prev = null;
for (let i = 0; i < 300; i++) { const s = JSON.stringify(B2M.pose(kid, track, i / 300 + 1).parts); if (prev !== null && s !== prev) changes++; prev = s; }
console.log(JSON.stringify({ changes }));
""")
    assert 6 <= r["changes"] <= 9, "8 steps a second means about 8 changes in one second"


@needs_node
def test_walk_run_and_talk_cycles_move_the_limbs():
    r = js("""
const kid = require(process.argv[1] + '/../cast/child.json');
const out = {};
for (const cycle of ['walk', 'run', 'talk', 'wave']) {
  const track = { keys: [{ t: 0, pose: 'idle' }], blink: false, visemes: [{ t: 0, v: 'AI' }], layers: [{ cycle, from: 0, to: 9, steps: 12 }] };
  const seen = new Set(); for (let i = 0; i < 90; i++) seen.add(JSON.stringify(B2M.pose(kid, track, 1 + i / 30).parts));
  out[cycle] = seen.size;
}
console.log(JSON.stringify(out));
""")
    assert all(n >= 3 for n in r.values()), r


# ---- skins --------------------------------------------------------------------------------------------------------

@needs_node
def test_skin_registry_lists_the_skins():
    ids = js("console.log(JSON.stringify(Object.keys(B2M.SKINS)))")
    assert set(SKIN_IDS) <= set(ids)
    for sid in ids:
        art_form = KIT.parent / "references" / "art-forms" / f"{sid}.md"
        assert art_form.is_file(), f"skin {sid} must match an art-form page"


@needs_node
def test_every_skin_resolves_every_pose_for_every_character():
    for path in CAST:
        out = js(f"""
const ch = require({json.dumps(str(path))});
const bad = [];
for (const sid of Object.keys(B2M.SKINS)) for (const name of Object.keys(B2M.POSES)) {{
  const p = B2M.pose(ch, [{{ t: 0, pose: name }}], 0.5, {{ steps: B2M.SKINS[sid].steps }});
  const items = B2M.layout(ch, B2M.SKINS[sid], p, {{ x: 400, y: 800, scale: 1 }});
  if (!items.length) bad.push(sid + ':' + name + ':empty');
  for (const it of items) {{ if (it.kind === 'path' && (typeof it.d !== 'string' || it.m.some((v) => !Number.isFinite(v)) || /NaN|undefined/.test(it.d))) bad.push(sid + ':' + name + ':bad'); }}
}}
console.log(JSON.stringify(bad));
""")
        assert out == [], f"{path.stem}: {out[:5]}"


@needs_node
def test_layout_is_deterministic_and_skins_look_different():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const make = (sid) => { const s = B2M.SKINS[sid]; const p = B2M.pose(ch, [{ t: 0, pose: 'wave' }], 1.3, { steps: s.steps }); return JSON.stringify(B2M.layout(ch, s, p, { x: 300, y: 700, scale: 1 })); };
console.log(JSON.stringify({ same: make('paper-cutout') === make('paper-cutout') && make('cel-shaded') === make('cel-shaded'), differ: make('paper-cutout') !== make('cel-shaded') }));
""")
    assert r == {"same": True, "differ": True}


@needs_node
def test_paper_cutout_has_shadows_and_cel_shaded_has_outlines_and_two_tones():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const items = (sid) => { const s = B2M.SKINS[sid]; const p = B2M.pose(ch, [{ t: 0, pose: 'idle' }], 0.5, { steps: s.steps }); return B2M.layout(ch, s, p, { x: 300, y: 700, scale: 1 }); };
const paper = items('paper-cutout'), cel = items('cel-shaded');
console.log(JSON.stringify({ shadows: paper.filter((i) => i.shadow).length, celStrokes: cel.filter((i) => i.stroke).length,
  celFills: new Set(cel.filter((i) => i.fill).map((i) => i.fill)).size }));
""")
    assert r["shadows"] > 5
    assert r["celStrokes"] > 5 and r["celFills"] >= 6


@needs_node
def test_handmade_skins_change_at_most_their_cadence_per_second():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const out = {};
for (const sid of ['paper-cutout', 'cel-shaded']) {
  const s = B2M.SKINS[sid]; let changes = 0, prev = null;
  for (let i = 0; i < 60; i++) { const t = 2 + i / 60; const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }, { t: 4, pose: 'wave' }], layers: [{ cycle: 'talk', from: 0, to: 5 }] }, t, { steps: s.steps });
    const k = JSON.stringify(B2M.layout(ch, s, p, { x: 300, y: 700, scale: 1 })); if (prev !== null && k !== prev) changes++; prev = k; }
  out[sid] = changes;
}
console.log(JSON.stringify(out));
""")
    assert all(n <= 12 for n in r.values()), r


@needs_node
def test_all_nine_mouth_shapes_draw_differently():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const s = B2M.SKINS['cel-shaded'];
const shapes = B2M.VISEMES.map((v) => { const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, visemes: [{ t: 0, v }, { t: 1, v: 'rest' }] }, 0.2, { steps: s.steps });
  return JSON.stringify(B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }).filter((i) => i.part === 'mouth')); });
console.log(JSON.stringify({ n: B2M.VISEMES.length, distinct: new Set(shapes).size }));
""")
    assert r["n"] == 9 and r["distinct"] == 9


# ---- checkpoint 2: art fixes, variants, anime redesign, image parts ----------------------------------------------

DEMO = KIT / "image-demo"


@needs_node
def test_hands_are_mittens_and_wave_and_point_swap_the_drawing():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), s = B2M.SKINS['paper-cutout'];
const count = (pose) => { const p = B2M.pose(ch, [{ t: 0, pose }], 0, { steps: 12 }); return B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }).filter((i) => i.part === 'handN').length; };
console.log(JSON.stringify({ idle: count('idle'), wave: count('wave'), point: count('point') }));
""")
    assert r["wave"] > r["idle"] and r["point"] >= r["idle"] and r["wave"] >= 6


@needs_node
def test_a_raised_arm_draws_over_the_head_and_a_hanging_arm_behind_it():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), s = B2M.SKINS['cel-shaded'];
const order = (pose) => { const p = B2M.pose(ch, [{ t: 0, pose }], 0, { steps: 12 }); const parts = B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }).map((i) => i.part);
  return { arm: parts.indexOf('armN_up'), head: parts.indexOf('head') }; };
console.log(JSON.stringify({ idle: order('idle'), wave: order('wave') }));
""")
    assert r["idle"]["arm"] < r["idle"]["head"] and r["wave"]["arm"] > r["wave"]["head"]


@needs_node
def test_wave_moves_the_wrist_through_two_held_drawings():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const track = { keys: [{ t: 0, pose: 'wave' }], blink: false, breath: false, layers: [{ cycle: 'wave', from: 0, to: 5, steps: 6 }] };
const seen = new Set(); for (let i = 0; i < 120; i++) seen.add(B2M.pose(ch, track, 1 + i / 60, { steps: 12 }).parts.handN.r.toFixed(3));
console.log(JSON.stringify(Array.from(seen)));
""")
    assert len(r) == 2


@needs_node
def test_the_front_view_redraws_head_eyes_brows_and_mouth():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), s = B2M.SKINS['paper-cutout'];
const items = (view) => { const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, view }, 0, { steps: 12 }); return B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }); };
const side = items(undefined), front = items('front');
const at = (list, part) => JSON.stringify(list.filter((i) => i.part === part).map((i) => i.d));
const out = {}; for (const part of ['head', 'eyeN', 'eyeF', 'browN', 'browF', 'mouth']) out[part] = at(side, part) !== at(front, part);
out.torsoSame = at(side, 'torso') === at(front, 'torso');
console.log(JSON.stringify(out));
""")
    assert all(r.values()), r


@needs_node
def test_mouths_are_large_and_each_shape_has_its_own_parts():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), s = B2M.SKINS['cel-shaded'];
const out = {};
B2M.VISEMES.forEach((v) => {
  const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, visemes: [{ t: 0, v }, { t: 9, v: 'rest' }] }, 0.2, { steps: 12 });
  const items = B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }).filter((i) => i.part === 'mouth');
  const wide = Math.max(...items.map((i) => B2M.pathBounds(i.d).w));
  out[v] = { wide: Math.round(wide), fills: items.map((i) => i.fill) };
});
const palette = ch.palette, def = B2M.DEFAULT_PALETTE;
out.teeth = def.teeth; out.tongue = def.tongue; out.lip = def.lip;
console.log(JSON.stringify(out));
""")
    # the first child's mouth was 24 units wide and about 11 tall: now 38 wide and 17 tall, two and a half times the area
    assert r["AI"]["wide"] >= 36 and r["E"]["wide"] >= 36 and r["O"]["wide"] >= 16
    assert r["AI"]["fills"].count(r["teeth"]) >= 1 and r["E"]["fills"].count(r["teeth"]) >= 1
    assert r["L"]["fills"].count(r["tongue"]) >= 1 and r["AI"]["fills"].count(r["tongue"]) >= 1
    assert r["MBP"]["fills"].count(r["lip"]) == 1 and r["MBP"]["fills"].count(r["teeth"]) == 0
    fv = r["FV"]["fills"]
    assert fv.index(r["teeth"]) < fv.index(r["lip"]), "FV: the top teeth sit on the lower lip, which is drawn over them"


@needs_node
def test_anime_skin_changes_the_design_not_only_the_line():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const items = (sid) => { const s = B2M.SKINS[sid]; const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false }, 0, { steps: 12 }); return B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }); };
const paper = items('paper-cutout'), cel = items('cel-shaded');
const eyeW = (list) => Math.max(...list.filter((i) => i.part === 'eyeN').map((i) => B2M.pathBounds(i.d).h));
console.log(JSON.stringify({ eyeRatio: eyeW(cel) / eyeW(paper), iris: cel.filter((i) => i.part === 'pupilN' && i.fill === ch.palette.iris).length, paperIris: paper.filter((i) => i.fill === ch.palette.iris).length,
  highlights: cel.filter((i) => i.part === 'pupilN' && /^#fffaf0$|^#ffffff$/i.test(i.fill)).length,
  hairCel: cel.filter((i) => i.part === 'head' && i.fill === ch.palette.hairShine).length, hairPaper: paper.filter((i) => i.part === 'head' && i.fill && i.fill === ch.palette.hairShine).length,
  noseCel: cel.filter((i) => i.part === 'nose').length, nosePaper: paper.filter((i) => i.part === 'nose').length,
  celShadowShapes: ch.parts.flatMap((p) => [p.shapes].concat(Object.values(p.variants || {}).map((v) => v.shapes || [])).flat()).filter((sh) => sh.role === 'cel').length }));
""")
    assert r["eyeRatio"] > 1.2, "anime eyes are larger"
    assert r["iris"] >= 1 and r["paperIris"] == 0 and r["highlights"] >= 2, "an iris and two highlights"
    assert r["hairCel"] >= 1 and r["hairPaper"] == 0, "a hair shine band only in the anime skin"
    assert r["celShadowShapes"] >= 4


@needs_node
def test_cel_skin_throws_speed_lines_on_jump_and_run_only():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const fx = (sid, keys, layers) => { const s = B2M.SKINS[sid]; const p = B2M.pose(ch, { keys, layers: layers || [], blink: false }, 2.2, { steps: 12 }); return B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }).filter((i) => i.part === 'fx').length; };
const idle = [{ t: 0, pose: 'idle' }], jump = [{ t: 0, pose: 'jump' }];
console.log(JSON.stringify({ jump: fx('cel-shaded', jump), run: fx('cel-shaded', idle, [{ cycle: 'run', from: 0, to: 5 }]), idle: fx('cel-shaded', idle), paperJump: fx('paper-cutout', jump) }));
""")
    assert r["jump"] >= 8 and r["run"] >= 8 and r["idle"] == 0 and r["paperJump"] == 0


@needs_node
def test_paper_skin_has_grain_and_a_lighter_cut_edge_on_every_layer():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), s = B2M.SKINS['paper-cutout'];
const p = B2M.pose(ch, [{ t: 0, pose: 'idle' }], 0.5, { steps: 12 });
const items = B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 });
const lum = (hex) => B2M.toRgb(hex).reduce((a, b) => a + b, 0);
const edged = items.filter((i) => i.shadow && i.stroke);
console.log(JSON.stringify({ grain: items.filter((i) => i.fill && i.fill.pattern === 'grain').length, edged: edged.length,
  lighter: edged.every((i) => lum(i.stroke) > lum(i.fill)), thin: edged.every((i) => i.sw <= 2), shadows: items.filter((i) => i.shadow).length }));
""")
    assert r["grain"] >= 10 and r["edged"] >= 10 and r["lighter"] and r["thin"]


@needs_node
def test_shoes_have_soles_and_shorts_have_leg_openings():
    ch = load("child")
    foot = next(p for p in ch["parts"] if p["id"] == "footN")
    assert any(sh.get("fill") == "sole" for sh in foot["shapes"]) and len(foot["shapes"]) >= 4
    leg = next(p for p in ch["parts"] if p["id"] == "legN_up")
    fills = [sh.get("fill") for sh in leg["shapes"]]
    assert "pantsIn" in fills and fills.index("skin") < fills.index("pants"), "skin leg under the shorts, opening drawn at the hem"


# ---- image parts ----------------------------------------------------------------------------------------------------

def png_info(data: bytes) -> tuple[int, int, int]:
    """Width, height and the alpha of the top-left pixel of an 8-bit RGBA PNG, read with zlib only."""
    import struct
    import zlib
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
    assert (depth, ctype) == (8, 6)
    pos, idat = 8, b""
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        if data[pos + 4:pos + 8] == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    return w, h, raw[1 + 3]


def test_image_demo_is_made_by_the_shipped_script_and_is_reproducible(tmp_path):
    out = subprocess.run([sys.executable, str(DEMO / "make_tin_bot.py"), str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    made = sorted(p.name for p in (tmp_path / "parts").glob("*.png"))
    assert made == sorted(p.name for p in (DEMO / "parts").glob("*.png")) and len(made) >= 20
    for name in made:
        assert (tmp_path / "parts" / name).read_bytes() == (DEMO / "parts" / name).read_bytes(), f"{name} differs between runs"
    assert (tmp_path / "tin-bot.json").read_text(encoding="utf-8") == (DEMO / "tin-bot.json").read_text(encoding="utf-8")


def test_part_pictures_are_png_with_a_transparent_background():
    for path in (DEMO / "parts").glob("*.png"):
        w, h, corner_alpha = png_info(path.read_bytes())
        assert w > 8 and h > 8 and corner_alpha == 0, path.name


def test_the_image_character_validates_and_names_one_mouth_picture_per_shape():
    data = json.loads((DEMO / "tin-bot.json").read_text(encoding="utf-8"))
    assert validate.validate_character(data, DEMO) == []
    mouth = next(p for p in data["parts"] if p["id"] == "mouth")["mouth"]
    assert mouth["kind"] == "images" and set(mouth["images"]) == {"rest", "AI", "E", "O", "U", "MBP", "FV", "L", "etc"}


def test_validator_checks_picture_files_extensions_and_the_rest_mouth():
    data = json.loads((DEMO / "tin-bot.json").read_text(encoding="utf-8"))
    def broken(edit):
        d = json.loads(json.dumps(data))
        edit(d)
        return validate.validate_character(d, DEMO)
    assert any("not found" in e for e in broken(lambda d: d["parts"][0]["image"].update(src="parts/nope.png")))
    assert any("does not match" in e for e in broken(lambda d: d["parts"][0]["image"].update(src="parts/head.gif")))
    assert any("rest" in e for e in broken(lambda d: next(p for p in d["parts"] if p["id"] == "mouth")["mouth"]["images"].pop("rest")))
    assert any("missing" in e for e in broken(lambda d: d["parts"][0]["image"].pop("w")))
    inline = broken(lambda d: d["parts"][0]["image"].update(src="data:image/png;base64,AAAA"))
    assert inline == [], "a data: URI needs no file"
    assert validate.validate_character(data) == [], "without a folder the files are not checked"


FAKE_DOM = """
const mk = (tag) => ({ tagName: tag, attrs: {}, style: {}, kids: [], setAttribute(k, v) { this.attrs[k] = String(v); }, appendChild(c) { this.kids.push(c); return c; }, replaceChild(n, o) { this.kids[this.kids.indexOf(o)] = n; } });
const doc = { createElementNS: (ns, tag) => mk(tag) };
"""


@needs_node
def test_image_parts_render_through_both_backends():
    r = js(FAKE_DOM + """
const ch = require(process.argv[1] + '/../image-demo/tin-bot.json'), s = B2M.SKINS['paper-cutout'];
const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, visemes: [{ t: 0, v: 'O' }, { t: 3, v: 'rest' }] }, 0.5, { steps: 12 });
const items = B2M.layout(ch, s, p, { x: 100, y: 500, scale: 1 });
const images = items.filter((i) => i.kind === 'image');
// SVG backend
const root = mk('div'), svg = B2M.createSVG(doc, root, 400, 600); svg.update(items);
const els = svg.svg.kids.filter((k) => k.tagName === 'image');
// canvas backend with a recording context and a fake loader
const calls = []; globalThis.Image = class { constructor() { this.complete = true; } decode() { return Promise.resolve(); } };
const g2 = { save() {}, restore() {}, setTransform() {}, drawImage(...a) { calls.push(a.slice(1)); }, fill() {}, stroke() {}, createPattern() { return 'pattern'; } };
globalThis.document = { createElement: () => ({ getContext: () => ({ beginPath() {}, arc() {}, fill() {} }) }) };
B2M.preloadImages({ bot: ch }).then(() => { B2M.drawCanvas(g2, items); console.log(JSON.stringify({ n: images.length, svg: els.length, href: els.every((e) => /^parts\\/.+\\.png$/.test(e.attrs.href)), drawn: calls.length,
  mouth: images.filter((i) => i.part === 'mouth').map((i) => i.src) })); });
""")
    assert r["n"] >= 15 and r["svg"] == r["n"] and r["href"] and r["drawn"] == r["n"]
    assert r["mouth"] == ["parts/mouth_O.png"], "the mouth picture follows the viseme"


@needs_node
def test_every_mouth_picture_is_chosen_by_its_viseme_and_unknown_falls_back_to_rest():
    r = js("""
const ch = require(process.argv[1] + '/../image-demo/tin-bot.json'), s = B2M.SKINS['cel-shaded'];
const src = (v) => { const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], visemes: [{ t: 0, v }, { t: 3, v: 'rest' }] }, 0.5, { steps: 12 }); return B2M.layout(ch, s, p, { x: 0, y: 0, scale: 1 }).filter((i) => i.part === 'mouth').map((i) => i.src)[0]; };
console.log(JSON.stringify(B2M.VISEMES.map(src)));
""")
    assert len(set(r)) == 9


@needs_node
def test_the_svg_backend_draws_paths_with_pattern_fills():
    r = js(FAKE_DOM + """
const ch = require(process.argv[1] + '/../cast/child.json'), s = B2M.SKINS['paper-cutout'];
const p = B2M.pose(ch, [{ t: 0, pose: 'idle' }], 0.5, { steps: 12 });
const items = B2M.layout(ch, s, p, { x: 100, y: 500, scale: 1 });
const root = mk('div'), svg = B2M.createSVG(doc, root, 400, 600); svg.update(items);
const paths = svg.svg.kids.filter((k) => k.tagName === 'path');
const defs = svg.svg.kids[0];
console.log(JSON.stringify({ paths: paths.length, items: items.length, patterns: defs.kids.filter((k) => k.tagName === 'pattern').length, usesPattern: paths.some((e) => /url\\(#b2m-grain\\)/.test(e.attrs.fill)) }));
""")
    assert r["paths"] == r["items"] and r["patterns"] == 1 and r["usesPattern"]


def test_preload_lists_every_picture_a_character_uses():
    r = js("""
const ch = require(process.argv[1] + '/../image-demo/tin-bot.json');
console.log(JSON.stringify(B2M.imageSources(ch).length));
""")
    assert r >= 20


def test_project_builder_inlines_pictures_as_data_uris():
    sys.path.insert(0, str(SKILL / "scripts"))
    import character_project as cp
    data = cp.load_file(DEMO / "tin-bot.json")
    head = next(p for p in data["parts"] if p["id"] == "head")
    assert head["image"]["src"].startswith("data:image/png;base64,")
    mouth = next(p for p in data["parts"] if p["id"] == "mouth")["mouth"]["images"]["AI"]["src"]
    assert mouth.startswith("data:image/png;base64,")


def test_readme_explains_how_to_prepare_part_images():
    text = (KIT / "README-CHARACTERS.md").read_text(encoding="utf-8").lower()
    for phrase in ("one image per part", "transparent", "pivot", "same scale", "mouth", "webp"):
        assert phrase in text, phrase


@pytest.mark.slow
def test_child_and_image_character_sheets_render(tmp_path):
    if shutil.which("npx") is None:
        pytest.skip("npx not found")
    script = str(SKILL / "scripts" / "character_sheet.py")
    for args in (["--character", "child", "--skin", "all"], ["--file", str(DEMO / "tin-bot.json"), "--skin", "all"]):
        out = subprocess.run([sys.executable, script, *args, "--out", str(tmp_path)], capture_output=True, text=True, encoding="utf-8", timeout=900)
        assert out.returncode == 0, out.stdout[-800:] + out.stderr[-800:]
    pngs = sorted(tmp_path.glob("*.png"))
    assert len(pngs) == 4
    for png in pngs:
        import struct
        w, h = struct.unpack(">II", png.read_bytes()[16:24])
        assert (w, h) == (1920, 1080) and png.stat().st_size > 20000
    assert len({p.read_bytes() for p in pngs}) == 4, "every sheet is different"
