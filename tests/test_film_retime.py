"""retime.py: the picture is re-timed to the measured voice. Arithmetic checked by hand."""
from __future__ import annotations

import json

import pytest

import film_common as fc
import retime as rt
from film_lib import FilmError

TIMINGS = {"lines": {
    "L01": {"duration": 2.0, "speech_start": 0.0, "speech_end": 2.0},
    "L02": {"duration": 1.5, "speech_start": 0.0, "speech_end": 1.5},
    "L03": {"duration": 3.0, "speech_start": 0.0, "speech_end": 3.0},
    "L04": {"duration": 2.5, "speech_start": 0.1, "speech_end": 2.4}}}


def board(**over):
    sb = {"version": 1, "fps": 30, "acts": [{"id": "A1", "beats": ["B01", "B02"]}, {"id": "A2", "beats": ["B03"]}],
          "beats": [{"id": "B01", "act": "A1", "lines": ["L01", "L02"], "caption": "ONE", "sound": [{"cue": "hit", "at": "start"}, {"cue": "tick", "at": "line:L02", "offset": -0.05}]},
                    {"id": "B02", "act": "A1", "lines": ["L03"], "caption": "TWO", "sound": [{"cue": "whoosh", "at": "end", "offset": -0.1}]},
                    {"id": "B03", "act": "A2", "lines": ["L04"], "caption": "THREE"}]}
    sb.update(over)
    return sb


ARGS = dict(gap_line=0.30, gap_beat=0.40, gap_act=1.0, lead=0.30, end_hold=1.8, min_beat=2.0)


def test_line_starts_follow_the_measured_voice_plus_breaths():
    out = rt.retime(board(), TIMINGS, **ARGS)
    b1, b2, b3 = out["beats"]
    assert b1["line_starts"] == {"L01": pytest.approx(0.3), "L02": pytest.approx(2.6)}              # lead 0.3; then 0.30 s after L01 ends at 2.3
    assert b2["line_starts"] == {"L03": pytest.approx(4.5)}                                         # 0.40 s after L02 ends at 4.1
    assert b3["line_starts"] == {"L04": pytest.approx(8.4)}                                         # 1.0 s after L03 ends at 7.5, minus the 0.1 s in the file before the voice


def test_beat_cuts_fall_in_the_middle_of_the_breath_and_on_frames():
    out = rt.retime(board(), TIMINGS, **ARGS)
    assert [b["start"] for b in out["beats"]] == [pytest.approx(0.0), pytest.approx(4.3), pytest.approx(8.0)]
    assert [b["duration"] for b in out["beats"]] == [pytest.approx(4.3), pytest.approx(3.7), pytest.approx(4.6)]
    assert out["duration"] == pytest.approx(12.6)                                                   # last speech ends at 10.8, then the 1.8 s hold
    assert all(abs(b["start"] * 30 - round(b["start"] * 30)) < 1e-6 for b in out["beats"]) and abs(out["duration"] * 30 - round(out["duration"] * 30)) < 1e-6


def test_acts_get_their_span():
    out = rt.retime(board(), TIMINGS, **ARGS)
    assert [(a["id"], a["start"], a["end"]) for a in out["acts"]] == [("A1", pytest.approx(0.0), pytest.approx(8.0)), ("A2", pytest.approx(8.0), pytest.approx(12.6))]


def test_sound_cues_are_resolved_to_film_time():
    out = rt.retime(board(), TIMINGS, **ARGS)
    cues = {(c["cue"], round(c["t"], 3)) for b in out["beats"] for c in b.get("sound", [])}
    assert cues == {("hit", 0.0), ("tick", 2.55), ("whoosh", 7.9)}                                  # start; L02 starts at 2.6, -0.05; B02 ends at 8.0, -0.1


def test_the_input_is_not_changed():
    sb = board()
    before = json.dumps(sb, sort_keys=True)
    rt.retime(sb, TIMINGS, **ARGS)
    assert json.dumps(sb, sort_keys=True) == before


def test_a_short_beat_is_held_long_enough_to_read():
    sb = board()
    sb["beats"][2]["caption"] = "one two three four five six seven eight nine ten eleven twelve"      # 12 words: 12/3 + 0.5 = 4.5 s
    tm = json.loads(json.dumps(TIMINGS))
    tm["lines"]["L04"] = {"duration": 1.0, "speech_start": 0.0, "speech_end": 1.0}
    out = rt.retime(sb, tm, **{**ARGS, "end_hold": 0.5})
    assert out["beats"][2]["duration"] >= 4.5 - 1e-6


def test_speech_never_moves_earlier_or_overlaps():
    out = rt.retime(board(), TIMINGS, **ARGS)
    end = 0.0
    for b in out["beats"]:
        for lid in b["lines"]:
            start = b["line_starts"][lid]
            assert start >= end - 1e-9
            end = start + TIMINGS["lines"][lid]["duration"]


def test_cuts_snap_up_to_the_music_beat_and_everything_after_follows():
    grid = {"beats": [round(0.1 + 0.5 * k, 3) for k in range(60)]}
    plain = rt.retime(board(), TIMINGS, **ARGS)
    snapped = rt.retime(board(), TIMINGS, **ARGS, grid=grid, snap_max=0.5)
    starts = [b["start"] for b in snapped["beats"][1:]]
    for s in starts:
        assert min(abs(s - g) for g in grid["beats"]) <= 0.02                               # on a beat, to within a frame
    assert snapped["beats"][1]["start"] >= plain["beats"][1]["start"] - 1e-9                          # only ever later: the voice is not cut
    assert snapped["duration"] >= plain["duration"]
    gap = snapped["beats"][0]["line_starts"]["L02"] - snapped["beats"][0]["line_starts"]["L01"]
    assert gap == pytest.approx(plain["beats"][0]["line_starts"]["L02"] - plain["beats"][0]["line_starts"]["L01"])   # lines inside a beat keep their spacing


def test_a_cut_too_far_from_any_beat_is_left_alone():
    grid = {"beats": [0.1 + 5.0 * k for k in range(10)]}
    plain = rt.retime(board(), TIMINGS, **ARGS)
    snapped = rt.retime(board(), TIMINGS, **ARGS, grid=grid, snap_max=0.2)
    assert [b["start"] for b in snapped["beats"]] == [pytest.approx(b["start"]) for b in plain["beats"]]


def test_act_changes_use_the_downbeats_when_the_grid_has_them():
    grid = {"beats": [round(0.5 * k, 3) for k in range(60)], "downbeats": [round(2.0 * k + 0.25, 3) for k in range(20)]}
    out = rt.retime(board(), TIMINGS, **ARGS, grid=grid, snap_max=1.0)
    assert min(abs(out["beats"][2]["start"] - d) for d in grid["downbeats"]) <= 0.02


def test_missing_line_in_timings_names_it():
    tm = {"lines": {k: v for k, v in TIMINGS["lines"].items() if k != "L03"}}
    with pytest.raises(FilmError, match="L03"):
        rt.retime(board(), tm, **ARGS)


def test_unused_voice_line_is_reported_not_dropped_silently():
    tm = json.loads(json.dumps(TIMINGS))
    tm["lines"]["L09"] = {"duration": 1.0, "speech_start": 0.0, "speech_end": 1.0}
    assert any("L09" in w for w in rt.retime(board(), tm, **ARGS)["warnings"])


def test_cli_rewrites_the_storyboard(tmp_path):
    (tmp_path / "STORYBOARD.json").write_text(json.dumps(board()), encoding="utf-8")
    (tmp_path / "TIMINGS.json").write_text(json.dumps(TIMINGS), encoding="utf-8")
    proc = fc.py_script("retime.py", tmp_path / "STORYBOARD.json", tmp_path / "TIMINGS.json")
    assert proc.returncode == 0 and "PASS" in proc.stdout, proc.stdout + proc.stderr
    out = json.loads((tmp_path / "STORYBOARD.json").read_text(encoding="utf-8"))
    assert out["retimed"] is True and out["duration"] > 12 and out["beats"][0]["line_starts"]["L01"] == pytest.approx(0.3, abs=0.01)
    again = fc.py_script("retime.py", tmp_path / "STORYBOARD.json", tmp_path / "TIMINGS.json")             # re-running is safe: same result
    assert again.returncode == 0 and json.loads((tmp_path / "STORYBOARD.json").read_text(encoding="utf-8"))["duration"] == out["duration"]
    bad = fc.py_script("retime.py", tmp_path / "nope.json", tmp_path / "TIMINGS.json")
    assert bad.returncode == 1 and bad.stdout.startswith("FAIL")


def test_earlier_warnings_are_kept_and_retime_adds_its_own_once():
    sb = board(warnings=["B02: no public domain, CC0 or CC BY picture was found: it is built as a typeset title beat"])
    tm = {"lines": {**TIMINGS["lines"], "L09": {"duration": 1.0, "speech_start": 0.0, "speech_end": 1.0}}}
    once = rt.retime(sb, tm, **ARGS)
    assert once["warnings"][0].startswith("B02: no public domain") and any("L09" in w for w in once["warnings"])
    twice = rt.retime(once, tm, **ARGS)
    assert twice["warnings"] == once["warnings"]                                                     # running it again repeats nothing
    fixed = rt.retime(twice, TIMINGS, **ARGS)                                                        # the unused line is gone now
    assert fixed["warnings"] == ["B02: no public domain, CC0 or CC BY picture was found: it is built as a typeset title beat"]


def test_the_voice_notes_reach_the_storyboard_for_the_report():
    tm = {**TIMINGS, "notes": ["no word timings: pauses alone were used"], "warnings": ["L03: 3.0 s of speech, check the split"]}
    out = rt.retime(board(), tm, **ARGS)
    assert out["retime"]["notes"] == ["no word timings: pauses alone were used", "L03: 3.0 s of speech, check the split"]
