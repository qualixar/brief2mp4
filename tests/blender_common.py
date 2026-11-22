"""Helpers for the Blender recipe tests (no tests here).

Recipes run through the system Blender, headless, at a few pixels and a few frames. A recipe prints one
`B2M3D_RECIPE {json}` line; the tests read the numbers from it and, where a picture is the proof, compare
BMP frames the recipe wrote (BMP is plain enough to read with the standard library, so no imaging package
is needed).
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
from pathlib import Path

from b2m3d import paths
from conftest import PACK

RECIPES = PACK / "templates" / "recipes"
MARKER = "B2M3D_RECIPE"


def run_recipe(name: str, *args: str, timeout: int = 600) -> dict:
    """Run recipes/b2m_<name>.py in Blender and return its result JSON; fail loudly with the output tail."""
    exe = paths.blender()
    assert exe, "Blender not found"
    cmd = [exe, "-b", "--factory-startup", "-P", str(RECIPES / f"b2m_{name}.py"), "--", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env={**os.environ})
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(MARKER + " "):
            return json.loads(line[len(MARKER) + 1:])
    raise AssertionError(f"recipe {name} gave no result (exit {proc.returncode}):\n{(proc.stdout + proc.stderr)[-2500:]}")


def read_bmp(path: Path) -> tuple[int, int, bytes]:
    """A 24 or 32 bit uncompressed BMP as (width, height, rgb bytes without row padding)."""
    raw = Path(path).read_bytes()
    assert raw[:2] == b"BM", f"{path} is not a BMP"
    offset, = struct.unpack_from("<I", raw, 10)
    width, height, _planes, bpp, comp = struct.unpack_from("<iiHHI", raw, 18)
    assert comp in (0, 3) and bpp in (24, 32), f"unsupported BMP: {bpp} bpp, compression {comp}"
    height = abs(height)
    step = bpp // 8
    stride = (width * step + 3) // 4 * 4
    rgb = bytearray()
    for y in range(height):
        row = raw[offset + y * stride: offset + y * stride + width * step]
        for x in range(width):
            b, g, r = row[x * step], row[x * step + 1], row[x * step + 2]
            rgb += bytes((r, g, b))
    return width, height, bytes(rgb)


def mean_abs_diff(a: Path, b: Path) -> float:
    """Mean absolute difference between two same-size BMP frames, in 0..255 steps per channel."""
    wa, ha, da = read_bmp(a)
    wb, hb, db = read_bmp(b)
    assert (wa, ha) == (wb, hb), "frames differ in size"
    return sum(abs(x - y) for x, y in zip(da, db)) / len(da)
