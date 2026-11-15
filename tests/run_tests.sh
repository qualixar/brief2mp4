#!/usr/bin/env bash
# run_tests.sh: run the brief2mp4 tests.
#
#   bash tests/run_tests.sh            # fast tests only (seconds)
#   bash tests/run_tests.sh --slow     # also the renders: example 04 through HyperFrames, Blender, fallback
#   bash tests/run_tests.sh -k hf      # any other argument goes to pytest
#
# The 3D tests run against an installed pack: B2M3D_HOME (default ~/.brief2mp4/3d) with the `core`
# component, plus `dev` for pytest:  bash plugin/skills/brief2mp4/3d/install_3d.sh --components core,dev
# Tests that need an optional piece (CadQuery, Blender, network) skip with a reason.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export B2M3D_HOME="${B2M3D_HOME:-$HOME/.brief2mp4/3d}"
PY="$B2M3D_HOME/venv/bin/python"
[[ -x "$PY" ]] || PY="$B2M3D_HOME/venv/Scripts/python.exe"   # Git Bash on Windows
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || command -v python)"
  echo "run_tests.sh: no pack venv in $B2M3D_HOME; the 3D tests will skip. Install: bash plugin/skills/brief2mp4/3d/install_3d.sh --components core,dev" >&2
fi
"$PY" -c "import pytest" 2>/dev/null || { echo "run_tests.sh: pytest is missing for $PY. Install it: bash plugin/skills/brief2mp4/3d/install_3d.sh --components dev" >&2; exit 1; }

ARGS=(-m "not slow")
PASSTHROUGH=()
for a in "$@"; do
  if [[ "$a" == "--slow" ]]; then ARGS=(); else PASSTHROUGH+=("$a"); fi
done
exec "$PY" -m pytest "$HERE" -p no:cacheprovider -q ${ARGS[@]+"${ARGS[@]}"} ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}
