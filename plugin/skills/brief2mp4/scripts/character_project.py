#!/usr/bin/env python3
"""character_project.py: helpers that put the character kit into a HyperFrames project folder.

    from character_project import prepare_project
    prepare_project(project_dir, ["child", "crow"])      # runtime files, cast.js, vendor/gsap.min.js (+ three.js)

The runtime files are copied next to the page (characters/*.js) and the cast files are inlined as `cast.js`, so a
render never reads the network or a JSON file at run time. Standard library only; vendoring GSAP and three.js
uses scripts/vendor_libs.sh, as everywhere else in the skill.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
KIT = SKILL / "characters"
RUNTIME = ["poses.js", "rig.js", "shapes.js", "render.js", "skins.js", "sheet.js"]


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
    cast.update(extra_cast or {})
    text = "window.B2M_CAST = " + json.dumps(cast, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (project / "characters" / "cast.js").write_text(text, encoding="utf-8", newline="\n")
    if not (project / "vendor" / "gsap.min.js").exists() or (three and not (project / "vendor" / "three.module.js").exists()):
        vendor(project, three)
