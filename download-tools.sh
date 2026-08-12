#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runtime_dir=$script_dir
if [[ -f "$script_dir/binary/boot/bootloader.reti" ]]; then
  runtime_dir="$script_dir/binary"
fi

system=$(uname -s)
machine=$(uname -m)

case "$machine" in
  x86_64|amd64) architecture=x86_64 ;;
  arm64|aarch64) architecture=arm64 ;;
  *)
    echo "No PicoOS tool binaries are released for architecture: $machine" >&2
    exit 1
    ;;
esac

case "$system" in
  Darwin)
    platform=macos
    ;;
  Linux)
    if [[ -n "${ANDROID_ROOT:-}" ]] || [[ "$(uname -o 2>/dev/null || true)" == Android ]]; then
      platform=android
    else
      platform=linux
    fi
    ;;
  *)
    echo "Use download-tools.ps1 on Windows; unsupported operating system: $system" >&2
    exit 1
    ;;
esac

case "$platform-$architecture" in
  linux-x86_64|macos-x86_64|macos-arm64|android-arm64) ;;
  *)
    echo "No PicoOS tool binaries are released for $platform-$architecture" >&2
    exit 1
    ;;
esac

if command -v curl >/dev/null 2>&1; then
  download() {
    curl --fail --location --retry 3 --output "$2" "$1"
  }
elif command -v wget >/dev/null 2>&1; then
  download() {
    wget --output-document="$2" "$1"
  }
else
  echo "Downloading the PicoOS tools requires curl or wget" >&2
  exit 1
fi

temporary_dir=$(mktemp -d)
trap 'rm -rf "$temporary_dir"' EXIT

install_package() {
  local repository=$1
  local asset=$2
  local executable_name=$3
  local archive="$temporary_dir/$asset"
  local extracted="$temporary_dir/${asset%.tar.gz}"
  local executable
  local package_root
  local file
  local relative_path
  local destination

  echo "Downloading latest $repository release..."
  download "https://github.com/matthejue/$repository/releases/latest/download/$asset" "$archive"
  mkdir -p "$extracted"
  tar -xzf "$archive" -C "$extracted"

  executable=$(find "$extracted" -type f -name "$executable_name" -print -quit)
  if [[ -z "$executable" ]]; then
    echo "$asset does not contain $executable_name" >&2
    exit 1
  fi
  package_root=$(dirname -- "$executable")

  while IFS= read -r -d '' file; do
    relative_path=${file#"$package_root"/}
    [[ "$relative_path" == README.md ]] && continue
    destination="$runtime_dir/$relative_path"
    mkdir -p "$(dirname -- "$destination")"
    cp -pP "$file" "$destination"
  done < <(find "$package_root" \( -type f -o -type l \) -print0)
}

install_package \
  RETI-Emulator \
  "reti-emulator-$platform-$architecture.tar.gz" \
  reti_emulator
install_package \
  PicoC-Compiler \
  "picoc-compiler-$platform-$architecture.tar.gz" \
  picoc_compiler

chmod 755 "$runtime_dir/reti_emulator" "$runtime_dir/picoc_compiler"
echo "Installed the latest RETI Emulator and PicoC Compiler in $runtime_dir"
