"""film_build.py and the archive desk template: markup, data attributes, assets, acts, dips, credits, no network at render time."""
from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

import film_common as fc
import film_assets as fas
import film_build as fb
import film_script as fs
import film_story as story
import film_storyboard as sbd
import film_voice as fv
import retime as rt
from film_lib import FilmError, Project, load_json

SCRIPT = """# Script
pace: 150
format: documentary

## L01
say: Nearly all intercontinental data does not fly. It swims.
screen: UNDER THE SEA <&> MORE
source: https://example.org/a
asset: assets/archive/ship.png
date: MARCH 1931

## L02
say: A cable runs from Alexandria to Aswan.
screen: ALEXANDRIA TO ASWAN
source: https://example.org/b
visual: map
region: Egypt
point: Alexandria=31.20,29.92
point: Aswan=24.09,32.90
route: Alexandria>Aswan

## L03
say: About one point four million kilometres of cable lie on the seabed.
screen: ON THE SEABED
source: https://example.org/c
count: 0 -> 1400000 | km of cable
asset: assets/archive/ship.png
region: Egypt
point: Cairo=30.04,31.24

## L04
say: That is how the internet crosses an ocean.
screen: HOW IT CROSSES
source: https://example.org/d
"""


def make(tmp_path, acts=2, script=SCRIPT, cc_by=False):
    p = Project(tmp_path)
    (tmp_path / "assets" / "archive").mkdir(parents=True)
    (tmp_path / "assets" / "archive" / "ship.png").write_bytes(fc.png_bytes())
    sc = fs.parse_script(script)
    sb = sbd.build_storyboard(sc, story.parse_brief("a 20 second film"), "a 20 second film", acts=acts)
    sb = fas.run_assets(p, sb, fetch=False)
    if cc_by:
        data = json.loads(p.assets.read_text(encoding="utf-8"))
        for a in data["assets"]:
            if a["file"].endswith("ship.png"):
                a.update(licence="CC BY 4.0", licence_code="by", author="Ada Lovelace", source="wikimedia-commons", kind="archive")
        p.assets.write_text(json.dumps(data), encoding="utf-8")
    tm = fv.standin(sc, p.lines_dir, p.timings)
    sb = rt.retime(sb, tm)
    return p, sb, tm, load_json(p.assets)


def vendor_stub(tmp_path):
    (tmp_path / "vstub" / "vendor" / "fonts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vstub" / "vendor" / "gsap.min.js").write_text("/* gsap */", encoding="utf-8")
    (tmp_path / "vstub" / "vendor" / "fonts" / "fonts.css").write_text("", encoding="utf-8")
    return tmp_path / "vstub"


def build(tmp_path, act=None, **kw):
    p, sb, tm, assets = make(tmp_path, **{k: kw.pop(k) for k in ("acts", "cc_by") if k in kw})
    out = tmp_path / ("project" if act is None else f"act-{act}")
    info = fb.build_project(p, sb, tm, assets, out, act=act, vendor_from=vendor_stub(tmp_path), **kw)
    return p, sb, tm, out, info


def page(out):
    return (out / "index.html").read_text(encoding="utf-8")


# ---- the page --------------------------------------------------------------------------------------------------------

def test_one_section_per_beat_with_times_from_the_retimed_storyboard(tmp_path):
    p, sb, tm, out, info = build(tmp_path)
    html = page(out)
    assert re.findall(r'<section class="beat(?: first)?" id="(B\d\d)"', html) == ["B01", "B02", "B03", "B04"]
    for b in sb["beats"]:
        m = re.search(rf'id="{b["id"]}" data-t0="([0-9.]+)" data-t1="([0-9.]+)"', html)
        assert float(m.group(1)) == pytest.approx(b["start"], abs=1e-3) and float(m.group(2)) == pytest.approx(b["end"], abs=1e-3)
    assert html.count('class="beat first"') == 1 and 'class="beat first" id="B01"' in html


def test_root_duration_is_whole_frames_minus_a_millisecond(tmp_path):
    p, sb, tm, out, info = build(tmp_path)
    m = re.search(r'id="root"[^>]*data-duration="([0-9.]+)"', page(out))
    assert float(m.group(1)) == pytest.approx(sb["duration"] - 0.001, abs=1e-6) and info["frames"] == round(sb["duration"] * 30)


def test_text_is_escaped_and_the_stamp_counts_beats(tmp_path):
    _, _, _, out, _ = build(tmp_path)
    html = page(out)
    assert "UNDER THE SEA &lt;&amp;&gt; MORE" in html and "<&>" not in html
    assert 'No. 01 / 04<br />MARCH 1931' in html and "No. 04 / 04" in html


def test_a_picture_beat_has_a_picture_a_caption_and_no_title_block(tmp_path):
    _, _, _, out, _ = build(tmp_path)
    b1 = re.search(r'<section class="beat first" id="B01".*?</section>', page(out), re.S).group(0)
    assert '<img class="shot" src="assets/archive/ship.png"' in b1 and '<h2 class="caption">' in b1 and 'class="big"' not in b1
    b4 = re.search(r'<section class="beat" id="B04".*?</section>', page(out), re.S).group(0)
    assert 'class="plate title"' in b4 and '<h2 class="big">HOW IT CROSSES</h2>' in b4 and 'class="caption"' not in b4


def test_a_map_beat_inlines_its_svg_with_unique_ids(tmp_path):
    _, _, _, out, _ = build(tmp_path)
    html = page(out)
    assert 'id="B02-route-1"' in html and 'id="route-1"' not in html and '<?xml' not in html
    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert 'class="inset"' in html


def test_the_counter_ends_when_the_number_is_spoken(tmp_path):
    p, sb, tm, out, _ = build(tmp_path)
    b3 = sb["beats"][2]
    at, end = fb.counter_window(b3, tm)
    words = tm["lines"]["L03"]["words"]
    spoken_end = b3["line_starts"]["L03"] + next(w for w in words if w["text"] == "million")["end"] - b3["start"]
    assert end == pytest.approx(min(spoken_end, b3["duration"] - 0.4), abs=0.02) and at < end
    html = page(out)
    assert 'data-count-from="0" data-count-to="1400000"' in html and '<p class="ledger"><span class="n" style="font-size:68px">0</span><br /><span class="l">km of cable</span></p>' in html


def test_counter_window_on_known_words():
    beat = {"start": 10.0, "duration": 8.0, "line_starts": {"L1": 10.5}, "counter": {"line": "L1"}}
    timings = {"lines": {"L1": {"speech_start": 0.0, "speech_end": 4.0, "words": [{"text": "About", "start": 0.0, "end": 0.4}, {"text": "1.4", "start": 0.4, "end": 1.0},
                                                                          {"text": "million", "start": 1.0, "end": 1.6}, {"text": "km", "start": 1.6, "end": 2.0}]}}}
    at, end = fb.counter_window(beat, timings)
    assert at == pytest.approx(0.5) and end == pytest.approx(10.5 + 1.6 - 10.0)


def test_pictures_are_copied_and_paths_stay_relative(tmp_path):
    _, _, _, out, _ = build(tmp_path)
    assert (out / "assets" / "archive" / "ship.png").is_file()
    html = page(out)
    assert not re.search(r'(?:src|href)="(?:/|[A-Za-z]:|https?:)', html)


def test_credits_name_the_author_and_licence_of_a_cc_by_picture_only(tmp_path):
    _, _, _, out, _ = build(tmp_path, cc_by=True)
    html = page(out)
    assert '<p class="credit">Ada Lovelace / CC BY 4.0 / Wikimedia Commons</p>' in html
    _, _, _, out2, _ = build(tmp_path / "again")
    assert 'class="credit"' not in page(out2)                                       # a picture the user supplied needs none, and a map is public domain


def test_burned_captions_replace_the_credit_so_the_frame_stays_under_four_blocks(tmp_path):
    cues = [{"start": 1.0, "end": 2.5, "text": "Nearly all data\ndoes not fly.", "line": "L01"}]
    _, _, _, out, _ = build(tmp_path, cc_by=True, burn=True, cues=cues)
    html = page(out)
    assert '<p class="sub" data-t0="1.000" data-t1="2.500">Nearly all data<br />does not fly.</p>' in html and 'class="credit"' not in html


def test_not_burned_leaves_no_sub_elements(tmp_path):
    _, _, _, out, _ = build(tmp_path, cues=[{"start": 1.0, "end": 2.0, "text": "x", "line": "L01"}])
    assert 'class="sub"' not in page(out)


# ---- acts and dips ----------------------------------------------------------------------------------------------------

def test_each_act_builds_alone_with_times_shifted_to_zero(tmp_path):
    p, sb, tm, assets = make(tmp_path)
    acts = {a["id"]: a for a in sb["acts"]}
    assert len(acts) == 2
    total = 0
    for aid, a in acts.items():
        out = tmp_path / f"act{aid}"
        info = fb.build_project(p, sb, tm, assets, out, act=aid, vendor_from=vendor_stub(tmp_path))
        html = page(out)
        first = re.search(r'data-t0="([0-9.]+)"', html[html.index("<section"):])
        assert float(first.group(1)) == 0.0
        assert info["frames"] == round((a["end"] - a["start"]) * 30)
        total += info["frames"]
    assert total == round(sb["duration"] * 30)


def test_acts_dip_to_dark_so_separate_renders_meet_on_the_same_frame(tmp_path):
    p, sb, tm, assets = make(tmp_path)
    a1, a2 = sb["acts"]
    o1, o2 = tmp_path / "o1", tmp_path / "o2"
    fb.build_project(p, sb, tm, assets, o1, act="A1", vendor_from=vendor_stub(tmp_path))
    fb.build_project(p, sb, tm, assets, o2, act="A2", vendor_from=vendor_stub(tmp_path))
    last_of_1 = re.findall(r"<section[^>]*>", page(o1))[-1]
    first_of_2 = re.findall(r"<section[^>]*>", page(o2))[0]
    assert 'data-dip-out="0.4"' in last_of_1
    assert 'data-dip-in="0.4"' in first_of_2 and "beat first" not in first_of_2
    assert 'class="beat first"' in re.findall(r"<section[^>]*>", page(o1))[0]


def test_a_single_act_has_no_dip(tmp_path):
    _, _, _, out, _ = build(tmp_path, acts=1)
    assert not re.search(r'data-dip-(?:in|out)="', page(out))


def test_an_unretimed_storyboard_is_refused(tmp_path):
    p, sb, tm, assets = make(tmp_path)
    raw = sbd.build_storyboard(fs.parse_script(SCRIPT), story.parse_brief("x"), "x")
    with pytest.raises(FilmError, match="retime"):
        fb.build_project(p, raw, tm, assets, tmp_path / "o", vendor_from=vendor_stub(tmp_path))


def test_same_inputs_give_the_same_page(tmp_path):
    p, sb, tm, assets = make(tmp_path)
    fb.build_project(p, sb, tm, assets, tmp_path / "a", vendor_from=vendor_stub(tmp_path))
    fb.build_project(p, sb, tm, assets, tmp_path / "b", vendor_from=vendor_stub(tmp_path))
    assert page(tmp_path / "a") == page(tmp_path / "b")


def test_hyperframes_files_are_written(tmp_path):
    _, _, _, out, _ = build(tmp_path)
    assert json.loads((out / "hyperframes.json").read_text(encoding="utf-8")) and json.loads((out / "meta.json").read_text(encoding="utf-8"))["id"].startswith("film-")
    assert (out / "vendor" / "gsap.min.js").is_file() and (out / "film.css").is_file()
    assert 'window.__timelines["main"] = tl' in page(out) and 'src="film.js"' not in page(out)             # the timeline registration is on the page itself


# ---- the template ----------------------------------------------------------------------------------------------------

TEMPLATE_FILES = [fc.TEMPLATES / n for n in ("index.html", "film.css", "film.js")]


@pytest.mark.parametrize("path", TEMPLATE_FILES, ids=lambda p: p.name)
def test_template_is_self_contained_and_a_pure_function_of_time(path):
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"https?://", text.replace("http://www.w3.org", "")), "no CDN or network reference"
    for banned in ("Math.random", "Date.now", "new Date", "requestAnimationFrame", "setTimeout", "setInterval", "fetch(", "pathLength", "backdrop-filter", "@import"):
        assert banned not in text, banned
    assert "\r" not in text and len(text.splitlines()) <= 400


def test_template_keeps_text_blocks_and_safe_margins():
    css = (fc.TEMPLATES / "film.css").read_text(encoding="utf-8")
    assert "left: 96px" in css and "top: 54px" in css                                       # the 5% safe margins at 1080p
    caption = re.search(r"\.caption \{[^}]*\}", css).group(0)
    assert "58px" in caption and int(re.search(r"font: 400 (\d+)px", caption).group(1)) >= 40


@pytest.mark.skipif(shutil.which("node") is None, reason="node not found")
def test_film_js_parses():
    assert subprocess.run(["node", "--check", str(fc.TEMPLATES / "film.js")], capture_output=True).returncode == 0


def test_the_looks_page_names_the_archive_desk_in_the_art_form_list_of_the_router():
    import art_route
    assert art_route.route("an archive documentary with stills and a map")["form"] == "archive-documentary"


def test_map_land_reaches_past_the_view_so_a_push_in_from_below_scale_1_shows_no_edge(tmp_path):
    css = (fc.TEMPLATES / "film.css").read_text(encoding="utf-8")
    assert re.search(r"\.plate \.mapbox svg \{[^}]*overflow: visible", css), "the map svg must not clip its own land at the viewBox"
    p, sb, tm, out, _ = build(tmp_path)
    svg = (tmp_path / "assets" / "maps" / "B02.svg").read_text(encoding="utf-8")
    xs = [float(v) for v in re.findall(r"[ML](-?[\d.]+) ", " ".join(re.findall(r'class="mm-(?:land|ctx|hl)"[^>]* d="([^"]+)"', svg)))]
    assert min(xs) < 0 and max(xs) > 1296, "land is drawn past both sides of the plate's view"


def chrome():
    import check_clutter
    return check_clutter.find_chrome()


@pytest.mark.skipif(chrome() is None, reason="needs Chrome, Chromium or Edge")
def test_a_date_stamp_with_an_ampersand_types_one_character_not_an_entity(tmp_path):
    js = (fc.TEMPLATES / "film.js").read_text(encoding="utf-8")
    stub = "window.gsap={timeline:function(){var t={fromTo:function(){return t},to:function(){return t},set:function(){return t}};return t}};"
    page = tmp_path / "p.html"
    page.write_text(f'<!doctype html><html><body><section class="beat" data-t0="0" data-t1="2"><p class="stamp">No. 01 / 01<br />R&amp;D &lt;1931&gt;</p>'
                    f"</section><script>{stub}</script><script>{js}</script></body></html>", encoding="utf-8")
    dom = subprocess.run([chrome(), "--headless=new", "--disable-gpu", f"--user-data-dir={tmp_path / 'prof'}", "--dump-dom", page.as_uri()],
                         capture_output=True, text=True, timeout=60).stdout
    chars = re.findall(r'<span class="ch">(.*?)</span>', dom)
    assert "".join(chars) == "No. 01 / 01R&amp;D &lt;1931&gt;", chars                       # one span per visible character
    assert chars.count("&amp;") == 1 and "<br>" in dom.split('class="stamp"', 1)[1]
