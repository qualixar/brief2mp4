#!/usr/bin/env python3
"""hue_scan.py: count pixels whose hue reads as teal, mint or cyan-green (hue 140-190 deg) with real
saturation and brightness. Uses the PNG reader from the skill's bounds.py. Usage: hue_scan.py BOUNDS_PY still.png ..."""
import sys, colorsys, importlib.util
spec = importlib.util.spec_from_file_location("bounds", sys.argv[1]); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
worst = 0
for path in sys.argv[2:]:
    w, h, ch, rows = b.read_png(path)
    n = 0; tot = 0
    for row in rows:
        for x in range(0, w * ch, ch * 2):          # every second pixel
            r, g, bl = row[x], row[x + 1], row[x + 2]
            tot += 1
            hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, bl / 255)
            if 140 <= hh * 360 <= 190 and s > 0.35 and v > 0.3: n += 1
    worst = max(worst, n / tot)
    print(f"{path}: teal/mint-hue pixels {n} of {tot} sampled ({100 * n / tot:.4f}%)")
print(f"worst still: {100 * worst:.4f}%")
