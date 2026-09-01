#!/usr/bin/env python3
import argparse
import sys
import tempfile
import time
from pathlib import Path

from run_os_tests import (
    append_summary,
    build_test_programs,
    copy_staged_test_file,
    emulator_args_request_debug,
    normalize_os_output,
    outputs_match,
    print_heading,
    remove_if_exists,
    run_os_test,
    selected_test_dirs,
    stage_test_directories,
    split_extra_args,
    is_os_feature_test,
    validate_test_dir,
    write_not_passed_tests,
)


OS_FEATURE_TEST_LAUNCHER = "./system/fast_os_test_launcher.bin"
FAST_TEST_TIMEOUT_SECONDS = 60
SHELL_TEST_CAPTURE_FILENAME = ".fast_shell_output.txt"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Pico-OS integration tests with shared OS boots."
    )
    parser.add_argument(
        "--kind",
        choices=("all", "os", "shell"),
        default="all",
        help="Select all OS tests, OS feature tests, or shell tests.",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Compile merged RETI files directly from PicoC sources.",
    )
    parser.add_argument("columns", nargs="?", default="120")
    parser.add_argument("test_pattern", nargs="?", default="")
    parser.add_argument("cpl_args", nargs="?", default="")
    parser.add_argument("emu_args", nargs="?", default="")
    return parser.parse_args()


def is_uart_shell_test(test_dir):
    input_text = (test_dir / "input.txt").read_text(encoding="utf-8")
    return any(
        sequence in input_text
        for sequence in (
            "\\b",
            "\\up",
            "\\down",
            "\\left",
            "\\right",
            "\\home",
            "\\esc",
            "\\ctrlU",
            "\\ctrlW",
            "\\ctrlC",
            "\\ctrlZ",
            "\\ctrlL",
        )
    )


def requires_independent_shell_session(test_dir):
    input_lines = (test_dir / "input.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    for line in input_lines:
        command = line.strip()
        if (command == "shell.bin" or
                command.endswith("/shell.bin") or
                "/device/terminal.dev" in command):
            return True
    return False


def write_manifest(path, test_dirs):
    path.write_text(
        "".join(f"./{test_dir}\n" for test_dir in test_dirs),
        encoding="utf-8",
    )


def run_fast_session(
    os_feature_test_dirs,
    eval_shell_test_dirs,
    uart_shell_test_dirs,
    extra_emu_args,
):
    with tempfile.TemporaryDirectory(prefix="pico-os-fast-") as directory:
        session_dir = Path(directory)
        input_lines = []

        if eval_shell_test_dirs:
            shell_manifest = session_dir / "s.txt"
            write_manifest(shell_manifest, eval_shell_test_dirs)
            input_lines.append(f"run-shell-tests {shell_manifest}")
        if os_feature_test_dirs:
            os_feature_manifest = session_dir / "o.txt"
            write_manifest(os_feature_manifest, os_feature_test_dirs)
            input_lines.append(
                f"{OS_FEATURE_TEST_LAUNCHER} {os_feature_manifest}"
            )
        for test_dir in uart_shell_test_dirs:
            input_lines.extend(
                (test_dir / "input.txt").read_text(
                    encoding="utf-8"
                ).splitlines()
            )
        if not uart_shell_test_dirs:
            input_lines.append("poweroff.bin")

        (session_dir / "input.txt").write_text(
            "\n".join(input_lines) + "\n",
            encoding="utf-8",
        )
        shared_test_count = (
            len(os_feature_test_dirs) +
            len(eval_shell_test_dirs) +
            len(uart_shell_test_dirs)
        )
        status = run_os_test(
            session_dir,
            extra_emu_args,
            FAST_TEST_TIMEOUT_SECONDS * max(1, shared_test_count),
        )
        if uart_shell_test_dirs:
            session_output = (session_dir / "output.txt").read_text(
                encoding="utf-8"
            )
            uart_shell_test_dirs[0].joinpath("output.txt").write_text(
                session_output,
                encoding="utf-8",
            )
        return status


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


def is_process_created_line(line):
    return line.startswith("process with pid ") and line.endswith(" created")


def fast_expected_output(test_dir, os_feature_test, uart_shell_test):
    expected = (test_dir / "expected_output.txt").read_text(
        encoding="utf-8"
    )
    lines = expected.rstrip().splitlines()

    if os_feature_test and lines and is_process_created_line(lines[0]):
        lines.pop(0)
    if lines and is_process_created_line(lines[-1]):
        if os_feature_test or not uart_shell_test:
            lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def normalize_captured_output(test_dir):
    output_path = test_dir / "output.txt"
    if output_path.is_file():
        output_path.write_text(
            normalize_os_output(output_path.read_text(encoding="utf-8")),
            encoding="utf-8",
        )


def main():
    start_time = time.monotonic()
    args = parse_args()
    extra_cpl_args = split_extra_args(args.cpl_args)
    extra_emu_args = split_extra_args(args.emu_args)
    paths = [
        path
        for path in selected_test_dirs(args.test_pattern, args.kind)
        if validate_test_dir(path)
    ]

    if not paths:
        print("No matching OS tests found.", file=sys.stderr)
        return 1
    if emulator_args_request_debug(extra_emu_args):
        print("Fast OS tests do not support emulator debug mode.", file=sys.stderr)
        return 1

    os_feature_paths = [
        path
        for path in paths
        if is_os_feature_test(path)
    ]
    independent_shell_paths = [
        path
        for path in paths
        if path not in os_feature_paths and
        requires_independent_shell_session(path)
    ]
    uart_shell_paths = [
        path
        for path in paths
        if path not in os_feature_paths and
        path not in independent_shell_paths and
        is_uart_shell_test(path)
    ]
    eval_shell_paths = [
        path
        for path in paths
        if path not in os_feature_paths and
        path not in independent_shell_paths and
        path not in uart_shell_paths
    ]
    shell_paths = (
        eval_shell_paths +
        uart_shell_paths +
        independent_shell_paths
    )
    statuses = {}
    ready_os_feature_paths = []
    ready_eval_shell_paths = []
    ready_uart_shell_paths = []
    ready_independent_shell_paths = []

    stage_test_directories(paths)
    for test_dir in paths:
        print_heading(test_dir, args.columns)
        remove_if_exists(test_dir / "output.txt")
        remove_if_exists(test_dir / "raw_output.txt")
        remove_if_exists(test_dir / SHELL_TEST_CAPTURE_FILENAME)
        if build_test_programs(test_dir, extra_cpl_args, args.direct):
            if test_dir in os_feature_paths:
                ready_os_feature_paths.append(test_dir)
            elif test_dir in independent_shell_paths:
                ready_independent_shell_paths.append(test_dir)
            elif test_dir in uart_shell_paths:
                ready_uart_shell_paths.append(test_dir)
            else:
                ready_eval_shell_paths.append(test_dir)
        else:
            statuses[test_dir] = "failed"

    ready_shared_paths = (
        ready_os_feature_paths +
        ready_eval_shell_paths +
        ready_uart_shell_paths
    )
    if ready_shared_paths:
        print("Running one shared OS session", flush=True)
        print(
            "OS feature tests:",
            " ".join(str(path) for path in ready_os_feature_paths),
            flush=True,
        )
        print(
            "Shell tests:",
            " ".join(
                str(path)
                for path in ready_eval_shell_paths + ready_uart_shell_paths
            ),
            flush=True,
        )
        session_status = run_fast_session(
            ready_os_feature_paths,
            ready_eval_shell_paths,
            ready_uart_shell_paths,
            extra_emu_args,
        )
        for test_dir in ready_shared_paths:
            copy_staged_test_file(test_dir, "output.txt")
            copy_staged_test_file(
                test_dir,
                SHELL_TEST_CAPTURE_FILENAME,
            )
        if session_status != "passed":
            for test_dir in ready_shared_paths:
                statuses[test_dir] = session_status
        else:
            for test_dir in ready_eval_shell_paths:
                capture_path = (
                    test_dir / SHELL_TEST_CAPTURE_FILENAME
                )
                if capture_path.is_file():
                    capture_path.replace(test_dir / "output.txt")
                else:
                    statuses[test_dir] = "failed"

            for test_dir in ready_shared_paths:
                if statuses.get(test_dir) == "failed":
                    continue
                normalize_captured_output(test_dir)
                statuses[test_dir] = (
                    "passed"
                    if outputs_match(
                        test_dir,
                        fast_expected_output(
                            test_dir,
                            test_dir in os_feature_paths,
                            test_dir in uart_shell_paths,
                        ),
                    )
                    else "not-passed"
                )

    for test_dir in ready_independent_shell_paths:
        print(f"Running {test_dir} in an independent OS session", flush=True)
        status = run_os_test(
            test_dir,
            extra_emu_args,
            FAST_TEST_TIMEOUT_SECONDS,
        )
        if status == "passed" and not outputs_match(test_dir):
            status = "not-passed"
        statuses[test_dir] = status

    failing, not_passed, timed_out = collect_results(paths, statuses)
    write_not_passed_tests(not_passed)
    append_summary(
        len(paths),
        failing,
        not_passed,
        timed_out,
        args.columns,
        int(time.monotonic() - start_time),
    )
    print("OS feature tests:", " ".join(
        str(path) for path in os_feature_paths
    ))
    print("Shell tests:", " ".join(
        str(path) for path in shell_paths
    ))
    return 1 if not_passed else 0


if __name__ == "__main__":
    sys.exit(main())
