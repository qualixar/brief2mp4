#!/usr/bin/env bash
# Install the brief2mp4 skill for Claude Code and Codex.
#
#   bash install.sh               # both
#   bash install.sh --claude      # Claude Code only
#   bash install.sh --codex       # Codex only
#   bash install.sh --uninstall   # remove from both
#   bash install.sh --uninstall --uninstall-3d   # also remove the 3D pack folder
#   bash install.sh --with-3d     # also install the optional 3D pack (core components)
#   bash install.sh --with-3d=core,cad   # pick 3D components: core, cad, blender
#   Windows PowerShell: use install.ps1 instead.
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

DO_CLAUDE=1 DO_CODEX=1 UNINSTALL=0 UNINSTALL_3D=0 WITH_3D=""
for arg in "$@"; do
  case "$arg" in
    --claude) DO_CODEX=0 ;;
    --codex) DO_CLAUDE=0 ;;
    --uninstall) UNINSTALL=1 ;;
    --uninstall-3d) UNINSTALL_3D=1 ;;
    --with-3d) WITH_3D="core" ;;
    --with-3d=*) WITH_3D="${arg#--with-3d=}" ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
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
  if [[ "$UNINSTALL_3D" == 1 ]]; then bash "$SRC/3d/install_3d.sh" --uninstall
  else echo "  The optional 3D pack (if installed) stays in ${B2M3D_HOME:-$HOME/.brief2mp4/3d}; add --uninstall-3d to remove it."; fi
  exit 0
fi

echo "Installing $NAME $VERSION"
[[ "$DO_CLAUDE" == 1 ]] && install_to "$CLAUDE_DIR" "Claude Code"
[[ "$DO_CODEX" == 1 ]] && install_to "$CODEX_DIR" "Codex"

if [[ -n "$WITH_3D" ]]; then
  echo
  echo "Installing the 3D pack (components: $WITH_3D)"
  bash "$SRC/3d/install_3d.sh" --components "$WITH_3D"
fi

echo
bash "$SRC/scripts/doctor.sh" || true

echo
echo "Done. Start a new Claude Code or Codex session, then try:"
echo "  Use the $NAME skill to make the video in this brief: <paste a brief from examples/>"
