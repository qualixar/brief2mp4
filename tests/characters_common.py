"""Shared helpers for the character kit tests (tests/test_characters*.py). Fast tests need Node (the skill already requires it)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin" / "skills" / "brief2mp4"
KIT = SKILL / "characters"
CAST = sorted((KIT / "cast").glob("*.json"))
NODE = shutil.which("node")
sys.path.insert(0, str(KIT))
import validate  # noqa: E402,F401

needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")
REQUIRED_POSES = ["idle", "wave", "point", "sit", "run-ready", "jump", "surprised", "sad", "laugh", "think", "fight-ready", "bow"]
SKIN_IDS = ["line-art", "paper-cutout", "shadow-puppet", "cel-shaded", "motion-comic", "flat-explainer"]


def js(code: str):
    """Run JS against the kit (loaded through characters/index.js) and return its JSON result."""
    prog = "const B2M = require(process.argv[1]);\n" + code
    out = subprocess.run([NODE, "-e", prog, str(KIT / "index.js")], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert out.returncode == 0, out.stderr[-1500:]
    return json.loads(out.stdout)


def load(name: str) -> dict:
    return json.loads((KIT / "cast" / f"{name}.json").read_text(encoding="utf-8"))


DEMO = KIT / "image-demo"


def png_info(data: bytes) -> tuple[int, int, int]:
    """Width, height and the alpha of the top-left pixel of an 8-bit RGBA PNG, read with zlib only."""
    import struct
    import zlib
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
    assert (depth, ctype) == (8, 6)
    pos, idat = 8, b""
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        if data[pos + 4:pos + 8] == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    return w, h, raw[1 + 3]


FAKE_DOM = """
const mk = (tag) => ({ tagName: tag, attrs: {}, style: {}, kids: [], setAttribute(k, v) { this.attrs[k] = String(v); }, appendChild(c) { this.kids.push(c); return c; }, replaceChild(n, o) { this.kids[this.kids.indexOf(o)] = n; } });
const doc = { createElementNS: (ns, tag) => mk(tag) };
"""


EX09 = REPO / "examples" / "09-story-characters"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import lipsync  # noqa: E402
import character_project as cp  # noqa: E402
import art_route  # noqa: E402
