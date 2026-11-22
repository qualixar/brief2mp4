"""b2m_rigid: rigid bodies held together by constraints: a hinged chain that swings (links=1 is a pendulum).

A fixed anchor and `links` boxes. Each joint is an empty with a rigid-body constraint (hinge: swings about the
Y axis, so the chain stays in one plane; point: a ball joint, free in every direction). The chain is released
from release_angle degrees and falls under gravity. The result reports how far any joint opened, how far the
tip travelled and, for a pendulum, its period, so a script can tell a held joint from a broken one.

  blender -b --factory-startup -P b2m_rigid.py -- --links 6 --joint hinge --release-angle 80 --out frames
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import b2m_common as c  # noqa: E402

DEFAULTS = {
    "frames": 120,
    "links": 5,
    "link_length": 0.5,     # metres
    "link_width": 0.12,
    "joint": "hinge",       # hinge or point
    "release_angle": 70.0,  # degrees from straight down, toward +X
    "mass": 1.0,            # kilograms per link
    "damping": 0.02,        # linear and angular damping; 0 swings forever
    "anchor_height": 2.6,
}


def _box(coll, name, w, d, h, loc, rot_y=0.0):
    x, y, z = w / 2, d / 2, h / 2
    verts = [(sx * x, sy * y, sz * z) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    obj = c.mesh_object(coll, name, verts, faces, loc)
    obj.rotation_euler = (0, rot_y, 0)
    return obj


def _activate(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def _body(obj, passive, p):
    _activate(obj)
    bpy.ops.rigidbody.object_add()
    rb = obj.rigid_body
    rb.type = "PASSIVE" if passive else "ACTIVE"
    rb.collision_shape = "BOX"
    rb.mass = float(p["mass"])
    rb.linear_damping = rb.angular_damping = float(p["damping"])


def _joint(coll, name, pivot, a, b, kind):
    e = c.empty(coll, name, pivot, size=0.12)
    if kind == "hinge":
        e.rotation_euler = (math.pi / 2, 0, 0)        # a hinge turns about its own Z axis: point that at world Y
    _activate(e)
    bpy.ops.rigidbody.constraint_add(type="HINGE" if kind == "hinge" else "POINT")
    con = e.rigid_body_constraint
    con.object1, con.object2, con.disable_collisions = a, b, True
    return e


def build(params=None, clear=True):
    p = c.merged(DEFAULTS, params)
    if p["joint"] not in ("hinge", "point"):
        raise ValueError("joint must be hinge or point")
    coll = c.begin("rigid", clear)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, int(p["frames"])
    n, length, width = int(p["links"]), float(p["link_length"]), float(p["link_width"])
    top = float(p["anchor_height"])
    objs = c.stage(scene, coll, p, target=(0.2, 0, top * 0.5), cam=(0.2, -(top * 1.9 + 2.5), top * 0.55), lens=40)   # the whole drop in frame
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    world = scene.rigidbody_world
    world.substeps_per_frame, world.solver_iterations = 20, 60
    world.point_cache.frame_start, world.point_cache.frame_end = 1, int(p["frames"])
    theta = math.radians(float(p["release_angle"]))
    d = (math.sin(theta), 0.0, -math.cos(theta))
    anchor = _box(coll, "b2m_anchor", 0.3, 0.3, 0.1, (0, 0, top))
    c.paint(anchor, c.material("b2m_anchor", p["ink"], roughness=0.5))
    _body(anchor, True, p)
    links, prev = [], anchor
    for i in range(n):
        mid = tuple(float(top * (k == 2)) + d[k] * (i + 0.5) * length for k in range(3))
        link = _box(coll, f"b2m_link{i}", width, width, length, mid, math.pi - theta)
        c.paint(link, c.material(f"b2m_link{i}", p["subject"] if i % 2 == 0 else p["accent"], roughness=0.35, metallic=0.4))
        _body(link, False, p)
        pivot = tuple(float(top * (k == 2)) + d[k] * i * length for k in range(3))
        _joint(coll, f"b2m_joint{i}", pivot, prev, link, p["joint"])
        links.append(link)
        prev = link
    c.caption(scene, coll, p["caption"], p, objs["camera"])
    return {"p": p, "scene": scene, "anchor": anchor, "links": links, "length": length, "top": top}


def _trace(state):
    """Step the simulation once, recording joint gaps, the tip's x and y, the first link's angle."""
    scene, anchor, links, length = state["scene"], state["anchor"], state["links"], state["length"]
    gaps, tip_x, off_plane, angle = [], [], [], []
    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)
        far = [c.world_pos(anchor)] + [c.world_pos(lk, (0, 0, length / 2)) for lk in links]
        near = [c.world_pos(lk, (0, 0, -length / 2)) for lk in links]
        gaps.append(max((a - b).length for a, b in zip(far, near)))
        tip_x.append(far[-1].x)
        off_plane.append(max(abs(c.world_pos(lk).y) for lk in links))
        first = far[1] - far[0]
        angle.append(math.atan2(first.x, -first.z))
    return gaps, tip_x, off_plane, angle


def _period(angle, fps):
    """Mean time between successive downward zero crossings of the first link's angle, in seconds."""
    times = [(i + angle[i] / (angle[i] - angle[i + 1])) / fps for i in range(len(angle) - 1) if angle[i] > 0 >= angle[i + 1]]
    return sum(b - a for a, b in zip(times, times[1:])) / (len(times) - 1) if len(times) >= 2 else None


def measure(state):
    gaps, tip_x, off_plane, angle = _trace(state)
    return {"constraints": len(state["links"]), "max_joint_gap": max(gaps), "tip_travel_x": max(tip_x) - min(tip_x),
            "max_out_of_plane": max(off_plane), "period_s": _period(angle, state["scene"].render.fps)}


if __name__ == "__main__":
    c.run_main("rigid", DEFAULTS, __doc__.split("\n")[0], build, measure)
