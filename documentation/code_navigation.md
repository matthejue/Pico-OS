# PicoC code navigation

VS Code treats `*.picoc` and `*.header` files as C and uses clangd as the only
code-navigation provider. Microsoft C/C++ IntelliSense is disabled for this
workspace because running both providers can produce conflicting F12 results.

`compile_commands.json` is generated from the current source tree rather than
maintained by hand. The `PicoOS: Refresh code index` VS Code task runs whenever
the repository folder opens. VS Code may ask once for permission to run
automatic tasks.

After adding, moving, renaming, or deleting PicoC files during an open session,
run:

```sh
make code-index
```

clangd normally notices the changed compilation database. If an old result
remains in memory, run `clangd: Restart language server` from the VS Code
command palette once.

## Kernel initialization call map

The kernel entry point is `kernel/kernel.picoc`. Its initialization calls are
implemented across the following translation units:

| Statement in `kernel/kernel.picoc` | Definition | README explanation |
| --- | --- | --- |
| `activate_kernel_stack_boundary()` | [`kernel/exception.picoc`](../kernel/exception.picoc) | [Stack-overflow boundary](../README.md#441-stack-overflow-boundary) |
| `debug;` | Compiler statement used directly in [`kernel/kernel.picoc`](../kernel/kernel.picoc); it is not a function | [PicoC-Compiler extensions](../README.md#picoc-compiler-extensions) |
| `init_kernel_heap()` | [`kernel/kmalloc.picoc`](../kernel/kmalloc.picoc) | [Heap initialization](../README.md#921-heap-initialization) |
| `initialize_process_table()` | [`kernel/process/process.picoc`](../kernel/process/process.picoc) | [Process table](../README.md#51-process-table) |
| `init_process_memory_heap()` | [`kernel/pmalloc.picoc`](../kernel/pmalloc.picoc) | [Heap initialization](../README.md#921-heap-initialization) and [process memory allocation](../README.md#94-process-memory-allocation) |
| `initialize_shared_memory()` | [`kernel/shared_memory.picoc`](../kernel/shared_memory.picoc) | [Shared memory](../README.md#95-shared-memory) |
| `initialize_terminal()` | [`kernel/filesystem/terminal.picoc`](../kernel/filesystem/terminal.picoc) | [UART and keypress interrupt](../README.md#48-uart-and-keypress-interrupt) |
| `interrupt_controller_initialize()` | [`kernel/interrupt_controller.picoc`](../kernel/interrupt_controller.picoc) | [Device mappings and controller initialization](../README.md#431-device-mappings-and-controller-initialization) |
| `load_process()` | [`kernel/process/process_loader.picoc`](../kernel/process/process_loader.picoc) | [Loading processes](../README.md#55-loading-processes) |
| `mark_process_ready_with_arguments()` | [`kernel/process/process_arguments.picoc`](../kernel/process/process_arguments.picoc) | [Program arguments and environment](../README.md#56-program-arguments-and-environment) and [initial process stack](../README.md#57-initial-process-stack) |
| `interrupt_controller_activate_timer()` | [`kernel/interrupt_controller.picoc`](../kernel/interrupt_controller.picoc) | [Timer interrupt](../README.md#47-timer-interrupt) |
| `dispatcher_start_next_process()` | [`kernel/dispatcher.picoc`](../kernel/dispatcher.picoc) | [Dispatcher](../README.md#8-dispatcher) |

## Subsystem source map

| Topic | PicoOS | Related project contract |
| --- | --- | --- |
| Boot and binary input | [`bootloader.picoc`](../boot/bootloader.picoc), [`process_loader.picoc`](../kernel/process/process_loader.picoc) | [binary sections](../../RETI-Emulator/documentation/section_file_entries.md) |
| UART | [`uart_hardware.picoc`](../kernel/uart_hardware.picoc), [`uart_protocol.picoc`](../common/uart_protocol.picoc) | [emulator UART](../../RETI-Emulator/documentation/uart_protocol.md) |
| IVT/ISRs | [`os_isrs.picoc`](../interrupt_service_routines/os_isrs.picoc) | [compiler low-level attributes](../../PicoC-Compiler/documentation/reti_sections_low_level_picoc.md) |
| Processes/waits | [`process.header`](../kernel/process.header), [`process.picoc`](../kernel/process/process.picoc) | [PicoC calls/frames](../../PicoC-Compiler/README.md#function-calls-and-stack-frames) |
| Scheduling/dispatch | [`scheduler.picoc`](../kernel/scheduler.picoc), [`dispatcher.picoc`](../kernel/dispatcher.picoc) | [`INT`/`RTI` interpreter](../../RETI-Emulator/source/interpr.c) |
| Exceptions | [`exception.picoc`](../kernel/exception.picoc) | [CPU exceptions](../../RETI-Emulator/documentation/cpu_exceptions.md) |
| Memory | [`heap.picoc`](../common/heap.picoc), [`kmalloc.picoc`](../kernel/kmalloc.picoc), [`pmalloc.picoc`](../kernel/pmalloc.picoc) | [generated kernel constants](../../PicoC-Compiler/documentation/kernel_header_option.md) |
| Files/descriptors | [`file_descriptor.picoc`](../kernel/filesystem/file_descriptor.picoc), [`filesystem.picoc`](../kernel/filesystem/filesystem.picoc), [`host_filesystem.picoc`](../kernel/filesystem/host_filesystem.picoc), [`library/unistd`](../library/unistd) | [UART escape sequences](../../RETI-Emulator/documentation/uart_protocol.md) |
| Kernel terminal | [`terminal.picoc`](../kernel/filesystem/terminal.picoc), [`terminal.header`](../kernel/filesystem/terminal.header) | [emulator UART](../../RETI-Emulator/documentation/uart_protocol.md) |
| Userspace lifecycle | [`start.picoc`](../library/start/start.picoc), [`init.picoc`](../system/init.picoc), [`shell.picoc`](../user/shell.picoc) | [compiler `-C`](../../PicoC-Compiler/README.md#command-line-options) |

## Filesystem and terminal call map

The filesystem directory separates per-process descriptor state from the
kernel-wide terminal object:

| Responsibility | Implementation |
| --- | --- |
| Create, inherit, close, duplicate, and destroy descriptor tables | [`file_descriptor.picoc`](../kernel/filesystem/file_descriptor.picoc) |
| Dispatch `open()`, `read()`, `write()`, and `lseek()` by descriptor kind | [`filesystem.picoc`](../kernel/filesystem/filesystem.picoc) |
| Normalize paths and issue host-file UART requests | [`host_filesystem.picoc`](../kernel/filesystem/host_filesystem.picoc) |
| Own the terminal input ring, block readers, and complete reads from UART interrupts | [`terminal.picoc`](../kernel/filesystem/terminal.picoc) |
| Expose the userspace syscall wrappers | [`library/unistd`](../library/unistd) |

`FileDescriptorTable` contains only descriptor entries. Standard descriptors
store `/device/terminal` in the same path field used by regular files; the
filesystem recognizes that path and enters the shared `Terminal`, which is
initialized once by the kernel. The UART ISR enters `handle_uart_interrupt()`
in `terminal.picoc`; descriptor-based terminal reads and the single-character
input syscall both enter `begin_terminal_read()` there. The release-tree marker
for this virtual device is
[`binary/device/terminal.dev`](../binary/device/terminal.dev). The Makefile
creates it as part of the runtime tree.
