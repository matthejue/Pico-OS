#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runtime_dir=$script_dir
if [[ -f "$script_dir/binary/boot/bootloader.reti" ]]; then
  runtime_dir="$script_dir/binary"
fi
emulator_path=""
dma_option=()
dma_specified=false
notui=false
emulator_options_file="$runtime_dir/config/emulator_options.txt"
emulator_options=()

usage() {
  cat <<'EOF'
Usage: ./start-picoos.sh [OPTIONS] [-- EMULATOR_ARGS...]

Options:
  --reti-emulator PATH  Use a custom RETI Emulator executable
  --dma, -M             Enable DMA loading
  --notui, -N           Start without the Debug TUI
  --help, -h            Show this help page
  --                    Pass all following arguments to RETI Emulator
EOF
}

download_tools() {
  local download_script="$script_dir/download-tools.sh"

  [[ -f "$download_script" ]] || { echo "Download script not found: $download_script" >&2; exit 1; }
  if [[ ! -x "$download_script" ]]; then
    chmod +x "$download_script"
  fi
  "$download_script" "$@"
}

prompt_download() {
  local tool=$1
  local tool_name=$2
  local answer

  printf '%s was not found. Download the latest version? [y/N] ' "$tool_name" >&2
  IFS= read -r answer || answer=""
  if [[ ! "$answer" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo "$tool_name was not downloaded" >&2
    return 1
  fi
  download_tools "$tool"
}

while (($#)); do
  case "$1" in
    --reti-emulator)
      [[ $# -ge 2 ]] || { echo "--reti-emulator requires a path" >&2; exit 2; }
      emulator_path=$2
      shift 2
      ;;
    --dma|-M)
      dma_option=(--dma)
      dma_specified=true
      shift
      ;;
    --notui|-N)
      notui=true
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
    return 1
  fi
}

compiler_available() {
  [[ -x "$runtime_dir/picoc_compiler" ]] ||
    [[ -x "$script_dir/picoc_compiler" ]] ||
    command -v picoc_compiler >/dev/null 2>&1
}

if ! resolve_emulator; then
  prompt_download reti_emulator "RETI Emulator" || true
  resolve_emulator || { echo "RETI Emulator was not found" >&2; emulator_missing=true; }
fi

if ! compiler_available; then
  prompt_download picoc_compiler "PicoC Compiler" || true
  compiler_available || echo "PicoC Compiler was not found" >&2
fi

if [[ "${emulator_missing:-false}" == true ]]; then
  exit 1
fi

if ! "$dma_specified"; then
  printf 'Enable DMA? [y/N] ' >&2
  IFS= read -r dma_answer || dma_answer=""
  if [[ "$dma_answer" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    dma_option=(--dma)
  fi
fi

[[ -f "$emulator_options_file" ]] || { echo "Emulator options file not found: $emulator_options_file" >&2; exit 1; }
IFS=' ' read -r -a emulator_options < "$emulator_options_file"
if "$notui"; then
  filtered_emulator_options=()
  for option in "${emulator_options[@]}"; do
    [[ "$option" == -d ]] || filtered_emulator_options+=("$option")
  done
  emulator_options=("${filtered_emulator_options[@]}")
fi

cd "$runtime_dir"
exec "$emulator_path" \
  "${emulator_options[@]}" \
  "${dma_option[@]}" \
  "$@"
