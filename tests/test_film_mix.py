"""mix.py: voice placed on the timeline, effects pinned by their peak, music ducked under the voice, loudness on target."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from array import array

import pytest

import film_common as fc
import mix as mx
import sfx_synth
from film_lib import FilmError

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not found")

LINES = {"L01": (2.0, 0.4), "L02": (2.5, 0.4)}                      # seconds, amplitude of the stand-in "voice" tone


def project(tmp_path, music=True, cues=None, voice_amp=0.3, seconds=14.0):
    """A small retimed project: two voice lines (tones), the effects, and optionally a 20 s music tone."""
    lines_dir = tmp_path / "audio" / "lines"
    lines_dir.mkdir(parents=True)
    timings = {"lines": {}}
    for lid, (dur, _) in LINES.items():
        path, _ = fc.tone_and_silence(lines_dir / f"{lid}.wav", [("tone", dur)], freq=180 if lid == "L01" else 220, amp=voice_amp)
        timings["lines"][lid] = {"file": f"audio/lines/{lid}.wav", "duration": dur, "speech_start": 0.0, "speech_end": dur}
    sfx_synth.write_all(tmp_path / "assets" / "sfx", seed=1)
    sb = {"fps": 30, "duration": seconds, "beats": [
        {"id": "B01", "start": 0.0, "end": 7.0, "duration": 7.0, "lines": ["L01"], "line_starts": {"L01": 1.0}, "sound": cues if cues is not None else
         [{"cue": "hit", "t": 0.2}, {"cue": "riser", "t": 5.0}]},
        {"id": "B02", "start": 7.0, "end": seconds, "duration": seconds - 7.0, "lines": ["L02"], "line_starts": {"L02": 8.0}, "sound": [{"cue": "whoosh", "t": 7.0}]}]}
    (tmp_path / "STORYBOARD.json").write_text(json.dumps(sb), encoding="utf-8")
    (tmp_path / "TIMINGS.json").write_text(json.dumps(timings), encoding="utf-8")
    if music:
        fc.ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=9", "-ac", "2", "-ar", "44100", tmp_path / "music.wav")   # shorter than the film: it must loop
    return sb, timings


def build(tmp_path, **kw):
    return mx.mix(tmp_path / "STORYBOARD.json", tmp_path / "TIMINGS.json", tmp_path / "assets" / "sfx", tmp_path / "audio" / "mix.wav", **kw)


def read(path):
    with wave.open(str(path), "rb") as wf:
        a = array("h")
        a.frombytes(wf.readframes(wf.getnframes()))
        return a, wf.getframerate(), wf.getnchannels()


def level(path, start, dur):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(start), "-t", str(dur), "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.search(r"mean_volume: (-?[0-9.]+) dB", err).group(1))


def lufs_of(path, start, dur):
    """Loudness of a stretch of a stem, in LUFS (what the mix is judged by: stereo and mono stems compare fairly)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(start), "-t", str(dur), "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.search(r"I:\s+(-?[0-9.]+) LUFS", err[err.rfind("Summary:"):]).group(1))


def onset(samples, rate, channels=1, thr=0.02):
    step = channels
    for i in range(0, len(samples), step):
        if abs(samples[i]) > thr * 32768:
            return i / step / rate
    return None


# ---- placing --------------------------------------------------------------------------------------------------------

def test_voice_lines_start_exactly_where_the_storyboard_says(tmp_path):
    project(tmp_path, music=False)
    build(tmp_path)
    s, rate, ch = read(tmp_path / "audio" / "stems" / "voice.wav")
    assert rate == 48000 and ch == 1
    assert onset(s, rate) == pytest.approx(1.0, abs=0.003)
    second = array("h", s[int(7.9 * rate):])
    assert onset(second, rate) == pytest.approx(0.1, abs=0.003)                  # L02 starts at 8.0


def test_effects_are_pinned_by_their_peak_not_their_start(tmp_path):
    project(tmp_path, music=False, cues=[{"cue": "riser", "t": 5.0}, {"cue": "tick", "t": 2.0}, {"cue": "whoosh", "t": 9.5}])
    build(tmp_path)
    s, rate, ch = read(tmp_path / "audio" / "stems" / "sfx.wav")
    def peak_time(a, b):
        idx = max(range(int(a * rate), int(b * rate)), key=lambda i: abs(s[i * ch]))
        return idx / rate
    assert peak_time(3.0, 5.6) == pytest.approx(5.0, abs=0.003)                  # the riser peaks at its end, so it starts about 2 s before
    assert peak_time(1.9, 2.2) == pytest.approx(2.0, abs=0.003)
    assert peak_time(8.9, 9.6) == pytest.approx(9.45, abs=0.004)                 # a whoosh lands 50 ms early (the ear expects it just before the object)


def test_an_effect_that_would_start_before_zero_is_trimmed_and_still_lands_on_time(tmp_path):
    project(tmp_path, music=False, cues=[{"cue": "riser", "t": 0.5}])
    build(tmp_path)
    s, rate, ch = read(tmp_path / "audio" / "stems" / "sfx.wav")
    idx = max(range(int(0.0 * rate), int(1.0 * rate)), key=lambda i: abs(s[i * ch]))
    assert idx / rate == pytest.approx(0.5, abs=0.003)


def test_the_cue_table_lists_time_file_volume_and_pinned_start(tmp_path):
    project(tmp_path, music=False)
    report = build(tmp_path)
    table = json.loads((tmp_path / "audio" / "cues.json").read_text(encoding="utf-8"))
    assert [c["t"] for c in table["cues"]] == sorted(c["t"] for c in table["cues"])
    riser = next(c for c in table["cues"] if c["cue"] == "riser")
    assert riser["file"].endswith("riser.wav") and 0 < riser["volume"] <= 1 and riser["start"] == pytest.approx(5.0 - riser["peak_lag"], abs=0.001)
    assert report["cues"] == len(table["cues"]) == 3


def test_a_cue_can_set_its_own_volume(tmp_path):
    project(tmp_path, music=False, cues=[{"cue": "tick", "t": 2.0, "volume": 0.9}])
    build(tmp_path)
    loud = read(tmp_path / "audio" / "stems" / "sfx.wav")[0][:3 * 48000]               # the tick only: B02 has a whoosh at 7 s
    project_dir = tmp_path / "b"
    project_dir.mkdir()
    project(project_dir, music=False, cues=[{"cue": "tick", "t": 2.0, "volume": 0.2}])
    build(project_dir)
    quiet = read(project_dir / "audio" / "stems" / "sfx.wav")[0][:3 * 48000]
    assert max(map(abs, loud)) > 3.5 * max(map(abs, quiet))


# ---- ducking --------------------------------------------------------------------------------------------------------

def test_the_duck_envelope_is_smooth_and_sits_under_the_voice():
    env = mx.duck_gains([(2.0, 4.0)], 8.0, depth_db=-8.0, attack=0.12, release=0.5, hop=0.01)
    g = lambda t: env[int(t / 0.01)]
    assert g(0.5) == pytest.approx(1.0) and g(3.0) == pytest.approx(10 ** (-8 / 20), rel=1e-3) and g(7.0) == pytest.approx(1.0)
    assert 10 ** (-8 / 20) < g(1.95) < 1.0 and 10 ** (-8 / 20) < g(4.2) < 1.0                          # ramping down before the voice, up after it
    assert max(abs(a - b) for a, b in zip(env, env[1:])) < 0.08                                          # a 2.5 dB-per-hop slope at most: smoother than any compressor attack


def test_short_breaths_between_lines_keep_the_bed_down(tmp_path):
    env = mx.duck_gains([(1.0, 2.0), (2.3, 3.3)], 6.0, depth_db=-8.0, attack=0.12, release=0.5, hop=0.01)
    assert env[int(2.15 / 0.01)] == pytest.approx(10 ** (-8 / 20), rel=1e-3)                              # the 0.3 s breath does not let the music pump up
    long = mx.duck_gains([(1.0, 2.0), (3.5, 4.5)], 6.0, depth_db=-8.0, attack=0.12, release=0.5, hop=0.01)
    assert long[int(2.8 / 0.01)] == pytest.approx(1.0)                                                   # a 1.5 s pause does


def test_the_bed_is_8_db_down_under_speech_and_12_to_18_db_below_the_voice(tmp_path):
    project(tmp_path)
    build(tmp_path, music=tmp_path / "music.wav")
    stems = tmp_path / "audio" / "stems"
    under_voice = lufs_of(stems / "music.wav", 1.5, 1.0)                  # L01 speaks 1.0-3.0
    in_gap = lufs_of(stems / "music.wav", 5.0, 1.5)                        # nobody speaks 3.5-7.9
    voice = lufs_of(stems / "voice.wav", 1.5, 1.0)
    assert 6.0 <= in_gap - under_voice <= 10.0, (in_gap, under_voice)
    assert 12.0 <= voice - under_voice <= 18.0, (voice, under_voice)


def test_music_is_looped_to_the_film_length_and_faded_out(tmp_path):
    project(tmp_path)
    build(tmp_path, music=tmp_path / "music.wav")
    s, rate, ch = read(tmp_path / "audio" / "stems" / "music.wav")
    assert ch == 2 and len(s) / ch / rate == pytest.approx(14.0, abs=0.05)
    stem = tmp_path / "audio" / "stems" / "music.wav"
    assert level(stem, 13.9, 0.1) < level(stem, 11.0, 0.5) - 15                                     # the last 0.1 s is nearly gone: the tail fades


def test_without_music_there_is_no_ducking_and_no_music_stem(tmp_path):
    project(tmp_path, music=False)
    build(tmp_path)
    assert not (tmp_path / "audio" / "stems" / "music.wav").exists()


# ---- loudness -------------------------------------------------------------------------------------------------------

def measure(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    return float(re.search(r"I:\s+(-?[0-9.]+) LUFS", tail).group(1)), float(re.search(r"Peak:\s+(-?[0-9.]+) dBFS", tail).group(1))


@pytest.mark.parametrize("amp", [0.05, 0.3, 0.8])
def test_the_mix_lands_on_minus_14_lufs_and_under_minus_1_dbtp(tmp_path, amp):
    project(tmp_path, voice_amp=amp)
    report = build(tmp_path, music=tmp_path / "music.wav")
    lufs, peak = measure(tmp_path / "audio" / "mix.wav")
    assert lufs == pytest.approx(-14.0, abs=1.0) and peak <= -1.0, (lufs, peak)
    assert report["lufs"] == pytest.approx(lufs, abs=0.3) and report["true_peak"] <= -1.0


def test_mix_is_stereo_48k_and_as_long_as_the_film(tmp_path):
    project(tmp_path)
    build(tmp_path, music=tmp_path / "music.wav")
    s, rate, ch = read(tmp_path / "audio" / "mix.wav")
    assert (rate, ch) == (48000, 2) and len(s) / ch / rate == pytest.approx(14.0, abs=0.05)


def test_same_inputs_give_the_same_mix(tmp_path):
    project(tmp_path)
    build(tmp_path, music=tmp_path / "music.wav")
    first = (tmp_path / "audio" / "mix.wav").read_bytes()
    build(tmp_path, music=tmp_path / "music.wav")
    assert (tmp_path / "audio" / "mix.wav").read_bytes() == first


# ---- mistakes -------------------------------------------------------------------------------------------------------

def test_unknown_cue_is_named(tmp_path):
    project(tmp_path, music=False, cues=[{"cue": "boing", "t": 1.0}])
    with pytest.raises(FilmError, match="boing"):
        build(tmp_path)


def test_missing_effects_say_how_to_make_them(tmp_path):
    project(tmp_path, music=False)
    shutil.rmtree(tmp_path / "assets" / "sfx")
    with pytest.raises(FilmError, match="sfx_synth.py all"):
        build(tmp_path)


def test_a_voice_line_that_is_not_48k_mono_is_refused(tmp_path):
    project(tmp_path, music=False)
    fc.write_wav(tmp_path / "audio" / "lines" / "L01.wav", [0.1] * 4410, rate=44100)
    with pytest.raises(FilmError, match="48 kHz mono"):
        build(tmp_path)


def test_nothing_to_mix_is_an_error(tmp_path):
    project(tmp_path, music=False, cues=[])
    sb = json.loads((tmp_path / "STORYBOARD.json").read_text(encoding="utf-8"))
    sb["beats"] = [{**b, "lines": [], "line_starts": {}, "sound": []} for b in sb["beats"]]
    (tmp_path / "STORYBOARD.json").write_text(json.dumps(sb), encoding="utf-8")
    with pytest.raises(FilmError, match="nothing to mix"):
        build(tmp_path)


def test_cli(tmp_path):
    project(tmp_path)
    proc = fc.py_script("mix.py", tmp_path / "STORYBOARD.json", tmp_path / "TIMINGS.json", "--sfx-dir", tmp_path / "assets" / "sfx",
                        "--music", tmp_path / "music.wav", "--out", tmp_path / "audio" / "mix.wav")
    assert proc.returncode == 0 and "PASS" in proc.stdout, proc.stdout + proc.stderr
    assert (tmp_path / "audio" / "mix_report.json").is_file() and (tmp_path / "audio" / "stems" / "voice.wav").is_file()
    bad = fc.py_script("mix.py", tmp_path / "nope.json", tmp_path / "TIMINGS.json")
    assert bad.returncode == 1 and bad.stdout.startswith("FAIL")
