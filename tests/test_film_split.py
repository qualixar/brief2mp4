"""split_takes.py: cut one long recording into per-line WAVs by pauses and, when available, word timings."""
from __future__ import annotations

import json
import shutil
import wave

import pytest

import film_common as fc
import split_takes as st
from film_lib import FilmError

SCRIPT = "\n\n".join(f"## L0{i}\nsay: {t}\nsource: https://example.org/{i}" for i, t in
                     enumerate(["Ninety nine percent of data swims.", "A cable runs from Alexandria to Aswan.", "It lies on the seabed.", "That is how the internet crosses an ocean."], 1))
PLAN = [("gap", 0.6), ("tone", 1.5), ("gap", 0.7), ("tone", 2.2), ("gap", 0.6), ("tone", 1.0), ("gap", 0.8), ("tone", 1.8), ("gap", 0.5)]


@pytest.fixture(autouse=True)
def no_real_recogniser(monkeypatch):
    monkeypatch.delenv("WHISPER_MODEL", raising=False)


def take(tmp_path, plan=PLAN, name="take.wav"):
    path, bounds = fc.tone_and_silence(tmp_path / name, plan)
    (tmp_path / "SCRIPT.md").write_text(SCRIPT, encoding="utf-8")
    return path, bounds


def run_split(tmp_path, path, **kw):
    return st.split(path, tmp_path / "SCRIPT.md", tmp_path / "audio" / "lines", tmp_path / "TIMINGS.json", **kw)


def test_boundaries_are_found_within_30_ms_on_a_tone_and_silence_take(tmp_path):
    path, truth = take(tmp_path)
    result = run_split(tmp_path, path)
    assert [l["id"] for l in result["lines"]] == ["L01", "L02", "L03", "L04"]
    for line, (a, b) in zip(result["lines"], truth):
        assert abs(line["source_start"] + line["speech_start"] - a) < 0.03
        assert abs(line["source_start"] + line["speech_end"] - b) < 0.03


def test_each_cut_is_a_wav_whose_measured_duration_is_written_down(tmp_path):
    path, truth = take(tmp_path)
    result = run_split(tmp_path, path)
    for line, (a, b) in zip(result["lines"], truth):
        f = tmp_path / line["file"]
        assert f.is_file() and f.suffix == ".wav"
        assert fc.wav_info(f)[0] == pytest.approx(line["duration"], abs=0.001)
        assert line["duration"] == pytest.approx((b - a) + st.PAD_HEAD + st.PAD_TAIL, abs=0.05)
    timings = json.loads((tmp_path / "TIMINGS.json").read_text(encoding="utf-8"))
    assert timings["source"] == "take.wav" and set(timings["lines"]) == {"L01", "L02", "L03", "L04"}
    assert timings["lines"]["L02"]["duration"] == result["lines"][1]["duration"]


def test_the_voice_is_cut_not_stretched(tmp_path):
    path, truth = take(tmp_path)
    run_split(tmp_path, path)
    with wave.open(str(path), "rb") as src, wave.open(str(tmp_path / "audio" / "lines" / "L02.wav"), "rb") as cut:
        assert cut.getframerate() == src.getframerate() == 48000
        src_frames = src.readframes(src.getnframes())
        cut_frames = cut.readframes(cut.getnframes())
    mid = len(cut_frames) // 2 // 2 * 2
    assert cut_frames[mid:mid + 2000] in src_frames                               # the same samples, in the same order, at the same rate


def test_too_few_pauses_gives_a_message_that_says_what_to_do(tmp_path):
    path, _ = take(tmp_path, [("gap", 0.5), ("tone", 1.5), ("gap", 0.7), ("tone", 2.2), ("gap", 0.6), ("tone", 1.0), ("gap", 0.5)])
    with pytest.raises(FilmError, match=r"3 .*4 lines.*(pause|--words)"):
        run_split(tmp_path, path)


def test_a_pause_inside_a_line_does_not_confuse_it_when_the_gaps_between_lines_are_longer(tmp_path):
    plan = [("gap", 0.5), ("tone", 1.0), ("gap", 0.36), ("tone", 0.8), ("gap", 0.9), ("tone", 2.2), ("gap", 0.9), ("tone", 1.0), ("gap", 0.9), ("tone", 1.8), ("gap", 0.5)]
    path, truth = take(tmp_path, plan)
    result = run_split(tmp_path, path)
    assert len(result["lines"]) == 4
    assert abs(result["lines"][0]["speech_end"] + result["lines"][0]["source_start"] - truth[1][1]) < 0.03   # line 1 spans both of its tones


def test_short_gaps_are_split_by_word_timings_instead(tmp_path):
    plan = [("gap", 0.4), ("tone", 1.5), ("gap", 0.18), ("tone", 2.2), ("gap", 0.18), ("tone", 1.0), ("gap", 0.18), ("tone", 1.8), ("gap", 0.4)]
    path, truth = take(tmp_path, plan)
    words = [{"text": w, "start": a + 0.05 + i * 0.1, "end": a + 0.1 + i * 0.1} for (a, b), ws in zip(truth, [["Ninety", "nine", "percent", "of", "data", "swims"], ["A", "cable", "runs", "from", "Alexandria", "to", "Aswan"],
             ["It", "lies", "on", "the", "seabed"], ["That", "is", "how", "the", "internet", "crosses", "an", "ocean"]]) for i, w in enumerate(ws)]
    wp = tmp_path / "words.json"
    wp.write_text(json.dumps(words), encoding="utf-8")
    result = run_split(tmp_path, path, words_path=wp)
    for line, (a, b) in zip(result["lines"], truth):
        assert abs(line["source_start"] + line["speech_start"] - a) < 0.03
        assert abs(line["source_start"] + line["speech_end"] - b) < 0.03


def test_asr_that_disagrees_with_the_script_on_a_word_still_cuts_in_the_right_gap(tmp_path):
    plan = [("gap", 0.4), ("tone", 1.5), ("gap", 0.18), ("tone", 2.2), ("gap", 0.18), ("tone", 1.0), ("gap", 0.18), ("tone", 1.8), ("gap", 0.4)]
    path, truth = take(tmp_path, plan)
    heard = [["99%", "of", "data", "swims"], "A cable runs from Alexandria to Aswan".split(), "It lies on the seabed".split(), "That is how the internet crosses an ocean".split()]
    words = []
    for (a, b), ws in zip(truth, heard):
        step = (b - a - 0.2) / len(ws)
        words += [{"text": w, "start": a + 0.1 + i * step, "end": a + 0.1 + (i + 1) * step} for i, w in enumerate(ws)]
    wp = tmp_path / "w.json"
    wp.write_text(json.dumps(words), encoding="utf-8")
    result = run_split(tmp_path, path, words_path=wp)
    assert abs(result["lines"][0]["source_start"] + result["lines"][0]["speech_end"] - truth[0][1]) < 0.03
    assert abs(result["lines"][1]["source_start"] + result["lines"][1]["speech_start"] - truth[1][0]) < 0.03


def test_word_times_use_the_script_words_and_stay_inside_the_line(tmp_path):
    path, _ = take(tmp_path)
    result = run_split(tmp_path, path)
    for line in result["lines"]:
        words = line["words"]
        assert words and all(0 <= w["start"] < w["end"] <= line["duration"] + 1e-6 for w in words)
        assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(words, words[1:]))
    assert [w["text"] for w in result["lines"][0]["words"]] == "Ninety nine percent of data swims.".split()


def test_asr_anchors_place_words_where_they_were_heard():
    tokens = "Ninety nine percent of data swims.".split()
    heard = [{"text": "99%", "start": 0.0, "end": 0.6}, {"text": "of", "start": 0.6, "end": 0.8}, {"text": "data", "start": 0.8, "end": 1.2}, {"text": "swims", "start": 1.2, "end": 1.8}]
    times = st.word_times(tokens, heard, 0.0, 1.8)
    assert times[3] == (pytest.approx(0.6), pytest.approx(0.8)) and times[5][1] == pytest.approx(1.8)
    assert times[0][0] == 0.0 and times[2][1] <= 0.6 + 1e-9                                 # the unheard words share the time before "of"


def test_implausible_line_length_is_a_warning(tmp_path):
    path, _ = take(tmp_path, [("gap", 0.5), ("tone", 9.0), ("gap", 0.7), ("tone", 2.2), ("gap", 0.6), ("tone", 1.0), ("gap", 0.8), ("tone", 1.8), ("gap", 0.5)])
    result = run_split(tmp_path, path)
    assert any("L01" in w and "script" in w for w in result["warnings"])


def test_non_wav_takes_are_converted_first(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not found")
    path, truth = take(tmp_path)
    fc.ffmpeg("-i", path, tmp_path / "take.flac")
    result = run_split(tmp_path, tmp_path / "take.flac")
    assert abs(result["lines"][0]["source_start"] + result["lines"][0]["speech_start"] - truth[0][0]) < 0.03


def test_whisper_json_is_read_into_words():
    words = st.parse_whisper(fc.recorded("whisper_words.json"))
    assert [w["text"] for w in words][:4] == ["99%", "of", "intercontinental", "data"] and words[0]["start"] == 0.0 and words[1]["start"] == pytest.approx(0.59)


def test_without_a_recogniser_it_says_so_and_still_works(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(st.shutil, "which", lambda n: None)
    assert st.asr_words(tmp_path / "x.wav", None, None) is None
    path, _ = take(tmp_path)
    assert len(run_split(tmp_path, path)["lines"]) == 4


def test_cli(tmp_path):
    path, _ = take(tmp_path)
    proc = fc.py_script("split_takes.py", path, tmp_path / "SCRIPT.md", "--out-dir", tmp_path / "audio" / "lines", "--timings", tmp_path / "TIMINGS.json")
    assert proc.returncode == 0 and "PASS  4 lines cut" in proc.stdout, proc.stdout + proc.stderr
    bad = fc.py_script("split_takes.py", tmp_path / "nope.wav", tmp_path / "SCRIPT.md")
    assert bad.returncode == 1 and bad.stdout.startswith("FAIL")
