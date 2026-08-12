#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runtime_dir=$script_dir
if [[ -f "$script_dir/binary/boot/bootloader.reti" ]]; then
  runtime_dir="$script_dir/binary"
fi
emulator_path=""

usage() {
  cat <<'EOF'
Usage: ./start-picoos.sh [--reti-emulator PATH] [-- EMULATOR_ARGS...]
EOF
}

while (($#)); do
  case "$1" in
    --reti-emulator)
      [[ $# -ge 2 ]] || { echo "--reti-emulator requires a path" >&2; exit 2; }
      emulator_path=$2
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

resolve_emulator() {
  if [[ -n "$emulator_path" ]]; then
    [[ -x "$emulator_path" ]] || { echo "RETI Emulator is not executable: $emulator_path" >&2; exit 1; }
    emulator_path=$(cd -- "$(dirname -- "$emulator_path")" && printf '%s/%s\n' "$PWD" "$(basename -- "$emulator_path")")
  elif [[ -x "$runtime_dir/reti_emulator" ]]; then
    emulator_path="$runtime_dir/reti_emulator"
  elif [[ -x "$script_dir/reti_emulator" ]]; then
    emulator_path="$script_dir/reti_emulator"
  elif command -v reti_emulator >/dev/null 2>&1; then
    emulator_path=$(command -v reti_emulator)
  else
    echo "RETI Emulator not found in the release directory or PATH" >&2
    echo "Run ./download-tools.sh to download the latest release" >&2
    echo "Use --reti-emulator PATH to select it explicitly" >&2
    exit 1
  fi
}

resolve_emulator
cd "$runtime_dir"
exec "$emulator_path" \
  -n 4 \
  -e ./boot/bootloader.reti \
  -d -c -O \
  -r 262144 \
  -S kernel/kernel.sections \
  -D kernel/kernel.debuginfo \
  "$@"
