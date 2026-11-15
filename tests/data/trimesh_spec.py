"""A spec that returns a trimesh directly, with its own PARAMS and UNITS."""
import trimesh

PARAMS = {"size": 2.0}
UNITS = "cm"


def build(params):
    return trimesh.creation.box(extents=[params["size"]] * 3)
