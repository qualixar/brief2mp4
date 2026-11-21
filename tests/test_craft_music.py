"""fetch_music.py against a local fake Openverse: licence filter, retries, attribution file, bad downloads."""
from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from craft_common import SCRIPTS, ffmpeg, needs_ffmpeg, py_script

spec = importlib.util.spec_from_file_location("fetch_music", SCRIPTS / "fetch_music.py")
fm = importlib.util.module_from_spec(spec)
sys.modules["fetch_music"] = fm
spec.loader.exec_module(fm)

FAST = ["--backoff", "0.01"]


class Fake:
    """A tiny Openverse: /v1/audio/ search, /v1/audio/<id>/ detail, /files/* downloads. Counts requests per path."""

    def __init__(self, tone: bytes):
        self.tone, self.hits, self.fail_first = tone, {}, {}      # fail_first: path prefix -> how many 503s before working
        self.items = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                path = self.path.split("?")[0]
                outer.hits[path] = outer.hits.get(path, 0) + 1
                for prefix, n in outer.fail_first.items():
                    if path.startswith(prefix) and outer.hits[path] <= n:
                        return self.send(503, b"busy", "text/plain")
                if path == "/v1/audio/":
                    return self.send(200, json.dumps({"results": outer.items}).encode(), "application/json")
                if path.startswith("/v1/audio/"):
                    found = [i for i in outer.items if i["id"] == path.split("/")[3]]
                    return self.send(200, json.dumps(found[0]).encode(), "application/json") if found else self.send(404, b"no", "text/plain")
                if path == "/files/tone.mp3":
                    return self.send(200, outer.tone, "audio/mpeg")
                if path == "/files/page.mp3":
                    return self.send(200, b"<html>" + b"x" * 3000 + b"</html>", "text/html")
                if path == "/files/tiny.mp3":
                    return self.send(200, b"abc", "audio/mpeg")
                self.send(404, b"no", "text/plain")

            def send(self, code, body, ctype):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()

    def item(self, id_, license_="by", url="/files/tone.mp3", title="Calm Pad", duration=60000, **extra):
        it = {"id": id_, "title": title, "creator": "A. Maker", "license": license_, "license_version": "4.0",
              "license_url": "https://creativecommons.org/licenses/by/4.0/", "url": self.base + url,
              "foreign_landing_url": "https://example.org/track/" + id_, "duration": duration, "source": "example",
              "filetype": "mp3", "attribution": f'"{title}" by A. Maker is licensed under CC BY 4.0.', "mature": False, **extra}
        self.items.append(it)
        return it


@pytest.fixture
def fake(tmp_path):
    tone = tmp_path / "tone.mp3"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1", tone)
    srv = Fake(tone.read_bytes())
    yield srv
    srv.server.shutdown()


def run(fake, *args):
    return py_script("fetch_music.py", *args, env={"OPENVERSE_API": fake.base + "/v1"})


# ---- search ----------------------------------------------------------------------------------------------------

def test_search_lists_usable_tracks_and_drops_the_wrong_licences(fake):
    fake.item("aaaa1111", "by"); fake.item("bbbb2222", "cc0"); fake.item("cccc3333", "pdm")
    fake.item("dddd4444", "by-nc"); fake.item("eeee5555", "by-sa"); fake.item("ffff6666", "by-nd")
    out = run(fake, "search", "calm").stdout
    assert out.count("\n   https://example.org") == 3 and "aaaa1111" in out and "bbbb2222" in out and "cccc3333" in out
    for bad in ("dddd4444", "eeee5555", "ffff6666"):
        assert bad not in out, "NonCommercial, ShareAlike and NoDerivatives tracks must never be offered, even if the API sends them"


def test_search_drops_mature_and_out_of_range_tracks(fake):
    fake.item("long00001", duration=900000); fake.item("short0001", duration=3000); fake.item("mature001", mature=True); fake.item("good00001")
    out = run(fake, "search", "calm", "--min-seconds", "20", "--max-seconds", "300").stdout
    assert "good00001" in out and "long00001" not in out and "short0001" not in out and "mature001" not in out


def test_search_with_nothing_usable_fails(fake):
    fake.item("dddd4444", "by-nc")
    proc = run(fake, "search", "calm")
    assert proc.returncode == 1 and "FAIL  fetch_music: no usable" in proc.stdout


# ---- download and attribution --------------------------------------------------------------------------------------

@needs_ffmpeg
def test_download_saves_the_file_and_writes_attribution(fake, tmp_path):
    fake.item("aaaa1111")
    out_dir = tmp_path / "audio"
    proc = run(fake, "download", "calm", "--out-dir", out_dir)
    assert proc.returncode == 0, proc.stdout
    files = list(out_dir.glob("*.mp3"))
    assert len(files) == 1 and files[0].name == "calm-pad-aaaa1111.mp3" and files[0].stat().st_size > 1024
    text = (out_dir / "ATTRIBUTION.md").read_text(encoding="utf-8")
    for needle in ("## Calm Pad", "File: calm-pad-aaaa1111.mp3", "Creator: A. Maker", "CC BY 4.0", "creativecommons.org/licenses/by/4.0",
                   "https://example.org/track/aaaa1111", "Credit required: yes", "Retrieved:"):
        assert needle in text, needle
    assert "credit in the video description" in proc.stdout


@needs_ffmpeg
def test_cc0_download_says_credit_is_not_required_and_a_second_download_appends(fake, tmp_path):
    fake.item("aaaa1111", "cc0", title="Free One"); fake.item("bbbb2222", "by", title="Second")
    out_dir = tmp_path / "audio"
    run(fake, "download", "x", "--pick", "1", "--out-dir", out_dir)
    run(fake, "download", "x", "--pick", "2", "--out-dir", out_dir)
    run(fake, "download", "x", "--pick", "2", "--out-dir", out_dir)          # again: no duplicate entry
    text = (out_dir / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert text.count("## ") == 2 and "Credit required: no" in text and "CC0 1.0" in text and text.count("File: second-bbbb2222.mp3") == 1


@needs_ffmpeg
def test_download_by_id_refuses_a_noncommercial_track(fake, tmp_path):
    fake.item("dddd4444", "by-nc")
    proc = run(fake, "download", "--id", "dddd4444", "--out-dir", tmp_path / "a")
    assert proc.returncode == 1 and "not CC0, public domain or CC BY" in proc.stdout and not (tmp_path / "a").exists()


@needs_ffmpeg
def test_a_download_that_is_a_web_page_is_rejected_and_not_kept(fake, tmp_path):
    fake.item("pageaaaa", url="/files/page.mp3")
    proc = run(fake, "download", "calm", "--out-dir", tmp_path / "a")
    assert proc.returncode == 1 and "not audio" in proc.stdout
    assert not list((tmp_path / "a").glob("*.mp3")) and not (tmp_path / "a" / "ATTRIBUTION.md").exists()


def test_a_tiny_download_is_rejected(fake, tmp_path):
    fake.item("tinyaaaa", url="/files/tiny.mp3")
    proc = run(fake, "download", "calm", "--out-dir", tmp_path / "a")
    assert proc.returncode == 1 and "only 3 bytes" in proc.stdout


def test_a_pick_beyond_the_results_fails(fake, tmp_path):
    fake.item("aaaa1111")
    proc = run(fake, "download", "calm", "--pick", "5", "--out-dir", tmp_path / "a")
    assert proc.returncode == 1 and "no result number 5" in proc.stdout


# ---- retries ------------------------------------------------------------------------------------------------------

def test_a_server_error_is_retried_until_it_works(fake):
    fake.item("aaaa1111")
    fake.fail_first["/v1/audio/"] = 2
    proc = run(fake, "search", "calm", *FAST)
    assert proc.returncode == 0 and fake.hits["/v1/audio/"] == 3


def test_a_server_that_never_recovers_fails_after_the_retries(fake):
    fake.item("aaaa1111")
    fake.fail_first["/v1/audio/"] = 99
    proc = run(fake, "search", "calm", "--retries", "2", *FAST)
    assert proc.returncode == 1 and "HTTP 503" in proc.stdout and "gave up after 3 tries" in proc.stdout
    assert fake.hits["/v1/audio/"] == 3


def test_a_client_error_is_not_retried(fake):
    proc = run(fake, "download", "--id", "missing", "--out-dir", "unused", *FAST)
    assert proc.returncode == 1 and "HTTP 404" in proc.stdout and fake.hits["/v1/audio/missing/"] == 1


def test_a_refused_connection_is_retried_then_reported(tmp_path):
    proc = py_script("fetch_music.py", "search", "calm", "--retries", "1", *FAST, env={"OPENVERSE_API": "http://127.0.0.1:9/v1"})
    assert proc.returncode == 1 and "network error" in proc.stdout and "gave up after 2 tries" in proc.stdout


# ---- helpers ------------------------------------------------------------------------------------------------------

def test_slug_and_extension_helpers():
    assert fm.slug("Calm Pad (Final)!") == "calm-pad-final" and fm.slug("") == "track"
    assert fm.extension({"filetype": "mp32"}, "") == "mp3" and fm.extension({}, "audio/ogg; charset=x") == "ogg"
