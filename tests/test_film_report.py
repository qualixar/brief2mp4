"""film_render.py, film_check.py and film_report.py: the parts around the render that do not need a render."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import film_common as fc
import film_check as ck
import film_render as fr
import film_report as rp
from film_lib import FilmError, Project, save_json

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not found")


def clip(path, seconds=1.0, color="red"):
    fc.ffmpeg("-f", "lavfi", "-i", f"color=c={color}:s=320x180:r=30:d={seconds}", "-c:v", "libx264", "-pix_fmt", "yuv420p", path)
    return path


def test_acts_are_joined_with_stream_copy(tmp_path):
    p = Project(tmp_path)
    a, b = clip(tmp_path / "a.mp4", 1.0, "red"), clip(tmp_path / "b.mp4", 1.5, "blue")
    (tmp_path / "render").mkdir()
    joined = fr.join(p, [{"file": a}, {"file": b}])
    assert fr.frame_count(joined) == 75


def test_one_act_is_just_copied(tmp_path):
    p = Project(tmp_path)
    (tmp_path / "render").mkdir()
    a = clip(tmp_path / "a.mp4", 1.0)
    assert fr.frame_count(fr.join(p, [{"file": a}])) == 30


def test_a_render_with_extra_frames_is_trimmed_to_the_plan(tmp_path):
    a = clip(tmp_path / "a.mp4", 1.0)
    assert fr.frame_count(fr.trim_to(a, 24)) == 24


def test_hf_command_pins_the_version_and_resumes_long_renders():
    tmp = Path("proj")
    cmd = fr.hf_command("npx", tmp, Path("o.mp4"), "draft", 4, True)
    assert cmd[:3] == ["npx", "--yes", "hyperframes@0.8.216"] and "--resume" in cmd and cmd[cmd.index("--workers") + 1] == "4" and cmd[cmd.index("--fps") + 1] == "30"
    assert "--resume" not in fr.hf_command("npx", tmp, tmp, "draft", 4, False)


def test_workers_are_shared_between_acts():
    assert [fr.workers_for(n) for n in (1, 2, 3, 6, 20)] == [8, 6, 4, 2, 1]


def test_finish_uses_the_mix_the_size_and_the_exact_duration(tmp_path, monkeypatch):
    seen = {}

    class Done:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(fr.subprocess, "run", lambda cmd, **k: seen.setdefault("cmd", cmd) and Done())
    p = Project(tmp_path)
    mix = fc.write_wav(tmp_path / "mix.wav", [0.1] * 4800)
    fr.finish(p, tmp_path / "j.mp4", 19.7333, mix, "1920x1080", 30)
    cmd = seen["cmd"]
    assert cmd[0] == "bash" and cmd[1].endswith("finish.sh") and cmd[cmd.index("--seconds") + 1] == "19.7333" and cmd[cmd.index("--audio") + 1] == str(mix)


def test_rest_times_sample_each_beat_after_its_entrances():
    sb = {"beats": [{"act": "A1", "start": 0.0, "duration": 5.0}, {"act": "A1", "start": 5.0, "duration": 1.0}, {"act": "A2", "start": 6.0, "duration": 4.0}]}
    assert ck.rest_times(sb, None, 0.0) == [2.4, 5.6, 8.4]
    assert ck.rest_times(sb, "A2", 6.0) == [2.4]


def test_check_needs_a_render_first(tmp_path):
    p = Project(tmp_path)
    save_json(p.storyboard, {"acts": [{"id": "A1", "start": 0}], "beats": [], "duration": 1, "size": [1920, 1080], "fps": 30})
    save_json(p.p("BUILD.json"), {"projects": []})
    with pytest.raises(FilmError, match="render"):
        ck.check_film(p)


def make_report_project(tmp_path):
    p = Project(tmp_path)
    save_json(p.storyboard, {"title": "T", "look": "archive-desk", "art_form": "archive-documentary", "format": "documentary", "size": [1920, 1080], "fps": 30, "duration": 12.0,
                             "retimed": True, "beats": [{"id": "B01"}], "acts": [{"id": "A1"}], "music": None, "warnings": ["B03: no picture"], "retime": {"notes": []}})
    p.script.write_text("## L01\nsay: Known thing.\nsource: https://example.org/x\n\n## L02\nsay: Doubtful thing.\n", encoding="utf-8")
    save_json(p.assets, {"assets": [
        {"file": "assets/maps/B02.svg", "kind": "map", "licence": "Public domain", "attribution": "Map data: Natural Earth (public domain)", "credit_required": False},
        {"file": "assets/archive/a.jpg", "kind": "archive", "licence": "CC BY 4.0", "attribution": '"Ship" by Ada, licensed CC BY 4.0', "credit_required": True, "source_url": "https://commons.example/a"}]})
    save_json(p.timings, {"source": "take.wav"})
    return p


def test_report_lists_credits_first_the_unverified_lines_and_open_items(tmp_path):
    p = make_report_project(tmp_path)
    text = rp.write_report(p).read_text(encoding="utf-8")
    assert text.index('"Ship" by Ada') < text.index("Natural Earth (public domain)")                  # CC BY credits come first: they must go in the description
    assert "- L02: Doubtful thing." in text and "- L01" not in text.split("## Unverified lines")[1].split("## Sources")[0]
    assert "- L01: https://example.org/x" in text and "B03: no picture" in text and "Voice: take.wav" in text and "github.com/qualixar/brief2mp4" in text
    assert "The checks have not been run yet" in text


def test_report_includes_check_lines_when_they_exist(tmp_path):
    p = make_report_project(tmp_path)
    save_json(p.p("checks.json"), {"delivery": {"ok": True, "lines": ["PASS  duration 12s"]}, "clutter": {"ok": False, "lines": ["FAIL  something"]}})
    text = rp.write_report(p).read_text(encoding="utf-8")
    assert "### delivery: PASS" in text and "    PASS  duration 12s" in text and "### clutter: FAIL" in text
