#!/usr/bin/env python3
"""make_standin_voice.py: a stand-in voice track made from the word timings, so the example renders with sound
and the delivery checks have something to measure. It is a buzz that rises and falls with each word, not speech.
Record your own voice and replace it.

    python3 make_standin_voice.py words.json voice.wav [SECONDS]

Standard library only.
"""
import json
import math
import struct
import sys
import wave

RATE = 48000


def main(argv):
    words = json.load(open(argv[0], encoding="utf-8"))
    seconds = float(argv[2]) if len(argv) > 2 else max(w["end"] for w in words) + 0.5
    out = [0.0] * int(seconds * RATE)
    for w in words:
        a, b = int(w["start"] * RATE), int(w["end"] * RATE)
        f0 = 150 + 25 * math.sin(len(w["text"]) * 1.7)
        for i in range(a, min(b, len(out))):
            x = (i - a) / max(1, b - a)
            env = math.sin(math.pi * x) ** 0.6
            t = i / RATE
            f = f0 * (1 + 0.06 * math.sin(2 * math.pi * 5.5 * t) + 0.12 * (0.5 - x))
            ph = 2 * math.pi * f * t
            out[i] += env * 0.22 * (math.sin(ph) + 0.5 * math.sin(2 * ph) + 0.3 * math.sin(3 * ph + 1.0) + 0.15 * math.sin(7 * ph))
    with wave.open(argv[1], "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(RATE)
        wf.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32000)) for v in out))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1:])
