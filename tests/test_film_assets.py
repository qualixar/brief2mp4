"""film_assets.py: pictures, maps, effects and music for every beat, each recorded in ASSETS.json. Network mocked."""
from __future__ import annotations

import json

import pytest

import film_common as fc
import fetch_archive as fa
import film_assets as fas
import film_script as fs
import film_story as story
import film_storyboard as sbd
from film_lib import FilmError, Project

OPENVERSE = fc.recorded("openverse_images.json")

SCRIPT = """# Script
## L01
say: Nearly all data swims.
source: https://example.org/a
asset: assets/archive/ship.png
date: MARCH 1931

## L02
say: A cable runs from Alexandria to Aswan.
source: https://example.org/b
visual: map
region: Egypt
point: Alexandria=31.20,29.92
point: Aswan=24.09,32.90
route: Alexandria>Aswan

## L03
say: A cable ship lays it.
source: https://example.org/c
query: cable ship
region: Egypt
point: Cairo=30.04,31.24
"""


def storyboard():
    return sbd.build_storyboard(fs.parse_script(SCRIPT), story.parse_brief("a 20 second film"), "a 20 second film")


def project(tmp_path):
    p = Project(tmp_path)
    (tmp_path / "assets" / "archive").mkdir(parents=True)
    (tmp_path / "assets" / "archive" / "ship.png").write_bytes(fc.png_bytes())
    return p


def fake_network(monkeypatch):
    def get(url, retries=3, backoff=1.0, timeout=60, agent=None):
        if "openverse.org/v1/images" in url:
            return json.dumps(OPENVERSE).encode(), "application/json"
        if "commons.wikimedia.org" in url:
            raise fa.FetchError("HTTP 503 from test")                                        # one source down is fine
        return fc.png_bytes(), "image/png"
    monkeypatch.setattr(fa, "http_get", get)
    monkeypatch.setattr(fa.time, "sleep", lambda s: None)


def assets_by_kind(p, kind):
    return [a for a in json.loads(p.assets.read_text(encoding="utf-8"))["assets"] if a["kind"] == kind]


def test_a_picture_the_user_gave_is_recorded_as_supplied(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    out = fas.run_assets(p, storyboard(), fetch=True, delay=0)
    ship = next(a for a in assets_by_kind(p, "archive") if a["file"] == "assets/archive/ship.png")
    assert ship["licence_code"] == "user" and "supplied by the user" in ship["licence"] and len(ship["sha256"]) == 64
    assert out["beats"][0]["asset"] == "assets/archive/ship.png"


def test_a_query_is_fetched_licensed_and_recorded(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    out = fas.run_assets(p, storyboard(), delay=0)
    b3 = out["beats"][2]
    assert b3["kind"] == "archive" and b3["asset"].startswith("assets/archive/") and (tmp_path / b3["asset"]).is_file()
    entry = next(a for a in assets_by_kind(p, "archive") if a["file"] == b3["asset"])
    assert entry["licence_code"] in ("cc0", "pdm", "by") and entry["source_url"].startswith("http") and entry["author"] and entry["attribution"]


def test_without_a_picture_the_beat_becomes_a_title_and_says_so(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    out = fas.run_assets(p, storyboard(), fetch=False)
    b3 = out["beats"][2]
    assert b3["kind"] == "title" and b3["asset"] is None and b3["route"] == "hyperframes:title"
    assert any("B03" in w and "typeset title" in w for w in out["warnings"])


def test_when_nothing_licensed_is_found_the_beat_falls_back_the_same_way(tmp_path, monkeypatch):
    monkeypatch.setattr(fa, "http_get", lambda *a, **k: (json.dumps({"results": [], "query": {"pages": {}}}).encode(), "application/json"))
    monkeypatch.setattr(fa.time, "sleep", lambda s: None)
    out = fas.run_assets(project(tmp_path), storyboard(), delay=0)
    assert out["beats"][2]["kind"] == "title" and any("no public domain" in w for w in out["warnings"])


def test_maps_are_written_with_their_positions_and_credited_as_public_domain(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    out = fas.run_assets(p, storyboard(), delay=0)
    assert out["beats"][1]["map_file"] == "assets/maps/B02.svg" and (tmp_path / "assets/maps/B02.svg").is_file() and (tmp_path / "assets/maps/B02.json").is_file()
    assert out["beats"][2]["inset_file"] == "assets/maps/B03-inset.svg"
    maps = assets_by_kind(p, "map")
    assert len(maps) == 2 and all(m["licence"] == "Public domain" and "Natural Earth" in m["attribution"] for m in maps)
    meta = json.loads((tmp_path / "assets/maps/B02.json").read_text(encoding="utf-8"))
    assert meta["size"] == [1296, 740] and meta["routes"][0]["length"] > 100


def test_sound_effects_are_made_once_and_recorded(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    fas.run_assets(p, storyboard(), delay=0)
    manifest = (tmp_path / "assets" / "sfx" / "sfx.json")
    first = manifest.read_bytes()
    fas.run_assets(p, storyboard(), delay=0)
    assert manifest.read_bytes() == first and len(assets_by_kind(p, "sfx")) == 1


def test_every_asset_entry_has_a_licence_and_a_checksum(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    fas.run_assets(p, storyboard(), delay=0)
    for a in json.loads(p.assets.read_text(encoding="utf-8"))["assets"]:
        assert a["licence"] and a["licence_code"] and a["sha256"] and a["file"] and not a["file"].startswith("/"), a


def test_running_again_does_not_duplicate_entries(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    out = fas.run_assets(p, storyboard(), delay=0)
    fas.run_assets(p, out, delay=0)
    files = [a["file"] for a in json.loads(p.assets.read_text(encoding="utf-8"))["assets"]]
    assert len(files) == len(set(files))


def test_a_missing_user_picture_is_named(tmp_path):
    p = Project(tmp_path)
    with pytest.raises(FilmError, match="ship.png"):
        fas.run_assets(p, storyboard(), fetch=False)


def test_a_picture_outside_the_project_is_copied_in(tmp_path):
    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / "pic.png").write_bytes(fc.png_bytes())
    p = Project(tmp_path / "proj")
    (tmp_path / "proj").mkdir()
    sb = storyboard()
    sb["beats"][0]["asset"] = str(other / "pic.png")
    out = fas.run_assets(p, sb, fetch=False)
    assert out["beats"][0]["asset"] == "assets/archive/pic.png" and (tmp_path / "proj" / "assets/archive/pic.png").is_file()


def test_user_music_is_copied_into_the_project_and_recorded(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    (tmp_path / "ext").mkdir()
    (tmp_path / "proj").mkdir()
    track = fc.write_wav(tmp_path / "ext" / "bed.wav", [0.1] * 4800)
    p = Project(tmp_path / "proj")
    (tmp_path / "proj" / "assets" / "archive").mkdir(parents=True)
    (tmp_path / "proj" / "assets" / "archive" / "ship.png").write_bytes(fc.png_bytes())
    out = fas.run_assets(p, storyboard(), delay=0, music_file=track)
    assert out["music"] == "assets/music/bed.wav" and (tmp_path / "proj" / "assets/music/bed.wav").is_file()
    assert assets_by_kind(p, "music")[0]["licence_code"] == "user"


def test_musicgen_missing_says_how_to_install_and_the_licence(tmp_path, monkeypatch):
    class Done:
        returncode, stderr = 1, "ModuleNotFoundError: No module named 'audiocraft'"
    monkeypatch.setattr(fas.subprocess, "run", lambda *a, **k: Done())
    with pytest.raises(FilmError) as err:
        fas.musicgen(Project(tmp_path), "calm piano", 20)
    assert "pip install audiocraft" in str(err.value) and "CC BY-NC" in str(err.value)


def test_running_the_stage_again_keeps_every_cc_by_credit(tmp_path, monkeypatch):
    # run 1 downloads a CC BY picture for B03; run 2 (film.py assets again, or run --from assets) sees it as `asset:`
    # and must keep its licence, author and credit, never relabel it "supplied by the user"
    fake_network(monkeypatch)
    p = project(tmp_path)
    once = fas.run_assets(p, storyboard(), delay=0)
    b3 = once["beats"][2]["asset"]
    first = next(a for a in assets_by_kind(p, "archive") if a["file"] == b3)
    assert first["licence_code"] in ("by", "cc0", "pdm")
    twice = fas.run_assets(p, once, delay=0)
    again = next(a for a in assets_by_kind(p, "archive") if a["file"] == b3)
    assert {k: again[k] for k in ("licence", "licence_code", "author", "attribution", "credit_required", "source_url")} == \
           {k: first[k] for k in ("licence", "licence_code", "author", "attribution", "credit_required", "source_url")}
    fas.run_assets(p, twice, fetch=False, delay=0)                                                 # offline third run: same
    assert next(a for a in assets_by_kind(p, "archive") if a["file"] == b3)["licence_code"] == first["licence_code"]


def test_a_cc_by_credit_survives_a_rerun_even_when_the_file_was_moved(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    once = fas.run_assets(p, storyboard(), delay=0)
    src = tmp_path / once["beats"][2]["asset"]
    moved = tmp_path / "assets" / "archive" / "renamed.png"
    src.rename(moved)
    once["beats"][2]["asset"] = "assets/archive/renamed.png"
    fas.run_assets(p, once, delay=0)
    entry = next(a for a in assets_by_kind(p, "archive") if a["file"] == "assets/archive/renamed.png")
    assert entry["licence_code"] != "user" and entry["author"] != "supplied by the user"


def test_rerunning_does_not_repeat_warnings(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    once = fas.run_assets(p, storyboard(), fetch=False)
    twice = fas.run_assets(p, once, fetch=False)
    assert twice["warnings"] == once["warnings"] and len(twice["warnings"]) == len(set(twice["warnings"]))


def test_giving_a_downloaded_cc_by_track_again_as_music_keeps_its_credit(tmp_path, monkeypatch):
    fake_network(monkeypatch)
    p = project(tmp_path)
    (tmp_path / "assets" / "music").mkdir(parents=True)
    track = fc.write_wav(tmp_path / "assets" / "music" / "bed.wav", [0.1] * 4800)
    entry = {**fas._entry(p, track, "music"), "source": "openverse", "author": "A. Maker", "licence": "CC BY 4.0", "licence_code": "by",
             "attribution": '"Bed" by A. Maker, CC BY 4.0', "credit_required": True}
    p.assets.write_text(json.dumps({"version": 1, "assets": [entry]}), encoding="utf-8")
    fas.run_assets(p, storyboard(), delay=0, music_file=track)
    music = assets_by_kind(p, "music")
    assert len(music) == 1 and music[0]["licence_code"] == "by" and music[0]["credit_required"] is True
