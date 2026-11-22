"""film_story.py and film_storyboard.py: BRIEF.md to STORY.md, SCRIPT.md to STORYBOARD.json."""
from __future__ import annotations

import json

import pytest

import film_common  # noqa: F401  (puts scripts/ on the path)
import film_script as fs
import film_story as story
import film_storyboard as sbd
from film_lib import FilmError

BRIEF = """# How undersea cables carry the internet

Make a 20-second explainer on how undersea cables carry the internet, documentary look, with a generated voice.

audience: curious people who use the internet every day
takeaway: nearly all intercontinental data travels under the sea
"""

SCRIPT = """# Script
pace: 150
format: documentary

## L01
say: Nearly all intercontinental data does not fly. It swims.
screen: UNDER THE SEA
source: https://example.org/a
visual: archive
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
say: About one point four million kilometres lie on the seabed.
screen: ON THE SEABED
source: https://example.org/c
count: 0 -> 1400000 | km of cable
asset: assets/archive/ship.png

## L04
say: That is how the internet crosses an ocean.
screen: HOW IT CROSSES
source: https://example.org/d
beat: 4

## L05
say: It is a very long wire.
screen: A LONG WIRE
source: https://example.org/e
beat: 4
"""


def sb(**kw):
    return sbd.build_storyboard(fs.parse_script(SCRIPT), story.parse_brief(BRIEF), BRIEF, **kw)


# ---- the brief and the story ----------------------------------------------------------------------------------------

def test_brief_fields_are_read_from_keys_and_prose():
    b = story.parse_brief(BRIEF)
    assert b["title"] == "How undersea cables carry the internet" and b["seconds"] == 20 and b["format"] == "documentary"
    assert b["voice"] == "f5-tts" and b["audience"].startswith("curious people") and b["takeaway"].startswith("nearly all")


@pytest.mark.parametrize("text,seconds", [("a 3-minute explainer", 180), ("make it 90 seconds", 90), ("length: 45 s", 45), ("about 2 minutes long", 120), ("no length given", 180)])
def test_length_in_minutes_or_seconds(text, seconds):
    assert story.parse_brief(text)["seconds"] == seconds


@pytest.mark.parametrize("text,voice", [("my voice from take.wav", "take"), ("use my recording", "take"), ("a generated voice", "f5-tts"), ("draft please", "standin")])
def test_voice_choice(text, voice):
    assert story.parse_brief(text)["voice"] == voice


def test_story_has_the_act_structure_with_a_hook_in_the_first_five_seconds():
    text = story.derive_story(BRIEF)
    for part in ("Hook", "Setup", "Beat 1", "Beat 2", "Beat 3", "Turn", "Payoff"):
        assert part in text
    assert "0-5 s" in text and "logline:" in text and "takeaway: nearly all" in text and "pace: 150" in text
    rows = story.act_table(180)
    assert rows[0] == ("Hook", 0, 5) and rows[-1][2] == 180 and all(a[2] == b[1] for a, b in zip(rows, rows[1:]))


def test_story_scaffold_never_overwrites_an_edited_story(tmp_path):
    (tmp_path / "BRIEF.md").write_text(BRIEF, encoding="utf-8")
    (tmp_path / "STORY.md").write_text("my edited story", encoding="utf-8")
    assert story.write_story(tmp_path / "BRIEF.md", tmp_path / "STORY.md") is False
    assert (tmp_path / "STORY.md").read_text(encoding="utf-8") == "my edited story"
    assert story.write_story(tmp_path / "BRIEF.md", tmp_path / "STORY.md", force=True) is True


def test_story_fields_read_back():
    assert story.read_story_fields(story.derive_story(BRIEF))["voice"] == "f5-tts"


# ---- the storyboard -------------------------------------------------------------------------------------------------

def test_lines_with_the_same_beat_number_share_a_beat():
    s = sb()
    assert [b["lines"] for b in s["beats"]] == [["L01"], ["L02"], ["L03"], ["L04", "L05"]]
    assert s["beats"][3]["caption"] == "HOW IT CROSSES A LONG WIRE"


def test_a_beat_number_that_comes_back_later_is_an_error():
    bad2 = SCRIPT.replace("## L01\n", "## L01\nbeat: 3\n").replace("## L02\n", "## L02\nbeat: 4\n").replace("## L03\n", "## L03\nbeat: 3\n")
    with pytest.raises(FilmError, match="beat 3"):
        sbd.build_storyboard(fs.parse_script(bad2), story.parse_brief(BRIEF), BRIEF)


def test_each_beat_gets_a_kind_and_its_pieces():
    b = sb()["beats"]
    assert [x["kind"] for x in b] == ["archive", "map", "archive", "title"]
    assert b[0]["asset"] == "assets/archive/ship.png" and b[0]["date"] == "MARCH 1931" and b[0]["route"] == "hyperframes:archive-still"
    assert b[1]["map"] == {"region": "Egypt", "points": ["Alexandria=31.20,29.92", "Aswan=24.09,32.90"], "routes": ["Alexandria>Aswan"]} and b[1]["route"] == "hyperframes:map"
    assert b[2]["counter"] == {"from": 0.0, "to": 1400000.0, "label": "km of cable", "line": "L03"}
    assert b[3]["asset"] is None and b[3]["route"] == "hyperframes:title"


def test_a_beat_with_a_picture_and_a_region_gets_an_inset_map():
    text = SCRIPT.replace("## L01\n", "## L01\nregion: Egypt\npoint: Cairo=30.04,31.24\n")
    b = sbd.build_storyboard(fs.parse_script(text), story.parse_brief(BRIEF), BRIEF)["beats"][0]
    assert b["kind"] == "archive" and b["inset"] == {"region": "Egypt", "points": ["Cairo=30.04,31.24"], "routes": []}


def test_the_camera_has_the_same_velocity_in_every_beat_so_hard_cuts_are_matched():
    s = sb()
    assert sbd.velocity_problems(s) == []
    cams = [b["camera"] for b in s["beats"]]
    assert len({(c["rate"], c["vx"], c["vy"]) for c in cams}) == 1
    assert len({(c["fx"], c["fy"]) for c in cams}) > 1                                   # but each beat looks at a different part of its picture


def test_a_mismatched_hard_cut_is_reported():
    s = sb()
    s["beats"][2]["camera"] = {**s["beats"][2]["camera"], "vx": 10}
    assert any("B02" in p and "B03" in p for p in sbd.velocity_problems(s))
    s = sb()
    s["beats"][2]["camera"] = {**s["beats"][2]["camera"], "vx": 10}
    for i in (2, 3):                                                                     # the cuts into and out of the odd beat
        s["beats"][i]["transition"] = {"type": "dip", "duration": 0.4, "meaning": "time passes"}
    assert sbd.velocity_problems(s) == []                                                # a dip hides a change of motion


def test_transitions_carry_their_meaning_and_acts_change_with_a_dip():
    s = sb(acts=2)
    t = [b["transition"] for b in s["beats"]]
    assert t[0]["type"] == "none" and all(x["meaning"] for x in t[1:])
    assert {b["act"] for b in s["beats"]} == {"A1", "A2"}
    first_of_act2 = next(i for i, b in enumerate(s["beats"]) if b["act"] == "A2")
    assert t[first_of_act2]["type"] == "dip" and all(x["type"] == "hard-cut" for i, x in enumerate(t) if i not in (0, first_of_act2))
    assert [a["beats"] for a in s["acts"]] == [[b["id"] for b in s["beats"] if b["act"] == a] for a in ("A1", "A2")]


def test_sound_cues_follow_the_beat_kind():
    s = sb()["beats"]
    cues = lambda i: [c["cue"] for c in s[i]["sound"]]
    assert "hit" in cues(0) and "typewriter" in cues(0)                                  # cold open and a date being typed
    assert "whoosh" in cues(1)                                                           # the route starts drawing
    assert "tick" in cues(2)                                                             # the counter
    assert "thud" in cues(3)                                                             # the last beat lands
    assert all(len(b["sound"]) <= 3 for b in s)
    assert all(c["at"] in ("start", "end") or c["at"].startswith("line:") for b in s for c in b["sound"])


def test_acts_default_follows_the_length():
    assert len({b["act"] for b in sb()["beats"]}) == 1                                   # a short film is one act
    long = fs.parse_script("\n".join(f"## L{i:02d}\nsay: {'word ' * 20}\nsource: https://example.org/{i}\nquery: thing {i}\n" for i in range(1, 25)))
    s = sbd.build_storyboard(long, story.parse_brief("a 3-minute film"), "a 3-minute film")
    assert 3 <= len(s["acts"]) <= 6


def test_art_form_comes_from_the_router_and_the_look_is_the_archive_desk():
    s = sb()
    assert s["look"] == "archive-desk" and s["art_form"] == "archive-documentary" and s["fps"] == 30 and s["size"] == [1920, 1080]
    assert sb()["format"] == "documentary" and s["pace"] == 150


def test_another_look_is_explained_not_faked():
    with pytest.raises(FilmError, match="archive desk"):
        sbd.build_storyboard(fs.parse_script(SCRIPT), story.parse_brief(BRIEF + "\nlook: claymation\n"), BRIEF, look="claymation")


def test_estimated_durations_are_there_for_planning():
    s = sb()
    assert all(b["duration"] > 0 for b in s["beats"]) and s["duration"] == pytest.approx(sum(b["duration"] for b in s["beats"]))


def test_caption_longer_than_two_lines_is_warned():
    text = SCRIPT.replace("screen: UNDER THE SEA", "screen: " + "WORD " * 20)
    s = sbd.build_storyboard(fs.parse_script(text), story.parse_brief(BRIEF), BRIEF)
    assert any("B01" in w and "caption" in w for w in s["warnings"])


def test_storyboard_is_plain_json():
    json.dumps(sb())


@pytest.mark.parametrize("brief,seconds", [
    ("a documentary about how the 1950s changed television", 180), ("the 50s and 60s in pictures", 180),
    ("a 20-second explainer", 20), ("make it 3 minutes long", 180), ("about 90 s", 90), ("a 2.5 min film", 150), ("a 45 sec teaser", 45)])
def test_lengths_are_read_but_decades_and_years_are_not(brief, seconds):
    assert story.parse_brief(brief)["seconds"] == seconds


@pytest.mark.parametrize("brief,voice", [
    ("what people take away from the first recorded flight", "standin"), ("a recorded history of radio", "standin"),
    ("use my voice for the narration", "take"), ("I will record it myself", "take"), ("my recording is take.wav", "take"),
    ("narration from narration-final.m4a", "take"), ("my own take on the story", "take")])
def test_the_users_recording_is_asked_for_only_when_the_brief_says_so(brief, voice):
    assert story.parse_brief(brief)["voice"] == voice
