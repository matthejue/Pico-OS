# System Tests

This directory contains three kinds of tests:

- library tests as single `*.picoc` files directly in `test/`
- OS feature tests with a `launcher.picoc` in a subdirectory
- shell tests whose `input.txt` exercises shell command handling

OS feature and shell tests run through the Pico-OS kernel, init process, and
shell.

## OS Test Directory Layout

Each OS test is one subdirectory. The directory name should describe the
behavior under test, for example:

```text
test/hello_world/
```

A test directory contains:

```text
launcher.picoc           test entry point
program.picoc            optional worker or subject programs
input.txt                required
expected_output.txt      required
```

During a test run, the fixture is copied to `binary/test/<test-name>` and its
generated program files are written there:

```text
program.reti
program.bin
```

The comparison files remain next to the source fixture:

```text
output.txt
raw_output.txt
```

`raw_output.txt` is the complete emulator stdout stream. `output.txt` is the
normalized output used for comparison. Loader requests use
`<esc>load <path><esc>/`, where `<esc>` is ASCII byte 27; the emulator consumes
these control frames instead of writing them to stdout.

## PicoC Programs

Every `*.picoc` file in the test directory is compiled with `picoc_compiler`
and assembled below `binary/test` with:

```sh
reti_emulator -a binary/test/<test-name>/program.reti
```

For an OS feature test, the resulting `launcher.bin` is loaded by the OS
through `input.txt`. The launcher uses the unistd library to load, run, wait
for, and optionally unload the other test binaries. Keeping process
orchestration in PicoC makes each test self-contained and avoids encoding
process IDs and setup steps in UART input.

The Makefile links `library/start/libstart.picoc` into every test program through the
compiler's `-C` option. This startup function initializes the process heap,
passes the process arguments to `main`, and exits through the process syscall
so the kernel can schedule another process and wake any waiters.

## input.txt

`input.txt` contains the ASCII command stream typed into the shell. An OS
feature test loads and runs its launcher, then finishes with `poweroff.bin`.
Shell tests contain the commands whose parsing or shell state they exercise.
The raw shell-test encodings `\b`, `\up`, `\down`, `\left`, `\right`, `\home`,
`\esc`, `\ctrlU`, `\ctrlW`, `\ctrlC`, `\ctrlZ`, and `\ctrlL` send their
corresponding key input instead of literal characters.

Example:

```text
load test/hello_world/launcher.bin
run 3
poweroff.bin
```

PID `1` is normally `system/init.bin` and PID `2` is `user/shell.bin`, so the
first program loaded by the shell is usually PID `3`.

## expected_output.txt

`expected_output.txt` contains the UART output expected from the OS and the test
programs after normalization.

Example:

```text
hello world
```

`make test-os` and `make test-shell` compare `output.txt` against this file.
Trailing whitespace is ignored for the comparison.

The shell redirects a started process's standard input with `< path`, its
standard output with `> path`, appends output with `>> path`, or redirects
stderr with `2> path` and `2>> path`:

```text
shell.bin < ./test/example/commands.txt
echo.bin hello > ./test/example/output.txt
echo.bin again >> ./test/example/output.txt
cat.bin missing.txt 2> ./device/null.dev
cat.bin missing-again.txt 2>> ./test/example/errors.txt
cat.bin input.txt | sed.bin "5aNEW" > output.txt
```

It opens each target in the requested mode, uses `dup2()` for the corresponding
standard descriptor, and passes the resulting descriptors to the process when
it is started. Processes subsequently started by that process inherit the same
redirection. The shell passes `\n` through unchanged, and `echo.bin` expands it
to a newline character while printing its arguments.

A shell whose stdin is redirected executes newline-separated commands with its
ordinary line reader and exits successfully at EOF. Use `shell.bin < FILE` to
run commands from a file; the shell does not accept a file path argument. The
one supported `|` is sequential and uses a temporary file, not a streaming
kernel pipe.

## Running OS Tests

Run every test category sequentially:

```sh
make test
```

This runs the configured library tests and the OS feature and shell tests
normally. Use `make test-fast` to run the library tests followed by OS feature
and shell tests with shared OS sessions per test group. Both targets print the
runtime of the OS feature group, the shell group, and their combined system
tests in `MM:SS` format. At the end, combined targets repeat the library, OS
feature, and shell result summaries under separate headings in execution order.

Run only the library tests:

```sh
make test-lib
```

Normal library and OS tests run independent jobs in parallel. When started
from a terminal, the test runner asks whether it may use all CPU cores or how
many cores it should use. Non-interactive runs use two jobs. `TEST_JOBS` skips
the question and sets the parallelism directly:

```sh
make test TEST_JOBS=4
```

Combined targets such as `make test` and `make test-sys` ask once, then use
the selected count for every nested test group.

Fast OS tests and compatible shell tests run serially inside one shared OS
session, so `TEST_JOBS` does not parallelize `make test-os-fast` or
`make test-shell-fast`. Shell scenarios that start another interactive shell
use an independent session. `TEST_JOBS` only applies to the library-test part
of `make test-fast`.

Each assembler and emulator process receives its own temporary peripheral
directory, so concurrent processes never share `sram.bin`. Tests use staged
`.reti_blocks`/`.st` compilation by default. Direct mode instead passes the
`.picoc` sources straight to the compiler for each merged `.reti` file and
does not reuse staged artifacts:

```sh
make test TEST_BUILD_MODE=direct
```

Set `TEST_PATTERN=all` to run every library test explicitly:

```sh
make test-lib TEST_PATTERN=all
```

Run OS feature and shell tests normally:

```sh
make test-sys
```

Run only OS feature tests or shell tests normally:

```sh
make test-os
make test-shell
```

Run OS feature and shell tests with shared OS boots per test group:

```sh
make test-sys-fast
```

Run only OS feature tests or shell tests through shared OS boots:

```sh
make test-os-fast
make test-shell-fast
```

`system/fast_os_test_launcher.picoc` reads compatible test directories from a
generated manifest. It starts each `launcher.bin` in sequence, redirects its
inherited standard output directly to that test's `output.txt`, and removes
leftover test processes before continuing. The launcher removes
`PICOOS_LOADING_BAR` from its environment first, so test launchers and their
workers do not inherit loader UI output.

For compatible shell tests, the shell reads each `input.txt` and passes its
lines to `eval()`. Before each test, `shell_reset()` removes test processes,
resets descriptors, status values, process IDs, and the environment. Each
test's stdout and stderr are captured together. The line-editing test remains
a raw UART command at the end of the same boot because it specifically tests
backspace handling in `read_line()`. Tests that start another interactive
shell or write directly to `/device/terminal.dev` use an independent OS
session because their behavior cannot be isolated through the shared capture
file. `run_os_tests_fast.py` identifies these cases from `input.txt`: a line
that is exactly `shell.bin` or ends in `/shell.bin` starts an interactive
shell, and any line containing `/device/terminal.dev` writes directly to the
terminal. This is behavior-based rather than a list of test-directory names.
The runner similarly identifies raw UART tests from the line-editing escape
sequences such as `\up`, `\b`, and `\ctrlC`.

Run one configured OS test without comparing `expected_output.txt`:

```sh
make run-os
```

`make run-os` still compiles and assembles the test programs. Without debug
mode, it also writes `raw_output.txt` and `output.txt`.

When `config/os_run_emu_opts.txt` contains `-d`, `make run-os` starts
`reti_emulator` directly on the current terminal so the ncurses debug TUI can
use stdin and stdout. In that debug mode `input.txt` is not piped into the
emulator and stdout is not captured; enter UART input manually through the TUI.

## opts Configuration

The OS feature and shell test targets use their own files in `config/`, separate
from the library tests:

```text
config/os_test_pattern.txt      pattern used by system test targets
config/os_test_cpl_opts.txt     compiler options used by OS and shell tests
config/os_test_emu_opts.txt     emulator options used by OS and shell tests
config/os_run_path.txt          test directory used by make run-os
config/os_run_cpl_opts.txt      compiler options used by make run-os
config/os_run_emu_opts.txt      emulator options used by make run-os
```

The same values can be overridden on the command line:

```sh
make test-os OS_TEST_PATTERN=hello_world
make test-shell OS_TEST_PATTERN=environment
make run-os OS_RUN_PATH=test/hello_world
```

Additional options can be appended with the shared variables:

```sh
make test-os EXTRA_CPL_ARGS='...' EXTRA_EMU_ARGS='...'
make run-os EXTRA_CPL_ARGS='...' EXTRA_EMU_ARGS='...'
```

## Shell PATH Configuration

At startup, init reads `config/environment.txt` into its environment. Child
processes inherit a copy of that environment through their initial stack.
The shell reads `PATH` with `getenv()` and searches its colon-separated
directories when a command does not begin with `./`. For example, the default
`PATH=./user` entry allows `echo.bin hello` to execute `user/echo.bin`.
Relative entries use the immutable emulator startup directory, so they keep
working after `cd` and when one shell starts another shell.
`export NAME="value"` updates the shell environment, and `$NAME` in command
arguments expands to its value.

## Process Environments

`run(pid, arguments, NULL)` copies the calling process's environment to the
child. Passing a custom null-terminated environment array as the third
argument uses that environment instead.

## Results

`make test-os` writes a summary to:

```text
test/os_tests.res
```

The paths of OS tests that did not pass are written to:

```text
config/not_passed_os_tests.txt
```

Normal OS emulator runs have a fixed 120-second timeout. The shared fast
session allows 60 seconds per OS feature or shell test.
