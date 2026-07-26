# System Tests

This directory contains two different kinds of tests:

- legacy compiler/runtime sys tests as single `*.picoc` files directly in
  `sys_tests/`
- operating-system integration tests as subdirectories below `sys_tests/`

The OS tests are run through the Pico-OS kernel, init process, and shell. They
are meant to test commands implemented by `system/shell.picoc`, such as `load`,
`run`, `unload`, `list`, `quit`, and `exit`.

## OS Test Directory Layout

Each OS test is one subdirectory. The directory name should describe the
behavior under test, for example:

```text
sys_tests/hello_world/
```

A test directory contains:

```text
launcher.picoc           test entry point
program.picoc            optional worker or subject programs
input.txt                required
expected_output.txt      required
```

During a test run, generated files are written next to the test input files,
including:

```text
program.reti
program.bin
output.txt
raw_output.txt
```

`raw_output.txt` is the complete emulator stdout stream. `output.txt` is the
normalized output used for comparison. Loader requests use
`<esc>load <path><esc>/`, where `<esc>` is ASCII byte 27; the emulator consumes
these control frames instead of writing them to stdout.

## PicoC Programs

Every `*.picoc` file in the test directory is compiled with `picoc_compiler`
and assembled with:

```sh
reti_emulator -f /tmp -a program.reti
```

The resulting `launcher.bin` is loaded by the OS through `input.txt`. The
launcher uses the unistd library to load, run, wait for, and optionally unload
the other test binaries. Keeping process orchestration in PicoC makes each test
self-contained and avoids encoding process IDs and setup steps in UART input.

The Makefile links `lib/start/libstart.picoc` into every test program through the
compiler's `-C` option. This startup function initializes the process heap,
passes the process arguments to `main`, and exits through the process syscall
so the kernel can schedule another process and wake any waiters.

## input.txt

`input.txt` contains the ASCII command stream typed into init. It only loads
and runs the test's launcher, then finishes with `quit` or `exit`.

Example:

```text
load sys_tests/hello_world/launcher.bin
run 3
exit
```

PID `1` is normally `system/init.bin` and PID `2` is `system/shell.bin`, so the
first program loaded by the shell is usually PID `3`.

## expected_output.txt

`expected_output.txt` contains the UART output expected from the OS and the test
programs after normalization.

Example:

```text
hello world
```

`make test-os` compares `output.txt` against this file. Trailing whitespace is
ignored for the comparison.

The shell redirects a started process's standard output with a trailing
`> path`:

```text
echo.bin hello > ./sys_tests/example/output.txt
```

It opens and truncates the target, uses `dup2()` for standard output, and
passes the resulting standard descriptors to the process when it is started.
Processes subsequently started by that process inherit the same redirection.

## Running OS Tests

Run all configured OS tests:

```sh
make test-os
```

Run launcher-based tests through one shared OS boot:

```sh
make test-os-fast
```

`system/fast_os_test_launcher.picoc` reads the selected test directories from
a generated manifest. It starts each available `launcher.bin` in sequence,
redirects its inherited standard output directly to that test's `output.txt`,
and removes leftover test processes before continuing. The launcher removes
`PICOOS_LOADING_BAR` from its environment first, so test launchers and their
workers do not inherit loader UI output.

Tests whose expected behavior depends on interactive shell input still use the
normal isolated OS runner. This includes tests without a `launcher.picoc` and
tests whose `input.txt` does more than load and run that launcher. Their
results are included in the same final summary, so `test-os-fast` covers the
same selected test directories as `test-os`.

Run one configured OS test without comparing `expected_output.txt`:

```sh
make run-os
```

`make run-os` still compiles and assembles the test programs. Without debug
mode, it also writes `raw_output.txt` and `output.txt`.

When `opts/os_run_emu_opts.txt` contains `-d`, `make run-os` starts
`reti_emulator` directly on the current terminal so the ncurses debug TUI can
use stdin and stdout. In that debug mode `input.txt` is not piped into the
emulator and stdout is not captured; enter UART input manually through the TUI.

## opts Configuration

The OS test targets use their own files in `opts/`, separate from the legacy
single-file sys tests:

```text
opts/os_test_pattern.txt      pattern used by make test-os
opts/os_test_cpl_opts.txt     compiler options used by make test-os
opts/os_test_emu_opts.txt     emulator options used by make test-os
opts/os_run_path.txt          test directory used by make run-os
opts/os_run_cpl_opts.txt      compiler options used by make run-os
opts/os_run_emu_opts.txt      emulator options used by make run-os
```

The same values can be overridden on the command line:

```sh
make test-os OS_TEST_PATTERN=hello_world
make run-os OS_RUN_PATH=sys_tests/hello_world
```

Additional options can be appended with the shared variables:

```sh
make test-os EXTRA_CPL_ARGS='...' EXTRA_EMU_ARGS='...'
make run-os EXTRA_CPL_ARGS='...' EXTRA_EMU_ARGS='...'
```

## Shell PATH Configuration

At startup, init reads `opts/environment.txt` into its environment. Child
processes inherit a copy of that environment through their initial stack.
The shell reads `PATH` with `getenv()` and searches its colon-separated
directories when a command does not begin with `./`. For example, the default
`PATH=./user` entry allows `echo.bin hello` to execute `./user/echo.bin`.
`export NAME="value"` updates the shell environment, and `$NAME` in command
arguments expands to its value.

## Process Environments

`run(pid, arguments, NULL)` copies the calling process's environment to the
child. Passing a custom null-terminated environment array as the third
argument uses that environment instead.

## Results

`make test-os` writes a summary to:

```text
sys_tests/os_tests.res
```

The paths of OS tests that did not pass are written to:

```text
opts/not_passed_os_tests.txt
```

The OS emulator run currently has a fixed timeout in `run_os_tests.py`.
