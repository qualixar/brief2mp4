"""Character kit core: files, schema, the rig as a pure function of time, poses and skins."""
from __future__ import annotations

from characters_common import *  # noqa: F401,F403


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
    for path in kit_files() + sorted((REPO / "tests").glob("*characters*.py")):
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


# ---- poses as the rig mixes them ----------------------------------------------------------------------------------------

@needs_node
def test_a_pose_scale_is_the_size_itself_not_added_to_the_rest_size():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const at = (pose) => B2M.pose(ch, { keys: [{ t: 0, pose }], blink: false, breath: false }, 0, { steps: 12 }).parts.eyeN;
console.log(JSON.stringify({ surprised: at('surprised'), sad: at('sad'), idle: at('idle') }));
""")
    assert abs(r["surprised"]["sy"] - 1.15) < 1e-6 and abs(r["surprised"]["sx"] - 1.12) < 1e-6
    assert abs(r["sad"]["sy"] - 0.8) < 1e-6 and r["idle"]["sx"] == r["idle"]["sy"] == 1


@needs_node
def test_eyes_stay_inside_the_head_in_every_pose_and_every_transition_between_poses():
    r = js("""
const faces = { child: 'head', adult: 'head', crow: 'head', tomato: 'torso' };
const bad = [], poses = Object.keys(B2M.POSES);
const box = (items, ids) => {
  let b = null;
  items.filter((i) => i.kind === 'path' && ids.includes(i.part)).forEach((i) => {
    const d = B2M.mapPoints(i.d, (x, y) => [i.m[0] * x + i.m[2] * y + i.m[4], i.m[1] * x + i.m[3] * y + i.m[5]]), p = B2M.pathBounds(d);
    b = b ? { x0: Math.min(b.x0, p.x0), y0: Math.min(b.y0, p.y0), x1: Math.max(b.x1, p.x1), y1: Math.max(b.y1, p.y1) } : p;
  });
  return b;
};
let n = 0;
for (const name of Object.keys(faces)) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json');
  for (const sid of ['flat-explainer', 'cel-shaded']) {
    const skin = B2M.SKINS[sid];
    for (const a of poses) for (const b of poses) {
      if (a === b) continue;
      const track = { keys: [{ t: 0, pose: a }, { t: 1, pose: b, ease: 'linear' }], blink: false, breath: false };
      for (let k = 0; k <= 9; k++) {
        const t = k / 9, p = B2M.pose(ch, track, t, { smooth: true }), items = B2M.layout(ch, skin, p, { x: 0, y: 0, scale: 1 });
        const eyes = box(items, ['eyeN', 'eyeF']), head = box(items, [faces[name]]); n++;
        if (!eyes) continue;
        const tol = 2;
        if (eyes.x0 < head.x0 - tol || eyes.x1 > head.x1 + tol || eyes.y0 < head.y0 - tol || eyes.y1 > head.y1 + tol) bad.push([name, sid, a, b, k]);
      }
    }
  }
}
console.log(JSON.stringify({ n, bad: bad.slice(0, 5), count: bad.length }));
""")
    assert r["n"] >= 15000 and r["count"] == 0, r["bad"]


@needs_node
def test_a_character_that_is_not_speaking_keeps_a_closed_mouth_unless_a_key_asks_for_one():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), crow = require(process.argv[1] + '/../cast/crow.json');
const visemes = [{ t: 1, v: 'AI' }, { t: 1.3, v: 'rest' }, { t: 1.4, v: 'O' }, { t: 1.8, v: 'rest' }];
const listener = { keys: [{ t: 0, pose: 'surprised' }, { t: 2, pose: 'laugh' }, { t: 3, pose: 'jump' }], blink: false };
const asked = { keys: [{ t: 0, pose: 'idle' }, { t: 1, pose: 'laugh', mouth: 'AI' }, { t: 2, pose: 'idle' }], blink: false };
const v = (c, tr, t) => B2M.pose(c, tr, t, { steps: 12 }).viseme;
const all = []; for (let t = 0; t <= 3.5; t += 0.1) all.push(v(ch, listener, t), v(crow, listener, t));
console.log(JSON.stringify({ closed: all.every((x) => x === 'rest'), poseMouthsOptIn: v(ch, Object.assign({ poseMouths: true }, listener), 0.5), asked: [v(ch, asked, 0.5), v(ch, asked, 1.5), v(ch, asked, 2.5)],
  speaking: v(ch, Object.assign({ visemes }, listener), 1.1) }));
""")
    assert r["closed"], "a surprised, laughing or jumping listener has a closed mouth"
    assert r["poseMouthsOptIn"] == "O", "poseMouths: true restores each pose's own mouth"
    assert r["asked"] == ["rest", "AI", "rest"], "a key's mouth holds until the next key"
    assert r["speaking"] == "AI"
