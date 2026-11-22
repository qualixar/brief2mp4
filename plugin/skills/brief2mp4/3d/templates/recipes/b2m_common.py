"""b2m_common: helpers shared by the brief2mp4 Blender motion recipes.

Every recipe has the same shape and works in two places:

  headless   blender -b --factory-startup -P b2m_<name>.py -- --out frames --frames 96
  live       import b2m_<name>; b2m_<name>.build({...}, clear=False)     (inside a running Blender)

A recipe module exposes DEFAULTS (every knob, with its default), build(params, clear) which makes the scene and
returns a state dict, and measure(state) which returns plain numbers that prove the motion did what it should.
main() parses the command line, builds, measures, renders if --out is given, and prints one result line:

  B2M3D_RECIPE {json}

Rules kept here so the recipes stay short: colours are converted to linear, nodes are found by type, engine
names are tried in turn, and animation curves are read through fcurves() because Blender 5 moved them
into slotted actions.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

MARKER = "B2M3D_RECIPE"

COMMON = {
    "out": "",            # folder for frames; empty means measure only, render nothing
    "render_frames": "",  # "1,48,10-12"; empty means every frame
    "fmt": "PNG",         # PNG, or BMP for tiny test frames
    "fps": 30, "width": 1920, "height": 1080, "samples": 16, "engine": "EEVEE",
    "bg": "#15171c", "floor": "#23262e", "subject": "#f2a65a", "accent": "#e4572e", "ink": "#f4efe6",
    "caption": "",        # one short line shown low in the frame, as 3D text
    "json": "",           # also write the result to this file
}


# ---------- command line ----------

def _bool(text: str) -> bool:
    return str(text).lower() in ("1", "true", "yes", "on")


def parse_args(defaults: dict, description: str, argv: list[str] | None = None) -> dict:
    """Every key of defaults becomes --key-with-dashes, typed like its default. Arguments follow `--`."""
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description=description)
    for key, default in {**COMMON, **defaults}.items():
        flag = "--" + key.replace("_", "-")
        if isinstance(default, bool):          # --naive, or --naive 0
            ap.add_argument(flag, dest=key, type=_bool, nargs="?", const=True, default=default)
        else:
            ap.add_argument(flag, dest=key, type=type(default), default=default)
    return vars(ap.parse_args(argv))


def merged(defaults: dict, params: dict | None) -> dict:
    """defaults plus overrides; an unknown key is an error, so a typo cannot silently do nothing."""
    base = {**COMMON, **defaults}
    extra = set(params or {}) - set(base)
    if extra:
        raise KeyError(f"unknown parameter(s): {', '.join(sorted(extra))}")
    return {**base, **(params or {})}


def frame_list(spec: str, start: int, end: int) -> list[int]:
    """'1,48,10-12' -> [1, 10, 11, 12, 48]; empty -> start..end."""
    if not spec.strip():
        return list(range(start, end + 1))
    frames: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part[1:]:
            a, b = part.split("-", 1)
            frames.update(range(int(a), int(b) + 1))
        elif part:
            frames.add(int(part))
    return sorted(frames)


# ---------- colour, material ----------

def hex_rgba(h: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, alpha)


def mix_hex(a: str, b: str, t: float) -> str:
    """A colour t of the way from hex a to hex b, mixed in sRGB."""
    pa, pb = (tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for h in (a, b))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def material(name: str, color: str, roughness: float = 0.5, metallic: float = 0.0,
             emission: str | None = None, strength: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")   # by type, never by name
    bsdf.inputs["Base Color"].default_value = hex_rgba(color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        bsdf.inputs["Emission Color"].default_value = hex_rgba(emission)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def paint(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ---------- scene, stage ----------

def begin(name: str, clear: bool) -> bpy.types.Collection:
    """clear=True (headless): an empty file. clear=False (live): keep the user's scene and only replace
    the collection this recipe made last time, so running it twice does not pile up objects."""
    if clear:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    old = bpy.data.collections.get(f"b2m_{name}")
    if old is not None:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new(f"b2m_{name}")
    scene.collection.children.link(coll)
    return coll


def add(coll: bpy.types.Collection, obj: bpy.types.Object) -> bpy.types.Object:
    coll.objects.link(obj)
    return obj


def empty(coll, name: str, loc=(0, 0, 0), parent=None, display="PLAIN_AXES", size=0.1) -> bpy.types.Object:
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = display, size
    add(coll, e)
    if parent is not None:
        e.parent = parent          # parent first, then the local location: no parent-inverse jump
    e.location = loc
    return e


def mesh_object(coll, name: str, verts, faces, loc=(0, 0, 0)) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    return add(coll, obj)


def set_engine(scene, wanted: str, samples: int) -> None:
    names = {"EEVEE": ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"], "CYCLES": ["CYCLES"],
             "WORKBENCH": ["BLENDER_WORKBENCH"]}[wanted.upper()]
    for name in names:
        try:
            scene.render.engine = name
            break
        except TypeError:
            continue
    if scene.render.engine == "CYCLES":
        scene.cycles.samples, scene.cycles.use_denoising = samples, True
    elif scene.render.engine != "BLENDER_WORKBENCH":
        scene.eevee.taa_render_samples = samples
    for view in ("Khronos PBR Neutral", "Standard"):      # look rule 1: a neutral view keeps palette colours
        try:
            scene.view_settings.view_transform = view
            break
        except TypeError:
            continue


def stage(scene, coll, p: dict, target=(0, 0, 0.6), cam=(4.5, -7.0, 3.0), lens=50.0, floor=True,
          floor_size=60.0) -> dict:
    """Floor, dark world, three area lights and a tracking camera: the recipe from references/blender.md."""
    scene.render.resolution_x, scene.render.resolution_y = int(p["width"]), int(p["height"])
    scene.render.resolution_percentage = 100
    scene.render.fps = int(p["fps"])
    set_engine(scene, p["engine"], int(p["samples"]))
    world = bpy.data.worlds.new("b2m_world")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = hex_rgba(p["bg"])
    bg.inputs["Strength"].default_value = 0.6
    scene.world = world
    aim = empty(coll, "b2m_aim", target)
    objs = {"aim": aim}
    if floor:
        half = floor_size / 2
        fl = mesh_object(coll, "b2m_floor", [(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)], [(0, 1, 2, 3)])
        paint(fl, material("b2m_floor", p["floor"], roughness=0.65))
        objs["floor"] = fl
    for name, kind, loc, watts, size, color in (("key", "AREA", (-3.5, -4.5, 5.5), 600, 3.0, "#ffffff"),
                                                ("rim", "AREA", (4.0, 4.5, 3.5), 400, 2.0, p["accent"]),
                                                ("fill", "AREA", (5.0, -4.0, 2.0), 120, 5.0, "#ffffff")):
        data = bpy.data.lights.new("b2m_" + name, kind)
        data.energy, data.size, data.color = watts, size, hex_rgba(color)[:3]
        lamp = add(coll, bpy.data.objects.new("b2m_" + name, data))
        lamp.parent = aim            # lights ride the aim point, so a recipe that moves it keeps the lighting
        lamp.location = loc
        track(lamp, aim)
    cdata = bpy.data.cameras.new("b2m_cam")
    cdata.lens = lens
    camera = add(coll, bpy.data.objects.new("b2m_cam", cdata))
    camera.location = cam
    track(camera, aim)
    scene.camera = camera
    objs["camera"] = camera
    return objs


def track(obj, target) -> None:
    con = obj.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"


def caption(scene, coll, text: str, p: dict, camera) -> bpy.types.Object | None:
    """One short line of flat 3D text parented to the camera: bottom left, inside the safe margin."""
    if not text:
        return None
    cu = bpy.data.curves.new("b2m_caption", "FONT")
    cu.body, cu.size, cu.align_x, cu.align_y = text, 0.5, "LEFT", "BOTTOM"
    cu.font = bpy.data.fonts.load("<builtin>")          # a text curve made from code has no font until one is loaded
    ob = add(coll, bpy.data.objects.new("b2m_caption", cu))
    ob.parent = camera
    ratio = scene.render.resolution_x / scene.render.resolution_y
    depth = 1.0                                       # metres in front of the lens: close, so nothing in the set can hide it
    half_h = depth * (camera.data.sensor_width / 2 / ratio) / camera.data.lens   # half the view height at that depth
    half_w = half_h * ratio
    px = 2 * half_h / scene.render.resolution_y         # metres per pixel at that depth
    cu.size = 54 * px                                   # 54 px tall text at 1080p
    ob.location = (-half_w + 100 * px, -half_h + 70 * px, -depth)
    paint(ob, material("b2m_caption", p["ink"], roughness=0.9, emission=p["ink"], strength=1.2))
    ob.visible_shadow = False
    return ob


# ---------- animation helpers ----------

def fcurves(idb) -> list:
    """Every F-curve of an ID, on Blender 4.x and on 5.x (slotted actions)."""
    ad = getattr(idb, "animation_data", None)
    act = ad.action if ad else None
    if act is None:
        return []
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out: list = []
    for layer in act.layers:
        for strip in layer.strips:
            bag = strip.channelbag(ad.action_slot) if ad.action_slot else None
            if bag:
                out += list(bag.fcurves)
    return out


def animated_ids(objs) -> list:
    """The objects, their data and their shape keys: where a recipe's keyframes can live."""
    ids: list = []
    for o in objs:
        ids.append(o)
        data = getattr(o, "data", None)
        if data is not None:
            ids.append(data)
            if getattr(data, "shape_keys", None):
                ids.append(data.shape_keys)
    return ids


def set_interpolation(ids, mode: str) -> None:
    for idb in ids:
        for fc in fcurves(idb):
            for kp in fc.keyframe_points:
                kp.interpolation = mode


def step(scene, frame: int) -> None:
    scene.frame_set(frame)


def world_pos(obj, local=(0, 0, 0)) -> Vector:
    """World position of a point of an object, read from the evaluated copy (physics writes there)."""
    dg = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(dg).matrix_world @ Vector(local)


# ---------- render, result ----------

def render_frames(scene, out_dir: str, frames: list[int], fmt: str) -> list[str]:
    """Frames in ascending order, so simulations step forward. Names are 0001.png, 0002.png, ... (finish.sh reads them)."""
    os.makedirs(out_dir, exist_ok=True)
    scene.render.image_settings.file_format = fmt
    ext = {"PNG": "png", "BMP": "bmp", "JPEG": "jpg"}.get(fmt, fmt.lower())
    done = []
    for f in sorted(frames):
        scene.frame_set(f)
        path = os.path.join(out_dir, f"{f:04d}.{ext}")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done.append(path)
    return done


def warm_up(scene, upto: int) -> None:
    """Step 1..upto once so cloth and rigid-body caches fill before any frame is rendered out of order."""
    for f in range(scene.frame_start, upto + 1):
        scene.frame_set(f)


def emit(result: dict, json_path: str = "") -> dict:
    result = {"blender": bpy.app.version_string, **result}
    if json_path:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
    print(f"{MARKER} {json.dumps(result)}")
    return result


def run_main(module_name: str, defaults: dict, description: str, build, measure) -> dict:
    """The standard main(): parse, build, measure, render, print."""
    p = parse_args(defaults, description)
    state = build(p, clear=True)
    scene = bpy.context.scene
    result = {"recipe": module_name, "frame_start": scene.frame_start, "frame_end": scene.frame_end,
              "fps": scene.render.fps, **measure(state)}
    if p["out"]:
        frames = frame_list(p["render_frames"], scene.frame_start, scene.frame_end)
        warm_up(scene, max(frames))
        result["rendered"] = render_frames(scene, p["out"], frames, p["fmt"])
    return emit(result, p["json"])


def smoothstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


TAU = 2 * math.pi
