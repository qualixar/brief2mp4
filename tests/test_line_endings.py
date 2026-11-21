"""Every tracked file must have a fixed line ending (or be binary).

`* text=auto` alone lets each machine pick its own endings, so a Windows
checkout with core.autocrlf turns unpinned text files into CRLF. These tests
catch that on any OS by reading git's attributes, not the working tree.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (REPO / ".git").exists(),
    reason="needs a git checkout",
)


def _git(*args):
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True)
    return out.stdout


def _attrs():
    files = [f for f in _git("ls-files", "-z").split("\0") if f]
    proc = subprocess.run(
        ["git", "-C", str(REPO), "check-attr", "-z", "text", "eol", "--stdin", "-z"],
        input="\0".join(files), capture_output=True, text=True, check=True,
    )
    parts = proc.stdout.split("\0")
    table = {}
    for i in range(0, len(parts) - 2, 3):
        path, attr, value = parts[i], parts[i + 1], parts[i + 2]
        table.setdefault(path, {})[attr] = value
    return table


def test_every_tracked_file_has_a_pinned_ending_or_is_binary():
    loose = [p for p, a in _attrs().items() if a.get("text") != "unset" and a.get("eol") not in ("lf", "crlf")]
    assert not loose, f"add an eol rule (or 'binary') to .gitattributes for: {sorted(loose)[:20]}"


def test_only_powershell_files_use_crlf():
    crlf = [p for p, a in _attrs().items() if a.get("eol") == "crlf"]
    assert all(p.endswith(".ps1") for p in crlf), crlf
