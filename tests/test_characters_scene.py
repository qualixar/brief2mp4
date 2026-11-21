"""Character kit scenes: the other skins, lip sync, the stage, example 09, the 3D starter, routing and docs."""
from __future__ import annotations

from characters_common import *  # noqa: F401,F403


# ---- checkpoint 3: the full cast, six skins, lip sync, the stage, example 09 ------------------------------------------

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


def test_example_09_child_walks_with_a_walk_key_and_the_feet_are_planted():
    scene = json.loads((EX09 / "scene.json").read_text(encoding="utf-8"))
    kid = scene["cast"][0]
    a, b = kid["track"]["move"]
    assert b.get("walk") is True and not any(layer["cycle"] == "walk" for layer in kid["track"].get("layers", []))
    code = "const B2M = require(process.argv[1]); const c = require(process.argv[2]); const s = B2M.walkSteps(c, %d, %s, %s); console.log(JSON.stringify([s, B2M.strideSpeed(c, 'walk', s) * %s]))" % (b["x"] - a["x"], b["t"] - a["t"], kid["scale"], kid["scale"])
    steps, planted = json.loads(subprocess.run([NODE, "-e", code, str(KIT / "index.js"), str(KIT / "cast" / "child.json")], capture_output=True, text=True, encoding="utf-8").stdout)
    assert abs(planted - (b["x"] - a["x"]) / (b["t"] - a["t"])) < 0.5, "the walk speed is the planted-feet speed"
    assert 6 < steps < 9, "about the 8 drawings a second the example used before"


def test_example_09_has_a_brief_the_words_and_a_readme():
    brief = (EX09 / "BRIEF.md").read_text(encoding="utf-8")
    for must in ("14.0 s", "paper cut-out", "anime", "Hey crow, that is my kite!", "Finders keepers, little one.", "words.json"):
        assert must in brief
    assert (EX09 / "README.md").is_file() and (SCRIPTS / "standin_voice.py").is_file() and not (EX09 / "make_standin_voice.py").exists()
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
    assert subprocess.run([sys.executable, str(SCRIPTS / "standin_voice.py"), str(EX09 / "words.json"), str(voice), "--seconds", "14"], capture_output=True).returncode == 0
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


@needs_node
def test_in_example_09_the_listener_keeps_a_closed_mouth_while_the_other_character_speaks(tmp_path):
    scene = resolved_scene()
    f = tmp_path / "scene.json"
    f.write_text(json.dumps(scene), encoding="utf-8")
    code = """
const fs = require('fs'); const B2M = require(process.argv[1]);
const scene = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const chars = { child: require(process.argv[1] + '/../cast/child.json'), crow: require(process.argv[1] + '/../cast/crow.json') };
const out = [];
scene.cast.forEach((speaker, i) => {
  const words = speaker.track.visemes, listener = scene.cast[1 - i];
  for (let t = words[0].t; t <= words[words.length - 1].t; t += 0.05) {
    const speaking = B2M.pose(chars[speaker.character], speaker.track, t, { steps: 12 }).viseme;
    const heard = B2M.pose(chars[listener.character], listener.track, t, { steps: 12 }).viseme;
    out.push({ who: speaker.id, t: Math.round(t * 100) / 100, heard, speaking });
  }
});
console.log(JSON.stringify(out));
"""
    out = subprocess.run([NODE, "-e", code, str(KIT / "index.js"), str(f)], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr[-500:]
    rows = json.loads(out.stdout)
    assert len(rows) > 80
    assert [r for r in rows if r["who"] == "kid" and r["heard"] != "rest"] == [], "the crow's beak is shut while the child speaks"
    assert [r for r in rows if r["who"] == "crow" and r["heard"] != "rest"] == [], "the child's mouth is shut while the crow speaks"
    assert {r["speaking"] for r in rows} - {"rest"}, "the speaker's mouth does move"
