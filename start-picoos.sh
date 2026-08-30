#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runtime_dir=$script_dir
if [[ -f "$script_dir/binary/boot/bootloader.reti" ]]; then
  runtime_dir="$script_dir/binary"
fi
emulator_path=""
dma_option=()

usage() {
  cat <<'EOF'
Usage: ./start-picoos.sh [--reti-emulator PATH] [--dma] [-- EMULATOR_ARGS...]
EOF
}

download_tools() {
  local download_script="$script_dir/download-tools.sh"
  local answer

  printf 'RETI Emulator was not found. Download the latest RETI Emulator and PicoC Compiler? [y/N] ' >&2
  IFS= read -r answer || answer=""
  if [[ ! "$answer" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo "PicoOS tools were not downloaded" >&2
    exit 1
  fi

  [[ -f "$download_script" ]] || { echo "Download script not found: $download_script" >&2; exit 1; }
  if [[ ! -x "$download_script" ]]; then
    chmod +x "$download_script"
  fi
  "$download_script"
}

while (($#)); do
  case "$1" in
    --reti-emulator)
      [[ $# -ge 2 ]] || { echo "--reti-emulator requires a path" >&2; exit 2; }
      emulator_path=$2
      shift 2
      ;;
    --dma)
      dma_option=(--dma)
      shift
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
    download_tools
    if [[ -x "$runtime_dir/reti_emulator" ]]; then
      emulator_path="$runtime_dir/reti_emulator"
    elif [[ -x "$script_dir/reti_emulator" ]]; then
      emulator_path="$script_dir/reti_emulator"
    else
      echo "The downloaded RETI Emulator was not found" >&2
      exit 1
    fi
  fi
}

resolve_emulator
cd "$runtime_dir"
exec "$emulator_path" \
  -n 5 \
  -e ./boot/bootloader.reti \
  -d -c -O \
  -r 262144 \
  -S kernel/kernel.sections \
  -D kernel/kernel.debuginfo \
  "${dma_option[@]}" \
  "$@"
