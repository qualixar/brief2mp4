"""check_clutter.py: each layout rule has a layout that must pass and one that must fail."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

from craft_common import SCRIPTS, py_script, text_png

spec = importlib.util.spec_from_file_location("check_clutter", SCRIPTS / "check_clutter.py")
clutter = importlib.util.module_from_spec(spec)
sys.modules["check_clutter"] = clutter
spec.loader.exec_module(clutter)


def text(id_, x, y, w=300, h=80):
    return {"id": id_, "kind": "text", "x": x, "y": y, "w": w, "h": h}


def card(id_, x, y, w=500, h=300):
    return {"id": id_, "kind": "card", "x": x, "y": y, "w": w, "h": h}


GOOD = [text("title", 100, 80), card("a", 100, 300), text("a-label", 140, 340), card("b", 700, 300), text("b-label", 740, 340)]


def run_boxes(tmp_path, boxes, *extra, frame=None):
    data = [{"t": 1.0, "boxes": boxes}]
    if frame:
        data = {"frame": {"width": frame[0], "height": frame[1]}, "samples": data}
    f = tmp_path / "boxes.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return py_script("check_clutter.py", "--boxes", f, *extra)


def test_a_clean_layout_passes_every_rule(tmp_path):
    proc = run_boxes(tmp_path, GOOD)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.count("PASS") == 4 and "FAIL" not in proc.stdout


def test_card_on_card_fails(tmp_path):
    proc = run_boxes(tmp_path, [card("a", 100, 300), card("b", 500, 400)])
    assert proc.returncode == 1
    assert "FAIL  no card on card" in proc.stdout and "card 'a' overlaps card 'b'" in proc.stdout


def test_a_card_inside_a_card_fails_unless_nested_is_allowed(tmp_path):
    boxes = [card("outer", 100, 100, 800, 600), card("inner", 200, 200, 300, 200)]
    assert run_boxes(tmp_path, boxes).returncode == 1
    assert run_boxes(tmp_path, boxes, "--allow-nested").returncode == 0


def test_text_straddling_a_card_edge_fails_but_text_inside_passes(tmp_path):
    assert run_boxes(tmp_path, [card("a", 100, 300), text("in", 140, 340)]).returncode == 0
    proc = run_boxes(tmp_path, [card("a", 100, 300), text("edge", 500, 340)])   # runs from x=500 to 800, card ends at 600
    assert proc.returncode == 1 and "straddles the edge of card 'a'" in proc.stdout


def test_text_boxes_closer_than_24_px_fail(tmp_path):
    ok = run_boxes(tmp_path, [text("a", 100, 100), text("b", 100, 204)])        # 24 px apart: allowed, zero tolerance below
    assert ok.returncode == 0, ok.stdout
    bad = run_boxes(tmp_path, [text("a", 100, 100), text("b", 100, 203)])        # 23 px
    assert bad.returncode == 1 and "'a' and 'b' are 23 px apart" in bad.stdout
    over = run_boxes(tmp_path, [text("a", 100, 100), text("b", 200, 140)])
    assert over.returncode == 1 and "(overlapping)" in over.stdout


def test_min_gap_is_adjustable(tmp_path):
    boxes = [text("a", 100, 100), text("b", 100, 190)]                           # 10 px apart
    assert run_boxes(tmp_path, boxes).returncode == 1
    assert run_boxes(tmp_path, boxes, "--min-gap", "8").returncode == 0


def test_more_than_four_text_blocks_fail(tmp_path):
    four = [text(f"t{i}", 100, 100 + i * 150) for i in range(4)]
    assert run_boxes(tmp_path, four).returncode == 0
    proc = run_boxes(tmp_path, four + [text("t4", 100, 800)])
    assert proc.returncode == 1 and "5 text blocks on screen" in proc.stdout


def test_text_past_the_frame_edge_fails_but_off_stage_text_does_not(tmp_path):
    assert run_boxes(tmp_path, [text("in", 1500, 100)]).returncode == 0
    clipped = run_boxes(tmp_path, [text("half", 1700, 100)])                     # 1700 + 300 > 1920
    assert clipped.returncode == 1 and "text 'half' runs past the frame edge" in clipped.stdout
    assert run_boxes(tmp_path, [text("off", 2200, 100)]).returncode == 0         # fully off stage: not on screen at all


def test_frame_size_comes_from_the_file(tmp_path):
    boxes = [text("a", 700, 100)]                                                # 700 + 300 = 1000 > 960
    assert run_boxes(tmp_path, boxes, frame=(960, 540)).returncode == 1
    assert run_boxes(tmp_path, boxes, frame=(1920, 1080)).returncode == 0


def test_a_bare_list_of_boxes_is_one_sample(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps(GOOD), encoding="utf-8")
    assert py_script("check_clutter.py", "--boxes", f).returncode == 0


def test_failures_name_the_time_of_each_sample(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps([{"t": 1.0, "boxes": GOOD}, {"t": 4.5, "boxes": [card("a", 0, 0), card("b", 10, 10)]}]), encoding="utf-8")
    proc = py_script("check_clutter.py", "--boxes", f)
    assert proc.returncode == 1 and "t=4.5s" in proc.stdout and "t=1.0s" not in proc.stdout


# ---- pixels only -------------------------------------------------------------------------------------------------

def test_still_ink_touching_the_edge_fails_and_centred_text_passes(tmp_path):
    ok = text_png(tmp_path / "ok.png", ["TODO"], origin=(300, 300))
    assert py_script("check_clutter.py", "--still", ok, "--bg", "#ffffff").returncode == 0
    clipped = text_png(tmp_path / "clipped.png", ["TODO"], origin=(0, 300))
    proc = py_script("check_clutter.py", "--still", clipped, "--bg", "#ffffff")
    assert proc.returncode == 1 and "touches the left edge" in proc.stdout


# ---- the browser script and the --dom route ---------------------------------------------------------------------

PAGE = """<!doctype html><html><head><style>
body{margin:0;background:#101114;width:1920px;height:1080px;position:relative;font:48px sans-serif;color:#fff}
.card{position:absolute;background:#2a2a35;padding:20px}
h1{position:absolute;left:100px;top:60px;margin:0;font-size:90px}
</style></head><body>
<h1>Hello world</h1>
<div class="card" id="c1" style="left:100px;top:300px;width:600px;height:300px"><p>Card one</p></div>
<div class="card" id="c2" style="left:500px;top:450px;width:600px;height:300px;opacity:0"><p>Card two</p></div>
<script>window.__timelines = { main: { pause: function () {}, seek: function (t) { document.getElementById('c2').style.opacity = t >= 2 ? 1 : 0; } } };</script>
</body></html>"""


def test_dom_boxes_js_is_valid_javascript():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not found")
    proc = subprocess.run([node, "--check", str(SCRIPTS / "dom_boxes.js")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(clutter.find_chrome() is None or os.name == "nt", reason="needs Chrome, Chromium or Edge (not run on Windows)")
def test_dom_route_sees_a_card_appear_on_a_card(tmp_path):
    page = tmp_path / "index.html"
    page.write_text(PAGE, encoding="utf-8")
    before = py_script("check_clutter.py", "--dom", page, "--at", "1")
    assert before.returncode == 0, before.stdout + before.stderr
    after = py_script("check_clutter.py", "--dom", page, "--at", "1,3")
    assert after.returncode == 1 and "t=3s: card" in after.stdout, after.stdout + after.stderr


def test_dom_route_without_chrome_skips_with_a_message_and_exit_0(tmp_path, monkeypatch, capsys):
    page = tmp_path / "index.html"
    page.write_text(PAGE, encoding="utf-8")
    monkeypatch.setattr(clutter, "find_chrome", lambda: None)
    monkeypatch.setattr(sys, "argv", ["check_clutter.py", "--dom", str(page), "--at", "1"])
    assert clutter.main() == 0
    out = capsys.readouterr().out
    assert out.startswith("SKIP") and "Install Google Chrome" in out
