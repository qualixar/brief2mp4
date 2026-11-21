"""Character kit art: variants, hands, the anime redesign, front view, mouths, image parts and the sheets."""
from __future__ import annotations

from characters_common import *  # noqa: F401,F403


# ---- checkpoint 2: art fixes, variants, anime redesign, image parts ----------------------------------------------


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


# ---- shadow puppet, spikes, the crow's wing, the crow's front view ---------------------------------------------------------

@needs_node
def test_shadow_puppet_is_a_profile_silhouette_with_at_most_an_eye_hole():
    r = js("""
const out = {};
const skin = B2M.SKINS['shadow-puppet'];
for (const name of ['child', 'adult', 'crow', 'tomato']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json');
  const props = ch.parts.filter((p) => p.prop).map((p) => p.id);
  const track = (view) => ({ keys: [{ t: 0, pose: 'idle' }], blink: false, view, props });
  const side = B2M.layout(ch, skin, B2M.pose(ch, track(undefined), 0, { steps: 12 }), { x: 0, y: 0, scale: 1 });
  const front = B2M.layout(ch, skin, B2M.pose(ch, track('front'), 0, { steps: 12 }), { x: 0, y: 0, scale: 1 });
  const paths = side.filter((i) => i.kind === 'path' && i.part !== 'rod');
  const fills = new Set(paths.filter((i) => i.fill).map((i) => i.fill));
  out[name] = {
    colours: Array.from(fills).length, frontIsProfile: JSON.stringify(front) === JSON.stringify(side),
    features: paths.filter((i) => /^(brow|pupil)/.test(i.part) || (i.part === 'mouth' && i.fill !== undefined && ch.parts.find((p) => p.id === 'mouth').mouth.kind === 'lips')).length,
    holes: Array.from(new Set(paths.filter((i) => i.fill === '#f4b862').map((i) => i.part))),
    propItems: paths.filter((i) => props.includes(i.part) && i.fill).map((i) => i.fill),
    hat: paths.filter((i) => name === 'tomato' && i.part === 'head').map((i) => i.fill),
    strokes: paths.filter((i) => i.fill && i.stroke).length,
  };
}
console.log(JSON.stringify(out));
""")
    for name, o in r.items():
        assert o["colours"] <= 2 and o["frontIsProfile"] and o["features"] == 0 and o["strokes"] == 0, name
        assert set(o["holes"]) <= {"eyeN", "eyeF"}, f"{name}: only an eye hole may be cut out, found {o['holes']}"
        assert all(f == "#150b06" for f in o["propItems"]), f"{name}: props are silhouettes too"
    assert set(r["tomato"]["hat"]) == {"#150b06"}, "the chef hat is leather like the rest"
    assert r["child"]["holes"] and r["crow"]["holes"], "the optional eye hole is there"


@needs_node
def test_the_sheet_shows_no_front_cell_for_a_profile_only_skin():
    r = js("""
globalThis.Path2D = class {}; require(process.argv[1] + '/../sheet.js');
const texts = [];
const g2 = new Proxy({}, { get: (t, k) => (k === 'fillText' ? (s) => texts.push(s) : () => ({ addColorStop() {} })), set: () => true });
const ch = require(process.argv[1] + '/../cast/child.json');
const labels = (sid) => { texts.length = 0; B2M.drawSheet(g2, ch, B2M.SKINS[sid]); return texts.slice(); };
console.log(JSON.stringify({ shadow: labels('shadow-puppet'), cel: labels('cel-shaded') }));
""")
    assert "front view (close-up)" in r["cel"] and "front view (close-up)" not in r["shadow"]
    assert "standing view" in r["shadow"] and "wave" in r["shadow"]
    readme = (KIT / "README-CHARACTERS.md").read_text(encoding="utf-8")
    assert "profile" in readme and "no front view" in readme.lower()


@needs_node
def test_hair_spikiness_is_a_per_character_field_with_a_moderate_default():
    adult = load("adult")
    assert adult["spikes"] == 0.35 and "spikes" not in load("child")
    r = js("""
const base = require(process.argv[1] + '/../cast/adult.json'), skin = B2M.SKINS['cel-shaded'];
const top = (spikes) => {
  const ch = Object.assign({}, base); if (spikes === undefined) delete ch.spikes; else ch.spikes = spikes;
  const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false }, 0, { steps: 12 });
  const hair = B2M.layout(ch, skin, p, { x: 0, y: 0, scale: 1 }).filter((i) => i.part === 'head' && i.fill === ch.palette.hair);
  return Math.min(...hair.map((i) => B2M.pathBounds(B2M.mapPoints(i.d, (x, y) => [i.m[0] * x + i.m[2] * y + i.m[4], i.m[1] * x + i.m[3] * y + i.m[5]])).y0));
};
console.log(JSON.stringify({ calm: top(0), few: top(0.35), moderate: top(undefined), spiky: top(1) }));
""")
    assert r["spiky"] < r["moderate"] < r["few"] < r["calm"] - 0.5 or (r["spiky"] < r["moderate"] and r["moderate"] < r["calm"] and r["few"] < r["calm"]), r
    assert r["spiky"] < r["few"] < r["calm"] and r["calm"] - r["spiky"] > 12, "tips grow with the field"


def test_schema_and_validator_accept_spikes_and_check_the_calm_outline():
    good = load("adult")
    assert validate.validate_character(good) == []
    assert validate.validate_character({**good, "spikes": 1.5}), "spikes is between 0 and 1"
    broken = json.loads(json.dumps(good))
    shape = next(sh for p in broken["parts"] for v in p.get("variants", {}).values() for sh in v.get("shapes", []) if "calm" in sh)
    shape["calm"] = shape["calm"][:-1]
    assert any("calm" in e for e in validate.validate_character(broken))


@needs_node
def test_the_crow_wing_is_a_folded_wing_lying_along_the_body_tip_to_the_tail():
    r = js("""
const ch = require(process.argv[1] + '/../cast/crow.json'), skin = B2M.SKINS['flat-explainer'];
const wing = (pose) => {
  const p = B2M.pose(ch, { keys: [{ t: 0, pose }], blink: false, breath: false }, 0, { steps: 12 }), items = B2M.layout(ch, skin, p, { x: 0, y: 0, scale: 1 });
  const b = (ids) => { let o = null; items.filter((i) => ids.includes(i.part) && i.kind === 'path' && i.fill).forEach((i) => { const q = B2M.pathBounds(B2M.mapPoints(i.d, (x, y) => [i.m[0] * x + i.m[2] * y + i.m[4], i.m[1] * x + i.m[3] * y + i.m[5]]));
    o = o ? { x0: Math.min(o.x0, q.x0), y0: Math.min(o.y0, q.y0), x1: Math.max(o.x1, q.x1), y1: Math.max(o.y1, q.y1) } : q; }); return o; };
  return { wing: b(['armN_up', 'armN_lo']), body: b(['torso']), tail: b(['tail']) };
};
console.log(JSON.stringify({ idle: wing('idle'), wave: wing('wave') }));
""")
    w, body = r["idle"]["wing"], r["idle"]["body"]
    assert (w["x1"] - w["x0"]) > 2.2 * (w["y1"] - w["y0"]), "long and low: it lies along the body"
    assert w["x0"] < body["x0"] - 5, "the tip reaches past the back of the body, towards the tail"
    assert w["y0"] > body["y0"] and w["y1"] < body["y1"] + 5, "it sits on the body, not hanging below it"
    assert r["wave"]["wing"]["y0"] < r["idle"]["wing"]["y0"] - 40, "a wave lifts the wing"
    sign = {p["id"]: p.get("sign") for p in load("crow")["parts"]}
    assert sign["armN_up"] == 1 and sign["armN_lo"] == 1


def test_the_crow_front_view_has_no_neck_tube_or_side_view_body_ring():
    crow = {p["id"]: p for p in load("crow")["parts"]}
    head_front = crow["head"]["variants"]["front"]["shapes"]
    assert not any(sh["type"] == "capsule" for sh in head_front), "no neck tube"
    torso_front = crow["torso"]["variants"]["front"]["shapes"]
    assert not any(sh.get("role") == "detail" for sh in torso_front) and len(torso_front) <= 2, "a plain front body, no inner ring"
    assert crow["tail"]["variants"]["front"]["shapes"] == []
