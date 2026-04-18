#!/usr/bin/env bash

if [[ -n "$1" ]]; then
  paths=(./sys_tests/*$1*.picoc)
else
  paths=(./sys_tests/*.picoc)
fi

for test in "${paths[@]}"; do
  expected=$(sed -n '2p' "$test" | sed -e 's/^\/\/ expected://')
  if [[ "$expected" == '' ]]; then
    echo -n '' > "${test%.picoc}.expected_output"
  else
    echo "$expected" | tr '\n' ' ' > "${test%.picoc}.expected_output"
  fi
done
