#!/usr/bin/env bash
# Render docs/diagrams/*.html to assets/*.png at 2x with headless Chrome.
#   bash docs/diagrams/render.sh            # all diagrams
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/../../assets"
CHROME="${CHROME:-}"
for c in "$CHROME" "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" "$(command -v google-chrome || true)" "$(command -v chromium || true)"; do
  [[ -n "$c" && -x "$c" ]] && { CHROME="$c"; break; }
done
[[ -x "$CHROME" ]] || { echo "render.sh: set CHROME to a Chrome or Chromium binary" >&2; exit 1; }
for f in "$HERE"/*.html; do
  name="$(basename "$f" .html)"
  w="$(sed -n 's/.*body{width:\([0-9]*\)px;height:\([0-9]*\)px.*/\1/p' "$f")"
  h="$(sed -n 's/.*body{width:\([0-9]*\)px;height:\([0-9]*\)px.*/\2/p' "$f")"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size="${w},${h}" --virtual-time-budget=8000 --screenshot="$OUT/$name.png" "file://$f" >/dev/null 2>&1
  echo "wrote assets/$name.png"
done
