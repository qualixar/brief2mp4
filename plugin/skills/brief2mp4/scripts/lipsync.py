#!/usr/bin/env python3
"""lipsync.py: turn word timestamps (or, failing that, a WAV file) into a mouth-shape track for the character rig.

    python3 lipsync.py words.json                      # word timestamps -> [{"t": 3.4, "v": "AI"}, ...]
    python3 lipsync.py words.json --lang hi --fps 24   # romanised Hindi, best effort
    python3 lipsync.py --wav voice.wav                 # no timestamps: open, half-open and closed mouth from loudness
    python3 lipsync.py words.json --from 3.2 --to 6.0 --out visemes.json   # only the words in a time range

Input is what `npx hyperframes transcribe voice.wav` writes: a list of {"text", "start", "end"} words (an object
with a "words" list also works). Output is a list of {"t", "v"} keys; a mouth shape holds until the next key. The
nine shapes are rest, AI, E, O, U, MBP, FV, L and etc (every other consonant).

How a word becomes shapes: letter rules (digraphs first, then single letters) with a small table of exceptions,
spread across the word's time in proportion to how long each sound takes (vowels longest). The mouth closes
("rest") in a pause longer than 150 ms, and no shape is held for less than one frame at --fps: every key is snapped
to the frame grid, a shape that would be shorter is merged into its neighbour, and a word too short for all its
shapes drops the weakest consonants first. English rules are tuned for English; --lang hi reads romanised Hindi
(aa, ee, oo, kh, bh and so on) and is approximate: it is a mouth, not a phonetic transcription. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import wave
from pathlib import Path

VISEMES = ("rest", "AI", "E", "O", "U", "MBP", "FV", "L", "etc")
VOWEL_WEIGHT, CONSONANT_WEIGHT = 2.0, 0.8
PAUSE_CLOSE = 0.15           # a gap longer than this closes the mouth

# Words the letter rules get wrong, as the shapes you see when they are said.
EXCEPTIONS = {
    "the": ["L", "E"], "a": ["AI"], "i": ["AI"], "you": ["etc", "U"], "your": ["etc", "O", "etc"], "one": ["U", "etc"], "once": ["U", "etc"],
    "two": ["etc", "U"], "to": ["etc", "U"], "do": ["etc", "U"], "who": ["U"], "whose": ["U", "etc"], "what": ["U", "AI", "etc"], "was": ["U", "AI", "etc"],
    "were": ["U", "E"], "said": ["etc", "E", "etc"], "are": ["AI", "etc"], "of": ["O", "FV"], "love": ["L", "AI", "FV"], "some": ["etc", "AI", "MBP"],
    "come": ["etc", "AI", "MBP"], "give": ["etc", "E", "FV"], "have": ["etc", "AI", "FV"], "my": ["MBP", "AI"], "me": ["MBP", "E"], "we": ["U", "E"],
    "she": ["etc", "E"], "he": ["etc", "E"], "be": ["MBP", "E"], "no": ["etc", "O"], "so": ["etc", "O"], "go": ["etc", "O"], "hey": ["etc", "E"],
    "kite": ["etc", "AI", "etc"], "little": ["L", "E", "etc", "L"], "one's": ["U", "etc"], "water": ["U", "O", "etc", "E"], "mister": ["MBP", "E", "etc", "etc", "E"],
}

DIGRAPHS = [   # (letters, shapes), longest first
    ("tch", ["etc"]), ("sch", ["etc"]), ("igh", ["AI"]), ("ough", ["O"]), ("eigh", ["E"]), ("th", ["L"]), ("sh", ["etc"]), ("ch", ["etc"]), ("zh", ["etc"]),
    ("ph", ["FV"]), ("gh", []), ("ng", ["etc"]), ("ck", ["etc"]), ("qu", ["etc", "U"]), ("wh", ["U"]), ("kn", ["etc"]), ("wr", ["etc"]),
    ("oo", ["U"]), ("ou", ["O"]), ("ow", ["O"]), ("oa", ["O"]), ("oi", ["O"]), ("oy", ["O"]), ("ee", ["E"]), ("ea", ["E"]), ("ie", ["E"]), ("ey", ["E"]),
    ("ai", ["AI"]), ("ay", ["AI"]), ("au", ["O"]), ("aw", ["O"]), ("ew", ["U"]), ("ue", ["U"]), ("ar", ["AI", "etc"]), ("or", ["O", "etc"]),
]
HINDI_DIGRAPHS = [
    ("chh", ["etc"]), ("aa", ["AI"]), ("ee", ["E"]), ("ii", ["E"]), ("oo", ["U"]), ("uu", ["U"]), ("ai", ["E"]), ("au", ["O"]), ("kh", ["etc"]), ("gh", ["etc"]),
    ("ch", ["etc"]), ("jh", ["etc"]), ("th", ["etc"]), ("dh", ["etc"]), ("sh", ["etc"]), ("ph", ["MBP"]), ("bh", ["MBP"]), ("ng", ["etc"]),
]
SINGLE = {"a": "AI", "e": "E", "i": "E", "o": "O", "u": "AI", "b": "MBP", "m": "MBP", "p": "MBP", "f": "FV", "v": "FV", "l": "L", "w": "U", "q": "etc", "y": "E"}
SINGLE_HI = {"a": "AI", "e": "E", "i": "E", "o": "O", "u": "U", "b": "MBP", "m": "MBP", "p": "MBP", "f": "FV", "v": "FV", "l": "L", "w": "U", "y": "E"}


def _is_vowel(shape: str) -> bool:
    return shape in ("AI", "E", "O", "U")


def _shapes_for(word: str, lang: str) -> list[str]:
    """Letters to mouth shapes, in order. Empty if the word has no letters (a bare number or punctuation)."""
    letters = re.sub(r"[^a-z]", "", word.lower().replace("'", ""))
    if not letters:
        return []
    if lang == "en" and letters in EXCEPTIONS:
        return list(EXCEPTIONS[letters])
    table, single = (HINDI_DIGRAPHS, SINGLE_HI) if lang == "hi" else (DIGRAPHS, SINGLE)
    if lang == "hi" and len(letters) > 2 and letters.endswith("a") and not letters.endswith("aa"):
        letters = letters[:-1]       # a final schwa is usually not said: "namaste", "bahut"
    elif lang == "en" and len(letters) > 3 and letters.endswith("e") and letters[-2] not in "aeiouly":
        letters = letters[:-1]       # a silent final e: "make", "kite"
    out, i = [], 0
    while i < len(letters):
        hit = next(((k, v) for k, v in table if letters.startswith(k, i)), None)
        if hit:
            out += hit[1]
            i += len(hit[0])
            continue
        ch = letters[i]
        shape = single.get(ch, "etc")
        if ch == "i" and lang == "en" and (letters[i + 1:i + 3] in ("nd", "ld", "gh") or i == len(letters) - 1):
            shape = "AI"
        if ch == "y" and lang == "en":
            shape = "AI" if (i == len(letters) - 1 and len(letters) <= 3) else "etc" if i == 0 else "E"
        out.append(shape)
        i += 1
    return [s for n, s in enumerate(out) if n == 0 or s != out[n - 1]]      # "ll", "mm", "pp" are one shape


def _allocate(shapes: list[str], start: float, end: float, min_dur: float) -> list[tuple[float, str]]:
    """Spread a word's shapes over its time. Each gets at least min_dur; the rest is shared by how long the sound is."""
    shapes = shapes[:]
    room = max(1, int((end - start) / min_dur + 1e-9))
    while len(shapes) > room:           # no room for every shape: drop the weakest consonant, else the last
        weak = [n for n, s in enumerate(shapes) if s == "etc"] or [n for n, s in enumerate(shapes) if not _is_vowel(s)] or [len(shapes) - 1]
        shapes.pop(weak[0])
    weights = [VOWEL_WEIGHT if _is_vowel(s) else CONSONANT_WEIGHT for s in shapes]
    spare = max(0.0, (end - start) - min_dur * len(shapes))
    t, out = start, []
    for s, w in zip(shapes, weights):
        out.append((t, s))
        t += min_dur + spare * w / sum(weights)
    return out


def _tidy(keys: list[tuple[float, str]], end: float, fps: float) -> list[dict]:
    """Snap every key to the frame grid, fold shapes shorter than a frame into their neighbours, drop repeats."""
    frame = 1.0 / fps
    snapped: list[tuple[int, str]] = []
    for t, v in keys:
        n = int(round(t * fps))
        if snapped and snapped[-1][0] == n:
            snapped[-1] = (n, v)            # two keys on one frame: the later one wins
        else:
            snapped.append((n, v))
    out: list[tuple[int, str]] = []
    for n, v in snapped:
        if out and out[-1][1] == v:
            continue
        out.append((n, v))
    end_n = max(int(round(end * fps)), out[-1][0] + 1) if out else 0
    return [{"t": round(n * frame, 4), "v": v} for n, v in out] + ([{"t": round(end_n * frame, 4), "v": "rest"}] if out and out[-1][1] != "rest" else [])


def build_track(words: list[dict], fps: float = 30.0, lang: str = "en") -> list[dict]:
    """Word timestamps to a viseme track. The mouth is closed before the first word, in pauses over 150 ms and after the last."""
    clean = [w for w in sorted(words, key=lambda w: w["start"]) if w["end"] > w["start"]]
    if not clean:
        return []
    min_dur, keys = 1.0 / fps, []
    for i, w in enumerate(clean):
        shapes = _shapes_for(w["text"], lang)
        if not shapes:
            continue
        keys += _allocate(shapes, w["start"], w["end"], min_dur)
        nxt = clean[i + 1]["start"] if i + 1 < len(clean) else None
        if nxt is None or nxt - w["end"] > PAUSE_CLOSE:
            keys.append((w["end"], "rest"))
    if not keys:
        return []
    return _tidy([(max(0.0, keys[0][0] - min_dur), "rest")] + keys, clean[-1]["end"], fps)


def load_words(path: Path) -> list[dict]:
    """Read the word list `hyperframes transcribe` writes (a list, or an object holding "words" or "segments")."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("words") or [w for seg in data.get("segments", []) for w in seg.get("words", [])]
    out = []
    for w in data:
        text, start, end = w.get("text", w.get("word")), w.get("start", w.get("t0")), w.get("end", w.get("t1"))
        if text is None or start is None or end is None:
            raise ValueError(f"a word needs text, start and end: {w!r}")
        out.append({"text": str(text), "start": float(start), "end": float(end)})
    return out


def _samples(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wf:
        width, rate, chans, frames = wf.getsampwidth(), wf.getframerate(), wf.getnchannels(), wf.getnframes()
        raw = wf.readframes(frames)
    if width == 1:
        vals = [(b - 128) / 128.0 for b in raw]
    elif width == 2:
        vals = [v / 32768.0 for v in struct.unpack("<%dh" % (len(raw) // 2), raw)]
    elif width == 3:
        vals = [int.from_bytes(raw[i:i + 3], "little", signed=True) / 8388608.0 for i in range(0, len(raw) - 2, 3)]
    elif width == 4:
        vals = [v / 2147483648.0 for v in struct.unpack("<%di" % (len(raw) // 4), raw)]
    else:
        raise ValueError(f"unsupported sample width {width}")
    mono = [sum(vals[i:i + chans]) / chans for i in range(0, len(vals) - chans + 1, chans)]
    return mono, rate


def amplitude_track(path: Path, fps: float = 30.0) -> list[dict]:
    """No word timestamps: an open, half-open or closed mouth from how loud the voice is in each frame."""
    try:
        mono, rate = _samples(Path(path))
    except wave.Error as exc:
        raise ValueError(f"{path}: not a PCM WAV file ({exc}). Convert it first: ffmpeg -i in.mp3 -ar 48000 out.wav") from exc
    hop = max(1, int(rate / fps))
    rms = []
    for i in range(0, len(mono), hop):
        chunk = mono[i:i + hop]
        rms.append((sum(x * x for x in chunk) / len(chunk)) ** 0.5)
    if not rms:
        return []
    peak = sorted(rms)[int(0.95 * (len(rms) - 1))]
    floor = max(0.004, 0.08 * peak)
    shapes = ["rest" if r < floor else "etc" if r < 0.45 * peak else "AI" for r in rms]
    keys = [(i / fps, s) for i, s in enumerate(shapes)]
    return _tidy(keys, len(rms) / fps, fps)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("words", nargs="?", help="word timestamps JSON from `npx hyperframes transcribe`")
    ap.add_argument("--wav", help="no timestamps: use the loudness of this WAV file instead")
    ap.add_argument("--fps", type=float, default=30.0, help="the video's frame rate (default 30)")
    ap.add_argument("--lang", choices=("en", "hi"), default="en", help="en, or hi for romanised Hindi (approximate)")
    ap.add_argument("--from", dest="t0", type=float, help="only words starting at or after this time (seconds)")
    ap.add_argument("--to", dest="t1", type=float, help="only words starting before this time (seconds)")
    ap.add_argument("--out", help="write the track here instead of printing it")
    args = ap.parse_args(argv)
    if not args.words and not args.wav:
        ap.error("give a words JSON file, or --wav FILE")
    if args.fps <= 0:
        ap.error("--fps must be above 0")
    try:
        if args.words:
            words = [w for w in load_words(Path(args.words)) if (args.t0 is None or w["start"] >= args.t0) and (args.t1 is None or w["start"] < args.t1)]
            track = build_track(words, args.fps, args.lang)
        else:
            track = amplitude_track(Path(args.wav), args.fps)
    except (OSError, ValueError, KeyError) as exc:
        print(f"lipsync.py: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(track, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
