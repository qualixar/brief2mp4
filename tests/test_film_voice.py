"""film_voice.py and film_captions.py: stand-in, take and F5-TTS voices into TIMINGS.json; word-timed captions."""
from __future__ import annotations

import json
import os
import stat
import sys
import wave

import pytest

import film_common as fc
import film_captions as cap
import film_script as fs
import film_voice as fv
from film_lib import FilmError

SCRIPT = """## L01
say: Nearly all intercontinental data does not fly. It swims.
source: https://example.org/a

## L02
say: A cable runs from Alexandria to Aswan, and it is long.
source: https://example.org/b
"""


def script():
    return fs.parse_script("# Script\npace: 150\n\n" + SCRIPT)


# ---- stand-in -------------------------------------------------------------------------------------------------------

def test_standin_writes_one_48k_mono_wav_per_line_with_measured_duration(tmp_path):
    data = fv.standin(script(), tmp_path / "audio" / "lines", tmp_path / "TIMINGS.json")
    assert data["source"] == "standin" and data["order"] == ["L01", "L02"]
    for lid, entry in data["lines"].items():
        path = tmp_path / entry["file"]
        assert fc.wav_info(path) == (pytest.approx(entry["duration"], abs=0.001), 48000)
        with wave.open(str(path), "rb") as wf:
            assert wf.getnchannels() == 1 and wf.getsampwidth() == 2
        assert entry["speech_start"] == 0.0 and entry["speech_end"] == pytest.approx(entry["duration"])
    assert data["lines"]["L01"]["duration"] == pytest.approx(fs.estimate_seconds(script().lines[0]["say"], 150), abs=0.01)
    on_disk = json.loads((tmp_path / "TIMINGS.json").read_text(encoding="utf-8"))
    assert on_disk["lines"]["L02"]["file"] == "audio/lines/L02.wav"


def test_word_times_cover_every_script_word_in_order(tmp_path):
    data = fv.standin(script(), tmp_path / "audio" / "lines", tmp_path / "TIMINGS.json")
    words = data["lines"]["L01"]["words"]
    assert [w["text"] for w in words] == script().lines[0]["say"].split()
    assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(words, words[1:])) and words[-1]["end"] == pytest.approx(data["lines"]["L01"]["duration"], abs=0.01)


def test_a_longer_word_takes_longer():
    words = fv.spread_words("a extraordinary", 0.0, 2.0)
    assert words[1]["end"] - words[1]["start"] > 3 * (words[0]["end"] - words[0]["start"])


# ---- take -----------------------------------------------------------------------------------------------------------

def test_take_goes_through_split_takes(tmp_path):
    take, _ = fc.tone_and_silence(tmp_path / "take.wav", [("gap", 0.5), ("tone", 2.5), ("gap", 0.8), ("tone", 3.0), ("gap", 0.5)])
    (tmp_path / "SCRIPT.md").write_text("# Script\n\n" + SCRIPT, encoding="utf-8")
    result = fv.from_take(tmp_path / "SCRIPT.md", take, tmp_path / "audio" / "lines", tmp_path / "TIMINGS.json")
    assert [l["id"] for l in result["lines"]] == ["L01", "L02"]
    assert json.loads((tmp_path / "TIMINGS.json").read_text(encoding="utf-8"))["source"] == "take.wav"


# ---- F5-TTS (a stand-in executable proves the plumbing; the real tool is the user's install) ----------------------------

def fake_f5(tmp_path):
    exe = tmp_path / "bin" / "f5-tts_infer-cli"
    exe.parent.mkdir()
    exe.write_text(f"""#!{sys.executable}
import sys, math, struct, wave, os
a = sys.argv
out = os.path.join(a[a.index("--output_dir") + 1], a[a.index("--output_file") + 1])
text = a[a.index("--gen_text") + 1]
rate = 24000
n = int(rate * (0.4 + 0.5 * len(text.split()) / 4))
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 200 * i / rate)) if rate * 0.3 < i < n - rate * 0.1 else 0) for i in range(n)))
""", encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return exe


@pytest.mark.skipif(os.name == "nt", reason="the stand-in executable is a script")
def test_f5_lines_are_converted_trimmed_and_measured(tmp_path):
    ref = fc.write_wav(tmp_path / "ref.wav", [0.1] * 48000)
    data = fv.f5(script(), tmp_path / "audio" / "lines", tmp_path / "TIMINGS.json", ref, "hello there", exe=str(fake_f5(tmp_path)))
    assert data["source"] == "f5-tts" and "CC BY-NC" in data["note"]
    e = data["lines"]["L01"]
    assert fc.wav_info(tmp_path / e["file"])[1] == 48000 and e["speech_end"] <= e["duration"] <= e["speech_end"] + 0.15 + 0.03
    assert e["speech_start"] == pytest.approx(0.10, abs=0.03)                                  # the 0.3 s of silence in front was trimmed to 0.10 s


def test_missing_f5_says_how_to_install_and_names_the_licence(tmp_path, monkeypatch):
    monkeypatch.setattr(fv.shutil, "which", lambda n: None)
    with pytest.raises(FilmError) as err:
        fv.f5(script(), tmp_path / "a", tmp_path / "T.json", tmp_path / "r.wav", "x")
    assert "pip install f5-tts" in str(err.value) and "CC BY-NC" in str(err.value) and "--take" in str(err.value)


def test_f5_needs_a_reference_clip_and_its_text(tmp_path):
    with pytest.raises(FilmError, match="--ref-audio"):
        fv.f5(script(), tmp_path / "a", tmp_path / "T.json", tmp_path / "nope.wav", "x", exe="/bin/echo")


# ---- captions -------------------------------------------------------------------------------------------------------

def retimed(tmp_path):
    data = fv.standin(script(), tmp_path / "audio" / "lines", tmp_path / "TIMINGS.json")
    sb = {"beats": [{"id": "B01", "lines": ["L01"], "line_starts": {"L01": 1.0}}, {"id": "B02", "lines": ["L02"], "line_starts": {"L02": 8.0}}]}
    return sb, data


def test_captions_have_two_to_seven_words_and_break_at_phrases(tmp_path):
    cues = cap.caption_cues(*retimed(tmp_path))
    assert all(2 <= len(c["text"].split()) <= 7 or c is cues[-1] for c in cues)
    assert [c["text"] for c in cues if c["line"] == "L01"][0].endswith("fly.") or "data does not fly." in " ".join(c["text"] for c in cues)
    texts = [c["text"] for c in cues]
    assert any(t.endswith(",") for t in texts) or any(t.endswith("Aswan,") for t in texts)


def test_captions_never_cross_a_voice_line_and_never_overlap(tmp_path):
    sb, data = retimed(tmp_path)
    cues = cap.caption_cues(sb, data)
    assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(cues, cues[1:]))
    assert {c["line"] for c in cues} == {"L01", "L02"} and cues[-1]["line"] == "L02"
    assert min(c["start"] for c in cues if c["line"] == "L02") >= 8.0 and min(c["start"] for c in cues) >= 1.0


def test_every_script_word_is_in_the_captions_in_order(tmp_path):
    sb, data = retimed(tmp_path)
    spoken = " ".join(c["text"] for c in cap.caption_cues(sb, data)).split()
    assert spoken == " ".join(l["say"] for l in script().lines).split()


def test_each_caption_is_shown_long_enough(tmp_path):
    cues = cap.caption_cues(*retimed(tmp_path))
    assert all(c["end"] - c["start"] >= 0.1 for c in cues) and sum(1 for c in cues if c["end"] - c["start"] >= 0.4) >= len(cues) - 1


def test_srt_round_trips_and_wraps_long_captions_to_two_lines():
    cues = [{"start": 1.0, "end": 3.5, "text": "Nearly all intercontinental data does not fly.", "line": "L01"}]
    srt = cap.to_srt(cues)
    assert srt.startswith("1\n00:00:01,000 --> 00:00:03,500\n") and srt.count("\n") == 5
    assert all(len(l) <= 32 for l in srt.splitlines()[2:4])
    back = cap.parse_srt(srt)
    assert back[0]["start"] == 1.0 and back[0]["end"] == 3.5 and back[0]["text"] == "Nearly all intercontinental data does not fly."


def test_srt_time_format():
    assert cap.srt_time(3661.0075) == "01:01:01,008" or cap.srt_time(3661.0075) == "01:01:01,007"
