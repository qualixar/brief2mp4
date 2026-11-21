#!/usr/bin/env python3
"""character_project.py: put the character kit and a scene into a HyperFrames project folder.

    python3 character_project.py --scene scene.json --skin cel-shaded --out project/
    npx hyperframes render project -o render.mp4 --quality delivery --fps 30

The scene file names the cast, their tracks, the backdrop and the captions (see characters/stage.js). A track may
carry "visemesFrom": { "words": "words.json", "from": 3.3, "to": 6, "lang": "en" }; it is turned into the
lip-sync track with scripts/lipsync.py. The same scene renders in any skin: pass --skin, or leave the scene's own.

As a module:

    from character_project import prepare_project
    prepare_project(project_dir, ["child", "crow"])      # runtime files, cast.js, vendor/gsap.min.js (+ three.js)
    prepare_project(project_dir, [], extra_cast={"mine": load_file("my-character.json")})

The runtime files are copied next to the page (characters/*.js) and the cast files are inlined as `cast.js`, so a
render never reads the network or a JSON file at run time. Standard library only; vendoring GSAP and three.js
uses scripts/vendor_libs.sh, as everywhere else in the skill.
"""
from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
KIT = SKILL / "characters"
RUNTIME = ["poses.js", "rig.js", "shapes.js", "render.js", "skins.js", "skins-extra.js", "stage.js", "sheet.js"]


def cast_ids() -> list[str]:
    return sorted(p.stem for p in (KIT / "cast").glob("*.json"))


def load_cast(ids: list[str]) -> dict[str, dict]:
    cast = {}
    for cid in ids:
        path = KIT / "cast" / f"{cid}.json"
        if not path.is_file():
            raise SystemExit(f"character_project: no character '{cid}'. Available: {', '.join(cast_ids())}")
        cast[cid] = json.loads(path.read_text(encoding="utf-8"))
    return cast


def _inline(pic: dict, base: Path) -> None:
    src = pic.get("src", "")
    if src and not src.startswith("data:"):
        mime = "image/webp" if src.lower().endswith(".webp") else "image/png"
        pic["src"] = f"data:{mime};base64," + base64.b64encode((base / src).read_bytes()).decode("ascii")


def inline_images(character: dict, base: Path) -> dict:
    """Replace every picture path in a character with a data: URI, so the page needs no file at render time."""
    for part in character["parts"]:
        for holder in [part] + list(part.get("variants", {}).values()):
            if "image" in holder:
                _inline(holder["image"], base)
            for pic in (holder.get("mouth") or {}).get("images", {}).values():
                _inline(pic, base)
    return character


def load_file(path: Path) -> dict:
    """Load a character file from anywhere (your own art, the image-parts demo) with its pictures inlined."""
    path = Path(path)
    return inline_images(json.loads(path.read_text(encoding="utf-8")), path.resolve().parent)


def vendor(project: Path, three: bool = False) -> None:
    cmd = ["bash", str(SKILL / "scripts" / "vendor_libs.sh"), str(project)] + (["--three"] if three else [])
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise SystemExit(f"character_project: vendoring GSAP failed (needs npm and the network once):\n{done.stderr[-600:]}")


def prepare_project(project: Path, ids: list[str], three: bool = False, extra_cast: dict | None = None) -> None:
    """Copy the runtime, inline the named characters as cast.js and vendor GSAP (and three.js)."""
    project = Path(project)
    (project / "characters").mkdir(parents=True, exist_ok=True)
    for name in RUNTIME:
        shutil.copyfile(KIT / name, project / "characters" / name)
    cast = load_cast(ids)
    for cid, character in (extra_cast or {}).items():
        cast[cid] = character
    text = "window.B2M_CAST = " + json.dumps(cast, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (project / "characters" / "cast.js").write_text(text, encoding="utf-8", newline="\n")
    if not (project / "vendor" / "gsap.min.js").exists() or (three and not (project / "vendor" / "three.module.js").exists()):
        vendor(project, three)


HF_JSON = '{"$schema":"https://hyperframes.heygen.com/schema/hyperframes.json","registry":"https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry","paths":{"blocks":"compositions","components":"compositions/components","assets":"assets"}}'


def write_hf_files(project: Path, name: str) -> None:
    """The two small files `npx hyperframes` expects next to index.html."""
    (project / "hyperframes.json").write_text(HF_JSON + "\n", encoding="utf-8", newline="\n")
    (project / "meta.json").write_text(json.dumps({"id": name, "name": name}) + "\n", encoding="utf-8", newline="\n")


class SceneError(ValueError):
    """A scene file with problems. `problems` lists each one, naming the field and what is allowed."""

    def __init__(self, problems: list[str]):
        super().__init__("the scene has %d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))
        self.problems = problems


def resolve_scene(scene: dict, base: Path) -> dict:
    """Expand each track's visemesFrom into a lip-sync track, and check the cast and skin names."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import lipsync
    for member in scene["cast"]:
        track = member.get("track")
        spec = isinstance(track, dict) and track.pop("visemesFrom", None)
        if spec:
            words = [w for w in lipsync.load_words(base / spec["words"]) if spec["from"] <= w["start"] < spec["to"]]
            track["visemes"] = lipsync.build_track(words, scene.get("fps", 30), spec.get("lang", "en"))
    return scene


_PATHS_JS = """
const fs = require('fs'); const B2M = require(process.argv[1]);
const scene = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const skin = B2M.SKINS[scene.skin], W = scene.width;
const out = {};
const hexToRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const lumOf = (rgb) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]); };
const colourOf = (fill, x, y) => {
  if (typeof fill === 'string') return /^#[0-9a-f]{6}$/i.test(fill) ? hexToRgb(fill) : null;
  if (fill && fill.grad === 'radial') {
    const k = Math.min(1, Math.max(0, (Math.hypot(x - fill.cx, y - fill.cy) - (fill.r0 || 0)) / (fill.r - (fill.r0 || 0))));
    let i = 0; while (i < fill.stops.length - 2 && fill.stops[i + 1][0] < k) i++;
    const a = fill.stops[i], b = fill.stops[i + 1], u = Math.min(1, Math.max(0, (k - a[0]) / (b[0] - a[0] || 1))), p = hexToRgb(a[1]), q = hexToRgb(b[1]);
    return p.map((v, n) => v + (q[n] - v) * u);
  }
  return null;
};
const inside = (d, x, y) => {
  const pts = []; B2M.parsePath(d).forEach((s) => s.pts.forEach((p) => pts.push(p)));
  let c = false; for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) if ((pts[i][1] > y) !== (pts[j][1] > y) && x < ((pts[j][0] - pts[i][0]) * (y - pts[i][1])) / (pts[j][1] - pts[i][1]) + pts[i][0]) c = !c;
  return c;
};
const backdrop = B2M.createStage(Object.assign({}, scene, { cast: [], captions: [] }), {}).items(0).filter((i) => i.kind === 'path' && i.d && !['panel', 'caption'].includes(i.part));
const behind = (x, y) => { for (let n = backdrop.length - 1; n >= 0; n--) { const it = backdrop[n], c = colourOf(it.fill, x, y); if (c && inside(it.d, x, y)) return c; } return null; };
scene.cast.forEach((m) => {
  const ch = require(process.argv[1] + '/../cast/' + m.character + '.json'), home = B2M.homeOf(m, scene), x = [], flip = [], y = [];
  for (let t = 0; t <= scene.duration + 1e-9; t += 0.1) {
    const p = B2M.pose(ch, m.track || {}, t, { home, scale: m.scale || 1 }).move;
    x.push(p.x === null ? home.x : p.x); flip.push(p.flip); y.push(p.y === null ? home.y : p.y);
  }
  // the colour the figure mostly is (weighted by area) and the colours of the background behind its middle and its feet
  const posed = B2M.pose(ch, m.track || {}, 0, { home, scale: m.scale || 1, steps: skin.steps, smooth: !skin.steps });
  const items = B2M.layout(ch, skin, posed, { x: home.x, y: home.y, scale: m.scale || 1 }).filter((i) => i.kind === 'path' && typeof i.fill === 'string' && !['fx', 'rod'].includes(i.part));
  let sum = [0, 0, 0], wsum = 0, box = null;
  items.forEach((i) => {
    const q = B2M.pathBounds(B2M.mapPoints(i.d, (px, py) => [i.m[0] * px + i.m[2] * py + i.m[4], i.m[1] * px + i.m[3] * py + i.m[5]])), c = colourOf(i.fill, 0, 0), a = Math.max(1, (q.x1 - q.x0) * (q.y1 - q.y0));
    box = box ? { x0: Math.min(box.x0, q.x0), y0: Math.min(box.y0, q.y0), x1: Math.max(box.x1, q.x1), y1: Math.max(box.y1, q.y1) } : q;
    if (c) { sum = sum.map((v, n) => v + c[n] * a); wsum += a; }
  });
  const tone = wsum ? sum.map((v) => v / wsum) : null, spots = box ? [[(box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2], [(box.x0 + box.x1) / 2, box.y1 - 4]] : [];
  const bg = spots.map(([sx, sy]) => behind(sx, sy)).filter(Boolean);
  const walks = []; const keys = ((m.track && m.track.move) || []).slice().sort((a, b) => a.t - b.t);
  for (let n = 1; n < keys.length; n++) if (keys[n].walk) {
    const x0 = keys[n - 1].x === undefined ? home.x : keys[n - 1].x, x1 = keys[n].x === undefined ? home.x : keys[n].x;
    if (x0 !== x1 && keys[n].t > keys[n - 1].t) walks.push({ from: keys[n - 1].t, to: keys[n].t, steps: B2M.walkSteps(ch, Math.abs(x1 - x0), keys[n].t - keys[n - 1].t, m.scale || 1) });
  }
  out[m.id] = { x, y, flip, half: ((ch.proportions.width || ch.proportions.height * 0.6) * (m.scale || 1)) / 2, tone, bg, walks, lum: tone ? lumOf(tone) : null, bgLum: bg.map(lumOf) };
});
console.log(JSON.stringify(out));
"""


def _walk_scene(scene: dict) -> dict:
    """Where each cast member stands every 0.1 s, which way it faces, its tone and the tone behind it, and its walks, all
    worked out by the same rig and stage that render the film."""
    import tempfile
    node = shutil.which("node")
    if not node:
        raise SystemExit("character_project: node not found; install Node.js 22 or newer")
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "scene.json"
        f.write_text(json.dumps(scene), encoding="utf-8")
        done = subprocess.run([node, "-e", _PATHS_JS, str(KIT / "index.js"), str(f)], capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise SystemExit("character_project: could not trace the cast through the scene:\n" + done.stderr[-600:])
    return json.loads(done.stdout)


def _hex(rgb: list[float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in rgb)


def screen_problems(scene: dict) -> tuple[list[str], list[str]]:
    """Errors and warnings about where the cast stands: fully out of the frame for over half a second (error), speakers
    facing away from each other (warning). Positions in a move track are absolute screen pixels."""
    paths, errors, warnings = _walk_scene(scene), [], []
    width, step = scene["width"], 0.1
    for m in scene["cast"]:
        if m.get("allowOffscreen"):
            continue
        p, run = paths[m["id"]], None
        for i, x in enumerate(p["x"] + [None]):
            out = x is not None and (x + p["half"] < 0 or x - p["half"] > width)
            if out and run is None:
                run = i
            elif not out and run is not None:
                if (i - run) * step > 0.5 + 1e-9:
                    side = "left" if p["x"][run] < 0 else "right"
                    errors.append(f"scene.cast[{scene['cast'].index(m)}] ({m['id']}, {m['character']}) is fully outside the frame to the {side} from {run * step:.1f} s to {(i - 1) * step:.1f} s "
                                  f"(x = {p['x'][run]:.0f}, the frame is 0 to {width}). Positions in a move track are absolute screen pixels; fix x or the move keys, or set allowOffscreen: true if this is meant")
                run = None
    height, ground = scene["height"], scene["ground"]
    for n, m in enumerate(scene["cast"]):
        p = paths[m["id"]]
        feet = max(p["y"])
        if feet > height:
            errors.append(f"scene.cast[{n}] ({m['id']}, {m['character']}): its feet are at y = {feet:.0f}, below the bottom of the frame ({height}). y is the y of the feet on screen; leave it out to stand on the ground top ({ground})")
        elif feet > ground + 0.5 * (height - ground):
            warnings.append(f"{m['id']}: its feet are at y = {feet:.0f}, deep inside the ground band (the ground top is {ground}); leave y out to stand on the ground top")
        for w in p["walks"]:
            if w["steps"] > 12:
                warnings.append(f"{m['id']} walks {w['from']:.1f} s to {w['to']:.1f} s fast enough to need {w['steps']:.0f} drawings a second, which looks like a run: allow more time or a shorter distance")
        if p["lum"] is not None and p["bgLum"]:
            ratio = min((max(p["lum"], b) + 0.05) / (min(p["lum"], b) + 0.05) for b in p["bgLum"])
            if ratio < 1.6:
                warnings.append(f"{m['id']} ({m['character']}) is hard to see: its tone {_hex(p['tone'])} is close to the background {_hex(p['bg'][0])} behind it (contrast {ratio:.1f}:1, aim for 1.6 or more); change the palette or the skin")
    speakers = [m for m in scene["cast"] if isinstance(m.get("track"), dict) and m["track"].get("visemes")]
    for a in speakers:
        i = min(len(paths[a["id"]]["x"]) - 1, int(a["track"]["visemes"][0]["t"] / step) + 3)
        for b in speakers:
            if a is b:
                continue
            toward = 1 if paths[b["id"]]["x"][i] > paths[a["id"]]["x"][i] else -1
            if paths[a["id"]]["flip"][i] != toward:
                warnings.append(f"{a['id']} faces {'right' if toward < 0 else 'left'} while speaking to {b['id']}, who stands to its {'right' if toward > 0 else 'left'}: speakers usually face each other (set facing: \"{'right' if toward > 0 else 'left'}\")")
    return errors, warnings


def build_scene_project(scene_path: Path, out: Path, skin: str | None = None) -> dict:
    """Write a complete HyperFrames project for the scene; return the scene as written. Raises SceneError for a bad scene."""
    scene_path = Path(scene_path)
    sys.path.insert(0, str(KIT))
    import validate_scene
    raw = json.loads(scene_path.read_text(encoding="utf-8"))
    if skin:
        raw["skin"] = skin
    problems = validate_scene.validate_scene(raw, scene_path.resolve().parent)
    if problems:
        raise SceneError(problems)
    scene = resolve_scene(raw, scene_path.resolve().parent)
    errors, warnings = screen_problems(scene)
    if errors:
        raise SceneError(errors)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    ids = sorted({m["character"] for m in scene["cast"]})
    out.mkdir(parents=True, exist_ok=True)
    prepare_project(out, ids)
    (out / "characters" / "scene.js").write_text("window.B2M_SCENE = " + json.dumps(scene, separators=(",", ":")) + ";\n", encoding="utf-8", newline="\n")
    html = (KIT / "stage.html").read_text(encoding="utf-8")
    for key, value in (("__WIDTH__", scene["width"]), ("__HEIGHT__", scene["height"]), ("__DURATION__", scene["duration"])):
        html = html.replace(key, str(value))
    (out / "index.html").write_text(html, encoding="utf-8", newline="\n")
    write_hf_files(out, "character-scene")
    return scene


def build_stage3d_project(ids: list[str], out: Path, seconds: float = 6.0) -> None:
    """Write a project from templates/threejs/characters-stage.html: rigged characters as planes in a Three.js set."""
    out.mkdir(parents=True, exist_ok=True)
    prepare_project(out, ids, three=True)
    html = (SKILL / "templates" / "threejs" / "characters-stage.html").read_text(encoding="utf-8").replace("__DURATION__", str(seconds))
    (out / "index.html").write_text(html, encoding="utf-8", newline="\n")
    write_hf_files(out, "character-stage-3d")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build a HyperFrames project from a character scene file.")
    ap.add_argument("--scene", help="scene JSON (see characters/stage.js)")
    ap.add_argument("--stage3d", action="store_true", help="instead of a scene: the 2D-in-3D starter, with --cast and --seconds")
    ap.add_argument("--cast", default="child,crow", help="with --stage3d: comma-separated character ids")
    ap.add_argument("--seconds", type=float, default=6.0, help="with --stage3d: duration")
    ap.add_argument("--out", required=True, help="project folder to write")
    ap.add_argument("--skin", help="override the scene's skin (line-art, paper-cutout, shadow-puppet, cel-shaded, motion-comic, flat-explainer)")
    args = ap.parse_args(argv)
    if args.stage3d:
        build_stage3d_project([c for c in args.cast.split(",") if c], Path(args.out), args.seconds)
        print(f"2D-in-3D project written to {args.out}")
        return 0
    if not args.scene:
        ap.error("give --scene FILE, or --stage3d")
    try:
        scene = build_scene_project(Path(args.scene), Path(args.out), args.skin)
    except SceneError as exc:
        print(f"character_project: {exc}", file=sys.stderr)
        return 2
    print(f"project written to {args.out}: {scene['width']}x{scene['height']}, {scene['duration']} s, skin {scene['skin']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
