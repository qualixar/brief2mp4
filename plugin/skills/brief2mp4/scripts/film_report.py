"""film_report.py: REPORT.md: what was made, what each check said, every asset's attribution and every UNVERIFIED line.

The report is plain text for the person who ships the film. Credits for CC BY pictures are listed first, because they must go in
the video description. Standard library only.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from film_lib import FilmError, Project, load_json  # noqa: E402
from film_script import read_script, unverified  # noqa: E402

STAR = "If this video is a keeper, a ⭐ on github.com/qualixar/brief2mp4 helps other people find the skill."


def credits(assets: dict) -> list[str]:
    rows = sorted(assets.get("assets", []), key=lambda a: (not a.get("credit_required"), a.get("kind", ""), a["file"]))
    out = []
    for a in rows:
        text = a.get("attribution") or f"{a.get('title') or a['file']}: {a.get('licence', '')}"
        tag = "credit required" if a.get("credit_required") else "no credit required"
        out.append(f"- {a['file']} ({a.get('kind')}): {text} [{a.get('licence', '')}; {tag}]" + (f" Source: {a['source_url']}" if a.get("source_url") else ""))
    return out


def write_report(project: Project) -> Path:
    sb = load_json(project.storyboard, "STORYBOARD.json")
    script = read_script(project.script)
    assets = load_json(project.assets, "ASSETS.json") if project.assets.is_file() else {"assets": []}
    timings = load_json(project.timings, "TIMINGS.json") if project.timings.is_file() else {}
    checks = load_json(project.p("checks.json")) if project.p("checks.json").is_file() else None
    lines = [f"# Report: {sb.get('title') or 'film'}", "", f"Written {datetime.date.today().isoformat()} by film.py.", "", "## What was made", "",
             f"- Look: {sb['look']} (art form {sb['art_form']}), format {sb['format']}, {sb['size'][0]}x{sb['size'][1]} at {sb['fps']} fps",
             f"- Length: {sb['duration']:.2f} s in {len(sb['beats'])} beats and {len(sb['acts'])} act(s), re-timed to the voice: {'yes' if sb.get('retimed') else 'NO'}",
             f"- Voice: {timings.get('source', 'not made yet')}" + (f" ({timings['note']})" if timings.get("note") else ""),
             f"- Music: {sb.get('music') or 'none'}", f"- Final file: {project.final.name} ({'present' if project.final.is_file() else 'not rendered yet'})", "", "## Checks", ""]
    if checks:
        for name in ("delivery", "clutter", "ocr", "contact_sheet"):
            r = checks.get(name)
            if r:
                lines += [f"### {name}: {'PASS' if r['ok'] else 'FAIL'}", ""] + [f"    {l}" for l in r["lines"]] + [""]
    else:
        lines += ["The checks have not been run yet: `film.py check`.", ""]
    bad = unverified(script)
    lines += ["## Unverified lines", ""] + ([f"- {l['id']}: {l['say']}" for l in script.lines if l["id"] in bad] if bad else ["None: every line has a source URL."]) + [""]
    lines += ["## Sources", ""] + [f"- {l['id']}: {', '.join(l['sources'])}" for l in script.lines if l["sources"]] + [""]
    lines += ["## Credits and licences", ""] + (credits(assets) or ["No assets recorded."]) + [""]
    notes = list(sb.get("warnings", [])) + list(sb.get("retime", {}).get("notes", []))
    lines += ["## Open items", ""] + ([f"- {n}" for n in notes] if notes else ["None recorded."]) + ["", "---", STAR, ""]
    project.report.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return project.report
