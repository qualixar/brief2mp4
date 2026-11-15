#!/usr/bin/env bash
# Install the brief2mp4 skill for Claude Code and Codex.
#
#   bash install.sh               # both
#   bash install.sh --claude      # Claude Code only
#   bash install.sh --codex       # Codex only
#   bash install.sh --uninstall   # remove from both
#
# Claude Code reads skills from ~/.claude/skills (or $CLAUDE_CONFIG_DIR/skills).
# Codex reads skills from ~/.codex/skills (or $CODEX_HOME/skills).
set -euo pipefail

NAME="brief2mp4"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/plugin/skills/$NAME"
VERSION="$(cat "$HERE/VERSION" 2>/dev/null || echo dev)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}/skills"

DO_CLAUDE=1 DO_CODEX=1 UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --claude) DO_CODEX=0 ;;
    --codex) DO_CLAUDE=0 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "install.sh: unknown option $arg" >&2; exit 2 ;;
  esac
done

[[ -f "$SRC/SKILL.md" ]] || { echo "install.sh: cannot find $SRC/SKILL.md (run it from the repo folder)" >&2; exit 1; }

remove_ours() {
  # Only ever removes a folder this installer created (it carries our marker file).
  local dest="$1"
  [[ -n "$dest" && "$(basename "$dest")" == "$NAME" ]] || return 1
  if [[ -f "$dest/.installed-by-$NAME" ]]; then
    rm -r "$dest"
    return 0
  fi
  return 1
}

install_to() {
  local base="$1" label="$2" dest="$1/$NAME"
  mkdir -p "$base"
  if [[ -e "$dest" ]]; then
    if ! remove_ours "$dest"; then
      local backup
      backup="$dest.backup-$(date +%Y%m%d-%H%M%S)"
      mv "$dest" "$backup"
      echo "  kept your existing $NAME folder at $backup"
    fi
  fi
  cp -R "$SRC" "$dest"
  chmod +x "$dest"/scripts/*.sh
  echo "$VERSION" > "$dest/.installed-by-$NAME"
  echo "  $label: installed to $dest"
}

uninstall_from() {
  local dest="$1/$NAME" label="$2"
  if [[ -e "$dest" ]]; then
    if remove_ours "$dest"; then echo "  $label: removed $dest"
    else echo "  $label: $dest was not installed by this script; left it alone"; fi
  else
    echo "  $label: nothing to remove"
  fi
}

if [[ "$UNINSTALL" == 1 ]]; then
  echo "Removing $NAME"
  [[ "$DO_CLAUDE" == 1 ]] && uninstall_from "$CLAUDE_DIR" "Claude Code"
  [[ "$DO_CODEX" == 1 ]] && uninstall_from "$CODEX_DIR" "Codex"
  exit 0
fi

echo "Installing $NAME $VERSION"
[[ "$DO_CLAUDE" == 1 ]] && install_to "$CLAUDE_DIR" "Claude Code"
[[ "$DO_CODEX" == 1 ]] && install_to "$CODEX_DIR" "Codex"

echo
echo "Tools the skill uses:"
check() {
  local cmd="$1" why="$2" fix="$3"
  if command -v "$cmd" >/dev/null 2>&1; then echo "  ok       $cmd ($why)"
  else echo "  missing  $cmd ($why). Install: $fix"; fi
}
check node "HyperFrames and Three.js, version 22 or newer" "https://nodejs.org or: brew install node"
check ffmpeg "finishing and checks, needed for every video" "brew install ffmpeg  (Linux: apt install ffmpeg)"
if command -v blender >/dev/null 2>&1 || [[ -x /Applications/Blender.app/Contents/MacOS/Blender ]]; then
  echo "  ok       blender (only for Blender briefs)"
else
  echo "  missing  blender (only for Blender briefs). Install: https://www.blender.org/download or: brew install --cask blender"
fi
if command -v node >/dev/null 2>&1; then
  major="$(node -v | sed 's/^v//; s/\..*//')"
  [[ "$major" -ge 22 ]] 2>/dev/null || echo "  note     node $(node -v) is older than 22; HyperFrames needs 22 or newer"
fi

echo
echo "Done. Start a new Claude Code or Codex session, then try:"
echo "  Use the $NAME skill to make the video in this brief: <paste a brief from examples/>"
