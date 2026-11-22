"""b2m3d recipe: the Blender motion recipes (loop, retime, cloth, rigid, fold, walk) run headless.

`recipe list` needs no Blender. `recipe run NAME -- <recipe options>` runs templates/recipes/b2m_NAME.py in the
system Blender and returns the recipe's own result JSON (its measurements, and the frames it wrote).
"""
from __future__ import annotations

import ast
from pathlib import Path

from . import paths
from .run import B2M3DError, last_json, run

MARKER = "B2M3D_RECIPE"


def folder() -> Path:
    return paths.TEMPLATES / "recipes"


def available() -> list[dict]:
    """Every b2m_<name>.py, with the first line of its docstring (read without importing: it needs bpy)."""
    found = []
    for path in sorted(folder().glob("b2m_*.py")):
        name = path.stem.removeprefix("b2m_")
        if name == "common":
            continue
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        found.append({"name": name, "summary": doc.splitlines()[0].removeprefix(f"b2m_{name}: "), "script": str(path)})
    return found


def run_recipe(name: str, args: list[str], timeout: int = 7200) -> dict:
    known = {r["name"]: r for r in available()}
    if name not in known:
        raise B2M3DError(f"no recipe called {name!r}; the recipes are: {', '.join(known)}")
    exe = paths.blender()
    if not exe:
        raise B2M3DError("Blender was not found. Install it, or set B2M3D_BLENDER to its executable "
                         "(run `python -m b2m3d doctor` for the install command).")
    args = [a for a in args if a != "--"] if args[:1] == ["--"] else args
    out = run([exe, "-b", "--factory-startup", "-P", known[name]["script"], "--", *args], timeout=timeout)
    return last_json(out, MARKER)
