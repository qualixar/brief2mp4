"""Character kit scene files and docs: the scene schema and its messages, absolute move positions, facing, the
off-screen check, the stand-in voice, and a README that matches the code."""
from __future__ import annotations

import copy
import wave

from characters_common import *  # noqa: F401,F403
import validate_scene  # noqa: E402  (characters/ is on sys.path through characters_common)

README = (KIT / "README-CHARACTERS.md").read_text(encoding="utf-8")
GOOD = json.loads((EX09 / "scene.json").read_text(encoding="utf-8"))


def scene(**edit):
    s = copy.deepcopy(GOOD)
    for dotted, value in edit.items():
        node = s
        parts = dotted.split("__")
        for p in parts[:-1]:
            node = node[int(p)] if p.isdigit() else node[p]
        node[int(parts[-1]) if parts[-1].isdigit() else parts[-1]] = value
    return s


def problems(s, base=EX09):
    return validate_scene.validate_scene(s, base)


# ---- the scene schema and its messages ---------------------------------------------------------------------------

def test_example_09_is_a_valid_scene():
    assert problems(GOOD) == []


def test_every_problem_names_the_field_and_says_what_is_allowed():
    cases = [
        (scene(skin="papper"), "scene.skin", "Allowed: paper-cutout"),
        (scene(cast__1__track__keys__2__pose="wavee"), "scene.cast[1].track.keys[2].pose", "Allowed: idle, wave"),
        (scene(cast__0__x="left"), "scene.cast[0].x", "expected number, got string"),
        (scene(palette__sun="yellow"), "scene.palette.sun", "a colour like #f6d7a7"),
        (scene(cast__0__character="crw"), "scene.cast[0].character", "Allowed: adult, child, crow, tomato"),
        (scene(cast__0__facing="up"), "scene.cast[0].facing", "Allowed: left, right"),
        (scene(hills__0__fill="hil1"), "scene.hills[0].fill", "Palette keys:"),
        (scene(width=10), "scene.width", "below the minimum of 64"),
        (scene(duration=0), "scene.duration", "must be above 0"),
        (scene(cast__1__id="kid"), "scene.cast[1].id", "used twice"),
        (scene(captions__0__to=1.0), "scene.captions[0]", "'to' (1.0) must be after 'from'"),
        (scene(cast__0__track__visemesFrom__words="nope.json"), "scene.cast[0].track.visemesFrom.words", "not found"),
        (scene(cast__0__track__props=["prop_sword"]), "scene.cast[0].track.props[0]", "Allowed: prop_kite"),
        (scene(cast__1__track__props=["prop_x"]), "scene.cast[1].track.props[0]", "no props"),
    ]
    for bad, field, said in cases:
        found = [p for p in problems(bad) if field in p and said in p]
        assert found, f"{field} / {said!r} not reported; got {problems(bad)}"


def test_unknown_fields_missing_fields_and_typos_are_caught_with_the_allowed_list():
    s = scene()
    s["cast"][0]["track"]["kyes"] = []
    del s["ground"]
    s["cast"][1].pop("x")
    got = "\n".join(problems(s))
    assert "scene.cast[0].track: unknown field 'kyes'. Allowed: keys, move, layers" in got
    assert "scene: missing required field 'ground'" in got
    assert "scene.cast[1]: missing required field 'x'" in got
    assert "scene.set[0]: a circle needs 'r'" in "\n".join(problems(scene(set=[{"type": "circle", "c": [1, 2], "fill": "sun"}])))


def test_the_schema_enums_are_the_names_the_code_has():
    names = js("console.log(JSON.stringify({ poses: Object.keys(B2M.POSES), cycles: Object.keys(B2M.CYCLES), eases: B2M.EASES, visemes: B2M.VISEMES, skins: Object.keys(B2M.SKINS) }))")
    schema = validate_scene.SCHEMA
    track = schema["$defs"]["track"]["properties"]
    assert track["keys"]["items"]["properties"]["pose"]["enum"] == names["poses"]
    assert track["layers"]["items"]["properties"]["cycle"]["enum"] == names["cycles"] + ["talk"]
    assert track["keys"]["items"]["properties"]["ease"]["enum"] == names["eases"]
    assert track["visemes"]["items"]["properties"]["v"]["enum"] == names["visemes"] == track["keys"]["items"]["properties"]["mouth"]["enum"]
    assert schema["properties"]["skin"]["enum"] == names["skins"]


def test_a_bad_scene_builds_nothing_and_the_command_reports_every_problem(tmp_path):
    bad = scene(skin="papper", cast__1__track__keys__2__pose="wavee")
    (tmp_path / "scene.json").write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "words.json").write_text((EX09 / "words.json").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(cp.SceneError) as err:
        cp.build_scene_project(tmp_path / "scene.json", tmp_path / "project")
    assert len(err.value.problems) == 2 and not (tmp_path / "project").exists()
    run = subprocess.run([sys.executable, str(SCRIPTS / "character_project.py"), "--scene", str(tmp_path / "scene.json"), "--out", str(tmp_path / "project")], capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 2 and "scene.skin: 'papper' is not allowed" in run.stderr and "scene.cast[1].track.keys[2].pose" in run.stderr
    cli = subprocess.run([sys.executable, str(KIT / "validate_scene.py"), str(EX09 / "scene.json")], capture_output=True, text=True, encoding="utf-8")
    assert cli.returncode == 0 and "OK" in cli.stdout


# ---- the README: a complete scene, tables from the code, words JSON, stand-in voice ----------------------------------

def readme_scene() -> dict:
    block = README[README.index("```jsonc") + 8:README.index("```", README.index("```jsonc") + 8)]
    return json.loads(re.sub(r"\s//[^\n]*", "", block))


def test_the_readme_has_a_complete_scene_that_is_valid_and_shows_every_field():
    example = readme_scene()
    assert validate_scene.validate_scene(example, None) == [], validate_scene.validate_scene(example, None)
    schema = validate_scene.SCHEMA
    seen = set()
    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                seen.add(k)
                keys(v)
        elif isinstance(node, list):
            for v in node:
                keys(v)
    keys(example)
    wanted = set(schema["properties"]) | set(schema["properties"]["cast"]["items"]["properties"]) | set(schema["$defs"]["track"]["properties"]) | set(schema["properties"]["set"]["items"]["properties"])
    wanted |= set(schema["properties"]["captions"]["items"]["properties"]) | set(schema["$defs"]["track"]["properties"]["move"]["items"]["properties"]) | set(schema["$defs"]["track"]["properties"]["layers"]["items"]["properties"])
    wanted |= set(schema["$defs"]["track"]["properties"]["visemesFrom"]["properties"]) | set(schema["$defs"]["track"]["properties"]["keys"]["items"]["properties"]) | set(schema["properties"]["hills"]["items"]["properties"])
    assert wanted <= seen, f"fields the README example never shows: {sorted(wanted - seen)}"
    assert set(schema["properties"]["palette"]["required"]) <= set(example["palette"])


def test_the_readme_tables_match_the_code():
    done = subprocess.run([sys.executable, str(SCRIPTS / "build_character_docs.py"), "--check"], capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 0, done.stdout
    names = js("console.log(JSON.stringify({ poses: Object.keys(B2M.POSES), info: Object.keys(B2M.POSE_INFO), cycles: Object.keys(B2M.CYCLES), cycleInfo: Object.keys(B2M.CYCLE_INFO), visemes: B2M.VISEMES, visemeInfo: Object.keys(B2M.VISEME_INFO), eases: B2M.EASES, easeInfo: Object.keys(B2M.EASE_INFO) }))")
    assert names["poses"] == names["info"] and names["visemes"] == names["visemeInfo"] and names["eases"] == names["easeInfo"]
    assert set(names["cycles"]) | {"talk", "blink"} == set(names["cycleInfo"])
    poses_block = README[README.index("<!-- BEGIN generated: poses -->"):README.index("<!-- END generated: poses -->")]
    for kind in ("poses", "visemes", "eases"):
        for n in names[kind]:
            assert f"| `{n}` |" in README, f"{kind[:-1]} {n} is missing from the README table"
    assert poses_block.count("\n| `") == len(names["poses"])
    for n in names["cycles"] + ["talk", "blink"]:
        assert f"| `{n}` |" in README


def test_the_readme_check_fails_when_the_table_drifts(tmp_path):
    drifted = README.replace("| `idle` | standing, arms loose, a slight breath |", "| `idle` | an old description |")
    assert drifted != README
    sys.path.insert(0, str(SCRIPTS))
    import build_character_docs as docs
    assert docs.rewrite(drifted, docs.blocks(docs.kit_tables())) == README, "regenerating restores the table"
    assert docs.rewrite(README, docs.blocks(docs.kit_tables())) == README


# ---- positions: absolute, and loud about being off screen ------------------------------------------------------------------

POS = """
const ch = require(process.argv[1] + '/../cast/child.json'), skin = B2M.SKINS['flat-explainer'];
const feet = (track, t, home) => { const p = B2M.pose(ch, track, t, { home }); const m = B2M.partPoint(ch, p, { x: home.x, y: home.y, scale: 1 }, 'hip'); return [Math.round(m[0]), p.move.flip]; };
"""


@needs_node
def test_move_positions_are_absolute_and_never_added_to_the_cast_x():
    r = js(POS + """
const home = { x: 1000, y: 900, flip: 1 }, track = { move: [{ t: 0, x: 300 }, { t: 2, x: 900, ease: 'linear' }] };
console.log(JSON.stringify({ start: feet(track, 0, home)[0], mid: feet(track, 1, home)[0], end: feet(track, 5, home)[0], none: feet({}, 1, home)[0], keep: feet({ move: [{ t: 0, facing: 'left' }] }, 1, home)[0] }));
""")
    assert (r["start"], r["mid"], r["end"]) == (300, 600, 900), "the cast x of 1000 is not added"
    assert r["none"] == r["keep"] == 1000, "no move, or a key with no x, stays at home"


@needs_node
def test_facing_left_and_right_work_on_the_cast_entry_and_on_move_keys_and_flip_still_works():
    r = js(POS + """
const home = { x: 500, y: 900, flip: 1 };
const f = (track, h) => feet(track, 1, h || home)[1];
const scene = { ground: 900 };
console.log(JSON.stringify({ homeLeft: B2M.homeOf({ x: 5, facing: 'left' }, scene).flip, homeRight: B2M.homeOf({ x: 5, facing: 'right' }, scene).flip, homeFlip: B2M.homeOf({ x: 5, flip: -1 }, scene).flip, homeBoth: B2M.homeOf({ x: 5, facing: 'right', flip: -1 }, scene).flip, homeNone: B2M.homeOf({ x: 5 }, scene).flip,
  keyLeft: f({ move: [{ t: 0, facing: 'left' }] }), keyRight: f({ move: [{ t: 0, facing: 'right' }] }, { x: 1, y: 1, flip: -1 }), keyFlip: f({ move: [{ t: 0, flip: -1 }] }),
  turns: [0.5, 1.5, 2.5].map((t) => feet({ move: [{ t: 0, facing: 'right' }, { t: 1, facing: 'left' }, { t: 2, facing: 'right' }] }, t, home)[1]) }));
""")
    assert (r["homeLeft"], r["homeRight"], r["homeFlip"], r["homeBoth"], r["homeNone"]) == (-1, 1, -1, 1, 1), "facing wins over flip"
    assert (r["keyLeft"], r["keyRight"], r["keyFlip"]) == (-1, 1, -1)
    assert r["turns"] == [1, -1, 1], "a key's facing holds until the next key"


def test_a_cast_member_fully_outside_the_frame_for_over_half_a_second_is_an_error_that_names_it():
    away = scene(cast__0__x=2720)
    away["cast"][0]["track"]["move"] = []
    errors, _ = cp.screen_problems(cp.resolve_scene(away, EX09))
    assert len(errors) == 1
    for must in ("scene.cast[0]", "kid", "child", "fully outside the frame to the right", "from 0.0 s to 14.0 s", "x = 2720", "absolute screen pixels", "allowOffscreen"):
        assert must in errors[0], must
    allowed = scene(cast__0__x=2720, cast__0__allowOffscreen=True)
    allowed["cast"][0]["track"]["move"] = []
    assert cp.screen_problems(cp.resolve_scene(allowed, EX09))[0] == []
    # the old mistake: a move key that was meant as an offset, added to the cast x, now reads as absolute and is caught
    mistaken = scene(cast__0__track__move=[{"t": 0, "x": 2720}, {"t": 14, "x": 2800}])
    assert cp.screen_problems(cp.resolve_scene(mistaken, EX09))[0]


def test_walking_in_from_off_screen_briefly_is_fine_but_staying_out_is_not():
    quick, _ = cp.screen_problems(cp.resolve_scene(copy.deepcopy(GOOD), EX09))
    assert quick == [], "example 09's child starts off screen and is back in view within half a second"
    slow = scene(cast__0__track__move=[{"t": 0, "x": -900}, {"t": 3, "x": 560, "ease": "linear"}])
    errors, _ = cp.screen_problems(cp.resolve_scene(slow, EX09))
    assert errors and "to the left" in errors[0] and "from 0.0 s to" in errors[0]


def test_speakers_facing_away_from_each_other_get_a_warning_and_example_09_none():
    assert cp.screen_problems(cp.resolve_scene(copy.deepcopy(GOOD), EX09))[1] == []
    turned = scene(cast__0__facing="left")
    turned["cast"][0]["track"]["move"][0]["facing"] = "left"   # told to face left, so the walk does not turn it
    warnings = cp.screen_problems(cp.resolve_scene(turned, EX09))[1]
    assert any("kid faces left while speaking to crow" in w and "speakers usually face each other" in w for w in warnings), warnings


# ---- the stand-in voice ----------------------------------------------------------------------------------------------------

def test_the_standin_voice_is_a_wav_that_is_loud_on_words_and_quiet_between():
    sys.path.insert(0, str(SCRIPTS))
    import standin_voice
    words = json.loads((EX09 / "words.json").read_text(encoding="utf-8"))
    samples = standin_voice.render(words, 14.0)
    assert len(samples) == 14 * standin_voice.RATE
    level = lambda a, b: max(abs(v) for v in samples[int(a * standin_voice.RATE):int(b * standin_voice.RATE)])  # noqa: E731
    assert level(3.5, 3.65) > 0.1 and level(5.25, 5.7) > 0.1, "words are audible"
    assert level(0, 3.3) < 1e-3 and level(4.2, 4.4) < 1e-3 and level(6.5, 7.1) < 1e-3, "silence between lines and in pauses"


def test_the_standin_voice_command_writes_a_wav_that_lip_sync_reads_back(tmp_path):
    out = tmp_path / "voice.wav"
    run = subprocess.run([sys.executable, str(SCRIPTS / "standin_voice.py"), str(EX09 / "words.json"), str(out), "--seconds", "14"], capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0 and "not speech" in run.stdout
    with wave.open(str(out)) as wf:
        assert (wf.getnchannels(), wf.getsampwidth(), wf.getframerate()) == (1, 2, 48000) and abs(wf.getnframes() / 48000 - 14) < 0.01
    track = lipsync.amplitude_track(out, 30)
    at = lambda t: next(k["v"] for k in reversed(track) if k["t"] <= t)  # noqa: E731
    assert at(1.0) == "rest" and at(4.3) == "rest" and {at(3.6), at(5.4), at(8.0)} - {"rest"}, "mouths open on words, shut between"
    default = subprocess.run([sys.executable, str(SCRIPTS / "standin_voice.py"), str(EX09 / "words.json"), str(tmp_path / "d.wav")], capture_output=True, text=True, encoding="utf-8")
    assert default.returncode == 0 and "10.3 s" in default.stdout, "default length is half a second after the last word"


def test_the_standin_voice_command_explains_bad_input(tmp_path):
    script = str(SCRIPTS / "standin_voice.py")
    run = lambda *a: subprocess.run([sys.executable, script, *a], capture_output=True, text=True, encoding="utf-8")  # noqa: E731
    assert run(str(tmp_path / "missing.json"), str(tmp_path / "o.wav")).returncode == 2
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    bad = run(str(empty), str(tmp_path / "o.wav"))
    assert bad.returncode == 2 and "empty" in bad.stderr


def test_the_words_example_in_the_readme_is_accepted_by_lipsync_and_by_the_standin_voice(tmp_path):
    block = README[README.index("```json\n[\n  { \"text\": \"Hey\""):]
    words = tmp_path / "words.json"
    words.write_text(block[len("```json\n"):block.index("```", 8)], encoding="utf-8")
    shown = json.loads(words.read_text(encoding="utf-8"))
    assert set(shown[0]) == {"text", "start", "end"}
    done = subprocess.run([sys.executable, str(SCRIPTS / "lipsync.py"), str(words)], capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 0 and {k["v"] for k in json.loads(done.stdout)} >= {"rest", "AI", "etc"}
    assert subprocess.run([sys.executable, str(SCRIPTS / "standin_voice.py"), str(words), str(tmp_path / "v.wav")], capture_output=True).returncode == 0
    transcribe = [{"id": "w0", "text": "Hello", "start": 0.0, "end": 0.5}, {"id": "w1", "text": "world.", "start": 0.6, "end": 1.2}]   # what npx hyperframes transcribe writes
    (tmp_path / "t.json").write_text(json.dumps(transcribe), encoding="utf-8")
    assert lipsync.load_words(tmp_path / "t.json") == [{"text": "Hello", "start": 0.0, "end": 0.5}, {"text": "world.", "start": 0.6, "end": 1.2}]
