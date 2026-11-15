"""A CadQuery assembly spec (needs the cad component)."""
import cadquery as cq


def build(params):
    assy = cq.Assembly(name="demo")
    assy.add(cq.Workplane("XY").box(20, 20, 4), name="plate", color=cq.Color(0.5, 0.5, 0.6))
    assy.add(cq.Workplane("XY").workplane(offset=4).circle(5).extrude(6), name="post", color=cq.Color(0.8, 0.4, 0.2))
    return assy
