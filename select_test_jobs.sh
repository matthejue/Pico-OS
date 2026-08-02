#!/usr/bin/env bash

if [[ -n "${TEST_JOBS:-}" ]]; then
  if [[ ! "$TEST_JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "TEST_JOBS must be a positive integer." >&2
    exit 2
  fi
  echo "$TEST_JOBS"
  exit 0
fi

if [[ ! -t 0 ]]; then
  echo 2
  exit 0
fi

max_test_jobs="$(nproc)"
read -r -p "Run system tests on all ${max_test_jobs} CPU cores? [y/N] " use_all_cores
if [[ "$use_all_cores" =~ ^[Yy]$ ]]; then
  echo "$max_test_jobs"
  exit 0
fi

while true; do
  read -r -p "Number of CPU cores to use [2]: " test_jobs
  test_jobs="${test_jobs:-2}"
  if [[ "$test_jobs" =~ ^[1-9][0-9]*$ ]] && ((test_jobs <= max_test_jobs)); then
    echo "$test_jobs"
    exit 0
  fi
  echo "Enter a number from 1 to ${max_test_jobs}." >&2
done
