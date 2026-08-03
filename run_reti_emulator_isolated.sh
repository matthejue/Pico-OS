#!/usr/bin/env bash

peripherals_dir="$(mktemp -d /tmp/reti_emulator.XXXXXX)" || exit 1

cleanup() {
  rm -r -- "$peripherals_dir"
}
trap cleanup EXIT

reti_emulator -f "$peripherals_dir" "$@"
