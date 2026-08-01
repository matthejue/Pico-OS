#!/usr/bin/env bash

NOT_PASSED_TESTS_FILE="./opts/not_passed_tests.txt"
RESULT_FILE="./tests/tests.res"
MAX_EMULATOR_DURATION_SECONDS=5

use_not_passed_tests=false

usage() {
  cat <<EOF
Usage:
  $0 [OPTIONS] COLUMNS [TEST_PATTERN] [EXTRA_CPL_ARGS] [EXTRA_EMU_ARGS]

Options:
  --not-passed
      Run only the whitespace-separated test paths listed in:
      ${NOT_PASSED_TESTS_FILE}

      TEST_PATTERN is ignored when this option is active.

  -h, --help
      Show this help message.

Examples:
  $0 120
  $0 120 basic
  $0 120 all
  $0 --not-passed 120

Each emulator invocation is stopped automatically after
${MAX_EMULATOR_DURATION_SECONDS} seconds.

After a completed test run, all tests that failed compilation, failed
emulation, timed out, or produced incorrect output are written as
whitespace-separated paths to:
  ${NOT_PASSED_TESTS_FILE}
EOF
}

cleanup() {
  echo "Termination signal received. Cleaning up..."
  exit 1
}

trap cleanup SIGINT SIGTERM

while [[ $# -gt 0 ]]; do
  case "$1" in
    --not-passed)
      use_not_passed_tests=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 1 ]]; then
  echo "Error: COLUMNS argument is required." >&2
  usage >&2
  exit 2
fi

columns="$1"
test_pattern="${2:-}"
extra_cpl_args="${3:-}"
extra_emu_args="${4:-}"
start_time=$SECONDS

num_tests=0
failing=()
not_passed=()
timed_out=()
paths=()

shopt -s nullglob

if [[ "$use_not_passed_tests" == true ]]; then
  if [[ ! -f "$NOT_PASSED_TESTS_FILE" ]]; then
    echo "Test list file not found: $NOT_PASSED_TESTS_FILE" >&2
    exit 1
  fi

  mapfile -t paths < <(
    tr -s '[:space:]' '\n' < "$NOT_PASSED_TESTS_FILE" |
      sed '/^[[:space:]]*$/d'
  )

  if (( ${#paths[@]} == 0 )); then
    echo "No tests are listed in $NOT_PASSED_TESTS_FILE"
    exit 0
  fi
elif [[ "$test_pattern" == "all" ]]; then
  paths=(./tests/*.picoc)
elif [[ -n "$test_pattern" ]]; then
  paths=(./tests/*"$test_pattern"*.picoc)
else
  paths=(./tests/*.picoc)
fi

if (( ${#paths[@]} == 0 )); then
  echo "No matching tests found." >&2
  exit 1
fi

for test in "${paths[@]}"; do
  if [[ ! -f "$test" ]]; then
    echo "Test file not found: $test" >&2
    exit 1
  fi
done

if [[ "$use_not_passed_tests" == true ]]; then
  # The helper accepts a pattern rather than an array of test paths.
  # Process every selected test using its exact basename.
  for test in "${paths[@]}"; do
    exact_test_pattern="$(basename "${test%.picoc}")"

    if ! ./extract_input_and_expected.sh "$exact_test_pattern"; then
      echo "Failed to extract input and expected output for $test" >&2
      exit 1
    fi
  done
else
  extraction_pattern="$test_pattern"
  if [[ "$test_pattern" == "all" ]]; then
    extraction_pattern=""
  fi

  if ! ./extract_input_and_expected.sh "$extraction_pattern"; then
    echo "Failed to extract input and expected output." >&2
    exit 1
  fi
fi

for test in "${paths[@]}"; do
  ./heading_subheadings.py "heading" "$test" "$columns" "="

  reti_file="${test%.picoc}.reti"
  expected_file="${test%.picoc}.expected_output"
  output_file="${test%.picoc}.output"

  # Prevent artifacts from an earlier run from being reused.
  rm -f "$reti_file" "$output_file"

  # The unquoted expansions intentionally permit multiple options.
  # shellcheck disable=SC2046,SC2086
  python3 ./compile_picoc.py \
    $(cat ./opts/test_cpl_opts.txt) \
    $extra_cpl_args \
    "$test" \
    -o "$reti_file"

  compile_status=$?
  test_passed=true

  if (( compile_status != 0 )); then
    echo "Compilation failed for $test"
    failing+=("$test")
    test_passed=false
  elif [[ ! -f "$reti_file" ]]; then
    echo "Compilation did not produce an output file for $test"
    failing+=("$test")
    test_passed=false
  else
    # Do not use --preserve-status here. Without it, GNU timeout returns
    # status 124 when the configured timeout is reached.
    #
    # --kill-after ensures that an emulator which ignores SIGTERM is
    # forcibly stopped one second later.
    #
    # shellcheck disable=SC2046,SC2086
    timeout \
      --signal=TERM \
      --kill-after=1s \
      "${MAX_EMULATOR_DURATION_SECONDS}s" \
      reti_emulator \
      $(cat ./opts/test_emu_opts.txt) \
      $extra_emu_args \
      "$reti_file"

    emulator_status=$?

    if (( emulator_status == 124 || emulator_status == 137 )); then
      echo "Test could not finish in time."
      echo \
        "Emulator timed out after ${MAX_EMULATOR_DURATION_SECONDS}s for $test"

      timed_out+=("$test")
      test_passed=false
    elif (( emulator_status != 0 )); then
      echo "Emulator failed with exit status $emulator_status for $test"
      test_passed=false
    elif [[ ! -f "$output_file" ]]; then
      echo "Emulator did not produce an output file for $test"
      test_passed=false
    elif [[ ! -f "$expected_file" ]]; then
      echo "Expected-output file not found: $expected_file"
      test_passed=false
    elif ! diff \
      <(sed -e 's/[[:space:]]*$//' "$expected_file") \
      <(sed -e 's/[[:space:]]*$//' "$output_file")
    then
      test_passed=false
    fi
  fi

  if [[ "$test_passed" == false ]]; then
    not_passed+=("$test")
  fi

  ((num_tests++))
done

write_not_passed_tests() {
  if (( ${#not_passed[@]} == 0 )); then
    : > "$NOT_PASSED_TESTS_FILE"
    return
  fi

  printf '%s' "${not_passed[0]}" > "$NOT_PASSED_TESTS_FILE" || return 1

  if (( ${#not_passed[@]} > 1 )); then
    printf ' %s' "${not_passed[@]:1}" >> "$NOT_PASSED_TESTS_FILE" ||
      return 1
  fi

  printf '\n' >> "$NOT_PASSED_TESTS_FILE"
}

if ! write_not_passed_tests; then
  echo "Failed to update $NOT_PASSED_TESTS_FILE" >&2
  exit 1
fi

duration=$((SECONDS - start_time))
summary="$({
  echo "Not failing: $((num_tests - ${#failing[@]})) / $num_tests"
  echo "Failing: ${failing[*]}"
  echo "Passed: $((num_tests - ${#not_passed[@]})) / $num_tests"
  echo "Not passed: ${not_passed[*]}"
  echo "Timed out: ${timed_out[*]}"
  printf 'Runtime: %02d:%02d\n' "$((duration / 60))" "$((duration % 60))"
})"

printf '%s\n' "$summary" | tee -a "$RESULT_FILE"

if [[ -n "${TEST_SUMMARY_FILE:-}" ]]; then
  {
    if [[ -s "$TEST_SUMMARY_FILE" ]]; then
      echo
    fi
    ./heading_subheadings.py \
      subheading "${TEST_SUMMARY_HEADING:-Library tests}" "$columns" "-"
    printf '%s\n' "$summary"
  } >> "$TEST_SUMMARY_FILE"
fi

echo "Updated test list: $NOT_PASSED_TESTS_FILE"

if (( ${#not_passed[@]} != 0 )); then
  exit 1
fi

exit 0
