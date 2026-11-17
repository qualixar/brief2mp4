"""Art forms: the data, the generated pages, the router and (slow) every demo look in a real browser."""
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
REF = SKILL / "references"
DATA = json.loads((REF / "art-forms.json").read_text())
LOOKS_JS = (SKILL / "art-forms" / "looks.js").read_text()
sys.path.insert(0, str(SKILL / "scripts"))
import art_route  # noqa: E402


def look_ids() -> list[str]:
    return re.findall(r"^  '?([a-z0-9-]+)'?: \{ kind:", LOOKS_JS, re.M)


def test_there_are_enough_forms_and_ids_are_unique():
    ids = [f["id"] for f in DATA["forms"]]
    assert len(ids) >= 28
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("form", DATA["forms"], ids=lambda f: f["id"])
def test_every_form_is_complete(form):
    assert len(form["what"]) > 60 and len(form["origin"]) > 20
    assert len(form["rules"]) >= 4 and len(form["build"]) >= 3 and len(form["pitfalls"]) >= 2
    assert form["timing"] and form["assets"] and form["sound"] and form["route"]
    assert form["family"] in DATA["families"]
    assert form["fps"] is None or 6 <= form["fps"] <= 30
    assert len(form["keywords"]) >= 3
    assert form["sources"] and all(u.startswith("https://") for u in form["sources"])
    assert form["looks"], "each form has at least one demo"


def test_every_form_has_a_demo_and_every_demo_belongs_to_a_form():
    in_data = {look for f in DATA["forms"] for look in f["looks"]}
    assert in_data == set(look_ids())


def test_looks_never_read_a_clock_or_unseeded_randomness():
    code = re.sub(r"//.*", "", LOOKS_JS)   # comments may name the things that are banned
    for banned in ("Math.random", "Date.now", "performance.now", "setInterval", "setTimeout", "requestAnimationFrame", "new Date"):
        assert banned not in code, f"looks.js must be a pure function of time: found {banned}"
    assert "http://" not in code and "https://" not in code, "looks load nothing from the network"


def test_stepped_looks_quantise_time():
    for form in DATA["forms"]:
        if not form["fps"]:
            continue
        for look in form["looks"]:
            m = re.search(r"^  '?%s'?: \{ kind:.*?^  \} \},\n" % re.escape(look), LOOKS_JS, re.M | re.S)
            assert m, look
            assert re.search(r"\b(held|onTwos|frameOf)\(", m.group(0)), f"{look} is a stepped look but never quantises time"


def test_generated_pages_are_current():
    out = subprocess.run([sys.executable, str(SKILL / "scripts" / "build_art_forms.py"), "--check"], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
    for form in DATA["forms"]:
        page = (REF / "art-forms" / f"{form['id']}.md").read_text()
        assert "## Tested demo" in page and "```js" in page and "## Sources" in page
    index = (REF / "art-forms.md").read_text()
    assert all(f"art-forms/{f['id']}.md" in index for f in DATA["forms"])


@pytest.mark.parametrize("brief,expected,confidence", [
    ("A claymation ad for our tea brand, 15 seconds", "claymation", "named"),
    ("An anime style intro for my channel", "cel-shaded", "named"),
    ("Make it look like a paper cut-out", "paper-cutout", "named"),
    ("Tell the story of Ravana from the Ramayana for a festival screen", "shadow-puppet", "inferred"),
    ("Explain how our SaaS onboarding works in 40 seconds", "flat-explainer", "inferred"),
    ("A lyric video for our new single", "lyric-video", "named"),
    ("Show our survey statistics: 62 percent growth", "infographic", "inferred"),
    ("A bedtime story for children about a fox", "paper-cutout", "inferred"),
    ("A retro 90s promo that feels like an old tape", "vhs-glitch", "inferred"),
    ("A calm meditation intro", "watercolour", "inferred"),
    ("chalkboard style maths lesson", "whiteboard", "named"),
])
def test_router_picks_the_form(brief, expected, confidence):
    r = art_route.route(brief)
    assert r["form"] == expected
    assert r["confidence"] == confidence
    assert (SKILL / r["read"][0]).exists()


def test_router_says_so_when_nothing_fits():
    for brief in ("make a cool video", "A paper plane flies over the title"):   # one stray word is not a look
        r = art_route.route(brief)
        assert r["form"] is None and r["confidence"] == "none"
    assert "none suggested" in art_route.report(art_route.route("make a cool video"))


def test_router_command_line(tmp_path):
    script = str(SKILL / "scripts" / "art_route.py")
    brief = tmp_path / "BRIEF.md"
    brief.write_text("A voxel style trailer for our game")
    out = subprocess.run([sys.executable, script, str(brief), "--json"], capture_output=True, text=True)
    assert out.returncode == 0 and json.loads(out.stdout)["form"] == "voxel"
    piped = subprocess.run([sys.executable, script, "-"], input="neon sign that says OPEN", capture_output=True, text=True)
    assert piped.returncode == 0 and piped.stdout.startswith("Art form: Neon sign")
    empty = subprocess.run([sys.executable, script, "-"], input="  ", capture_output=True, text=True)
    assert empty.returncode == 2
    assert subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True).returncode == 0


@pytest.mark.slow
def test_every_look_draws_moves_and_repeats_in_a_real_browser():
    """Needs Node, Chrome and the network (three.js for the five 3D looks). Skips when Node is missing."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    out = subprocess.run([node, str(REPO / "tests" / "art_forms" / "check_looks.mjs")], capture_output=True, text=True, timeout=900)
    if "Could not start Chrome" in out.stderr:
        pytest.skip("no Chrome or Chromium to start")
    assert out.returncode == 0, out.stdout[-2000:]
    assert f"{len(look_ids())} of {len(look_ids())} looks pass" in out.stdout
