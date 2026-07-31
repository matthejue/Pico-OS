#!/usr/bin/env bash

if [[ -n "$1" ]]; then
  paths=(./tests/*$1*.picoc)
else
  paths=(./tests/*.picoc)
fi

for test in "${paths[@]}"; do
  input=$(sed -n '1p' "$test" | sed -e 's/^\/\/ in://')
  echo "$input" | tr '\n' ' ' > "${test%.picoc}.input"

  expected=$(sed -n '2p' "$test" | sed -e 's/^\/\/ expected://')
  if [[ "$expected" == '' ]]; then
    echo -n '' > "${test%.picoc}.expected_output"
  else
    echo "$expected" | tr '\n' ' ' > "${test%.picoc}.expected_output"
  fi
done
