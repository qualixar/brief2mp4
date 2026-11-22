#!/usr/bin/env bash
# build.sh: render the five acts of brief 10 with the Blender motion recipes, join them, finish and check.
#
#   bash build.sh                 # full film: build/final.mp4 (about 15-30 minutes on a laptop)
#   bash build.sh --preview       # three stills per act at 960x540 in build/preview, nothing else
#
# Needs Blender and ffmpeg. Set B2M3D_BLENDER if Blender is not on the PATH; B2M_SKILL points at the skill folder
# (default: the one in this repository).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="${B2M_SKILL:-$HERE/../../plugin/skills/brief2mp4}"
REC="$SKILL/3d/templates/recipes"
BLENDER="${B2M3D_BLENDER:-$(command -v blender || echo /Applications/Blender.app/Contents/MacOS/Blender)}"
[[ -x "$BLENDER" ]] || { echo "build.sh: Blender not found; set B2M3D_BLENDER" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "build.sh: ffmpeg not found" >&2; exit 2; }
OUT="$HERE/build"
PREVIEW=0; [[ "${1:-}" == "--preview" ]] && PREVIEW=1
SIZE=(--width 1920 --height 1080 --samples 24)
(( PREVIEW )) && SIZE=(--width 960 --height 540 --samples 8)
PALETTE=(--bg "#1a1d29" --floor "#262a3a" --subject "#f0b24a" --accent "#d9573b" --ink "#f3ecdd")
mkdir -p "$OUT"

# act N, recipe, caption, frames to render in preview, recipe options
act() {
  local n="$1" recipe="$2" caption="$3" preview="$4"; shift 4
  local dir="$OUT/act$n"; rm -rf "$dir"
  local frames=(); (( PREVIEW )) && frames=(--render-frames "$preview")
  "$BLENDER" -b --factory-startup -P "$REC/b2m_$recipe.py" -- "${PALETTE[@]}" "${SIZE[@]}" --caption "$caption" --out "$dir" \
    ${frames[@]+"${frames[@]}"} --json "$OUT/act$n.json" "$@" > "$OUT/act$n.log" 2>&1 || { tail -20 "$OUT/act$n.log" >&2; exit 1; }
  echo "act $n ($recipe): $(grep -o '"max_slide_per_frame": [0-9.e-]*\|"centre_z": [0-9.]*\|"max_joint_gap": [0-9.e-]*\|"final_width": [0-9.]*\|"seam_slope_gap": [0-9.e-]*' "$OUT/act$n.log" | head -1)"
}

act 1 cloth  "Cloth drop"            "30,60,100" --frames 120 --object sphere --cloth-res 48 --smooth-levels 1 --drop-height 2.2 --delay 24
act 2 rigid  "Hinged chain"          "1,30,60"   --frames 120 --links 7 --link-length 0.45 --release-angle 85 --damping 0.01 --anchor-height 3.5
act 3 fold   "Folding"               "30,70,120" --folds 3 --fold-frames 29 --pause 8
act 4 walk   "Walking, feet planted" "30,60,100" --frames 120 --speed 1.2 --cycle-frames 32
LOOP_FRAMES=(--render-frames 1-60); (( PREVIEW )) && LOOP_FRAMES=()      # the loop is frames 1-60; frame 61 only repeats frame 1
act 5 loop   "Seamless loop"         "1,20,40"   --loop-frames 61 --turns 1 ${LOOP_FRAMES[@]+"${LOOP_FRAMES[@]}"}
(( PREVIEW )) && { mkdir -p "$OUT/preview"; for n in 1 2 3 4 5; do for f in "$OUT"/act$n/*.png; do cp "$f" "$OUT/preview/act$n-$(basename "$f")"; done; done; echo "stills in $OUT/preview"; exit 0; }

# Act 5 is a 60-frame loop played twice: frames 61-120 repeat frames 1-60.
for i in $(seq 1 60); do cp "$OUT/act5/$(printf %04d "$i").png" "$OUT/act5/$(printf %04d $((i + 60))).png"; done

# Each act becomes a clip with a dip to the stage colour at both ends, then the clips are joined with stream copy.
: > "$OUT/list.txt"
for n in 1 2 3 4 5; do
  ffmpeg -v error -y -framerate 30 -i "$OUT/act$n/%04d.png" -frames:v 120 \
    -vf "fade=t=in:st=0:d=0.2:color=0x1a1d29,fade=t=out:st=3.8:d=0.2:color=0x1a1d29,format=yuv420p" \
    -c:v libx264 -preset slow -crf 14 -r 30 "$OUT/act$n.mp4"
  echo "file 'act$n.mp4'" >> "$OUT/list.txt"
done
ffmpeg -v error -y -f concat -safe 0 -i "$OUT/list.txt" -c copy "$OUT/joined.mp4"

bash "$SKILL/scripts/sound_bed.sh" "$OUT/bed.wav" --seconds 20 --bpm 72 --hits 1.4 --ticks 0.2,4.2,8.2,12.2,16.2
bash "$SKILL/scripts/finish.sh" --in "$OUT/joined.mp4" --out "$OUT/final.mp4" --seconds 20 --audio "$OUT/bed.wav"
bash "$SKILL/scripts/check_delivery.sh" "$OUT/final.mp4" --seconds 20 --joins 4,8,12,16
