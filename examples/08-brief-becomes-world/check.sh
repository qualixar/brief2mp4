#!/usr/bin/env bash
# check.sh: run every "Done when" check of brief 08 on your own render.
# Usage: bash check.sh <path/to/final.mp4> [brief2mp4 scripts folder]
# Writes stills to ./checks next to where you run it. Needs ffmpeg, ffprobe, python3.
set -u
F="${1:?usage: bash check.sh final.mp4 [brief2mp4 scripts folder]}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
S="${2:-}"
if [ -z "$S" ]; then
  for d in "$HOME/.claude/skills/brief2mp4/scripts" "$HOME/.codex/skills/brief2mp4/scripts" "$HERE/../../plugin/skills/brief2mp4/scripts"; do
    [ -f "$d/check_delivery.sh" ] && S="$d" && break
  done
fi
[ -f "${S:-}/check_delivery.sh" ] || { echo "brief2mp4 scripts folder not found; pass it as the second argument"; exit 1; }
mkdir -p checks
LAST=$(( $(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$F") - 1 ))

echo "## 1. Delivery: 1920x1080, 30 fps, 25.0 s, H.264 + AAC, loudness -16 LUFS +/- 1"
bash "$S/check_delivery.sh" "$F" --seconds 25 --size 1920x1080 --fps 30 --lufs -16

echo; echo "## 2. Stills to open and look at (word peel 1.8 s, city 6 s, charts 11.5 s, galaxy 17 s, title 22 s)"
bash "$S/contact_sheet.sh" "$F" --at 0,1.8,3,6,9,11.5,14,17,20,20.5,22,23.5,24.9 --out checks

echo; echo "## 3. No cuts: scene changes found by scdet at threshold 10 (want 0)"
ffmpeg -hide_banner -nostats -i "$F" -vf "scdet=threshold=10" -an -f null - 2>&1 | grep -c "lavfi.scd.time"

echo; echo "## 4. Loop: SSIM of the first frame vs the last frame (want 0.90 or more)"
ffmpeg -v error -y -i "$F" -vf "select=eq(n\,0)" -frames:v 1 checks/first.png
ffmpeg -v error -y -i "$F" -vf "select=eq(n\,$LAST)" -frames:v 1 checks/last.png
ffmpeg -hide_banner -nostats -i checks/first.png -i checks/last.png -lavfi ssim -f null - 2>&1 | grep -o "All:[0-9.]*"

echo; echo "## 5. Title: ink box at 20.5, 22.0 and 23.5 s (want 150 px or taller, same box each time)"
for t in 020.50 022.00 023.50; do
  ffmpeg -v error -y -i "checks/t_${t}s.png" -vf "format=gray,lut=y='if(gt(val,150),255,0)'" "checks/bin_$t.png"
  python3 "$S/bounds.py" "checks/bin_$t.png" --bg "#000000" --region 100,300,1820,625 | head -1
done

echo; echo "## 6. Margins: all type at 22.0 s inside 64 px of the frame edge"
python3 "$S/bounds.py" checks/bin_022.00.png --bg "#000000" --margin 64,64 | head -1

echo; echo "## 7. No teal or mint: share of teal/mint-hue pixels per still (want a fraction of a percent, no region)"
python3 "$HERE/hue_scan.py" "$S/bounds.py" checks/t_0*.png | tail -1

echo; echo "Now open the stills in ./checks and read the five chip texts and the title against BRIEF.md."
