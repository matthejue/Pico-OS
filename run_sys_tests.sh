#!/usr/bin/env bash

NOT_PASSED_TESTS_FILE="./opts/not_passed_tests.txt"
RESULT_FILE="./tests/tests.res"
use_not_passed_tests=false
direct_compile=false

usage() {
  cat <<EOF
Usage:
  $0 [OPTIONS] COLUMNS [TEST_PATTERN] [EXTRA_CPL_ARGS] [EXTRA_EMU_ARGS]

Options:
  --not-passed
      Run only the whitespace-separated test paths listed in:
      ${NOT_PASSED_TESTS_FILE}

      TEST_PATTERN is ignored when this option is active.

  --direct
      Compile each test and its .picoc dependencies directly into the final
      .reti file. The default compiles reusable .reti_blocks and .st files.

  -h, --help
      Show this help message.

TEST_JOBS controls parallel compilation and emulator jobs and defaults to the
number of available processors. Every emulator uses a separate temporary
peripheral directory.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --not-passed)
      use_not_passed_tests=true
      shift
      ;;
    --direct)
      direct_compile=true
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
paths=()

cleanup() {
  echo "Termination signal received. Cleaning up..."
  exit 1
}
trap cleanup SIGINT SIGTERM

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
elif [[ "$test_pattern" == all ]]; then
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

  input="$(sed -n '1s@^// in:@@p' "$test")"
  expected="$(sed -n '2s@^// expected:@@p' "$test")"
  printf '%s\n' "$input" > "${test%.picoc}.input"
  printf '%s' "$expected" > "${test%.picoc}.expected_output"
done

temporary_root="/tmp/reti_emulator"
mkdir -p "$temporary_root" || exit 1
result_dir="$(mktemp -d -p "$temporary_root")"
cleanup_result_dir() {
  rm -r -- "$result_dir"
}
trap cleanup_result_dir EXIT

if [[ "$direct_compile" == true ]]; then
  test_build_mode=direct
else
  test_build_mode=staged
fi

export TEST_CPL_OPTIONS
export TEST_EMU_OPTIONS
export EXTRA_CPL_ARGS="$extra_cpl_args"
export EXTRA_EMU_ARGS="$extra_emu_args"
TEST_CPL_OPTIONS="$(< ./opts/test_cpl_opts.txt)"
TEST_EMU_OPTIONS="$(< ./opts/test_emu_opts.txt)"

if ! test_jobs="$(./select_test_jobs.sh)"; then
  exit 2
fi
make_status=0
TEST_JOBS="$test_jobs" COLUMNS="$columns" make \
  --no-print-directory \
  --output-sync=target \
  --keep-going \
  --jobs "$test_jobs" \
  -f ./tests/Makefile \
  TEST_BUILD_MODE="$test_build_mode" \
  TEST_SOURCES="${paths[*]}" \
  RESULT_DIR="$result_dir" \
  all || make_status=$?

num_tests=${#paths[@]}
failing=()
not_passed=()
timed_out=()

for test in "${paths[@]}"; do
  status_file="$result_dir/$(basename "${test%.picoc}").status"
  if [[ ! -f "$status_file" ]]; then
    failing+=("$test")
    not_passed+=("$test")
    continue
  fi

  read -r compile_status output_status timeout_status < "$status_file"
  if [[ $compile_status -ne 0 ]]; then
    failing+=("$test")
  fi
  if [[ $output_status -ne 0 ]]; then
    not_passed+=("$test")
  fi
  if [[ $timeout_status -ne 0 ]]; then
    timed_out+=("$test")
  fi
done

if (( ${#not_passed[@]} == 0 )); then
  : > "$NOT_PASSED_TESTS_FILE"
else
  (
    IFS=' '
    printf '%s\n' "${not_passed[*]}"
  ) > "$NOT_PASSED_TESTS_FILE"
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

if [[ $make_status -ne 0 || ${#not_passed[@]} -ne 0 ]]; then
  exit 1
fi
