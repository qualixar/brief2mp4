"""make_map.py: a country or region map from the shipped Natural Earth subset, markers, labels, routes; clear errors."""
from __future__ import annotations

import gzip
import json
import math
import re
import sys
import xml.etree.ElementTree as ET

import pytest

import film_common as fc
import make_map as mm
from make_map import MapError

SVG = "{http://www.w3.org/2000/svg}"
DATA_FILE = fc.SKILL / "data" / "ne_110m_countries.json.gz"


def build(region="Egypt", points=(), routes=(), **kw):
    return mm.build_map(region, list(points), list(routes), **kw)


def parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)


# ---- the data we ship -------------------------------------------------------------------------------------------------

def test_shipped_subset_is_small_and_credited():
    assert DATA_FILE.stat().st_size < 300 * 1024
    countries = json.loads(gzip.decompress(DATA_FILE.read_bytes()))
    assert len(countries) > 150 and {"n", "a", "i", "c", "g"} <= set(countries[0])
    note = (fc.SKILL / "data" / "NATURAL-EARTH.md").read_text(encoding="utf-8")
    assert "public domain" in note and "sha-256" in note.lower() and "naturalearthdata.com" in note


# ---- a known country renders -------------------------------------------------------------------------------------------

def test_known_country_renders_a_valid_svg_with_land_and_a_title():
    svg, meta = build("Egypt")
    root = parse(svg)
    assert root.tag == SVG + "svg" and root.get("viewBox") == "0 0 1600 900"
    hl = [p for p in root.iter(SVG + "path") if "mm-hl" in (p.get("class") or "")]
    assert hl and len(hl[0].get("d")) > 200
    assert root.find(SVG + "title").text == "Map of Egypt"
    assert meta["region"] == "Egypt" and meta["projection"]["name"] in {"albers", "mercator"}


@pytest.mark.parametrize("name,canonical", [("USA", "United States of America"), ("United States", "United States of America"), ("uk", "United Kingdom"),
                                            ("Ivory Coast", "Ivory Coast"), ("egypt", "Egypt"), ("  FRANCE ", "France"), ("Türkiye", "Turkey"),
                                            ("DRC", "Democratic Republic of the Congo"), ("Czech Republic", "Czechia")])
def test_names_aliases_and_codes_resolve(name, canonical):
    region = mm.resolve_region(name, mm.load_countries())
    assert [c["a"] for c in region.selected] == [canonical]


def test_several_countries_a_continent_and_the_world():
    c = mm.load_countries()
    assert {x["a"] for x in mm.resolve_region("France, Spain", c).selected} == {"France", "Spain"}
    africa = mm.resolve_region("Africa", c)
    assert len(africa.selected) > 40 and all(x["c"] == "Africa" for x in africa.selected)
    assert len(mm.resolve_region("world", c).selected) == len(c)


def test_unknown_name_errors_clearly_and_suggests_the_close_one():
    with pytest.raises(MapError) as err:
        build("Egyptt")
    text = str(err.value)
    assert "Egyptt" in text and "Egypt" in text and "Did you mean" in text


def test_unknown_name_with_no_close_match_says_how_to_list_names():
    with pytest.raises(MapError, match="--list"):
        build("Zzzzland")


def test_cli_unknown_country_exits_1_with_a_fail_line(tmp_path):
    proc = fc.py_script("make_map.py", "--region", "Narnia", "--out", tmp_path / "x.svg")
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL") and "Narnia" in proc.stdout and not (tmp_path / "x.svg").exists()


def test_bbox_region_and_bad_bbox():
    svg, meta = build("bbox:-10,30,40,60")
    assert parse(svg).get("viewBox") and meta["bbox"][0] <= -10
    with pytest.raises(MapError, match="bbox"):
        build("bbox:10,20,5,30")


# ---- projections --------------------------------------------------------------------------------------------------------

def test_projection_is_chosen_for_the_region():
    assert mm.choose_projection((-180, -60, 180, 80))[0] == "equal_earth"                 # the world
    assert mm.choose_projection((-125, 25, -66, 49))[0] == "albers"                       # the lower 48: wide, mid latitudes
    assert mm.choose_projection((-74, -34, -34, 5))[0] == "mercator"                      # Brazil: near the equator
    assert mm.choose_projection((2, 49, 8, 52))[0] == "mercator"                          # a small area is local


def test_projection_maths_known_values():
    ee = mm.projector("equal_earth", {"lon0": 0})
    assert ee(180, 0)[0] == pytest.approx(2.70663, abs=1e-4) and ee(0, 90)[1] == pytest.approx(1.31736, abs=1e-4)
    mer = mm.projector("mercator", {"lon0": 0})
    assert mer(0, 0) == (0.0, 0.0) and mer(0, 45)[1] == pytest.approx(math.log(math.tan(math.pi / 4 + math.radians(45) / 2)))
    alb = mm.projector("albers", {"lon0": -96, "lat0": 37.5, "phi1": 29.5, "phi2": 45.5})
    assert alb(-96, 37.5)[0] == pytest.approx(0, abs=1e-9)
    assert alb(-90, 37.5)[0] > 0 > alb(-100, 37.5)[0]


def test_north_is_up_and_east_is_right():
    svg, meta = build("bbox:0,0,40,40", points=["West=20,5", "East=20,35", "North=38,20", "South=2,20"])
    m = {p["name"]: p for p in meta["markers"]}
    assert m["East"]["x"] > m["West"]["x"] and m["North"]["y"] < m["South"]["y"]


def test_a_country_far_flung_pieces_do_not_stretch_the_map():
    _, meta = build("France")
    assert meta["bbox"][0] > -10 and meta["bbox"][2] < 12                                  # mainland, not French Guiana


# ---- markers, labels, routes ---------------------------------------------------------------------------------------------

POINTS = ["Alexandria=31.20,29.92", "Cairo=30.04,31.24", "Aswan=24.09,32.90"]


def test_markers_and_labels_are_drawn_inside_the_frame():
    svg, meta = build("Egypt", POINTS)
    root = parse(svg)
    labels = [t.text for t in root.iter(SVG + "text")]
    assert {"Alexandria", "Cairo", "Aswan"} <= set(labels)
    assert len([c for c in root.iter(SVG + "circle") if "mm-dot" in (c.get("class") or "")]) == 3
    for p in meta["markers"]:
        assert 0 <= p["x"] <= 1600 and 0 <= p["y"] <= 900


def test_close_labels_do_not_overlap():
    _, meta = build("Egypt", ["A Place=30.00,31.00", "B Place=30.05,31.05", "C Place=30.10,31.02"])
    boxes = [(l["x"], l["y"], l["w"], l["h"]) for l in meta["labels"]]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]


def test_route_is_a_curved_path_with_its_pixel_length_for_the_draw_on():
    svg, meta = build("Egypt", POINTS, ["Alexandria>Cairo>Aswan"])
    root = parse(svg)
    route = next(p for p in root.iter(SVG + "path") if "mm-route" in (p.get("class") or ""))
    assert route.get("id") == "route-1" and float(route.get("data-len")) > 100
    assert route.get("data-from") == "Alexandria" and route.get("data-to") == "Aswan"
    m = {p["name"]: p for p in meta["markers"]}
    straight = sum(math.dist((m[a]["x"], m[a]["y"]), (m[b]["x"], m[b]["y"])) for a, b in (("Alexandria", "Cairo"), ("Cairo", "Aswan")))
    assert meta["routes"][0]["length"] > straight * 0.99                                  # an arc is never shorter than the line
    assert meta["routes"][0]["points"] == ["Alexandria", "Cairo", "Aswan"]


def test_route_to_a_point_that_does_not_exist_errors():
    with pytest.raises(MapError, match="Luxor"):
        build("Egypt", POINTS, ["Cairo>Luxor"])


@pytest.mark.parametrize("bad", ["Nowhere=91,10", "Nowhere=10,181", "Nowhere", "Nowhere=a,b", "=1,2"])
def test_bad_points_error(bad):
    with pytest.raises(MapError):
        build("Egypt", [bad])


def test_text_in_labels_is_escaped():
    svg, _ = build("Egypt", ["A & B <x>=30,31"])
    parse(svg)                                                                              # still well-formed
    assert "A &amp; B &lt;x&gt;" in svg


def test_same_input_gives_the_same_bytes():
    assert build("Egypt", POINTS, ["Alexandria>Cairo"])[0] == build("Egypt", POINTS, ["Alexandria>Cairo"])[0]


def test_world_map_leaves_out_antarctica_but_asking_for_it_works():
    assert 'data-name="Antarctica"' not in build("world")[0]
    assert 'data-name="Antarctica"' in build("Antarctica")[0]


def test_far_countries_cannot_fill_a_conic_map():
    svg, _ = build("USA")                                                                   # Antarctica in a conic projection used to cover the frame
    assert 'data-name="Antarctica"' not in svg


def test_svg_stays_small_enough_to_inline():
    assert len(build("world")[0].encode()) < 250_000 and len(build("Egypt")[0].encode()) < 120_000


def test_custom_geojson_overrides_the_shipped_data(tmp_path):
    gj = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"NAME": "Squareland", "ADMIN": "Squareland", "ISO_A3": "SQR", "CONTINENT": "Asia"},
                                                      "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}}]}
    path = tmp_path / "x.geojson"
    path.write_text(json.dumps(gj), encoding="utf-8")
    svg, meta = mm.build_map("Squareland", [], [], countries=mm.load_countries(path))
    assert meta["region"] == "Squareland" and parse(svg).tag == SVG + "svg"


def test_cli_writes_svg_and_meta_and_list(tmp_path):
    out = tmp_path / "m.svg"
    proc = fc.py_script("make_map.py", "--region", "Egypt", "--point", "Cairo=30.04,31.24", "--point", "Aswan=24.09,32.90",
                        "--route", "Cairo>Aswan", "--out", out)
    assert proc.returncode == 0 and proc.stdout.startswith("PASS"), proc.stdout + proc.stderr
    assert parse(out.read_text(encoding="utf-8")).tag == SVG + "svg"
    meta = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["routes"][0]["length"] > 100
    listing = fc.py_script("make_map.py", "--list")
    assert "Egypt" in listing.stdout and "Africa" in listing.stdout


def test_no_geojson_download_and_no_network_use():
    text = (fc.SCRIPTS / "make_map.py").read_text(encoding="utf-8")
    assert "urllib" not in text and "socket" not in text and "urlopen" not in text
