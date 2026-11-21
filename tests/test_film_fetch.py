"""fetch_archive.py: licence gate, recorded Commons and Openverse responses, download, attribution, retries. No network."""
from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.parse

import pytest

import film_common as fc
import fetch_archive as fa
from fetch_archive import FetchError

COMMONS = fc.recorded("commons_search.json")
OPENVERSE = fc.recorded("openverse_images.json")
BAD = fc.recorded("openverse_bad_licences.json")


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(fa.time, "sleep", lambda s: None)


def fake_network(monkeypatch, routes: dict, calls: list | None = None):
    """Replace the HTTP layer: a URL containing a key in `routes` answers with that value (bytes or dict)."""
    def get(url, retries=3, backoff=1.0, timeout=60, agent=None):
        if calls is not None:
            calls.append(url)
        for key, body in routes.items():
            if key in url:
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                return data, "image/png" if isinstance(body, bytes) else "application/json"
        raise FetchError(f"HTTP 404 from test for {url}")
    monkeypatch.setattr(fa, "http_get", get)


# ---- the licence gate -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("code", ["cc-by-sa-4.0", "cc-by-sa-2.0", "cc-by-nc-4.0", "cc-by-nd-4.0", "cc-by-nc-sa-4.0", "cc-by-nc-nd-4.0",
                                  "by-sa", "by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "", None, "all rights reserved", "gfdl", "cc-by-3.0-igo",
                                  "no restrictions", "fair use", "unknown"])
def test_licence_gate_rejects_share_alike_non_commercial_no_derivatives_and_unknown(code):
    assert fa.licence_code(code) is None


@pytest.mark.parametrize("raw,want", [("cc0", "cc0"), ("CC0-1.0", "cc0"), ("pd", "pdm"), ("pd-old-70", "pdm"), ("pd-usgov-nasa", "pdm"), ("pdm", "pdm"),
                                      ("cc-by-4.0", "by"), ("cc-by-2.0", "by"), ("CC-BY-3.0", "by"), ("by", "by")])
def test_licence_gate_accepts_public_domain_cc0_and_cc_by(raw, want):
    assert fa.licence_code(raw) == want


def test_commons_keeps_pd_cc0_by_and_drops_by_sa_and_unknown():
    found = fa.parse_commons(COMMONS, min_width=1000)
    titles = {c["title"] for c in found}
    assert any("Landing of the submarine cable" in t for t in titles)           # cc0
    assert any("Submarine Cable Breaks at Valdez" in t for t in titles)        # pd
    assert not any("HMAS Stalwart" in t for t in titles)                       # CC BY-SA 4.0
    assert not any("Skewjack" in t for t in titles)                            # CC BY-SA 2.0
    assert not any("Faraday" in t for t in titles)                             # "No restrictions": not a licence we can name
    assert not any("slack indicator" in t for t in titles)                     # public domain but only 501 px wide
    assert {c["licence_code"] for c in found} <= {"cc0", "pdm", "by"}


def test_openverse_recorded_response_keeps_only_by_and_cc0():
    found = fa.parse_openverse(OPENVERSE, min_width=1000)
    assert found and {c["licence_code"] for c in found} <= {"cc0", "pdm", "by"}
    assert all(c["url"].startswith("https://") for c in found)


def test_openverse_response_that_ignores_the_licence_filter_is_still_rejected():
    assert fa.parse_openverse(BAD, min_width=0) == []


def test_candidates_carry_what_attribution_needs():
    c = next(c for c in fa.parse_openverse(OPENVERSE, min_width=1000) if c["licence_code"] == "by")
    for key in ("title", "creator", "licence", "licence_url", "page_url", "url", "source", "attribution"):
        assert c[key], key
    assert "CC BY" in c["attribution"] and c["creator"] in c["attribution"] and c["title"].split(".")[0][:10] in c["attribution"]


def test_commons_artist_html_is_reduced_to_plain_text():
    page = next(iter(COMMONS["query"]["pages"].values()))
    page = json.loads(json.dumps(page))
    page["imageinfo"][0]["extmetadata"]["Artist"] = {"value": '<a href="//commons.wikimedia.org/wiki/User:X">Ada &amp; Co</a>'}
    page["imageinfo"][0]["extmetadata"]["License"] = {"value": "cc-by-4.0"}
    page["imageinfo"][0]["width"] = 3000
    c = fa.parse_commons({"query": {"pages": {"1": page}}}, min_width=0)[0]
    assert c["creator"] == "Ada & Co" and "<" not in c["attribution"]


# ---- requests -------------------------------------------------------------------------------------------------------

def test_search_asks_only_for_allowed_licences_and_bitmaps(monkeypatch):
    calls = []
    fake_network(monkeypatch, {"commons.wikimedia.org": COMMONS, "openverse.org": OPENVERSE}, calls)
    fa.search("submarine cable", source="both", limit=5, min_width=1000, delay=0)
    ov = next(u for u in calls if "openverse" in u)
    assert urllib.parse.parse_qs(urllib.parse.urlsplit(ov).query)["license"] == ["cc0,pdm,by"]
    cm = next(u for u in calls if "commons.wikimedia" in u)
    assert "filetype%3Abitmap" in cm or "filetype:bitmap" in urllib.parse.unquote(cm)


def test_search_survives_one_source_failing(monkeypatch):
    fake_network(monkeypatch, {"openverse.org": OPENVERSE})            # Commons answers 404
    found = fa.search("cable", source="both", limit=5, min_width=1000, delay=0)
    assert found and all(c["source"] != "wikimedia-commons" for c in found)


def test_polite_rate_waits_between_calls(monkeypatch):
    waits = []
    monkeypatch.setattr(fa.time, "sleep", waits.append)
    fake_network(monkeypatch, {"commons.wikimedia.org": COMMONS, "openverse.org": OPENVERSE})
    fa.search("cable", source="both", limit=3, min_width=1000, delay=1.5)
    assert waits and max(waits) <= 1.5 and max(waits) > 0


def test_http_layer_retries_5xx_then_succeeds(monkeypatch):
    import fetch_music
    attempts = []

    class Resp(io.BytesIO):
        headers = {"Content-Type": "application/json"}
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def urlopen(req, timeout=0):
        attempts.append(req.get_header("User-agent"))
        if len(attempts) < 3:
            raise urllib.error.HTTPError(req.full_url, 504, "Gateway Timeout", {}, None)
        return Resp(b'{"ok": true}')

    monkeypatch.setattr(fetch_music.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(fetch_music.time, "sleep", lambda s: None)
    body, _ = fetch_music.http_get("https://example.invalid/x", 3, 0.01, agent="brief2mp4-fetch-archive/1.0")
    assert json.loads(body) == {"ok": True} and len(attempts) == 3 and attempts[0].startswith("brief2mp4-fetch-archive")


# ---- download and the asset record ----------------------------------------------------------------------------------

def first_candidate():
    return fa.parse_openverse(OPENVERSE, min_width=1000)[0]


def test_download_writes_the_image_and_one_assets_entry(tmp_path, monkeypatch):
    c = first_candidate()
    fake_network(monkeypatch, {c["url"]: fc.png_bytes()})
    entry = fa.download(c, tmp_path / "assets" / "archive", tmp_path / "ASSETS.json", delay=0)
    saved = tmp_path / entry["file"]
    assert saved.is_file() and saved.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    data = json.loads((tmp_path / "ASSETS.json").read_text(encoding="utf-8"))
    assert len(data["assets"]) == 1
    for key in ("file", "source_url", "author", "licence", "attribution", "sha256", "retrieved"):
        assert entry[key], key
    assert not entry["file"].startswith("/")                                 # relative to the project
    fa.download(c, tmp_path / "assets" / "archive", tmp_path / "ASSETS.json", delay=0)
    assert len(json.loads((tmp_path / "ASSETS.json").read_text(encoding="utf-8"))["assets"]) == 1   # re-running does not duplicate


def test_download_refuses_a_web_page_and_keeps_nothing(tmp_path, monkeypatch):
    c = first_candidate()
    fake_network(monkeypatch, {c["url"]: b"<html>" + b"x" * 4000 + b"</html>"})
    with pytest.raises(FetchError, match="not an image"):
        fa.download(c, tmp_path / "a", tmp_path / "ASSETS.json", delay=0)
    assert not list((tmp_path / "a").glob("*")) and not (tmp_path / "ASSETS.json").exists()


def test_download_refuses_a_candidate_that_fails_the_gate_even_if_called_directly(tmp_path, monkeypatch):
    c = {**first_candidate(), "licence_code": "by-sa"}
    fake_network(monkeypatch, {c["url"]: fc.png_bytes()})
    with pytest.raises(FetchError, match="licence"):
        fa.download(c, tmp_path / "a", tmp_path / "ASSETS.json", delay=0)


def test_cli_search_and_download(tmp_path, monkeypatch, capsys):
    fake_network(monkeypatch, {"openverse.org/v1/images": OPENVERSE, "commons.wikimedia.org": COMMONS, "staticflickr": fc.png_bytes(),
                               "upload.wikimedia.org": fc.png_bytes(), "rawpixel": fc.png_bytes()})
    assert fa.main(["search", "cable ship", "--source", "openverse", "--delay", "0"]) == 0
    assert "CC BY" in capsys.readouterr().out
    assert fa.main(["download", "cable ship", "--source", "openverse", "--pick", "1", "--out-dir", str(tmp_path / "a"),
                    "--assets", str(tmp_path / "ASSETS.json"), "--delay", "0"]) == 0
    assert (tmp_path / "ASSETS.json").exists()


def test_cli_says_so_when_nothing_is_usable(monkeypatch, capsys):
    fake_network(monkeypatch, {"openverse.org": BAD, "commons.wikimedia.org": {"query": {"pages": {}}}})
    assert fa.main(["search", "x", "--delay", "0"]) == 1
    assert "no usable" in capsys.readouterr().out.lower()


def test_prints_help():
    proc = fc.run([sys.executable, fc.SCRIPTS / "fetch_archive.py", "--help"])
    assert proc.returncode == 0 and "usage" in proc.stdout.lower()
