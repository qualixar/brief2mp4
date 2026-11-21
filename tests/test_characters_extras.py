"""Character kit extras: the shadow puppet's jaw and profile, light scenery, contrast, ground and captions, walk keys, routing."""
from __future__ import annotations

import copy

from characters_common import *  # noqa: F401,F403
import validate_scene  # noqa: E402

GOOD = json.loads((EX09 / "scene.json").read_text(encoding="utf-8"))
README = (KIT / "README-CHARACTERS.md").read_text(encoding="utf-8")
SHADOW = "'shadow-puppet'"
WORLD = "(i) => { const d = B2M.mapPoints(i.d, (x, y) => [i.m[0] * x + i.m[2] * y + i.m[4], i.m[1] * x + i.m[3] * y + i.m[5]]); return B2M.pathBounds(d); }"


def lum(hex_):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# ---- the hinged jaw -----------------------------------------------------------------------------------------------------

@needs_node
def test_the_shadow_puppet_jaw_swings_open_with_the_mouth_shape_for_humans_and_the_tomato():
    r = js("""
const skin = B2M.SKINS['shadow-puppet'], paper = B2M.SKINS['paper-cutout'], out = {};
for (const name of ['child', 'adult', 'tomato']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json'), angles = {};
  B2M.VISEMES.forEach((v) => {
    const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, breath: false, visemes: [{ t: 0, v }, { t: 9, v: 'rest' }] }, 0.5, { steps: 12 });
    const items = B2M.layout(ch, skin, p, { x: 0, y: 0, scale: 1 }), jaw = items.filter((i) => i.part === 'jaw'), gap = items.filter((i) => i.part === 'jawGap');
    angles[v] = { deg: Math.round(Math.atan2(jaw[0].m[1], jaw[0].m[0]) * 1800 / Math.PI) / 10, jaw: jaw.length, gap: gap.length, gapFill: gap[0].fill, jawFill: jaw[0].fill };
  });
  const other = B2M.layout(ch, paper, B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false }, 0, { steps: 12 }), { x: 0, y: 0, scale: 1 });
  out[name] = { angles, paperJaw: other.filter((i) => i.part === 'jaw' || i.part === 'jawGap').length };
}
console.log(JSON.stringify(out));
""")
    for name, o in r.items():
        a = {v: x["deg"] for v, x in o["angles"].items()}
        assert a["rest"] == 0 and a["MBP"] == 0, f"{name}: the jaw is shut for rest and MBP"
        assert a["AI"] > a["O"] > a["L"] > a["E"] > 0 and a["AI"] >= 20, f"{name}: AI opens widest, then O: {a}"
        assert len(set(a.values())) >= 6, f"{name}: the jaw angle differs across the mouth shapes: {a}"
        assert all(x["jaw"] == 1 and x["gap"] == 1 for x in o["angles"].values())
        assert o["angles"]["AI"]["gapFill"] == "#f7c470" and o["angles"]["AI"]["jawFill"] == "#150b06", "a black jaw over a light gap"
        assert o["paperJaw"] == 0, "the jaw pieces draw only in the shadow-puppet skin"


@needs_node
def test_the_closed_jaw_hides_its_gap_and_an_open_one_uncovers_it():
    r = js("""
const skin = B2M.SKINS['shadow-puppet'], ch = require(process.argv[1] + '/../cast/adult.json');
const box = (v) => { const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, breath: false, visemes: [{ t: 0, v }, { t: 9, v: 'rest' }] }, 0.5, { steps: 12 });
  const items = B2M.layout(ch, skin, p, { x: 0, y: 0, scale: 1 }), w = %s;
  const gap = w(items.find((i) => i.part === 'jawGap')), jaw = w(items.find((i) => i.part === 'jaw'));
  return { gapInside: gap.x0 >= jaw.x0 - 0.01 && gap.x1 <= jaw.x1 + 0.01 && gap.y0 >= jaw.y0 - 0.01 && gap.y1 <= jaw.y1 + 0.01, jawBottom: jaw.y1 }; };
console.log(JSON.stringify({ rest: box('rest'), ai: box('AI') }));
""" % WORLD)
    assert r["rest"]["gapInside"], "a shut jaw covers the gap completely"
    assert not r["ai"]["gapInside"], "an open jaw swings away from its gap, which shows as light"


# ---- a profile you can read ----------------------------------------------------------------------------------------------

@needs_node
def test_shadow_puppet_humans_have_a_profile_edge_nose_lips_chin_moustache_hem_and_fingers():
    adult, child = load("adult"), load("child")
    face = next(sh for p in adult["parts"] if p["id"] == "head" for sh in p["variants"]["shadow"]["shapes"] if sh["type"] == "poly" and sh["fill"] == "skin")
    front = sorted((pt for pt in face["pts"] if pt[0] >= 24 and pt[1] > -305), key=lambda pt: pt[1])
    dx = [b[0] - a[0] for a, b in zip(front, front[1:])]
    turns = sum(1 for a, b in zip(dx, dx[1:]) if a * b < 0)
    assert len(face["pts"]) >= 18 and turns >= 5, f"the adult's front edge (nose, moustache, lips, chin) changes direction {turns} times"
    assert max(pt[0] for pt in face["pts"]) >= 45 and min(pt[0] for pt in front if pt[1] < -277 and pt[1] > -285) < 40, "a nose that stands out from the brow"
    moustache = [pt for pt in face["pts"] if -266 < pt[1] < -258 and pt[0] > 38]
    assert moustache and max(pt[0] for pt in moustache) >= 40, "the moustache is a shape on the edge"
    head_child = next(p for p in child["parts"] if p["id"] == "head")["variants"]["shadow"]["shapes"]
    face_ell = next(sh for sh in head_child if sh["type"] == "ellipse" and sh["fill"] == "skin" and sh["r"][0] > 20)
    lips = next(sh for sh in head_child if sh["type"] == "ellipse" and sh["c"][0] > 28 and -150 < sh["c"][1] < -144)
    edge = face_ell["c"][0] + face_ell["r"][0] * (1 - ((lips["c"][1] - face_ell["c"][1]) / face_ell["r"][1]) ** 2) ** 0.5
    assert lips["c"][0] + lips["r"][0] > edge + 2, "the child's lips stand out from the face"
    assert len(head_child) >= 8 and any(sh["c"][1] > -135 for sh in head_child if sh["type"] == "ellipse" and sh["r"][0] < 12), "a chin"
    r = js("""
const skin = B2M.SKINS['shadow-puppet'], out = {};
for (const name of ['child', 'adult']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json');
  const items = B2M.layout(ch, skin, B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, breath: false }, 0, { steps: 12 }), { x: 0, y: 0, scale: 1 });
  out[name] = items.filter((i) => i.part === 'handN' && i.fill).length;
}
console.log(JSON.stringify(out));
""")
    assert r["child"] >= 6 and r["adult"] >= 6, "a hand with fingers and a thumb, not a ball"
    torso = next(sh for p in adult["parts"] if p["id"] == "torso" for sh in p["variants"]["shadow"]["shapes"] if sh["type"] == "poly")
    ys = sorted({pt[1] for pt in torso["pts"]})
    width = lambda y: max(pt[0] for pt in torso["pts"] if pt[1] == y) - min(pt[0] for pt in torso["pts"] if pt[1] == y)  # noqa: E731
    assert max(width(y) for y in ys[-3:]) > 1.35 * width(-192), "the kurta flares at the hem"
    assert len(next(p for p in adult["parts"] if p["id"] == "armN_up")["variants"]["shadow"]["shapes"]) == 2, "a sleeve with a cuff"
    assert any(sh["type"] == "poly" for p in adult["parts"] if p["id"] == "hip" for sh in p["variants"]["shadow"]["shapes"]), "the dhoti pleat hangs"


# ---- light scenery and tones ----------------------------------------------------------------------------------------------

@needs_node
def test_a_light_set_shape_stays_light_in_shadow_puppet_and_the_screen_tones_keep_figures_visible():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const scene = { width: 1920, height: 1080, skin: 'shadow-puppet', ground: 900, palette: { sky: '#aabbcc', ground: '#112233', hill1: '#010101', hill2: '#020202', sun: '#ffd166' },
  hills: [{ fill: 'hill1', pts: [[0, 600], [960, 500], [1920, 600]] }, { fill: 'hill2', pts: [[0, 700], [960, 640], [1920, 700]] }],
  set: [{ type: 'circle', c: [1500, 200], r: 80, fill: 'sun', layer: 'back', role: 'light' }, { type: 'circle', c: [300, 200], r: 60, fill: 'sun', layer: 'back' }, { type: 'rect', x: 100, y: 850, w: 80, h: 50, r: 0, fill: 'sun' }],
  cast: [{ id: 'k', character: 'child', x: 900, scale: 1.5, track: [{ t: 0, pose: 'idle' }] }] };
const items = B2M.createStage(scene, { child: ch }).items(1).filter((i) => i.kind === 'path');
const of = (part) => items.filter((i) => i.part === part).map((i) => i.fill);
console.log(JSON.stringify({ light: of('set0'), dark: of('set1'), rect: of('set2'), hill0: of('hill0'), hill1: of('hill1'), ground: of('ground'), screen: B2M.SKINS['shadow-puppet'].screen, sky: items.find((i) => i.part === 'sky').fill.stops }));
""")
    assert r["light"] == ["#fff4c2"], "the sun is light, not a black disc"
    assert r["dark"] == ["#150b06"] and r["rect"] == ["#150b06"], "other scenery is leather"
    tones = [r["hill0"][0], r["hill1"][0], r["ground"][0]]
    assert tones == ["#d98a35", "#bd6a22", "#a85a1c"] == [*r["screen"]["hills"], r["screen"]["ground"]], "the skin's own screen, not the palette's near-black"
    for tone in tones:
        assert contrast("#150b06", tone) >= 2.5, f"a black figure stands out against {tone}"
    assert all(contrast("#150b06", stop[1]) >= 4 for stop in r["sky"]), "and against the backlit sky"


def test_the_stage_check_warns_when_a_figure_is_close_in_tone_to_the_background_behind_it():
    dark = copy.deepcopy(GOOD)
    dark["skin"] = "flat-explainer"
    dark["palette"].update({"sky": "#1a1c28", "ground": "#1a1c28", "hill1": "#1c1e2a", "hill2": "#1b1d29"})
    dark["cast"] = [{"id": "bird", "character": "crow", "x": 900, "scale": 2.4, "facing": "left", "track": []}]
    dark["captions"], dark["set"] = [], []
    errors, warnings = cp.screen_problems(cp.resolve_scene(dark, EX09))
    assert errors == [] and any("bird (crow) is hard to see" in w and "contrast" in w and "change the palette or the skin" in w for w in warnings), warnings
    for skin in ("paper-cutout", "shadow-puppet", "cel-shaded", "motion-comic"):
        ok = copy.deepcopy(GOOD)
        ok["skin"] = skin
        assert not [w for w in cp.screen_problems(cp.resolve_scene(ok, EX09))[1] if "hard to see" in w], skin


# ---- the ground and the captions -------------------------------------------------------------------------------------------

@needs_node
def test_a_cast_member_with_no_y_stands_on_the_ground_top_so_its_feet_are_never_hidden():
    r = js("""
const out = {};
for (const name of ['child', 'adult', 'crow', 'tomato']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json');
  const scene = { width: 1920, height: 1080, skin: 'flat-explainer', ground: 820, palette: { sky: '#aabbcc', ground: '#889977' }, cast: [{ id: 'a', character: name, x: 900, scale: 1.4, track: [{ t: 0, pose: 'idle' }] }] };
  const items = B2M.createStage(scene, { [name]: ch }).items(0), ground = items.findIndex((i) => i.part === 'ground'), w = %s;
  const feet = items.map((it, n) => [it, n]).filter(([it]) => /^foot/.test(it.part) && it.kind === 'path' && it.fill);
  out[name] = { bottom: Math.round(Math.max(...feet.map(([it]) => w(it).y1))), drawnAfterGround: feet.every(([, n]) => n > ground), home: B2M.homeOf({ x: 1 }, scene).y };
}
console.log(JSON.stringify(out));
""" % WORLD)
    for name, o in r.items():
        assert o["home"] == 820 and o["drawnAfterGround"], name
        assert 815 <= o["bottom"] <= 824, f"{name}: the soles sit on the ground top (820), not below it: {o['bottom']}"


def test_feet_below_the_frame_are_an_error_and_feet_deep_in_the_ground_band_a_warning():
    low = copy.deepcopy(GOOD)
    low["cast"][0]["y"] = 1200
    errors = cp.screen_problems(cp.resolve_scene(low, EX09))[0]
    assert any("scene.cast[0]" in e and "below the bottom of the frame" in e and "leave it out to stand on the ground top (900)" in e for e in errors), errors
    deep = copy.deepcopy(GOOD)
    deep["cast"][0]["y"] = 1000
    assert any("deep inside the ground band" in w for w in cp.screen_problems(cp.resolve_scene(deep, EX09))[1])
    assert not cp.screen_problems(cp.resolve_scene(copy.deepcopy(GOOD), EX09))[1], "example 09 stands on the ground top and is silent"


@needs_node
def test_the_caption_moves_to_the_top_when_it_would_cover_a_character_and_stays_at_the_bottom_otherwise():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const make = (ground) => ({ width: 1920, height: 1080, skin: 'flat-explainer', ground, palette: { sky: '#aabbcc', ground: '#889977' },
  cast: [{ id: 'k', character: 'child', x: 900, scale: 1.9, track: [{ t: 0, pose: 'idle' }] }], captions: [{ from: 0, to: 5, text: 'Hey crow, that is my kite!' }] });
const rect = (ground, t) => { const items = B2M.createStage(make(ground), { child: ch }).items(t), cap = items.find((i) => i.part === 'caption' && i.kind === 'path'), q = B2M.pathBounds(cap.d); return { y0: q.y0, y1: q.y1, text: items.find((i) => i.kind === 'text').y }; };
const none = B2M.createStage(Object.assign(make(900), { captions: [] }), { child: ch }).items(1).some((i) => i.part === 'caption');
console.log(JSON.stringify({ ordinary: rect(900, 1), covered: rect(1040, 1), none }));
""")
    assert r["ordinary"]["y0"] >= 900, "the usual place is the bottom of the frame"
    assert r["covered"]["y1"] < 200 and r["covered"]["text"] < 200, "a caption that would cover the legs goes to the top"
    assert r["none"] is False


# ---- routing -----------------------------------------------------------------------------------------------------------------

def test_every_art_form_id_routes_to_its_form_however_it_is_spelled():
    forms = json.loads((SKILL / "references" / "art-forms.json").read_text(encoding="utf-8"))["forms"]
    for f in forms:
        spaced = f["id"].replace("-", " ")
        for spelling in (f["id"], spaced, spaced + "s", spaced.title(), f["id"].upper(), f["id"].replace("-", "  ")):
            got = art_route.route(f"A short film in {spelling} style")
            assert got["form"] == f["id"], f"{spelling!r} routed to {got['form']}"
    for brief in ("A shadow-puppet scene of a lost kite", "shadow puppets tell the story", "a film in shadow puppetry", "Shadow  Puppet theatre"):
        assert art_route.route(brief)["form"] == "shadow-puppet" and "none suggested" not in art_route.report(art_route.route(brief)), brief


# ---- walk keys -----------------------------------------------------------------------------------------------------------------

@needs_node
def test_a_walk_key_plants_the_feet_for_the_child_the_adult_and_the_tomato():
    r = js("""
const out = {};
for (const name of ['child', 'adult', 'tomato']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json'), scale = 1.6, dist = 900, seconds = 4;
  const steps = B2M.walkSteps(ch, dist, seconds, scale), P = 8 / steps, home = { x: 0, y: 900, flip: 1 };
  const track = { move: [{ t: 0, x: 100 }, { t: seconds, x: 100 + dist, walk: true, ease: 'in' }], blink: false, breath: false };
  const foot = (t) => { const p = B2M.pose(ch, track, t, { home, scale, smooth: true }), o = { x: 0, y: 900, scale };
    const hip = B2M.partPoint(ch, p, o, 'legN_up'), ank = B2M.partPoint(ch, p, o, 'footN'), len = Math.hypot(ank[0] - hip[0], ank[1] - hip[1]), want = ch.proportions.legLength * scale;
    return ank[0] + ((ank[0] - hip[0]) / len) * (want - len); };   // where the leg line meets the ground
  const body = (t) => B2M.pose(ch, track, t, { home, scale }).move.x;
  out[name] = { steps, stride: 4 * ch.proportions.legLength * Math.sin(28 * Math.PI / 180) * scale, planted: Math.abs(foot(0.75 * P) - foot(0.25 * P)), planted2: Math.abs(foot(1.75 * P) - foot(1.25 * P)),
    mid: body(2), speedAtStart: body(0.4) - body(0.3), speedAtEnd: body(3.7) - body(3.6), planted_speed: B2M.strideSpeed(ch, 'walk', steps) * scale };
}
console.log(JSON.stringify(out));
""")
    for name, o in r.items():
        assert o["planted"] < 0.05 * o["stride"] and o["planted2"] < 0.05 * o["stride"], f"{name}: the planted foot moved {o['planted']:.1f} px over a stance (a stride is {o['stride']:.0f})"
        assert abs(o["planted_speed"] - 225) < 0.5, "the cycle speed is the planted-feet speed for 900 px in 4 s"
        assert abs(o["mid"] - 550) < 0.5, "a walk key glides steadily, whatever ease the key says"
        assert abs(o["speedAtStart"] - o["speedAtEnd"]) < 1e-6


@needs_node
def test_a_walk_key_turns_the_character_to_face_the_way_it_walks_unless_a_key_says_otherwise():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), home = { x: 500, y: 900, flip: 1 };
const flip = (move, t) => B2M.pose(ch, { move }, t, { home, scale: 1 }).move.flip;
const legs = (move, t) => B2M.pose(ch, { move, blink: false, breath: false }, t, { home, scale: 1, smooth: true }).parts.legN_up.r;
const rest = legs([], 0);
const left = [{ t: 0, x: 900 }, { t: 2, x: 200, walk: true }], told = [{ t: 0, x: 900, facing: 'right' }, { t: 2, x: 200, walk: true }];
console.log(JSON.stringify({ left: flip(left, 1), right: flip([{ t: 0, x: 200 }, { t: 2, x: 900, walk: true }], 1), told: flip(told, 1), noWalk: flip([{ t: 0, x: 900 }, { t: 2, x: 200 }], 1),
  before: legs([{ t: 1, x: 900 }, { t: 3, x: 200, walk: true }], 0.5) - rest, during: [1.5, 1.7, 1.9, 2.1].map((t) => Math.round(legs([{ t: 1, x: 900 }, { t: 3, x: 200, walk: true }], t) * 10)), after: legs([{ t: 1, x: 900 }, { t: 3, x: 200, walk: true }], 3.4) - rest }));
""")
    assert r["left"] == -1 and r["right"] == 1 and r["told"] == 1 and r["noWalk"] == 1
    assert r["before"] == 0 and r["after"] == 0 and len(set(r["during"])) >= 3, "the legs move only during the walk"


def test_a_walk_that_needs_more_than_12_drawings_a_second_warns_that_it_looks_like_a_run():
    fast = copy.deepcopy(GOOD)
    fast["cast"][0]["track"]["move"] = [{"t": 0, "x": 100}, {"t": 1, "x": 1500, "walk": True}]
    warnings = cp.screen_problems(cp.resolve_scene(fast, EX09))[1]
    assert any("kid walks 0.0 s to 1.0 s" in w and "looks like a run" in w for w in warnings), warnings
    assert not [w for w in cp.screen_problems(cp.resolve_scene(copy.deepcopy(GOOD), EX09))[1] if "run" in w]


def test_the_scene_schema_accepts_walk_and_light_and_the_readme_recipes_are_valid_tracks():
    track = validate_scene.SCHEMA["$defs"]["track"]
    assert "walk" in track["properties"]["move"]["items"]["properties"] and "light" in validate_scene.SCHEMA["properties"]["set"]["items"]["properties"]["role"]["enum"]
    recipes = re.findall(r"### Recipe: ([^\n]+)\n.*?```json\n(.*?)```", README, re.S)
    assert [n for n, _ in recipes] == ["walk in and stop", "land on a perch", "jump off and leave", "turn to face"]
    for name, body in recipes:
        assert validate.check(json.loads(body), track, f"recipe {name}") == [], name
        member = {"id": "a", "character": "child", "x": 560, "scale": 1.5, "track": json.loads(body)}
        s = copy.deepcopy(GOOD)
        s["cast"] = [member]
        s["captions"] = []
        assert validate_scene.validate_scene(s, EX09) == [], name
    jump_off = json.loads(recipes[2][1])
    assert any(k.get("walk") for k in jump_off["move"]) and all(k["t"] >= 0 for k in jump_off["move"])


@needs_node
def test_the_jaw_gap_is_a_small_wedge_at_the_front_of_the_face_for_every_mouth_shape():
    """The light gap a jaw uncovers must read as a mouth, never as the head splitting: it stays in the front 30% of the head's width."""
    r = js("""
const skin = B2M.SKINS['shadow-puppet'], out = {}, w = %s;
const box = (items, part) => { let b = null; items.filter((i) => i.part === part && i.kind === 'path' && i.fill).forEach((i) => { const q = w(i);
  b = b ? { x0: Math.min(b.x0, q.x0), y0: Math.min(b.y0, q.y0), x1: Math.max(b.x1, q.x1), y1: Math.max(b.y1, q.y1) } : q; }); return b; };
for (const name of ['child', 'adult', 'tomato']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json');
  out[name] = {};
  B2M.VISEMES.forEach((v) => {
    const p = B2M.pose(ch, { keys: [{ t: 0, pose: 'idle' }], blink: false, breath: false, visemes: [{ t: 0, v }, { t: 9, v: 'rest' }] }, 0.5, { steps: 12 });
    const items = B2M.layout(ch, skin, p, { x: 0, y: 0, scale: 1 }), head = box(items, 'head'), gap = box(items, 'jawGap'), jaw = box(items, 'jaw');
    out[name][v] = { fromFront: (head.x1 - gap.x0) / (head.x1 - head.x0), gapW: gap.x1 - gap.x0, gapH: gap.y1 - gap.y0, jawFromFront: (head.x1 - jaw.x0) / (head.x1 - head.x0), headW: head.x1 - head.x0 };
  });
}
console.log(JSON.stringify(out));
""" % WORLD)
    for name, shapes in r.items():
        for v, o in shapes.items():
            assert o["fromFront"] <= 0.30, f"{name} {v}: the gap reaches back {o['fromFront']:.0%} of the head width from the front edge (allowed 30%)"
            assert o["gapW"] < 0.35 * o["headW"] and o["gapH"] < 0.25 * o["headW"], f"{name} {v}: the gap is a small wedge, not a slash ({o['gapW']:.0f} x {o['gapH']:.0f})"
        assert shapes["AI"]["fromFront"] > 0.05, f"{name}: the gap sits behind the front edge, at the mouth corner, not on the profile"
