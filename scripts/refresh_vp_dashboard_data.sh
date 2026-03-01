#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/xizuo/Cap"
SCRIPT="$ROOT/scripts/build_vp_dashboard_data.py"

if [[ $# -ge 1 ]]; then
  SRC="$1"
  python3 "$SCRIPT" --source "$SRC"
else
  python3 "$SCRIPT"
fi

echo
echo "Done. Output directory:"
echo "  $ROOT/output/tableau_ready"

