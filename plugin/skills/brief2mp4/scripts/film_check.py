"""film_check.py: the checks on a finished film: delivery (with seams and the joins between acts), layout, placeholder text, contact sheet.

Runs the skill's own checks and keeps their lines in checks.json for the report:
  check_delivery.sh   codec, size, frame rate, duration to the frame, loudness and true peak, black stretches, seams, freezes; the act
                      joins are passed as --joins so each is tested for a pop
  check_clutter.py    on every act's page, at rest after each beat's entrances: no card on card, 24 px between text, at most 4 blocks,
                      nothing clipped (needs Chrome; otherwise it says SKIP)
  ocr_sweep.sh        reads the finished frames for placeholder text and leaked paths (needs tesseract; otherwise it says SKIP)
  contact_sheet.sh    one still per beat, to look at (checks/)
A missing optional tool is a SKIP line, never a failure. Standard library only.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from film_lib import SCRIPTS, FilmError, Project, load_json, save_json  # noqa: E402

REST = 2.4          # seconds into a beat when its entrances are done


def run(cmd: list[str]) -> tuple[int, list[str]]:
    done = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return done.returncode, [l for l in (done.stdout + done.stderr).splitlines() if l.strip()]


def rest_times(sb: dict, act: str | None, t0: float) -> list[float]:
    out = []
    for b in sb["beats"]:
        if act in (None, "all") or b["act"] == act:
            out.append(round(b["start"] - t0 + min(REST, max(0.5, b["duration"] - 0.4)), 3))
    return out


def check_film(project: Project) -> dict:
    sb = load_json(project.storyboard, "STORYBOARD.json")
    build = load_json(project.p("BUILD.json"), "BUILD.json")
    if not project.final.is_file():
        raise FilmError(f"{project.final.name} not found: run the render stage first")
    joins = ",".join(f"{a['start']:.4f}" for a in sb["acts"][1:])
    size = "x".join(str(v) for v in sb["size"])
    cmd = ["bash", SCRIPTS / "check_delivery.sh", project.final, "--seconds", f"{sb['duration']:.4f}", "--size", size, "--fps", sb["fps"]]
    code, lines = run(cmd + (["--joins", joins] if joins else []))
    results = {"delivery": {"ok": code == 0, "lines": lines}}
    clutter_lines, clutter_ok = [], True
    for job in build["projects"]:
        times = rest_times(sb, None if job["act"] == "all" else job["act"], job["start"])
        c, ls = run([sys.executable, SCRIPTS / "check_clutter.py", "--dom", project.p(job["dir"], "index.html"), "--at", ",".join(str(t) for t in times)])
        clutter_ok &= c == 0
        clutter_lines += [f"{job['act']}: {l}" for l in ls]
    results["clutter"] = {"ok": clutter_ok, "lines": clutter_lines}
    c, ls = run(["bash", SCRIPTS / "ocr_sweep.sh", project.final])
    results["ocr"] = {"ok": c == 0, "lines": ls}
    starts = ",".join(f"{b['start'] + 1.0:.2f}" for b in sb["beats"])
    c, ls = run(["bash", SCRIPTS / "contact_sheet.sh", project.final, "--at", starts, "--out", project.p("checks")])
    results["contact_sheet"] = {"ok": c == 0, "lines": ls[-2:]}
    results["ok"] = all(r["ok"] for r in results.values() if isinstance(r, dict))
    save_json(project.p("checks.json"), results)
    return results
