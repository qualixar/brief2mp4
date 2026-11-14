#!/usr/bin/env bash
# finish.sh: turn a rough render (MP4/MOV or a folder of PNG frames) into a
# delivery-ready MP4: exact size, frame rate, duration, H.264 + AAC, loudness.
#
#   finish.sh --in render.mp4 --out final.mp4 --seconds 12
#   finish.sh --in frames/ --out final.mp4 --seconds 8 --audio bed.wav
#
# Options
#   --in PATH        video file, or a folder of numbered PNGs (0001.png ...)
#   --out PATH       output MP4 (default final.mp4)
#   --seconds N      exact duration of the result (required)
#   --fps N          frame rate (default 30)
#   --size WxH       frame size (default 1920x1080); the picture is fitted, never stretched
#   --audio PATH     soundtrack to lay under the picture (replaces any audio in --in)
#   --keep-audio     keep the audio already inside --in
#   --lufs N         integrated loudness target (default -14)
#   --crf N          x264 quality, lower is better (default 18)
set -euo pipefail

IN="" OUT="final.mp4" SECONDS_="" FPS=30 SIZE="1920x1080" AUDIO="" KEEP=0 LUFS=-14 CRF=18
while [[ $# -gt 0 ]]; do
  case "$1" in
    --in) IN="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --seconds) SECONDS_="$2"; shift 2 ;;
    --fps) FPS="$2"; shift 2 ;;
    --size) SIZE="$2"; shift 2 ;;
    --audio) AUDIO="$2"; shift 2 ;;
    --keep-audio) KEEP=1; shift ;;
    --lufs) LUFS="$2"; shift 2 ;;
    --crf) CRF="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "finish.sh: unknown option $1" >&2; exit 2 ;;
  esac
done

[[ -n "$IN" && -n "$SECONDS_" ]] || { echo "finish.sh: --in and --seconds are required" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "finish.sh: ffmpeg not found" >&2; exit 2; }
W="${SIZE%x*}" H="${SIZE#*x}"

# Picture input: a frame folder or a video file.
if [[ -d "$IN" ]]; then
  FIRST=""
  for f in "$IN"/*.png; do
    name="$(basename "$f")"
    if [[ "$name" =~ ^[0-9]+\.png$ ]] && { [[ -z "$FIRST" ]] || [[ "$name" < "$FIRST" ]]; }; then FIRST="$name"; fi
  done
  [[ -n "$FIRST" ]] || { echo "finish.sh: no numbered PNGs in $IN" >&2; exit 2; }
  DIGITS="${#FIRST}"; DIGITS=$((DIGITS - 4))
  START="$((10#${FIRST%.png}))"
  VIN=(-framerate "$FPS" -start_number "$START" -i "$IN/%0${DIGITS}d.png")
else
  [[ -f "$IN" ]] || { echo "finish.sh: $IN not found" >&2; exit 2; }
  VIN=(-i "$IN")
fi

# Fit inside the frame, pad the rest, hold the last frame if the render is short.
VF="scale=${W}:${H}:force_original_aspect_ratio=decrease:flags=lanczos,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,fps=${FPS},tpad=stop_mode=clone:stop_duration=${SECONDS_},format=yuv420p"
AF="loudnorm=I=${LUFS}:TP=-1.5:LRA=11,aresample=48000,apad,atrim=0:${SECONDS_},afade=t=out:st=$(awk "BEGIN{print ${SECONDS_}-0.4}"):d=0.4"

if [[ -n "$AUDIO" ]]; then
  ffmpeg -v error -y "${VIN[@]}" -i "$AUDIO" -map 0:v:0 -map 1:a:0 -vf "$VF" -af "$AF" \
    -t "$SECONDS_" -c:v libx264 -preset slow -crf "$CRF" -profile:v high -r "$FPS" \
    -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart "$OUT"
elif [[ "$KEEP" == 1 ]]; then
  ffmpeg -v error -y "${VIN[@]}" -map 0:v:0 -map 0:a:0 -vf "$VF" -af "$AF" \
    -t "$SECONDS_" -c:v libx264 -preset slow -crf "$CRF" -profile:v high -r "$FPS" \
    -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart "$OUT"
else
  # No soundtrack: add a silent stereo track so every player and platform accepts the file.
  ffmpeg -v error -y "${VIN[@]}" -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -map 0:v:0 -map 1:a:0 -vf "$VF" -t "$SECONDS_" \
    -c:v libx264 -preset slow -crf "$CRF" -profile:v high -r "$FPS" \
    -c:a aac -b:a 128k -ar 48000 -ac 2 -movflags +faststart "$OUT"
fi
echo "finish.sh: wrote $OUT (${W}x${H}, ${FPS} fps, ${SECONDS_} s)"
