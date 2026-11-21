"""Helpers for the film-mode tests (no tests here): script imports, recorded API responses, tiny media made at test time."""
from __future__ import annotations

import json
import math
import struct
import sys
import wave
import zlib
from pathlib import Path

from craft_common import SCRIPTS, SKILL, REPO, run, py_script, bash_script, ffmpeg, needs_ffmpeg, needs_bash  # noqa: F401  (re-exported)

DATA = Path(__file__).resolve().parent / "data" / "film"
TEMPLATES = SKILL / "templates" / "film"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

RATE = 48000


def recorded(name: str) -> dict:
    """A recorded (trimmed) API response from tests/data/film."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def png_bytes(w: int = 64, h: int = 48, rgb=(120, 90, 60)) -> bytes:
    """A small valid PNG with a diagonal gradient (so a push-in over it visibly changes)."""
    rows = b"".join(b"\x00" + b"".join(bytes((min(255, rgb[0] + x + y), rgb[1], rgb[2])) for x in range(w)) for y in range(h))

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def write_wav(path: Path, samples: list[float], rate: int = RATE) -> Path:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32000)) for v in samples))
    return path


def tone_and_silence(path: Path, plan: list[tuple[str, float]], freq: float = 220.0, amp: float = 0.4) -> tuple[Path, list[tuple[float, float]]]:
    """A WAV made of ("tone", seconds) and ("gap", seconds) pieces, with a faint room-noise floor in the gaps.

    Returns the path and the (start, end) of every tone, so a test knows where each "line" really is.
    """
    out: list[float] = []
    bounds: list[tuple[float, float]] = []
    t = 0.0
    seed = 12345
    for kind, seconds in plan:
        n = int(seconds * RATE)
        if kind == "tone":
            bounds.append((t, t + seconds))
        for i in range(n):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            floor = ((seed / 0x7FFFFFFF) - 0.5) * 0.002
            if kind == "tone":
                env = min(1.0, i / 240, (n - i) / 240)          # 5 ms ramps, so no click
                out.append(amp * env * math.sin(2 * math.pi * freq * (i / RATE)) + floor)
            else:
                out.append(floor)
        t += seconds
    return write_wav(path, out), bounds


def wav_info(path: Path) -> tuple[float, int]:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate(), wf.getframerate()
