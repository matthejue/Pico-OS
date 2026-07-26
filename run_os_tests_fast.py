#!/usr/bin/env python3
import argparse
import sys
import tempfile
from pathlib import Path

from run_os_tests import (
    MAX_EMULATOR_DURATION_SECONDS,
    append_summary,
    build_test_programs,
    emulator_args_request_debug,
    outputs_match,
    print_heading,
    remove_if_exists,
    run_one_test_dir,
    run_os_test,
    selected_test_dirs,
    split_extra_args,
    validate_test_dir,
    write_not_passed_tests,
)


FAST_LAUNCHER = "./system/fast_os_test_launcher.bin"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Pico-OS integration tests with one shared OS boot."
    )
    parser.add_argument("columns", nargs="?", default="120")
    parser.add_argument("test_pattern", nargs="?", default="")
    parser.add_argument("cpl_args", nargs="?", default="")
    parser.add_argument("emu_args", nargs="?", default="")
    return parser.parse_args()


def has_test_launcher(test_dir):
    return (test_dir / "launcher.picoc").is_file()


def direct_launcher_output_matches_test(test_dir):
    input_lines = (test_dir / "input.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    return has_test_launcher(test_dir) and input_lines == [
        f"load {test_dir}/launcher.bin",
        "run 3",
        "exit",
    ]


def run_fast_session(test_dirs, extra_emu_args):
    with tempfile.TemporaryDirectory(prefix="pico-os-fast-") as directory:
        session_dir = Path(directory)
        manifest_file = session_dir / "manifest.txt"
        manifest_file.write_text(
            "".join(f"./{test_dir}\n" for test_dir in test_dirs),
            encoding="utf-8",
        )
        (session_dir / "input.txt").write_text(
            f"{FAST_LAUNCHER} {manifest_file}\nexit\n",
            encoding="utf-8",
        )
        return run_os_test(
            session_dir,
            extra_emu_args,
            MAX_EMULATOR_DURATION_SECONDS * len(test_dirs),
        )


def collect_results(paths, statuses):
    failing = [
        path for path in paths
        if statuses.get(path) == "failed"
    ]
    timed_out = [
        path for path in paths
        if statuses.get(path) == "timeout"
    ]
    not_passed = [
        path for path in paths
        if statuses.get(path) != "passed"
    ]
    return failing, not_passed, timed_out


def main():
    args = parse_args()
    extra_cpl_args = split_extra_args(args.cpl_args)
    extra_emu_args = split_extra_args(args.emu_args)
    paths = [
        path
        for path in selected_test_dirs(args.test_pattern)
        if validate_test_dir(path)
    ]

    if not paths:
        print("No matching OS tests found.", file=sys.stderr)
        return 1
    if emulator_args_request_debug(extra_emu_args):
        print("Fast OS tests do not support emulator debug mode.", file=sys.stderr)
        return 1

    fast_paths = [path for path in paths if has_test_launcher(path)]
    isolated_paths = [
        path
        for path in paths
        if not direct_launcher_output_matches_test(path)
    ]
    comparable_fast_paths = [
        path for path in fast_paths if path not in isolated_paths
    ]
    statuses = {}
    ready_fast_paths = []

    for test_dir in fast_paths:
        print_heading(test_dir, args.columns)
        remove_if_exists(test_dir / "output.txt")
        remove_if_exists(test_dir / "raw_output.txt")
        if build_test_programs(test_dir, extra_cpl_args):
            ready_fast_paths.append(test_dir)
        else:
            statuses[test_dir] = "failed"

    if ready_fast_paths:
        session_status = run_fast_session(
            ready_fast_paths,
            extra_emu_args,
        )
        if session_status != "passed":
            for test_dir in ready_fast_paths:
                if test_dir in comparable_fast_paths:
                    statuses[test_dir] = session_status
        else:
            for test_dir in comparable_fast_paths:
                if test_dir not in ready_fast_paths:
                    continue
                statuses[test_dir] = (
                    "passed"
                    if outputs_match(test_dir)
                    else "not-passed"
                )

    for test_dir in isolated_paths:
        statuses[test_dir] = run_one_test_dir(
            test_dir,
            args.columns,
            extra_cpl_args,
            extra_emu_args,
            compare=True,
        )

    failing, not_passed, timed_out = collect_results(paths, statuses)
    write_not_passed_tests(not_passed)
    append_summary(
        len(paths),
        failing,
        not_passed,
        timed_out,
    )
    print("Fast-launcher tests:", " ".join(str(path) for path in fast_paths))
    print("Isolated shell tests:", " ".join(
        str(path) for path in isolated_paths
    ))
    return 1 if not_passed else 0


if __name__ == "__main__":
    sys.exit(main())
