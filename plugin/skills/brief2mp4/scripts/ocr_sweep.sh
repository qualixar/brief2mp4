#!/usr/bin/env bash
# ocr_sweep.sh: read the frames of a FINISHED video and fail on placeholder text or leaked file paths.
#
#   ocr_sweep.sh final.mp4
#   ocr_sweep.sh final.mp4 --fps 2 --extra 'Acme|v[0-9]+\.[0-9]+\.[0-9]+'
#   ocr_sweep.sh --scan-text notes.txt        # check a text file with the same patterns (no video, no OCR)
#
# It reads one frame per second (--fps) plus every scene change, runs OCR on each, and looks for:
#   TODO, TBD, FIXME, "placeholder", "lorem ipsum", "not recorded", {{ }} template tokens, [INSERT ...] style
#   tokens, and file paths (/Users/..., /home/..., C:\ or C:/Users).
# --extra adds your own pattern (an extended regular expression, case-insensitive): names, version
# strings, anything that must never be on screen.
#
# Needs tesseract. Without it the script prints the install command and exits 0 with a SKIP line, so a
# missing optional tool never fails a delivery:
#   macOS: brew install tesseract    Debian/Ubuntu: sudo apt-get install tesseract-ocr
#   Windows: winget install -e --id UB-Mannheim.TesseractOCR
#
# OCR misreads thin, wide-spaced display type, so a hit is a reason to LOOK at the frame (it is kept next
# to the list with --keep DIR), not proof. A miss is not proof either: view the frames yourself.
# Exit 1 when any pattern hits, 0 otherwise.
set -uo pipefail

FPS=1 EXTRA="" KEEP="" MAX_FRAMES=600 VIDEO="" SCAN_TEXT=""
TESS="${TESSERACT:-tesseract}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fps) FPS="$2"; shift 2 ;;
    --extra) EXTRA="$2"; shift 2 ;;
    --keep) KEEP="$2"; shift 2 ;;
    --max-frames) MAX_FRAMES="$2"; shift 2 ;;
    --scan-text) SCAN_TEXT="$2"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    -*) echo "ocr_sweep.sh: unknown option $1" >&2; exit 2 ;;
    *) VIDEO="$1"; shift ;;
  esac
done

# A word boundary that grep -E understands on macOS, Linux and Git Bash alike.
B='(^|[^A-Za-z0-9_])'
E='([^A-Za-z0-9_]|$)'
PATTERN="${B}(TODO|TBD|FIXME)${E}|lorem ipsum|${B}lorem${E}|placeholder|not recorded"
PATTERN+='|\{\{|\}\}|\[(INSERT|TODO|TBD|PLACEHOLDER)[^]]*\]'
PATTERN+='|/Users/|/home/[a-z]|[A-Za-z]:\\|[A-Za-z]:/Users'
[[ -n "$EXTRA" ]] && PATTERN+="|$EXTRA"

HITS=0
# scan_text LABEL FILE: print one FAIL line per matching string, count them.
scan_text() {
  local label="$1" file="$2" m
  while IFS= read -r m; do
    [[ -z "$m" ]] && continue
    echo "FAIL  placeholder or leak at $label: \"$m\""
    HITS=$((HITS + 1))
  done < <(grep -o -i -E "$PATTERN" "$file" 2>/dev/null | sed 's#^[[:space:].,;:!?"()]*##;s#[[:space:].,;:!?"()]*$##' | sort -u)
}

if [[ -n "$SCAN_TEXT" ]]; then
  [[ -f "$SCAN_TEXT" ]] || { echo "ocr_sweep.sh: no such file: $SCAN_TEXT" >&2; exit 2; }
  scan_text "$SCAN_TEXT" "$SCAN_TEXT"
  [[ "$HITS" == 0 ]] && echo "PASS  no placeholder text or leaked paths in $SCAN_TEXT"
  [[ "$HITS" == 0 ]]; exit $?
fi

[[ -f "$VIDEO" ]] || { echo "usage: ocr_sweep.sh FILE.mp4 [--fps N] [--extra REGEX] [--keep DIR]  |  --scan-text FILE" >&2; exit 2; }
if ! command -v "$TESS" >/dev/null 2>&1; then
  echo "SKIP  ocr_sweep: tesseract is not installed, so the final file was not read for placeholder text."
  echo "      Install it: macOS: brew install tesseract | Debian/Ubuntu: sudo apt-get install tesseract-ocr | Windows: winget install -e --id UB-Mannheim.TesseractOCR"
  echo "      Then rerun. Until then, look at the frames yourself (contact_sheet.sh)."
  exit 0
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# One frame per second, then every scene change (a frame just after a cut shows the new scene's text).
ffmpeg -nostats -v error -i "$VIDEO" -an -vf "fps=$FPS" -frames:v "$MAX_FRAMES" "$WORK/t_%05d.png"
ffmpeg -nostats -v info -i "$VIDEO" -an -vf "select=gt(scene\,0.3),showinfo" -fps_mode vfr -frames:v 200 "$WORK/s_%05d.png" 2> "$WORK/scene.log" \
  || ffmpeg -nostats -v error -i "$VIDEO" -an -vf "select=gt(scene\,0.3)" -vsync vfr -frames:v 200 "$WORK/s_%05d.png"
grep -o 'pts_time:[0-9.]*' "$WORK/scene.log" 2>/dev/null | cut -d: -f2 > "$WORK/scene_times.txt" || true

COUNT=0
for img in "$WORK"/t_*.png "$WORK"/s_*.png; do
  [[ -f "$img" ]] || continue
  base="$(basename "$img" .png)"; n=$((10#${base#*_}))
  if [[ "$base" == t_* ]]; then
    label="$(awk -v n="$n" -v f="$FPS" 'BEGIN{printf "%.1fs", (n-1)/f}')"
  else
    label="$(sed -n "${n}p" "$WORK/scene_times.txt" | awk '{printf "%.1fs (scene change)", $1}')"
  fi
  "$TESS" "$img" "$WORK/ocr" --psm 11 >/dev/null 2>&1 || true
  COUNT=$((COUNT + 1))
  before=$HITS
  scan_text "$label" "$WORK/ocr.txt"
  if [[ -n "$KEEP" && "$HITS" -gt "$before" ]]; then mkdir -p "$KEEP"; cp "$img" "$KEEP/$base.png"; fi
done

echo "----"
if [[ "$HITS" == 0 ]]; then
  echo "PASS  no placeholder text or leaked paths in $COUNT frame(s) of $VIDEO"
else
  echo "FAIL  $HITS hit(s) in $COUNT frame(s) of $VIDEO: open each frame and confirm${KEEP:+ (kept in $KEEP)}"
  exit 1
fi
