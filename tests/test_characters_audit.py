"""Regression tests for the independent audit: each one pins a root cause (facing after a walk, overlapping words,
path traversal in image parts, Devanagari, user characters in scenes, caption scaling, cache growth, WAV drift ...)."""
from __future__ import annotations

import copy
import os
import shutil
import struct
import wave
from array import array

from characters_common import *  # noqa: F401,F403
import validate_scene  # noqa: E402

GOOD = json.loads((EX09 / "scene.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(SCRIPTS))
import character_sheet as sheet_script  # noqa: E402
import standin_voice  # noqa: E402


def run_py(script: str, *args: str):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, encoding="utf-8")


# ---- 1. facing after a walk ------------------------------------------------------------------------------------------------

@needs_node
def test_facing_carries_forward_after_a_walk_and_a_glide_until_a_key_sets_it():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), home = { x: 500, y: 900, flip: 1 };
const flip = (move, t) => B2M.pose(ch, { move }, t, { home, scale: 1 }).move.flip;
const walk = [{ t: 0, x: 800 }, { t: 2, x: 300, walk: true }];
const glide = [{ t: 0, x: 800, facing: 'left' }, { t: 2, x: 300 }];
const turn = [{ t: 0, x: 800 }, { t: 2, x: 300, walk: true }, { t: 4, facing: 'right' }];
console.log(JSON.stringify({ walk: [1, 1.99, 2, 2.01, 2.5, 6].map((t) => flip(walk, t)), glide: [1, 1.99, 2, 2.5, 6].map((t) => flip(glide, t)), turn: [3, 3.99, 4, 5].map((t) => flip(turn, t)) }));
""")
    assert r["walk"] == [-1] * 6, "after the walk ends the child still faces the way it walked"
    assert r["glide"] == [-1] * 5, "a facing set on an earlier key holds after the last key"
    assert r["turn"] == [-1, -1, 1, 1], "until a key sets facing"


# ---- 2. overlapping and unsorted words, unsorted visemes ------------------------------------------------------------------------

def test_overlapping_words_never_make_a_mouth_track_go_backwards():
    track = lipsync.build_track([{"text": "hello", "start": 0.0, "end": 1.0}, {"text": "world", "start": 0.5, "end": 1.2}], 30)
    times = [k["t"] for k in track]
    assert times == sorted(times) and len(set(times)) == len(times), f"times must rise strictly: {times}"
    assert track[-1]["v"] == "rest" and track[-1]["t"] >= 1.2 - 1 / 30
    assert any(k["v"] != "rest" and k["t"] >= 0.5 for k in track), "world is still spoken"
    shuffled = lipsync.build_track([{"text": "world", "start": 0.5, "end": 1.2}, {"text": "hello", "start": 0.0, "end": 1.0}], 30)
    assert shuffled == track, "word order in the file does not matter"
    inside = lipsync.build_track([{"text": "hello", "start": 0.0, "end": 2.0}, {"text": "no", "start": 0.4, "end": 0.6}], 30)
    assert [k["t"] for k in inside] == sorted(k["t"] for k in inside)


def test_the_tidy_step_refuses_a_track_that_goes_backwards():
    with pytest.raises(ValueError, match="time order"):
        lipsync._tidy([(0.5, "AI"), (0.2, "E")], 1.0, 30)


@needs_node
def test_the_rig_sorts_hand_written_visemes_so_a_shuffled_track_reads_the_same():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const sorted = [{ t: 0.2, v: 'E' }, { t: 0.6, v: 'AI' }, { t: 1.0, v: 'O' }, { t: 1.5, v: 'rest' }], shuffled = [sorted[2], sorted[0], sorted[3], sorted[1]];
const at = (v, t) => B2M.pose(ch, { visemes: v, blink: false }, t, { steps: 12 }).viseme;
console.log(JSON.stringify([0.3, 0.7, 1.1, 1.6].map((t) => [at(sorted, t), at(shuffled, t)])));
""")
    assert all(a == b for a, b in r) and [a for a, _ in r] == ["E", "AI", "O", "rest"], r


def test_the_scene_validator_rejects_unsorted_visemes_with_a_clear_message():
    s = copy.deepcopy(GOOD)
    s["cast"][0]["track"]["visemes"] = [{"t": 1.5, "v": "AI"}, {"t": 1.2, "v": "E"}]
    found = [p for p in validate_scene.validate_scene(s, EX09) if "visemes" in p and "time order" in p]
    assert found and "scene.cast[0].track.visemes" in found[0] and "1.2" in found[0] and "1.5" in found[0], found


# ---- 3. image parts: traversal, file type, validation in load_file ---------------------------------------------------------------

def image_character(tmp_path, src: str, payload: bytes | None = None, *, name="char"):
    folder = tmp_path / name
    shutil.copytree(DEMO / "parts", folder / "parts")
    data = json.loads((DEMO / "tin-bot.json").read_text(encoding="utf-8"))
    data["parts"][0]["image"]["src"] = src
    (folder / "tin.json").write_text(json.dumps(data), encoding="utf-8")
    if payload is not None:
        target = (folder / src).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return folder / "tin.json"


def test_image_parts_cannot_reach_outside_the_characters_folder(tmp_path):
    png = (DEMO / "parts" / "head.png").read_bytes()
    escape = image_character(tmp_path, "../outside.png", png)
    with pytest.raises(ValueError, match="inside"):
        cp.load_file(escape)
    assert any("inside" in e for e in validate.validate_character(json.loads(escape.read_text(encoding="utf-8")), escape.parent)), "the validator says so too"
    absolute = image_character(tmp_path, str(tmp_path / "abs.png"), png, name="abs")
    with pytest.raises(ValueError):
        cp.load_file(absolute)


def test_image_parts_must_really_be_png_or_webp(tmp_path):
    fake = image_character(tmp_path, "parts/fake.png", b"<html>not a picture</html>", name="fake")
    with pytest.raises(ValueError, match="not a PNG or WebP"):
        cp.load_file(fake)
    assert any("not a PNG or WebP" in e for e in validate.validate_character(json.loads(fake.read_text(encoding="utf-8")), fake.parent))
    webp = image_character(tmp_path, "parts/real.webp", b"RIFF\x04\x00\x00\x00WEBPVP8 ", name="webp")
    assert cp.load_file(webp)["parts"][0]["image"]["src"].startswith("data:image/webp;base64,")
    good = image_character(tmp_path, "parts/head.png", None, name="good")
    assert cp.load_file(good)["parts"][0]["image"]["src"].startswith("data:image/png;base64,")


def test_only_png_and_webp_data_uris_are_accepted(tmp_path):
    for bad in ("data:text/html;base64,PGI+", "data:image/svg+xml;base64,PHN2Zz4=", "data:image/gif;base64,R0lGOD", "data:image/png,rawbytes"):
        path = image_character(tmp_path, bad, None, name="d" + str(abs(hash(bad)) % 9999))
        with pytest.raises(ValueError):
            cp.load_file(path)
        assert validate.validate_character(json.loads(path.read_text(encoding="utf-8")), path.parent), bad


def test_load_file_validates_the_character_before_using_it(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"id": "x", "palette": {}, "proportions": {"height": 1, "legLength": 1}, "parts": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="problem"):
        cp.load_file(broken)


# ---- 4. ids that reach a path ----------------------------------------------------------------------------------------------------

def test_a_character_id_cannot_escape_the_output_folder(tmp_path, monkeypatch):
    data = json.loads((KIT / "cast" / "child.json").read_text(encoding="utf-8"))
    data["id"] = "../../escape"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "deep" / "out"
    monkeypatch.setattr(sheet_script, "snapshot", lambda project, count: [(DEMO / "parts" / "head.png")] * count)
    monkeypatch.setattr(cp, "prepare_project", lambda *a, **k: None)
    monkeypatch.setattr(sheet_script, "build_page", lambda *a, **k: None)
    with pytest.raises(SystemExit) as err:
        sheet_script.main(["--file", str(bad), "--skin", "flat-explainer", "--out", str(out)])
    assert err.value.code not in (0, None)
    assert not list(tmp_path.rglob("escape*")), "nothing was written outside --out"
    for odd in ("../x", "a/b", "Up", "-x", ""):
        with pytest.raises(SystemExit):
            sheet_script.main(["--character", odd, "--skin", "flat-explainer", "--out", str(out)])
    with pytest.raises(SystemExit):
        cp.load_cast(["../../etc/passwd"])


# ---- 5. Devanagari and accented Latin -------------------------------------------------------------------------------------------

def test_devanagari_words_get_mouth_shapes():
    def shapes(word):
        return [k["v"] for k in lipsync.build_track([{"text": word, "start": 0.0, "end": 0.8}], 30) if k["v"] != "rest"]
    namaste = shapes("नमस्ते")
    assert namaste and "MBP" in namaste and "E" in namaste and set(namaste) <= set(lipsync.VISEMES), namaste
    assert shapes("पापा")[0] == "MBP" and shapes("फल")[0] == "FV" and "L" in shapes("फल") and shapes("वह")[0] == "FV"
    assert "O" in shapes("तो") and "U" in shapes("सुनो") and shapes("आम")[:2] == ["AI", "MBP"]
    assert shapes("क्या") and "AI" in shapes("क्या"), "a virama joins the consonants; the vowel sign still shows"
    assert shapes("हिन्दी") and "E" in shapes("हिन्दी")


def test_accented_latin_letters_are_folded_not_dropped():
    cafe = [k["v"] for k in lipsync.build_track([{"text": "café", "start": 0, "end": 0.6}], 30) if k["v"] != "rest"]
    plain = [k["v"] for k in lipsync.build_track([{"text": "cafe", "start": 0, "end": 0.6}], 30) if k["v"] != "rest"]
    assert cafe and cafe == plain
    shapes = lambda w: [k["v"] for k in lipsync.build_track([{"text": w, "start": 0, "end": 0.9}], 30)]  # noqa: E731
    assert shapes("señor") == shapes("senor") and shapes("über") == shapes("uber") and shapes("naïve") == shapes("naive")


def test_words_with_no_shapes_are_reported_and_an_empty_track_is_an_error_that_suggests_wav(tmp_path):
    skipped: list[str] = []
    track = lipsync.build_track([{"text": "hello", "start": 0, "end": 0.5}, {"text": "123", "start": 0.6, "end": 0.9}, {"text": "—", "start": 1.0, "end": 1.2}], 30, skipped=skipped)
    assert track and skipped == ["123", "—"]
    words = tmp_path / "w.json"
    words.write_text(json.dumps([{"text": "123", "start": 0, "end": 1}, {"text": "?!", "start": 1, "end": 2}]), encoding="utf-8")
    done = run_py("lipsync.py", str(words))
    assert done.returncode != 0 and "--wav" in done.stderr and "123" in done.stderr
    mixed = tmp_path / "m.json"
    mixed.write_text(json.dumps([{"text": "hello", "start": 0, "end": 0.5}, {"text": "123", "start": 0.6, "end": 0.9}]), encoding="utf-8")
    ok = run_py("lipsync.py", str(mixed))
    assert ok.returncode == 0 and "warning" in ok.stderr and '"123"' in ok.stderr and json.loads(ok.stdout)


# ---- 6. user characters in scenes ---------------------------------------------------------------------------------------------------

def bot_scene():
    s = copy.deepcopy(GOOD)
    s["cast"] = [{"id": "bot", "character": "tin-bot", "x": 700, "scale": 1.6, "track": {"keys": [{"t": 0, "pose": "idle"}, {"t": 3, "pose": "wave"}], "move": [{"t": 0, "x": 300}, {"t": 4, "x": 900, "walk": True}]}}]
    s["captions"] = []
    return s


def test_a_scene_can_use_a_character_from_a_file_and_says_how_when_it_cannot(monkeypatch, tmp_path):
    monkeypatch.setattr(cp, "vendor", lambda project, three=False: (project / "vendor").mkdir(exist_ok=True))
    scene_file = tmp_path / "scene.json"
    scene_file.write_text(json.dumps(bot_scene()), encoding="utf-8")
    with pytest.raises(cp.SceneError) as err:
        cp.build_scene_project(scene_file, tmp_path / "p0")
    assert any("tin-bot" in p and "--character-file" in p for p in err.value.problems), err.value.problems
    scene = cp.build_scene_project(scene_file, tmp_path / "p1", character_files=[DEMO / "tin-bot.json"])
    cast_js = (tmp_path / "p1" / "characters" / "cast.js").read_text(encoding="utf-8")
    assert "tin-bot" in cast_js and "data:image/png;base64," in cast_js and '"src":"parts/' not in cast_js and '"src":".' not in cast_js
    assert scene["cast"][0]["character"] == "tin-bot"
    clash = json.loads((DEMO / "tin-bot.json").read_text(encoding="utf-8"))
    clash["id"] = "child"
    (tmp_path / "clash.json").write_text(json.dumps(clash), encoding="utf-8")
    shutil.copytree(DEMO / "parts", tmp_path / "parts", dirs_exist_ok=True)
    with pytest.raises(cp.SceneError, match="starter cast"):
        cp.build_scene_project(scene_file, tmp_path / "p2", character_files=[tmp_path / "clash.json"])
    assert "--character-file" in run_py("character_project.py", "--help").stdout


def test_the_scene_validator_knows_extra_characters_and_checks_their_props():
    extra = {"tin-bot": json.loads((DEMO / "tin-bot.json").read_text(encoding="utf-8"))}
    assert validate_scene.validate_scene(bot_scene(), EX09, extra) == []
    bad = bot_scene()
    bad["cast"][0]["track"]["props"] = ["prop_kite"]
    assert any("not a prop of tin-bot" in p for p in validate_scene.validate_scene(bad, EX09, extra))


# ---- 7. captions that scale and wrap ----------------------------------------------------------------------------------------------

LONG = "Finders keepers, little one, and that is the whole story of the kite that never came back to the child"

CAPTION_JS = """
const ch = require(process.argv[1] + '/../cast/child.json'), out = {};
for (const [W, H] of [[1920, 1080], [1080, 1920], [3840, 2160]]) {
  const scene = { width: W, height: H, skin: 'flat-explainer', ground: Math.round(H * 0.83), palette: { sky: '#aabbcc', ground: '#889977' },
    cast: [{ id: 'k', character: 'child', x: W * 0.2, scale: 1.2 * H / 1080 * (W < H ? 0.6 : 1), track: [{ t: 0, pose: 'idle' }] }], captions: [{ from: 0, to: 5, text: %s }] };
  const items = B2M.createStage(scene, { child: ch }).items(1), texts = items.filter((i) => i.kind === 'text'), box = items.find((i) => i.part === 'caption' && i.kind === 'path');
  const q = box && B2M.pathBounds(box.d);
  out[W + 'x' + H] = { lines: texts.length, sizes: texts.map((i) => parseFloat(i.font.match(/(\\d+(?:\\.\\d+)?)px/)[1])), chars: texts.map((i) => i.text.length), xs: texts.map((i) => i.x), box: q };
}
console.log(JSON.stringify(out));
"""


@needs_node
def test_captions_wrap_scale_with_the_frame_and_stay_in_the_safe_zone():
    r = js(CAPTION_JS % json.dumps(LONG))
    for size, o in r.items():
        w, h = map(int, size.split("x"))
        s = min(w, h) / 1080
        assert o["lines"] >= 2, f"{size}: a long caption wraps"
        assert all(abs(px - 40 * s) < 1 for px in o["sizes"]), f"{size}: font scales with the frame: {o['sizes']}"
        assert all(c * 0.6 * px <= w * 0.92 for c, px in zip(o["chars"], o["sizes"])), f"{size}: every line fits the frame width"
        assert o["box"]["x0"] >= 0 and o["box"]["x1"] <= w and o["box"]["y0"] >= 0 and o["box"]["y1"] <= h, f"{size}: the box is inside the frame"
        if h > w:
            assert o["box"]["y0"] >= 0.15 * h - 1 and o["box"]["y1"] <= 0.65 * h + 1, "9:16: inside the platform's vertical safe zone"
            assert o["box"]["x0"] >= 64 * w / 1080 - 1 and o["box"]["x1"] <= w - 192 * w / 1080 + 1, "and clear of the side buttons"


def test_a_caption_too_long_for_two_lines_gets_a_warning_with_the_number_of_lines():
    s = copy.deepcopy(GOOD)
    s["captions"] = [{"from": 1, "to": 3, "text": "word " * 60}, {"from": 4, "to": 5, "text": "Short one."}]
    warnings = cp.screen_problems(cp.resolve_scene(s, EX09))[1]
    assert any("scene.captions[0]" in w and "lines" in w and "two" in w for w in warnings) and not any("scene.captions[1]" in w for w in warnings), warnings
    assert not [w for w in cp.screen_problems(cp.resolve_scene(copy.deepcopy(GOOD), EX09))[1] if "caption" in w]


# ---- 8. shadow rods ---------------------------------------------------------------------------------------------------------------

@needs_node
def test_shadow_puppet_rods_reach_the_bottom_of_the_frame_at_any_size():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json'), out = {};
for (const [W, H] of [[1920, 1080], [1080, 1920], [3840, 2160], [640, 360]]) {
  const scene = { width: W, height: H, skin: 'shadow-puppet', ground: Math.round(H * 0.83), palette: { sky: '#aabbcc', ground: '#889977' }, cast: [{ id: 'k', character: 'child', x: W / 2, scale: H / 1080, track: [{ t: 0, pose: 'point' }] }] };
  const rods = B2M.createStage(scene, { child: ch }).items(1).filter((i) => i.part === 'rod');
  out[W + 'x' + H] = rods.map((i) => Math.max(...B2M.parsePath(i.d).flatMap((s) => s.pts.map((p) => p[1]))));
}
console.log(JSON.stringify(out));
""")
    for size, ends in r.items():
        h = int(size.split("x")[1])
        assert len(ends) >= 2 and all(y >= h for y in ends), f"{size}: rods end at {ends}, the frame is {h} tall"
        assert all(y <= h * 1.2 for y in ends), "and do not run on for ever"


# ---- 9. caches stay bounded -------------------------------------------------------------------------------------------------------

@needs_node
def test_the_path_caches_stay_bounded_over_two_thousand_frames():
    r = js("""
const ch = require(process.argv[1] + '/../cast/child.json');
const scene = { width: 640, height: 360, skin: 'line-art', ground: 300, palette: { sky: '#ffffff', ground: '#dddddd' }, cast: [{ id: 'k', character: 'child', x: 300, scale: 0.5,
  track: { keys: [{ t: 0, pose: 'idle' }, { t: 100, pose: 'wave' }], layers: [{ cycle: 'talk', from: 0, to: 200 }], visemes: [{ t: 0, v: 'AI' }, { t: 100, v: 'rest' }] } }], captions: [] };
const stage = B2M.createStage(scene, { child: ch }); const sizes = [];
for (let f = 0; f < 2000; f++) { stage.items(f / 10); if (f %% 500 === 499) sizes.push(B2M.cacheStats()); }
for (let i = 0; i < 5000; i++) B2M.parsePath('M' + i + ' 0L' + i + ' 1Z');
console.log(JSON.stringify({ sizes, after: B2M.cacheStats() }));
""".replace("%%", "%"))
    for stats in [*r["sizes"], r["after"]]:
        assert stats["parsed"] <= 1000 and stats["shapes"] <= 1000, stats
    assert r["sizes"][-1]["parsed"] == r["sizes"][0]["parsed"] or r["sizes"][-1]["parsed"] <= 1000


# ---- 10. WAV fallback timing ----------------------------------------------------------------------------------------------------------

def test_the_wav_fallback_does_not_drift_over_ten_minutes_at_22050_hz_and_60_fps():
    rate, fps, minutes = 22050, 60, 10
    samples = array("h", bytes(2 * rate * 60 * minutes))
    start = int(599.0 * rate)
    burst = array("h", [20000, -20000] * (rate // 4))
    samples[start:start + len(burst)] = burst
    track = lipsync.amplitude_samples(samples, rate, fps)
    first = next(k["t"] for k in track if k["v"] != "rest")
    assert abs(first - 599.0) <= 1.5 / fps, f"the burst starts at 599.0 s but the track opens at {first:.3f} s"
    end = next(k["t"] for k in track if k["t"] > first and k["v"] == "rest")
    assert abs(end - 599.5) <= 2.5 / fps, end
    assert all(b["t"] > a["t"] for a, b in zip(track, track[1:]))


# ---- 11. one set of helpers in the kit ----------------------------------------------------------------------------------------------------

@needs_node
def test_the_kit_exports_the_walk_and_colour_helpers_the_scene_check_uses():
    r = js("""
console.log(JSON.stringify({ walkLayers: typeof B2M.walkLayers, contrast: typeof B2M.contrast, luminance: typeof B2M.luminance, report: typeof B2M.sceneReport, ratio: B2M.contrast('#000000', '#ffffff'), same: B2M.contrast('#336699', '#336699') }));
""")
    assert (r["walkLayers"], r["contrast"], r["luminance"], r["report"]) == ("function",) * 4
    assert abs(r["ratio"] - 21) < 0.01 and abs(r["same"] - 1) < 1e-9


def test_the_contrast_warning_samples_across_the_scene_and_names_the_background_that_failed():
    s = copy.deepcopy(GOOD)
    s["skin"] = "flat-explainer"
    s["palette"].update({"sky": "#f4f4f4", "ground": "#f4f4f4", "hill1": "#15161c", "hill2": "#f4f4f4"})
    s["hills"] = [{"fill": "hill1", "pts": [[1100, 900], [1100, 200], [1920, 200], [1920, 900]]}]   # a dark cliff on the right
    s["set"], s["captions"] = [], []
    s["cast"] = [{"id": "bird", "character": "crow", "x": 300, "scale": 2.0, "facing": "right", "track": {"move": [{"t": 0, "x": 300}, {"t": 12, "x": 1700, "walk": True}]}}]
    warnings = [w for w in cp.screen_problems(cp.resolve_scene(s, EX09))[1] if "hard to see" in w]
    assert len(warnings) == 1, warnings
    w = warnings[0]
    assert "bird (crow)" in w and "hill0" in w and "#15161c" in w and re.search(r"at \d+(\.\d)? s", w), w
    assert float(re.search(r"at (\d+(?:\.\d)?) s", w).group(1)) > 5, "it fails only once the bird is in front of the dark hill"


def test_character_project_no_longer_carries_its_own_copy_of_the_walk_and_colour_maths():
    code = (SCRIPTS / "character_project.py").read_text(encoding="utf-8")
    assert "Math.pow((v + 0.055)" not in code and "walks.push" not in code and "hexToRgb" not in code


# ---- 12. blinking ------------------------------------------------------------------------------------------------------------------------

@needs_node
def test_blinks_come_every_2_5_to_5_5_seconds():
    r = js("""
const out = {};
for (const name of ['child', 'adult', 'crow', 'tomato']) {
  const ch = require(process.argv[1] + '/../cast/' + name + '.json'), starts = []; let was = 0;
  for (let t = 0; t < 900; t += 0.02) { const b = B2M.pose(ch, [{ t: 0, pose: 'idle' }], t).blink; if (b > 0 && was === 0) starts.push(t); was = b; }
  const gaps = starts.slice(1).map((s, i) => s - starts[i]);
  out[name] = { n: starts.length, min: Math.min(...gaps), max: Math.max(...gaps) };
}
console.log(JSON.stringify(out));
""")
    for name, o in r.items():
        assert o["min"] >= 2.5 - 0.05 and o["max"] <= 5.5 + 0.05 and o["n"] > 150, f"{name}: gaps {o['min']:.2f} to {o['max']:.2f} s"
    assert "2.5 to 5.5 s" in "".join(js("console.log(JSON.stringify(B2M.CYCLE_INFO.blink))").split("\\")), "the table says what the code does"


# ---- 13. one colour list -------------------------------------------------------------------------------------------------------------------

def test_the_validators_share_one_list_of_built_in_colours():
    names = set(js("console.log(JSON.stringify(Object.keys(B2M.DEFAULT_PALETTE)))"))
    assert set(validate.BUILTIN_COLOURS) == set(validate_scene.BUILTIN_COLOURS) == names and "lip" in validate.BUILTIN_COLOURS
    ch = json.loads((KIT / "cast" / "child.json").read_text(encoding="utf-8"))
    ch["parts"][0]["shapes"] = [{"type": "circle", "c": [0, 0], "r": 3, "fill": "lip"}]
    assert validate.validate_character(ch) == []


# ---- 14. routing ---------------------------------------------------------------------------------------------------------------------------------

def test_the_router_names_the_kit_for_character_briefs_only():
    for brief in ("A chart that says revenue doubled, with at most 40 characters per line", "Our dashboard speaks volumes: 12 characters in the title",
                  "Show the characters per second metric", "A lyric video where the singer says goodbye", "Talking points for the keynote, as kinetic type",
                  "The title card says: Launch Day", "Explain a password that needs 8 characters"):
        assert art_route.route(brief)["kit"] is None, brief
    for brief in ("Two characters talk about a lost kite", "A short story with a child and a crow", "The child says \"hey\" to the crow", "A talking tomato chef explains the recipe",
                  "A mascot waves and speaks to the viewer", "A dialogue between a man and a robot", "An animated story about a fox who talks to the moon"):
        assert art_route.route(brief)["kit"] == "characters/README-CHARACTERS.md", brief


# ---- 15. example 09's brief and scene agree ------------------------------------------------------------------------------------------------

def test_example_09_brief_does_not_promise_a_hold_the_scene_does_not_keep():
    brief = (EX09 / "BRIEF.md").read_text(encoding="utf-8")
    duration = GOOD["duration"]
    if "hold still" in brief:
        assert all(layer.get("to", duration) <= duration - 1.5 for m in GOOD["cast"] for layer in m["track"].get("layers", [])), "the brief says the last 1.5 s hold still, but a cycle runs to the end"
    waving = [layer for m in GOOD["cast"] for layer in m["track"].get("layers", []) if layer["cycle"] == "wave"]
    assert not waving or "hold still" not in brief or max(layer["to"] for layer in waving) <= duration - 1.5


# ---- 16. word files that are not lists of objects -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("content", ['[1]', '{"words": [1, 2]}', '"words"', '3', '[{"text": "hi", "start": "a", "end": 1}]', '[null]', '{"segments": [{"words": [5]}]}'])
def test_word_files_with_the_wrong_shape_give_a_clean_exit_2_not_a_traceback(tmp_path, content):
    bad = tmp_path / "w.json"
    bad.write_text(content, encoding="utf-8")
    for script, args in (("lipsync.py", [str(bad)]), ("standin_voice.py", [str(bad), str(tmp_path / "o.wav")])):
        done = run_py(script, *args)
        assert done.returncode == 2 and "Traceback" not in done.stderr and script in done.stderr, (script, done.stderr[-300:])


# ---- 17. stacked captions, draw order by the current y ---------------------------------------------------------------------------------------------

@needs_node
def test_overlapping_captions_are_both_shown_and_the_cast_is_drawn_back_to_front_by_current_y():
    r = js("""
const child = require(process.argv[1] + '/../cast/child.json'), crow = require(process.argv[1] + '/../cast/crow.json');
const scene = { width: 1920, height: 1080, skin: 'flat-explainer', ground: 900, palette: { sky: '#aabbcc', ground: '#889977' },
  cast: [{ id: 'a', character: 'child', x: 500, scale: 1.2, track: [{ t: 0, pose: 'idle' }] }, { id: 'b', character: 'crow', x: 900, scale: 1.2, track: { move: [{ t: 0, y: 700 }, { t: 4, y: 1000, ease: 'linear' }] } }],
  captions: [{ from: 0, to: 5, text: 'First line' }, { from: 2, to: 6, text: 'Second line' }] };
const stage = B2M.createStage(scene, { child, crow });
const order = (t) => { const parts = stage.items(t).map((i) => i.part); return parts.indexOf('tail') < parts.indexOf('handN') ? 'crow first' : 'child first'; };
const texts = (t) => stage.items(t).filter((i) => i.kind === 'text').map((i) => i.text);
console.log(JSON.stringify({ early: order(0.5), late: order(3.5), both: texts(3), one: texts(1), none: texts(7) }));
""")
    assert r["early"] == "crow first" and r["late"] == "child first", "the crow crosses in front of the child as its y passes the child's"
    assert r["both"] == ["First line", "Second line"] and r["one"] == ["First line"] and r["none"] == []


# ---- 18. Windows vendoring -------------------------------------------------------------------------------------------------------------------------

def test_windows_vendors_libraries_with_a_powershell_script_that_pins_the_same_versions():
    sh = (SCRIPTS / "vendor_libs.sh").read_text(encoding="utf-8")
    ps = (SCRIPTS / "vendor_libs.ps1").read_text(encoding="utf-8")
    for sh_name, ps_name in (("GSAP_VERSION", "GsapVersion"), ("THREE_VERSION", "ThreeVersion"), ("FONT_VERSION", "FontVersion")):
        pinned = re.search(rf'{sh_name}="([^"]+)"', sh).group(1)
        assert re.search(rf'\${ps_name}\s*=\s*"{re.escape(pinned)}"', ps), f"{ps_name} must pin {pinned} like the bash script"
    for needed in ("param(", "[switch]$Three", "$Fonts", "gsap.min.js", "three.module.js", "fonts.css", "npm pack"):
        assert needed in ps, needed
    posix = cp.vendor_command(Path("proj"), True, windows=False)
    win = cp.vendor_command(Path("proj"), True, windows=True)
    assert posix[0] == "bash" and posix[1].endswith("vendor_libs.sh") and "--three" in posix
    assert "powershell" in win[0].lower() and "-File" in win and any(a.endswith("vendor_libs.ps1") for a in win) and "-Three" in win and "-Project" in win
    assert "-Three" not in cp.vendor_command(Path("proj"), False, windows=True)
    assert cp.vendor_command(Path("p"), False)[0] == ("powershell" if os.name == "nt" else "bash"), "the default follows the operating system"
