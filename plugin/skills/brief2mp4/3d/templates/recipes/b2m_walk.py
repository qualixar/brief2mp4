"""b2m_walk: a figure walks forward: a leg cycle plus root travel, with each planted foot staying put on the ground.

The body moves at a constant speed. A foot that is on the ground is held at one world position until it lifts
(the "plant"), and each leg is solved to reach it with two-bone IK; a foot in the air swings from one plant to the
next with a lift. So the stride is fitted to the speed (stride = speed x cycle time) and nothing slides. Every frame
is keyed, so the result is plain keyframes with no rig or add-on needed. With --naive the feet follow the body
instead, which makes the slide the checks catch.

  blender -b --factory-startup -P b2m_walk.py -- --speed 1.2 --cycle-frames 32 --frames 120 --out frames
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import b2m_common as c  # noqa: E402

DEFAULTS = {
    "frames": 96,
    "speed": 1.2,          # metres per second
    "cycle_frames": 32,    # frames for one foot to come round again (a left step plus a right step)
    "duty": 0.6,           # share of the cycle a foot spends on the ground
    "step_height": 0.12,   # how high the swing foot lifts, metres
    "thigh": 0.45,
    "shin": 0.45,
    "hip_height": 0.78,    # well under thigh + shin, so the legs reach the stride without locking
    "bob": 0.015,          # vertical bounce of the hips, twice a cycle
    "naive": False,        # feet follow the body instead of planting (shows foot slide)
}


def _box(coll, name, size, loc, parent, color, rot_y=0.0):
    sx, sy, sz = (s / 2 for s in size)
    verts = [(a * sx, b * sy, d * sz) for d in (-1, 1) for b in (-1, 1) for a in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    obj = c.mesh_object(coll, name, verts, faces)
    obj.parent = parent
    obj.location, obj.rotation_euler = loc, (0, rot_y, 0)
    c.paint(obj, color)
    return obj


def _ball(coll, name, radius, loc, parent, color):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, 0))
    obj = bpy.context.object
    bpy.context.collection.objects.unlink(obj)
    c.add(coll, obj)
    obj.name = name
    obj.parent = parent
    obj.location = loc
    bpy.ops.object.shade_smooth()
    c.paint(obj, color)
    return obj


def _figure(coll, p):
    body = c.material("b2m_body", p["subject"], roughness=0.45)
    limb = c.material("b2m_limb", p["accent"], roughness=0.45)
    ink = c.material("b2m_ink", p["ink"], roughness=0.6)
    l1, l2 = float(p["thigh"]), float(p["shin"])
    pelvis = c.empty(coll, "b2m_pelvis", (0, 0, float(p["hip_height"])))
    _box(coll, "b2m_hips", (0.2, 0.34, 0.14), (0, 0, 0), pelvis, body)
    torso = c.empty(coll, "b2m_torso", (0, 0, 0.07), pelvis)
    _box(coll, "b2m_chest", (0.22, 0.36, 0.5), (0, 0, 0.27), torso, body)
    _ball(coll, "b2m_head", 0.12, (0, 0, 0.66), torso, ink)
    rig = {"pelvis": pelvis, "torso": torso, "legs": {}, "arms": {}}
    for side, y in (("L", 0.1), ("R", -0.1)):
        hip = c.empty(coll, f"b2m_hip{side}", (0, y, 0), pelvis)
        knee = c.empty(coll, f"b2m_knee{side}", (0, 0, -l1), hip)
        ankle = c.empty(coll, f"b2m_ankle{side}", (0, 0, -l2), knee)
        _box(coll, f"b2m_thigh{side}", (0.11, 0.11, l1), (0, 0, -l1 / 2), hip, limb)
        _box(coll, f"b2m_shin{side}", (0.09, 0.09, l2), (0, 0, -l2 / 2), knee, limb)
        foot = _box(coll, f"b2m_foot{side}", (0.26, 0.1, 0.06), (0.06, 0, 0.03), ankle, ink)
        rig["legs"][side] = {"hip": hip, "knee": knee, "ankle": ankle, "foot": foot}
        shoulder = c.empty(coll, f"b2m_shoulder{side}", (0, y * 2.4, 0.42), torso)
        _box(coll, f"b2m_arm{side}", (0.08, 0.08, 0.5), (0, 0, -0.25), shoulder, limb)
        rig["arms"][side] = shoulder
    return rig


def solve_leg(hip, target, l1, l2):
    """Two-bone IK in the vertical plane. Returns (thigh angle, shin angle, overshoot, reached target); angles are
    measured from straight down, positive toward +x. The knee always bends forward."""
    dx, dz = target[0] - hip[0], target[1] - hip[1]
    dist = math.hypot(dx, dz)
    reach = min(dist, l1 + l2 - 1e-4)
    overshoot = max(0.0, dist - (l1 + l2))
    fx, fz = hip[0] + dx * reach / dist, hip[1] + dz * reach / dist
    alpha = math.atan2(dx, -dz)
    beta = math.acos(max(-1.0, min(1.0, (l1 * l1 + reach * reach - l2 * l2) / (2 * l1 * reach))))
    t1 = alpha + beta
    kx, kz = hip[0] + l1 * math.sin(t1), hip[1] - l1 * math.cos(t1)
    t2 = math.atan2(fx - kx, -(fz - kz))
    return t1, t2, overshoot, (fx, fz)


def foot_target(k, offset, p, hip_x):
    """World (x, z) of one foot at frame index k. offset shifts the leg half a cycle for the other foot."""
    cycle, duty, speed, fps = float(p["cycle_frames"]), float(p["duty"]), float(p["speed"]), float(p["fps"])
    pos = k / cycle + offset
    n = math.floor(pos)
    phase = pos - n
    stride = speed * cycle / fps
    mid_k = (n + duty / 2 - offset) * cycle           # frame at the middle of this stance, when the hip is over the foot
    plant = hip_x(mid_k)
    if p["naive"]:
        half = stride * duty / 2
        return hip_x(k) + half * math.cos(c.TAU * phase), float(p["step_height"]) * max(0.0, math.sin(c.TAU * phase))
    if phase < duty:
        return plant, 0.0
    s = (phase - duty) / (1 - duty)
    return plant + stride * c.smoothstep(s), float(p["step_height"]) * math.sin(math.pi * s)


def _key(obj, path, index, value, frame):
    vec = getattr(obj, path)
    vec[index] = value
    setattr(obj, path, vec)
    obj.keyframe_insert(path, index=index, frame=frame)


def _animate(rig, p):
    """Key every frame. Returns the targets and the largest IK overshoot, for the measurements."""
    l1, l2, fps, speed = float(p["thigh"]), float(p["shin"]), float(p["fps"]), float(p["speed"])
    hip_x = lambda k: speed * k / fps  # noqa: E731  (the hip's world x at frame index k)
    targets, worst = {"L": [], "R": []}, 0.0
    for f in range(1, int(p["frames"]) + 1):
        k = f - 1
        phase = (k / float(p["cycle_frames"])) % 1.0
        hz = float(p["hip_height"]) + float(p["bob"]) * math.cos(2 * c.TAU * phase)
        _key(rig["pelvis"], "location", 0, hip_x(k), f)
        _key(rig["pelvis"], "location", 2, hz, f)
        angles = {}
        for side, offset in (("L", 0.0), ("R", 0.5)):
            tx, tz = foot_target(k, offset, p, hip_x)
            t1, t2, over, reached = solve_leg((hip_x(k), hz), (tx, tz), l1, l2)
            worst = max(worst, over)
            targets[side].append(reached)
            leg = rig["legs"][side]
            _key(leg["hip"], "rotation_euler", 1, -t1, f)
            _key(leg["knee"], "rotation_euler", 1, -(t2 - t1), f)
            _key(leg["foot"], "rotation_euler", 1, t2, f)        # undo the shin's tilt: the sole stays flat
            angles[side] = t1
        for side, other in (("L", "R"), ("R", "L")):
            _key(rig["arms"][side], "rotation_euler", 1, -angles[other] * 0.8, f)   # the arm swings with the opposite leg
        _key(rig["torso"], "rotation_euler", 1, -0.08, f)                          # a slight forward lean
    c.set_interpolation(list(_ids(rig)), "LINEAR")
    return targets, worst


def _ids(rig):
    yield rig["pelvis"]
    yield rig["torso"]
    for leg in rig["legs"].values():
        yield from (leg["hip"], leg["knee"], leg["foot"])
    yield from rig["arms"].values()


def _ruler(coll, p, length):
    """A row of thin bars across the floor every half metre, so the travel is visible."""
    verts, faces = [], []
    for i in range(int(length / 0.5) + 4):
        x = -1.0 + i * 0.5
        base = len(verts)
        verts += [(x, -1.2, 0.002), (x + 0.04, -1.2, 0.002), (x + 0.04, 1.2, 0.002), (x, 1.2, 0.002)]
        faces.append((base, base + 1, base + 2, base + 3))
    bars = c.mesh_object(coll, "b2m_ruler", verts, faces)
    c.paint(bars, c.material("b2m_ruler", p["ink"], roughness=0.8))


def build(params=None, clear=True):
    p = c.merged(DEFAULTS, params)
    coll = c.begin("walk", clear)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, int(p["frames"])
    objs = c.stage(scene, coll, p, target=(0, 0, 0.8), cam=(1.4, -4.6, 1.5), lens=40)
    rig = _figure(coll, p)
    travel = float(p["speed"]) * (int(p["frames"]) - 1) / float(p["fps"])
    _ruler(coll, p, travel + 4)
    targets, worst = _animate(rig, p)
    aim, cam = objs["aim"], objs["camera"]            # the camera and lights ride the aim point, which follows the body
    cam.parent, cam.location = aim, (1.4, -4.6, 0.7)
    for f in (1, int(p["frames"])):
        _key(aim, "location", 0, float(p["speed"]) * (f - 1) / float(p["fps"]), f)
    c.set_interpolation([aim], "LINEAR")
    c.caption(scene, coll, p["caption"], p, cam)
    return {"p": p, "scene": scene, "rig": rig, "targets": targets, "overshoot": worst}


def measure(state):
    scene, rig, p = state["scene"], state["rig"], state["p"]
    trace = {"L": [], "R": []}
    root, err = [], 0.0
    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)
        root.append(c.world_pos(rig["pelvis"]).x)
        for side in trace:
            a = c.world_pos(rig["legs"][side]["ankle"])
            trace[side].append((a.x, a.z))
            tx, tz = state["targets"][side][f - 1]
            err = max(err, math.hypot(a.x - tx, a.z - tz))
    slide, contact, plants, lift = 0.0, 0, [], 0.0
    for side, pts in trace.items():
        run: list = []
        for i, (x, z) in enumerate(pts):
            lift = max(lift, z)
            if z < 0.004:
                contact += 1
                slide = max(slide, abs(x - pts[i - 1][0]) if run else 0.0)
                run.append(x)
            elif run:
                plants.append((i - len(run), sum(run) / len(run)))
                run = []
    plants.sort()
    steps = [b[1] - a[1] for a, b in zip(plants, plants[1:])]
    return {"root_distance": root[-1] - root[0], "contact_frames": contact, "max_slide_per_frame": slide,
            "min_foot_z": min(z for pts in trace.values() for _, z in pts), "max_foot_lift": lift,
            "max_leg_stretch": state["overshoot"], "max_ik_error": err, "plants": len(plants),
            "step_length": sum(steps) / len(steps) if steps else 0.0}


if __name__ == "__main__":
    c.run_main("walk", DEFAULTS, __doc__.split("\n")[0], build, measure)
