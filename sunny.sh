#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/kerrb/msync/sunnypilot"
VENV="$BASE_DIR/.venv/bin/activate"

usage() {
  echo "Usage: $0 [-b] {replay|ui|seat} [-- extra args]"
  exit 1
}

BUILD=0
while getopts ":bh" opt; do
  case "$opt" in
    b) BUILD=1 ;;
    h) usage ;;
    \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
  esac
done
shift $((OPTIND - 1))

[[ $# -ge 1 ]] || usage
MODE="$1"
shift || true  # shift off mode; remaining args passed through

cd "$BASE_DIR"
# shellcheck disable=SC1090
source "$VENV"

if (( BUILD )); then
  echo "Building (scons -j$(nproc))..."
  scons -j"$(nproc)"
fi

case "$MODE" in
  replay)
    tools/replay/replay --demo "$@"
    ;;
  ui)
    selfdrive/ui/ui "$@"
    ;;
  seat)
    python sunnypilot_dev_msync/msync_src/seat_control_service.py "$@"
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage
    ;;
esac
