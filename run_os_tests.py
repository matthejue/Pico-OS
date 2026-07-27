#!/usr/bin/env python3
import argparse
import os
import select
import shlex
import subprocess
import sys
import time
from pathlib import Path


RESULT_FILE = Path("sys_tests/os_tests.res")
NOT_PASSED_TESTS_FILE = Path("opts/not_passed_os_tests.txt")
MAX_EMULATOR_DURATION_SECONDS = 120
SHELL_PROMPT = "PICOS> "


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Pico-OS integration tests from sys_tests subdirectories."
    )
    parser.add_argument(
        "--kind",
        choices=("all", "os", "shell"),
        default="all",
        help="Select all OS tests, OS feature tests, or shell tests.",
    )
    parser.add_argument(
        "--run",
        metavar="TEST_DIR",
        help="Run one OS test directory without comparing expected_output.txt.",
    )
    parser.add_argument("columns", nargs="?", default="120")
    parser.add_argument("test_pattern", nargs="?", default="")
    parser.add_argument("cpl_args", nargs="?", default="")
    parser.add_argument("emu_args", nargs="?", default="")
    return parser.parse_args()


def split_extra_args(value):
    return shlex.split(value) if value else []


def run_command(command, **kwargs):
    return subprocess.run(command, text=True, **kwargs)


def print_process_output(result):
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def process_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def is_os_feature_test(test_dir):
    launcher_file = test_dir / "launcher.picoc"
    input_file = test_dir / "input.txt"

    if not launcher_file.is_file() or not input_file.is_file():
        return False
    return input_file.read_text(encoding="utf-8").splitlines() == [
        f"load {test_dir}/launcher.bin",
        "run 3",
        "exit",
    ]


def selected_test_dirs(pattern, kind="all"):
    candidates = [path for path in Path("sys_tests").iterdir() if path.is_dir()]
    if pattern and pattern != "all":
        candidates = [path for path in candidates if pattern in path.name]
    if kind == "os":
        candidates = [path for path in candidates if is_os_feature_test(path)]
    elif kind == "shell":
        candidates = [
            path for path in candidates if not is_os_feature_test(path)
        ]
    return sorted(candidates)


def validate_test_dir(test_dir):
    missing = [
        name
        for name in ("input.txt", "expected_output.txt")
        if not (test_dir / name).is_file()
    ]
    if missing:
        print(f"Missing {', '.join(missing)} in {test_dir}", file=sys.stderr)
        return False
    return True


def remove_if_exists(path):
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def compile_and_assemble(picoc_file, extra_cpl_args):
    reti_file = picoc_file.with_suffix(".reti")
    bin_file = picoc_file.with_suffix(".bin")

    for path in (reti_file, bin_file):
        remove_if_exists(path)

    compile_cmd = [
        "picoc_compiler",
        str(picoc_file),
        *extra_cpl_args,
        "-o",
        str(reti_file),
    ]
    result = run_command(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print_process_output(result)
        print(f"Compilation failed for {picoc_file}")
        return False
    if not reti_file.is_file():
        print(f"Compilation did not produce an output file for {picoc_file}")
        return False

    assemble_cmd = ["reti_emulator", "-f", "/tmp", "-a", str(reti_file)]
    result = run_command(assemble_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print_process_output(result)
        print(f"Assembly failed for {reti_file}")
        return False
    if not bin_file.is_file():
        print(f"Assembly did not produce an output file for {reti_file}")
        return False

    return True


def render_terminal_output(output):
    lines = [[]]
    column = 0

    for character in output:
        value = ord(character)
        if value == 10:
            lines.append([])
            column = 0
        elif value == 13:
            column = 0
        elif value in (8, 127):
            if column > 0:
                column -= 1
                if column < len(lines[-1]):
                    del lines[-1][column]
        elif value == 9:
            next_tab_stop = (column // 8 + 1) * 8
            while column < next_tab_stop:
                if column < len(lines[-1]):
                    lines[-1][column] = " "
                else:
                    lines[-1].append(" ")
                column += 1
        elif 32 <= value <= 126:
            if column < len(lines[-1]):
                lines[-1][column] = character
            else:
                lines[-1].extend(" " for _ in range(column - len(lines[-1])))
                lines[-1].append(character)
            column += 1

    return "\n".join("".join(line) for line in lines)


def is_loading_bar_line(line):
    return (
        len(line) >= 15
        and line[0] == "["
        and line[11:13] == "] "
        and line[-1] == "%"
        and all(character in "# " for character in line[1:11])
        and line[13:-1].isdigit()
    )


def normalize_os_output(output):
    rendered = render_terminal_output(output)
    rendered_lines = rendered.splitlines()
    lines = []
    for index, line in enumerate(rendered_lines):
        prompt_index = line.find(SHELL_PROMPT)
        if prompt_index >= 0:
            line = line[:prompt_index]
        next_line_is_loading_bar = (
            index + 1 < len(rendered_lines)
            and is_loading_bar_line(rendered_lines[index + 1])
        )
        is_loading_label = (
            (line.startswith("load ") or line.startswith("read "))
            and next_line_is_loading_bar
        )
        if line and not is_loading_bar_line(line) and not is_loading_label:
            lines.append(line)
    return "\n".join(lines)


def decode_test_input(line):
    return line.replace("\\b", "\x7f")


def emulator_args_request_debug(extra_emu_args):
    return "-d" in extra_emu_args or "--debug" in extra_emu_args


def run_os_test_interactive(test_dir, extra_emu_args):
    output_file = test_dir / "output.txt"
    raw_output_file = test_dir / "raw_output.txt"

    for path in (output_file, raw_output_file):
        remove_if_exists(path)

    command = [
        "reti_emulator",
        *extra_emu_args,
        "kernel.reti",
    ]

    print(
        "Debug mode detected; starting reti_emulator attached to this terminal."
    )
    print(
        "input.txt is not piped in debug mode because ncurses needs stdin."
    )
    result = run_command(command)
    return "passed" if result.returncode == 0 else "failed"


def run_os_test(
    test_dir,
    extra_emu_args,
    max_duration_seconds=MAX_EMULATOR_DURATION_SECONDS,
):
    input_file = test_dir / "input.txt"
    output_file = test_dir / "output.txt"
    raw_output_file = test_dir / "raw_output.txt"

    for path in (output_file, raw_output_file):
        remove_if_exists(path)

    command = [
        "stdbuf",
        "-o0",
        "-e0",
        "reti_emulator",
        *extra_emu_args,
        "kernel.reti",
    ]

    input_lines = input_file.read_text(encoding="utf-8").splitlines()
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = bytearray()
    stderr = bytearray()
    prompt_search_start = 0

    def read_available(wait_seconds):
        streams = [
            stream
            for stream in (process.stdout, process.stderr)
            if stream is not None
        ]
        if not streams:
            return
        readable, _, _ = select.select(streams, [], [], wait_seconds)
        for stream in readable:
            chunk = os.read(stream.fileno(), 4096)
            if stream is process.stdout:
                stdout.extend(chunk)
            else:
                stderr.extend(chunk)

    def wait_for_prompt():
        nonlocal prompt_search_start
        prompt = SHELL_PROMPT.encode("ascii")
        deadline = time.monotonic() + max_duration_seconds

        while time.monotonic() < deadline:
            prompt_index = stdout.find(prompt, prompt_search_start)
            if prompt_index >= 0:
                prompt_search_start = prompt_index + len(prompt)
                return True
            if process.poll() is not None:
                read_available(0)
                return False
            read_available(min(0.1, deadline - time.monotonic()))
        return False

    timed_out = False
    for line in input_lines:
        if not wait_for_prompt():
            timed_out = process.poll() is None
            break
        process.stdin.write((decode_test_input(line) + "\r").encode("latin-1"))
        process.stdin.flush()

    if process.stdin is not None:
        process.stdin.close()
        process.stdin = None

    if timed_out and process.poll() is None:
        process.kill()
    else:
        deadline = time.monotonic() + max_duration_seconds
        while process.poll() is None and time.monotonic() < deadline:
            read_available(min(0.1, deadline - time.monotonic()))
        if process.poll() is None:
            timed_out = True
            process.kill()
    process.wait()
    if process.stdout is not None:
        stdout.extend(process.stdout.read())
    if process.stderr is not None:
        stderr.extend(process.stderr.read())

    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")
    raw_output_file.write_text(stdout_text, encoding="utf-8")
    output_file.write_text(normalize_os_output(stdout_text), encoding="utf-8")

    if timed_out:
        if stdout_text:
            print(stdout_text, end="")
        if stderr_text:
            print(stderr_text, end="", file=sys.stderr)
        print(
            "Emulator timed out after "
            f"{max_duration_seconds}s for {test_dir}"
        )
        return "timeout"
    if process.returncode != 0:
        if stdout_text:
            print(stdout_text, end="")
        if stderr_text:
            print(stderr_text, end="", file=sys.stderr)
        print(
            f"Emulator failed with exit status {process.returncode} "
            f"for {test_dir}"
        )
        return "failed"

    return "passed"


def outputs_match(test_dir):
    expected_file = test_dir / "expected_output.txt"
    output_file = test_dir / "output.txt"

    expected = expected_file.read_text(encoding="utf-8").rstrip()
    actual = output_file.read_text(encoding="utf-8").rstrip()

    if expected == actual:
        return True

    result = run_command(
        ["diff", "-u", str(expected_file), str(output_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print_process_output(result)
    return False


def write_not_passed_tests(not_passed):
    NOT_PASSED_TESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOT_PASSED_TESTS_FILE.write_text(
        " ".join(str(path) for path in not_passed),
        encoding="utf-8",
    )
    if not_passed:
        with NOT_PASSED_TESTS_FILE.open("a", encoding="utf-8") as file:
            file.write("\n")


def print_heading(test_dir, columns):
    result = run_command(
        ["./heading_subheadings.py", "heading", str(test_dir), columns or "120", "="],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        print_process_output(result)
    else:
        print(f"==== {test_dir} ====")


def append_summary(num_tests, failing, not_passed, timed_out):
    lines = [
        f"Not failing: {num_tests - len(failing)} / {num_tests}",
        f"Failing: {' '.join(str(path) for path in failing)}",
        f"Passed: {num_tests - len(not_passed)} / {num_tests}",
        f"Not passed: {' '.join(str(path) for path in not_passed)}",
        f"Timed out: {' '.join(str(path) for path in timed_out)}",
    ]

    for line in lines:
        print(line)

    with RESULT_FILE.open("a", encoding="utf-8") as result_file:
        for line in lines:
            result_file.write(line + "\n")


def build_test_programs(test_dir, extra_cpl_args):
    for picoc_file in sorted(test_dir.glob("*.picoc")):
        if not compile_and_assemble(picoc_file, extra_cpl_args):
            return False
    return True


def run_one_test_dir(test_dir, columns, extra_cpl_args, extra_emu_args, compare):
    print_heading(test_dir, columns)

    if not build_test_programs(test_dir, extra_cpl_args):
        return "failed"

    if not compare and emulator_args_request_debug(extra_emu_args):
        run_status = run_os_test_interactive(test_dir, extra_emu_args)
    else:
        run_status = run_os_test(test_dir, extra_emu_args)
    if run_status != "passed":
        return run_status

    if compare and not outputs_match(test_dir):
        return "not-passed"

    return "passed"


def run_configured_test(args, extra_cpl_args, extra_emu_args):
    test_dir = Path(args.run)
    if not test_dir.is_dir():
        print(f"OS run path is not a directory: {test_dir}", file=sys.stderr)
        return 1
    if not validate_test_dir(test_dir):
        return 1

    status = run_one_test_dir(
        test_dir,
        args.columns,
        extra_cpl_args,
        extra_emu_args,
        compare=False,
    )
    return 0 if status == "passed" else 1


def run_matching_tests(args, extra_cpl_args, extra_emu_args):
    paths = selected_test_dirs(args.test_pattern, args.kind)
    paths = [path for path in paths if validate_test_dir(path)]

    if not paths:
        print("No matching OS tests found.", file=sys.stderr)
        return 1

    failing = []
    not_passed = []
    timed_out = []

    for test_dir in paths:
        status = run_one_test_dir(
            test_dir,
            args.columns,
            extra_cpl_args,
            extra_emu_args,
            compare=True,
        )

        if status != "passed":
            if status == "timeout":
                timed_out.append(test_dir)
            elif status == "failed":
                failing.append(test_dir)
            not_passed.append(test_dir)


    write_not_passed_tests(not_passed)
    append_summary(len(paths), failing, not_passed, timed_out)
    print(f"Updated test list: {NOT_PASSED_TESTS_FILE}")

    return 1 if not_passed else 0


def main():
    args = parse_args()
    extra_cpl_args = split_extra_args(args.cpl_args)
    extra_emu_args = split_extra_args(args.emu_args)

    if args.run:
        return run_configured_test(args, extra_cpl_args, extra_emu_args)

    return run_matching_tests(args, extra_cpl_args, extra_emu_args)


if __name__ == "__main__":
    sys.exit(main())
