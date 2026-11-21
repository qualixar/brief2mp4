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
SKIN_IDS = ["line-art", "paper-cutout", "shadow-puppet", "cel-shaded", "motion-comic", "flat-explainer"]


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
    for name in ("README-CHARACTERS.md", "rig.js", "poses.js", "shapes.js", "render.js", "skins.js", "skins-extra.js", "stage.js", "stage.html", "sheet.js", "index.js", "validate.py", "schema/character.schema.json",
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


@pytest.mark.parametrize("name", ["rig.js", "poses.js", "shapes.js", "render.js", "skins.js", "skins-extra.js", "stage.js", "sheet.js", "index.js"])
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
out.armsHiddenInFront = side.some((i) => /^(arm|hand)/.test(i.part)) && !front.some((i) => /^(arm|hand)/.test(i.part));
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
    assert len(pngs) == 12
    for png in pngs:
        import struct
        w, h = struct.unpack(">II", png.read_bytes()[16:24])
        assert (w, h) == (1920, 1080) and png.stat().st_size > 20000
    assert len({p.read_bytes() for p in pngs}) == 12, "every sheet is different"


# ---- checkpoint 3: the full cast, six skins, lip sync, the stage, example 09 ------------------------------------------

EX09 = REPO / "examples" / "09-story-characters"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import lipsync  # noqa: E402
import character_project as cp  # noqa: E402
import art_route  # noqa: E402

SHIPPED = [SCRIPTS / "lipsync.py", SCRIPTS / "character_project.py", SCRIPTS / "character_sheet.py", SKILL / "templates" / "threejs" / "characters-stage.html",
           SKILL / "references" / "formats.md", SKILL / "SKILL.md", SKILL / "scripts" / "art_route.py", *EX09.glob("*")]


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.name)
def test_shipped_files_are_utf8_lf_and_free_of_personal_paths(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    assert b"\r" not in raw, "LF endings only (Windows CI)"
    assert raw.count(b"\n") <= 800
    for word in ["/Us" + "ers/", "va" + "run", "C:\\" + "Users"]:
        assert word not in text.lower(), f"{word} in {path.name}"


def test_the_starter_cast_is_the_four_characters_with_props_and_anime_and_front_drawings():
    assert {p.stem for p in CAST} >= {"child", "adult", "crow", "tomato"}
    props = {"child": "prop_kite", "adult": "prop_sword", "tomato": "prop_ladle"}
    for name in ("child", "adult", "crow", "tomato"):
        ch = load(name)
        ids = {p["id"] for p in ch["parts"]}
        assert {"hip", "torso", "head", "mouth", "armN_up", "legN_up"} <= ids, name
        names = {v for p in ch["parts"] for v in p.get("variants", {})}
        assert {"anime", "front"} <= names, f"{name} needs an anime and a front drawing"
        if name in props:
            assert props[name] in ids
        assert any(sh.get("role") == "cel" for p in ch["parts"] for sh in [*p["shapes"], *[s for v in p.get("variants", {}).values() for s in v.get("shapes", [])]]), name
    assert next(p for p in load("crow")["parts"] if p["id"] == "mouth")["mouth"]["kind"] == "jaw"


@needs_node
def test_six_skins_each_have_their_look_on_the_same_character():
    r = js("""
const out = {};
for (const name of ['child', 'adult', 'crow', 'tomato']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json');
  for (const sid of Object.keys(B2M.SKINS)) {
    const s = B2M.SKINS[sid], p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false }, 0.5, { steps: s.steps, smooth: !s.steps });
    const items = B2M.layout(ch, s, p, { x: 300, y: 700, scale: 1 });
    const fills = new Set(items.filter((i) => i.kind === 'path' && typeof i.fill === 'string').map((i) => i.fill));
    out[name + ':' + sid] = { fills: fills.size, filledStroke: items.filter((i) => i.fill && i.stroke).length, rods: items.filter((i) => i.part === 'rod').length, patterns: items.filter((i) => i.fill && i.fill.pattern).map((i) => i.fill.pattern)[0] || '' };
  }
}
console.log(JSON.stringify(out));
""")
    for name in ("child", "adult", "crow", "tomato"):
        assert r[f"{name}:flat-explainer"]["filledStroke"] == 0, "flat vector has no outlines"
        assert r[f"{name}:flat-explainer"]["fills"] >= 6 and r[f"{name}:shadow-puppet"]["fills"] <= 3, "a silhouette is two colours"
        assert r[f"{name}:shadow-puppet"]["rods"] >= 1, "visible rods"
        assert r[f"{name}:motion-comic"]["patterns"] == "halftone"
        assert r[f"{name}:line-art"]["fills"] <= 3 and r[f"{name}:line-art"]["filledStroke"] >= 10, "line art: strokes, with the ground's colour inside"
        assert r[f"{name}:paper-cutout"]["patterns"] == "grain"


@needs_node
def test_shadow_puppet_has_a_warm_lamp_and_motion_comic_a_panel_and_a_caption_box():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const scene = { width: 1920, height: 1080, skin: 'x', ground: 900, palette: { sky: '#aabbcc', ground: '#889977' }, cast: [{ id: 'k', character: 'child', x: 600, scale: 1.5, track: [{ t: 0, pose: 'idle' }] }], captions: [{ from: 1, to: 3, text: 'Hello there' }] };
const make = (skin, t) => B2M.createStage(Object.assign({}, scene, { skin }), { child: ch }).items(t);
const shadow = make('shadow-puppet', 2), comic = make('motion-comic', 2), comicNoCaption = make('motion-comic', 4);
console.log(JSON.stringify({ lamp: shadow.some((i) => i.fill && i.fill.grad === 'radial'), panel: comic.some((i) => i.part === 'panel'), caption: comic.some((i) => i.part === 'caption' && i.text === 'Hello there'),
  noCaptionLater: !comicNoCaption.some((i) => i.part === 'caption'), panelStays: comicNoCaption.some((i) => i.part === 'panel') }));
""")
    assert all(r.values()), r


@needs_node
def test_the_stage_draws_the_same_frame_the_same_way_in_every_skin():
    r = js("""
const fs = require('fs'), path = require('path');
const base = JSON.parse(fs.readFileSync(path.resolve(process.argv[1], '..', '..', '..', '..', '..', 'examples', '09-story-characters', 'scene.json'), 'utf8'));
const cast = { child: require(process.argv[1] + '/../cast/child.json'), crow: require(process.argv[1] + '/../cast/crow.json') };
const out = {};
for (const sid of Object.keys(B2M.SKINS)) {
  const make = () => B2M.createStage(Object.assign({}, base, { skin: sid }), cast);
  const a = JSON.stringify(make().items(4.37)), b = JSON.stringify(make().items(4.37)), c = JSON.stringify(make().items(8.1));
  out[sid] = { same: a === b, moves: a !== c, finite: !/NaN|undefined|Infinity/.test(a) };
}
console.log(JSON.stringify(out));
""")
    assert len(r) == 6 and all(v["same"] and v["moves"] and v["finite"] for v in r.values()), r


# ---- lip sync ------------------------------------------------------------------------------------------------------

WORDS = json.loads((EX09 / "words.json").read_text(encoding="utf-8"))


def shapes_of(text: str, start=0.0, end=0.6, fps=30, lang="en") -> list[str]:
    track = lipsync.build_track([{"text": text, "start": start, "end": end}], fps, lang)
    return [k["v"] for k in track if k["v"] != "rest"]


def test_viseme_mapping_on_the_committed_sample():
    track = lipsync.build_track(WORDS, 30)
    assert track[0]["v"] == "rest" and track[-1]["v"] == "rest" and track[-1]["t"] >= WORDS[-1]["end"] - 1 / 30
    assert {k["v"] for k in track} <= set(lipsync.VISEMES)
    assert len({k["v"] for k in track}) >= 7, "a spoken line uses most of the nine shapes"
    assert [k["t"] for k in track] == sorted(k["t"] for k in track)
    assert shapes_of("my", 4.92, 5.14) == ["MBP", "AI"]
    assert shapes_of("five", 0, 0.6)[0] == "FV" and shapes_of("little", 0, 0.7)[0] == "L"
    assert "AI" in shapes_of("kite", 5.2, 5.78) and shapes_of("moon", 0, 0.6) == ["MBP", "U", "etc"]
    assert shapes_of("the", 0, 0.3) == ["L", "E"] and shapes_of("boo", 0, 0.5) == ["MBP", "U"]
    assert shapes_of("pop", 0, 0.5) == ["MBP", "O", "MBP"]


def test_a_pause_over_150_ms_closes_the_mouth_and_a_shorter_one_does_not():
    def gap_track(gap):
        return lipsync.build_track([{"text": "go", "start": 1.0, "end": 1.4}, {"text": "now", "start": 1.4 + gap, "end": 1.9 + gap}], 30)
    closed = gap_track(0.16)
    assert any(k["v"] == "rest" and 1.35 < k["t"] < 1.6 for k in closed), "a 160 ms pause closes the mouth"
    assert not any(k["v"] == "rest" and 1.0 < k["t"] < 1.9 for k in gap_track(0.14)), "a 140 ms pause keeps it open"
    sample = lipsync.build_track(WORDS, 30)
    assert any(k["v"] == "rest" and 4.12 <= k["t"] <= 4.45 for k in sample), "the pause after 'crow,' is closed"
    assert not any(k["v"] == "rest" and 4.7 < k["t"] < 5.2 for k in sample), "no pause between 'is' and 'my'"


@pytest.mark.parametrize("fps", [24, 25, 30, 60])
def test_no_mouth_shape_is_held_for_less_than_one_frame(fps):
    words = WORDS + [{"text": "extraordinarily", "start": 11.0, "end": 11.09}, {"text": "a", "start": 12.0, "end": 12.02}]
    track = lipsync.build_track(words, fps)
    for a, b in zip(track, track[1:]):
        assert b["t"] - a["t"] >= 1 / fps - 1e-3, (fps, a, b)
        assert a["v"] != b["v"], "no repeated key"
    assert all(abs(k["t"] * fps - round(k["t"] * fps)) < 0.01 for k in track), "keys sit on the frame grid"


def test_romanised_hindi_gets_a_best_effort_mapping_and_says_so():
    assert "MBP" in shapes_of("namaste", lang="hi") and shapes_of("bhai", 0, 0.5, lang="hi")[0] == "MBP"
    assert shapes_of("aap", 0, 0.5, lang="hi")[0] == "AI" and "U" in shapes_of("doost", 0, 0.5, lang="hi")
    assert "approximate" in (SCRIPTS / "lipsync.py").read_text(encoding="utf-8")


def test_lipsync_reads_the_transcribe_formats_and_rejects_bad_words(tmp_path):
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps(WORDS), encoding="utf-8")
    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"words": [{"word": w["text"], "start": w["start"], "end": w["end"]} for w in WORDS]}), encoding="utf-8")
    assert lipsync.load_words(flat) == lipsync.load_words(wrapped)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"text": "hi", "start": 1}]), encoding="utf-8")
    with pytest.raises(ValueError):
        lipsync.load_words(bad)


def write_wav(path: Path, parts: list[tuple[float, float]], width: int = 2, rate: int = 16000) -> None:
    """parts: (seconds, amplitude 0..1) blocks of a 200 Hz tone; amplitude 0 is silence."""
    import math
    import struct
    import wave
    frames = bytearray()
    peak = {1: 127, 2: 32767, 3: 8388607, 4: 2147483647}[width]
    for seconds, amp in parts:
        for i in range(int(seconds * rate)):
            v = int(amp * peak * math.sin(2 * math.pi * 200 * i / rate))
            if width == 1:
                frames += struct.pack("<B", v + 128)
            elif width == 2:
                frames += struct.pack("<h", v)
            elif width == 3:
                frames += int(v).to_bytes(3, "little", signed=True)
            else:
                frames += struct.pack("<i", v)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(bytes(frames))


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_the_wav_fallback_gives_open_half_open_and_closed_mouths(tmp_path, width):
    wav = tmp_path / "voice.wav"
    write_wav(wav, [(0.4, 0.0), (0.6, 0.8), (0.6, 0.2), (0.4, 0.0)], width)
    track = lipsync.amplitude_track(wav, 30)
    at = lambda t: next(k["v"] for k in reversed(track) if k["t"] <= t)  # noqa: E731
    assert (at(0.2), at(0.7), at(1.3), at(1.8)) == ("rest", "AI", "etc", "rest")
    for a, b in zip(track, track[1:]):
        assert b["t"] - a["t"] >= 1 / 30 - 1e-3


def test_the_wav_fallback_explains_a_file_it_cannot_read(tmp_path):
    bad = tmp_path / "not.wav"
    bad.write_bytes(b"this is not a wav file")
    with pytest.raises(ValueError, match="PCM WAV"):
        lipsync.amplitude_track(bad)


def test_lipsync_command_line(tmp_path):
    script = str(SCRIPTS / "lipsync.py")
    run = lambda *a: subprocess.run([sys.executable, script, *a], capture_output=True, text=True, encoding="utf-8")  # noqa: E731
    out = run(str(EX09 / "words.json"), "--fps", "24")
    assert out.returncode == 0 and json.loads(out.stdout)[0]["v"] == "rest"
    part = json.loads(run(str(EX09 / "words.json"), "--from", "7", "--to", "10").stdout)
    assert part[0]["t"] > 6.9 and part[-1]["t"] > 9.7
    dest = tmp_path / "v.json"
    assert run(str(EX09 / "words.json"), "--out", str(dest)).returncode == 0 and json.loads(dest.read_text(encoding="utf-8"))
    assert run().returncode == 2 and run(str(tmp_path / "missing.json")).returncode == 2 and run(str(EX09 / "words.json"), "--fps", "0").returncode == 2
    wav = tmp_path / "v.wav"
    write_wav(wav, [(0.5, 0.0), (0.5, 0.7)])
    assert json.loads(run("--wav", str(wav)).stdout)[-1]["v"] == "rest"


# ---- example 09, the project builder, the 3D stage ------------------------------------------------------------------

def test_example_09_scene_resolves_its_lip_sync_from_the_committed_words(monkeypatch, tmp_path):
    monkeypatch.setattr(cp, "vendor", lambda project, three=False: (project / "vendor").mkdir(exist_ok=True) or (project / "vendor" / "gsap.min.js").write_text("", encoding="utf-8"))
    scene = cp.build_scene_project(EX09 / "scene.json", tmp_path / "p", "cel-shaded")
    assert scene["skin"] == "cel-shaded" and scene["duration"] == 14 and {m["character"] for m in scene["cast"]} == {"child", "crow"}
    kid, crow = (m["track"]["visemes"] for m in scene["cast"])
    assert 3.3 < kid[0]["t"] < 3.5 and kid[-1]["t"] <= 6.0 and 7.0 < crow[0]["t"] < 7.3 and crow[-1]["t"] <= 10.0
    assert len({k["v"] for k in kid}) >= 5 and len({k["v"] for k in crow}) >= 5
    html = (tmp_path / "p" / "index.html").read_text(encoding="utf-8")
    assert 'data-duration="14"' in html and not re.search(r"__(WIDTH|HEIGHT|DURATION)__", html)
    assert "child" in (tmp_path / "p" / "characters" / "cast.js").read_text(encoding="utf-8")
    assert "B2M_SCENE" in (tmp_path / "p" / "characters" / "scene.js").read_text(encoding="utf-8")
    assert (tmp_path / "p" / "hyperframes.json").is_file()


def test_example_09_child_walks_without_sliding_feet():
    scene = json.loads((EX09 / "scene.json").read_text(encoding="utf-8"))
    kid = scene["cast"][0]
    a, b = kid["track"]["move"]
    speed = (b["x"] - a["x"]) / (b["t"] - a["t"])
    code = "const B2M = require(process.argv[1]); const c = require(process.argv[2]); console.log(B2M.strideSpeed(c, 'walk', 8) * " + str(kid["scale"]) + ")"
    planted = float(subprocess.run([NODE, "-e", code, str(KIT / "index.js"), str(KIT / "cast" / "child.json")], capture_output=True, text=True, encoding="utf-8").stdout)
    assert abs(speed - planted) / planted < 0.15, f"scene speed {speed:.0f} px/s vs planted-feet speed {planted:.0f}"
    assert kid["track"]["layers"][0]["steps"] == 8


def test_example_09_has_a_brief_the_words_and_a_readme():
    brief = (EX09 / "BRIEF.md").read_text(encoding="utf-8")
    for must in ("14.0 s", "paper cut-out", "anime", "Hey crow, that is my kite!", "Finders keepers, little one.", "words.json"):
        assert must in brief
    assert (EX09 / "README.md").is_file() and (EX09 / "make_standin_voice.py").is_file()
    assert [w["text"] for w in WORDS][:3] == ["Hey", "crow,", "that"]


def test_the_3d_stage_starter_is_deterministic_and_offline():
    html = (SKILL / "templates" / "threejs" / "characters-stage.html").read_text(encoding="utf-8")
    code = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    for banned in ("Math.random", "Date", "performance.now", "setInterval", "setTimeout", "requestAnimationFrame", "setAnimationLoop", "THREE.Clock", "http://", "https://"):
        assert banned not in code, banned
    assert "vendor/three.module.js" in html and "CanvasTexture" in html and "quaternion.copy(camera.quaternion)" in html
    assert html.count("new THREE.Mesh(") >= 8, "a ground, a few props and the actors"


def test_stage3d_project_builder_inlines_the_cast(monkeypatch, tmp_path):
    monkeypatch.setattr(cp, "vendor", lambda project, three=False: (project / "vendor").mkdir(exist_ok=True))
    cp.build_stage3d_project(["child", "crow"], tmp_path / "s", 5)
    html = (tmp_path / "s" / "index.html").read_text(encoding="utf-8")
    assert 'data-duration="5"' in html and "__DURATION__" not in html
    assert "crow" in (tmp_path / "s" / "characters" / "cast.js").read_text(encoding="utf-8")


# ---- routing and docs -----------------------------------------------------------------------------------------------

def test_the_router_names_the_kit_for_characters_and_dialogue_only():
    for brief in ("A short story with two characters who talk", "An anime duel between two characters", "A dialogue scene about a lost kite", "Our mascot says hello, lip sync it"):
        r = art_route.route(brief)
        assert r["kit"] == "characters/README-CHARACTERS.md" and any("character kit" in w for w in r["why"]) and "characters/README-CHARACTERS.md" in r["read"], brief
        assert "character kit" in art_route.report(r)
    for brief in ("A paper plane flies over the title", "Explain how our SaaS onboarding works in 40 seconds", "A lyric video for our new single"):
        assert art_route.route(brief)["kit"] is None
    none = art_route.route("make a video with a character")
    assert none["form"] is None and "character kit" in art_route.report(none)


def test_formats_and_skill_route_characters_to_the_kit_and_keep_lottie_and_rive():
    formats = (SKILL / "references" / "formats.md").read_text(encoding="utf-8")
    section = formats[formats.index("## Storytelling, skits and character pieces"):formats.index("## Vertical Shorts and Reels")]
    assert "characters/README-CHARACTERS.md" in section and "Lottie or Rive" in section and "lipsync.py" in section
    assert "Lip sync and full character animation are outside this skill" not in formats
    skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "### The character kit" in skill and "characters/README-CHARACTERS.md" in skill and "scripts/lipsync.py" in skill and "characters-stage.html" in skill


def test_readme_documents_every_part_of_the_kit():
    text = (KIT / "README-CHARACTERS.md").read_text(encoding="utf-8")
    for must in ("lipsync.py", "character_project.py", "character_sheet.py", "line-art", "shadow-puppet", "motion-comic", "flat-explainer", "child", "adult", "crow", "tomato", "stage3d", "strideSpeed", "examples/09-story-characters", "Known limits"):
        assert must in text, must


def resolved_scene() -> dict:
    return cp.resolve_scene(json.loads((EX09 / "scene.json").read_text(encoding="utf-8")), EX09)


def pick_mouth_times() -> list[float]:
    """Moments inside the child's line where the mouth shape differs, taken from the lip-sync track."""
    track = resolved_scene()["cast"][0]["track"]["visemes"]
    picked, seen = [], set()
    for a, b in zip(track, track[1:]):
        if a["v"] != "rest" and a["v"] not in seen and b["t"] - a["t"] >= 0.06:
            seen.add(a["v"])
            picked.append(round((a["t"] + b["t"]) / 2, 2))
    return picked[:6]


def mouth_positions(skin: str, times: list[float]) -> list[tuple[float, float]]:
    scene = {**resolved_scene(), "skin": skin}
    code = """
const fs = require('fs'); const B2M = require(process.argv[1]);
const scene = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')), times = JSON.parse(process.argv[3]);
const skin = B2M.SKINS[scene.skin], m = scene.cast[0], ch = require(process.argv[1] + '/../cast/child.json');
const out = times.map((t) => { const p = B2M.pose(ch, m.track, t, { steps: skin.steps, smooth: !skin.steps }); return B2M.partPoint(ch, p, { x: m.x, y: scene.ground, scale: m.scale }, 'mouth', skin); });
console.log(JSON.stringify(out));
"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "scene.json"
        f.write_text(json.dumps(scene), encoding="utf-8")
        out = subprocess.run([NODE, "-e", code, str(KIT / "index.js"), str(f), json.dumps(times)], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr[-500:]
    return [tuple(p) for p in json.loads(out.stdout)]


@pytest.mark.slow
def test_example_09_renders_in_both_skins_passes_the_delivery_checks_and_the_mouth_moves(tmp_path):
    """Render through HyperFrames, finish with a stand-in voice, check, and look at the speaker's mouth on the dialogue frames."""
    if shutil.which("npx") is None or shutil.which("ffmpeg") is None:
        pytest.skip("needs npx and ffmpeg")
    voice = tmp_path / "voice.wav"
    assert subprocess.run([sys.executable, str(EX09 / "make_standin_voice.py"), str(EX09 / "words.json"), str(voice), "14"], capture_output=True).returncode == 0
    bash = shutil.which("bash")
    finals = {}
    for skin in ("paper-cutout", "cel-shaded"):
        project = tmp_path / skin
        build = subprocess.run([sys.executable, str(SCRIPTS / "character_project.py"), "--scene", str(EX09 / "scene.json"), "--skin", skin, "--out", str(project)], capture_output=True, text=True, encoding="utf-8")
        assert build.returncode == 0, build.stderr[-600:]
        render = subprocess.run([shutil.which("npx"), "--yes", "hyperframes@0.8.216", "render", str(project), "--quality", "draft", "--workers", "4", "-o", str(tmp_path / f"{skin}-raw.mp4"), "--quiet"],
                                capture_output=True, text=True, encoding="utf-8", cwd=project, timeout=1200)
        assert render.returncode == 0, render.stdout[-600:] + render.stderr[-600:]
        final = tmp_path / f"{skin}.mp4"
        fin = subprocess.run([bash, str(SCRIPTS / "finish.sh"), "--in", str(tmp_path / f"{skin}-raw.mp4"), "--out", str(final), "--seconds", "14", "--audio", str(voice)], capture_output=True, text=True, encoding="utf-8")
        assert fin.returncode == 0, fin.stderr[-600:]
        check = subprocess.run([bash, str(SCRIPTS / "check_delivery.sh"), str(final), "--seconds", "14"], capture_output=True, text=True, encoding="utf-8")
        assert "RESULT: PASS" in check.stdout, check.stdout[-900:]
        finals[skin] = final
    times = pick_mouth_times()
    assert len(times) >= 4
    for skin, final in finals.items():
        sheet = tmp_path / f"contact-{skin}"
        cs = subprocess.run([bash, str(SCRIPTS / "contact_sheet.sh"), str(final), "--at", ",".join(f"{t:.2f}" for t in times), "--out", str(sheet)], capture_output=True, text=True, encoding="utf-8")
        assert cs.returncode == 0 and (sheet / "sheet.png").is_file(), cs.stderr[-400:]
        crops = set()
        for t, (x, y) in zip(times, mouth_positions(skin, times)):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(sheet / f"t_{t:06.2f}s.png"), "-vf", f"crop=96:72:{max(0, int(x) - 48)}:{max(0, int(y) - 36)},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
            assert len(raw) == 96 * 72
            crops.add(raw)
        assert len(crops) >= 3, f"{skin}: the speaker's mouth shows {len(crops)} different pictures on {len(times)} dialogue frames"


@pytest.mark.slow
def test_the_3d_stage_starter_renders_a_frame(tmp_path):
    if shutil.which("npx") is None:
        pytest.skip("needs npx")
    build = subprocess.run([sys.executable, str(SCRIPTS / "character_project.py"), "--stage3d", "--cast", "child,crow", "--seconds", "2", "--out", str(tmp_path / "s3")], capture_output=True, text=True, encoding="utf-8")
    assert build.returncode == 0, build.stderr[-500:]
    out = tmp_path / "s3.mp4"
    render = subprocess.run([shutil.which("npx"), "--yes", "hyperframes@0.8.216", "render", str(tmp_path / "s3"), "--quality", "draft", "-o", str(out), "--quiet"], capture_output=True, text=True, encoding="utf-8", cwd=tmp_path / "s3", timeout=900)
    assert render.returncode == 0 and out.exists(), render.stdout[-500:] + render.stderr[-500:]
    frames = [subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(out), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout for t in (0.2, 1.8)]
    assert all(len(f) > 20000 for f in frames) and frames[0] != frames[1], "the set and the camera move"


@pytest.mark.slow
def test_the_same_frame_at_the_same_time_renders_to_the_same_pixels(tmp_path):
    if shutil.which("npx") is None:
        pytest.skip("needs npx")
    project = tmp_path / "p"
    assert subprocess.run([sys.executable, str(SCRIPTS / "character_project.py"), "--scene", str(EX09 / "scene.json"), "--skin", "paper-cutout", "--out", str(project)], capture_output=True).returncode == 0
    shots = []
    for _ in range(2):
        done = subprocess.run([shutil.which("npx"), "--yes", "hyperframes@0.8.216", "snapshot", str(project), "--at", "4.4"], capture_output=True, text=True, encoding="utf-8", cwd=project, timeout=600)
        assert done.returncode == 0, done.stderr[-400:]
        snaps = sorted((project / ".hyperframes" / "artifacts" / "snapshots").rglob("frame-00-*.png"), key=lambda p: p.stat().st_mtime)
        shots.append(snaps[-1].read_bytes())
    assert shots[0] == shots[1]
