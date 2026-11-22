"""film_script.py: SCRIPT.md parsing, estimates, sources and the UNVERIFIED rule."""
from __future__ import annotations

import pytest

import film_common  # noqa: F401  (puts scripts/ on the path)
import film_script as fs
from film_lib import FilmError

SCRIPT = """# Script
pace: 150
format: explainer

## L01
say: Ninety-nine percent of intercontinental data does not fly. It swims.
screen: UNDER THE SEA
source: https://example.org/a, https://example.org/b
visual: archive
query: submarine cable ship
date: MARCH 1931

## L02
say: A cable runs from Alexandria
  to Aswan.
visual: map
region: Egypt
point: Alexandria=31.20,29.92
point: Aswan=24.09,32.90
route: Alexandria>Aswan
source: https://example.org/c
beat: 2

## L03
say: About a million kilometres of it lie on the seabed.
visual: counter
count: 0 -> 1400000 | km of cable
"""


def test_parse_reads_header_blocks_and_lists():
    s = fs.parse_script(SCRIPT)
    assert s.pace == 150 and s.meta["format"] == "explainer" and [l["id"] for l in s.lines] == ["L01", "L02", "L03"]
    l1, l2, l3 = s.lines
    assert l1["screen"] == "UNDER THE SEA" and l1["sources"] == ["https://example.org/a", "https://example.org/b"] and l1["date"] == "MARCH 1931"
    assert l2["say"] == "A cable runs from Alexandria to Aswan." and l2["points"] == ["Alexandria=31.20,29.92", "Aswan=24.09,32.90"] and l2["routes"] == ["Alexandria>Aswan"]
    assert l3["count"].startswith("0 -> 1400000") and l2["beat"] == "2"


def test_a_line_without_a_source_is_unverified_and_listed():
    s = fs.parse_script(SCRIPT)
    assert fs.unverified(s) == ["L03"]
    errors, warnings = fs.check_script(s)
    assert errors == [] and any("L03" in w and "UNVERIFIED" in w for w in warnings)


def test_the_word_unverified_as_the_source_counts_as_no_source():
    s = fs.parse_script("## L01\nsay: Hello there.\nsource: UNVERIFIED\n")
    assert fs.unverified(s) == ["L01"]


def test_estimate_is_words_at_the_pace_plus_sentence_pauses():
    assert fs.estimate_seconds("one two three four five", 150) == pytest.approx(2.0)
    assert fs.estimate_seconds("one two three four five.", 150) == pytest.approx(2.3)
    assert fs.estimate_seconds("a b, c d", 120) == pytest.approx(2.0 + 0.12)
    assert fs.estimate_seconds("x " * 30, 170) < fs.estimate_seconds("x " * 30, 150)         # a Short is read faster


@pytest.mark.parametrize("text,msg", [("## L01\nsource: https://x.org\n", "no 'say:'"), ("## L1x\nsay: hi\n", "ids look like"),
                                      ("## L01\nsay: a\n## L01\nsay: b\n", "used twice"), ("## L01\nsay: a\nvisual: hologram\n", "not one of"),
                                      ("# Script\n", "no lines")])
def test_check_reports_each_mistake(text, msg):
    errors, _ = fs.check_script(fs.parse_script(text))
    assert any(msg in e for e in errors), errors


def test_unknown_key_and_stray_text_are_explained():
    with pytest.raises(FilmError, match="unknown key 'colour'"):
        fs.parse_script("## L01\ncolour: red\nsay: hi\n")
    with pytest.raises(FilmError, match="key: value"):
        fs.parse_script("## L01\n- just a bullet\n")


def test_tokens_ignore_case_and_punctuation():
    assert fs.norm_token("Ninety-nine,") == "ninetynine" and fs.norm_token("99%") == "99"


def test_read_script_missing_file(tmp_path):
    with pytest.raises(FilmError, match="SCRIPT.md not found"):
        fs.read_script(tmp_path / "SCRIPT.md")


@pytest.mark.parametrize("source,unverified", [("https://", True), ("https://x", True), ("http:// example.org", True), ("UNVERIFIED", True),
                                               ("https://example.org/a", False), ("see https://en.wikipedia.org/wiki/X and https://example.org", False)])
def test_a_source_needs_a_real_host(source, unverified):
    line = fs.parse_script(f"## L01\nsay: A fact.\nsource: {source}\n").lines[0]
    assert line["unverified"] is unverified


def test_source_none_marks_a_line_with_no_claim_and_the_report_lists_it():
    script = fs.parse_script("## L01\nsay: Then it failed.\nsource: none (no factual claim)\n\n## L02\nsay: A fact.\n")
    assert fs.unverified(script) == ["L02"] and fs.no_claim(script) == ["L01"]
