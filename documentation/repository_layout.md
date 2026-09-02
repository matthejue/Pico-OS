# Repository layout

This page maps the PicoOS source tree to the generated runtime tree. Source
directories are compiled or copied into [`binary/`](../binary/); `make
release-archive` packages only the files that remain in that directory.

## Source and support directories

The following directories hold the PicoOS implementation, its configuration,
and its test and documentation material.

| Directory | Meaning |
| --- | --- |
| [`boot/`](../boot/) | EPROM bootloader source. It starts the machine, loads the kernel through the UART host protocol, and transfers control to it. |
| [`common/`](../common/) | PicoC code and headers shared by the kernel, bootloader, and userspace, such as heap, string, UART, signal, and syscall definitions. |
| [`config/`](../config/) | Build, run, test, emulator, environment, and release-version configuration files. [`config/config.header`](../config/config.header) contains PicoOS-wide compile-time configuration. |
| [`interrupt_service_routines/`](../interrupt_service_routines/) | Interrupt-vector-table and operating-system interrupt-service-routine sources. |
| [`kernel/`](../kernel/) | Kernel source and headers: startup, dispatching, scheduling, processes, memory, system calls, interrupts, devices, and host filesystem support. Its [`filesystem/`](../kernel/filesystem/) and [`process/`](../kernel/process/) subdirectories group those subsystems. |
| [`library/`](../library/) | Userspace PicoC libraries. Each subdirectory implements a library area such as standard I/O, strings, process and file operations, allocation, signals, mutexes, and startup code. |
| [`system/`](../system/) | Privileged system userspace programs. [`init.picoc`](../system/init.picoc) is the first process started by the kernel; [`fast_os_test_launcher.picoc`](../system/fast_os_test_launcher.picoc) is built only for the fast test workflow. |
| [`user/`](../user/) | Normal userspace command sources, including the shell and commands such as `cat`, `ls`, `mkdir`, and `ps`. |
| [`test/`](../test/) | Standalone library tests and OS/shell test fixtures. Scenario subdirectories normally contain PicoC programs, `input.txt`, and `expected_output.txt`; [`test/README.md`](../test/README.md) describes the test layout. |
| [`documentation/`](.) | Additional technical documentation, diagrams, and supporting material for PicoOS. |
| [`binary/`](../binary/) | Generated release tree. It is cleared and rebuilt by `make release-tree`; it is not the source of truth for PicoOS code. See [Release archive layout](../README.md#release-archive-layout). |

The root also contains [`Makefile`](../Makefile), which defines the build,
release, and test targets, and generated local-development files such as
[`compile_commands.json`](../compile_commands.json) and `README.pdf`. These
generated files are not part of the source or release archive layout.

## Root helper scripts

These scripts are used from the repository root unless stated otherwise. The
release copies only the start and tool-download scripts listed in the last
column; the other scripts support local development and testing.

| Script | Purpose | Included in release archive |
| --- | --- | --- |
| [`create_tag.sh`](../create_tag.sh) | Interactively selects the next PicoOS version, updates [`config/os-release.txt`](../config/os-release.txt), commits the release files, and creates a Git tag. | No |
| [`download-tools.sh`](../download-tools.sh) | Downloads matching Linux, macOS, or Android releases of `reti_emulator` and `picoc_compiler`. | Yes |
| [`download-tools.ps1`](../download-tools.ps1) | PowerShell equivalent that downloads matching Windows tool releases. | Yes |
| [`export_environment_vars_for_makefile.sh`](../export_environment_vars_for_makefile.sh) | Preserves terminal dimensions for nested `make` calls used by test targets. | No |
| [`heading_subheadings.py`](../heading_subheadings.py) | Prints formatted headings used by the shell-based library-test output. | No |
| [`run.sh`](../run.sh) | Compiles one supplied PicoC source with the configured run options and starts it in an isolated emulator instance. | No |
| [`run_lib_test_case.sh`](../run_lib_test_case.sh) | Compiles and runs one standalone library test, checks its output, and cleans its temporary emulator peripheral directory. | No |
| [`run_os_tests.py`](../run_os_tests.py) | Builds, stages, boots, drives, and checks OS feature and shell test scenarios. | No |
| [`run_os_tests_fast.py`](../run_os_tests_fast.py) | Runs compatible OS and shell scenarios with shared PicoOS boots to reduce test time. | No |
| [`run_reti_emulator_isolated.sh`](../run_reti_emulator_isolated.sh) | Starts `reti_emulator` with a new temporary peripheral directory so runs do not share host-device state. | No |
| [`run_sys_tests.sh`](../run_sys_tests.sh) | Runs the shell-based system-test workflow, optionally limiting it to failed tests or using direct compilation. | No |
| [`select_test_jobs.sh`](../select_test_jobs.sh) | Selects or validates the parallel-job count for system tests. | No |
| [`send_keypresses.py`](../send_keypresses.py) | Opens a graphical terminal and replays configured key presses for manual TUI interaction. It requires Python GUI-input packages. | No |
| [`start-picoos.sh`](../start-picoos.sh) | Starts a PicoOS runtime on Linux, macOS, or Android; it can download missing tools and accepts emulator options. | Yes |
| [`start-picoos.ps1`](../start-picoos.ps1) | PowerShell launcher for starting a PicoOS runtime on Windows. | Yes |
| [`update_code_index.py`](../update_code_index.py) | Regenerates [`compile_commands.json`](../compile_commands.json) for editor code navigation over PicoC sources. | No |
| [`run.py`](../run.py) | Legacy Python launcher that attempts to run `source.main`; it is not used by the PicoOS build, release, or test targets. | No |
