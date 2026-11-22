"""film_render.py, film_check.py and film_report.py: the parts around the render that do not need a render."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import film_common as fc
import film
import film_lib
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
    assert cmd[0] == fr.find_bash() and cmd[1].endswith("finish.sh") and cmd[cmd.index("--seconds") + 1] == "19.7333" and cmd[cmd.index("--audio") + 1] == str(mix)


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
    assert "- L01: https://example.org/x" in text and "B03: no picture" in text and "Voice: take.wav" in text and "github.com" not in text   # the report is the user's to hand on
    assert "The checks have not been run yet" in text


def test_report_includes_check_lines_when_they_exist(tmp_path):
    p = make_report_project(tmp_path)
    save_json(p.p("checks.json"), {"delivery": {"ok": True, "lines": ["PASS  duration 12s"]}, "clutter": {"ok": False, "lines": ["FAIL  something"]}})
    text = rp.write_report(p).read_text(encoding="utf-8")
    assert "### delivery: PASS" in text and "    PASS  duration 12s" in text and "### clutter: FAIL" in text


# ---- the frame rate, end to end ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,value,rate", [("24", 24.0, "24"), (30, 30.0, "30"), ("29.97", 30000 / 1001, "30000/1001"),
                                             ("24000/1001", 24000 / 1001, "24000/1001"), ("25.0", 25.0, "25")])
def test_frame_rates_are_parsed_exactly(text, value, rate):
    v, r = film_lib.parse_fps(text)
    assert v == pytest.approx(value) and r == rate


@pytest.mark.parametrize("bad", ["fast", "0", "300", "1/0"])
def test_bad_frame_rates_are_refused(bad):
    with pytest.raises(FilmError):
        film_lib.parse_fps(bad)


def test_hf_command_renders_at_the_storyboards_rate():
    cmd = fr.hf_command("npx", Path("p"), Path("o.mp4"), "draft", 4, False, "24")
    assert cmd[cmd.index("--fps") + 1] == "24"


class FakeRender:
    """Popen stand-in: 'renders' by writing an empty file; frame_count then reports whatever the test asks."""

    def __init__(self, cmd, **kw):
        self.cmd, self.returncode = cmd, 0
        FakeRender.seen.append(cmd)
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"x")

    def communicate(self):
        return "", ""


def render_project(tmp_path, monkeypatch, found, fps="24"):
    p = Project(tmp_path)
    save_json(p.p("BUILD.json"), {"projects": [{"act": "all", "dir": "project", "start": 0, "frames": 240, "seconds": 10.0}]})
    FakeRender.seen = []
    monkeypatch.setattr(fr.shutil, "which", lambda name: "npx")
    monkeypatch.setattr(fr.subprocess, "Popen", FakeRender)
    monkeypatch.setattr(fr, "frame_count", lambda path: found)
    monkeypatch.setattr(fr, "trim_to", lambda path, n: path.with_name("trimmed.mp4"))
    return p


def test_a_render_at_the_wrong_rate_fails_instead_of_being_trimmed(tmp_path, monkeypatch):
    # the old bug: rendered at 30 fps, trimmed to the 24 fps plan, relabelled 24: slow picture, PASS everywhere
    p = render_project(tmp_path, monkeypatch, found=300)
    with pytest.raises(FilmError, match="300 frames, 240 were planned at 24 fps"):
        fr.render_acts(p, "draft", None, "24")
    assert FakeRender.seen[0][FakeRender.seen[0].index("--fps") + 1] == "24"


@pytest.mark.parametrize("found,trimmed", [(240, False), (241, True), (239, False)])
def test_one_frame_either_way_is_accepted_and_only_an_extra_frame_is_trimmed(tmp_path, monkeypatch, found, trimmed):
    p = render_project(tmp_path, monkeypatch, found=found)
    (res,) = fr.render_acts(p, "draft", None, "24")
    assert res["trimmed"] is trimmed and (res["file"].name == "trimmed.mp4") is trimmed


def test_render_film_passes_the_storyboards_rate_to_hyperframes_and_finish(tmp_path, monkeypatch):
    p = render_project(tmp_path, monkeypatch, found=240)
    save_json(p.storyboard, {"fps": 24.0, "fps_rate": "24", "duration": 10.0, "size": [1920, 1080], "acts": [{"id": "A1", "start": 0}]})
    seen = {}
    monkeypatch.setattr(fr, "join", lambda project, parts: parts[0]["file"])
    monkeypatch.setattr(fr, "finish", lambda project, joined, seconds, mix, size, fps: seen.setdefault("fps", fps))
    fr.render_film(p, "draft")
    assert seen["fps"] == "24" and FakeRender.seen[0][FakeRender.seen[0].index("--fps") + 1] == "24"


def test_the_concat_list_survives_a_quote_in_the_path(tmp_path):
    p = Project(tmp_path / "O'Brien film")
    (p.root / "render").mkdir(parents=True)
    a, b = clip(p.root / "a.mp4", 1.0, "red"), clip(p.root / "b.mp4", 1.0, "blue")
    assert fr.frame_count(fr.join(p, [{"file": a}, {"file": b}])) == 60


# ---- the checks: Git Bash on Windows, skipped is not passed --------------------------------------------------------------

def test_windows_uses_git_bash_never_the_wsl_launcher(monkeypatch, tmp_path):
    git_bash = tmp_path / "bash.exe"
    git_bash.write_text("", encoding="utf-8")
    monkeypatch.setattr(film_lib.os, "name", "nt")
    monkeypatch.setattr(film_lib.shutil, "which", lambda name: r"C:\Windows\System32\bash.exe")
    monkeypatch.setattr(film_lib.os.path, "isfile", lambda path: str(path) in (str(git_bash), r"C:\Windows\System32\bash.exe"))
    monkeypatch.setenv("B2M_BASH", str(git_bash))
    assert film_lib.find_bash() == str(git_bash)
    monkeypatch.delenv("B2M_BASH")
    with pytest.raises(FilmError, match="Git Bash"):
        film_lib.find_bash()


def checked_project(tmp_path, monkeypatch, codes):
    p = Project(tmp_path)
    save_json(p.storyboard, {"acts": [{"id": "A1", "start": 0}], "beats": [{"act": "A1", "start": 0.0, "duration": 4.0}], "duration": 4.0,
                             "size": [1920, 1080], "fps": 24.0, "fps_rate": "24", "look": "archive-desk", "art_form": "archive-documentary",
                             "format": "documentary", "retimed": True, "warnings": []})
    save_json(p.p("BUILD.json"), {"projects": [{"act": "all", "dir": "project", "start": 0.0}]})
    p.script.write_text("## L01\nsay: Known.\nsource: https://example.org/x\n", encoding="utf-8")
    p.final.write_bytes(b"x")
    calls = []

    def fake_run(cmd):
        calls.append([str(c) for c in cmd])
        name = Path(str(cmd[1])).name
        return codes.get(name, 0), [f"{'SKIP' if codes.get(name) == 3 else 'FAIL' if codes.get(name) else 'PASS'}  {name}"]
    monkeypatch.setattr(ck, "run", fake_run)
    return p, calls


def test_check_passes_the_rate_and_a_whole_film_ocr_window(tmp_path, monkeypatch):
    p, calls = checked_project(tmp_path, monkeypatch, {})
    ck.check_film(p)
    delivery = next(c for c in calls if c[1].endswith("check_delivery.sh"))
    ocr = next(c for c in calls if c[1].endswith("ocr_sweep.sh"))
    assert delivery[delivery.index("--fps") + 1] == "24" and ocr[ocr.index("--max-frames") + 1] == "5"
    assert all(c[0] == film_lib.find_bash() for c in calls if c[1].endswith(".sh"))


def test_a_skipped_check_is_recorded_as_skipped_never_as_pass(tmp_path, monkeypatch):
    p, _ = checked_project(tmp_path, monkeypatch, {"ocr_sweep.sh": 3, "check_clutter.py": 3})
    r = ck.check_film(p)
    assert r["ok"] and r["ocr"]["status"] == "skipped" and r["clutter"]["status"] == "skipped" and set(r["skipped"]) == {"ocr", "clutter"}
    text = rp.write_report(p).read_text(encoding="utf-8")
    assert "### ocr: SKIPPED (not measured)" in text and "the ocr check was skipped" in text
    assert film.check_summary("ocr", r["ocr"])[0] == "SKIP"


def test_a_failed_check_writes_the_report_and_names_the_first_fail_line(tmp_path, monkeypatch, capsys):
    p, _ = checked_project(tmp_path, monkeypatch, {"check_clutter.py": 1})
    monkeypatch.setattr(ck, "run", lambda cmd: (1, ["PASS  no card on card", "FAIL  5 text blocks"]) if "check_clutter" in str(cmd[1]) else (0, ["PASS  ok"]))
    assert film.main(["check", "--project", str(p.root)]) == 1
    out = capsys.readouterr().out
    assert "FAIL  clutter: all: FAIL  5 text blocks" in out and p.report.is_file()
