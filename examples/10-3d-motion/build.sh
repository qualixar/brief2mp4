#!/usr/bin/env bash
# build.sh: brief 10. One studio, five Blender motion recipes, cut to music on the bar lines.
#
#   bash build.sh                 # full film: build/final.mp4 (about 10-20 minutes on a laptop; the acts render in parallel)
#   bash build.sh --preview       # three stills per act at 960x540 in build/preview, nothing else
#   ACTS="4" bash build.sh        # re-render act 4 only, keep the other acts' frames, then join and check again
#
# Needs Blender 4.2+, ffmpeg, python3 and a network connection the first time (the music comes from Openverse).
# Set B2M3D_BLENDER if Blender is not on the PATH; B2M_SKILL points at the skill folder (default: the one here).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="${B2M_SKILL:-$HERE/../../plugin/skills/brief2mp4}"
REC="$SKILL/3d/templates/recipes"
BLENDER="${B2M3D_BLENDER:-$(command -v blender || echo /Applications/Blender.app/Contents/MacOS/Blender)}"
[[ -x "$BLENDER" ]] || { echo "build.sh: Blender not found; set B2M3D_BLENDER" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "build.sh: ffmpeg not found" >&2; exit 2; }
OUT="$HERE/build"
PREVIEW=0; [[ "${1:-}" == "--preview" ]] && PREVIEW=1

# One world for every act: the same seamless studio, palette, lights and caption style.
PALETTE=(--bg "#c4beb6" --floor "#cdc7bf" --subject "#e0632f" --accent "#3358c8" --ink "#24212a")
LOOK=(--look studio --caption-fade 9)
SIZE=(--width 1920 --height 1080 --samples 64 --caption-px 38)
(( PREVIEW )) && SIZE=(--width 960 --height 540 --samples 16 --caption-px 19)

# The cut. The music runs at 95 BPM, so a bar is 2.524 s (75.7 frames). The acts join on every second bar line:
# frames 114, 265, 416 and 568, and the film ends at frame 720 (24.0 s). Each act renders HALF frames past each of
# its joins, so neighbours overlap by 12 frames and dissolve into each other, centred on the bar line.
JOINS=(114 265 416 568); END=720; HALF=6
MUSIC_ID="2ede71c8-18be-4a17-ab28-aa3bb1dac503"   # CC0, see ATTRIBUTION.md
MUSIC_IN=8.89                                       # seconds into the track at frame 0: its first big downbeat lands on join 1
mkdir -p "$OUT"

act_frames() {   # frames act N renders: from HALF before its first join to HALF after its last
  local n="$1" a=0 b="$END"
  (( n > 1 )) && a=$(( JOINS[n - 2] - HALF ))
  (( n < 5 )) && b=$(( JOINS[n - 1] + HALF ))
  echo $(( b - a ))
}

# act N recipe caption preview-frames recipe-options... (runs in the background; the PID goes to PIDS)
PIDS=()
act() {
  local n="$1" recipe="$2" caption="$3" preview="$4"; shift 4
  local dir="$OUT/act$n" count; count="$(act_frames "$n")"
  [[ " ${ACTS:-1 2 3 4 5} " == *" $n "* ]] || return 0      # not asked for: keep its frames from the last build
  rm -rf "$dir"
  local frames=(--render-frames "1-$count"); (( PREVIEW )) && frames=(--render-frames "$preview")
  local first=$(( n == 1 ? 8 : 2 * HALF + 1 )) last=$(( n == 5 ? count - 30 : count - 2 * HALF - 1 ))
  "$BLENDER" -b --factory-startup -P "$REC/b2m_$recipe.py" -- "${PALETTE[@]}" "${LOOK[@]}" "${SIZE[@]}" \
    --caption "$caption" --caption-frames "$first-$last" --out "$dir" "${frames[@]}" --json "$OUT/act$n.json" "$@" \
    > "$OUT/act$n.log" 2>&1 &
  PIDS+=("$!")
}

act 1 cloth  "Cloth drop"            "1,20,100" --frames "$(act_frames 1)" --object sphere --cloth-res 56 --quality 10 \
  --self-collision --smooth-levels 1 --thickness 0.012 --sheen 0.4 --drop-height 1.6 --orbit 4
act 2 rigid  "Hinged chain"          "1,40,90"  --frames "$(act_frames 2)" --links 7 --link-length 0.45 --release-angle 85 \
  --damping 0.01 --anchor-height 3.5 --orbit 3
act 3 fold   "Folding"               "1,55,150" --folds 3 --fold-frames 34 --pause 9 --back "#3358c8" --thickness 0.004 --orbit 4
act 4 walk   "Walking, feet planted" "1,60,120" --frames "$(act_frames 4)" --speed 0.95 --cycle-frames 34 --thigh 0.47 \
  --shin 0.47 --hip-height 0.9 --bob 0.024 --step-height 0.08
act 5 loop   "Seamless loop"         "1,38,76"  --loop-frames 77 --turns 1 --glow 0   # one turn per bar; frames past 77 keep looping
FAILED=0
for i in "${!PIDS[@]}"; do
  wait "${PIDS[$i]}" || { echo "act $((i + 1)) failed:" >&2; tail -20 "$OUT/act$((i + 1)).log" >&2; FAILED=1; }
done
(( FAILED )) && exit 1
for n in 1 2 3 4 5; do   # each recipe's own proof, from its result line
  echo "act $n: $(grep -o '"max_slide_per_frame": [0-9.e-]*\|"centre_z": [0-9.]*\|"frame_margin": [0-9.e-]*\|"final_width": [0-9.]*\|"seam_slope_gap": [0-9.e-]*' "$OUT/act$n.json" | head -1)"
done
(( PREVIEW )) && { mkdir -p "$OUT/preview"; for n in 1 2 3 4 5; do for f in "$OUT"/act$n/*.png; do cp "$f" "$OUT/preview/act$n-$(basename "$f")"; done; done; echo "stills in $OUT/preview"; exit 0; }

# Picture: chain the five acts with 0.4 s dissolves centred on the joins, then ease the last 0.6 s into the backdrop.
INPUTS=(); for n in 1 2 3 4 5; do INPUTS+=(-framerate 30 -i "$OUT/act$n/%04d.png"); done
GRAPH="[0]settb=AVTB,fps=30[v0]"
for n in 1 2 3 4; do
  GRAPH+=";[$n]settb=AVTB,fps=30[a$n];[v$((n - 1))][a$n]xfade=transition=fade:duration=0.4:offset=$(awk -v j="${JOINS[n - 1]}" -v h=$HALF 'BEGIN{printf "%.4f", (j - h) / 30}')[v$n]"
done
GRAPH+=";[v4]fade=t=out:st=23.4:d=0.6:color=0xe6dfd6,format=yuv420p[out]"
ffmpeg -v error -y "${INPUTS[@]}" -filter_complex "$GRAPH" -map "[out]" -frames:v "$END" -c:v libx264 -preset slow -crf 14 -r 30 "$OUT/joined.mp4"

# Sound: the music from Openverse (CC0), cut so its bar lines fall on the joins, faded at both ends.
if ! ls "$OUT"/audio/*.mp3 >/dev/null 2>&1; then
  python3 "$SKILL/scripts/fetch_music.py" download --id "$MUSIC_ID" --out-dir "$OUT/audio"
fi
TRACK="$(ls "$OUT"/audio/*.mp3 | head -1)"
ffmpeg -v error -y -ss "$MUSIC_IN" -t 24 -i "$TRACK" -af "afade=t=in:d=0.3,afade=t=out:st=22.2:d=1.8" -ar 48000 -ac 2 "$OUT/music.wav"
bash "$SKILL/scripts/finish.sh" --in "$OUT/joined.mp4" --out "$OUT/final.mp4" --seconds 24 --audio "$OUT/music.wav" --crf 16
JOIN_S="$(for j in "${JOINS[@]}"; do awk -v j="$j" 'BEGIN{printf "%.3f,", j / 30}'; done)"
bash "$SKILL/scripts/check_delivery.sh" "$OUT/final.mp4" --seconds 24 --joins "${JOIN_S%,}" --strict-flicker
