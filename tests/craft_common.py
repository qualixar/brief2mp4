"""Helpers for the craft-check tests (no tests here): tiny clips made by ffmpeg at test time, a script runner.

Nothing binary is committed. Every fixture is generated from ffmpeg's lavfi sources (testsrc2, color, sine)
or, for text, from a built-in 5x7 bitmap font written as a PNG by the standard library.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zlib
import struct
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin" / "skills" / "brief2mp4"
SCRIPTS = SKILL / "scripts"
REFS = SKILL / "references"

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="ffmpeg/ffprobe not found")
def _find_bash():
    """bash for the shell scripts. On Windows `bash` on PATH is often the WSL launcher in System32, which cannot run
    these scripts, so look for Git Bash instead (B2M_BASH overrides); skip when it is not installed."""
    if os.name != "nt":
        return shutil.which("bash")
    for cand in (os.environ.get("B2M_BASH"), r"C:\Program Files\Git\bin\bash.exe",
                 r"C:\Program Files\Git\usr\bin\bash.exe", shutil.which("bash")):
        if cand and os.path.isfile(cand) and "system32" not in cand.lower():
            return cand
    return None


BASH = _find_bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="bash (Git Bash on Windows) not found")

X264 = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "14"]


def ffmpeg(*args) -> None:
    """Run ffmpeg quietly; raise with its message if it fails."""
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *[str(a) for a in args]],
                          capture_output=True, text=True)
    assert proc.returncode == 0, f"ffmpeg failed: {proc.stderr}"


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, **kw.pop("env", {})}, **kw)


def py_script(name: str, *args, **kw) -> subprocess.CompletedProcess:
    return run([sys.executable, SCRIPTS / name, *args], **kw)


def bash_script(name: str, *args, **kw) -> subprocess.CompletedProcess:
    return run([BASH, SCRIPTS / name, *args], **kw)


# ---- clips -----------------------------------------------------------------------------------------------------

def moving_clip(path: Path, seconds: float = 3, flash: tuple | None = None) -> Path:
    """320x180 30 fps testsrc2 (moving content). flash=(first_frame, last_frame) paints those frames white."""
    vf = []
    if flash:
        vf = ["-vf", f"drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='between(n,{flash[0]},{flash[1]})'"]
    ffmpeg("-f", "lavfi", "-i", f"testsrc2=s=320x180:r=30:d={seconds}", *vf, *X264, path)
    return path


def cut_clip(path: Path) -> Path:
    """1.5 s of testsrc2, then a hard cut to 1.5 s of a different picture (mandelbrot)."""
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=1.5", "-f", "lavfi", "-i", "mandelbrot=s=320x180:r=30",
           "-filter_complex", "[1:v]trim=duration=1.5,setpts=PTS-STARTPTS[b];[0:v][b]concat=n=2:v=1:a=0", *X264, path)
    return path


def joined_clip(path: Path) -> Path:
    """One continuous 3 s clip, cut in two at 1.5 s and joined again (a clean join)."""
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=3", "-filter_complex",
           "[0:v]trim=0:1.5,setpts=PTS-STARTPTS[a];[0:v]trim=1.5:3,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0",
           *X264, path)
    return path


def pan_clip(path: Path) -> Path:
    """A slow pan (10 px per second) across a wide testsrc2 image."""
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=1280x180:r=30:d=4", "-vf", "crop=320:180:x='t*10':y=0", *X264, path)
    return path


def frozen_clip(path: Path) -> Path:
    """1 s of motion, then 3 s of one flat colour."""
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=1", "-f", "lavfi", "-i", "color=c=#202040:s=320x180:r=30:d=3",
           "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0", *X264, path)
    return path


# ---- text in a still (no drawtext needed): a 5x7 bitmap font written as a PNG --------------------------------------

FONT = {
    "A": "01110 10001 10001 11111 10001 10001 10001", "C": "01110 10001 10000 10000 10000 10001 01110",
    "D": "11110 10001 10001 10001 10001 10001 11110", "E": "11111 10000 10000 11110 10000 10000 11111",
    "I": "01110 00100 00100 00100 00100 00100 01110", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "O": "01110 10001 10001 10001 10001 10001 01110",
    "P": "11110 10001 10001 11110 10000 10000 10000", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "/": "00001 00010 00010 00100 01000 01000 10000",
    ":": "00000 00100 00100 00000 00100 00100 00000", " ": "00000 00000 00000 00000 00000 00000 00000",
    "H": "10001 10001 10001 11111 10001 10001 10001", "N": "10001 11001 10101 10101 10011 10001 10001",
    "W": "10001 10001 10001 10101 10101 11011 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "G": "01110 10001 10000 10111 10001 10001 01110", "Y": "10001 10001 01010 00100 00100 00100 00100",
}


def text_png(path: Path, lines: list[str], size=(1280, 720), scale=14, origin=(80, 80)) -> Path:
    """Black letters on white, one bitmap-font line per entry (capitals, space, / and : only)."""
    w, h = size
    rows = [bytearray([255]) * w for _ in range(h)]
    y0 = origin[1]
    for line in lines:
        x0 = origin[0]
        for ch in line.upper():
            glyph = FONT[ch].split()
            for gy, bits in enumerate(glyph):
                for gx, bit in enumerate(bits):
                    if bit == "1":
                        for yy in range(y0 + gy * scale, y0 + (gy + 1) * scale):
                            for xx in range(x0 + gx * scale, x0 + (gx + 1) * scale):
                                if 0 <= yy < h and 0 <= xx < w:
                                    rows[yy][xx] = 0
            x0 += 6 * scale
        y0 += 9 * scale
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    path.write_bytes(png)
    return path


def still_video(path: Path, png: Path, seconds: float = 2, fps: int = 5, soften: int = 8) -> Path:
    """Loop one PNG into a short H.264 clip. The blur rounds the blocky bitmap letters so OCR can read them."""
    ffmpeg("-loop", "1", "-framerate", str(fps), "-i", png, "-t", seconds, "-vf", f"gblur=sigma={soften}", *X264, path)
    return path
