# PicoOS
[\[↓ TOC\]](#contents)

PicoOS is a small educational operating system for the RETI teaching CPU. This
repository contains its bootloader, kernel, libraries, init process, user applications (including shell), and tests.

To try PicoOS, start with [`Build and run`](#build-and-run). To study its design,
follow the numbered chapters in the [contents](#contents). For source builds
and development, see the [development workflow](documentation/development_workflow.md).

PicoOS has **15 libraries**, **18 user applications** including the [`shell`](user/shell.picoc),
and **37 syscalls**. See [`10.2 Library overview and dependencies`](#102-library-overview-and-dependencies), [`13.2 Applications, library calls, and host requests`](#132-applications-library-calls-and-host-requests), and [`2.4.2.2.1 System-call groups`](#24221-system-call-groups) for their interfaces.

[POSIX](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html)
standardizes Unix interfaces and command behavior, including processes,
signals, files, terminals, shared memory, and shells. PicoOS borrows familiar
names and conventions from it, but implements only a small subset and does
not claim conformance. All code and data share one physical address space,
without an MMU or process isolation. Files live on the emulator host, reached
through UART. This small scope makes it possible to follow a library call
through the kernel and into e.g. a context switch.

PicoOS works with two sibling projects. Together they turn PicoC source into
an executing operating system:

- [PicoC-Compiler](../PicoC-Compiler/README.md) compiles the PicoC subset of C,
  links multiple translation units, lays out interrupt, code, and data
  sections, and produces RETI assembly plus section metadata
- [RETI-Emulator](../RETI-Emulator/README.md) assembles and executes RETI,
  models EPROM, SRAM, UART, interrupts, the timer, and CPU exceptions, and
  supplies the host-side file protocol
- PicoOS provides the EPROM bootloader, kernel, libraries, init process, shell,
  user programs, and tests

The build-and-boot diagram follows the bootloader into EPROM and the kernel
into SRAM. The compiler links RETI programs, and the emulator assembles the
kernel binary and runs the bootloader. Reusable `.reti_blocks` and `.st` files
can be linked with source files. The optional `-k eprom` and `-k sram` headers
supply compile-time memory constants.

![PicoOS build and boot overview](documentation/images/picoos-build-boot.svg)

`reti_emulator -e` loads the bootloader into EPROM. The bootloader then
requests the kernel binary over UART, reads its header, and copies the
payload into SRAM. [`1.1.8 Linked .sections metadata and the five-word binary header`](#118-linked-sections-metadata-and-the-five-word-binary-header) explains the binary format, and [`1.1.9 Generated memory constants for the bootloader and kernel`](#119-generated-memory-constants-for-the-bootloader-and-kernel) explains the
generated memory headers.

Each stage passes the following files or runtime requests to the next:

| Producer | Contract | Consumer |
| --- | --- | --- |
| PicoC-Compiler | Linked [`.reti`](../PicoC-Compiler/source/passes/linking/reti_pass.py), `.sections`, generated memory headers, and `.debuginfo` | RETI-Emulator assembler/debugger and PicoOS low-level builds |
| RETI-Emulator assembler | Five-word layout header followed by encoded RETI words in `.bin` | EPROM bootloader and kernel process loader |
| PicoOS libraries | Syscall number plus direct value/pointer or stack-local request structure | Interrupt entry, [`handle_syscall()`](kernel/syscall.picoc#L16), and the owning kernel subsystem |
| Kernel subsystems | PCBs, activations, queues, descriptor/shared-memory state, and periphery-register writes | Scheduler/dispatcher and emulated RETI hardware |
| PicoOS UART host request protocol | Bounded `<ESC>...<ESC>/` requests and big-endian responses | RETI-Emulator host file services, or a companion serial host on hardware |

## Build and run
[\[↓ TOC\]](#contents)

The quickest way to run PicoOS is the ready-built archive attached to the
[latest PicoOS release](https://github.com/matthejue/Pico-OS/releases/latest).
Download [`pico-os-runtime.tar.gz`](pico-os-runtime.tar.gz), extract it into its own directory, enter that
directory, and use the launcher for your platform. The archive expands its
runtime files directly, without an extra top-level directory.

```console
$ curl -fLO https://github.com/matthejue/Pico-OS/releases/latest/download/pico-os-runtime.tar.gz
$ mkdir pico-os-runtime
$ tar -xzf pico-os-runtime.tar.gz -C pico-os-runtime
$ cd pico-os-runtime
$ ./start-picoos.sh
```

On Windows, extract the same archive and run [`./start-picoos.ps1`](./start-picoos.ps1) from
PowerShell. On Android, use Termux and the shell launcher. The launchers search
the archive directory and `PATH` for the tools. When the RETI Emulator or PicoC
Compiler is absent, `start-picoos` offers to download a compatible release
beside the archive files. The extracted directory becomes PicoOS `/`, so files
created from PicoOS remain there. The emulator is required to run PicoOS. The
compiler is included for related PicoC work.

The launchers accept these options to select the emulator and terminal mode:

| Behavior | Shell launcher | PowerShell launcher |
| --- | --- | --- |
| Use a specific emulator | `--reti-emulator PATH` | `-RetiEmulator PATH` |
| Enable DMA loading | `--dma` or `-M` | `-Dma` or `-M` |
| Run directly in the terminal | `--notui` or `-N` | `-NoTui` or `-N` |
| Show help | `--help` or `-h` | `-Help` or `-h` |
| Pass remaining emulator options | `-- EMULATOR_ARGS...` | `-- EMULATOR_ARGS...` |

The launcher asks whether to enable DMA unless you already selected it on
the command line. DMA copies incoming executable data into SRAM while the
CPU can run other processes. [`4.2.1 Loading a process (load library call)`](#421-loading-a-process-load-library-call) compares DMA with polling, and [`2.7 DMA completion interrupt path`](#27-dma-completion-interrupt-path) follows
the completion interrupt.

On the first run, the launcher offers to download the
[`picoos-cheatsheet.pdf`](https://github.com/matthejue/Pico-OS_Cheatsheet/releases/latest/download/picoos-cheatsheet.pdf).
It records your choice in the archive README and leaves a download link there
if you decline.

To build or run a local kernel, follow the
[development workflow](documentation/development_workflow.md).

### Use the PicoOS shell
[\[↓ TOC\]](#contents)

The release launcher opens the Debug TUI by default. Press `c`, then Enter, to
continue through bootloader, kernel, and init startup. Press capital `V` to
open the raw UART terminal, where arrow keys, `Ctrl+C`, and `Ctrl+Z` reach
PicoOS. `Ctrl+]` returns to the debugger. Lowercase `v` opens the normal
terminal and Escape returns from it. Alternatively, start with `--notui` on
the shell launcher or `-NoTui` on PowerShell to use the PicoOS terminal
directly.

At `PicoOS>`, run a program by its executable name or a path. The shell finds
commands such as `echo.bin` in `/user`. This example replaces a phrase through
a file-backed pipeline and writes the result to `topics.txt`:

```console
PicoOS> echo.bin "kernel\ncontext switcher\nscheduler" > input.txt
PicoOS> cat.bin input.txt | sed.bin "s/context switcher/dispatcher/" > topics.txt
PicoOS> cat.bin topics.txt
kernel
dispatcher
scheduler
```

The shell runs the left command first, saves its output in a temporary file,
and gives that file to the right command as standard input. `>` sends the
right command's output to `topics.txt`. See [`12.7 Sequential file-backed pipelines`](#127-sequential-file-backed-pipelines) and [`12.6 Input/output redirection`](#126-inputoutput-redirection) for the details.

### Release archive layout
[\[↓ TOC\]](#contents)

For each `v*` tag, the [release workflow](.github/workflows/build.yml) builds
and verifies [`binary/`](binary/), then archives its contents as
[`pico-os-runtime.tar.gz`](pico-os-runtime.tar.gz). This runtime contains the binaries, configuration,
and launch scripts. The [development workflow](documentation/development_workflow.md#building-the-release-tree-and-archive)
explains how to build it locally.

The archive uses the extracted directory as PicoOS `/`. Host `/tmp` is not
mounted. Use the emulator version offered by the launcher.

The table locates each runtime component. Its links point to the generated
files under [`binary/`](binary/):

| Archive path | Contents and purpose |
| --- | --- |
| [`binary/README.md`](binary/README.md) | Short release-specific startup and host-filesystem instructions. It becomes [`README.md`](README.md) at the archive root. |
| [`binary/start-picoos.sh`](binary/start-picoos.sh), [`binary/start-picoos.ps1`](binary/start-picoos.ps1) | Linux/macOS/Android and Windows launchers. They find or download the tools, select the boot and kernel metadata, and start the emulator. |
| [`binary/download-tools.sh`](binary/download-tools.sh), [`binary/download-tools.ps1`](binary/download-tools.ps1) | Helpers used by the launcher to download matching released `picoc_compiler` and `reti_emulator` binaries when they are missing. |
| [`binary/boot/`](binary/boot/) | [`bootloader.reti`](binary/boot/bootloader.reti), the RETI EPROM image built from [`bootloader.picoc`](boot/bootloader.picoc) that loads and starts the kernel. |
| [`binary/kernel/`](binary/kernel/) | [`kernel.bin`](binary/kernel/kernel.bin), the loadable image built from [`kernel.picoc`](kernel/kernel.picoc), [`kernel.sections`](binary/kernel/kernel.sections), its linked memory-layout metadata, and [`kernel.debuginfo`](binary/kernel/kernel.debuginfo), its source/debug metadata. |
| [`binary/system/`](binary/system/) | Loadable system-program binaries, currently [`init.bin`](system/init.picoc). |
| [`binary/user/`](binary/user/) | Loadable PicoOS command binaries, including [`shell.bin`](user/shell.picoc) and the standard user commands built from [`user/`](user/). |
| [`binary/config/`](binary/config/) | Runtime configuration copied from [`config/`](config/): the initial environment, emulator options, and PicoOS release version. |
| [`binary/device/`](binary/device/) | `terminal.dev` and `null.dev` marker files. They represent PicoOS virtual device paths, they do not hold device data. |

For the corresponding source-tree directories and local helper scripts, see
[Repository layout](documentation/repository_layout.md).

## Intended physical hardware
[\[↓ TOC\]](#contents)

The proposed hardware uses an Alchitry Cu V2 FPGA board, two ISSI
IS61WV25616BLL-10TLI SRAM chips, and a SparkFun USB-to-UART adapter. The prices
are the design's example parts list, checked at DigiKey Germany on 12 August
2026, including VAT.

The circuit connects the host, FPGA, and SRAM. Both SRAM chips receive the
same address and control signals. Their 16-bit data buses form one 32-bit
interface shared by the CPU and DMA. UART receives bytes, and a buffer groups
four bytes into each DMA word:

![Intended physical hardware: host, FPGA, and shared SRAM](documentation/images/intended-hardware.svg)

UART receive-ready signals an interrupt for terminal input and host
responses. During DMA reception, the buffer instead supplies complete words
to DMA. The controller, buffer, and SRAM arbitration are FPGA logic described
in [DMA connections](documentation/dma_connections.md).

- **FPGA: [Alchitry Cu V2](https://www.digikey.de/short/8cmz0qnc) with Lattice
  iCE40-HX8K** ([board schematic](https://cdn.sparkfun.com/assets/2/f/9/9/3/CuSchematic.pdf),
  [FPGA datasheet](https://www.latticesemi.com/~/media/latticesemi/documents/datasheets/ice/ice40lphxfamilydatasheet.pdf)):
  **€55.66** (checked 12 August 2026). The FPGA implements the educational
  32-bit CPU, timer, interrupt controller, UART controller, DMA controller,
  receive word buffer, and arbitrated SRAM interface.
- **SRAM: two [ISSI
  IS61WV25616BLL-10TLI](https://www.digikey.de/short/075fh38w) chips**
  ([datasheet](https://www.issi.com/WW/pdf/61-64WV25616.pdf)):
  **2 × €5.80 = €11.60** (checked 12 August 2026). Each asynchronous SRAM is
  organized as 256K × 16 bits. Both chips share the FPGA’s 18 address lines,
  chip enable, output enable, write enable, and byte-enable control. One chip
  connects its 16 data pins to FPGA SRAM data bits 0–15 and the other to bits
  16–31.
  Driving both chips with the same address and control signals therefore makes
  them one 256K × 32-bit SRAM shared by CPU and DMA accesses. It provides
  2^18 = 262,144 individually
  addressable 32-bit words, addressed from 0 through 2^18 - 1. Each word holds
  four bytes, so the total is
  `262,144 words × 4 bytes = 1,048,576 bytes = 1 MiB`. For comparison, 2^18
  bytes alone would be only 0.262144 MB.
- **USB-to-UART: [SparkFun Serial Basic Breakout with CH340C and
  USB-C](https://www.digikey.de/short/h83tqvbw)**
  ([product sheet](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/739/DEV-15096_Web.pdf),
  [CH340C datasheet](https://cdn.sparkfun.com/assets/5/0/a/8/5/CH340DS1.PDF),
  [board schematic](https://cdn.sparkfun.com/assets/learn_tutorials/8/3/7/Serial-Basic-CH340C_Datasheet.pdf)):
  **€10.92** (checked 12 August 2026). Its `TXO` pin connects to the FPGA
  UART’s receive pin, its `RXI` pin connects to the FPGA UART’s transmit pin,
  and their grounds are connected. USB exposes the CH340C as a serial port on
  the host. The host and FPGA use the same baud rate and serial format, and
  UART transfers each request and response as a sequence of bytes.
  UART receive-ready drives the FPGA interrupt controller for ordinary
  interrupt-driven input. During an active DMA transfer, the receive buffer
  instead supplies groups of four incoming bytes to the DMA controller.

The example total is **€55.66 + 2 × €5.80 + €10.92 = €78.18 including VAT**.
This excludes USB cables, wires, connectors, a printed circuit board, other
interconnection hardware, and shipping. In the rest of this README, PCB means
*process control block* unless the hardware context says otherwise.

The hardware setup has not been used yet. During development, the emulator
provides UART and host file services. It exposes its launch directory as
PicoOS `/` and prevents `..` or symbolic links from escaping that root.

On hardware, a companion host program must serve the same requests over the
USB serial port. [`1.2.3 UART host-service protocol`](#123-uart-host-service-protocol) shows that protocol, and [`8.9 PicoOS paths, working directories, and host operations`](#89-picoos-paths-working-directories-and-host-operations) explains PicoOS paths.

The generated binaries give a sense of how much of the proposed 1 MiB SRAM
they occupy. These sizes include the five-word header and come from the
current files in [`binary/`](binary/):

| Image | 32-bit words | Size |
| --- | ---: | ---: |
| [`kernel.bin`](binary/kernel/kernel.bin) ([`kernel.picoc`](kernel/kernel.picoc)) | 41,502 | 0.166008 MB |
| [`init.bin`](binary/system/init.bin) ([`init.picoc`](system/init.picoc)) | 10,824 | 0.043296 MB |
| [`shell.bin`](binary/user/shell.bin) ([`shell.picoc`](user/shell.picoc)) | 29,647 | 0.118588 MB |
| [`cat.bin`](binary/user/cat.bin) ([`cat.picoc`](user/cat.picoc)) | 10,487 | 0.041948 MB |
| [`echo.bin`](binary/user/echo.bin) ([`echo.picoc`](user/echo.picoc)) | 12,018 | 0.048072 MB |

Counting headers conservatively, the kernel, init, and shell leave
`262,144 - (41,502 + 10,824 + 29,647) = 180,171` words, enough for 17 [`cat.bin`](user/cat.picoc)
images. Running processes also need heap and stack space. The loader omits
the five header words when copying each image to SRAM.

### RETI execution model
[\[↓ TOC\]](#contents)

RETI uses 32-bit word addresses. The top two bits select EPROM, peripherals,
or SRAM, as shown below. SRAM spans both `10` and `11`, giving it half of the
address space. These are address ranges, independent of installed capacity:

![RETI address space with EPROM and periphery each occupying one quarter and SRAM occupying one half](documentation/images/reti-memory-map.svg)

PicoOS uses the three regions as follows:

| High bits | Address space | PicoOS use |
| --- | --- | --- |
| `00` | EPROM | Bootloader |
| `01` | Memory-mapped periphery | UART, interrupt controller, timer, stack boundary, exception cause, DMA |
| `10` or `11` | SRAM | Interrupt table, kernel, process images, heaps, and stacks |

## Contents

The chapters explain the toolchain and kernel, then follow startup through
init, the shell, and user applications. The final chapters cover testing,
teaching uses, AI use, and limitations.

1. [Toolchain extensions for PicoOS](#1-toolchain-extensions-for-picoos)
   - [1.1 PicoC-Compiler extensions](#11-picoc-compiler-extensions)
      - [1.1.1 Compilation pipeline and compiler passes](#111-compilation-pipeline-and-compiler-passes)
      - [1.1.2 Separate compilation, reusable artifacts, and linking](#112-separate-compilation-reusable-artifacts-and-linking)
      - [1.1.3 System V ABI stack frames and call cleanup](#113-system-v-abi-stack-frames-and-call-cleanup)
         - [1.1.3.1 Stack-frame layout and caller cleanup](#1131-stack-frame-layout-and-caller-cleanup)
         - [1.1.3.2 Shared function epilogue and return values](#1132-shared-function-epilogue-and-return-values)
         - [1.1.3.3 Naked functions without a generated frame](#1133-naked-functions-without-a-generated-frame)
      - [1.1.4 Placing globals in .ivt with section("ivt")](#114-placing-globals-in-ivt-with-sectionivt)
      - [1.1.5 Selecting a startup function with -C / --startup-source](#115-selecting-a-startup-function-with--c----startup-source)
         - [1.1.5.1 Default compiler-generated _start](#1151-default-compiler-generated-_start)
         - [1.1.5.2 PicoOS libstart startup sequence](#1152-picoos-libstart-startup-sequence)
         - [1.1.5.3 Startup functions used by PicoOS images](#1153-startup-functions-used-by-picoos-images)
      - [1.1.6 Program sections, interrupt table entries, and linker placement](#116-program-sections-interrupt-table-entries-and-linker-placement)
      - [1.1.7 RETI pseudoinstructions](#117-reti-pseudoinstructions)
         - [1.1.7.1 Interrupt-safe PUSH and POP](#1171-interrupt-safe-push-and-pop)
         - [1.1.7.2 Loading 32-bit values with LOADI32](#1172-loading-32-bit-values-with-loadi32)
         - [1.1.7.3 Long jumps with JUMP32](#1173-long-jumps-with-jump32)
         - [1.1.7.4 Pseudoinstruction expansion during linking](#1174-pseudoinstruction-expansion-during-linking)
      - [1.1.8 Linked .sections metadata and the five-word binary header](#118-linked-sections-metadata-and-the-five-word-binary-header)
      - [1.1.9 Generated memory constants for the bootloader and kernel](#119-generated-memory-constants-for-the-bootloader-and-kernel)
   - [1.2 RETI-Emulator extensions](#12-reti-emulator-extensions)
      - [1.2.1 RETI machine model and memory-mapped peripherals](#121-reti-machine-model-and-memory-mapped-peripherals)
      - [1.2.2 Atomic test-and-set with TSL](#122-atomic-test-and-set-with-tsl)
         - [1.2.2.1 Test-and-set in SRAM](#1221-test-and-set-in-sram)
         - [1.2.2.2 TSL instruction encoding](#1222-tsl-instruction-encoding)
      - [1.2.3 UART host-service protocol](#123-uart-host-service-protocol)
      - [1.2.4 Debugger, source view, and terminal modes](#124-debugger-source-view-and-terminal-modes)
1. [Interrupts, system calls, preemption, and exceptions](#2-interrupts-system-calls-preemption-and-exceptions)
   - [2.1 RETI interrupt entry and the interrupt service routine table](#21-reti-interrupt-entry-and-the-interrupt-service-routine-table)
   - [2.2 Interrupt-controller mappings and priorities](#22-interrupt-controller-mappings-and-priorities)
      - [2.2.1 Interrupt-controller initialization](#221-interrupt-controller-initialization)
      - [2.2.2 Interrupt-controller function reference](#222-interrupt-controller-function-reference)
      - [2.2.3 Memory-mapped periphery function reference](#223-memory-mapped-periphery-function-reference)
   - [2.3 Saved interrupt stack frame](#23-saved-interrupt-stack-frame)
   - [2.4 System-call interface and execution](#24-system-call-interface-and-execution)
      - [2.4.1 Syscall selectors and register convention](#241-syscall-selectors-and-register-convention)
         - [2.4.1.1 Process, wait, signal, and memory request structures](#2411-process-wait-signal-and-memory-request-structures)
         - [2.4.1.2 File and directory request structures](#2412-file-and-directory-request-structures)
      - [2.4.2 System-call entry, execution, and return to userspace](#242-system-call-entry-execution-and-return-to-userspace)
         - [2.4.2.1 Entering kernel context](#2421-entering-kernel-context)
            - [2.4.2.1.1 Stack-boundary helpers](#24211-stack-boundary-helpers)
         - [2.4.2.2 Handle Syscall](#2422-handle-syscall)
            - [2.4.2.2.1 System-call groups](#24221-system-call-groups)
         - [2.4.2.3 Selecting the return path](#2423-selecting-the-return-path)
         - [2.4.2.4 Restoring process context with RTI](#2424-restoring-process-context-with-rti)
      - [2.4.3 System-call selection function reference](#243-system-call-selection-function-reference)
   - [2.5 Timer interrupts and userspace preemption](#25-timer-interrupts-and-userspace-preemption)
      - [2.5.1 Timer interrupt path](#251-timer-interrupt-path)
         - [2.5.1.1 Saving context and selecting the timer branch](#2511-saving-context-and-selecting-the-timer-branch)
         - [2.5.1.2 Requesting deferred scheduling for kernel work](#2512-requesting-deferred-scheduling-for-kernel-work)
         - [2.5.1.3 Restoring interrupted kernel context with RTI](#2513-restoring-interrupted-kernel-context-with-rti)
         - [2.5.1.4 Entering kernel context for userspace preemption](#2514-entering-kernel-context-for-userspace-preemption)
         - [2.5.1.5 Saving process context and restoring the selected process](#2515-saving-process-context-and-restoring-the-selected-process)
      - [2.5.2 Kernel non-preemption and deferred rescheduling](#252-kernel-non-preemption-and-deferred-rescheduling)
      - [2.5.3 Shell character delay for different timer intervals](#253-shell-character-delay-for-different-timer-intervals)
   - [2.6 UART receive interrupt path](#26-uart-receive-interrupt-path)
      - [2.6.1 Entering kernel segments on the interrupted stack](#261-entering-kernel-segments-on-the-interrupted-stack)
      - [2.6.2 Handling the received byte](#262-handling-the-received-byte)
      - [2.6.3 Restoring interrupted context with RTI](#263-restoring-interrupted-context-with-rti)
      - [2.6.4 UART nesting and interrupt priorities](#264-uart-nesting-and-interrupt-priorities)
      - [2.6.5 Polled UART function reference](#265-polled-uart-function-reference)
   - [2.7 DMA completion interrupt path](#27-dma-completion-interrupt-path)
      - [2.7.1 Entering kernel segments on the interrupted stack](#271-entering-kernel-segments-on-the-interrupted-stack)
      - [2.7.2 Completing the DMA wait](#272-completing-the-dma-wait)
      - [2.7.3 Restoring interrupted context with RTI](#273-restoring-interrupted-context-with-rti)
      - [2.7.4 DMA waiting and completion function reference](#274-dma-waiting-and-completion-function-reference)
   - [2.8 CPU exceptions and runtime errors](#28-cpu-exceptions-and-runtime-errors)
      - [2.8.1 CPU exception entry and registers](#281-cpu-exception-entry-and-registers)
         - [2.8.1.1 Entering kernel context after a fault](#2811-entering-kernel-context-after-a-fault)
            - [2.8.1.1.1 Comparing exception and timer context tests](#28111-comparing-exception-and-timer-context-tests)
         - [2.8.1.2 Reading and classifying the exception](#2812-reading-and-classifying-the-exception)
            - [2.8.1.2.1 Reporting the exception](#28121-reporting-the-exception)
         - [2.8.1.3 Halting the kernel or terminating the process](#2813-halting-the-kernel-or-terminating-the-process)
      - [2.8.2 Supported exceptions and allocation errors](#282-supported-exceptions-and-allocation-errors)
      - [2.8.3 Exception and stack-boundary function reference](#283-exception-and-stack-boundary-function-reference)
1. [Memory management and shared memory](#3-memory-management-and-shared-memory)
   - [3.1 Heap block layout and allocation algorithm](#31-heap-block-layout-and-allocation-algorithm)
   - [3.2 SRAM image and heap hierarchy](#32-sram-image-and-heap-hierarchy)
   - [3.3 Kernel Heap](#33-kernel-heap)
      - [3.3.1 Kernel Heap blocks and kernel objects](#331-kernel-heap-blocks-and-kernel-objects)
      - [3.3.2 Kernel Heap allocator function reference](#332-kernel-heap-allocator-function-reference)
   - [3.4 Process and Shared Data Heap](#34-process-and-shared-data-heap)
      - [3.4.1 Process allocations](#341-process-allocations)
      - [3.4.2 Shared Data allocations](#342-shared-data-allocations)
      - [3.4.3 Process and Shared Data Heap allocator function reference](#343-process-and-shared-data-heap-allocator-function-reference)
   - [3.5 User Process Heap](#35-user-process-heap)
      - [3.5.1 Per-Process User Process Heap](#351-per-process-user-process-heap)
      - [3.5.2 User Process Heap allocator function reference](#352-user-process-heap-allocator-function-reference)
   - [3.6 Heap and allocator function reference](#36-heap-and-allocator-function-reference)
      - [3.6.1 Common allocator linkage and function reference](#361-common-allocator-linkage-and-function-reference)
      - [3.6.2 Reallocation decisions](#362-reallocation-decisions)
      - [3.6.3 Allocation and repeated coalescing example](#363-allocation-and-repeated-coalescing-example)
         - [3.6.3.1 Initial state and first-fit search](#3631-initial-state-and-first-fit-search)
         - [3.6.3.2 Allocation splits D](#3632-allocation-splits-d)
         - [3.6.3.3 Free D and merge its remainder](#3633-free-d-and-merge-its-remainder)
            - [3.6.3.3.1 Mark D free](#36331-mark-d-free)
            - [3.6.3.3.2 Merge D and its remainder](#36332-merge-d-and-its-remainder)
         - [3.6.3.4 Free C and merge repeatedly at B](#3634-free-c-and-merge-repeatedly-at-b)
            - [3.6.3.4.1 Mark C free](#36341-mark-c-free)
            - [3.6.3.4.2 First merge at B](#36342-first-merge-at-b)
            - [3.6.3.4.3 Second merge at B](#36343-second-merge-at-b)
1. [Processes and process lifecycle](#4-processes-and-process-lifecycle)
   - [4.1 Process control block fields](#41-process-control-block-fields)
      - [4.1.1 Process states and transitions](#411-process-states-and-transitions)
      - [4.1.2 Global process list and current process](#412-global-process-list-and-current-process)
         - [4.1.2.1 From PCBs to Process Payloads in SRAM](#4121-from-pcbs-to-process-payloads-in-sram)
   - [4.2 Loading and starting a process](#42-loading-and-starting-a-process)
      - [4.2.1 Loading a process (load library call)](#421-loading-a-process-load-library-call)
         - [4.2.1.1 Step 1: Receiving the process image](#4211-step-1-receiving-the-process-image)
            - [4.2.1.1.1 ProcessLoad transfer record](#42111-processload-transfer-record)
         - [4.2.1.2 Step 2: Creating the child PCB](#4212-step-2-creating-the-child-pcb)
         - [4.2.1.3 Process stack after load](#4213-process-stack-after-load)
         - [4.2.1.4 Load function reference](#4214-load-function-reference)
      - [4.2.2 Starting a process (run library call)](#422-starting-a-process-run-library-call)
         - [4.2.2.1 Initial user process stack](#4221-initial-user-process-stack)
            - [4.2.2.1.1 User process stack placement](#42211-user-process-stack-placement)
            - [4.2.2.1.2 Initial argc, argv, and envp](#42212-initial-argc-argv-and-envp)
               - [4.2.2.1.2.1 Concrete initial-stack example](#422121-concrete-initial-stack-example)
         - [4.2.2.2 Parent-to-child inheritance](#4222-parent-to-child-inheritance)
            - [4.2.2.2.1 Environment origin and propagation](#42221-environment-origin-and-propagation)
            - [4.2.2.2.2 Loading-bar environment variable](#42222-loading-bar-environment-variable)
         - [4.2.2.3 Run function reference](#4223-run-function-reference)
   - [4.3 Process list, PCB metadata, and lifecycle function reference](#43-process-list-pcb-metadata-and-lifecycle-function-reference)
1. [Shared Memory Entries and Mappings](#5-shared-memory-entries-and-mappings)
   - [5.1 Named entries and per-process attachments](#51-named-entries-and-per-process-attachments)
      - [5.1.1 Global shared-memory list and entry names](#511-global-shared-memory-list-and-entry-names)
         - [5.1.1.1 From Shared Memory Entries to Shared Data Payloads in SRAM](#5111-from-shared-memory-entries-to-shared-data-payloads-in-sram)
      - [5.1.2 Per-process attachment lists in SRAM](#512-per-process-attachment-lists-in-sram)
   - [5.2 Mapping, unlinking, and deferred destruction](#52-mapping-unlinking-and-deferred-destruction)
   - [5.3 Shared Memory function reference](#53-shared-memory-function-reference)
1. [Scheduling and context switching](#6-scheduling-and-context-switching)
   - [6.1 Scheduler implementation](#61-scheduler-implementation)
      - [6.1.1 Algorithm and Round Robin comparison](#611-algorithm-and-round-robin-comparison)
         - [6.1.1.1 Selecting the next runnable process](#6111-selecting-the-next-runnable-process)
         - [6.1.1.2 Starting at the head after the last process](#6112-starting-at-the-head-after-the-last-process)
         - [6.1.1.3 Reaching the list end during a scan](#6113-reaching-the-list-end-during-a-scan)
         - [6.1.1.4 Implementation](#6114-implementation)
      - [6.1.2 Scheduler function reference](#612-scheduler-function-reference)
   - [6.2 Saved process registers](#62-saved-process-registers)
   - [6.3 Saving the current process and selecting the next process](#63-saving-the-current-process-and-selecting-the-next-process)
   - [6.4 Restoring the selected process and returning with RTI](#64-restoring-the-selected-process-and-returning-with-rti)
   - [6.5 Dispatcher function reference](#65-dispatcher-function-reference)
1. [Blocking, wait queues, signals, and mutexes](#7-blocking-wait-queues-signals-and-mutexes)
   - [7.1 Wait queues and PCB links](#71-wait-queues-and-pcb-links)
      - [7.1.1 Blocking with sleep and waking with wakeup](#711-blocking-with-sleep-and-waking-with-wakeup)
         - [7.1.1.1 From blocking to resumed execution](#7111-from-blocking-to-resumed-execution)
      - [7.1.2 Child waiting with waitpid](#712-child-waiting-with-waitpid)
         - [7.1.2.1 Recording termination status](#7121-recording-termination-status)
         - [7.1.2.2 Parent collection and final removal](#7122-parent-collection-and-final-removal)
      - [7.1.3 Wait queue function reference](#713-wait-queue-function-reference)
   - [7.2 Process signals](#72-process-signals)
      - [7.2.1 Supported signals and fixed actions](#721-supported-signals-and-fixed-actions)
      - [7.2.2 Stopping and continuing a process](#722-stopping-and-continuing-a-process)
      - [7.2.3 Termination, Ctrl-C, and parent collection](#723-termination-ctrl-c-and-parent-collection)
      - [7.2.4 Fixed PicoOS signal actions compared with Unix](#724-fixed-picoos-signal-actions-compared-with-unix)
      - [7.2.5 Signal function reference](#725-signal-function-reference)
   - [7.3 Mutexes with test-and-set and wait queues](#73-mutexes-with-test-and-set-and-wait-queues)
1. [Terminal, file descriptors, and host filesystem](#8-terminal-file-descriptors-and-host-filesystem)
   - [8.1 Per-process file-descriptor table](#81-per-process-file-descriptor-table)
   - [8.2 Global terminal input buffer](#82-global-terminal-input-buffer)
   - [8.3 Blocking and completing terminal reads](#83-blocking-and-completing-terminal-reads)
   - [8.4 Foreground input ownership and terminal-generated signals](#84-foreground-input-ownership-and-terminal-generated-signals)
   - [8.5 Virtual terminal and null-device paths](#85-virtual-terminal-and-null-device-paths)
   - [8.6 File-descriptor creation, inheritance, duplication, and cleanup](#86-file-descriptor-creation-inheritance-duplication-and-cleanup)
   - [8.7 Terminal-buffer and pending-read function reference](#87-terminal-buffer-and-pending-read-function-reference)
   - [8.8 Opening, reading, writing, and seeking](#88-opening-reading-writing-and-seeking)
   - [8.9 PicoOS paths, working directories, and host operations](#89-picoos-paths-working-directories-and-host-operations)
1. [Kernel data structures: relationships, storage, and lifetimes](#9-kernel-data-structures-relationships-storage-and-lifetimes)
   - [9.1 Memory layout, allocation sources, and lifetimes](#91-memory-layout-allocation-sources-and-lifetimes)
   - [9.2 Containment and reference relationships](#92-containment-and-reference-relationships)
   - [9.3 Kernel global variables and process-list roots](#93-kernel-global-variables-and-process-list-roots)
   - [9.4 Wait requests and queue storage](#94-wait-requests-and-queue-storage)
1. [Userspace libraries](#10-userspace-libraries)
   - [10.1 From a library call to the kernel: waitpid](#101-from-a-library-call-to-the-kernel-waitpid)
      - [10.1.1 Header, implementation, and linking](#1011-header-implementation-and-linking)
      - [10.1.2 Packing arguments and executing the syscall](#1012-packing-arguments-and-executing-the-syscall)
      - [10.1.3 Interrupt entry, waiting, and return](#1013-interrupt-entry-waiting-and-return)
   - [10.2 Library overview and dependencies](#102-library-overview-and-dependencies)
      - [10.2.1 unistd: processes, descriptors, paths, and wait queues](#1021-unistd-processes-descriptors-paths-and-wait-queues)
         - [10.2.1.1 Process operations in process.picoc](#10211-process-operations-in-processpicoc)
         - [10.2.1.2 Descriptor operations in io.picoc](#10212-descriptor-operations-in-iopicoc)
         - [10.2.1.3 Working-directory operations in working_directory.picoc](#10213-working-directory-operations-in-working_directorypicoc)
         - [10.2.1.4 Path operations in file_removal.picoc](#10214-path-operations-in-file_removalpicoc)
         - [10.2.1.5 Wait-queue operations in blocking.picoc](#10215-wait-queue-operations-in-blockingpicoc)
      - [10.2.2 fcntl: opening and creating files](#1022-fcntl-opening-and-creating-files)
      - [10.2.3 sys/wait: waiting for children](#1023-syswait-waiting-for-children)
      - [10.2.4 mutex: locking and waking contenders](#1024-mutex-locking-and-waking-contenders)
      - [10.2.5 sys/mman: named shared memory](#1025-sysmman-named-shared-memory)
      - [10.2.6 dirent: directory streams](#1026-dirent-directory-streams)
      - [10.2.7 stdlib: process heap, environment, conversion, and exit](#1027-stdlib-process-heap-environment-conversion-and-exit)
         - [10.2.7.1 Heap operations in malloc.picoc](#10271-heap-operations-in-mallocpicoc)
         - [10.2.7.2 Decimal conversion in atoi.picoc](#10272-decimal-conversion-in-atoipicoc)
         - [10.2.7.3 Environment operations in env.picoc](#10273-environment-operations-in-envpicoc)
         - [10.2.7.4 Process exit in exit.picoc](#10274-process-exit-in-exitpicoc)
      - [10.2.8 string: copying, comparison, and length](#1028-string-copying-comparison-and-length)
      - [10.2.9 stdio: streams, formatting, and scanning](#1029-stdio-streams-formatting-and-scanning)
         - [10.2.9.1 Streams and output in stdio.picoc](#10291-streams-and-output-in-stdiopicoc)
         - [10.2.9.2 Scanning in scanf.picoc](#10292-scanning-in-scanfpicoc)
      - [10.2.10 start: entering and leaving a user program](#10210-start-entering-and-leaving-a-user-program)
      - [10.2.11 Single-function libraries](#10211-single-function-libraries)
1. [Complete startup: bootloader, kernel, init, shell, and user applications](#11-complete-startup-bootloader-kernel-init-shell-and-user-applications)
   - [11.1 Loading the kernel from the EPROM bootloader](#111-loading-the-kernel-from-the-eprom-bootloader)
   - [11.2 Kernel startup](#112-kernel-startup)
      - [11.2.1 Loading init and entering normal execution](#1121-loading-init-and-entering-normal-execution)
   - [11.3 Init process](#113-init-process)
      - [11.3.1 Init responsibilities](#1131-init-responsibilities)
      - [11.3.2 Initial environment configuration](#1132-initial-environment-configuration)
      - [11.3.3 Loading, starting, and waiting for the shell](#1133-loading-starting-and-waiting-for-the-shell)
      - [11.3.4 Shell startup](#1134-shell-startup)
      - [11.3.5 Loading user applications](#1135-loading-user-applications)
      - [11.3.6 Shell exit and restart policy](#1136-shell-exit-and-restart-policy)
      - [11.3.7 When init terminates](#1137-when-init-terminates)
1. [Shell](#12-shell)
   - [12.1 Shell-owned state](#121-shell-owned-state)
   - [12.2 Shell startup and command loop](#122-shell-startup-and-command-loop)
   - [12.3 Interactive line editing and command history](#123-interactive-line-editing-and-command-history)
   - [12.4 Command parsing, expansion, and execution](#124-command-parsing-expansion-and-execution)
   - [12.5 Shell built-in commands](#125-shell-built-in-commands)
      - [12.5.1 Foreground processes, background processes, and job-control signals](#1251-foreground-processes-background-processes-and-job-control-signals)
   - [12.6 Input/output redirection](#126-inputoutput-redirection)
   - [12.7 Sequential file-backed pipelines](#127-sequential-file-backed-pipelines)
1. [User applications and commands](#13-user-applications-and-commands)
   - [13.1 Writing a simple user application](#131-writing-a-simple-user-application)
   - [13.2 Applications, library calls, and host requests](#132-applications-library-calls-and-host-requests)
      - [13.2.1 Command behavior and supported options](#1321-command-behavior-and-supported-options)
      - [13.2.2 Command errors and exit statuses](#1322-command-errors-and-exit-statuses)
1. [Test system](#14-test-system)
   - [14.1 Library, OS, shell, and boot test categories](#141-library-os-shell-and-boot-test-categories)
      - [14.1.1 Files that make up a test](#1411-files-that-make-up-a-test)
      - [14.1.2 Library test example](#1412-library-test-example)
      - [14.1.3 OS test example](#1413-os-test-example)
      - [14.1.4 Shell test example](#1414-shell-test-example)
      - [14.1.5 Boot test example](#1415-boot-test-example)
   - [14.2 Test execution](#142-test-execution)
      - [14.2.1 Make targets](#1421-make-targets)
1. [Use in operating-systems and real-time operating-systems lectures](#15-use-in-operating-systems-and-real-time-operating-systems-lectures)
   - [15.1 Operating-systems topics](#151-operating-systems-topics)
      - [15.1.1 Inspecting PicoOS execution in the RETI-Emulator](#1511-inspecting-picoos-execution-in-the-reti-emulator)
      - [15.1.2 Exploring userspace heap allocation](#1512-exploring-userspace-heap-allocation)
      - [15.1.3 Editing and executing symbolic RETI assembly](#1513-editing-and-executing-symbolic-reti-assembly)
   - [15.2 Real-time operating-systems topics](#152-real-time-operating-systems-topics)
      - [15.2.1 Parent, workers, and shared memory](#1521-parent-workers-and-shared-memory)
      - [15.2.2 Complete launcher and worker code](#1522-complete-launcher-and-worker-code)
      - [15.2.3 Following the counter and mutex through execution](#1523-following-the-counter-and-mutex-through-execution)
1. [Use of AI in the project](#16-use-of-ai-in-the-project)
1. [Limitations](#17-limitations)
- [Appendix: Inspecting .bin files with hexyl](#appendix-inspecting-bin-files-with-hexyl)

# 1. Toolchain extensions for PicoOS
[\[↑ TOC\]](#contents)

The original teaching compiler and emulator ran standalone programs. PicoOS
needed linking, loading, interrupts, and debugging support. This chapter
explains the extensions that let us build and inspect the OS in PicoC and RETI.

The sibling projects keep their detailed change histories in the
[PicoC-Compiler feature history](../PicoC-Compiler/documentation/new_features_for_pico_os.md)
and [RETI-Emulator feature history](../RETI-Emulator/documentation/new_features_for_pico_os.md).

## 1.1 PicoC-Compiler extensions
[\[↑ TOC\]](#contents)

The compiler extensions support larger programs and give PicoOS control over
entry points and memory layout. The table summarizes them:

| Feature | Contribution used by PicoOS |
| --- | --- |
| Installation | The compiler installation creates the environment and installs the `picoc_compiler` command |
| Preprocessing | `#include`, include paths, `#pragma once`, object-like macros, line splicing, dependency output, and optional syntax checking |
| Multiple translation units | Per-file compilation, symbol merging, cross-file calls/globals, and final program-wide linking |
| Reusable build artifacts | `.reti_blocks` and `.st` retain lowered code, symbols, data, startup, and debug metadata for later links |
| Automatic artifact reuse | Source/header hashes and compiler options decide whether an unchanged compiled file can be reused, Make dependency files expose the same inputs |
| Broader PicoC syntax | `typedef`, casts, mixed declarations/statements, postfix increment, array-size inference, and compile-time integer simplification |
| Pointer support | Pointer returns, `void *`, typed pointer arithmetic, dereference/member conditions, and compatible forward/repeated struct declarations |
| Function pointers | Declarations, arrays, assignments, indirect calls, and statically emitted function addresses |
| Variadic functions | Variadic declarations and the documented System-V-style stack-frame locations used by [`printf()`](library/stdio/stdio.picoc#L354) and [`scanf()`](library/stdio/scanf.picoc#L112) |
| String and character data | Escapes, inferred local arrays, global strings, deduplicated string literals, and linker-safe literal names |
| Inline RETI assembly | `asm("...")`, linked labels inside assembly, and safe pseudoinstructions such as `LOADI32`, `JUMP32`, `PUSH`, and `POP` |
| Low-level functions | `__attribute__((naked))` suppresses compiler prologue/epilogue code for startup and interrupt handlers |
| Custom sections | `__attribute__((section("ivt")))` places selected globals or functions in `.ivt`, ordinary functions and globals use `.text` and `.data` |
| interrupt service routines entries | `IVTE` resolves handler pointers into tagged SRAM addresses |
| Runtime startup | Generated default entry or a replaceable custom `-C` startup such as PicoOS [`libstart`](library/start/libstart.picoc) |
| Global initialization | `-O1` emits known scalar, string, struct, array, and function-pointer initializers directly into `.data` or an attributed `.ivt` |
| Shared epilogues | All ordinary returns converge on one generated restore/return block |
| Section layout | Separate `.ivt`, `.text`, and `.data` regions and the paired final `.sections` file |
| Linked labels | Human-readable labels remain until final patching, making generated RETI inspectable |
| Kernel headers | `-k sram` and `-k eprom` generate [`memory_constants.header`](kernel/memory_constants.header) for code that has no PCB/runtime loader context |
| Debug information | `.debuginfo` describes source ranges, globals, frames, arguments, calls, returns, and local variables for the emulator TUI |
| Inspectable intermediates | Preprocessed source and named RETI-block stages make the result of individual compiler passes visible |
| Source trap and RETI `NOP` | `debug;` lowers to the emulator trap and inline `NOP` remains a real instruction |

### 1.1.1 Compilation pipeline and compiler passes
[\[↑ TOC\]](#contents)

The original compiler used Lark to turn one PicoC source file into a parse tree.
Its [`TransformerPicoC`](https://github.com/matthejue/PicoC-Compiler/blob/fb553487c96c6105689cbdf4d9caf61cc9d6434d/src/ast_transformers.py#L10) converted that tree into a PicoC AST,
which the [compiler passes](https://github.com/matthejue/PicoC-Compiler/blob/fb553487c96c6105689cbdf4d9caf61cc9d6434d/src/passes.py) lowered into RETI:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    source["One PicoC source file"]

    subgraph frontend["Lexing and parsing"]
        lexer["Lark lexer and parser"]
        tree["Parse tree"]
        ast["PicoC AST"]
    end

    subgraph compilation["Single-file compilation passes"]
        shrink["picoc_shrink"]
        blocks["picoc_blocks"]
        anf["picoc_anf"]
        reti_blocks["reti_blocks"]
        patch["reti_patch"]
        reti["reti"]
    end

    output["One RETI program"]

    source --> lexer --> tree -->|TransformerPicoC| ast
    ast --> shrink --> blocks --> anf --> reti_blocks --> patch --> reti --> output
```

The extended pipeline replaces Lark with Tree-sitter to parse preprocessed source.
[`TransformerPicoC.build_ast()`](../PicoC-Compiler/source/ast_transformers.py#L111) converts the parse tree into a PicoC AST before per-file symbol, type, and lowering passes.
Linking merges results, inserts startup code, and resolves addresses. Amber stages mark additions or replacements:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    source["PicoC source files"]

    subgraph preprocessing["Preprocessing"]
        preprocessor["Includes, macros, and line splicing"]:::added
        preprocessed["Preprocessed source"]:::added
    end

    subgraph frontend["Lexing and parsing"]
        parser["Tree-sitter lexer and parser"]:::added
        parse_tree["Tree-sitter parse tree"]
        ast["PicoC AST"]
    end

    subgraph compilation["Per-file compilation passes"]
        shrink["picoc_shrink"]
        blocks["picoc_blocks"]
        symbol["PicoC symbols<br/>picoc_symbol"]:::added
        typing["PicoC typing<br/>picoc_typing"]:::added
        anf["picoc_anf"]
        reti_blocks["reti_blocks"]
    end

    subgraph linking["Program-wide linking passes"]
        merge["Merge code / global symbols<br/>Insert startup code"]:::added
        patch["reti_patch"]
        reti["reti"]
    end

    output["Linked RETI program"]

    source --> preprocessor --> preprocessed --> parser --> parse_tree -->|TransformerPicoC.build_ast| ast
    ast --> shrink --> blocks --> symbol --> typing --> anf --> reti_blocks
    reti_blocks --> merge --> patch --> reti --> output
    classDef added fill:#fff1d6,stroke:#805916,stroke-width:3px,color:#17313a
    style preprocessing fill:#fff1d6,stroke:#805916,stroke-width:3px,color:#17313a
```

### 1.1.2 Separate compilation, reusable artifacts, and linking
[\[↑ TOC\]](#contents)

Separate compilation follows the C object-file workflow. GCC or Clang
compiles a `.c` file into an `.o` file with `-c`. PicoC compiles a `.picoc`
file into a `.reti_blocks` file and its `.st` symbol table. A conventional
object file stores that table internally. The example builds [`libstring.picoc`](library/string/libstring.picoc)
and [`basic_string.picoc`](test/basic_string.picoc), together with the test's [`libstdlib`](library/stdlib/libstdlib.picoc) and [`libstdio`](library/stdio/libstdio.picoc)
dependencies. The equivalent C filenames illustrate the comparison:

```console
$ gcc -c -O2 libstring.c basic_string.c
$ ls -1 basic_string.o libstring.o
basic_string.o
libstring.o

$ gcc -o basic_string basic_string.o libstring.o
$ ls -1 basic_string
basic_string

$ picoc_compiler -c -O1 library/string/libstring.picoc test/basic_string.picoc \
    library/stdlib/libstdlib.picoc library/stdio/libstdio.picoc
$ ls -1 library/string/libstring.{reti_blocks,st} test/basic_string.{reti_blocks,st}
library/string/libstring.reti_blocks
library/string/libstring.st
test/basic_string.reti_blocks
test/basic_string.st

$ picoc_compiler -O1 -o binary/basic_string.reti test/basic_string.reti_blocks \
    library/string/libstring.reti_blocks library/stdlib/libstdlib.reti_blocks \
    library/stdio/libstdio.reti_blocks
$ ls -1 binary/basic_string.{reti,sections}
binary/basic_string.reti
binary/basic_string.sections
```

In C, the linker consumes object files and their embedded symbol tables:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart TB
    SRC["libstring.c + included .h headers"] --> COMPILE["gcc -c -O2 libstring.c"]
    COMPILE --> OBJ["libstring.o"]
    OBJ --> LINK["gcc -o basic_string libstring.o basic_string.o ..."]
    MORE["basic_string.o, ..."] --> LINK
    LINK --> OUT["basic_string<br/>executable binary"]
```

Compiler-generated `.reti_blocks` inputs use matching `.st` symbol tables
in the same directory, which the compiler reads automatically. Hand-written
assembly using only registers, numeric operands, and labels needs no symbol
table. The diagram shows the compiler-generated files:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart TB
    SRC["libstring.picoc<br/>includes string.picoc / shared helpers"] --> COMPILE["picoc_compiler -c -O1 libstring.picoc"]
    COMPILE --> OBJ["libstring.reti_blocks"]
    COMPILE --> SYMBOLS["libstring.st<br/>JSON symbol table"]
    OBJ --> LINK["picoc_compiler -O1 -o basic_string.reti<br/>libstring.reti_blocks basic_string.reti_blocks ..."]
    SYMBOLS -.->|automatically read with libstring.reti_blocks| LINK
    MORE["basic_string.reti_blocks, ..."] --> LINK
    LINK --> RETI["basic_string.reti"]
    LINK --> SECTIONS["basic_string.sections"]
```

`-o` names the linked output. PicoC keeps its metadata in separate files:
`.st` for symbols, `.sections` for memory layout, and `.debuginfo` for debugging.

### 1.1.3 System V ABI stack frames and call cleanup
[\[↑ TOC\]](#contents)

The [System V Application Binary Interface (ABI)](https://github.com/hjl-tools/x86-psABI/wiki/x86-64-psABI-1.0.pdf)
defines how compiled code interoperates, including calling conventions and
stack frames. PicoC adapts this general model to RETI. It does not implement
the AMD64 ABI. The following frame and return rules let compiled functions,
assembly wrappers, startup code, and interrupt handlers work together.

#### 1.1.3.1 Stack-frame layout and caller cleanup
[\[↑ TOC\]](#contents)

The called function saves and restores `BAF`. Its caller pushes a generated
continuation-block address and removes the argument cells after the return.
For `func(arg1, arg2)`, the compiler evaluates and pushes `arg2` first, then
`arg1`. This is the compiler's actual evaluation order, rather than a general
C guarantee.

The stack grows toward lower addresses. Bold rows show the current call,
while italic rows show its caller's frame. `caller BAF` distinguishes the
caller's frame pointer from the current `BAF`:

| Address direction / position | Contents | Managed by |
| --- | --- | --- |
| **Higher addresses ↑** | *Earlier stack contents* | *Earlier calls* |
| *`caller BAF + 3`* | *Caller function's argument* | *Caller's caller* |
| *`caller BAF + 2`* | *Caller function's return address* | *Caller's caller* |
| *`caller BAF + 1`* | *Frame pointer saved on entry to the caller* | *Caller function's own frame* |
| *`caller BAF`* | *Caller function's local variable* | *Caller function's own frame* |
| *`caller BAF - 1`* | *Temporary expression value retained across this call* | *Caller function's expression evaluation* |
| **`BAF + 4`** | **Second argument (`arg2`)** | **Caller, for this call** |
| **`BAF + 3`** | **First argument (`arg1`)** | **Caller, for this call** |
| **`BAF + 2`** | **Return address to the caller's continuation block** | **Caller, for this call** |
| **`BAF + 1`** | **Saved `caller BAF`** | **Current callee** |
| **`BAF`** | **First local variable, if present** | **Current callee** |
| **`BAF - 1`, ...** | **Further locals and temporary expression values** | **Current callee** |
| **`SP`** | **Free cell immediately below occupied stack cells** | **Current stack boundary** |
| **Lower addresses ↓** | **Direction of stack growth** | |

One-cell arguments begin at `BAF + 3`. Arrays and structs passed by value
occupy their full width, increasing later offsets accordingly. The temporary
cell above the arguments can hold a value such as `left` while evaluating
`left + func(arg1, arg2)`.

This layout lets variadic functions walk arguments toward higher addresses
without knowing their total count. [`printf()`](library/stdio/stdio.picoc#L354) starts after its format at
`BAF + 4`, and [`fprintf()`](library/stdio/stdio.picoc#L346) after its stream and format at `BAF + 5`. [`1.1.7.1 Interrupt-safe PUSH and POP`](#1171-interrupt-safe-push-and-pop)
explains interrupt-safe stack updates.

#### 1.1.3.2 Shared function epilogue and return values
[\[↑ TOC\]](#contents)

Every ordinary function has one `<function>_epilogue` block. A return puts
its value in `IN2` and jumps there to restore `BAF` and the return address.
Keeping the result in `IN2` leaves `ACC` free for long jumps:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    return_a["return expression A"] --> epilogue["function_epilogue"]
    return_b["return expression B"] --> epilogue
    return_void["return"] --> epilogue
    epilogue --> restore["Restore BAF"]
    restore --> caller["Jump to saved return address"]
```

This example shows the callee returning a value and the caller cleaning up
its argument:

```c
int add_one(int value) {
    return value + 1;
}

int main(void) {
    return add_one(41);
}
```

`-c` compiles without linking, `-v` adds pattern comments, and `-w` writes
the pass results to files. Use these options to generate both representations:

```console
$ picoc_compiler -c -O1 -v -w normal-function.picoc
```

The `.picoc_anf` file is the last PicoC representation before RETI lowering:

```text
_global_inits:
add_one:
  NewStackframe(Num('0'))
  Exp(StackframeParam(Num('0')))
  Exp(Num('1'))
  Exp(BinOp(Stack(Num('2')), Add(), Stack(Num('1'))))
  Assign(IN2, Stack(Num('1')))
  Exp(GoTo(Name('add_one_epilogue')))
add_one_epilogue:
  RestoreStackframe()
  RestoreReturnAddress()
main:
  NewStackframe(Num('0'))
  // Call(Name('add_one'), [Num('41')])
  Exp(Num('41'))
  SaveReturnAddress(Name('main_cont.3'))
  Exp(FunRef(Name('add_one')))
  Exp(GoTo(Stack(Num('1'))))
main_cont.3:
  RemoveArguments(Num('1'))
  Exp(IN2)
  Assign(IN2, Stack(Num('1')))
  Exp(GoTo(Name('main_epilogue')))
main_epilogue:
  RestoreStackframe()
  RestoreReturnAddress()
```

The `.reti_blocks` output retains labels and pseudoinstructions. Pattern
comments show the operation behind each sequence. Only the machine-specific
`# @picoc-cache` line is omitted:

```reti
  .ivt
  .text
add_one:
  # NewStackframe(Num('0'))
  PUSH BAF
  MOVE SP BAF
  SUBI SP 0
  # Exp(StackframeParam(Num('0')))
  LOADIN BAF ACC 3
  PUSH ACC
  # Exp(Num('1'))
  LOADI ACC 1
  PUSH ACC
  # Exp(BinOp(Stack(Num('2')), Add(), Stack(Num('1'))))
  LOADIN SP ACC 2
  LOADIN SP IN2 1
  ADD ACC IN2
  STOREIN SP ACC 2
  ADDI SP 1
  # Assign(IN2, Stack(Num('1')))
  POP IN2
  # Exp(GoTo(Name('add_one_epilogue')))
  JUMP32 add_one_epilogue
add_one_epilogue:
  # RestoreStackframe()
  MOVE BAF SP
  POP BAF
  # RestoreReturnAddress()
  POP IN1
  MOVE IN1 PC
main:
  # NewStackframe(Num('0'))
  PUSH BAF
  MOVE SP BAF
  SUBI SP 0
  # // Call(Name('add_one'), [Num('41')])
  # Exp(Num('41'))
  LOADI ACC 41
  PUSH ACC
  # SaveReturnAddress(Name('main_cont.3'))
  LOADI32 ACC main_cont.3
  ADD ACC CS
  PUSH ACC
  # Exp(FunRef(Name('add_one')))
  LOADI32 ACC add_one
  ADD ACC CS
  PUSH ACC
  # Exp(GoTo(Stack(Num('1'))))
  POP ACC
  MOVE ACC PC
main_cont.3:
  # RemoveArguments(Num('1'))
  ADDI SP 1
  # Exp(IN2)
  PUSH IN2
  # Assign(IN2, Stack(Num('1')))
  POP IN2
  # Exp(GoTo(Name('main_epilogue')))
  JUMP32 main_epilogue
main_epilogue:
  # RestoreStackframe()
  MOVE BAF SP
  POP BAF
  # RestoreReturnAddress()
  POP IN1
  MOVE IN1 PC
  .data
```

[`NewStackframe`](../PicoC-Compiler/source/picoc_nodes.py#L754) saves `BAF` and reserves locals. The caller pushes a return
address and transfers control. The callee puts its result in `IN2`, restores
its frame, and returns. At `main_cont.3`, the caller removes the argument.
The result survives both cleanup steps in `IN2`.

#### 1.1.3.3 Naked functions without a generated frame
[\[↑ TOC\]](#contents)

`__attribute__((naked))` removes both the compiler-generated stack-frame
prologue and the shared epilogue. `return;` emits no epilogue jump, while
`return expression;` only evaluates the expression and places its value in
`IN2`. A naked function must therefore provide its own register setup and
return or control-transfer sequence.

Here a normal `main` calls a naked function. `constant` supplies its own
return sequence in assembly:

```c
__attribute__((naked))
int constant(void) {
    asm("LOADI IN2 7");
    asm("LOADIN SP ACC 1");
    asm("ADDI SP 1");
    asm("MOVE ACC PC");
}

int main(void) {
    return constant();
}
```

Compile-only mode preserves the complete naked block and its surrounding
sections:

```console
$ picoc_compiler -c -O1 naked-function.picoc
```

```reti
  .ivt
  .text
constant:
  LOADI IN2 7
  LOADIN SP ACC 1
  ADDI SP 1
  MOVE ACC PC
main:
  PUSH BAF
  MOVE SP BAF
  SUBI SP 0
  LOADI32 ACC main_cont.2
  ADD ACC CS
  PUSH ACC
  LOADI32 ACC constant
  ADD ACC CS
  PUSH ACC
  POP ACC
  MOVE ACC PC
main_cont.2:
  PUSH IN2
  POP IN2
  JUMP32 main_epilogue
main_epilogue:
  MOVE BAF SP
  POP BAF
  POP IN1
  MOVE IN1 PC
  .data
```

`constant` begins with its assembly body and has no generated epilogue. Its
last three instructions restore the return address and transfer control.

Compile-only mode needs no `main`. Linking without one emits a warning and
omits the generated `_start`, so the result has no normal entry point. This
example includes `main` so it can run as a complete program.

PicoOS uses naked functions for boot and userspace entry, interrupt handlers,
and dispatcher restoration. Their assembly must match the stack layouts
created by the compiler, hardware, or kernel.

### 1.1.4 Placing globals in `.ivt` with `section("ivt")`
[\[↑ TOC\]](#contents)

The `section` attribute places a global or function in `.ivt`. PicoC accepts
only `"ivt"` as an explicit section name. Ordinary functions use `.text`, and
ordinary globals use `.data`.

These two function-pointer tables contain the same handler. The attribute
places only `ivt_table` in `.ivt`, at the beginning of the linked image:

```c
void handler(void);

__attribute__((section("ivt")))
void (*ivt_table[1])(void) = {handler};

void (*ordinary_table[1])(void) = {handler};

void handler(void) {
}

int main(void) {
    return 0;
}
```

With `-O1`, known initializers become `IVTE` entries rather than startup
stores. Compile-only output retains their labels and sections:

```console
$ picoc_compiler -c -O1 section-placement.picoc
```

The emitted `section-placement.reti_blocks` program body is:

```reti
  .ivt
ivt_table:
  IVTE handler
  .text
handler:
  PUSH BAF
  MOVE SP BAF
  SUBI SP 0
  JUMP32 handler_epilogue
handler_epilogue:
  MOVE BAF SP
  POP BAF
  POP IN1
  MOVE IN1 PC
main:
  PUSH BAF
  MOVE SP BAF
  SUBI SP 0
  LOADI ACC 0
  PUSH ACC
  POP IN2
  JUMP32 main_epilogue
main_epilogue:
  MOVE BAF SP
  POP BAF
  POP IN1
  MOVE IN1 PC
  .data
ordinary_table:
  IVTE handler
```

The tables occupy different sections but point to the same handler. Link
with annotations to see their resolved addresses:

```console
$ picoc_compiler -O1 -v -o section-placement.reti section-placement.picoc
```

The linked excerpt shows both entries and their handler. `# ...` marks
omitted instructions:

```reti
# // Block('ivt_table', [])
2147483668
# ...
# // Block('handler', [])
# NewStackframe(Num('0'))
SUBI SP 1
STOREIN SP BAF 1
MOVE SP BAF
SUBI SP 0
# ...
# // Block('ordinary_table', [])
2147483668
```

Here `handler` begins at image offset `20`. Both `IVTE` entries become
`0x80000014`, the SRAM base plus that offset. With a one-word `.ivt`, `CS` is
`SRAM_BASE + 1`, so the handler is also at `CS + 19`. `IVTE` creates pointers
for an image loaded at the SRAM base. It does not relocate them to an
arbitrary process-image address.

### 1.1.5 Selecting a startup function with `-C` / `--startup-source`
[\[↑ TOC\]](#contents)

A linked program can use the generated entry point or a custom startup
source. PicoOS supplies its own entry for each kind of image.

#### 1.1.5.1 Default compiler-generated `_start`
[\[↑ TOC\]](#contents)

Without a custom entry, the compiler generates [`_start`](../PicoC-Compiler/source/option_handler.py#L834) for a program with
`main`. The generated entry runs any remaining global initializer code before
calling `main`. After `main` returns, the compiler translates its internal
[`Exit(0)`](../PicoC-Compiler/source/picoc_nodes.py#L263) operation into `LOADI ACC 0`
and `JUMP 0`, as implemented in [`reti_blocks_pass.py`](../PicoC-Compiler/source/passes/compilation/reti_blocks_pass.py#L348).
This source-equivalent example shows those instructions as inline assembly:

```c
void _start(void) {
    main();
    asm("LOADI ACC 0");
    asm("JUMP 0");
}
```

`LOADI ACC 0` writes zero into `ACC`, regardless of the return value of `main`.
`JUMP 0` is a relative jump with an offset of zero, so it points to itself.
The emulator recognizes it as a stop instruction and
[ends execution](../RETI-Emulator/source/interpr.c#L529).

#### 1.1.5.2 PicoOS `libstart` startup sequence
[\[↑ TOC\]](#contents)

`-C PATH` or `--startup-source PATH` links a startup source or `.reti_blocks`
file. If it defines [`_start()`](library/start/start.picoc#L14), that function becomes the first in `.text`.
Otherwise the compiler generates the default entry. Any remaining global
initializers run before either entry body.

PicoOS selects [`library/start/libstart.picoc`](library/start/libstart.picoc)
for userspace with `-C library/start/libstart.picoc`. The wrapper records its
compiled-library dependency and includes the actual startup implementation:

```c
// dependencies: ../stdlib/libstdlib.reti_blocks

#include "start.picoc"
```

The included [`library/start/start.picoc`](library/start/start.picoc) contains
the complete userspace startup path:

```c
#include "../stdlib/stdlib.header"
#include "../unistd/unistd.header"

int main(int argc, char **argv);
void initialize_environment(char **environment);

void start_process(int argc, char **argv) {
    init_process_heap();
    initialize_environment(argv + argc + 1);
    exit(main(argc, argv));
}

__attribute__((naked))
void _start(int argc, char *first_argument) {
    start_process(argc, (char **)&first_argument);
}
```

The naked [`_start()`](library/start/start.picoc#L14) reads the stack built by the kernel and passes [`argv`](kernel/process/process_arguments.picoc#L140)
to [`start_process()`](library/start/start.picoc#L7). That helper initializes the heap and environment, calls
[`main()`](library/start/start.picoc#L4), and sends its return value to [`exit()`](library/stdlib/exit.picoc#L3). Like the startup support
supplied with `libc`, [`libstart`](library/start/libstart.picoc) prepares the runtime before the application
runs. [`4.2.2.1 Initial user process stack`](#4221-initial-user-process-stack) shows the initial stack.

#### 1.1.5.3 Startup functions used by PicoOS images
[\[↑ TOC\]](#contents)

The table identifies each image's entry point. Init, the shell, and other
applications share `libstart`. [`11. Complete startup: bootloader, kernel, init, shell, and user applications`](#11-complete-startup-bootloader-kernel-init-shell-and-user-applications) follows them through boot and startup.

| Image | `_start` used | Next function |
| --- | --- | --- |
| EPROM bootloader | Its explicitly defined naked [`_start()`](boot/bootloader.picoc#L9), compiled as part of the bootloader without `-C` | [`boot_main()`](boot/bootloader.picoc#L41) |
| SRAM kernel | Compiler-generated default `_start`, because the kernel is linked without `-C` | [`main()`](kernel/kernel.picoc#L31) |
| Init process | [`libstart` `_start()`](library/start/start.picoc#L14), selected with `-C library/start/libstart.picoc` | [`main()`](system/init.picoc#L100) |
| Shell | [`libstart` `_start()`](library/start/start.picoc#L14), selected with the same `-C` option | [`main()`](user/shell.picoc#L1448) |
| User applications | [`libstart` `_start()`](library/start/start.picoc#L14), selected by the common userspace link rule | The application's `main` |

### 1.1.6 Program sections, interrupt table entries, and linker placement
[\[↑ TOC\]](#contents)

The linker orders each flat RETI image as `.ivt`, `.text`, then `.data`.
These are regions within one program. The table shows what goes into them:

| Section | Default contents and addressing | How source selects it |
| --- | --- | --- |
| `.ivt` | interrupt service routines words and, when requested, low-level functions, it begins at image offset 0 and uses `CS`-relative global references | Add `__attribute__((section("ivt")))` to a global variable, function declaration, or function definition |
| `.text` | `_start` followed by ordinary functions and their instructions, execution and code labels are relative to `CS` | This is the default for functions |
| `.data` | Ordinary global storage, addressed relative to `DS` | This is the default for global variables |

With `-O1`, known global initializers become words in `.data` or the selected
`.ivt`. Runtime-dependent initializers still execute at startup. The kernel
uses this for its five [`interrupt_vector_table`](interrupt_service_routines/os_isrs.picoc#L23) pointers, which must be
available immediately after loading. [`1.1.4 Placing globals in .ivt with section("ivt")`](#114-placing-globals-in-ivt-with-sectionivt) demonstrates placement, and [`2.1 RETI interrupt entry and the interrupt service routine table`](#21-reti-interrupt-entry-and-the-interrupt-service-routine-table)
shows the complete table and interrupt entry.

<!-- Presentation: Show the interrupt_vector_table PicoC code example from
2.1 RETI interrupt entry and the interrupt service routine table here, rather than
showing only the README cross-reference. -->

Linked labels let inline assembly call C helpers after final placement.
Those helpers follow the stack-frame rules in [`1.1.3 System V ABI stack frames and call cleanup`](#113-system-v-abi-stack-frames-and-call-cleanup).

### 1.1.7 RETI pseudoinstructions
[\[↑ TOC\]](#contents)

RETI has no native stack instructions, and its immediate values and relative
jumps are limited to 22 bits. The compiler provides these pseudoinstructions
and expands them into hardware instructions during linking:

| Pseudoinstruction | Purpose | Concrete size |
| --- | --- | ---: |
| `PUSH reg` | Reserves one stack cell and stores `reg` in it | 2 instructions |
| `POP reg` | Loads the top stack cell into `reg` and releases it | 2 instructions |
| `LOADI32 reg operand` | Loads a 32-bit literal, linked symbol, or `symbol +/- offset` | 3 instructions |
| `JUMP32[relation] target` | Jumps to an immediate address or linked code label without the normal jump-range limit | 4--6 instructions when retained |

`JUMP32` is unconditional unless followed by a relation such as `==` or `<`.
Conditions compare `ACC` with zero. Numeric operands are accepted directly,
while symbols are resolved after all files and sections have been combined.

#### 1.1.7.1 Interrupt-safe `PUSH` and `POP`
[\[↑ TOC\]](#contents)

`SP` points to the free cell below the occupied stack. `PUSH` reserves a cell
before writing it, and `POP` reads a cell before releasing it:

| Pseudoinstruction | Expansion |
| --- | --- |
| `PUSH ACC` | `SUBI SP 1`<br>`STOREIN SP ACC 1` |
| `POP ACC` | `LOADIN SP ACC 1`<br>`ADDI SP 1` |

Starting with `SP = p`, a push first sets `SP = p - 1`, then stores at `p`.
An intervening interrupt therefore uses the next free cell rather than
overwriting the pushed value. A pop reads `p + 1` before increasing `SP`,
keeping that value protected until it has been read.

The compiler uses these operations for arguments, return addresses, and
saved `BAF`. PicoOS also uses them in naked functions, for example to save
registers in an ISR:

```c
asm("PUSH ACC");
asm("PUSH IN1");
/* Handle the interrupt */
asm("POP IN1");
asm("POP ACC");
```

#### 1.1.7.2 Loading 32-bit values with `LOADI32`
[\[↑ TOC\]](#contents)

`LOADI32` builds a 32-bit value from a signed 22-bit immediate. The compiler
splits the value into the upper 22 bits and the lower ten bits.

Write the original bits as $b_{31},\ldots,b_0$. The upper field is interpreted
as a signed two's-complement number, with its own sign bit at position `21`
(original bit `31`):

$$
\mathrm{signed\_upper} = -b_{31}2^{21} + \sum_{j=0}^{20} b_{j+10}2^j,
\qquad
\mathrm{lower\_bits} = \sum_{j=0}^{9} b_j2^j.
$$

If bit `21` of `unsigned_upper` is set, subtract `2^22` to obtain its signed
representation. Otherwise keep it unchanged. The result fits the signed
22-bit range. The linker emits:

```reti
LOADI reg signed_upper
MULTI reg 1024
ORI reg lower_bits
```

The emulator sign-extends the `LOADI` immediate to 32 bits. Multiplication by
`1024 = 2^10` moves the upper contribution into bits `31..10` and clears the
ten low bits. `ORI` then inserts `lower_bits` into those low bits, reconstructing
the original word. For `0x80000005`, `unsigned_upper = 2097152`,
`signed_upper = -2097152`, and `lower_bits = 5`:

```reti
LOADI ACC -2097152
MULTI ACC 1024
ORI ACC 5
```

This also explains the tagged SRAM base `0x80000000`, represented in PicoC as
`-2147483648`. Code labels are resolved relative to `CS`, so an absolute code
address requires adding `CS` afterward. The bootloader uses this pattern:

```c
asm("LOADI32 ACC start_loaded_kernel");
asm("ADD ACC CS");
asm("MOVE ACC PC");
```

The same pseudoinstruction loads absolute segment and stack values from the
generated [kernel](kernel/memory_constants.header) and
[bootloader](boot/memory_constants.header) headers and constructs function
addresses and continuation addresses.

Signed and unsigned interpretations of the same operands produce identical
low 32 product bits. Their high bits can differ. The
[RISC-V multiplication specification](https://docs.riscv.org/reference/isa/v20240411/unpriv/m-st-ext.html#_multiplication_operations)
uses one low-product instruction and separate high-product instructions for
that reason.

For this particular 22-bit field, `unsigned_upper` and `signed_upper` are equal
when bit `21` is zero. Otherwise,
$\mathrm{unsigned\_upper}-\mathrm{signed\_upper}=2^{22}$, so

$$
\mathrm{unsigned\_upper}\,2^{10} - \mathrm{signed\_upper}\,2^{10} = 2^{32}.
$$

The products differ by `2^32`, so either reconstructs the same word under
modulo arithmetic. The current assembler requires a signed 22-bit `LOADI`
operand, however, and rejects `2097152`. The conversion is needed for that
interface.

The emulator multiplies signed `int32_t` values. `signed_upper * 1024` stays
within their range. Using the unsigned upper value would require unsigned or
explicit modulo arithmetic. Overflowing signed multiplication in C is
[undefined](https://open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf#page=94), even when the desired low bits are known.

#### 1.1.7.3 Long jumps with `JUMP32`
[\[↑ TOC\]](#contents)

`JUMP32` reaches beyond the hardware's signed 22-bit relative range. For a
symbolic target, it builds the target's `CS`-relative address in `ACC`, adds
`CS`, and moves the result to `PC`. The bit split follows [`1.1.7.2 Loading 32-bit values with LOADI32`](#1172-loading-32-bit-values-with-loadi32):

```reti
LOADI ACC signed_upper
MULTI ACC 1024
ORI ACC lower_bits
ADD ACC CS
MOVE ACC PC
```

A numeric target is treated as an absolute address, so its expansion omits
`ADD ACC CS` and contains four instructions. A conditional form first emits a
short jump with the opposite relation to skip over the long-jump sequence when
the condition is false. It is therefore one instruction longer: six
instructions for a symbolic target and five for an immediate target.

Long jumps use `ACC` as scratch space, so function results stay in `IN2`.
The compiler uses `JUMP32` for ordinary control flow, and naked functions can
use it in inline assembly.

#### 1.1.7.4 Pseudoinstruction expansion during linking
[\[↑ TOC\]](#contents)

Linking separates instruction counting from address resolution. [`reti_patch`](../PicoC-Compiler/source/passes/linking/reti_patch_pass.py)
expands `PUSH` and `POP`, patches large numeric immediates, and removes jumps
to the immediately following block.

It then records block positions using each pseudoinstruction's expanded
size. `LOADI32` counts as three instructions, symbolic `JUMP32` as five, and
numeric `JUMP32` as four. A condition adds one instruction. Comments count
as zero.

This strip shows why expanded sizes matter. The address of `done` depends
on both preceding blocks:

![Expanded code blocks and the jump to done](documentation/images/pseudoinstruction-blocks.svg)

| Block | Symbolic instructions | Real instructions after expansion |
| --- | --- | ---: |
| `entry` | `PUSH BAF`, `LOADI32 ACC done`, `JUMP32 done` | `2 + 3 + 5 = 10` |
| `work` | `PUSH ACC`, `POP IN1`, `LOADI32 ACC 7` | `2 + 2 + 3 = 7` |
| `done` | `POP BAF` | `2` |

Here `done` begins at offset `10 + 7 = 17`. The symbolic `JUMP32` loads `17`
into `ACC` and adds `CS`. Counting each pseudoinstruction as just one word
would instead place `done` at offset `6`, producing the wrong target.

The final [`reti`](../PicoC-Compiler/source/passes/linking/reti_pass.py) pass resolves labels and expands `LOADI32` and `JUMP32`.
Counting their sizes first avoids needing a target address before the
preceding blocks have been laid out. Numeric forms use the same expansion
path for consistency.

`PUSH` and `POP` can expand earlier because their operands do not depend on
labels. Inline assembly follows the same rules. The emulator receives only
concrete instructions.

### 1.1.8 Linked `.sections` metadata and the five-word binary header
[\[↑ TOC\]](#contents)

A completed link emits [`program.reti`](../PicoC-Compiler/source/passes/linking/reti_pass.py) and `program.sections`. The latter
records the image layout used for loading and segment, heap, and stack setup.
A typical userspace file looks like this:

```json
{
  "codesegment_start": 0,
  "datasegment_start": 11595,
  "heap_start": 11621,
  "heap_size": 2000,
  "stack_start": 14621
}
```

These entries determine the runtime addresses. Userspace images need not
have an ISR entry:

| Entry | Meaning |
| --- | --- |
| `interrupt_service_routines_start` | Optional start of separately identified ISR code when the linked image contains it |
| `codesegment_start` | Process-relative start loaded into `CS`, for a normal userspace image this is also its initial entry region |
| `datasegment_start` | Process-relative start loaded into `DS` |
| [`heap_start`](kernel/process/process.header#L36) | First cell after static data and first cell managed by the process-local heap |
| [`heap_size`](kernel/process/process.header#L37) | Heap capacity in RETI cells, `-1` requests PicoOS's default |
| [`stack_start`](kernel/process/process_loader.picoc#L121) | Highest process-relative stack cell, `-1` requests the kernel's default placement |

The compiler creates this file only at the final link. A compile-only `-c`
invocation instead creates reusable `.reti_blocks` and `.st` files because no
complete program layout exists yet.

The final [`reti()`](../PicoC-Compiler/source/passes/linking/reti_pass.py#L311)
pass calculates the offsets from the linked `.ivt`, `.text`, and `.data`
sections. [`_entries_size()`](../PicoC-Compiler/source/passes/linking/reti_pass.py#L271)
counts the emitted RETI words, ignoring comments. The global-data extent is
the greatest offset-plus-size value among global data symbols, calculated by
[`_data_segment_symbol_size()`](../PicoC-Compiler/source/passes/linking/reti_pass.py#L274).
Taking the larger data size ensures that the heap begins after all static
storage, including storage represented by symbol metadata rather than emitted
data words. The default metadata is calculated as follows:

| Entry | Default value |
| --- | --- |
| `codesegment_start` | $\text{words in .ivt}$ |
| `datasegment_start` | $\text{words in .ivt} + \text{words in .text}$ |
| `heap_start` | $\texttt{datasegment\_start} + \max(\text{words in .data}, \text{global-data extent})$ |
| `heap_size` | $-1$ |
| `stack_start` | $-1$ |

Normal userspace images have no `.ivt` words, so their code starts at offset
0. When both `--heap-size CELLS` and `--stack-size CELLS` are supplied,
[`_apply_memory_sizes()`](../PicoC-Compiler/source/option_handler.py#L1195)
replaces the two `-1` defaults with the requested heap size and
`stack_start = heap_start + heap_size + stack_size`. These values describe
RETI cell offsets and counts within the Process Payload, not file byte offsets.

Run `reti_emulator -a program.reti` to assemble a loadable binary. It reads
the matching `.sections` file and prepends five big-endian layout words through
[`assemble_sram_program_to_binary()`](../RETI-Emulator/source/reti_emulator_main.c#L107).
`-S PATH` selects another metadata file. The diagram shows both inputs:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart TB
    RETI["program.reti<br/>linked RETI instructions and data"] --> ASSEMBLE["reti_emulator -a program.reti"]
    SECTIONS["program.sections<br/>linked layout metadata"] -->|automatically found beside program.reti| ASSEMBLE
    ASSEMBLE --> BIN["program.bin<br/>five-word big-endian layout header<br/>encoded RETI instructions + data words"]
```

For example, with the `.sections` values above, assembling an illustrative
[`program.reti`](../PicoC-Compiler/source/passes/linking/reti_pass.py) produces this five-word header:

```console
$ reti_emulator -a program.reti
$ hexyl -n 20 program.bin
┌────────┬─────────────────────────┬─────────────────────────┬────────┬────────┐
│00000000│ 00 00 00 00 00 00 2d 4b ┊ 00 00 2d 65 00 00 07 d0 │......-K┊..-e....│
│00000010│ 00 00 39 1d             ┊                         │..9.    ┊        │
└────────┴─────────────────────────┴─────────────────────────┴────────┴────────┘
```

These first 20 bytes encode the five displayed layout values. The appendix
shows how to inspect other ranges.

The header contains no field names. The assembler writes values in a fixed
order, and the loaders identify them by their position. Each word occupies
four bytes, so the five reads consume file bytes 0 through 19:

| Word | File byte offset | Value | Use in PicoOS |
| ---: | ---: | --- | --- |
| 0 | 0 | [`codesegment_start`](../PicoC-Compiler/source/passes/linking/reti_pass.py#L345) | Stored in [`ProcessLoad.code_start`](kernel/process/process_loader.picoc#L17), then added to [`base_address`](kernel/process/process.header#L34) for [`activation.cs`](kernel/process/process.header#L27) by [`create_process()`](kernel/process/process.picoc#L89) |
| 1 | 4 | [`datasegment_start`](../PicoC-Compiler/source/passes/linking/reti_pass.py#L346) | Stored in [`ProcessLoad.data_start`](kernel/process/process_loader.picoc#L18), then added to [`base_address`](kernel/process/process.header#L34) for [`activation.ds`](kernel/process/process.header#L28) by [`create_process()`](kernel/process/process.picoc#L89) |
| 2 | 8 | [`heap_start`](kernel/process/process.header#L36) | Process-relative start of the User Process Heap, passed through [`ProcessLoad.heap_start`](kernel/process/process_loader.picoc#L19) to [`create_process()`](kernel/process/process.picoc#L89) |
| 3 | 12 | [`heap_size`](kernel/process/process.header#L37) | Resolved by [`begin_process_load()`](kernel/process/process_loader.picoc#L109), which substitutes [`DEFAULT_PROCESS_HEAP_CELLS`](kernel/process/process_loader.header#L6) for `-1`, then stores [`ProcessLoad.heap_size`](kernel/process/process_loader.picoc#L20) |
| 4 | 16 | [`stack_start`](kernel/process/process_loader.picoc#L121) | Resolved by [`loaded_process_stack_start()`](kernel/process/process_loader.picoc#L28) to the highest stack offset. Adding one gives [`ProcessLoad.process_size`](kernel/process/process_loader.picoc#L16), later stored as PCB [`size`](kernel/process/process.header#L35) |

[`begin_process_load()`](kernel/process/process_loader.picoc#L109) requests
`read-range 0 20`, consumes the response's byte count, and then calls
[`receive_word()`](common/uart_protocol.picoc#L7) five times in the table's order.
Each call combines four UART bytes as a signed big-endian 32-bit value.
Thus `ff ff ff ff` becomes `-1`, the heap and stack default marker.
[`4.2.2.1.1 User process stack placement`](#42211-user-process-stack-placement)
explains how the defaults determine the reservation.

The bootloader receives a word count followed by the header and payload
through the [`load`](#123-uart-host-service-protocol) host request. The process loader uses `file-size` and
`read-range`. Both consume the header and copy only the payload to SRAM.
[`load_process()`](kernel/process/process_loader.picoc#L305) consumes its response's
word count before reading the same five fields. The [`bootloader`](boot/bootloader.picoc#L41)
also reads them in order, but discards the two heap fields because the kernel
uses [`kernel/memory_constants.header`](kernel/memory_constants.header).
A Process Payload also reserves space for its heap and stack. [`4.2.1 Loading a process (load library call)`](#421-loading-a-process-load-library-call) follows
the loading paths.

### 1.1.9 Generated memory constants for the bootloader and kernel
[\[↑ TOC\]](#contents)

The kernel and bootloader need memory constants before runtime loading can
supply them. `-k sram` generates [`kernel/memory_constants.header`](kernel/memory_constants.header), and
`-k eprom` generates [`boot/memory_constants.header`](boot/memory_constants.header). This invocation writes
only the header, named [`memory_constants.header`](kernel/memory_constants.header) in the `-o` directory. A
subsequent compile includes it to build the executable.

The current kernel header is shown below. Its values come from the linked
kernel layout with a 4,096-cell heap and a 2,715-cell stack:

```c
#define SRAM_BASE (-2147483647 - 1) // -2^31
#define SRAM_MAX_ADDRESS_IN_MEMORY_MAP -2147221505 // -2^31 + 2^18 - 1
#define KERNEL_HEAP_START -2147442162 // -2^31 + heap_start
#define KERNEL_HEAP_SIZE 4096 // heap_size
#define PROCESS_MEMORY_START -2147435350 // -2^31 + stack_start + 1
#define KERNEL_CS_START_ASM "LOADI32 CS -2147483643" // -2^31 + codesegment_start
#define KERNEL_DS_START_ASM "LOADI32 DS -2147442893" // -2^31 + datasegment_start
#define KERNEL_SP_START_ASM "LOADI32 SP -2147435351" // -2^31 + stack_start
#define KERNEL_CS_ACC_ASM "LOADI32 ACC -2147483643" // -2^31 + codesegment_start
```

The table connects these constants to the state they initialize or restore.

| Kernel constant | Consumer and purpose |
| --- | --- |
| [`SRAM_BASE`](kernel/memory_constants.header#L1) | Converts process-relative linked addresses to the absolute SRAM address space |
| [`SRAM_MAX_ADDRESS_IN_MEMORY_MAP`](kernel/memory_constants.header#L2) | Inclusive final configured SRAM cell, bounds the Process and Shared Data Heap |
| [`KERNEL_HEAP_START`](kernel/memory_constants.header#L3), [`KERNEL_HEAP_SIZE`](kernel/memory_constants.header#L4) | Initialize the global [`kernel_heap`](kernel/kmalloc.picoc#L7) descriptor and define its stack boundary |
| [`PROCESS_MEMORY_START`](kernel/memory_constants.header#L5) | First cell managed by the global [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7) for Process Payloads and Shared Data Payloads |
| [`KERNEL_CS_START_ASM`](kernel/memory_constants.header#L6), [`KERNEL_DS_START_ASM`](kernel/memory_constants.header#L7) | Inline assembly fragments used when interrupt entries install kernel segments |
| [`KERNEL_SP_START_ASM`](kernel/memory_constants.header#L8) | Inline assembly fragment that installs the linked kernel stack start |
| [`KERNEL_CS_ACC_ASM`](kernel/memory_constants.header#L9) | Generated fragment for loading the kernel code base into `ACC`, currently unused by PicoOS source |

The current bootloader header establishes the temporary context before the
kernel image supplies its own segment and stack values. The code shows the
generated format, and the following table explains its three constants:

```c
#define SRAM_MAX_ADDRESS 262143 // 2^18 - 1
#define EPROM_DS_START_ASM "LOADI32 DS 3165" // datasegment_start
#define EPROM_STACK_START_ASM "LOADI32 SP -2147221505" // -2^31 + 2^18 - 1
```

| Bootloader constant | Consumer and purpose |
| --- | --- |
| [`SRAM_MAX_ADDRESS`](boot/memory_constants.header#L1) | Final physical SRAM offset, fallback kernel stack offset when the loaded header contains -1 |
| [`EPROM_DS_START_ASM`](boot/memory_constants.header#L2) | Loads the bootloader's linked EPROM data segment |
| [`EPROM_STACK_START_ASM`](boot/memory_constants.header#L3) | Loads the absolute top-of-SRAM temporary stack |

The kernel header and `.sections` describe the same linked layout. The
header adds [`SRAM_BASE`](kernel/memory_constants.header#L1) for absolute addresses. `.sections` retains relative
offsets. The bootloader uses its own header at entry, then reads the kernel
binary's header to establish the kernel context.

[`2.4.2 System-call entry, execution, and return to userspace`](#242-system-call-entry-execution-and-return-to-userspace) shows these constants installing kernel registers. [`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy) locates the
heap and stack, and [`6.4 Restoring the selected process and returning with RTI`](#64-restoring-the-selected-process-and-returning-with-rti) shows the dispatcher restoring process registers.

## 1.2 RETI-Emulator extensions
[\[↑ TOC\]](#contents)

The emulator assembles the compiler's output, runs RETI, and provides the
devices and host services PicoOS uses. These are its relevant extensions:

| Feature | Contribution used by PicoOS |
| --- | --- |
| Plain execution output | Without the debugger, completed UART output is written directly to host stdout |
| Commented assembly | Debug mode can show source-derived labels and comments beside instructions |
| Atomic locking | `TSL` atomically returns a cell's old value and stores `1`, supporting the mutex library |
| Structured loading | `.sections` distinguishes the interrupt service routine table, ISR code, `.text`, `.data`, heap, and stack |
| Binary assembly | `--assemble program.reti` combines RETI words with the five layout header words in `program.bin` |
| EPROM-only boot | `-e boot/bootloader.reti` starts CPU execution at the EPROM bootloader without preloading a program into SRAM |
| Configurable SRAM | PicoOS selects 262,144 physical 32-bit cells while retaining the RETI tagged address space |
| Memory-mapped periphery | UART, device mappings, priorities, timer interval, stack boundary, exception cause, and optional DMA occupy offsets 0–16 |
| Interrupt controller | Timer, DMA through the custom device line, and UART have configurable ISR mappings, priorities, pending state, and nesting behavior |
| Direct memory access | Optional DMA copies UART words into SRAM for kernel, init, and later program loading, scheduled loads receive a completion interrupt |
| Manual interrupts | The TUI can select and trigger an interrupt service routines for inspection |
| Runtime timer | An instruction-count interval produces repeatable userspace preemption and exposes the live counter in the TUI |
| Raw-byte UART | Receive/send registers and status bits model byte delivery rather than line-oriented console input |
| UART host services | The emulator parses bounded load, read, file-size, output, directory, and removal requests from the byte stream |
| Normal and raw terminals | The normal view preserves host signal processing, raw mode forwards control and escape bytes needed by the shell |
| CPU exceptions | Divide by zero, stack overflow, and illegal instructions enter interrupt service routine table entry 3 and expose a cause value |
| Stack/heap protection | The active inclusive boundary is checked whenever an instruction attempts to decrease `SP` |
| Runtime segment interpretation | Code/data/watch views follow live `CS` and `DS` after bootloading and context switches |
| Source-level debugging | `.debuginfo` and preprocessed source provide globals, locals, arguments, calls, frames, and source positions |
| SRAM transcoding | Memory can be viewed as numbers, characters, or decoded instructions without losing known-code regions |
| Snapshots and restart | Complete CPU, memory, interrupt, UART, and peripheral state can be saved, restored repeatedly, or restarted |
| Live inspection/editing | Windows can be selected, scrolled, centered, and edited while inspecting registers or memory |
| Synthetic OS context | The initial debugger state can model the kernel/interrupt context needed before PicoOS's first `RTI` |
| Explicit ISR table size | The emulator can reserve the five-entry IVT before the bootloader populates SRAM |
| Isolated assembly runs | The repository wrapper keeps assembler processes from overwriting peripheral files belonging to an active OS instance |

### 1.2.1 RETI machine model and memory-mapped peripherals
[\[↑ TOC\]](#contents)

PicoOS accesses devices through ordinary loads, stores, and interrupt
service routines. Periphery cell `n` is at `0x40000000 + n`. SRAM begins at
`0x80000000`.

The emulator documentation calls the `01` region **periphery**. The map
places this region between EPROM and SRAM:

![RETI address space with periphery between EPROM and SRAM](documentation/images/reti-periphery-memory-map.svg)

The address-space table distinguishes implemented registers from unused
addresses:

| Address range | Top-bit prefix | RETI region | Implemented PicoOS use |
| --- | --- | --- | --- |
| `0x00000000..0x3fffffff` | `00` | EPROM | Bootloader code and data |
| **`0x40000000..0x7fffffff`** | **`01`** | **Periphery** | **Offsets `0..16`, through `0x40000010`, are implemented memory-mapped registers** |
| `0x80000000..0xffffffff` | `10` or `11` | SRAM | Kernel image, process images, heaps, stacks, and shared data |

Older maps called the middle region the UART area. UART still occupies
cells 0–2, but the other peripherals now extend through cell 16. The table
lists the implemented registers:

| Offset | Register | Access and connection to PicoOS |
| ---: | --- | --- |
| 0 | UART send | Kernel/bootloader write the low byte and clear send-ready in offset 2 |
| 1 | UART receive | Emulator writes an incoming byte, polling code or UART ISR reads it |
| 2 | UART status | Bit 0 reports send-ready and bit 1 receive-ready |
| 3–5 | Device-to-ISR mappings | Timer, custom device, and UART select IVT indices, 255 disables a line |
| 6–8 | Device priorities | Interrupt controller selects the highest-priority pending device |
| 9 | Timer interval | Instruction-count period, zero disables and a write restarts the counter |
| 10 | Stack/heap boundary | Inclusive active lower stack limit, dispatcher rewrites it on every context switch |
| 11 | CPU exception cause | Read-only: none, divide by zero, stack overflow, or illegal instruction |
| 12 | DMA active | Always present, `1` enables DMA and exposes offsets 13–16 |
| 13 | DMA source | Absolute UART receive address used by PicoOS |
| 14 | DMA destination | Absolute SRAM destination address |
| 15 | DMA word count | Number of complete 32-bit words to copy |
| 16 | DMA status/control | `0` idle, write/read `1` for start/busy, `2` complete, `3` error |

CPU exceptions enter service routine 3 directly. Startup configures the
timer, DMA, and UART mappings. The dispatcher writes each process's
`base_address + heap_start + heap_size - 1` to cell 10 as its stack boundary.

### 1.2.2 Atomic test-and-set with `TSL`
[\[↑ TOC\]](#contents)

`TSL S D i` atomically tests and sets a memory cell. It saves address `S + i`,
reads the old value into `D`, and writes `1` to that address. No interrupt or
process switch can occur between the read and write.

#### 1.2.2.1 Test-and-set in SRAM
[\[↑ TOC\]](#contents)

The example uses a non-zero offset to distinguish the base from the target.
`DS = 0x80000040`, so `DS + 2 = 0x80000042` selects the third SRAM cell:

```reti
# Before: M[DS + 2] = 0
TSL DS ACC 2
# After:  ACC = 0 and M[DS + 2] = 1
```

The diagram shows four adjacent SRAM cells and the target at `DS + 2`
changing from `0` to `1`. Addresses count 32-bit words, so offset `2` advances
two cells, not two bytes:

![TSL DS ACC 2 accessing adjacent SRAM word cells with the target changing from 0 to 1](documentation/images/tsl-memory-layout.svg)

`D` receives the exact old word, including values other than `0` and `1`.
Saving the address first lets `S` and `D` be the same register. Writing to
`SP` can fail stack protection before the store, and writing to `PC` changes
control flow. The example uses `ACC`, avoiding those special cases.

#### 1.2.2.2 `TSL` instruction encoding
[\[↑ TOC\]](#contents)

`TSL` occupies mode `10` of RETI's Store, Move category. These fields encode
`TSL DS ACC 2`:

![TSL DS ACC 2 instruction fields](documentation/images/tsl-instruction-format.svg)

The complete machine word is `0xAEC00002`. The immediate field `i` is a signed
22-bit displacement, here `+2`.

The register fields have different roles in neighboring modes. Here `S` is
the address base and `D` receives the old value:

| Type | Mode `M` | Assembly syntax | Operation |
| --- | --- | --- | --- |
| `10` | `00` | `STORE S i` | Store register `S` at the direct, DS-completed address |
| `10` | `01` | `STOREIN D S i` | Store register `S` at address `D + i` |
| `10` | `10` | `TSL S D i` | Return `M[S + i]` in `D`, then set that cell to `1` |
| `10` | `11` | `MOVE S D` | Copy register `S` to register `D` |

[`testset(lock_addr)`](library/mutex/mutex.picoc#L3) uses `TSL` with the lock address in `IN2`. [`mutex_lock(m)`](library/mutex/mutex.picoc#L18)
uses the old value to decide whether it acquired the lock. [`7.3 Mutexes with test-and-set and wait queues`](#73-mutexes-with-test-and-set-and-wait-queues) explains the
retry and wait-queue behavior, including its lost-wakeup limitation.

### 1.2.3 UART host-service protocol
[\[↑ TOC\]](#contents)

On hardware, a host program serves PicoOS filesystem and terminal requests
over the USB-to-UART connection. The diagram follows requests and responses
through that connection:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    UART["RETI UART controller"] <-->|"UART bytes<br/>host requests / responses"| ADAPTER["UART-to-USB adapter"]
    ADAPTER <-->|"USB connection<br/>host requests / responses"| SERVICE
    subgraph HOST["Host operating system"]
        SERVICE["Dedicated host-side service software<br/>interpret escape-sequence requests"]
        TERMINAL["Terminal"]
        FILES["Sandboxed host filesystem"]
        SERVICE -->|normal UART output| TERMINAL
        SERVICE -->|"host request: mkdir, touch, write, ..."| FILES
        FILES -->|data or result for host response| SERVICE
    end
```

During development, the emulator models UART and serves those requests
directly:

```mermaid
%%{init: {"flowchart":{"nodeSpacing":20,"rankSpacing":45,"wrappingWidth":300},"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    subgraph HOST["Host operating system"]
        direction LR
        subgraph EMU["RETI-Emulator"]
            direction LR
            GUEST["PicoOS on<br/>emulated RETI"]
            UART["Emulated UART<br/>controller"]
            SERVICE["Built-in<br/>host-service parser"]
            GUEST <-->|UART send / receive bytes| UART
            UART <-->|host requests / responses| SERVICE
        end
        SERVICE -->|normal UART output| TERMINAL["Host terminal<br/>launches the emulator"]
        SERVICE -->|sandboxed filesystem operation| FILES["Sandboxed host filesystem<br/>Launch directory = PicoOS /"]
        FILES -->|data or result| SERVICE
    end
```

The emulator's [`guest_filesystem.c`](../RETI-Emulator/source/guest_filesystem.c) uses its launch directory as PicoOS `/`.
It normalizes `..` within that root and blocks symbolic-link escapes. Host
requests read, create, and modify files within this sandbox.

Requests have the form `<ESC>operation arguments<ESC>/`, with escape byte
27. Ordinary bytes go to the terminal or selected output file. The table
lists each request and response:

| Request form | Result |
| --- | --- |
| `<ESC>load <path><ESC>/` | Big-endian word count followed by binary bytes, used by the bootloader |
| `<ESC>read-range <offset> <count> <path><ESC>/` | Returned byte count followed by that file range |
| `<ESC>file-size <path><ESC>/` | File size as one 32-bit value |
| `<ESC>write <path><ESC>/` | Create/truncate a file and route following UART bytes to it |
| `<ESC>write-at <offset> <path><ESC>/` | Preserve a file and route following UART bytes to the byte offset |
| `<ESC>write stdout<ESC>/` / [`stderr`](library/stdio/stdio.header#L11) | Restore a host standard output stream |
| `<ESC>literal-output <count><ESC>/` | Treat exactly the next `count` UART bytes as output data, even when they contain `<ESC>` |
| `<ESC>pwd<ESC>/` | PicoOS root `/` as a length-prefixed string |
| `<ESC>is-directory <path><ESC>/` | Directory test |
| `<ESC>mkdir <path><ESC>/` | Create a directory |
| `<ESC>ls <path><ESC>/` | Length-prefixed directory listing |
| `<ESC>unlink <path><ESC>/` | Remove a file |
| `<ESC>rmdir <path><ESC>/` | Remove an empty directory |
| `<ESC>move <old path>\n<new path><ESC>/` | Move or rename a file or directory |
| `<ESC>touch <path><ESC>/` | Create a file or update its timestamps |

The protocol provides fixed filesystem operations. Debugger commands are
separate and inspect the emulated machine.

Replies arrive on the same UART stream. A [`load`](#123-uart-host-service-protocol) response contains a word
count followed by file bytes. `ESC` below means byte 27:

```mermaid
%%{init: {"sequence":{"wrap":false,"actorMargin":60,"width":180,"height":45,"messageMargin":25,"mirrorActors":false,"diagramMarginY":35},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }","theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"}}}%%
sequenceDiagram
    participant P as PicoOS loader
    participant H as RETI-Emulator host

    P->>H: ESC load path ESC /
    H-->>P: total word count (big-endian 32-bit)
    H-->>P: complete file payload
```

Ranged reads return a byte count and payload. Metadata and status requests
return one big-endian value:

```mermaid
%%{init: {"sequence":{"wrap":false,"actorMargin":60,"width":180,"height":45,"messageMargin":25,"mirrorActors":false,"diagramMarginY":35},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }","theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"}}}%%
sequenceDiagram
    participant P as PicoOS
    participant H as RETI-Emulator host

    P->>H: ESC file-size path ESC /
    H-->>P: file size (big-endian 32-bit)
    P->>H: ESC read-range offset count path ESC /
    H-->>P: returned byte count (big-endian 32-bit)
    H-->>P: requested byte range
    P->>H: ESC is-directory path ESC /
    H-->>P: status value
```

For [`load`](#123-uart-host-service-protocol), `UINT32_MAX` signals failure. Boot and the initial init load use
this complete-file stream. Later process loads use `file-size` and
`read-range`, either as one DMA transfer or as 1 KiB polling chunks. Between
chunks, other processes can use UART.

[`write`](library/unistd/io.picoc#L32) and `write-at` select a host output file until `write stdout` or
`write stderr` changes it. `literal-output` marks a byte count that must not
be parsed as a request. Regular-file writes use it when data contains an
escape byte.

PicoOS keeps descriptor and path state. The host stores the files, including
the binaries requested by the bootloader and process loader.

### 1.2.4 Debugger, source view, and terminal modes
[\[↑ TOC\]](#contents)

The debugger shows RETI state alongside PicoC source. This recording
demonstrates execution controls, snapshots, and the UART terminal:

[![asciicast](https://asciinema.org/a/1264549.svg)](https://asciinema.org/a/1264549)

Open the recording to see stepping, continuing, restarting, ISR inspection,
register and memory editing, snapshots, source debugging, and terminal
input. Each delivered input byte can raise a UART interrupt.

The TUI displays all eight registers. Its code windows follow `PC`, its data
window follows `DS`, and its stack window follows `SP`. These views track
the bootloader, kernel, and selected process as their contexts change.

The default watchobjects and available alternatives are:

| View | Default tracking | Additional selection |
| --- | --- | --- |
| CPU registers | All eight current register values | Select a register to inspect or edit its value |
| EEPROM / SRAM code | `PC`, in the matching address space | Assign another register or a direct memory address |
| SRAM data | `DS` | Assign another register or a direct memory address |
| SRAM stack | `SP` | Assign another register or a direct memory address |
| Periphery | UART state | Cycle interrupt/timer, exception, and DMA views |

Select a window with `Tab` or `Shift+Tab`, then press `a` to choose a register
or address to follow. `j` and `k` scroll, and `C` centers the watchobject.

`.debuginfo`, preprocessed source, labels, and `.sections` connect addresses
to PicoC. `PC` selects the source location, while frame metadata and `BAF`
locate arguments, locals, and return addresses.

Normal terminal mode `v` keeps host signal processing active and exits with
Escape. Raw mode `V` forwards control and escape bytes, including arrow
keys, `Ctrl+C`, and `Ctrl+Z`. Use raw mode for the PicoOS shell and `Ctrl+]`
to return to the debugger.

# 2. Interrupts, system calls, preemption, and exceptions
[\[↑ TOC\]](#contents)

System calls bring library requests into the kernel. Timer and device
interrupts report events independently of the running process. CPU exceptions
report instructions that cannot complete safely. This chapter follows their
entry, handling, and return paths.

## 2.1 RETI interrupt entry and the interrupt service routine table
[\[↑ TOC\]](#contents)

The first five SRAM cells hold the kernel's interrupt service routine table.
The array and table below connect each entry to its source:

```c
__attribute__((section("ivt")))
void (*interrupt_vector_table[OS_INTERRUPT_VECTOR_COUNT])(void) = {
    syscall_interrupt,
    timer_interrupt,
    uart_interrupt,
    cpu_exception_interrupt,
    dma_interrupt
};
```

| Index | Entry | Source |
| ---: | --- | --- |
| 0 | [`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94) | Software `INT 0` from userspace |
| 1 | [`timer_interrupt()`](interrupt_service_routines/os_isrs.picoc#L32) | Timer device |
| 2 | [`uart_interrupt()`](interrupt_service_routines/os_isrs.picoc#L185) | UART receive device |
| 3 | [`cpu_exception_interrupt()`](interrupt_service_routines/os_isrs.picoc#L161) | Fixed synchronous CPU exception entry |
| 4 | [`dma_interrupt()`](interrupt_service_routines/os_isrs.picoc#L223) | DMA completion on the hardware custom-device line |

[`interrupt_vector_table`](interrupt_service_routines/os_isrs.picoc#L23) contains function pointers of type `void (*)(void)`.
The linker encodes each handler's SRAM address. Interrupt entry loads that
address into `PC`, without a C call or generated stack frame.

This excerpt connects the first entry to [`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94). Its `naked`
attribute lets it save registers before any generated code could change them.
[`2.4.2 System-call entry, execution, and return to userspace`](#242-system-call-entry-execution-and-return-to-userspace) gives the complete body:

```c
__attribute__((naked))
void syscall_interrupt(void) {
    // ...
}
```

Interrupt entry automatically saves only a return PC on the active stack.
For software `INT 0`, this is the address of that instruction. For hardware
interrupts and CPU exceptions, the emulator saves the address one instruction
before the instruction to resume or retry. Each ISR explicitly saves any
general registers it needs.

## 2.2 Interrupt-controller mappings and priorities
[\[↑ TOC\]](#contents)

`interrupt_device_isrs[]` maps timer, DMA, and UART to entries `1`, `4`,
and `2`. `interrupt_device_priorities[]` gives them priorities `1`, `1`, and
`2`. UART can interrupt timer or DMA handling. Equal-priority events wait.

### 2.2.1 Interrupt-controller initialization
[\[↑ TOC\]](#contents)

Startup first disables each device, then writes its configured mapping and
priority. The timer starts after init is ready, with a 5,000-instruction
interval:

```c
int interrupt_device_isrs[INTERRUPT_DEVICE_COUNT] = {
    1,                            // INTERRUPT_DEVICE_INTTIMER (index 0)
    4,                            // INTERRUPT_DEVICE_DMA (index 1)
    2                             // INTERRUPT_DEVICE_UART (index 2)
};

int interrupt_device_priorities[INTERRUPT_DEVICE_COUNT] = {
    1, // INTERRUPT_DEVICE_INTTIMER (index 0)
    1, // INTERRUPT_DEVICE_DMA (index 1)
    2  // INTERRUPT_DEVICE_UART (index 2)
};

void interrupt_controller_initialize(void) {
    int device = 0;
    int interrupt_index;
    int priority;

    while (device < INTERRUPT_DEVICE_COUNT) {
        interrupt_controller_disable_device(device);
        interrupt_index = interrupt_device_isrs[device];
        priority = interrupt_device_priorities[device];

        if (interrupt_index != INTERRUPT_CONTROLLER_DISABLED) {
            interrupt_controller_assign_device(device, interrupt_index, priority);
        }

        device = device + 1;
    }
}
```

The two three-cell arrays reside in kernel `.data`. They hold table indices
and priorities. The separate [`interrupt_vector_table`](interrupt_service_routines/os_isrs.picoc#L23) in `.ivt` holds the
actual handler pointers.

The memory map locates these arrays within the kernel image. Arrows show
where their values are written in the interrupt controller. [`1.2.1 RETI machine model and memory-mapped peripherals`](#121-reti-machine-model-and-memory-mapped-peripherals) describes
the peripheral registers:

![SRAM initialization arrays and six interrupt-controller cells in the ReTI memory map](documentation/images/interrupt-controller-initialization.svg)

[`interrupt_controller_disable_device()`](kernel/interrupt_controller.picoc#L23) writes mapping `255` and priority
`0`. [`interrupt_controller_assign_device()`](kernel/interrupt_controller.picoc#L59) then writes the configured index
and priority. The table traces each array entry to its register:

| Device / array index | Mapping source → periphery cell | Priority source → periphery cell |
| --- | --- | --- |
| Timer / `0` | `interrupt_device_isrs[0] = 1` → `0x40000003` | `interrupt_device_priorities[0] = 1` → `0x40000006` |
| DMA on custom line / `1` | `interrupt_device_isrs[1] = 4` → `0x40000004` | `interrupt_device_priorities[1] = 1` → `0x40000007` |
| UART / `2` | `interrupt_device_isrs[2] = 2` → `0x40000005` | `interrupt_device_priorities[2] = 2` → `0x40000008` |

[`9.3 Kernel global variables and process-list roots`](#93-kernel-global-variables-and-process-list-roots) lists the globals and their storage. Terminal reads temporarily disable
UART delivery when inspecting the input buffer to prevent a race with its ISR.

### 2.2.2 Interrupt-controller function reference
[\[↑ TOC\]](#contents)

The controller functions in
[`kernel/interrupt_controller.picoc`](kernel/interrupt_controller.picoc) use
the memory-mapped helpers in the next subsection. This table connects the
controller's global mapping arrays to the register writes they produce.

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`interrupt_controller_initialize(void)`](kernel/interrupt_controller.picoc#L41) | Returns no value | Rewrites timer, DMA, and UART mappings and priorities in periphery registers 3–8 from [`interrupt_device_isrs`](kernel/interrupt_controller.picoc#L3) and [`interrupt_device_priorities`](kernel/interrupt_controller.picoc#L9) | [`interrupt_controller_disable_device()`](kernel/interrupt_controller.picoc#L23), [`interrupt_controller_assign_device()`](kernel/interrupt_controller.picoc#L59) | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31) |
| [`interrupt_controller_assign_device(device, interrupt_index, priority)`](kernel/interrupt_controller.picoc#L59) | Returns no value | Writes one device's interrupt service routine-table index and priority | [`interrupt_controller_device_to_isr_register()`](kernel/interrupt_controller.picoc#L15), [`interrupt_controller_device_to_priority_register()`](kernel/interrupt_controller.picoc#L19), [`periphery_write_register()`](kernel/periphery.picoc#L11) | **Kernel functions:** [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`interrupt_controller_initialize()`](kernel/interrupt_controller.picoc#L41), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) |
| [`interrupt_controller_disable_device(device)`](kernel/interrupt_controller.picoc#L23) | Returns no value | Writes mapping 255 and priority 0 for one device | [`interrupt_controller_device_to_isr_register()`](kernel/interrupt_controller.picoc#L15), [`interrupt_controller_device_to_priority_register()`](kernel/interrupt_controller.picoc#L19), [`periphery_write_register()`](kernel/periphery.picoc#L11) | **Kernel functions:** [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`interrupt_controller_initialize()`](kernel/interrupt_controller.picoc#L41), [`reboot()`](kernel/kernel.picoc#L19), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) |
| [`interrupt_controller_activate_timer(void)`](kernel/interrupt_controller.picoc#L34) | Returns no value | Writes the 5,000-instruction interval to periphery register 9 | [`periphery_write_register()`](kernel/periphery.picoc#L11) | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31) |

### 2.2.3 Memory-mapped periphery function reference
[\[↑ TOC\]](#contents)

Functions in [`kernel/periphery.picoc`](kernel/periphery.picoc) perform the
actual reads and writes. Their callers show that the same access layer also
serves stack protection, CPU exceptions, and UART handling.

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`periphery_read_register(register_index)`](kernel/periphery.picoc#L5) | Returns the selected periphery value | Reads one memory-mapped periphery cell, changes no kernel state | None | **Kernel functions:** [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`handle_cpu_exception()`](kernel/exception.picoc#L70), [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) |
| [`periphery_write_register(register_index, value)`](kernel/periphery.picoc#L11) | Returns no value | Writes one memory-mapped periphery cell | None | **Kernel functions:** [`activate_current_process_stack_boundary()`](kernel/exception.picoc#L22), [`activate_kernel_stack_boundary()`](kernel/exception.picoc#L11), [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213), [`interrupt_controller_activate_timer()`](kernel/interrupt_controller.picoc#L34), [`interrupt_controller_assign_device()`](kernel/interrupt_controller.picoc#L59), [`interrupt_controller_disable_device()`](kernel/interrupt_controller.picoc#L23), [`reboot()`](kernel/kernel.picoc#L19) |

## 2.3 Saved interrupt stack frame
[\[↑ TOC\]](#contents)

System calls and process timer preemption create the same process-stack frame.
[`caller_context`](kernel/dispatcher.picoc#L71) points to its free cell. **`SP`
initially holds this address; `MOVE SP BAF` copies it into `BAF` before `SP`
switches to the kernel stack.** The entry routines then pass the address as the
C argument `caller_context` using `PUSH BAF`
([syscall entry](interrupt_service_routines/os_isrs.picoc#L94),
[process timer entry](interrupt_service_routines/os_isrs.picoc#L74)):

| Offset | Stored value | Address marker at entry |
| ---: | --- | --- |
| **`+0`** | Free cell addressed by [`caller_context`](kernel/dispatcher.picoc#L71) | **← `BAF` = `caller_context`** (copied from `SP`) |
| `+1` | Saved `DS` | |
| `+2` | Saved `CS` | |
| `+3` | Saved `BAF` | Interrupted process's original `BAF` value |
| `+4` | Saved `IN2` | |
| `+5` | Saved `IN1` | |
| `+6` | Saved `ACC` | |
| `+7` | Return PC saved by interrupt entry | |

The live **`BAF` pointer → `+0`** and the **saved `BAF` value at `+3`** have
different roles. Inside a C function, `BAF` is used for that function's call
frame; `caller_context` is accessed as a pointer argument.

[`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) copies offsets 1–6 into the current PCB’s
embedded activation and records [`activation.sp`](kernel/process/process.header#L25) = [`caller_context`](kernel/dispatcher.picoc#L71) + 6. The
return PC remains at [`activation.sp`](kernel/process/process.header#L25) + 1 for the later `RTI`.

Saved user-stack registers and return PCs can be corrupted by a process.
[Linux saves syscall context on the kernel stack](https://github.com/torvalds/linux/blob/master/arch/x86/entry/entry_64.S).
RETI entry and `RTI` use the active `SP`, with no banked kernel stack pointer
or dedicated scratch register. Switching safely would require extra bootstrap
storage and nested-interrupt handling. PicoOS has no memory isolation, so
processes can overwrite either stack and kernel memory.

## 2.4 System-call interface and execution
[\[↑ TOC\]](#contents)

A library wrapper passes a syscall selector and arguments to the installed
kernel. [`handle_syscall()`](kernel/syscall.picoc#L16) chooses the implementation. This avoids embedding
kernel function addresses in user programs.

Kernel functions can move without changing the wrapper. Compatibility still
depends on selectors, register conventions, request layouts, and argument
and result meanings. Together these form the syscall ABI. Changing it can
require rebuilding libraries or programs.

[POSIX](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html)
addresses source portability rather than binary portability. A library can
implement a standard interface using a different kernel's syscalls. PicoOS
uses some POSIX-like names but also differs in signatures and behavior.
[`10.1 From a library call to the kernel: waitpid`](#101-from-a-library-call-to-the-kernel-waitpid) follows one wrapper, [`waitpid()`](library/sys/wait/wait.picoc#L14), through this boundary.

The register convention comes first, followed by the request structures
used when a call needs several arguments.

### 2.4.1 Syscall selectors and register convention
[\[↑ TOC\]](#contents)

A syscall wrapper places its selector in `ACC` and a value or pointer in
`IN1`, then executes `INT 0`. On return, `IN2` holds the result, matching the
PicoC return convention in [`1.1.3 System V ABI stack frames and call cleanup`](#113-system-v-abi-stack-frames-and-call-cleanup).

For multiple arguments, the wrapper fills a request structure on its stack
and passes its absolute address in `IN1`. [`10.1.2 Packing arguments and executing the syscall`](#1012-packing-arguments-and-executing-the-syscall) shows this for [`waitpid()`](library/sys/wait/wait.picoc#L14).

<!-- Presentation: Copy the waitpid code example from Section 10.1.2 directly
into the slides here. Do not merely link to it or jump between sections. -->

The declarations in [`common/syscall.header`](common/syscall.header) and [`common/file.header`](common/file.header) define
these requests. The field tables below explain their contents:

```c
struct LoadProcessRequest { char *path; bool show_loading_bar; };
struct RunProcessRequest { int pid; char *arguments; char **environment; };
struct WaitPidRequest { int pid; int *status; };
struct KillRequest { int pid; int signal_number; };
struct PrctlRequest { int option; int argument; };
struct ShmOpenRequest { char *name; size_t size; };
struct GetCwdRequest { char *buffer; int size; };
struct ReadDirectoryRequest { char *path; char *buffer; int capacity; };
struct MoveRequest { char *old_path; char *new_path; };

struct OpenRequest { char *path; int flags; };
struct IoRequest {
    int file_descriptor;
    char *buffer;
    int count;
    bool protect_uart_control;
    bool show_loading_bar;
    int transferred;
    int loading_bar_update;
    bool complete;
};
struct SeekRequest {
    int file_descriptor;
    int offset;
    int origin;
};
struct Dup2Request { int old_file_descriptor; int new_file_descriptor; };
```

Requests live in the wrapper's stack frame until it returns, including any
time spent suspended. The kernel reads them during the syscall and does not
retain the request pointer. [`9.1 Memory layout, allocation sources, and lifetimes`](#91-memory-layout-allocation-sources-and-lifetimes) compares their lifetime with kernel objects.

#### 2.4.1.1 Process, wait, signal, and memory request structures
[\[↑ TOC\]](#contents)

Each wrapper initializes its request before entering the kernel. The table
shows how process, wait, signal, and memory fields are used. Kernel startup
also creates a [`RunProcessRequest`](common/syscall.header#L55) for init:

| Field | Meaning | Used by |
| --- | --- | --- |
| [`LoadProcessRequest.path`](common/syscall.header#L51) | Path of the `.bin` image | First initialized by [`load()`](library/unistd/process.picoc#L17), passed through [`SYSCALL_LOAD_PROCESS`](common/syscall.header#L8), the loader normalizes it and the PCB receives its own [`kmalloc()`](kernel/kmalloc.picoc#L23) path copy |
| [`LoadProcessRequest.show_loading_bar`](common/syscall.header#L52) | Whether UART transfer progress should be printed | First initialized by [`load()`](library/unistd/process.picoc#L17), read only during loading, derived from [`PICOOS_LOADING_BAR`](common/loading_bar.header#L5) |
| [`RunProcessRequest.pid`](common/syscall.header#L56) | PID of an existing process in state [`NEW`](kernel/process/process.header#L12) | First initialized by [`run()`](library/unistd/process.picoc#L31) (or kernel [`main()`](kernel/kernel.picoc#L31) for init), passed through [`SYSCALL_RUN_PROCESS_WITH_ARGUMENTS`](common/syscall.header#L9), identifies the process whose PCB state becomes [`READY`](kernel/process/process.header#L13) |
| [`RunProcessRequest.arguments`](common/syscall.header#L57) | Space/tab-separated argument string, or `NULL` | First initialized by [`run()`](library/unistd/process.picoc#L31) (or kernel [`main()`](kernel/kernel.picoc#L31) for init), copied into the child's initial process stack, the pointer itself is not retained |
| [`RunProcessRequest.environment`](common/syscall.header#L58) | Null-terminated array of `NAME=value` pointers | First initialized by [`run()`](library/unistd/process.picoc#L31) (or kernel [`main()`](kernel/kernel.picoc#L31) for init), strings and pointer table are copied into the child's initial stack |
| [`WaitPidRequest.pid`](common/syscall.header#L62) | Exact child PID | First initialized by [`waitpid()`](library/sys/wait/wait.picoc#L14), passed through [`SYSCALL_WAITPID`](common/syscall.header#L13), used to find and validate the child |
| [`WaitPidRequest.status`](common/syscall.header#L63) | Address of caller's status cell | First initialized by [`waitpid()`](library/sys/wait/wait.picoc#L14), immediate status destination or copied into the waiting parent's [`waiting_status_ptr`](kernel/process/process.header#L44) while blocked |
| [`KillRequest.pid`](common/syscall.header#L67) | Target process | First initialized by [`kill()`](library/signal/signal.picoc#L14), passed through [`SYSCALL_KILL`](common/syscall.header#L16), lookup only, not retained |
| [`KillRequest.signal_number`](common/syscall.header#L68) | Signal to deliver, 0 probes existence | First initialized by [`kill()`](library/signal/signal.picoc#L14), may change target state or defer termination, but the request is not retained |
| [`PrctlRequest.option`](common/syscall.header#L73) | Currently only [`PR_SET_PDEATHSIG`](common/prctl.header#L3) | First initialized by [`prctl()`](library/sys/prctl/prctl.picoc#L14), passed through [`SYSCALL_PRCTL`](common/syscall.header#L17), selects the supported operation |
| [`PrctlRequest.argument`](common/syscall.header#L75) | Signal number, or 0 to disable | First initialized by [`prctl()`](library/sys/prctl/prctl.picoc#L14), copied into current PCB [`parent_death_signal`](kernel/process/process.header#L59) |
| [`ShmOpenRequest.name`](common/syscall.header#L79) | Name used to find an entry in the kernel's shared-memory linked list | First initialized by [`shm_open()`](library/sys/mman/mman.picoc#L15), passed through [`SYSCALL_SHM_OPEN`](common/syscall.header#L26), a new entry receives a [`kmalloc()`](kernel/kmalloc.picoc#L23) copy |
| [`ShmOpenRequest.size`](common/syscall.header#L80) | Requested shared region size in RETI cells | First initialized by [`shm_open()`](library/sys/mman/mman.picoc#L15), used only when creating a name, an existing entry is not resized |

#### 2.4.1.2 File and directory request structures
[\[↑ TOC\]](#contents)

File and directory wrappers initialize the fields needed for their
operation. The table follows those values into the kernel:

| Field | Meaning | Used by |
| --- | --- | --- |
| [`OpenRequest.path`](common/file.header#L27) | Relative or absolute PicoOS path to a host-backed file or kernel device | First initialized by [`open()`](library/fcntl/fcntl.picoc#L5) or [`fopen()`](library/stdio/stdio.picoc#L125), passed through [`SYSCALL_OPEN`](common/syscall.header#L31), normalized and copied into the selected descriptor |
| [`OpenRequest.flags`](common/file.header#L28) | Access mode plus [`O_CREAT`](common/file.header#L13), [`O_TRUNC`](common/file.header#L14), or [`O_APPEND`](common/file.header#L15) | First initialized by [`open()`](library/fcntl/fcntl.picoc#L5) or [`fopen()`](library/stdio/stdio.picoc#L125), copied into the descriptor, create/truncate decide open requests and append changes later write positioning |
| [`IoRequest.file_descriptor`](common/file.header#L32) | Entry number in the current PCB’s eight-entry table | First initialized by [`read()`](library/unistd/io.picoc#L6), [`write()`](library/unistd/io.picoc#L32), [`write_without_uart_escape_check()`](library/unistd/io.picoc#L43), or stdio I/O wrappers, passed through [`SYSCALL_READ`](common/syscall.header#L32) or [`SYSCALL_WRITE`](common/syscall.header#L33) |
| [`IoRequest.buffer`](common/file.header#L33) | Userspace destination for read or source for write | First initialized by [`read()`](library/unistd/io.picoc#L6), [`write()`](library/unistd/io.picoc#L32), [`write_without_uart_escape_check()`](library/unistd/io.picoc#L43), or stdio I/O wrappers, used directly during the call, for a blocked terminal read the caller's PCB temporarily retains the destination pointer |
| [`IoRequest.count`](common/file.header#L34) | Maximum cells to read or exact cells to write | First initialized by [`read()`](library/unistd/io.picoc#L6), [`write()`](library/unistd/io.picoc#L32), [`write_without_uart_escape_check()`](library/unistd/io.picoc#L43), or stdio I/O wrappers, validated before transfer, retained in terminal pending state only while stdin is blocked |
| [`IoRequest.protect_uart_control`](common/file.header#L35) | Whether a write must scan for `<ESC>` and protect a matching buffer with `literal-output <count>` | First initialized to `true` by [`write()`](library/unistd/io.picoc#L32), [`fputc()`](library/stdio/stdio.picoc#L204), and [`fputs()`](library/stdio/stdio.picoc#L229), initialized to `false` by [`write_without_uart_escape_check()`](library/unistd/io.picoc#L43), [`read()`](library/unistd/io.picoc#L6), [`fgetc()`](library/stdio/stdio.picoc#L178), [`write_process_exception_message()`](kernel/exception.picoc#L29), and [`list_processes()`](kernel/process/process.picoc#L32), read by [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |
| [`IoRequest.show_loading_bar`](common/file.header#L36) | Whether a host-file read shows progress | First initialized by [`read()`](library/unistd/io.picoc#L6), write wrappers, or stdio I/O wrappers, [`read()`](library/unistd/io.picoc#L6) derives this from the environment, writes set it false |
| [`IoRequest.transferred`](common/file.header#L37) | Bytes already copied by earlier chunks of the same [`read()`](library/unistd/io.picoc#L6) | First initialized to 0 by [`read()`](library/unistd/io.picoc#L6) (or stdio input), updated by [`read()`](library/unistd/io.picoc#L6) and read by [`read_regular_file()`](kernel/filesystem/filesystem.picoc#L90) as the next buffer position |
| [`IoRequest.loading_bar_update`](common/file.header#L38) | Next total byte count that redraws read progress | First initialized by [`read_regular_file()`](kernel/filesystem/filesystem.picoc#L90) after the first successful range response, retained and updated for subsequent chunks |
| [`IoRequest.complete`](common/file.header#L39) | Whether [`read()`](library/unistd/io.picoc#L6) should return instead of invoking another chunk | First initialized to false by [`read()`](library/unistd/io.picoc#L6), set by [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150) or [`read_regular_file()`](kernel/filesystem/filesystem.picoc#L90) on completion/error |
| [`SeekRequest.file_descriptor`](common/file.header#L43) | Regular-file descriptor to reposition | First initialized by [`lseek()`](library/unistd/io.picoc#L66), passed through [`SYSCALL_LSEEK`](common/syscall.header#L35) |
| [`SeekRequest.offset`](common/file.header#L44) | Signed displacement | First initialized by [`lseek()`](library/unistd/io.picoc#L66), combined with [`SEEK_SET`](common/file.header#L17), current descriptor offset, or host file size |
| [`SeekRequest.origin`](common/file.header#L45) | [`SEEK_SET`](common/file.header#L17), [`SEEK_CUR`](common/file.header#L18), or [`SEEK_END`](common/file.header#L19) | First initialized by [`lseek()`](library/unistd/io.picoc#L66), selects the base for the new descriptor offset |
| [`Dup2Request.old_file_descriptor`](common/file.header#L49) | Descriptor to copy | First initialized by [`dup2()`](library/unistd/io.picoc#L58), [`SYSCALL_DUP2`](common/syscall.header#L36) leaves the source entry unchanged |
| [`Dup2Request.new_file_descriptor`](common/file.header#L50) | Entry to replace | First initialized by [`dup2()`](library/unistd/io.picoc#L58), the target receives an independent copy of the source fields and path |
| [`GetCwdRequest.buffer`](common/syscall.header#L84) | Userspace destination | First initialized by [`getcwd()`](library/unistd/working_directory.picoc#L11), passed through [`SYSCALL_GETCWD`](common/syscall.header#L40), receives the selected directory copy |
| [`GetCwdRequest.size`](common/syscall.header#L85) | Destination capacity | First initialized by [`getcwd()`](library/unistd/working_directory.picoc#L11), prevents copying a path that does not fit |
| [`ReadDirectoryRequest.path`](common/syscall.header#L89) | Directory to list | First initialized by [`opendir()`](library/dirent/dirent.picoc#L8), passed through [`SYSCALL_READ_DIRECTORY`](common/syscall.header#L42), normalized for the host request |
| [`ReadDirectoryRequest.buffer`](common/syscall.header#L90) | Userspace listing buffer | First initialized by [`opendir()`](library/dirent/dirent.picoc#L8), receives `d name\n` / `- name\n` records from the host |
| [`ReadDirectoryRequest.capacity`](common/syscall.header#L91) | Maximum returned cells | First initialized by [`opendir()`](library/dirent/dirent.picoc#L8), bounds the UART response and copy |
| [`MoveRequest.old_path`](common/syscall.header#L95) | Existing file or directory | First initialized by [`move()`](library/unistd/file_removal.picoc#L12), normalized and sent as the first [`move`](library/unistd/file_removal.picoc#L12) host request path |
| [`MoveRequest.new_path`](common/syscall.header#L96) | New file or directory path | First initialized by [`move()`](library/unistd/file_removal.picoc#L12), normalized and sent as the second [`move`](library/unistd/file_removal.picoc#L12) host request path |

[`load()`](library/unistd/process.picoc#L17) and regular-file [`read()`](library/unistd/io.picoc#L6) reuse their requests across chunks.
A blocked terminal read instead saves its destination and count in the PCB.
The buffer must remain valid until completion. See [`8.3 Blocking and completing terminal reads`](#83-blocking-and-completing-terminal-reads) for terminal reads
and [`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid) for the retained child-status pointer.

Single-value calls pass their argument directly in `IN1`, for example a PID,
descriptor, shared-memory ID, path, or wait-queue pointer.

### 2.4.2 System-call entry, execution, and return to userspace
[\[↑ TOC\]](#contents)

`INT 0` saves its PC on the process stack and enters [`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94).
The ISR installs the kernel context and calls [`handle_syscall()`](kernel/syscall.picoc#L16). The diagram
follows the request through execution and either direct restoration or
scheduling. [`2.4.2.3 Selecting the return path`](#2423-selecting-the-return-path) explains that choice:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    ENTRY["<b>syscall_interrupt()</b><br/>write_stack_heap_boundary_from_in1()<br/>activate_kernel_stack_boundary()"] --> HANDLE["<b>handle_syscall()</b>"]
    HANDLE -->|returns| RETURN["<b>syscall_interrupt_return()</b><br/>caller_context[4] = IN2<br/>dispatcher_reschedule_if_requested()"]
    RETURN --> CHECK{"reschedule_requested?"}
    CHECK -->|false| RESTORE["<b>syscall_interrupt_restore()</b><br/>activate_current_process_stack_boundary()<br/>RTI"]
    CHECK -->|true| DISPATCH["Dispatcher<br/>RTI"]
    HANDLE -->|blocks / yields / exits| DISPATCH
    HANDLE -->|shutdown or reboot| SYSTEM["Halt or restart"]
    click ENTRY "interrupt_service_routines/os_isrs.picoc#L94"
    click HANDLE "kernel/syscall.picoc#L16"
    click RETURN "interrupt_service_routines/os_isrs.picoc#L133"
    click CHECK "kernel/dispatcher.picoc#L8"
    click RESTORE "interrupt_service_routines/os_isrs.picoc#L148"
    click DISPATCH "kernel/dispatcher.picoc#L57"
```

#### 2.4.2.1 Entering kernel context
[\[↑ TOC\]](#contents)

[`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94) saves the
caller's registers and installs the kernel context. `BAF` holds
the saved-frame pointer while kernel `CS`, `DS`, and `SP` are active. The
macros come from [`kernel/memory_constants.header`](kernel/memory_constants.header), described in [`1.1.9 Generated memory constants for the bootloader and kernel`](#119-generated-memory-constants-for-the-bootloader-and-kernel):

```c
__attribute__((naked))
void syscall_interrupt(void) {
    // Saves the same context layout as timer_interrupt
    asm("PUSH ACC"); // Syscall number
    asm("PUSH IN1"); // Syscall argument
    asm("PUSH IN2");
    asm("PUSH BAF");
    asm("PUSH CS");
    asm("PUSH DS");

    // BAF keeps old_sp while loading kernel CS, DS and SP
    asm("MOVE SP BAF");
    asm("LOADI IN1 0");
    write_stack_heap_boundary_from_in1();
    asm(KERNEL_CS_START_ASM); // LOADI32 CS -2147483643
    asm(KERNEL_DS_START_ASM); // LOADI32 DS -2147442893
    asm(KERNEL_SP_START_ASM); // LOADI32 SP -2147435351
    activate_kernel_stack_boundary();

    // Builds the handle_syscall arguments from the saved context
    asm("PUSH BAF"); // Caller context
    asm("LOADIN BAF IN2 5");
    asm("PUSH IN2"); // Syscall argument
    asm("LOADIN BAF IN2 6");
    asm("PUSH IN2"); // Syscall number

    // A syscall that switches processes resumes with a successful IN2 result
    asm("LOADI IN2 1");
    asm("STOREIN BAF IN2 4");

    // Calls handle_syscall and returns through syscall_interrupt_return
    asm("LOADI32 ACC syscall_interrupt_return");
    asm("ADD ACC CS");
    asm("PUSH ACC"); // Return address: syscall return continuation
    asm("LOADI32 ACC handle_syscall");
    asm("ADD ACC CS");
    asm("MOVE ACC PC");
}
```

[`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94) prepares
the kernel call in these steps:

1. Save `ACC`, `IN1`, `IN2`, `BAF`, `CS`, and `DS` on the user-process stack.
   Together with the automatically saved PC, these form the context in
   [`2.3 Saved interrupt stack frame`](#23-saved-interrupt-stack-frame).
2. Copy `SP` to `BAF` to preserve the
   [`caller_context`](kernel/dispatcher.picoc#L71) pointer while switching stacks.
3. Set `IN1 = 0` and call
   [`write_stack_heap_boundary_from_in1()`](common/periphery_asm.header#L2) to
   disable the old limit. Load kernel `CS`, `DS`, and `SP`, then call
   [`activate_kernel_stack_boundary()`](kernel/exception.picoc#L11). The old
   process limit would reject the lower kernel `SP`. Both helpers are explained
   in [`2.4.2.1.1 Stack-boundary helpers`](#24211-stack-boundary-helpers).
4. Push the context pointer, argument, and selector onto the kernel stack.
   Read the argument from the saved `IN1` and the selector from the saved
   `ACC`, pushing each before reusing `IN2`.
5. Set saved `IN2` to the default result `1`, so an operation that switches
   processes can later resume successfully. An operation such as DMA loading
   can replace this saved result before switching.
6. Push [`syscall_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L133)
   as the C return address and transfer control to
   [`handle_syscall()`](kernel/syscall.picoc#L16). Its C epilogue restores `BAF`
   to the context pointer before returning.

Only the call arguments are copied to the kernel stack. The interrupted
register values remain on the user-process stack.

##### 2.4.2.1.1 Stack-boundary helpers
[\[↑ TOC\]](#contents)

Switching stacks also changes the protection boundary in periphery cell
`0x4000000a`. It is the lowest allowed free `SP`. Zero disables checking.
Instructions that decrease `SP` below the limit fail, while automatic
interrupt entry bypasses the check so an exhausted stack can report its fault.

Kernel `SP` lies below the process boundary. Entry disables that limit,
loads kernel `SP`, then installs the kernel limit. UART, DMA, and the timer
branch for kernel work retain the interrupted stack and boundary.

The inline writer in [`common/periphery_asm.header`](common/periphery_asm.header#L2) uses `IN1` without a C
call frame. It can disable protection even on an almost exhausted stack.
It clobbers `ACC`, which resumable entries have already saved:

```c
static inline void write_stack_heap_boundary_from_in1(void) {
    asm("LOADI ACC 1048576");
    asm("MULTI ACC 1024");
    asm("STOREIN ACC IN1 10");
}
```

The writer builds the periphery base in `ACC` and stores `IN1` in cell 10.
Entry uses it with zero. The dispatcher uses it with the selected process's
boundary after restoring `SP`.

The C helpers in [`kernel/exception.picoc`](kernel/exception.picoc#L11) need ordinary call space, so
entry installs kernel `SP` before calling them:

```c
void activate_kernel_stack_boundary(void) {
    periphery_write_register(
        STACK_HEAP_BOUNDARY_REGISTER,
        KERNEL_HEAP_START + KERNEL_HEAP_SIZE - 1
    );
}

int process_stack_boundary(struct ProcessControlBlock *process) {
    return process->base_address + process->heap_start + process->heap_size - 1;
}

void activate_current_process_stack_boundary(void) {
    periphery_write_register(
        STACK_HEAP_BOUNDARY_REGISTER,
        process_stack_boundary(current_process())
    );
}
```

[`activate_kernel_stack_boundary()`](kernel/exception.picoc#L11) writes
`KERNEL_HEAP_START + KERNEL_HEAP_SIZE - 1`, the final kernel-heap cell,
through [`periphery_write_register()`](kernel/periphery.picoc#L11).

[`process_stack_boundary(process)`](kernel/exception.picoc#L18) returns
`base_address + heap_start + heap_size - 1` from the supplied PCB.

[`activate_current_process_stack_boundary()`](kernel/exception.picoc#L22) obtains the current PCB,
computes its limit, and writes it. It changes protection without moving
`SP` or scheduling.

Direct syscall return reinstalls the caller's boundary. Scheduled return
restores `SP` and writes the selected process's boundary in
[`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21). Borrowed-stack handlers retain the existing
limit.

#### 2.4.2.2 Handle Syscall
[\[↑ TOC\]](#contents)

[`handle_syscall()`](kernel/syscall.picoc#L16) selects the operation with an `if`/`else if` chain. It
passes simple values directly and casts request pointers to their declared
types. This excerpt shows both forms and a call needing the saved context:

```c
int handle_syscall(int syscall_number, int argument, int *caller_context) {
    if (syscall_number == SYSCALL_SHUTDOWN) {
        shutdown();
        return 1;
    } else if (syscall_number == SYSCALL_REBOOT) {
        reboot();
        return 1;
    } else if (syscall_number == SYSCALL_LOAD_PROCESS) {
        return load_process_chunk(
            ((struct LoadProcessRequest *)argument)->path,
            ((struct LoadProcessRequest *)argument)->show_loading_bar,
            caller_context
        );
    } else if (syscall_number == SYSCALL_RUN_PROCESS_WITH_ARGUMENTS) {
        return mark_process_ready_with_arguments((struct RunProcessRequest *)argument);
    } else if (syscall_number == SYSCALL_LIST_PROCESSES) {
        list_processes();
        return 1;
    } else if (syscall_number == SYSCALL_UNLOAD_PROCESS) {
        return unload_process_by_pid(argument);
    }

    // ...

    return 0;
}
```

The dispatch rules are:

1. Match a `SYSCALL_*` selector and call its kernel function, passing the
   saved context when needed.
2. Return the function's result in `IN2`, or `0` for an unknown selector.
   Blocking, yielding, or terminating calls may switch processes before
   reaching this return.

##### 2.4.2.2.1 System-call groups
[\[↑ TOC\]](#contents)

PicoOS implements **37 syscalls**, declared in [`common/syscall.header`](common/syscall.header) and
selected by [`handle_syscall()`](kernel/syscall.picoc#L16). The groups below organize them by subsystem:

The `Kernel functions` column identifies the implementation reached by each
group. [`2.4.1 Syscall selectors and register convention`](#241-syscall-selectors-and-register-convention) defines the argument convention and requests.

| Group | Syscalls, in declaration order | Kernel functions |
| --- | --- | --- |
| System control | Shutdown, reboot | [`shutdown()`](kernel/kernel.picoc#L15), [`reboot()`](kernel/kernel.picoc#L19) |
| Process management | Load, run, list, unload, exit, exact-child wait, PID query, terminal ownership, signal delivery, parent-death setting | [`load_process_chunk()`](kernel/process/process_loader.picoc#L292), [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241), [`list_processes()`](kernel/process/process.picoc#L32), [`unload_process_by_pid()`](kernel/process/process.picoc#L328), [`exit_process()`](kernel/process/process.picoc#L430), [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348), [`current_process()`](kernel/process/process.picoc#L62), [`set_foreground_process()`](kernel/signal.picoc#L148), [`send_signal_by_pid()`](kernel/signal.picoc#L108), [`set_parent_death_signal()`](kernel/signal.picoc#L137) |
| Scheduling | Queue sleep, queue wakeup, yield | [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390), [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) |
| Process and shared memory | Heap start, heap size, heap-exhaustion handling, shared-memory open, map, unlink | [`process_heap_start()`](kernel/process/process.picoc#L418), [`process_heap_size()`](kernel/process/process.picoc#L424), [`handle_process_heap_full_exception()`](kernel/exception.picoc#L82), [`open_shared_memory()`](kernel/shared_memory.picoc#L92), [`map_shared_memory()`](kernel/shared_memory.picoc#L130), [`unlink_shared_memory()`](kernel/shared_memory.picoc#L151) |
| Descriptors and I/O | Descriptor availability, open, read, write, close, seek, duplicate, direct UART byte send | Descriptor availability returns 1 directly, [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217), [`close_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L146), [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268), [`duplicate_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L163), [`send_byte_over_uart()`](kernel/uart_hardware.picoc#L9) |
| Paths and directories | Change/get working directory, make/read directory, unlink file, remove directory, move path, touch file | [`change_working_directory()`](kernel/filesystem/host_filesystem.picoc#L163), [`get_working_directory()`](kernel/filesystem/host_filesystem.picoc#L156), [`make_host_directory()`](kernel/filesystem/host_filesystem.picoc#L177), [`read_host_directory()`](kernel/filesystem/host_filesystem.picoc#L187), [`unlink_host_file()`](kernel/filesystem/host_filesystem.picoc#L208), [`remove_host_directory()`](kernel/filesystem/host_filesystem.picoc#L212), [`move_host_path()`](kernel/filesystem/host_filesystem.picoc#L216), [`touch_host_file()`](kernel/filesystem/host_filesystem.picoc#L234) |

#### 2.4.2.3 Selecting the return path
[\[↑ TOC\]](#contents)

A returning syscall saves its result, then checks [`reschedule_requested`](kernel/dispatcher.picoc#L8).
This flag records whether the dispatcher should select a process before
returning to userspace.

The return routine stores the result before checking whether to dispatch:

```c
__attribute__((naked))
void syscall_interrupt_return(void) {
    // Handle_syscall restores BAF to the saved caller context before returning
    // Saves the IN2 result before a pending timer request can dispatch the caller
    asm("STOREIN BAF IN2 4");

    asm("PUSH BAF"); // Caller context
    asm("LOADI32 ACC syscall_interrupt_restore");
    asm("ADD ACC CS");
    asm("PUSH ACC");
    asm("LOADI32 ACC dispatcher_reschedule_if_requested");
    asm("ADD ACC CS");
    asm("MOVE ACC PC");
}
```

[`syscall_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L133)
handles a normally returning kernel operation:

1. Store the result from `IN2` in `caller_context[4]` before a reschedule can
   move that context into the PCB's
   [`activation.in2`](kernel/process/process.header#L23).
2. Pass the context pointer to
   [`dispatcher_reschedule_if_requested()`](kernel/dispatcher.picoc#L14), using
   [`syscall_interrupt_restore()`](interrupt_service_routines/os_isrs.picoc#L148)
   as its return address.
3. Continue to restoration if the helper returns. If
   [`reschedule_requested`](kernel/dispatcher.picoc#L8) is true, the helper
   enters the dispatcher instead, as shown in the decision diagram above. The
   helpers below implement this choice.

These helpers set the flag and act on it. The second helper enters the
dispatcher directly when the flag is set:

```c
bool reschedule_requested = false;

void dispatcher_request_reschedule(void) {
    reschedule_requested = true;
}

void dispatcher_reschedule_if_requested(int *caller_context) {
    if (reschedule_requested) {
        dispatcher_switch_from_context(caller_context);
    }
}
```

[`dispatcher_request_reschedule()`](kernel/dispatcher.picoc#L10) sets `reschedule_requested = true`.
Repeated requests keep it set. This saves no context and switches no process.

[`dispatcher_reschedule_if_requested()`](kernel/dispatcher.picoc#L14) returns if the flag is clear.
Otherwise it passes [`caller_context`](kernel/dispatcher.picoc#L71) to [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71).
The saved syscall result becomes [`activation.in2`](kernel/process/process.header#L23) and survives the switch.

A timer interrupt during kernel work sets the flag. A terminating signal
for the current process also sets it and records [`pending_termination_signal`](kernel/process/process.header#L63).
The dispatcher handles that termination at a safe point. See [`2.5.2 Kernel non-preemption and deferred rescheduling`](#252-kernel-non-preemption-and-deferred-rescheduling).

After selection, this helper clears the flag, sets the current process, and
passes its stack boundary to the restoration routine in [`6.4 Restoring the selected process and returning with RTI`](#64-restoring-the-selected-process-and-returning-with-rti):

```c
void dispatcher_switch_to_process(struct ProcessControlBlock *process) {
    if (current_process() != NULL && current_process()->state == PROCESS_STATE_RUNNING) {
        current_process()->state = PROCESS_STATE_READY;
    }

    reschedule_requested = false;
    set_current_process(process);
    process->state = PROCESS_STATE_RUNNING;

    dispatcher_jump_to_process(process, process_stack_boundary(process));
}
```

[`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43) completes
selection in these steps:

1. If the outgoing process's [`state`](kernel/process/process.header#L33) is
   [`PROCESS_STATE_RUNNING`](kernel/process/process.header#L14), change it to
   [`PROCESS_STATE_READY`](kernel/process/process.header#L13).
2. Clear [`reschedule_requested`](kernel/dispatcher.picoc#L8), make the
   selected PCB the current process through
   [`set_current_process()`](kernel/process/process.picoc#L66), and set its
   [`state`](kernel/process/process.header#L33) to
   [`PROCESS_STATE_RUNNING`](kernel/process/process.header#L14).
3. Compute its limit with [`process_stack_boundary(process)`](kernel/exception.picoc#L18)
   and call [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21).
   That routine restores the selected process and finishes with `RTI`.

Blocking, yielding, and exiting can dispatch inside [`handle_syscall()`](kernel/syscall.picoc#L16).
Those paths restore a selected PCB's registers. Direct syscall restoration
uses the caller's saved stack frame.

The flag check and `RTI` are not atomic. A timer after the check leaves its
request pending until a later scheduling point. A timer in userspace enters
the dispatcher directly.

[`6.3 Saving the current process and selecting the next process`](#63-saving-the-current-process-and-selecting-the-next-process)
shows saving the outgoing activation, and
[`6.4 Restoring the selected process and returning with RTI`](#64-restoring-the-selected-process-and-returning-with-rti)
shows restoring the selected process.

#### 2.4.2.4 Restoring process context with `RTI`
[\[↑ TOC\]](#contents)

[`syscall_interrupt_restore()`](interrupt_service_routines/os_isrs.picoc#L148)
restores the caller's `SP` and explicitly pops the general-purpose registers,
`BAF`, `CS`, and `DS` from the saved interrupt frame. After a process switch,
[`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) restores these
registers from the selected PCB's [`activation`](kernel/process/process.header#L40)
instead. In both paths, restored `SP` points one cell below the PC saved on
that process's stack at its last hardware or software interrupt. `RTI` reads
that PC at `SP + 1`, increments `SP`, and advances `PC` by one to resume
execution. It does not restore the other registers.

The direct syscall return performs this restoration explicitly:

```c
__attribute__((naked))
void syscall_interrupt_restore(void) {
    asm("MOVE BAF SP");
    activate_current_process_stack_boundary();
    asm("POP DS");
    asm("POP CS");
    asm("POP BAF");
    asm("POP IN2");
    asm("POP IN1");
    asm("POP ACC");
    asm("RTI");
}
```

[`syscall_interrupt_restore()`](interrupt_service_routines/os_isrs.picoc#L148)
resumes the caller when no switch was requested:

1. Copy `BAF` to `SP` to select the saved user-process frame and discard the
   kernel scratch call frames.
2. Call [`activate_current_process_stack_boundary()`](kernel/exception.picoc#L22)
   to replace the kernel limit with the caller's limit. Kernel `CS` and `DS`
   remain active while this helper reads the current PCB. Its temporary call
   uses free space below the saved registers.
3. Pop `DS`, `CS`, `BAF`, `IN2`, `IN1`, and `ACC`, including the saved syscall
   result, then execute `RTI` to resume after `INT 0`.

The diagram shows Process 1 being restored alongside two other processes,
using the layout from [`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy).
Restored [`activation.sp`](kernel/process/process.header#L25) selects Process 1's
stack, and `RTI` returns execution to its `.text`:

![Three process memory layouts with optional .ivt, .text and .data grouped as each process image, followed by its heap and stack. PCB 1 restores each CPU register, SP selects Process 1's stack, and RTI returns the PC to the resume instruction in Process 1's .text.](documentation/images/process-context-restore.svg)

### 2.4.3 System-call selection function reference
[\[↑ TOC\]](#contents)

The C entry in [`kernel/syscall.picoc`](kernel/syscall.picoc) connects the ABI
and saved caller context to the subsystem functions grouped above.

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`handle_syscall(syscall_number, argument, caller_context)`](kernel/syscall.picoc#L16) | Returns the selected operation's result for immediate calls. Calls that switch processes leave through the saved interrupt frame. Exit, shutdown, and reboot do not return normally. | Selects one of 37 kernel operations and may change process, scheduler, memory, descriptor, or host-filesystem state | The kernel functions in [`2.4.2.2.1 System-call groups`](#24221-system-call-groups) | **System-call entry:** [`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94) after userspace executes `INT 0` |

## 2.5 Timer interrupts and userspace preemption
[\[↑ TOC\]](#contents)

Startup activates the timer with a 5,000-instruction interval after init
is ready. This counts emulated instructions rather than wall-clock time.
[`2.5.3 Shell character delay for different timer intervals`](#253-shell-character-delay-for-different-timer-intervals) explains the choice.

### 2.5.1 Timer interrupt path
[\[↑ TOC\]](#contents)

The timer schedules immediately after interrupting userspace and defers
scheduling after interrupting kernel work. The diagram follows the functions
below, comparing the saved PC with kernel `DS`, the start of kernel `.data`.
A deferred request is handled at a later scheduling point, including the
syscall return path in
[`2.4.2 System-call entry, execution, and return to userspace`](#242-system-call-entry-execution-and-return-to-userspace):

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    ENTRY["<b>timer_interrupt()</b><br/>Save context"] --> CHECK{"saved PC ><br/>kernel DS?"}
    CHECK -->|no: kernel| REQUEST_K["<b>dispatcher_request_reschedule()</b><br/>reschedule_requested = true"]
    REQUEST_K --> RETURN["<b>timer_interrupt_kernel_return()</b><br/>RTI: kernel work"]
    CHECK -->|yes: userspace| PROCESS["<b>timer_interrupt_process()</b><br/>write_stack_heap_boundary_from_in1()<br/>activate_kernel_stack_boundary()"]
    PROCESS --> SWITCH["<b>dispatcher_switch_from_context(caller_context)</b><br/>Save process->activation<br/>RUNNING state becomes READY"]
    SWITCH --> RESTORE["Dispatcher<br/>Clear reschedule_requested<br/>RTI: selected process"]
    click ENTRY "interrupt_service_routines/os_isrs.picoc#L32"
    click CHECK "interrupt_service_routines/os_isrs.picoc#L51"
    click REQUEST_K "kernel/dispatcher.picoc#L10"
    click RETURN "interrupt_service_routines/os_isrs.picoc#L62"
    click PROCESS "interrupt_service_routines/os_isrs.picoc#L74"
    click SWITCH "kernel/dispatcher.picoc#L71"
    click RESTORE "#64-restoring-the-selected-process-and-returning-with-rti"
```

#### 2.5.1.1 Saving context and selecting the timer branch
[\[↑ TOC\]](#contents)

[`timer_interrupt()`](interrupt_service_routines/os_isrs.picoc#L32) saves the
interrupted registers and uses the saved PC to choose between kernel and
userspace execution. The complete entry below prepares both continuations:

```c
__attribute__((naked))
void timer_interrupt(void) {
    // Saves the interrupted context before requesting a process switch
    asm("PUSH ACC");
    asm("PUSH IN1");
    asm("PUSH IN2");
    asm("PUSH BAF");
    asm("PUSH CS");
    asm("PUSH DS");
    // SP now addresses the free cell below DS, CS, BAF, IN2, IN1 and ACC

    // Uses kernel segments because an interrupt can arrive during entry or return
    asm(KERNEL_CS_START_ASM); // LOADI32 CS -2147483643
    asm(KERNEL_DS_START_ASM); // LOADI32 DS -2147442893

    // Six saved registers put the automatic return PC at SP + 7.
    // DS is now kernel .data's start: kernel code is below it, process code above.
    // Test saved PC because CS may still be changing on kernel entry/return.
    asm("LOADIN SP ACC 7"); // Saved return PC at SP + 7
    asm("SUB ACC DS"); // Saved PC minus the kernel .data start
    asm("JUMP32> timer_interrupt_process"); // Positive: process context

    asm("LOADI32 ACC timer_interrupt_kernel_return");
    asm("ADD ACC CS");
    asm("PUSH ACC");
    asm("LOADI32 ACC dispatcher_request_reschedule");
    asm("ADD ACC CS");
    asm("MOVE ACC PC");
}
```

[`timer_interrupt()`](interrupt_service_routines/os_isrs.picoc#L32) chooses
between immediate and deferred scheduling in these steps:

1. Save `ACC`, `IN1`, `IN2`, `BAF`, `CS`, and `DS` on the interrupted stack.
   Automatic entry has already saved the return PC, which is now at `SP + 7`.
2. Load kernel `CS` and `DS` for the ISR's code and global data. Keep the
   interrupted `SP` until the saved PC identifies the execution context.
3. Execute `LOADIN SP ACC 7`, `SUB ACC DS`, and
   `JUMP32> timer_interrupt_process`. This loads the saved PC, subtracts the
   start of kernel `.data`, and branches on a positive result. The contiguous
   SRAM layout below places kernel `DS` at the start of `.data`, between kernel
   code and user-process code. Offsets increase from left to right, and widths
   are illustrative:

   ![Kernel execution below kernel DS and user-process execution strictly above it](documentation/images/timer-pc-memory-layout.svg)

Kernel `.text` is below kernel `DS`. User images are above it, in the
Process and Shared Data Heap. The subtraction therefore distinguishes valid
code addresses without overflow in the configured `2^18`-word SRAM.
[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy)
explains the heap regions in more detail.

Testing saved PC handles entry and restore windows where `CS` is changing.
[`2.8.1.1.1 Comparing exception and timer context tests`](#28111-comparing-exception-and-timer-context-tests)
explains why exception entry uses a different test and where the tests can disagree.

For a saved PC at or below kernel `DS`, keep the stack, request rescheduling,
and use [`timer_interrupt_kernel_return()`](interrupt_service_routines/os_isrs.picoc#L62).
Otherwise continue through
[`timer_interrupt_process()`](interrupt_service_routines/os_isrs.picoc#L74).

#### 2.5.1.2 Requesting deferred scheduling for kernel work
[\[↑ TOC\]](#contents)

For the kernel branch, [`timer_interrupt()`](interrupt_service_routines/os_isrs.picoc#L32)
calls [`dispatcher_request_reschedule()`](kernel/dispatcher.picoc#L10) on
the interrupted stack, with [`timer_interrupt_kernel_return()`](interrupt_service_routines/os_isrs.picoc#L62)
as its return address. The helper only sets
[`reschedule_requested`](kernel/dispatcher.picoc#L8), preserving the
current process's [`activation`](kernel/process/process.header#L40) and
[`state`](kernel/process/process.header#L33). Its implementation is in
[`2.4.2.3 Selecting the return path`](#2423-selecting-the-return-path).

The kernel has no PCB of its own. Kernel execution includes syscalls, device
handlers, and the dispatcher's wait loop. Resetting its stack during a timer
interrupt would overwrite suspended call frames.

#### 2.5.1.3 Restoring interrupted kernel context with `RTI`
[\[↑ TOC\]](#contents)

After the request helper returns,
[`timer_interrupt_kernel_return()`](interrupt_service_routines/os_isrs.picoc#L62)
restores the saved registers. This continuation keeps the interrupted stack
and its active boundary:

```c
__attribute__((naked))
void timer_interrupt_kernel_return(void) {
    // The request stays pending while the interrupted kernel instructions resume
    asm("POP DS");
    asm("POP CS");
    asm("POP BAF");
    asm("POP IN2");
    asm("POP IN1");
    asm("POP ACC");
    asm("RTI");
}
```

[`timer_interrupt_kernel_return()`](interrupt_service_routines/os_isrs.picoc#L62)
resumes the interrupted kernel work in these steps:

1. Pop `DS`, `CS`, `BAF`, `IN2`, `IN1`, and `ACC` from the interrupted stack.
   The request helper has already restored `SP` to the saved frame. This path
   never replaced active `BAF` with that frame pointer, so it needs no
   `MOVE BAF SP` or boundary change.
2. Execute `RTI` to resume the interrupted kernel instructions. The pending
   [`reschedule_requested`](kernel/dispatcher.picoc#L8) flag is checked at a
   later scheduling point, as explained in
   [`2.5.2 Kernel non-preemption and deferred rescheduling`](#252-kernel-non-preemption-and-deferred-rescheduling).

#### 2.5.1.4 Entering kernel context for userspace preemption
[\[↑ TOC\]](#contents)

The userspace branch jumps directly from
[`timer_interrupt()`](interrupt_service_routines/os_isrs.picoc#L32) to
[`timer_interrupt_process()`](interrupt_service_routines/os_isrs.picoc#L74),
bypassing the deferred-request and kernel-return functions. This entry
installs kernel `SP` before passing the saved frame to the dispatcher:

```c
__attribute__((naked))
void timer_interrupt_process(void) {
    // BAF preserves caller_context while SP switches to the kernel stack
    asm("MOVE SP BAF");
    asm("LOADI IN1 0");
    write_stack_heap_boundary_from_in1();
    asm(KERNEL_SP_START_ASM); // LOADI32 SP -2147435351
    activate_kernel_stack_boundary();

    // Passes the interrupted stack frame to the dispatcher
    asm("PUSH BAF"); // Caller context

    // The dispatcher switches to a process through RTI and does not return
    asm("LOADI ACC 0");
    asm("PUSH ACC"); // Unreachable return address required by the call frame
    asm("LOADI32 ACC dispatcher_switch_from_context");
    asm("ADD ACC CS");
    asm("MOVE ACC PC");
}
```

[`timer_interrupt_process()`](interrupt_service_routines/os_isrs.picoc#L74)
prepares an immediate process switch in these steps:

1. Copy the saved-frame pointer from `SP` to `BAF`, preserving the outgoing
   process context while changing stacks. Kernel `CS` and `DS` are already active.
2. Set `IN1 = 0`, call
   [`write_stack_heap_boundary_from_in1()`](common/periphery_asm.header#L2),
   load kernel `SP`, and call
   [`activate_kernel_stack_boundary()`](kernel/exception.picoc#L11). This makes
   space for kernel calls without comparing kernel `SP` against the process's
   old limit. The helpers are explained in
   [`2.4.2.1.1 Stack-boundary helpers`](#24211-stack-boundary-helpers).
3. Push the context pointer held in `BAF` and a dummy return address of `0`
   to prepare the C call.
4. Transfer control to
   [`dispatcher_switch_from_context(caller_context)`](kernel/dispatcher.picoc#L71).
   [`2.5.1.5 Saving process context and restoring the selected process`](#2515-saving-process-context-and-restoring-the-selected-process)
   follows the dispatcher from saving this context to resuming the selected
   process.

A nested UART interrupt returns to the timer handler, which continues the
same immediate switch.

#### 2.5.1.5 Saving process context and restoring the selected process
[\[↑ TOC\]](#contents)

The userspace timer branch calls
[`dispatcher_switch_from_context(caller_context)`](kernel/dispatcher.picoc#L71)
unconditionally, without setting or checking
[`reschedule_requested`](kernel/dispatcher.picoc#L8). The dispatcher
copies the interrupted registers into the current PCB's
[`activation`](kernel/process/process.header#L40). If the process's
[`state`](kernel/process/process.header#L33) is
[`PROCESS_STATE_RUNNING`](kernel/process/process.header#L14), it changes
that attribute to [`PROCESS_STATE_READY`](kernel/process/process.header#L13).
It then calls
[`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55).
[`6.3 Saving the current process and selecting the next process`](#63-saving-the-current-process-and-selecting-the-next-process)
shows the complete context copy and selection loop.

For the selected process,
[`dispatcher_switch_to_process(process)`](kernel/dispatcher.picoc#L43)
clears [`reschedule_requested`](kernel/dispatcher.picoc#L8), updates the
current-process pointer through
[`set_current_process(process)`](kernel/process/process.picoc#L66), and sets its
[`state`](kernel/process/process.header#L33) to
[`PROCESS_STATE_RUNNING`](kernel/process/process.header#L14). It then calls
[`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21), which restores
the selected PCB's registers and stack boundary and executes `RTI`.
[`6.4 Restoring the selected process and returning with RTI`](#64-restoring-the-selected-process-and-returning-with-rti)
shows that restoration. The timer continuation does not return through its
dummy C return address.

### 2.5.2 Kernel non-preemption and deferred rescheduling
[\[↑ TOC\]](#contents)

Deferring a process switch lets a kernel operation finish before another
process enters the kernel. Device interrupts can still run during that work.

A timer during kernel execution requests a later switch and returns to the
interrupted work. Syscall return checks the flag before resuming userspace,
subject to the timing window in [`2.4.2.3 Selecting the return path`](#2423-selecting-the-return-path). UART handlers also return to the
interrupted operation. This serializes processes' kernel calls, while shared
terminal state still needs protection against UART interrupts.

Blocking, yielding, or termination can dispatch before the syscall return
check. Selection clears the flag. If all processes are blocked, the
dispatcher waits until an interrupt makes one runnable.

Polling loads and regular-file reads transfer at most 1 KiB per syscall.
Returning between chunks allows a pending timer request to schedule another
process. DMA loading starts one payload transfer and blocks its caller until
completion.

### 2.5.3 Shell character delay for different timer intervals
[\[↑ TOC\]](#contents)

Shorter timer intervals give processes more frequent turns but spend more
time switching. The following measurements time shell character delay while
an endless empty loop is running:

![Measured character delay for each timer interrupt interval](documentation/images/timer_interval_measurements.png)

**PicoOS uses 5,000 instructions**. In these measurements, its character delay
was close to 10,000, with less potential waiting between turns. Shorter
intervals added switching overhead. See
[Shell input latency and timer interval](documentation/shell_input_latency.md)
for the method and results.

## 2.6 UART receive interrupt path
[\[↑ TOC\]](#contents)

UART reception enters service routine 2 at priority 2. It handles one byte
and resumes the interrupted context. The diagram follows the choice between
a terminal signal and ordinary input:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    ENTRY["<b>uart_interrupt()</b><br/>Save context"] --> HANDLE["<b>handle_uart_interrupt()</b><br/>Read + acknowledge byte<br/>handle_terminal_signal_character()"]
    HANDLE --> SIGNAL{"Ctrl+C / Ctrl+Z?"}
    SIGNAL -->|yes: signal handled| RETURN["<b>uart_interrupt_return()</b><br/>RTI"]
    SIGNAL -->|no: input byte| INPUT["<b>enqueue_terminal_byte()</b><br/>complete_pending_terminal_read()"]
    INPUT --> RETURN
    click ENTRY "interrupt_service_routines/os_isrs.picoc#L185"
    click HANDLE "kernel/filesystem/terminal.picoc#L213"
    click SIGNAL "kernel/signal.picoc#L192"
    click INPUT "kernel/filesystem/terminal.picoc#L49"
    click RETURN "interrupt_service_routines/os_isrs.picoc#L210"
```

### 2.6.1 Entering kernel segments on the interrupted stack
[\[↑ TOC\]](#contents)

[`uart_interrupt()`](interrupt_service_routines/os_isrs.picoc#L185) preserves
the interrupted context and calls the C handler with kernel `CS` and `DS`.
The entry keeps the existing stack so suspended kernel calls remain intact:

```c
__attribute__((naked))
void uart_interrupt(void) {
    // Saves the interrupted context while the kernel transfers one input byte
    asm("PUSH ACC");
    asm("PUSH IN1");
    asm("PUSH IN2");
    asm("PUSH BAF");
    asm("PUSH CS");
    asm("PUSH DS");

    // BAF keeps the interrupted stack while the handler uses kernel segments
    // Keeping SP avoids overwriting a suspended kernel call frame when all
    // processes are blocked and the dispatcher is waiting for an interrupt
    asm("MOVE SP BAF");
    asm(KERNEL_CS_START_ASM); // LOADI32 CS -2147483643
    asm(KERNEL_DS_START_ASM); // LOADI32 DS -2147442893

    asm("LOADI32 ACC uart_interrupt_return");
    asm("ADD ACC CS");
    asm("PUSH ACC");
    asm("LOADI32 ACC handle_uart_interrupt");
    asm("ADD ACC CS");
    asm("MOVE ACC PC");
}
```

[`uart_interrupt()`](interrupt_service_routines/os_isrs.picoc#L185) enters the
handler in these steps:

1. Save `ACC`, `IN1`, `IN2`, `BAF`, `CS`, and `DS`, preserving the interrupted
   context alongside its automatically saved PC.
2. Keep the saved-frame pointer in `BAF` and load kernel `CS` and `DS`.
   Retain the interrupted `SP` and boundary so nested kernel calls remain intact.
3. Push [`uart_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L210)
   as the return address and transfer control to
   [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213).

UART and DMA save registers and call their handlers on the interrupted
stack. Calls use free space below the saved frame. Resetting kernel `SP`
could overwrite suspended kernel calls.

The existing stack limit remains active. A fault inside either handler is
classified as a kernel exception once kernel `CS` has been installed, even
when the handler is borrowing a user stack.

Direct syscall return additionally changes the stack boundary, as shown in
[`2.4.2.4 Restoring process context with RTI`](#2424-restoring-process-context-with-rti).

### 2.6.2 Handling the received byte
[\[↑ TOC\]](#contents)

The complete C handler below acknowledges the byte before deciding whether it
is a signal character or ordinary terminal input:

```c
void handle_uart_interrupt(void) {
    struct ProcessControlBlock *process = terminal_input_process();
    struct Terminal *terminal = kernel_terminal();
    int value;
    int status;

    value = periphery_read_register(UART_RECEIVE_REGISTER) & 255;
    status = periphery_read_register(UART_STATUS_REGISTER);
    periphery_write_register(
        UART_STATUS_REGISTER,
        status | UART_RECEIVE_READY
    );

    if (handle_terminal_signal_character(value)) {
        return;
    }

    enqueue_terminal_byte(terminal, value);
    complete_pending_terminal_read(process, terminal);
}
```

[`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213) handles
that byte in these steps:

1. Obtain the input process through
   [`terminal_input_process()`](kernel/signal.picoc#L178) and the
   global terminal through [`kernel_terminal()`](kernel/filesystem/terminal.picoc#L22).
2. Read the low byte from the receive register, read UART status, and write
   status with [`UART_RECEIVE_READY`](kernel/filesystem/terminal.picoc#L10)
   set to acknowledge the byte.
3. Call [`handle_terminal_signal_character()`](kernel/signal.picoc#L192).
   `Ctrl+C` sends [`SIGINT`](common/signal.header#L4), while `Ctrl+Z` sends
   [`SIGTSTP`](common/signal.header#L8). Return immediately if the character
   was handled as a signal.
4. Offer an ordinary byte to the terminal ring through
   [`enqueue_terminal_byte()`](kernel/filesystem/terminal.picoc#L49). A full ring drops
   the new byte. Then call
   [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182)
   to copy available bytes to a waiting foreground reader, set its saved
   [`activation.in2`](kernel/process/process.header#L23), and make it runnable.
   The ring and overflow policy are explained in
   [`8.2 Global terminal input buffer`](#82-global-terminal-input-buffer).

### 2.6.3 Restoring interrupted context with `RTI`
[\[↑ TOC\]](#contents)

When [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213)
returns, [`uart_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L210)
resumes the interrupted process or kernel operation. The saved frame supplies
the registers restored below:

```c
__attribute__((naked))
void uart_interrupt_return(void) {
    // Restores the context that was active before the UART interrupt
    asm("MOVE BAF SP");
    asm("POP DS");
    asm("POP CS");
    asm("POP BAF");
    asm("POP IN2");
    asm("POP IN1");
    asm("POP ACC");
    asm("RTI");
}
```

[`uart_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L210)
resumes the interrupted work in these steps:

1. Copy `BAF` back to `SP` to select the saved frame after the C handler returns.
2. Pop `DS`, `CS`, `BAF`, `IN2`, `IN1`, and `ACC`.
3. Execute `RTI` to resume the interrupted instruction stream. This return
   does not query the scheduling flag or switch processes.

### 2.6.4 UART nesting and interrupt priorities
[\[↑ TOC\]](#contents)

The emulator allows only a strictly higher-priority hardware interrupt to
nest inside an active handler. Software `INT 0` does not establish a hardware
priority. With timer and DMA at `1` and UART at `2`, the result is:

| Event | Context already executing | Result |
| --- | --- | --- |
| UART receive | Syscall, with no hardware handler active | UART runs immediately and returns to the same syscall work |
| UART receive | Timer or DMA handler | UART priority `2` nests over priority `1`, then restores the interrupted handler |
| Timer expiration | UART handler | Priority `1` waits in the emulator's pending-handler queue until UART returns |
| DMA completion | UART handler | Priority `1` waits in that queue until UART returns |
| Timer expiration | DMA handler | Equal priority waits until DMA returns |
| DMA completion | Timer handler | Equal priority waits until timer completes its `RTI` path |
| Another UART byte | UART handler or an already pending UART byte | The terminal input queue keeps it until the active byte's ISR completes |

A pending timer runs after UART returns. It schedules a resumed user process
or requests a later switch for kernel work. UART itself restores the
interrupted context. It may wake a reader or send a terminal signal.

`Ctrl+C` targeting the current process records [`pending_termination_signal`](kernel/process/process.header#L63)
and requests scheduling. `Ctrl+Z` changes the process state without setting
that flag. CPU selection enforces either change at the next scheduling point.
[`2.4.2.3 Selecting the return path`](#2423-selecting-the-return-path) describes the request helpers.

Lower or equal priorities wait. The timer keeps one expiration outstanding,
DMA latches completion, and UART retains one byte while later terminal bytes
queue on the host. Mapping UART to `255` leaves them queued. This differs
from the kernel ring's full-buffer policy, which drops new bytes. The
emulator reports pending-handler queue overflow explicitly.

### 2.6.5 Polled UART function reference
[\[↑ TOC\]](#contents)

The interrupt path above handles terminal input. The target-specific functions
in [`kernel/uart_hardware.picoc`](kernel/uart_hardware.picoc) provide the
separate polled UART path used by kernel and directly linked common code.

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`send_byte_over_uart(value)`](kernel/uart_hardware.picoc#L9) | Returns no value | Sends the low byte through UART register 0 and polls UART status, changes no kernel structure | [`switch_to_periphery_address_space()`](kernel/uart_hardware.picoc#L1) | **Library functions:** [`send_byte_over_uart()`](library/stdio/stdio.picoc#L19) through the direct-UART syscall<br>**Shared/Common functions:** [`uart_print_character()`](common/uart_protocol.picoc#L21), linked directly to the kernel implementation<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`receive_byte_over_uart(void)`](kernel/uart_hardware.picoc#L24) | Returns one received byte | Polls UART status and reads UART register 1, changes no kernel structure | [`switch_to_periphery_address_space()`](kernel/uart_hardware.picoc#L1) | **Shared/Common functions:** [`receive_word()`](common/uart_protocol.picoc#L7), linked directly to the kernel implementation<br>**Kernel functions:** [`drain_process_bytes()`](kernel/process/process_loader.picoc#L62), [`read_regular_file()`](kernel/filesystem/filesystem.picoc#L90), [`uart_receive_string()`](kernel/filesystem/host_filesystem.picoc#L10) |

## 2.7 DMA completion interrupt path
[\[↑ TOC\]](#contents)

DMA completion enters service routine 4 and wakes the waiting loader. The
loader checks success or failure when it next runs. This diagram follows
the handler's call to [`wakeup_wait_queue(&dma_waiters)`](kernel/process/process.picoc#L395).
Interrupt delivery follows the priority rules in
[`2.6.4 UART nesting and interrupt priorities`](#264-uart-nesting-and-interrupt-priorities):

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    ENTRY["<b>dma_interrupt()</b><br/>Save context"] --> HANDLE["<b>handle_dma_interrupt()</b><br/>wakeup_wait_queue(&dma_waiters)"]
    HANDLE --> QUEUE{"dma_waiters.head != NULL?"}
    QUEUE -->|yes| WAKE["Wake FIFO head"]
    QUEUE -->|no| RETURN["<b>dma_interrupt_return()</b><br/>RTI"]
    WAKE --> RETURN
    click ENTRY "interrupt_service_routines/os_isrs.picoc#L223"
    click HANDLE "kernel/dma.picoc#L40"
    click QUEUE "kernel/dma.picoc#L6"
    click WAKE "kernel/process/process.picoc#L395"
    click RETURN "interrupt_service_routines/os_isrs.picoc#L246"
```

### 2.7.1 Entering kernel segments on the interrupted stack
[\[↑ TOC\]](#contents)

[`dma_interrupt()`](interrupt_service_routines/os_isrs.picoc#L223) saves the
interrupted registers and installs kernel `CS` and `DS`. Like UART entry,
it borrows the interrupted stack for the C handler:

```c
__attribute__((naked))
void dma_interrupt(void) {
    // Saves the interrupted context while the kernel completes the DMA wait
    asm("PUSH ACC");
    asm("PUSH IN1");
    asm("PUSH IN2");
    asm("PUSH BAF");
    asm("PUSH CS");
    asm("PUSH DS");

    // BAF keeps the interrupted stack while the handler uses kernel segments
    asm("MOVE SP BAF");
    asm(KERNEL_CS_START_ASM); // LOADI32 CS -2147483643
    asm(KERNEL_DS_START_ASM); // LOADI32 DS -2147442893

    asm("LOADI32 ACC dma_interrupt_return");
    asm("ADD ACC CS");
    asm("PUSH ACC");
    asm("LOADI32 ACC handle_dma_interrupt");
    asm("ADD ACC CS");
    asm("MOVE ACC PC");
}
```

[`dma_interrupt()`](interrupt_service_routines/os_isrs.picoc#L223) enters
the C handler in these steps:

1. Save `ACC`, `IN1`, `IN2`, `BAF`, `CS`, and `DS` on the interrupted stack.
2. Keep the saved-frame pointer in `BAF` and load kernel `CS` and `DS` so the
   handler can access [`dma_waiters`](kernel/dma.picoc#L6). Preserve `SP` and
   the active boundary to protect suspended kernel calls.
3. Push [`dma_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L246)
   as the return address and transfer control to
   [`handle_dma_interrupt()`](kernel/dma.picoc#L40).

### 2.7.2 Completing the DMA wait
[\[↑ TOC\]](#contents)

[`initialize_dma()`](kernel/dma.picoc#L9) initializes [`dma_waiters`](kernel/dma.picoc#L6). [`start_dma_uart_receive()`](kernel/dma.picoc#L18)
accepts one transfer when DMA is active and idle with no waiter. It saves
the continuation result, queues the caller, programs DMA, and dispatches.
Completion makes the caller runnable.

At completion, [`handle_dma_interrupt()`](kernel/dma.picoc#L40) wakes a
waiter through the following call. It leaves process selection and checking
the transfer result to later execution:

```c
void handle_dma_interrupt(void) {
    wakeup_wait_queue(&dma_waiters);
}
```

[`handle_dma_interrupt()`](kernel/dma.picoc#L40) calls [`wakeup_wait_queue(&dma_waiters)`](kernel/process/process.picoc#L395). It removes
the FIFO head from [`dma_waiters`](kernel/dma.picoc#L6), updates the queue's
[`head`](common/wait_queue.header#L6) and [`tail`](common/wait_queue.header#L7),
and clears the PCB's [`wait_next`](kernel/process/process.header#L51) and
[`waiting_queue_ptr`](kernel/process/process.header#L48). If the process's
[`state`](kernel/process/process.header#L33) is
[`PROCESS_STATE_STOPPED`](kernel/process/process.header#L16), it sets
[`stopped_from_state`](kernel/process/process.header#L62) to
[`PROCESS_STATE_READY`](kernel/process/process.header#L13), preserving the
stop until the process is continued. Otherwise it sets
[`state`](kernel/process/process.header#L33) to
[`PROCESS_STATE_READY`](kernel/process/process.header#L13). An empty queue is
unchanged.

### 2.7.3 Restoring interrupted context with `RTI`
[\[↑ TOC\]](#contents)

After [`handle_dma_interrupt()`](kernel/dma.picoc#L40) returns,
[`dma_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L246)
restores the interrupted context from its saved frame:

```c
__attribute__((naked))
void dma_interrupt_return(void) {
    // Restores the context that was active before the DMA interrupt
    asm("MOVE BAF SP");
    asm("POP DS");
    asm("POP CS");
    asm("POP BAF");
    asm("POP IN2");
    asm("POP IN1");
    asm("POP ACC");
    asm("RTI");
}
```

[`dma_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L246)
resumes the interrupted work in these steps:

1. Copy `BAF` back to `SP` to select the saved frame after the C handler returns.
2. Pop `DS`, `CS`, `BAF`, `IN2`, `IN1`, and `ACC`.
3. Execute `RTI`, without querying the reschedule flag or dispatching a process.
   The stack and boundary behavior matches
   [`2.6.1 Entering kernel segments on the interrupted stack`](#261-entering-kernel-segments-on-the-interrupted-stack).

DMA and the timer have equal priority, so they wait for each other's handler.
UART can interrupt either. DMA can interrupt a syscall and then return to it.
[`2.6.4 UART nesting and interrupt priorities`](#264-uart-nesting-and-interrupt-priorities) explains nesting and pending events.

### 2.7.4 DMA waiting and completion function reference
[\[↑ TOC\]](#contents)

The functions in [`kernel/dma.picoc`](kernel/dma.picoc) connect process
loading to the DMA registers and the completion path described above.

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`initialize_dma(void)`](kernel/dma.picoc#L9) | Returns no value | Initializes [`dma_waiters`](kernel/dma.picoc#L6) and sets [`dma_initialized`](kernel/dma.picoc#L7) once when DMA is active, otherwise changes nothing | [`dma_is_active()`](common/dma.picoc#L17) | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31), [`start_dma_uart_receive()`](kernel/dma.picoc#L18) |
| [`start_dma_uart_receive(destination, word_count, caller_context)`](kernel/dma.picoc#L18) | Returns `false` when DMA is unavailable, busy, or already has a waiter. Successful setup does not return through the current kernel call. The process later resumes from its saved interrupt frame with [`SYSCALL_LOAD_PROCESS_CONTINUE`](common/syscall.header#L48). | Stores the continuation result in the saved syscall frame, blocks the caller on [`dma_waiters`](kernel/dma.picoc#L6), starts a UART-to-SRAM transfer, and switches processes | [`dma_is_active()`](common/dma.picoc#L17), [`initialize_dma()`](kernel/dma.picoc#L9), [`dma_transfer_status()`](common/dma.picoc#L21), [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375), [`start_dma_uart_transfer()`](common/dma.picoc#L25), [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109) |
| [`handle_dma_interrupt(void)`](kernel/dma.picoc#L40) | Returns no value | Wakes the first process whose PCB is queued on [`dma_waiters`](kernel/dma.picoc#L6) | [`wakeup_wait_queue()`](kernel/process/process.picoc#L395) | **Hardware interrupts:** DMA completion via [`dma_interrupt()`](interrupt_service_routines/os_isrs.picoc#L223) |

## 2.8 CPU exceptions and runtime errors
[\[↑ TOC\]](#contents)

CPU exceptions report instructions that cannot continue. Allocators report
heap exhaustion separately. The kernel either terminates the affected
process or halts the system, depending on where the failure occurred.

### 2.8.1 CPU exception entry and registers
[\[↑ TOC\]](#contents)

Division or modulo by zero, stack overflow, and illegal instructions enter
service routine 3 directly, bypassing device mappings and priorities. The
diagram shows why the faulting context does not resume:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    ENTRY["<b>cpu_exception_interrupt()</b><br/>write_stack_heap_boundary_from_in1()<br/>activate_kernel_stack_boundary()"] --> HANDLE["<b>handle_cpu_exception()</b><br/>Read cause<br/>print_cpu_exception_message()"]
    HANDLE --> KERNEL{"interrupted CS = kernel CS?"}
    KERNEL -->|yes: kernel panic| HALT["<b>shutdown()</b><br/>JUMP 0"]
    KERNEL -->|no: process error| EXIT["<b>exit_process()</b><br/>PROCESS_EXIT_STATUS_EXCEPTION<br/>dispatcher_start_next_process()"]
    EXIT -->|no processes remain| HALT
    EXIT -->|process selected| RESTORE["<b>dispatcher_jump_to_process()</b><br/>RTI: selected process"]
    click ENTRY "interrupt_service_routines/os_isrs.picoc#L161"
    click HANDLE "kernel/exception.picoc#L70"
    click KERNEL "kernel/exception.picoc#L72"
    click HALT "kernel/kernel.picoc#L15"
    click EXIT "kernel/process/process.picoc#L430"
    click RESTORE "kernel/dispatcher.picoc#L21"
```

#### 2.8.1.1 Entering kernel context after a fault
[\[↑ TOC\]](#contents)

The two periphery registers below control protection and report the cause.
They connect the emulator's fault detection to the kernel handler:

| Register | Written by | Contents and use |
| ---: | --- | --- |
| 10, [`STACK_HEAP_BOUNDARY_REGISTER`](kernel/exception.header#L5) | PicoOS | `0` disables stack protection. Any other value is the active boundary, the emulator raises a stack-overflow exception when an instruction decreases `SP` to a value below it. [`activate_kernel_stack_boundary()`](kernel/exception.picoc#L11) writes [`KERNEL_HEAP_START`](kernel/memory_constants.header#L3) + [`KERNEL_HEAP_SIZE`](kernel/memory_constants.header#L4) − 1. A process boundary is [`base_address`](kernel/process/process.header#L34) + [`heap_start`](kernel/process/process.header#L36) + [`heap_size`](kernel/process/process.header#L37) − 1. |
| 11, [`CPU_EXCEPTION_CAUSE_REGISTER`](kernel/exception.header#L6) | RETI CPU/emulator | `0` means no exception has been recorded, `1` means division or modulo by zero, `2` means stack overflow, and `3` means illegal instruction. Guest writes are ignored. [`handle_cpu_exception()`](kernel/exception.picoc#L70) reads this value after exception entry. |

Exception entry saves the faulting PC minus one. The naked handler abandons
that context, so it does not save the other registers:

```c
__attribute__((naked))
void cpu_exception_interrupt(void) {
    // BAF preserves the interrupted CS while the handler resets kernel context
    asm("MOVE CS BAF");
    asm("LOADI IN1 0");
    write_stack_heap_boundary_from_in1();
    asm(KERNEL_CS_START_ASM); // LOADI32 CS -2147483643
    asm(KERNEL_DS_START_ASM); // LOADI32 DS -2147442893
    asm(KERNEL_SP_START_ASM); // LOADI32 SP -2147435351
    activate_kernel_stack_boundary();

    // A zero difference identifies an exception raised in kernel code
    asm("MOVE BAF ACC");
    asm("SUB ACC CS");
    asm("PUSH ACC");

    // The exception handler terminates the process or halts after a kernel panic
    asm("LOADI ACC 0");
    asm("PUSH ACC");
    asm("LOADI32 ACC handle_cpu_exception");
    asm("ADD ACC CS");
    asm("MOVE ACC PC");
}
```

[`cpu_exception_interrupt()`](interrupt_service_routines/os_isrs.picoc#L161)
prepares the exception handler in these steps:

1. Preserve the interrupted `CS` value in `BAF`. Here `BAF` temporarily holds
   a value used for classification, rather than a saved-frame pointer.
2. Set `IN1 = 0` and call
   [`write_stack_heap_boundary_from_in1()`](common/periphery_asm.header#L2).
   Load kernel `CS`, `DS`, and `SP`, then call
   [`activate_kernel_stack_boundary()`](kernel/exception.picoc#L11). Even a
   kernel fault resets `SP`, because the interrupted stack may be exhausted
   and its call frames will not be resumed. The helpers are explained in
   [`2.4.2.1.1 Stack-boundary helpers`](#24211-stack-boundary-helpers).
3. Subtract kernel `CS` from the preserved old `CS` and push the difference
   as the C handler's argument. The boundary helper preserves the old value
   across its ordinary C call.
4. Push a dummy return address of `0` and transfer control to
   [`handle_cpu_exception()`](kernel/exception.picoc#L70). This handler halts
   or terminates the process, so it never returns through that address.

The diagram follows step 3, showing how the difference between interrupted
`CS` in `BAF` and kernel `CS` becomes the argument passed on the kernel stack
to [`handle_cpu_exception(diff)`](kernel/exception.picoc#L70). In box D,
`diff` abbreviates the parameter
[`interrupted_kernel_cs_difference`](kernel/exception.picoc#L70), and the
arrow shows that it receives the pushed `ACC` value.
User `CS` comes from the PCB's [`activation.cs`](kernel/process/process.header#L27),
restored by [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21).

The contiguous SRAM row uses the grouping from
[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy).
The example Process Payload A has no optional `.ivt`, so its `.text` follows
[`BlockHeader`](common/heap.header#L5) A. Its `.data`, User Process Heap, and
User Process Stack follow `.text`, while `…` represents other heap blocks.

![Continuous SRAM with kernel and process CS pointing to their respective code sections, followed by the CS difference pushed into the handler's diff parameter](documentation/images/exception-cs-comparison.svg)

##### 2.8.1.1.1 Comparing exception and timer context tests
[\[↑ TOC\]](#contents)

The timer must recognize unfinished kernel work before switching processes.
During [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21), user `CS`
is already loaded while kernel restore instructions are still executing.
**Saved PC identifies those instructions correctly.** The timer therefore
tests `saved PC > kernel DS`, as shown in
[`2.5.1.1 Saving context and selecting the timer branch`](#2511-saving-context-and-selecting-the-timer-branch).

Exception entry instead preserves `CS` in `BAF` and resets the potentially
exhausted stack. It uses **`interrupted CS == kernel CS`** to select kernel
panic. This simpler test agrees with the timer during ordinary execution,
including syscalls using kernel `CS`.

**The exception test has a limitation:** a fault in kernel restore code
after loading user `CS` would be classified as a process error. Using saved
PC is possible here too, but it would have to be preserved before resetting
`SP`. The different condition is an implementation choice.

#### 2.8.1.2 Reading and classifying the exception
[\[↑ TOC\]](#contents)

The C handler below implements the two outcomes using the supplied CS
comparison and the cause register:

```c
void handle_cpu_exception(int interrupted_kernel_cs_difference) {
    int cause = periphery_read_register(CPU_EXCEPTION_CAUSE_REGISTER);
    bool kernel_exception = interrupted_kernel_cs_difference == 0;

    print_cpu_exception_message(cause, kernel_exception);
    if (kernel_exception) {
        shutdown();
    }

    exit_process(PROCESS_EXIT_STATUS_EXCEPTION);
}
```

[`handle_cpu_exception()`](kernel/exception.picoc#L70) handles the fault in
these steps:

1. Read [`CPU_EXCEPTION_CAUSE_REGISTER`](kernel/exception.header#L6), then
   determine whether the interrupted CS difference is zero.
2. Call [`print_cpu_exception_message()`](kernel/exception.picoc#L44) with
   the cause and classification before choosing the termination path.

##### 2.8.1.2.1 Reporting the exception
[\[↑ TOC\]](#contents)

[`print_cpu_exception_message(cause, kernel_exception)`](kernel/exception.picoc#L44)
chooses a diagnostic for division by zero, stack overflow, or an illegal
instruction. The classification determines the output path:

| Fault context | Diagnostic output | Kernel functions |
| --- | --- | --- |
| Kernel | Sends the panic message directly over UART, avoiding the current process's descriptor table | [`uart_print_string()`](common/uart_protocol.picoc#L73) |
| Process | Sends the termination message through descriptor 1 in the current PCB's [`file_descriptors`](kernel/process/process.header#L42), so output follows that process's redirection | [`write_process_exception_message(message)`](kernel/exception.picoc#L29) builds an [`IoRequest`](common/file.header#L31) and calls [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |

#### 2.8.1.3 Halting the kernel or terminating the process
[\[↑ TOC\]](#contents)

After reporting the fault, [`handle_cpu_exception()`](kernel/exception.picoc#L70)
calls [`shutdown()`](kernel/kernel.picoc#L15) for a kernel exception or
[`exit_process(PROCESS_EXIT_STATUS_EXCEPTION)`](kernel/process/process.picoc#L430)
for a process exception. These complete functions show why neither path
returns to the faulting instruction:

```c
void shutdown(void) {
    asm("JUMP 0");
}
```

```c
void exit_process(int status) {
    terminate_process(current_process(), status);
    dispatcher_start_next_process();
    // Switching to a next process returns via RTI; shutdown is only reached when none remain
    shutdown();
}
```

The two outcomes proceed as follows:

1. For interrupted kernel `CS`, call [`shutdown()`](kernel/kernel.picoc#L15)
   and halt with `JUMP 0`.
2. Otherwise call [`exit_process(PROCESS_EXIT_STATUS_EXCEPTION)`](kernel/process/process.picoc#L430).
   It reaches [`terminate_process()`](kernel/process/process.picoc#L304),
   records [`exit_status`](kernel/process/process.header#L60), changes
   [`state`](kernel/process/process.header#L33) to
   [`PROCESS_STATE_ZOMBIE`](kernel/process/process.header#L17), and removes
   the PCB immediately when no parent needs to collect it.
3. Enter [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55).
   The selected process resumes through the steps in
   [`6.4 Restoring the selected process and returning with RTI`](#64-restoring-the-selected-process-and-returning-with-rti).
   If the process list becomes empty, selection returns and
   [`exit_process()`](kernel/process/process.picoc#L430) shuts down. The
   faulting process's saved PC and registers are never restored.

Exceptions classify the context by interrupted `CS`. The timer instead uses
saved PC. During entry or restoration these can disagree. A borrowed-stack
UART or DMA handler has kernel `CS` and therefore takes the panic path.

Exception entry discards the old stack and dispatches directly after
termination. Process heap exhaustion enters through a syscall but also
terminates the process instead of returning.

### 2.8.2 Supported exceptions and allocation errors
[\[↑ TOC\]](#contents)

The table lists CPU exceptions and allocator failures. Rejected arguments,
missing files, and invalid images return normal failure values:

| Condition | Trigger | Entry or reported cause | PicoOS handling |
| --- | --- | --- | --- |
| Division or modulo by zero | A RETI `DIV`, `DIVI`, `MOD`, or `MODI` instruction has a zero divisor | CPU exception cause `1`, interrupt service routine table entry 3 | [`handle_cpu_exception()`](kernel/exception.picoc#L70) reports division by zero. It terminates the current process with exception status for a userspace fault, or reports a kernel panic and shuts down for a kernel fault. |
| Stack overflow | An instruction decreases `SP` below the active boundary in periphery register 10 | CPU exception cause `2`, interrupt service routine table entry 3 | [`handle_cpu_exception()`](kernel/exception.picoc#L70) reports process stack overflow and terminates that process, or reports kernel stack overflow and shuts down. |
| Illegal instruction | The fetched word is not a valid RETI instruction, or instruction decoding reaches an unsupported opcode | CPU exception cause `3`, interrupt service routine table entry 3 | [`handle_cpu_exception()`](kernel/exception.picoc#L70) reports an illegal instruction and applies the process-or-kernel policy above. The message helper also treats any unexpected cause value as illegal instruction. |
| Process heap full | [`malloc()`](library/stdlib/malloc.picoc#L35) or [`realloc()`](library/stdlib/malloc.picoc#L42) cannot satisfy a positive-size allocation | [`require_process_heap_allocation()`](library/stdlib/malloc.picoc#L8) invokes the process-heap-full syscall | [`handle_process_heap_full_exception()`](kernel/exception.picoc#L82) reports `Process terminated: heap full` through descriptor 1 and terminates the current process with exception status. |
| Kernel heap full | [`kmalloc()`](kernel/kmalloc.picoc#L23) or [`krealloc()`](kernel/kmalloc.picoc#L31) cannot satisfy a positive-size allocation | [`require_kernel_heap_allocation()`](kernel/kmalloc.picoc#L9) calls the panic handler directly | [`panic_kernel_heap_full()`](kernel/exception.picoc#L89) writes `Kernel panic: kernel heap full` directly over UART and shuts down. |
| Process and Shared Data Heap exhausted | [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) cannot reserve a contiguous Process Payload or Shared Data Payload | Returns [`PSDMALLOC_INVALID_START`](kernel/psdmalloc.header#L3), no CPU exception is raised | [`begin_process_load()`](kernel/process/process_loader.picoc#L109) and [`load_process()`](kernel/process/process_loader.picoc#L305) report `error: not enough process memory` and fail the load. [`open_shared_memory()`](kernel/shared_memory.picoc#L92) frees the new entry and returns `-1`. The running process and kernel continue. |

### 2.8.3 Exception and stack-boundary function reference
[\[↑ TOC\]](#contents)

Functions in [`kernel/exception.picoc`](kernel/exception.picoc) manage the
active stack boundary and decide whether a fault terminates a process or the
kernel. The table also includes the two heap-exhaustion handlers implemented in
that file.

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`handle_process_heap_full_exception(void)`](kernel/exception.picoc#L82) | Does not return normally | Writes a diagnostic through descriptor 1 and terminates the current process with exception status | [`write_process_exception_message()`](kernel/exception.picoc#L29), [`exit_process()`](kernel/process/process.picoc#L430) | **Library functions:** [`require_process_heap_allocation()`](library/stdlib/malloc.picoc#L8) through the process-heap-full syscall<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`activate_kernel_stack_boundary(void)`](kernel/exception.picoc#L11) | Returns no value | Writes the kernel heap end to periphery register 10 | [`periphery_write_register()`](kernel/periphery.picoc#L11) | **System-call entry:** [`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94)<br>**Hardware interrupts:** timer via [`timer_interrupt_process()`](interrupt_service_routines/os_isrs.picoc#L74)<br>**CPU exceptions:** [`cpu_exception_interrupt()`](interrupt_service_routines/os_isrs.picoc#L161)<br>**Kernel functions:** [`main()`](kernel/kernel.picoc#L31) |
| [`process_stack_boundary(process)`](kernel/exception.picoc#L18) | Returns the process's absolute heap end | Reads [`base_address`](kernel/process/process.header#L34), [`heap_start`](kernel/process/process.header#L36), and [`heap_size`](kernel/process/process.header#L37), changes no state | None | **Kernel functions:** [`activate_current_process_stack_boundary()`](kernel/exception.picoc#L22), [`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43) |
| [`activate_current_process_stack_boundary(void)`](kernel/exception.picoc#L22) | Returns no value | Writes the current process boundary to periphery register 10 | [`current_process()`](kernel/process/process.picoc#L62), [`process_stack_boundary()`](kernel/exception.picoc#L18), [`periphery_write_register()`](kernel/periphery.picoc#L11) | **System-call return:** [`syscall_interrupt_restore()`](interrupt_service_routines/os_isrs.picoc#L148) |
| [`handle_cpu_exception(interrupted_kernel_cs_difference)`](kernel/exception.picoc#L70) | Does not return normally | Reads register 11, terminates the current process for a process fault or shuts down for a kernel fault | [`periphery_read_register()`](kernel/periphery.picoc#L5), [`print_cpu_exception_message()`](kernel/exception.picoc#L44), [`shutdown()`](kernel/kernel.picoc#L15), [`exit_process()`](kernel/process/process.picoc#L430) | **CPU exceptions:** [`cpu_exception_interrupt()`](interrupt_service_routines/os_isrs.picoc#L161) |
| [`panic_kernel_heap_full(void)`](kernel/exception.picoc#L89) | Does not return | Writes a UART kernel-panic message and shuts down | [`uart_print_string()`](common/uart_protocol.picoc#L73), [`shutdown()`](kernel/kernel.picoc#L15) | **Kernel functions:** [`require_kernel_heap_allocation()`](kernel/kmalloc.picoc#L9) |

# 3. Memory management and shared memory
[\[↑ TOC\]](#contents)

PicoOS manages one physical SRAM address space with a common allocator.
This chapter explains its block list and the three heaps that store kernel
objects, process payloads, and userspace allocations.

## 3.1 Heap block layout and allocation algorithm
[\[↑ TOC\]](#contents)

[`Heap.first_block`](common/heap.header#L12) starts the allocator's list. Each [`BlockHeader`](common/heap.header#L5) describes
the payload immediately after it. The definition and field table show how
the allocator uses them:

```c
struct BlockHeader {
    int size;
    bool free;
    struct BlockHeader *next;
};

struct Heap {
    struct BlockHeader *first_block;
};
```

[`Heap`](common/heap.header#L11) stores a pointer to the first header, separate from the managed
region. [`heap_init_region()`](common/heap.picoc#L49) creates the initial free block. Allocation uses
first fit and may split a block. Freeing merges adjacent free blocks.
Reallocation can resize in place or move the payload.

Every header occupies three cells for [`size`](common/heap.header#L6), [`free`](common/heap.header#L7), and [`next`](common/heap.header#L8). This
four-block example shows physical adjacency and the header-pointer chain:

![One contiguous heap with Block Headers A–D and adjacent payloads, rooted at Heap.first_block](documentation/images/memory-generic-heap.svg)

The links point to headers. Merging free neighbors combines their payloads
and the intervening header into one larger payload.

| Field | Meaning | Used by |
| --- | --- | --- |
| [`BlockHeader.size`](common/heap.header#L6) | Number of usable cells after this header, excluding the header itself | First initialized by [`heap_init_region()`](common/heap.picoc#L49), read by [`heap_alloc_from()`](common/heap.picoc#L65), read/changed by [`heap_split_block()`](common/heap.picoc#L14), [`heap_merge_free_blocks()`](common/heap.picoc#L30), and [`heap_realloc_from()`](common/heap.picoc#L87) |
| [`BlockHeader.free`](common/heap.header#L7) | Whether the associated cells may satisfy an allocation | First initialized by [`heap_init_region()`](common/heap.picoc#L49), initialized for new split headers by [`heap_split_block()`](common/heap.picoc#L14), read/changed by [`heap_alloc_from()`](common/heap.picoc#L65), changed by [`heap_free_from()`](common/heap.picoc#L146), read by [`heap_realloc_from()`](common/heap.picoc#L87) and [`heap_merge_free_blocks()`](common/heap.picoc#L30) |
| [`BlockHeader.next`](common/heap.header#L8) | Address of the next in-region header, or `NULL`. Splitting inserts and merging removes links | First initialized by [`heap_init_region()`](common/heap.picoc#L49), read by [`heap_alloc_from()`](common/heap.picoc#L65), read/changed by [`heap_split_block()`](common/heap.picoc#L14), [`heap_merge_free_blocks()`](common/heap.picoc#L30), and [`heap_realloc_from()`](common/heap.picoc#L87) |
| [`Heap.first_block`](common/heap.header#L12) | First header in the managed region, the descriptor owns no separate block array | First initialized by [`heap_init_region()`](common/heap.picoc#L49), read by [`heap_alloc_from()`](common/heap.picoc#L65) and [`heap_merge_free_blocks()`](common/heap.picoc#L30). Reallocation/freeing reach it through these functions |

[`3.6.3 Allocation and repeated coalescing example`](#363-allocation-and-repeated-coalescing-example)
follows these sizes and links through an allocation and two frees.

## 3.2 SRAM image and heap hierarchy
[\[↑ TOC\]](#contents)

The Kernel Heap follows the linked Kernel Image, then comes the Kernel
Stack. The Process and Shared Data Heap uses the remaining SRAM. Each Process
Payload contains its own User Process Heap. Sizes count 32-bit RETI cells.

A [`ProcessControlBlock`](kernel/process/process.header#L31) manages a separate Process Payload. A
[`SharedMemoryEntry`](kernel/shared_memory.header#L8) manages shared data, with [`SharedMemoryAttachment`](kernel/shared_memory.header#L17) records
for mappings. [`4. Processes and process lifecycle`](#4-processes-and-process-lifecycle) and [`5. Shared Memory Entries and Mappings`](#5-shared-memory-entries-and-mappings) explain their lifecycles. The table locates the heap
descriptors that manage these allocations:

| Heap context | Descriptor storage | Managed payloads | Interface |
| --- | --- | --- | --- |
| Kernel Heap | [`kernel_heap`](kernel/kmalloc.picoc#L7), a [`struct Heap`](common/heap.header#L11) global in kernel `.data` | PCBs, copied paths, descriptor tables, [`SharedMemoryEntry`](kernel/shared_memory.header#L8), [`SharedMemoryAttachment`](kernel/shared_memory.header#L17), and other kernel objects | [`kmalloc()`](kernel/kmalloc.picoc#L23) / [`kfree()`](kernel/kmalloc.picoc#L38) |
| Process and Shared Data Heap | [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7), a [`struct Heap`](common/heap.header#L11) global in kernel `.data` | Complete Process Payloads and Shared Data Payloads | [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) / [`PSDFree()`](kernel/psdmalloc.picoc#L47) |
| User Process Heap | [`process_heap`](library/stdlib/malloc.picoc#L6), a [`struct Heap`](common/heap.header#L11) global in that process's `.data` | Allocations made by that process and its linked libraries | [`malloc()`](library/stdlib/malloc.picoc#L35) / [`free()`](library/stdlib/malloc.picoc#L49) |

The diagram locates the three heaps in SRAM and expands one Process Payload
into its image, heap, and stack.

![Continuous SRAM with the Kernel Heap, Process and Shared Data Heap, and nested User Process Heap highlighted by amber outlines and grouping bands, four blocks per heap, concrete kernel payload examples, and a dashed expansion of Process Payload A into its image, heap, and stack](documentation/images/memory-sram-overview.svg)

These current offsets come from [`kernel/kernel.sections`](kernel/kernel.sections) and
[`kernel/memory_constants.header`](kernel/memory_constants.header). They are relative to [`SRAM_BASE`](kernel/memory_constants.header#L1) and change
when the kernel is rebuilt:

| Larger part | SRAM offset | Section or region | Contents |
| --- | ---: | --- | --- |
| Kernel Image | `0..4` | `.ivt` | Five interrupt service routine addresses |
| Kernel Image | `5..40754` | `.text` | Kernel code, including interrupt service routines |
| Kernel Image | `40755..41485` | `.data` | Kernel globals, including both kernel-managed heap descriptors and list roots |
| Kernel runtime reservation | `41486..45581` | Kernel Heap | 4096 cells, including in-region block headers |
| Kernel runtime reservation | `45582..48297` | Kernel Stack | Stack grows toward lower addresses from the initial free `SP` cell |
| After the Kernel region | `48298..262143` | Process and Shared Data Heap | Outer blocks for Process Payloads and Shared Data Payloads |

The bootloader consumes the binary header separately from the Kernel Image.
[`init_kernel_heap()`](kernel/kmalloc.picoc#L17) initializes the reserved kernel heap, and
[`init_process_shared_data_heap()`](kernel/psdmalloc.picoc#L9) initializes the range from
[`PROCESS_MEMORY_START`](kernel/memory_constants.header#L5) through [`SRAM_MAX_ADDRESS_IN_MEMORY_MAP`](kernel/memory_constants.header#L2).
[`activate_kernel_stack_boundary()`](kernel/exception.picoc#L11) protects the final kernel-heap cell.

The loader reads each process's image offsets from its binary header. The
table connects them to PCB addresses:

| Process Payload part | Relative address | Runtime role |
| --- | --- | --- |
| Optional `.ivt` | Before [`code_start`](kernel/process/process_loader.picoc#L117) when present | Process-local attributed data, ordinary PicoOS user images normally omit it |
| `.text` | [`code_start`](kernel/process/process_loader.picoc#L117) | [`create_process()`](kernel/process/process.picoc#L89) adds [`base_address`](kernel/process/process.header#L34) to initialize [`activation.cs`](kernel/process/process.header#L27) |
| `.data` | [`data_start`](kernel/process/process_loader.picoc#L118) | Added to [`base_address`](kernel/process/process.header#L34) for [`activation.ds`](kernel/process/process.header#L28), contains global data such as [`process_heap`](library/stdlib/malloc.picoc#L6) |
| User Process Heap | [`heap_start`](kernel/process/process.header#L36) through `heap_start + heap_size - 1` | Contains its own [`BlockHeader`](common/heap.header#L5) chain and library allocations. Its final cell is the stack boundary |
| User Process Stack | First cell beyond the heap through [`effective_stack_start`](kernel/process/process_loader.picoc#L122) | Holds initial arguments, environment strings, return PC, and later call frames. Grows toward lower addresses |

[`base_address`](kernel/process/process.header#L34) is absolute, while [`heap_start`](kernel/process/process.header#L36) is relative to it.
[`process_heap_start()`](kernel/process/process.picoc#L418) adds them, and [`process_heap_size()`](kernel/process/process.picoc#L424) returns the size.
[`libstart`](library/start/libstart.picoc) uses both to initialize the user heap. [`4.2.2.1.1 User process stack placement`](#42211-user-process-stack-placement) explains stack
reservation, and [`4.2.2.1.2 Initial argc, argv, and envp`](#42212-initial-argc-argv-and-envp) shows startup contents.

## 3.3 Kernel Heap
[\[↑ TOC\]](#contents)

The Kernel Heap stores kernel objects separately from the process and
shared-data payloads they manage. [`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy) locates it in SRAM.

### 3.3.1 Kernel Heap blocks and kernel objects
[\[↑ TOC\]](#contents)

The kernel-global [`kernel_heap.first_block`](common/heap.header#L12) points to the first header
at [`KERNEL_HEAP_START`](kernel/memory_constants.header#L3). Each object occupies a separate allocation.

[`create_process()`](kernel/process/process.picoc#L89) uses [`kmalloc()`](kernel/kmalloc.picoc#L23) for its PCB and [`copy_process_path()`](kernel/process/process.picoc#L70)
for the PCB-owned path string. [`open_shared_memory()`](kernel/shared_memory.picoc#L92) allocates its entry
here too. [`base_address`](kernel/process/process.header#L34) and [`address`](kernel/shared_memory.header#L11) point into the outer heap instead.

### 3.3.2 Kernel Heap allocator function reference
[\[↑ TOC\]](#contents)

These functions select [`kernel_heap`](kernel/kmalloc.picoc#L7) and call the common allocator. Failed
positive-size requests invoke the kernel panic policy:

| Kernel / Library Function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`kmalloc(size)`](kernel/kmalloc.picoc#L23) (Kernel only) | Payload pointer, `NULL` for nonpositive size, panics if a positive request has no fit | Allocates through the list rooted at [`kernel_heap`](kernel/kmalloc.picoc#L7)'s [`first_block`](common/heap.header#L12), may insert a split header and marks the selected block allocated | [`require_kernel_heap_allocation()`](kernel/kmalloc.picoc#L9), [`heap_alloc_from()`](common/heap.picoc#L65) | **Kernel functions:** [`copy_shared_memory_name()`](kernel/shared_memory.picoc#L27), [`open_shared_memory()`](kernel/shared_memory.picoc#L92), [`map_shared_memory()`](kernel/shared_memory.picoc#L130), [`copy_process_path()`](kernel/process/process.picoc#L70), [`create_process()`](kernel/process/process.picoc#L89), [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`copy_file_path()`](kernel/filesystem/file_descriptor.picoc#L6), [`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35) |
| [`krealloc(ptr, size)`](kernel/kmalloc.picoc#L31) (Kernel only) | Original/replacement payload pointer, `NULL` after freeing on nonpositive size, panics on positive-size failure | Resizes a Kernel Heap block, a null pointer requests a new allocation. Currently unused | [`require_kernel_heap_allocation()`](kernel/kmalloc.picoc#L9), [`heap_realloc_from()`](common/heap.picoc#L87) | None |
| [`kfree(ptr)`](kernel/kmalloc.picoc#L38) (Kernel only) | Returns no value | Marks the preceding [`BlockHeader.free`](common/heap.header#L7) true and coalesces free neighbors throughout the Kernel Heap. A null pointer has no effect | [`heap_free_from()`](common/heap.picoc#L146) | **Kernel functions:** [`destroy_shared_memory_entry()`](kernel/shared_memory.picoc#L69), [`open_shared_memory()`](kernel/shared_memory.picoc#L92), [`unlink_shared_memory()`](kernel/shared_memory.picoc#L151), [`release_process_shared_memory()`](kernel/shared_memory.picoc#L172), [`free_process_load()`](kernel/process/process_loader.picoc#L71), [`remove_process()`](kernel/process/process.picoc#L209), [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`set_process_working_directory()`](kernel/filesystem/host_filesystem.picoc#L128), [`copy_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L82), [`destroy_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L118), [`close_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L146) |
| [`init_kernel_heap(void)`](kernel/kmalloc.picoc#L17) (Kernel only) | Returns no value | Initializes [`kernel_heap`](kernel/kmalloc.picoc#L7) over [`KERNEL_HEAP_START`](kernel/memory_constants.header#L3) and [`KERNEL_HEAP_SIZE`](kernel/memory_constants.header#L4), creating one free block | [`heap_init_region()`](common/heap.picoc#L49) | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31) |
| [`require_kernel_heap_allocation(memory, size)`](kernel/kmalloc.picoc#L9) (Kernel only) | Returns the unchanged pointer, or does not return if a positive request failed | Converts a failed positive Kernel Heap allocation into a kernel panic | [`panic_kernel_heap_full()`](kernel/exception.picoc#L89) | **Kernel functions:** [`kmalloc()`](kernel/kmalloc.picoc#L23), [`krealloc()`](kernel/kmalloc.picoc#L31) |

## 3.4 Process and Shared Data Heap
[\[↑ TOC\]](#contents)

[`process_shared_data_heap`](kernel/psdmalloc.picoc#L7) manages the region after the Kernel Stack. It
allocates complete Process Payloads and Shared Data Payloads. Their kernel
metadata remains in the Kernel Heap.

### 3.4.1 Process allocations
[\[↑ TOC\]](#contents)

[`PSDMalloc()`](kernel/psdmalloc.picoc#L20) returns the payload's absolute address. A PCB records it in
[`base_address`](kernel/process/process.header#L34) and keeps the requested cell count in [`size`](kernel/process/process.header#L35). The actual block
may be slightly larger if its remainder is too small to split.

[`4.1.2.1 From PCBs to Process Payloads in SRAM`](#4121-from-pcbs-to-process-payloads-in-sram) shows PCB pointers reaching these payloads. The PCB's [`next`](kernel/process/process.header#L53) links
process records, independently of the allocator's header chain.

[`load_process()`](kernel/process/process_loader.picoc#L305) and [`begin_process_load()`](kernel/process/process_loader.picoc#L109) reserve payloads with
[`PSDMalloc()`](kernel/psdmalloc.picoc#L20). [`remove_process()`](kernel/process/process.picoc#L209) releases the whole image, heap, and stack
with [`PSDFree(base_address)`](kernel/psdmalloc.picoc#L47). Userspace [`free()`](library/stdlib/malloc.picoc#L49) releases only an inner
heap allocation.

### 3.4.2 Shared Data allocations
[\[↑ TOC\]](#contents)

[`open_shared_memory()`](kernel/shared_memory.picoc#L92) also calls [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) and stores the address in
[`SharedMemoryEntry.address`](kernel/shared_memory.header#L11). Its entry and name are separate Kernel Heap
allocations.

[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy) shows that pointer reaching the Shared Data Payload.
[`shared_memory_list_head`](kernel/shared_memory.picoc#L6) and the entries' [`next`](kernel/shared_memory.header#L14) links form an independent
registry, and each [`name`](kernel/shared_memory.header#L9) points to a copied Kernel Heap string.

A shared entry can have several process mappings, while a PCB manages one
process. Shared data has no nested user heap. [`destroy_shared_memory_entry()`](kernel/shared_memory.picoc#L69)
releases it with [`PSDFree()`](kernel/psdmalloc.picoc#L47). [`5. Shared Memory Entries and Mappings`](#5-shared-memory-entries-and-mappings) explains when destruction is allowed.

### 3.4.3 Process and Shared Data Heap allocator function reference
[\[↑ TOC\]](#contents)

These functions select [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7). They return absolute
integer addresses, with [`PSDMALLOC_INVALID_START`](kernel/psdmalloc.header#L3) for failure:

[`load()`](library/unistd/process.picoc#L17) and [`shm_open()`](library/sys/mman/mman.picoc#L15) reach these allocations through syscalls.
[`mmap()`](library/sys/mman/mman.picoc#L23) adds a Kernel Heap attachment record to an existing shared region.

| Kernel / Library Function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`PSDMalloc(size)`](kernel/psdmalloc.picoc#L20) (Kernel only) | Absolute payload address, or [`PSDMALLOC_INVALID_START`](kernel/psdmalloc.header#L3) (`-1`) for nonpositive size or no fit | Allocates a complete Process Payload or shared-data region through [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7), converts the common payload pointer to an integer address | [`heap_alloc_from()`](common/heap.picoc#L65) | **Kernel functions:** [`open_shared_memory()`](kernel/shared_memory.picoc#L92), [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`load_process()`](kernel/process/process_loader.picoc#L305) |
| [`PSDRealloc(start, size)`](kernel/psdmalloc.picoc#L31) (Kernel only) | Absolute original/replacement payload address, or [`PSDMALLOC_INVALID_START`](kernel/psdmalloc.header#L3) (`-1`) for nonpositive size or no fit | Resizes an outer allocation. An invalid start requests a new allocation. Nonpositive size releases an existing block, failed positive growth preserves it. Currently unused | [`heap_realloc_from()`](common/heap.picoc#L87) | None |
| [`PSDFree(start)`](kernel/psdmalloc.picoc#L47) (Kernel only) | Returns no value | Releases the outer block at the supplied payload address and coalesces free neighbors throughout [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7). An invalid start has no effect | [`heap_free_from()`](common/heap.picoc#L146) | **Kernel functions:** [`destroy_shared_memory_entry()`](kernel/shared_memory.picoc#L69), [`cancel_process_load()`](kernel/process/process_loader.picoc#L76), [`remove_process()`](kernel/process/process.picoc#L209) |
| [`init_process_shared_data_heap(void)`](kernel/psdmalloc.picoc#L9) (Kernel only) | Returns no value | Initializes [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7) over [`PROCESS_MEMORY_START`](kernel/memory_constants.header#L5) through [`SRAM_MAX_ADDRESS_IN_MEMORY_MAP`](kernel/memory_constants.header#L2), inclusive, creating one free block | [`heap_init_region()`](common/heap.picoc#L49) | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31) |

## 3.5 User Process Heap
[\[↑ TOC\]](#contents)

Each process and its libraries allocate within that process's User Process
Heap. The common allocator manages it inside the outer Process Payload.

### 3.5.1 Per-Process User Process Heap
[\[↑ TOC\]](#contents)

[`process_heap`](library/stdlib/malloc.picoc#L6) resides in the process image's `.data`. [`init_process_heap()`](library/stdlib/malloc.picoc#L18)
obtains the heap bounds through syscalls and initializes its first header.
[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy) shows the inner block list between the image and stack.

[`malloc()`](library/stdlib/malloc.picoc#L35),
[`realloc()`](library/stdlib/malloc.picoc#L42), and
[`free()`](library/stdlib/malloc.picoc#L49) call the shared allocator directly
with this descriptor. They change the inner block chain, leaving the outer
allocation in place.

Each process has its own descriptor. Restoring [`activation.ds`](kernel/process/process.header#L28) selects that
process's globals, including [`process_heap`](library/stdlib/malloc.picoc#L6). No shared userspace heap pointer
is replaced during a context switch. [`6.4 Restoring the selected process and returning with RTI`](#64-restoring-the-selected-process-and-returning-with-rti) shows the register restoration.

### 3.5.2 User Process Heap allocator function reference
[\[↑ TOC\]](#contents)

These library functions use [`process_heap`](library/stdlib/malloc.picoc#L6) and call the allocator directly.
Syscalls supply the initial bounds and handle allocation failure:

| Kernel / Library Function | Return value / status | Effects | Calls | Syscalls | Called by |
| --- | --- | --- | --- | --- | --- |
| [`malloc(size)`](library/stdlib/malloc.picoc#L35) (Library only) | Payload pointer, `NULL` for nonpositive size, process-heap-full exception if a positive request has no fit | Allocates through the calling image's [`process_heap`](library/stdlib/malloc.picoc#L6), searches and updates blocks directly in library code | [`require_process_heap_allocation()`](library/stdlib/malloc.picoc#L8), [`heap_alloc_from()`](common/heap.picoc#L65) | Process-heap-full on positive-size failure | **Library functions:** [`opendir()`](library/dirent/dirent.picoc#L8), [`copy_environment_variable()`](library/stdlib/env.picoc#L20), [`initialize_environment()`](library/stdlib/env.picoc#L97), [`setenv()`](library/stdlib/env.picoc#L126), [`clone_environment()`](library/stdlib/env.picoc#L205)<br>**User applications:** [`main()` in sed](user/sed.picoc#L67), [`read_environment()` in init](system/init.picoc#L19)<br>**Test programs (direct calls):** [`basic_heap_allocator_example.picoc`](test/basic_heap_allocator_example.picoc), [`basic_malloc.picoc`](test/basic_malloc.picoc), [`basic_free.picoc`](test/basic_free.picoc), [`basic_free_block_merging.picoc`](test/basic_free_block_merging.picoc), [`basic_realloc.picoc`](test/basic_realloc.picoc), [`basic_realloc_null_and_zero.picoc`](test/basic_realloc_null_and_zero.picoc), [`basic_string.picoc`](test/basic_string.picoc), [`exception_heap_full/heap_full.picoc`](test/exception_heap_full/heap_full.picoc), [`exercise_sheet_4_heap/launcher.picoc`](test/exercise_sheet_4_heap/launcher.picoc) |
| [`realloc(ptr, size)`](library/stdlib/malloc.picoc#L42) (Library only) | Original/replacement payload pointer, `NULL` after freeing on nonpositive size, process-heap-full exception on positive-size failure | Resizes a User Process Heap block, a null pointer requests a new allocation. Calls the common implementation directly | [`require_process_heap_allocation()`](library/stdlib/malloc.picoc#L8), [`heap_realloc_from()`](common/heap.picoc#L87) | Process-heap-full on positive-size failure | **Library functions:** [`store_environment_variable()`](library/stdlib/env.picoc#L67)<br>**Test programs (direct calls):** [`basic_realloc.picoc`](test/basic_realloc.picoc), [`basic_realloc_null_and_zero.picoc`](test/basic_realloc_null_and_zero.picoc) |
| [`free(ptr)`](library/stdlib/malloc.picoc#L49) (Library only) | Returns no value | Releases and coalesces blocks only in the calling image's [`process_heap`](library/stdlib/malloc.picoc#L6). A null pointer has no effect | [`heap_free_from()`](common/heap.picoc#L146) | None | **Library functions:** [`opendir()`](library/dirent/dirent.picoc#L8), [`closedir()`](library/dirent/dirent.picoc#L66), [`store_environment_variable()`](library/stdlib/env.picoc#L67), [`unsetenv()`](library/stdlib/env.picoc#L157), [`clearenv()`](library/stdlib/env.picoc#L194), [`destroy_environment()`](library/stdlib/env.picoc#L230)<br>**User applications:** [`main()` in sed](user/sed.picoc#L67), [`read_environment()` in init](system/init.picoc#L19)<br>**Test programs (direct calls):** [`basic_heap_allocator_example.picoc`](test/basic_heap_allocator_example.picoc), [`basic_free.picoc`](test/basic_free.picoc), [`basic_free_block_merging.picoc`](test/basic_free_block_merging.picoc), [`basic_realloc.picoc`](test/basic_realloc.picoc), [`exercise_sheet_4_heap/launcher.picoc`](test/exercise_sheet_4_heap/launcher.picoc) |
| [`init_process_heap(void)`](library/stdlib/malloc.picoc#L18) (Library only) | Returns no value | Gets the current process's absolute heap start and size, then initializes [`process_heap`](library/stdlib/malloc.picoc#L6) and its first free header | [`heap_init_region()`](common/heap.picoc#L49) | Process-heap-start, process-heap-size | **Library functions:** [`start_process()`](library/start/start.picoc#L7)<br>**Test programs (direct calls):** [`basic_heap_allocator_example.picoc`](test/basic_heap_allocator_example.picoc), [`basic_environment.picoc`](test/basic_environment.picoc), [`basic_malloc.picoc`](test/basic_malloc.picoc), [`basic_free.picoc`](test/basic_free.picoc), [`basic_free_block_merging.picoc`](test/basic_free_block_merging.picoc), [`basic_realloc.picoc`](test/basic_realloc.picoc), [`basic_realloc_null_and_zero.picoc`](test/basic_realloc_null_and_zero.picoc), [`basic_string.picoc`](test/basic_string.picoc) |
| [`require_process_heap_allocation(memory, size)`](library/stdlib/malloc.picoc#L8) (Library only) | Returns the unchanged pointer, or terminates the process if a positive request failed | Invokes the process-heap-full syscall only when the common allocator returns `NULL` for a positive request | No C calls | Process-heap-full on positive-size failure | **Library functions:** [`malloc()`](library/stdlib/malloc.picoc#L35), [`realloc()`](library/stdlib/malloc.picoc#L42) |

## 3.6 Heap and allocator function reference
[\[↑ TOC\]](#contents)

[`common/heap.picoc`](common/heap.picoc) implements the allocator. Its functions take a [`Heap`](common/heap.header#L11)
without choosing the region or failure policy. [`3.3.2 Kernel Heap allocator function reference`](#332-kernel-heap-allocator-function-reference), [`3.4.3 Process and Shared Data Heap allocator function reference`](#343-process-and-shared-data-heap-allocator-function-reference), and [`3.5.2 User Process Heap allocator function reference`](#352-user-process-heap-allocator-function-reference)
show the wrappers for each heap.

### 3.6.1 Common allocator linkage and function reference
[\[↑ TOC\]](#contents)

The kernel links [`common/heap.picoc`](common/heap.picoc) directly. [`libstdlib`](library/stdlib/libstdlib.picoc#L1) includes the same source in
each user image. The two boxes compare direct allocator calls using the kernel's
[`kernel_heap`](kernel/kmalloc.picoc#L7) and [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7)
with calls using each user image's own [`process_heap`](library/stdlib/malloc.picoc#L6):

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    subgraph K["Kernel target"]
        direction TB
        KW["kmalloc / krealloc / kfree<br/>kernel_heap"] -->|direct calls| KC["common/heap.picoc<br/>heap_alloc_from / heap_realloc_from / heap_free_from"]
        PW["PSDMalloc / PSDRealloc / PSDFree<br/>process_shared_data_heap"] -->|direct calls| KC
    end
    subgraph L["Each userspace target: libstdlib"]
        direction TB
        LW["malloc / realloc / free<br/>process_heap in this image"] -->|direct calls| LC["same common/heap.picoc source<br/>heap_alloc_from / heap_realloc_from / heap_free_from"]
    end
    K ~~~ L
```

The table covers the common allocator. Sizes count cells. Free and realloc
require a valid pointer from the supplied heap and recover its header by
pointer arithmetic, without an ownership check:

| Kernel / Library Function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`heap_init_region(heap, start, cell_count)`](common/heap.picoc#L49) (Shared/Common) | Returns no value | For a null heap, does nothing. For a null start or at most three cells, sets [`Heap.first_block`](common/heap.header#L12) to `NULL`. Otherwise writes one header with [`size`](common/heap.header#L6) = cell count minus three, [`free`](common/heap.header#L7) = true, [`next`](common/heap.header#L8) = `NULL`, and stores its address in the descriptor | None | **Library functions (directly linked):** [`init_process_heap()`](library/stdlib/malloc.picoc#L18)<br>**Kernel functions (directly linked):** [`init_kernel_heap()`](kernel/kmalloc.picoc#L17), [`init_process_shared_data_heap()`](kernel/psdmalloc.picoc#L9)<br>**Test programs (direct calls):** [`basic_heap_allocator_example.picoc`](test/basic_heap_allocator_example.picoc) |
| [`heap_alloc_from(heap, size)`](common/heap.picoc#L65) (Shared/Common) | Payload pointer, or `NULL` for a null heap, nonpositive size, or no fit | Scans from [`Heap.first_block`](common/heap.header#L12) through [`next`](common/heap.header#L8), selects the first free block with enough payload cells, optionally splits it, sets [`free`](common/heap.header#L7) false, and returns the address immediately after the header | [`heap_split_block()`](common/heap.picoc#L14) | **Library functions (directly linked):** [`malloc()`](library/stdlib/malloc.picoc#L35)<br>**Kernel functions (directly linked):** [`kmalloc()`](kernel/kmalloc.picoc#L23), [`PSDMalloc()`](kernel/psdmalloc.picoc#L20)<br>**Shared/common functions (directly linked):** [`heap_realloc_from()`](common/heap.picoc#L87) |
| [`heap_realloc_from(heap, ptr, size)`](common/heap.picoc#L87) (Shared/Common) | Original/replacement payload pointer, or `NULL` for a null heap, nonpositive size, or failed replacement allocation | With a valid heap, nonpositive size frees the block, a null pointer allocates. Otherwise shrinks/splits in place and coalesces, grows into only the immediate free neighbor if sufficient, or allocates/copies/frees. Failed replacement allocation preserves the old block | [`heap_free_from()`](common/heap.picoc#L146), [`heap_alloc_from()`](common/heap.picoc#L65), [`heap_split_block()`](common/heap.picoc#L14), [`heap_merge_free_blocks()`](common/heap.picoc#L30), [`heap_copy_cells()`](common/heap.picoc#L3) | **Library functions (directly linked):** [`realloc()`](library/stdlib/malloc.picoc#L42)<br>**Kernel functions (directly linked):** [`krealloc()`](kernel/kmalloc.picoc#L31), [`PSDRealloc()`](kernel/psdmalloc.picoc#L31) |
| [`heap_free_from(heap, ptr)`](common/heap.picoc#L146) (Shared/Common) | Returns no value | For a null heap or pointer, does nothing. Otherwise finds the preceding header, sets [`free`](common/heap.header#L7) true, and scans the entire heap to coalesce consecutive free blocks. Does not erase payload contents | [`heap_merge_free_blocks()`](common/heap.picoc#L30) | **Library functions (directly linked):** [`free()`](library/stdlib/malloc.picoc#L49)<br>**Kernel functions (directly linked):** [`kfree()`](kernel/kmalloc.picoc#L38), [`PSDFree()`](kernel/psdmalloc.picoc#L47)<br>**Shared/common functions (directly linked):** [`heap_realloc_from()`](common/heap.picoc#L87) |
| [`heap_split_block(block, size)`](common/heap.picoc#L14) (Shared/Common) | Returns no value | Splits only if [`size`](common/heap.header#L6) ≥ requested size + three header cells + one payload cell. Inserts a free header after the requested payload, links it to the old successor, then updates the original size and successor. Otherwise leaves the block unchanged. Does not change the original free flag | None | **Shared/common functions (directly linked):** [`heap_alloc_from()`](common/heap.picoc#L65), [`heap_realloc_from()`](common/heap.picoc#L87) |
| [`heap_merge_free_blocks(heap)`](common/heap.picoc#L30) (Shared/Common) | Returns no value | For a null heap, does nothing. Scans from [`Heap.first_block`](common/heap.header#L12). When current and next are free, adds three header cells and the next payload to the current size, bypasses the next header, and rechecks the same current header. Advances only when the pair cannot merge | None | **Shared/common functions (directly linked):** [`heap_realloc_from()`](common/heap.picoc#L87), [`heap_free_from()`](common/heap.picoc#L146) |
| [`heap_copy_cells(destination, source, count)`](common/heap.picoc#L3) (Shared/Common) | Returns no value | Copies count cells in increasing index order from source to destination. Used for the overlap between old payload size and requested replacement size | None | **Shared/common functions (directly linked):** [`heap_realloc_from()`](common/heap.picoc#L87) |

### 3.6.2 Reallocation decisions
[\[↑ TOC\]](#contents)

For a valid block and positive size, this graph shows when realloc keeps
the address or moves the payload. A failed move preserves the old block.
A null pointer allocates, while a nonpositive size frees:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    R["Resize an existing block"] --> FIT{"Current payload large enough?"}
    FIT -->|Yes| SHRINK["heap_split_block<br/>heap_merge_free_blocks"]
    SHRINK --> SAME["Return original pointer"]
    FIT -->|No| NEXT{"Immediate next block free and combined space enough?"}
    NEXT -->|Yes| GROW["Absorb next header and payload<br/>heap_split_block"]
    GROW --> SAME
    NEXT -->|No| ALLOC["heap_alloc_from"]
    ALLOC --> OK{"Allocation succeeded?"}
    OK -->|No| KEEP["Return NULL<br/>Old block remains allocated"]
    OK -->|Yes| COPY["heap_copy_cells<br/>heap_free_from old block"]
    COPY --> NEW["Return replacement pointer"]
```

Growth absorbs at most one successor. Shrinking and freeing run the repeated
merge scan illustrated next.

### 3.6.3 Allocation and repeated coalescing example
[\[↑ TOC\]](#contents)

This 52-cell example follows an allocation and two frees. Gray boxes are
headers, teal payloads are allocated, and green payloads are free. Arrows
show `next` links. The amber outline marks the changed block. Offsets count
cells, although drawn widths are not proportional to sizes.

#### 3.6.3.1 Initial state and first-fit search
[\[↑ TOC\]](#contents)

The four payloads have sizes 8, 4, 12, and 16. Including four three-cell
headers gives `8 + 4 + 12 + 16 + 4 × 3 = 52` cells. Allocating all four and
then freeing B and D produces this state:

![Initial heap with allocated A, C and free B, D, linked from left to right](documentation/images/heap-01-initial.svg)

#### 3.6.3.2 Allocation splits D
[\[↑ TOC\]](#contents)

D can split because `16 >= 11 + 3 + 1`. Its header stays at offset 33,
[`size`](common/heap.header#L6) becomes 11, and [`free`](common/heap.header#L7) becomes false. The returned payload starts
at offset 36:

The remainder D′ gets a header at `36 + 11 = 47` and a two-cell payload.
Its [`next`](common/heap.header#L8) is `NULL`, and D's [`next`](common/heap.header#L8) now points to it. A, B, and C stay put.

![After allocation, D has eleven allocated payload cells and links to new free Header D′ with two payload cells](documentation/images/heap-02-allocated.svg)

> **Note:** A 14-cell request cannot split D because the two-cell remainder
> cannot hold a header and payload. It receives all 16 cells.

#### 3.6.3.3 Free D and merge its remainder
[\[↑ TOC\]](#contents)

Freeing D leaves two adjacent free blocks, D and its remainder D′.
The merge scan restores D's original 16-cell payload.

##### 3.6.3.3.1 Mark D free
[\[↑ TOC\]](#contents)

Freeing the payload recovers D's header and sets [`free`](common/heap.header#L7) to true. This is
the intermediate state before merging:

![D marked free with its eleven payload cells still separate from free D′ and its two payload cells](documentation/images/heap-03-d-marked-free.svg)

##### 3.6.3.3.2 Merge D and its remainder
[\[↑ TOC\]](#contents)

The merge scan starts at A and reaches D/D′. Both are free, so D absorbs
D′'s header and payload. Its size becomes `11 + 3 + 2 = 16`, and [`next`](common/heap.header#L8)
becomes `NULL`. The absorbed header cells become usable payload space:

![D restored to sixteen free payload cells after absorbing Header D′ and its two payload cells](documentation/images/heap-04-d-merged.svg)

D has no successor, so the scan ends with the initial four-block layout.

#### 3.6.3.4 Free C and merge repeatedly at B
[\[↑ TOC\]](#contents)

Freeing C creates a run of three free blocks. The allocator combines them
through two merges at B without advancing to another header.

##### 3.6.3.4.1 Mark C free
[\[↑ TOC\]](#contents)

Freeing C's payload at offset 21 marks C free. B, C, and D are now adjacent
free blocks:

![C marked free, making B, C, and D consecutive free blocks after allocated A](documentation/images/heap-05-c-marked-free.svg)

##### 3.6.3.4.2 First merge at B
[\[↑ TOC\]](#contents)

The scan reaches B/C and merges them. B's size becomes `4 + 3 + 12 = 19`,
and its [`next`](common/heap.header#L8) becomes D:

![First merge at B bypasses Header C and produces nineteen free payload cells followed by free D](documentation/images/heap-06-b-c-merged.svg)

##### 3.6.3.4.3 Second merge at B
[\[↑ TOC\]](#contents)

The scan stays at B and checks its new neighbor D. It merges again, giving
B `19 + 3 + 16 = 38` payload cells and `next = NULL`. This is repeated
iteration at one header:

![Second merge at B bypasses Header D, leaving allocated A and a thirty-eight-cell free B with next equal to NULL](documentation/images/heap-07-b-d-merged.svg)

The final list is A → B and still occupies `8 + 38 + 2 × 3 = 52` cells.
A stays allocated, and [`Heap.first_block`](common/heap.header#L12) continues to point to it.

The merge loop relies on headers being in contiguous address order.
Rechecking after each merge combines an entire free run.
[`basic_heap_allocator_example.picoc`](test/basic_heap_allocator_example.picoc) checks this example, including first
fit, splitting, merging, and preserved data. The figures come from
[`documentation/generate_heap_allocator_diagrams.py`](documentation/generate_heap_allocator_diagrams.py).

# 4. Processes and process lifecycle
[\[↑ TOC\]](#contents)

The kernel records each process's identity, resources, and saved execution
state in a PCB. This chapter connects those fields to loading, starting,
and lifecycle management. [`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid)
explains how a parent waits for a child and collects its termination status.

## 4.1 Process control block fields
[\[↑ TOC\]](#contents)

[`ProcessControlBlock`](kernel/process/process.header#L31) is the kernel's record for one process. Its definition
and field table connect memory, resources, saved registers, and lifecycle
bookkeeping to the functions that initialize and use them:

```c
struct ProcessControlBlock {
    int pid;
    int state;
    int base_address;
    int size;
    int heap_start;
    int heap_size;
    char *binary_path;
    char *working_directory;
    struct ActivationRecord activation;
    struct FileDescriptorTable *file_descriptors;
    int *waiting_status_ptr;
    struct wait_queue waiters;
    struct wait_queue *waiting_queue_ptr;
    struct ProcessControlBlock *wait_next;
    struct ProcessControlBlock *next;
    struct SharedMemoryAttachment *shared_memory_attachments;
    int parent_pid;
    int parent_death_signal;
    int exit_status;
    int stop_signal;
    int stopped_from_state;
    int pending_termination_signal;
    char *pending_terminal_read_buffer;
    int pending_terminal_read_count;
    struct ProcessLoad *pending_load;
};
```

| Attribute | Meaning | Used by |
| --- | --- | --- |
| [`pid`](kernel/process/process.header#L32) | Assigned from the global counter when the PCB is created, never changes | First initialized by [`create_process()`](kernel/process/process.picoc#L89), read by [`find_process_by_pid()`](kernel/process/process.picoc#L162) and [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) |
| [`state`](kernel/process/process.header#L33) | [`NEW`](kernel/process/process.header#L12), [`READY`](kernel/process/process.header#L13), [`RUNNING`](kernel/process/process.header#L14), [`BLOCKED`](kernel/process/process.header#L15), [`STOPPED`](kernel/process/process.header#L16), or [`ZOMBIE`](kernel/process/process.header#L17) | First initialized by [`create_process()`](kernel/process/process.picoc#L89), changed by [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241), queue helpers, [`stop_process()`](kernel/signal.picoc#L37), [`continue_process()`](kernel/signal.picoc#L50), [`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43), and [`terminate_process()`](kernel/process/process.picoc#L304) |
| [`base_address`](kernel/process/process.header#L34), [`size`](kernel/process/process.header#L35) | Absolute start and requested cell count of the [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) Process Payload | First initialized by [`create_process()`](kernel/process/process.picoc#L89), released by [`remove_process()`](kernel/process/process.picoc#L209) |
| [`heap_start`](kernel/process/process.header#L36), [`heap_size`](kernel/process/process.header#L37) | Process-relative userspace heap start and cell count from the binary header/defaults | First initialized by [`create_process()`](kernel/process/process.picoc#L89), read by [`process_heap_start()`](kernel/process/process.picoc#L418), [`process_heap_size()`](kernel/process/process.picoc#L424), and [`process_stack_boundary()`](kernel/exception.picoc#L18) |
| [`binary_path`](kernel/process/process.header#L38) | PCB-owned executable path without the leading `/`, it exists while the process is [`NEW`](kernel/process/process.header#L12), supplies the later [`argv[0]`](kernel/process/process_arguments.picoc#L184) copy, and remains the kernel's stable name for process listings | First initialized by [`create_process()`](kernel/process/process.picoc#L89), copied by [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125), printed by [`list_processes()`](kernel/process/process.picoc#L32), freed by [`remove_process()`](kernel/process/process.picoc#L209) |
| [`working_directory`](kernel/process/process.header#L39) | PCB-owned absolute PicoOS path, copied from the parent or initialized to `/` for PID 1 | First initialized by [`create_process()`](kernel/process/process.picoc#L89) through copying, read by [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), replaced by [`change_working_directory()`](kernel/filesystem/host_filesystem.picoc#L163), freed by [`remove_process()`](kernel/process/process.picoc#L209) |
| [`activation`](kernel/process/process.header#L40) | Embedded saved CPU context needed later by the dispatcher, [`6.2 Saved process registers`](#62-saved-process-registers) explains its fields | First initialized by [`create_process()`](kernel/process/process.picoc#L89), later maintained by [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125), [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71), [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182), and [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) |
| [`file_descriptors`](kernel/process/process.header#L42) | Pointer to this process's descriptor table. [`9.2 Containment and reference relationships`](#92-containment-and-reference-relationships) shows the wrapper, entry array, and path references | First initialized by [`create_process()`](kernel/process/process.picoc#L89) through [`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35), inherited by [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241), destroyed by [`remove_process()`](kernel/process/process.picoc#L209) |
| [`waiting_status_ptr`](kernel/process/process.header#L44) | Pointer into this process’s suspended userspace [`waitpid()`](library/sys/wait/wait.picoc#L14) frame | First initialized to `NULL` by [`create_process()`](kernel/process/process.picoc#L89), set by [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348), written and cleared by [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) or [`notify_process_stopped()`](kernel/signal.picoc#L23) |
| [`waiters`](kernel/process/process.header#L46) | Embedded FIFO queue of processes waiting for this process | First initialized by [`create_process()`](kernel/process/process.picoc#L89), filled by [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348), drained by [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) or [`notify_process_stopped()`](kernel/signal.picoc#L23) |
| [`waiting_queue_ptr`](kernel/process/process.header#L48), [`wait_next`](kernel/process/process.header#L51) | Queue containing this PCB and its intrusive successor link | First initialized by [`create_process()`](kernel/process/process.picoc#L89), maintained by [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375), [`enqueue_terminal_reader()`](kernel/filesystem/terminal.picoc#L61), [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), and [`remove_from_wait_queue()`](kernel/process/process.picoc#L176) |
| [`next`](kernel/process/process.header#L53) | Link in the global process list | First initialized/linked by [`create_process()`](kernel/process/process.picoc#L89), traversed by [`scheduler_next_process()`](kernel/scheduler.picoc#L12) and [`find_process_by_pid()`](kernel/process/process.picoc#L162), unlinked by [`remove_process()`](kernel/process/process.picoc#L209) |
| [`shared_memory_attachments`](kernel/process/process.header#L55) | Head of this process's mapping-record list. Each record references a shared-memory entry as shown in [`9.2 Containment and reference relationships`](#92-containment-and-reference-relationships) | First initialized by [`create_process()`](kernel/process/process.picoc#L89), extended by [`map_shared_memory()`](kernel/shared_memory.picoc#L130), released by [`remove_process()`](kernel/process/process.picoc#L209) through [`release_process_shared_memory()`](kernel/shared_memory.picoc#L172) |
| [`parent_pid`](kernel/process/process.header#L57), [`parent_death_signal`](kernel/process/process.header#L59) | Creator PID and optional signal delivered when that parent terminates | First initialized by [`create_process()`](kernel/process/process.picoc#L89), parent-death setting changed by [`set_parent_death_signal()`](kernel/signal.picoc#L137), used by [`orphan_and_signal_children()`](kernel/process/process.picoc#L279) |
| [`exit_status`](kernel/process/process.header#L60) | Status retained while the process is a zombie | First initialized to 0 by [`create_process()`](kernel/process/process.picoc#L89), set by [`terminate_process()`](kernel/process/process.picoc#L304), collected by [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) |
| [`stop_signal`](kernel/process/process.header#L61), [`stopped_from_state`](kernel/process/process.header#L62), [`pending_termination_signal`](kernel/process/process.header#L63) | Signal bookkeeping for stopped and deferred termination paths | First initialized by [`create_process()`](kernel/process/process.picoc#L89), used by [`stop_process()`](kernel/signal.picoc#L37), [`continue_process()`](kernel/signal.picoc#L50), [`send_signal_to_process()`](kernel/signal.picoc#L75), and [`prepare_process_termination()`](kernel/signal.picoc#L126) |
| [`pending_terminal_read_buffer`](kernel/process/process.header#L65), [`pending_terminal_read_count`](kernel/process/process.header#L66) | Userspace request retained while a terminal read is blocked or stopped | First initialized to `NULL`/0 by [`create_process()`](kernel/process/process.picoc#L89), set by [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), consumed by [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182) or [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) |
| [`pending_load`](kernel/process/process.header#L68) | Executable metadata, paths, progress, and reserved Process and Shared Data Heap region while this process is between load chunks | First initialized to `NULL` by [`create_process()`](kernel/process/process.picoc#L89), set by [`begin_process_load()`](kernel/process/process_loader.picoc#L109), advanced by [`continue_process_load()`](kernel/process/process_loader.picoc#L227), cleared by [`finish_process_load()`](kernel/process/process_loader.picoc#L90) or [`cancel_process_load()`](kernel/process/process_loader.picoc#L76) |

PCB address fields refer into a separate Process Payload. These are ordinary
physical addresses, with no MMU translation or process isolation.

[`8.9 PicoOS paths, working directories, and host operations`](#89-picoos-paths-working-directories-and-host-operations) explains [`working_directory`](kernel/process/process.header#L39), and [`8.1 Per-process file-descriptor table`](#81-per-process-file-descriptor-table) explains [`file_descriptors`](kernel/process/process.header#L42).
[`binary_path`](kernel/process/process.header#L38) exists before `argv[0]` is copied to the stack and remains
available to [`list_processes()`](kernel/process/process.picoc#L32) even if userspace changes `argv[0]`. [`4.2.2.1.2 Initial argc, argv, and envp`](#42212-initial-argc-argv-and-envp)
shows that stack copy.

### 4.1.1 Process states and transitions
[\[↑ TOC\]](#contents)

[`state`](kernel/process/process.header#L33) tells the scheduler and lifecycle functions whether a process can
run, must wait, is stopped, or has finished. PicoOS uses these six values:

| State | Numeric value | Meaning | Typical transition |
| --- | --- | --- | --- |
| [`NEW`](kernel/process/process.header#L12) | 0 | Loaded image and PCB exist, but the final startup layout is not yet prepared | Completed process load |
| [`READY`](kernel/process/process.header#L13) | 1 | Eligible for the scheduler | Run setup, queue wakeup, or [`SIGCONT`](common/signal.header#L6) |
| [`RUNNING`](kernel/process/process.header#L14) | 2 | Activation is loaded into the CPU | Dispatcher |
| [`BLOCKED`](kernel/process/process.header#L15) | 3 | PCB is linked into one wait queue | Terminal read, DMA completion wait, [`waitpid()`](library/sys/wait/wait.picoc#L14), or [`sleep()`](library/unistd/blocking.picoc#L9) |
| [`STOPPED`](kernel/process/process.header#L16) | 4 | Suspended by [`SIGSTOP`](common/signal.header#L7), [`SIGTSTP`](common/signal.header#L8), or [`SIGTTIN`](common/signal.header#L9) | Signal subsystem |
| [`ZOMBIE`](kernel/process/process.header#L17) | 5 | Terminated status retained for a parent | [`terminate_process()`](kernel/process/process.picoc#L304) |

[`NEW`](kernel/process/process.header#L12) keeps a loaded process out of scheduling until [`run()`](library/unistd/process.picoc#L31) prepares its
arguments, environment, descriptors, and stack. It also guards against
starting twice. Another OS could use a startup flag or omit unstarted
processes from its runnable collection instead.

This guard applies to normal run setup. [`stop_process()`](kernel/signal.picoc#L37) accepts [`NEW`](kernel/process/process.header#L12), and
[`continue_process()`](kernel/signal.picoc#L50) can then set [`READY`](kernel/process/process.header#L13). A stop/continue sequence can
therefore expose an unstarted process to scheduling.

[`scheduler_can_run()`](kernel/scheduler.picoc#L4) accepts [`READY`](kernel/process/process.header#L13) and [`RUNNING`](kernel/process/process.header#L14). This lets the current
process run again if no other process is eligible. Being ready does not
start execution immediately.

[`ZOMBIE`](kernel/process/process.header#L17) retains the termination status while excluding the process from
scheduling. [`7.1.2.1 Recording termination status`](#7121-recording-termination-status) and [`7.1.2.2 Parent collection and final removal`](#7122-parent-collection-and-final-removal) explain status delivery and final removal.

The diagram follows normal startup, scheduling, waits, signals, and
termination. Removal ends the PCB's lifetime. [`6. Scheduling and context switching`](#6-scheduling-and-context-switching) explains scheduling, and
[`7. Blocking, wait queues, signals, and mutexes`](#7-blocking-wait-queues-signals-and-mutexes) explains blocking and signal suspension:

```mermaid
%%{init: {"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }","theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"}}}%%
stateDiagram-v2
    [*] --> NEW: completed load
    NEW --> READY: run and build initial stack
    READY --> RUNNING: dispatcher
    RUNNING --> READY: timer or yield
    RUNNING --> BLOCKED: waitpid, sleep, empty stdin, or DMA load
    BLOCKED --> READY: wakeup, input, or DMA completion
    READY --> STOPPED: stop signal
    RUNNING --> STOPPED: stop signal
    BLOCKED --> STOPPED: stop signal remembers BLOCKED
    STOPPED --> BLOCKED: SIGCONT while still queued
    STOPPED --> READY: SIGCONT when wait is satisfied
    STOPPED --> STOPPED: pending terminal read without input ownership
    NEW --> ZOMBIE: termination or unload
    READY --> ZOMBIE: termination or signal
    RUNNING --> ZOMBIE: exit or fatal signal
    BLOCKED --> ZOMBIE: fatal signal
    STOPPED --> ZOMBIE: fatal signal
    ZOMBIE --> [*]: collection, orphan cleanup, or unload
```

### 4.1.2 Global process list and current process
[\[↑ TOC\]](#contents)

The diagram shows [`process_list_head`](kernel/process/process.picoc#L16),
[`process_list_tail`](kernel/process/process.picoc#L17), and [`active_process`](kernel/process/process.picoc#L18)
pointing to PCBs linked by [`next`](kernel/process/process.header#L53),
in SRAM (above) and as a process list (below):

![Kernel globals and three linked PCBs in SRAM, followed by a process-list view of those same PCB objects with process_list_head, process_list_tail, and active_process pointing to PCB 1, PCB 3, and PCB 2](documentation/images/memory-process-list.svg)

[`initialize_process_table()`](kernel/process/process.picoc#L21) clears the roots and resets the PID counter.
[`create_process()`](kernel/process/process.picoc#L89) allocates a PCB and appends it after the tail. The first
PCB becomes both head and tail.

[`process_list_head`](kernel/process/process.picoc#L16) starts lookup and scheduler wraparound.
[`process_list_tail`](kernel/process/process.picoc#L17) lets creation append in O(1) time, without scanning the
list. The scheduler itself does not use the tail.

Appending preserves creation order. [`scheduler_next_process()`](kernel/scheduler.picoc#L12) follows
[`next`](kernel/process/process.header#L53) and wraps to the head.

The shared-memory registry inserts at its head because it does not need
creation order. Both lists can link a node in O(1) time. This comparison
covers linking, rather than allocation or lookup:

| List | Insertion policy | Pointers and linking cost |
| --- | --- | --- |
| PCB list | [`create_process()`](kernel/process/process.picoc#L89) appends at the end | [`process_list_head`](kernel/process/process.picoc#L16) starts traversal, [`process_list_tail`](kernel/process/process.picoc#L17) makes append O(1). With only a head, append would take O(n) |
| [`SharedMemoryEntry`](kernel/shared_memory.header#L8) registry | [`open_shared_memory()`](kernel/shared_memory.picoc#L92) prepends at the beginning | Sets the new entry's [`next`](kernel/shared_memory.header#L14) to [`shared_memory_list_head`](kernel/shared_memory.picoc#L6), then moves the head to the new entry. A head alone makes insertion O(1) |

A shared-memory tail would add maintenance without improving insertion.
Name lookup and finding a predecessor for removal still require a scan.

[`remove_process()`](kernel/process/process.picoc#L209) finds the PCB and predecessor, bypasses the node, and
updates the head, tail, and current pointer as needed. [`7.1.2.2 Parent collection and final removal`](#7122-parent-collection-and-final-removal) explains
resource cleanup. [`7.1 Wait queues and PCB links`](#71-wait-queues-and-pcb-links) covers its separate wait-queue link.

The scheduler scans the process list directly. Wait queues use [`wait_next`](kernel/process/process.header#L51),
leaving [`next`](kernel/process/process.header#L53) for list order. [`6.1.1 Algorithm and Round Robin comparison`](#611-algorithm-and-round-robin-comparison) explains scheduler traversal.

#### 4.1.2.1 From PCBs to Process Payloads in SRAM
[\[↑ TOC\]](#contents)

[`base_address`](kernel/process/process.header#L34) connects each PCB to its Process Payload in the outer heap.
That allocation contains the image, user heap, and stack described in [`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy).
Its allocator header lies just before it.

In this two-process example, PCB 1 and PCB 2 occupy Kernel Heap payloads A
and C. Their green [`base_address`](kernel/process/process.header#L34) arrows reach the corresponding Process
Payloads. The middle allocation holds shared data:

![Complete SRAM with three blocks per heap and two kernel PCBs pointing through base_address to Process Payloads A and C](documentation/images/memory-process-payload-links.svg)

[`create_process()`](kernel/process/process.picoc#L89) stores the [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) address in [`base_address`](kernel/process/process.header#L34).
Adding code and data offsets gives [`activation.cs`](kernel/process/process.header#L27) and [`activation.ds`](kernel/process/process.header#L28).
Adding [`heap_start`](kernel/process/process.header#L36) gives the user-heap address.

## 4.2 Loading and starting a process
[\[↑ TOC\]](#contents)

[`load()`](library/unistd/process.picoc#L17) receives a program, and [`run()`](library/unistd/process.picoc#L31) prepares it to execute. Their
wrappers reach [`load_process_chunk()`](kernel/process/process_loader.picoc#L292) and [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241).
The dispatcher later restores the prepared activation, as shown in [`6.4 Restoring the selected process and returning with RTI`](#64-restoring-the-selected-process-and-returning-with-rti).

The memory diagrams below arrange addresses from lower to higher, left to
right. Region widths are illustrative.

### 4.2.1 Loading a process (`load` library call)
[\[↑ TOC\]](#contents)

Loading first receives the program into a reserved Process Payload, then
creates its [`ProcessControlBlock`](kernel/process/process.header#L31).
The two steps below distinguish the caller's temporary transfer record from
the child's PCB. Only after reception succeeds does the child receive a PID,
with [`state`](kernel/process/process.header#L33) set to [`NEW`](kernel/process/process.header#L12).

#### 4.2.1.1 Step 1: Receiving the process image
[\[↑ TOC\]](#contents)

[`begin_process_load()`](kernel/process/process_loader.picoc#L109) resolves the path,
validates the five-word binary header, applies heap and stack defaults, and
reserves the Process Payload with [`PSDMalloc()`](kernel/psdmalloc.picoc#L20).
The caller's [`pending_load`](kernel/process/process.header#L68) points to a
[`ProcessLoad`](kernel/process/process_loader.picoc#L14) that retains the destination
and transfer progress between syscalls. No child PCB exists yet.

The diagram follows the image from host storage through UART into SRAM,
using dashed arrows for data movement and solid arrows for stored pointers.
The kernel consumes the five-word header and copies only the following image
words into the User Process Image. The user heap and stack are reserved but
remain uninitialized:

![EPROM, the complete peripheral mapping, and SRAM with CPU-polling and DMA transfer paths into the newly allocated User Process Image, while the caller owns ProcessLoad](documentation/images/process-load-transfer.svg)

##### 4.2.1.1.1 `ProcessLoad` transfer record
[\[↑ TOC\]](#contents)

[`ProcessLoad`](kernel/process/process_loader.picoc#L14) is the temporary kernel-heap
record for an in-progress userspace load. The loading caller owns it through
[`pending_load`](kernel/process/process.header#L68). It preserves the reserved
payload's address, header values, copied binary path, and transfer progress
between syscalls, including while the caller waits for DMA completion.
The child PCB is created only after reception succeeds.

The table explains the struct's fields and the functions that use them.
[`9.1 Memory layout, allocation sources, and lifetimes`](#91-memory-layout-allocation-sources-and-lifetimes)
describes its allocation and ownership:

| Field | Meaning | Used by |
| --- | --- | --- |
| [`ProcessLoad.base_address`](kernel/process/process_loader.picoc#L15) | Absolute start of the reserved Process and Shared Data Heap region | First initialized by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), used by [`continue_process_load(owner)`](kernel/process/process_loader.picoc#L227), [`finish_process_load(owner)`](kernel/process/process_loader.picoc#L90), and [`cancel_process_load(process)`](kernel/process/process_loader.picoc#L76) |
| [`ProcessLoad.process_size`](kernel/process/process_loader.picoc#L16) | Total reserved cells for the User Process Image, User Process Heap, and User Process Stack | First initialized by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), passed to [`create_process()`](kernel/process/process.picoc#L89) by [`finish_process_load(owner)`](kernel/process/process_loader.picoc#L90) |
| [`ProcessLoad.code_start`](kernel/process/process_loader.picoc#L17), [`ProcessLoad.data_start`](kernel/process/process_loader.picoc#L18) | Linked code- and data-segment offsets from the binary header | First initialized by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), passed to [`create_process()`](kernel/process/process.picoc#L89) by [`finish_process_load(owner)`](kernel/process/process_loader.picoc#L90) |
| [`ProcessLoad.heap_start`](kernel/process/process_loader.picoc#L19), [`ProcessLoad.heap_size`](kernel/process/process_loader.picoc#L20) | Resolved userspace heap offset and cell count | First initialized by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), passed to [`create_process()`](kernel/process/process.picoc#L89) by [`finish_process_load(owner)`](kernel/process/process_loader.picoc#L90) |
| [`ProcessLoad.payload_word_count`](kernel/process/process_loader.picoc#L21) | Encoded program words after the five-word header | First initialized by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), bounds both DMA and polling transfers in [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109) and [`continue_process_load(owner)`](kernel/process/process_loader.picoc#L227) |
| [`ProcessLoad.loaded_word_count`](kernel/process/process_loader.picoc#L22) | Words copied by the polling transfer so far | First initialized to 0 by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), advanced and checked by [`continue_process_load(owner)`](kernel/process/process_loader.picoc#L227) |
| [`ProcessLoad.loading_bar_update`](kernel/process/process_loader.picoc#L23) | Next word count at which progress output is redrawn | First initialized by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), updated by [`continue_process_load(owner)`](kernel/process/process_loader.picoc#L227) |
| [`ProcessLoad.uses_dma`](kernel/process/process_loader.picoc#L24) | Whether the reserved image is being filled by one DMA transfer rather than polling chunks | First initialized to `false` and set to `true` by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), checked by [`continue_process_load(owner)`](kernel/process/process_loader.picoc#L227) and [`cancel_process_load(process)`](kernel/process/process_loader.picoc#L76) |
| [`ProcessLoad.path`](kernel/process/process_loader.picoc#L25) | Kernel-owned absolute binary path used by later range requests and copied into the completed PCB | First initialized by [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109), read by [`continue_process_load(owner)`](kernel/process/process_loader.picoc#L227) and [`finish_process_load(owner)`](kernel/process/process_loader.picoc#L90), freed by [`free_process_load(load)`](kernel/process/process_loader.picoc#L71) |

On success, [`finish_process_load()`](kernel/process/process_loader.picoc#L90)
passes the reserved payload to the new child PCB, clears the caller's
[`pending_load`](kernel/process/process.header#L68), and frees the transfer record
and its copied path. [`cancel_process_load()`](kernel/process/process_loader.picoc#L76) cancels active DMA
and releases the partial Process Payload and temporary transfer record if
reception fails.

#### 4.2.1.2 Step 2: Creating the child PCB
[\[↑ TOC\]](#contents)

After reception succeeds, [`create_process()`](kernel/process/process.picoc#L89)
creates the child's [`ProcessControlBlock`](kernel/process/process.header#L31).
The diagram shows its place in the process list and its pointers to the received
image, fresh descriptors, and preliminary stack:

![Completed load with the child PCB appended in the kernel heap, state NEW, fresh descriptors, initialized activation fields, and only one preliminary entry-PC cell on its stack](documentation/images/process-load-complete.svg)

#### 4.2.1.3 Process stack after `load`
[\[↑ TOC\]](#contents)

After a successful [`load()`](library/unistd/process.picoc#L17) returns the child PID,
[`create_process()`](kernel/process/process.picoc#L89) has initialized only one cell
of the child's reserved stack. The highest stack address, `highest_stack_address`,
is [`base_address`](kernel/process/process.header#L34) + [`size`](kernel/process/process.header#L35) - 1.
As in the initial stack table in [`4.2.2.1.2 Initial argc, argv, and envp`](#42212-initial-argc-argv-and-envp),
the stack is drawn vertically with lower addresses at the top and higher
addresses at the bottom. Stack growth is upward toward lower addresses.
The arrows connect the saved registers in the child's PCB to the stack cells
they point to:

![Child stack after load, lower addresses at the top and higher addresses at the bottom: saved activation.baf points to the only initialized stack cell at the bottom, while saved activation.sp points to the uninitialized cell immediately above it; stack growth is upward](documentation/images/process-loaded-stack.svg)

The bottom two stack boxes each represent one 32-bit cell. The larger top box
represents all remaining reserved stack cells. Saved
[`activation.baf`](kernel/process/process.header#L26) points to `highest_stack_address`.
Saved [`activation.sp`](kernel/process/process.header#L25) points one cell lower,
to `highest_stack_address - 1`. The cell at `highest_stack_address`
contains [`activation.cs`](kernel/process/process.header#L27) minus 1, the value
that `RTI` would consume from `SP + 1` before advancing PC.

The child's [`state`](kernel/process/process.header#L33) remains
[`NEW`](kernel/process/process.header#L12), so it cannot yet be selected to run.
There is no `argc`, `argv[]`, `envp[]`, or copied-string area. The other reserved
stack cells have unspecified contents because loading does not zero them.
[`run()`](library/unistd/process.picoc#L31) builds the complete
startup layout shown in [`4.2.2.1 Initial user process stack`](#4221-initial-user-process-stack).

#### 4.2.1.4 Load function reference
[\[↑ TOC\]](#contents)

The table starts with the syscall-backed loader, then lists transfer
helpers and the boot-time loader. [`4.2.2.3 Run function reference`](#4223-run-function-reference) covers run setup:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`load_process_chunk(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L292) | Positive PID when complete, 0 on failure, or [`SYSCALL_LOAD_PROCESS_CONTINUE`](common/syscall.header#L48) (-1) while work remains | Starts or resumes the caller-owned load. Successful completion creates a PCB with [`state`](kernel/process/process.header#L33) [`NEW`](kernel/process/process.header#L12) | [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`continue_process_load()`](kernel/process/process_loader.picoc#L227), [`current_process()`](kernel/process/process.picoc#L62)<br>**Host requests:** `file-size <path>` and `read-range <offset> <count> <path>` through helpers | **Library functions:** [`load()`](library/unistd/process.picoc#L17) via the syscall<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16) |
| <hr><hr> | <hr><hr> | <hr><hr> | <hr><hr> | <hr><hr> |
| [`load_process(path, show_loading_bar)`](kernel/process/process_loader.picoc#L305) | PID on success, 0 on rejected path, missing/short header, invalid stack placement, or exhausted process memory | Kernel boot-time continuous transfer. Reserves the Process Payload, receives the image, and creates the PCB | [`PSDMalloc()`](kernel/psdmalloc.picoc#L20), [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`create_process()`](kernel/process/process.picoc#L89), [`drain_process_words()`](kernel/process/process_loader.picoc#L40), [`loaded_process_stack_start()`](kernel/process/process_loader.picoc#L28), [`receive_word()`](common/uart_protocol.picoc#L7), [`receive_words_to_sram()`](common/sram_loader.picoc#L6), [`system_relative_path()`](kernel/filesystem/host_filesystem.picoc#L121), [`uart_print_loading_bar_label()`](common/loading_bar.picoc#L6), [`uart_print_string()`](common/uart_protocol.picoc#L73), [`uart_send_host_request()`](common/uart_protocol.picoc#L82)<br>**Host requests:** `load <path>` | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31) in [`kernel/kernel.picoc`](kernel/kernel.picoc) |
| [`begin_process_load(path, show_loading_bar, caller_context)`](kernel/process/process_loader.picoc#L109) | PID for an empty payload, continuation status after transfer setup, or 0 on path/header/allocation/transfer failure | Reads the header, reserves memory, allocates [`ProcessLoad`](kernel/process/process_loader.picoc#L14) and its path, sets [`caller.pending_load`](kernel/process/process.header#L68), initializes progress, and optionally starts blocking DMA | [`PSDMalloc()`](kernel/psdmalloc.picoc#L20), [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`cancel_process_load()`](kernel/process/process_loader.picoc#L76), [`copy_process_path()`](kernel/process/process.picoc#L70), [`current_process()`](kernel/process/process.picoc#L62), [`dma_is_active()`](common/dma.picoc#L17), [`drain_process_bytes()`](kernel/process/process_loader.picoc#L62), [`finish_process_load()`](kernel/process/process_loader.picoc#L90), [`kmalloc()`](kernel/kmalloc.picoc#L23), [`loaded_process_stack_start()`](kernel/process/process_loader.picoc#L28), [`receive_word()`](common/uart_protocol.picoc#L7), [`start_dma_uart_receive()`](kernel/dma.picoc#L18), [`system_relative_path()`](kernel/filesystem/host_filesystem.picoc#L121), [`uart_print_loading_bar_label()`](common/loading_bar.picoc#L6), [`uart_print_string()`](common/uart_protocol.picoc#L73), [`uart_send_file_range_command()`](common/uart_protocol.picoc#L90), [`uart_send_host_request()`](common/uart_protocol.picoc#L82), [`uart_start_loading_bar()`](common/loading_bar.picoc#L43)<br>**Host requests:** `file-size <path>`, `read-range 0 20 <path>`, optional whole-payload `read-range 20 <count> <path>` | **Kernel functions:** [`load_process_chunk()`](kernel/process/process_loader.picoc#L292) |
| [`continue_process_load(owner)`](kernel/process/process_loader.picoc#L227) | PID on completion, continuation status while DMA is busy or polling work remains, or 0 on transfer failure | Checks DMA status or polls up to 256 payload words, advances [`loaded_word_count`](kernel/process/process_loader.picoc#L22) and progress, completes or cancels the load | [`cancel_process_load()`](kernel/process/process_loader.picoc#L76), [`dma_transfer_status()`](common/dma.picoc#L21), [`drain_process_bytes()`](kernel/process/process_loader.picoc#L62), [`finish_process_load()`](kernel/process/process_loader.picoc#L90), [`receive_word()`](common/uart_protocol.picoc#L7), [`uart_send_file_range_command()`](common/uart_protocol.picoc#L90), [`uart_update_loading_bar()`](common/loading_bar.picoc#L58)<br>**Host requests:** Polling `read-range <offset> <count> <path>` | **Kernel functions:** [`load_process_chunk()`](kernel/process/process_loader.picoc#L292) |
| [`finish_process_load(owner)`](kernel/process/process_loader.picoc#L90) | New PID | Creates the child PCB after transfer, clears [`owner.pending_load`](kernel/process/process.header#L68), and frees temporary load metadata and its copied path | [`create_process()`](kernel/process/process.picoc#L89), [`free_process_load()`](kernel/process/process_loader.picoc#L71), [`system_relative_path()`](kernel/filesystem/host_filesystem.picoc#L121) | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`continue_process_load()`](kernel/process/process_loader.picoc#L227) |
| [`create_process(base_address, size, code_start, data_start, heap_start, heap_size, binary_path)`](kernel/process/process.picoc#L89) | PCB pointer. Kernel-heap exhaustion halts the OS through allocation checks | Assigns PID and [`state`](kernel/process/process.header#L33) [`NEW`](kernel/process/process.header#L12), records memory fields, initializes [`activation`](kernel/process/process.header#L40), queues and signals, creates standard descriptors, copies paths and parent-derived metadata, writes the preliminary entry PC, and appends the PCB | [`copy_process_path()`](kernel/process/process.picoc#L70), [`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35), [`current_process()`](kernel/process/process.picoc#L62), [`kmalloc()`](kernel/kmalloc.picoc#L23) | **Kernel functions:** [`finish_process_load()`](kernel/process/process_loader.picoc#L90), [`load_process()`](kernel/process/process_loader.picoc#L305) |
| [`copy_process_path(path)`](kernel/process/process.picoc#L70) | New kernel-owned string pointer | Allocates and copies a path including its terminator | [`kmalloc()`](kernel/kmalloc.picoc#L23) | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`create_process()`](kernel/process/process.picoc#L89), [`set_process_working_directory()`](kernel/filesystem/host_filesystem.picoc#L128) |
| [`loaded_process_stack_start(heap_start, heap_size, stack_start)`](kernel/process/process_loader.picoc#L28) | Highest process-relative stack offset, or [`PSDMALLOC_INVALID_START`](kernel/psdmalloc.header#L3) for overlap | Resolves the default highest stack offset or checks an explicit offset, no memory writes | None | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`load_process()`](kernel/process/process_loader.picoc#L305) |
| [`cancel_process_load(process)`](kernel/process/process_loader.picoc#L76) | No return value | Cancels busy DMA if needed, clears [`process.pending_load`](kernel/process/process.header#L68), frees the partial Process Payload and temporary metadata | [`PSDFree()`](kernel/psdmalloc.picoc#L47), [`cancel_dma_transfer()`](common/dma.picoc#L32), [`dma_transfer_status()`](common/dma.picoc#L21), [`free_process_load()`](kernel/process/process_loader.picoc#L71) | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`continue_process_load()`](kernel/process/process_loader.picoc#L227), [`remove_process()`](kernel/process/process.picoc#L209) |
| [`free_process_load(load)`](kernel/process/process_loader.picoc#L71) | No return value | Frees the temporary kernel-owned host path and [`ProcessLoad`](kernel/process/process_loader.picoc#L14) | [`kfree()`](kernel/kmalloc.picoc#L38) | **Kernel functions:** [`cancel_process_load()`](kernel/process/process_loader.picoc#L76), [`finish_process_load()`](kernel/process/process_loader.picoc#L90) |
| [`drain_process_words(payload_word_count, show_loading_bar)`](kernel/process/process_loader.picoc#L40) | No return value | Consumes a rejected continuous payload so UART remains synchronized, optionally reports progress | [`receive_word()`](common/uart_protocol.picoc#L7), [`uart_start_loading_bar()`](common/loading_bar.picoc#L43), [`uart_update_loading_bar()`](common/loading_bar.picoc#L58) | **Kernel functions:** [`load_process()`](kernel/process/process_loader.picoc#L305) |
| [`drain_process_bytes(byte_count)`](kernel/process/process_loader.picoc#L62) | No return value | Consumes unexpected positive range-response data so UART remains synchronized | [`receive_byte_over_uart()`](kernel/uart_hardware.picoc#L24) | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`continue_process_load()`](kernel/process/process_loader.picoc#L227) |

The directly linked transfer helper is shared by bootloader and kernel:

| Kernel / Library Function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`receive_words_to_sram(base_address, word_count, show_loading_bar)`](common/sram_loader.picoc#L6) (Shared/Common) | No return value | Receives word_count cells at base_address. Polls UART without DMA, otherwise starts DMA and busy-waits for its status, updates requested loading progress | [`dma_is_active()`](common/dma.picoc#L17), [`dma_transfer_status()`](common/dma.picoc#L21), [`receive_word()`](common/uart_protocol.picoc#L7), [`start_dma_uart_transfer()`](common/dma.picoc#L25), [`uart_start_loading_bar()`](common/loading_bar.picoc#L43), [`uart_update_loading_bar()`](common/loading_bar.picoc#L58) | **Kernel functions:** [`load_process()`](kernel/process/process_loader.picoc#L305)<br>**Bootloader functions:** [`boot_main()`](boot/bootloader.picoc#L41) |

### 4.2.2 Starting a process (`run` library call)
[\[↑ TOC\]](#contents)

Starting finishes the process setup in this order:

1. Pack the PID, raw arguments, and selected environment into a
   [`RunProcessRequest`](common/syscall.header#L55). A `NULL` environment selects the caller's environment.
   A custom null-terminated array replaces it. [`4.2.2.2.1 Environment origin and propagation`](#42221-environment-origin-and-propagation)
   explains how the library selects the environment.
2. Find the PCB and require [`state`](kernel/process/process.header#L33) to be [`NEW`](kernel/process/process.header#L12).
3. Copy inheritable descriptors from the run caller.
4. Copy arguments and environment strings to the child stack, build their
   pointer arrays, and update [`activation.sp`](kernel/process/process.header#L25) and [`activation.baf`](kernel/process/process.header#L26).
5. Set [`state`](kernel/process/process.header#L33) to [`READY`](kernel/process/process.header#L13) and return success.

The diagram shows the descriptor and stack changes in SRAM, with the caller's
arguments and environment in separate buffers. The user heap remains reserved
until userspace startup:

![Run changes inside the same SRAM layout: inherited descriptor table, copied caller arguments and environment, new stack and activation pointers, and state NEW to READY](documentation/images/process-run-setup.svg)

The shell separates the command name, expands variables, and passes the
remaining argument string to [`run()`](library/unistd/process.picoc#L31). The kernel splits it on spaces and
tabs, preserving quoted whitespace and removing matching quotes. It builds
the pointer array itself. [`12.4 Command parsing, expansion, and execution`](#124-command-parsing-expansion-and-execution) explains shell parsing.

The kernel copies the request's strings into the child stack.
[`4.2.2.1 Initial user process stack`](#4221-initial-user-process-stack) below shows
the prepared layout, including a concrete diagram for `add.bin`.

Setting [`READY`](kernel/process/process.header#L13) permits later scheduling. The call does not load the CPU
registers immediately. On first dispatch, [`_start()`](library/start/start.picoc#L14) initializes the heap
and environment before entering the application.

#### 4.2.2.1 Initial user process stack
[\[↑ TOC\]](#contents)

This is the child stack prepared by a successful [`run()`](library/unistd/process.picoc#L31)
call, before the child executes its first instruction. Setup completes the
stack before setting [`state`](kernel/process/process.header#L33) to [`READY`](kernel/process/process.header#L13).
The preliminary entry PC left by [`load()`](library/unistd/process.picoc#L17) is replaced
by the layout below. The scheduler may dispatch the child before the caller
resumes; these figures show the prepared startup stack.

##### 4.2.2.1.1 User process stack placement
[\[↑ TOC\]](#contents)

The teal highlight locates one process's stack after its image and heap.
The lower view expands Process Payload A, excluding its outer allocator
header. Other processes have their own stacks in separate Process Payloads:

![Complete SRAM expanded into Process Payload A, with both the payload and its User Process Stack highlighted by matching teal fills and thick amber borders](documentation/images/process-stack-placement.svg)

[`base_address`](kernel/process/process.header#L34) starts the payload, and [`size`](kernel/process/process.header#L35) includes image, heap, and
stack. Its highest stack cell is `base_address + size - 1`. Growth proceeds
toward the heap, whose final cell forms the lower boundary.

The binary header supplies the reservation. A heap size of `-1` selects
[`DEFAULT_PROCESS_HEAP_CELLS`](kernel/process/process_loader.header#L6), currently 1000. A stack start of `-1` selects
`heap_start + heap_size + DEFAULT_PROCESS_STACK_CELLS`, also currently 1000.
Because this is the inclusive highest offset, it reserves 1001 cells beyond
the heap. The loader rejects a stack start inside the heap and adds one to
the effective offset for the allocation size.

##### 4.2.2.1.2 Initial `argc`, `argv`, and `envp`
[\[↑ TOC\]](#contents)

[`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) fills the high end of that reservation during
run setup. These values belong to runtime stack storage, separate from the
linked image copied during loading.

[`argc`](kernel/process/process_arguments.picoc#L131) includes the executable path, and `envc` counts environment entries.
These names describe the layout rather than additional PCB fields:

| Name | Meaning | Calculation |
| --- | --- | --- |
| `startup_cell_count` | Number of cells needed for all startup values and strings | Sum shown below |
| `entry_pc_address` | Address of the cell holding the entry PC | `base_address + size - startup_cell_count` |
| `strings_start_address` | Address of the first copied string character | `entry_pc_address + argc + envc + 4` |
| `highest_stack_address` | Address of the highest reserved stack cell | `base_address + size - 1` |

Each ordinary row represents one 32-bit cell, even for a character. `...`
stands for omitted cells:

| Cell address | Stored value |
| --- | --- |
| **↑ Decreasing addresses** | **Lower addresses · stack grows ↑** |
| `entry_pc_address` | Entry PC = [`activation.cs`](kernel/process/process.header#L27) minus 1 |
| `entry_pc_address + 1` | [`argc`](kernel/process/process_arguments.picoc#L131) |
| `entry_pc_address + 2` | [`argv[0]`](kernel/process/process_arguments.picoc#L184) |
| `...` | `...` |
| `entry_pc_address + argc + 2` | [`argv[argc] = NULL`](kernel/process/process_arguments.picoc#L180) |
| `entry_pc_address + argc + 3` | [`envp[0]`](kernel/process/process_arguments.picoc#L225) |
| `...` | `...` |
| `entry_pc_address + argc + envc + 3` | [`envp[envc] = NULL`](kernel/process/process_arguments.picoc#L181) |
| `strings_start_address` | First character of the copied [`binary_path`](kernel/process/process.header#L38) |
| `strings_start_address + 1` | Next character of the path, or its `\0` terminator |
| `...` | Remaining path, argument, and environment characters and `\0` terminators |
| `highest_stack_address` | Last string's `\0` |
| **↓ Increasing addresses** | **Higher addresses** |

The pointers address copied strings on the child stack. `argv[0]` holds
the executable path without its leading `/`, followed by arguments and
`NAME=value` environment strings. Every string has a zero terminator, and
each pointer array ends in `NULL`.

[`argv`](kernel/process/process_arguments.picoc#L140) is the address of the first argument-pointer cell at
`entry_pc_address + 2`. [`envp`](kernel/process/process_arguments.picoc#L141) begins at `argv + argc + 1`. Neither is an
extra cell holding an array pointer.

Setup uses the existing reservation without checking that all startup data
fits above the heap. This calculation includes the entry PC, counts, pointer
sentinels, and string terminators:

```text
startup_cell_count = 1 + 1 + argc + 1 + envc + 1
    + cells(binary_path including its terminator)
    + cells(all argument strings including their terminators)
    + cells(all environment strings including their terminators)
```

Setup saves `activation.sp = entry_pc_address - 1` and
`activation.baf = entry_pc_address - 2`. The first `RTI` consumes the entry
PC. [`_start()`](library/start/start.picoc#L14) reads [`argc`](kernel/process/process_arguments.picoc#L131) at `BAF + 3` and [`argv`](kernel/process/process_arguments.picoc#L140) at `BAF + 4`.
[`start_process()`](library/start/start.picoc#L7) finds [`envp`](kernel/process/process_arguments.picoc#L141) after [`argv`](kernel/process/process_arguments.picoc#L140), initializes the heap, and copies
the environment into heap storage before calling `main()`.

The comparison is the **System V ABI, Intel386 Architecture Processor
Supplement, Process Initialization**, [Figure 3-31](https://refspecs.linuxbase.org/elf/abi386-4.pdf#page=54). PicoOS keeps its order of
argument count, argument pointers, null sentinel, environment pointers, and
null sentinel. RETI adds an entry-PC cell, uses word addresses and one cell
per character, and omits the auxiliary vector. It also fixes string order,
which the Intel386 ABI leaves unspecified. This is an adaptation, rather
than Intel386 ABI compliance.

[POSIX.1-2024 `exec`](https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html) and [environment conventions](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html) define the source-level
arrays and `NAME=value` strings. They do not prescribe their physical stack
layout. PicoOS shares these representations but uses separate [`load()`](library/unistd/process.picoc#L17) and
[`run()`](library/unistd/process.picoc#L31) calls rather than POSIX `exec`.

<!-- Presentation: mention the System V Intel386 initial-process-stack comparison,
     distinguish POSIX source-level conventions, and explain the RETI adaptations. -->

###### 4.2.2.1.2.1 Concrete initial-stack example
[\[↑ TOC\]](#contents)

Save this program as `add.picoc` and link it with [`libstart`](library/start/libstart.picoc) and [`libstdlib`](library/stdlib/libstdlib.picoc).
It adds two arguments when environment variable `X` is `1`:

```c
#include "library/stdlib/stdlib.header"

int main(int argc, char **argv) {
    char *enabled = getenv("X");

    if (argc == 3 && enabled != NULL && atoi(enabled) == 1) {
        return atoi(argv[1]) + atoi(argv[2]);
    }
    return 0;
}
```

The launcher passes `2`, `3`, and a null-terminated environment array. With
successful loading and starting, [`waitpid()`](library/sys/wait/wait.picoc#L14) returns the result `5`:

```c
#include "library/unistd/unistd.header"
#include "library/sys/wait/wait.header"

int main(void) {
    char *environment[3];
    int pid = load("/add.bin");

    environment[0] = "X=1";
    environment[1] = "Y=0";
    environment[2] = NULL;
    run(pid, "2 3", environment);
    return waitpid(pid);
}
```

`argc = 3` and two environment entries occupy 29 startup cells. Thus
`entry_pc_address = base_address + size - 29`. Read the rows in order. Each
box is one cell labeled by its offset, and the pointer values stored there
are absolute addresses:

![Initial stack for add.bin with two arguments, 2 and 3, and two environment variables, X=1 and Y=0, showing cell offsets from entry_pc_address, absolute pointer targets by offset, both address directions, and continuation arrows between rows](documentation/images/process-initial-stack-example.svg)

`SP` is saved one cell below the entry PC and `BAF` two cells below it.
The last string terminator overwrites the preliminary entry PC at the top
of the stack. The final entry PC now lies below [`argc`](kernel/process/process_arguments.picoc#L131).

#### 4.2.2.2 Parent-to-child inheritance
[\[↑ TOC\]](#contents)

The diagram shows what the child inherits during [`load()`](library/unistd/process.picoc#L17)
and [`run()`](library/unistd/process.picoc#L31), and where the copies are stored:

![Complete SRAM map with compact Kernel Image, Kernel Stack and Process and Shared Data Heap regions surrounding detailed Kernel Heap allocations for parent and child PCBs, independent directory strings and descriptor tables, with pointers and copy operations](documentation/images/process-inheritance.svg)

##### 4.2.2.2.1 Environment origin and propagation
[\[↑ TOC\]](#contents)

The kernel stores no environment pointer in the PCB. It starts init with
null arguments and environment, giving it only `argv[0]` and an empty
environment. Init then reads the configuration. [`11.2.1 Loading init and entering normal execution`](#1121-loading-init-and-entering-normal-execution) covers its first
dispatch.

Each image has its own [`environ`](library/stdlib/env.picoc#L4) global. It points to a
null-terminated array of `NAME=value` string pointers in that process's heap.
Both the array and its strings belong to that process. [`start_process()`](library/start/start.picoc#L7) initializes it
with an independent heap array. Init then reads up to 256 cells from
[`config/environment.txt`](config/environment.txt) and parses `NAME=value` entries. Invalid input or
file and allocation failures stop init startup.

[`setenv()`](library/stdlib/env.picoc#L126) stores independent strings, so init can release the read buffer.
The current file supplies `PATH=/user`. Init optionally adds
[`PICOOS_LOADING_BAR`](common/loading_bar.header#L5) before starting the shell.

Passing `NULL` as the environment argument to [`run()`](library/unistd/process.picoc#L31)
selects the caller's current environment at run time, rather than at
[`load()`](library/unistd/process.picoc#L17) time. The library calls
[`current_environment()`](library/stdlib/env.picoc#L6), which simply returns
the calling image's [`environ`](library/stdlib/env.picoc#L4) global, and stores
that pointer in [`RunProcessRequest.environment`](common/syscall.header#L58)
before invoking the syscall. It does not look up the recorded parent through
[`parent_pid`](kernel/process/process.header#L57). The environment comes from
the process calling [`run()`](library/unistd/process.picoc#L31).

A custom null-terminated array of `NAME=value` strings is stored in
[`RunProcessRequest.environment`](common/syscall.header#L58) instead. It replaces
the default completely without merging entries. To supply an empty environment,
pass an array whose first entry is `NULL`, rather than a `NULL` array pointer.
Thus [`run(shell_pid, NULL, NULL)`](library/unistd/process.picoc#L31) selects
init's environment. The kernel's direct boot call bypasses this library
selection, so init itself starts empty.

Environment propagation makes two copies. First, [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125)
copies strings onto the child stack, builds pointers to those copies, and
updates its saved stack registers. [`4.2.2.1.2 Initial argc, argv, and envp`](#42212-initial-argc-argv-and-envp) shows the layout.

At first dispatch, [`initialize_environment()`](library/stdlib/env.picoc#L97) copies that stack array and
its strings into the child heap, then assigns [`environ`](library/stdlib/env.picoc#L4). Later environment
changes affect neither the initial stack nor the parent's copies.

The tree shows the kernel loading and starting [`init`](system/init.picoc),
which reads `PATH=/user` from [`config/environment.txt`](config/environment.txt)
through [`read_environment()`](system/init.picoc#L19). It then follows `PATH`
through the [`shell`](user/shell.picoc) and two child generations. Each process box shows only the
`PATH` entry in that process's [`environ`](library/stdlib/env.picoc#L4), after
any local change. The three branches remove, change, or keep the entry, then
pass their result to another child through
[`run(cpid, "arg1", NULL)`](library/unistd/process.picoc#L31). `cpid1` through
`cpid6` denote the PIDs returned by preceding
[`load()`](library/unistd/process.picoc#L17) calls:

![Environment origin and inheritance tree showing the kernel loading and starting init with an empty environment, init reading PATH=/user from config/environment.txt, and the shell's three child branches removing, changing, or keeping PATH before passing it to their children](documentation/images/process-environment-propagation.svg)

The [`shell`](user/shell.picoc) passes its environment through the `NULL`
environment argument inside [`run_process()`](user/shell.picoc#L1034).
Its `export NAME=value` built-in calls
[`setenv()`](library/stdlib/env.picoc#L126) to update the shell's own
[`environ`](library/stdlib/env.picoc#L4). The changes in the tree happen in the
shell's children, so the shell and the other branches keep `PATH=/user`.

[`unsetenv("PATH")`](library/stdlib/env.picoc#L157) removes and frees an entry.
[`setenv("PATH", "/test", true)`](library/stdlib/env.picoc#L126) replaces one. These changes affect the
caller and children started afterward. Existing processes keep their copies.
[`getenv()`](library/stdlib/env.picoc#L115) returns a pointer to the value or `NULL`. [`10.2.7.3 Environment operations in env.picoc`](#10273-environment-operations-in-envpicoc) covers the API.

##### 4.2.2.2.2 Loading-bar environment variable
[\[↑ TOC\]](#contents)

The early boot flag [`loading_bar_enabled`](config/config.header#L5) makes init add
[`PICOOS_LOADING_BAR=true`](common/loading_bar.header#L5). The shell and its applications inherit the entry.

[`load()`](library/unistd/process.picoc#L17) and [`read()`](library/unistd/io.picoc#L6) test whether the variable is present. A value of
`false` still enables bars. Remove the entry with [`unsetenv()`](library/stdlib/env.picoc#L157) to disable them.

`cat.bin` removes its inherited entry before reading, keeping progress bars
out of file contents. The constant names the environment variable:

```c
int main(int argc, char **argv) {
    // ...
    unsetenv(LOADING_BAR_ENVIRONMENT_VARIABLE);
    // ...
}
```

This affects only cat's environment. The shell can still show a bar while
loading cat.

#### 4.2.2.3 Run function reference
[\[↑ TOC\]](#contents)

The syscall-backed start helper appears first, followed by its parsing and
stack-copying helpers. [`8.6 File-descriptor creation, inheritance, duplication, and cleanup`](#86-file-descriptor-creation-inheritance-duplication-and-cleanup) covers descriptor inheritance:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`mark_process_ready_with_arguments(request)`](kernel/process/process_arguments.picoc#L241) | true after setup, false for missing PID or [`state`](kernel/process/process.header#L33) other than [`NEW`](kernel/process/process.header#L12) | Copies current caller descriptors when present, writes the child stack, updates [`activation.sp`](kernel/process/process.header#L25) and [`activation.baf`](kernel/process/process.header#L26), then sets [`state`](kernel/process/process.header#L33) to [`READY`](kernel/process/process.header#L13). Init keeps its original table because no current process exists | [`current_process()`](kernel/process/process.picoc#L62), [`destroy_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L118), [`find_process_by_pid()`](kernel/process/process.picoc#L162), [`inherit_file_descriptors()`](kernel/filesystem/file_descriptor.picoc#L99), [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) | **Library functions:** [`run()`](library/unistd/process.picoc#L31) via the syscall<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16), [`main()`](kernel/kernel.picoc#L31) in [`kernel/kernel.picoc`](kernel/kernel.picoc) |
| <hr><hr> | <hr><hr> | <hr><hr> | <hr><hr> | <hr><hr> |
| [`store_process_arguments(process, arguments, environment)`](kernel/process/process_arguments.picoc#L125) | No return value | Copies path, tokens, and selected NAME=value strings into the child User Process Stack, writes entry PC/count/arrays/NULL sentinels, and saves [`activation.sp`](kernel/process/process.header#L25) and [`activation.baf`](kernel/process/process.header#L26) | [`copy_process_string()`](kernel/process/process_arguments.picoc#L113), [`process_argument_is_quote()`](kernel/process/process_arguments.picoc#L9), [`process_argument_is_space()`](kernel/process/process_arguments.picoc#L5), [`process_argument_string_cell_count()`](kernel/process/process_arguments.picoc#L51), [`process_argument_token_count()`](kernel/process/process_arguments.picoc#L14), [`process_environment_count()`](kernel/process/process_arguments.picoc#L89), [`process_string_cell_count()`](kernel/process/process_arguments.picoc#L103) | **Kernel functions:** [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241) |
| [`process_argument_token_count(arguments)`](kernel/process/process_arguments.picoc#L14) | Number of argument tokens, 0 for NULL | Reads the raw string, treating space/tab outside matching quotes as separators | [`process_argument_is_quote()`](kernel/process/process_arguments.picoc#L9), [`process_argument_is_space()`](kernel/process/process_arguments.picoc#L5) | **Kernel functions:** [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) |
| [`process_argument_string_cell_count(arguments)`](kernel/process/process_arguments.picoc#L51) | Copied argument characters plus one terminator per token, 0 for NULL | Counts the exact argument-string cells after matching quote removal | [`process_argument_is_quote()`](kernel/process/process_arguments.picoc#L9), [`process_argument_is_space()`](kernel/process/process_arguments.picoc#L5) | **Kernel functions:** [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) |
| [`process_argument_is_space(value)`](kernel/process/process_arguments.picoc#L5) | true for space or tab, otherwise false | Classifies one input character, no writes | None | **Kernel functions:** [`process_argument_string_cell_count()`](kernel/process/process_arguments.picoc#L51), [`process_argument_token_count()`](kernel/process/process_arguments.picoc#L14), [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) |
| [`process_argument_is_quote(value)`](kernel/process/process_arguments.picoc#L9) | true for single or double quote, otherwise false | Classifies one input character, no writes | None | **Kernel functions:** [`process_argument_string_cell_count()`](kernel/process/process_arguments.picoc#L51), [`process_argument_token_count()`](kernel/process/process_arguments.picoc#L14), [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) |
| [`process_environment_count(environment)`](kernel/process/process_arguments.picoc#L89) | Number of entries before NULL, 0 for NULL array | Reads the selected environment pointer array | None | **Kernel functions:** [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) |
| [`process_string_cell_count(value)`](kernel/process/process_arguments.picoc#L103) | Number of character cells including the zero terminator | Reads one null-terminated string | None | **Kernel functions:** [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) |
| [`copy_process_string(target, source)`](kernel/process/process_arguments.picoc#L113) | Address of the first cell after the copied zero terminator | Copies a string and its terminator to the destination stack area | None | **Kernel functions:** [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125) |

## 4.3 Process list, PCB metadata, and lifecycle function reference
[\[↑ TOC\]](#contents)

These functions manage process metadata, list membership, termination, and
removal. [`4.2.1.4 Load function reference`](#4214-load-function-reference) covers loading, [`4.2.2.3 Run function reference`](#4223-run-function-reference) covers starting, and [`7.1.3 Wait queue function reference`](#713-wait-queue-function-reference) covers
wait queues:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`list_processes(void)`](kernel/process/process.picoc#L32) | No return value | Traverses the process list and writes each PID and stable binary path through descriptor 1 | [`first_process()`](kernel/process/process.picoc#L28), [`system_relative_path()`](kernel/filesystem/host_filesystem.picoc#L121), [`uart_append_decimal()`](common/uart_protocol.picoc#L26), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217)<br>**Host requests:** Output through a regular file uses `write-at <offset> <path>`, optional append `file-size <path>`, then `write stdout`. Terminal stderr uses `write stderr`, then `write stdout`. Terminal stdout or null needs no host request | **Library functions:** [`list_processes()`](library/unistd/process.picoc#L51) via the syscall<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16)<br>**User applications:** [`main()`](user/ps.picoc#L11) in [`user/ps.picoc`](user/ps.picoc) |
| [`unload_process_by_pid(pid)`](kernel/process/process.picoc#L328) | true after removal, false for a missing or currently active PID | Terminates with success status and forces final removal, including an uncollected zombie | [`find_process_by_pid()`](kernel/process/process.picoc#L162), [`remove_process()`](kernel/process/process.picoc#L209), [`terminate_process()`](kernel/process/process.picoc#L304) | **Library functions:** [`unload()`](library/unistd/process.picoc#L47) via the syscall<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`exit_process(status)`](kernel/process/process.picoc#L430) | Does not return normally | Terminates the current process and dispatches another process, shuts down if none remain | [`current_process()`](kernel/process/process.picoc#L62), [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55), [`shutdown()`](kernel/kernel.picoc#L15), [`terminate_process()`](kernel/process/process.picoc#L304) | **Library functions:** [`exit()`](library/stdlib/exit.picoc#L3) via the syscall<br>**Kernel functions:** [`handle_cpu_exception()`](kernel/exception.picoc#L70), [`handle_process_heap_full_exception()`](kernel/exception.picoc#L82), [`handle_syscall()`](kernel/syscall.picoc#L16)<br>**CPU exceptions:** through [`handle_cpu_exception()`](kernel/exception.picoc#L70) |
| [`process_heap_start(void)`](kernel/process/process.picoc#L418) | Absolute current-process heap address | Adds [`base_address`](kernel/process/process.header#L34) to [`heap_start`](kernel/process/process.header#L36), no writes | [`current_process()`](kernel/process/process.picoc#L62) | **Library functions:** [`init_process_heap()`](library/stdlib/malloc.picoc#L18) via the syscall<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`process_heap_size(void)`](kernel/process/process.picoc#L424) | Current-process heap cell count | Reads [`heap_size`](kernel/process/process.header#L37), no writes | [`current_process()`](kernel/process/process.picoc#L62) | **Library functions:** [`init_process_heap()`](library/stdlib/malloc.picoc#L18) via the syscall<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16) |
| <hr><hr> | <hr><hr> | <hr><hr> | <hr><hr> | <hr><hr> |
| [`initialize_process_table(void)`](kernel/process/process.picoc#L21) | No return value | Clears head, tail, and [`active_process`](kernel/process/process.picoc#L18), resets [`next_process_id`](kernel/process/process.picoc#L19) to 1 | None | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31) in [`kernel/kernel.picoc`](kernel/kernel.picoc) |
| [`first_process(void)`](kernel/process/process.picoc#L28) | Head PCB pointer or NULL | Reads [`process_list_head`](kernel/process/process.picoc#L16) | None | **Kernel functions:** [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55), [`list_processes()`](kernel/process/process.picoc#L32) in [`kernel/process/process.picoc`](kernel/process/process.picoc), [`scheduler_next_process()`](kernel/scheduler.picoc#L12) |
| [`current_process(void)`](kernel/process/process.picoc#L62) | Current PCB pointer or NULL | Reads [`active_process`](kernel/process/process.picoc#L18) | None | **Kernel functions:** [`activate_current_process_stack_boundary()`](kernel/exception.picoc#L22), [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`change_working_directory()`](kernel/filesystem/host_filesystem.picoc#L163), [`close_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L146), [`create_process()`](kernel/process/process.picoc#L89), [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71), [`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43), [`duplicate_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L163), [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375), [`exit_process()`](kernel/process/process.picoc#L430), [`get_working_directory()`](kernel/filesystem/host_filesystem.picoc#L156), [`handle_syscall()`](kernel/syscall.picoc#L16), [`load_process_chunk()`](kernel/process/process_loader.picoc#L292), [`map_shared_memory()`](kernel/shared_memory.picoc#L130), [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241), [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`process_heap_size()`](kernel/process/process.picoc#L424), [`process_heap_start()`](kernel/process/process.picoc#L418), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`scheduler_next_process()`](kernel/scheduler.picoc#L12), [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268), [`send_signal_to_process()`](kernel/signal.picoc#L75), [`set_foreground_process()`](kernel/signal.picoc#L148) in [`kernel/signal.picoc`](kernel/signal.picoc), [`set_parent_death_signal()`](kernel/signal.picoc#L137), [`terminal_input_process()`](kernel/signal.picoc#L178), [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |
| [`set_current_process(process)`](kernel/process/process.picoc#L66) | No return value | Replaces [`active_process`](kernel/process/process.picoc#L18) | None | **Kernel functions:** [`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43) |
| [`find_process_by_pid(pid)`](kernel/process/process.picoc#L162) | Matching PCB pointer or NULL | Traverses [`process_list_head`](kernel/process/process.picoc#L16) through PCB next | None | **Kernel functions:** [`handle_terminal_signal_character()`](kernel/signal.picoc#L192), [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241), [`send_signal_by_pid()`](kernel/signal.picoc#L108), [`set_foreground_process()`](kernel/signal.picoc#L148) in [`kernel/signal.picoc`](kernel/signal.picoc), [`terminal_input_process()`](kernel/signal.picoc#L178), [`terminate_process()`](kernel/process/process.picoc#L304), [`unload_process_by_pid()`](kernel/process/process.picoc#L328), [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) |
| [`terminate_process(process, status)`](kernel/process/process.picoc#L304) | No return value, no effect for NULL or an existing zombie | Handles children, records [`exit_status`](kernel/process/process.header#L60), sets [`state`](kernel/process/process.header#L33) [`ZOMBIE`](kernel/process/process.header#L17), hands off status and wakes [`waiters`](kernel/process/process.header#L46), removes the PCB when no parent remains or its waiting parent received the status | [`find_process_by_pid()`](kernel/process/process.picoc#L162), [`orphan_and_signal_children()`](kernel/process/process.picoc#L279), [`process_has_waiting_parent()`](kernel/process/process.picoc#L249), [`remove_process()`](kernel/process/process.picoc#L209), [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) | **Kernel functions:** [`exit_process()`](kernel/process/process.picoc#L430), [`kill_process()`](kernel/signal.picoc#L71), [`unload_process_by_pid()`](kernel/process/process.picoc#L328) |
| [`remove_process(process)`](kernel/process/process.picoc#L209) | No return value, no effect when absent from the list | Unlinks queue and process-list membership, adjusts list roots, releases shared mappings, cancels partial loading, frees Process Payload, descriptor objects, PCB-owned strings and PCB | [`PSDFree()`](kernel/psdmalloc.picoc#L47), [`cancel_process_load()`](kernel/process/process_loader.picoc#L76), [`destroy_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L118), [`kfree()`](kernel/kmalloc.picoc#L38), [`release_process_shared_memory()`](kernel/shared_memory.picoc#L172), [`remove_from_wait_queue()`](kernel/process/process.picoc#L176) | **Kernel functions:** [`orphan_and_signal_children()`](kernel/process/process.picoc#L279), [`terminate_process()`](kernel/process/process.picoc#L304), [`unload_process_by_pid()`](kernel/process/process.picoc#L328), [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) |
| [`orphan_and_signal_children(parent)`](kernel/process/process.picoc#L279) | No return value | Sets direct children [`parent_pid`](kernel/process/process.header#L57) to 0, removes existing zombies, signals live children when [`parent_death_signal`](kernel/process/process.header#L59) is nonzero | [`remove_process()`](kernel/process/process.picoc#L209), [`send_signal_to_process()`](kernel/signal.picoc#L75) | **Kernel functions:** [`terminate_process()`](kernel/process/process.picoc#L304) |
| [`process_has_waiting_parent(process)`](kernel/process/process.picoc#L249) | true when the recorded parent is in the child [`waiters`](kernel/process/process.header#L46) queue, otherwise false | Scans the child [`waiters`](kernel/process/process.header#L46) queue through [`wait_next`](kernel/process/process.header#L51) | None | **Kernel functions:** [`terminate_process()`](kernel/process/process.picoc#L304) |
| [`wake_parent_waiting_for_process(process, status)`](kernel/process/process.picoc#L261) | No return value | Writes the status through the parent [`waiting_status_ptr`](kernel/process/process.header#L44) when supplied, clears that pointer, and wakes all child [`waiters`](kernel/process/process.header#L46) | [`wakeup_wait_queue()`](kernel/process/process.picoc#L395) | **Kernel functions:** [`terminate_process()`](kernel/process/process.picoc#L304) |

# 5. Shared Memory Entries and Mappings
[\[↑ TOC\]](#contents)

Shared memory lets processes read and write the same physical cells.
PicoOS allocates them in the Process and Shared Data Heap. A named kernel
entry describes each region, and attachments record which processes map it.
This chapter follows those records through mapping, unlinking, and cleanup.

## 5.1 Named entries and per-process attachments
[\[↑ TOC\]](#contents)

[`SharedMemoryEntry`](kernel/shared_memory.header#L8) describes one region. [`SharedMemoryAttachment`](kernel/shared_memory.header#L17) records
one mapping and belongs to the PCB's [`shared_memory_attachments`](kernel/process/process.header#L55) list. It
references the entry without owning its data.

The definitions and field tables show the metadata and pointers connecting
these objects:

```c
struct SharedMemoryEntry {
    char *name;
    int id;
    void *address;
    int reference_count;
    bool unlink_requested;
    struct SharedMemoryEntry *next;
};

struct SharedMemoryAttachment {
    struct SharedMemoryEntry *entry;
    struct SharedMemoryAttachment *next;
};
```

[`open_shared_memory()`](kernel/shared_memory.picoc#L92) allocates the entry, name, and shared data separately.
[`map_shared_memory()`](kernel/shared_memory.picoc#L130) inserts an attachment at the head of the PCB's
[`shared_memory_attachments`](kernel/process/process.header#L55) list and increments [`reference_count`](kernel/shared_memory.header#L12).
Every mapping receives the same absolute address. [`9.1 Memory layout, allocation sources, and lifetimes`](#91-memory-layout-allocation-sources-and-lifetimes) compares their lifetimes.

Attachments tell process cleanup which mapping references to release. Two
processes mapping one region need one entry and two attachments. The
attachments store no shared bytes.

| Attribute | Meaning | Used by |
| --- | --- | --- |
| [`SharedMemoryEntry.name`](kernel/shared_memory.header#L9) | Kernel-owned lookup name, freed and set to `NULL` on unlink | First initialized by [`open_shared_memory()`](kernel/shared_memory.picoc#L92), read by [`find_shared_memory_by_name()`](kernel/shared_memory.picoc#L45), freed by [`unlink_shared_memory()`](kernel/shared_memory.picoc#L151) and [`destroy_shared_memory_entry()`](kernel/shared_memory.picoc#L69) |
| [`SharedMemoryEntry.id`](kernel/shared_memory.header#L10) | Numeric open/map handle | First initialized and returned by [`open_shared_memory()`](kernel/shared_memory.picoc#L92), read by [`find_shared_memory_by_id()`](kernel/shared_memory.picoc#L57) for [`map_shared_memory()`](kernel/shared_memory.picoc#L130) |
| [`SharedMemoryEntry.address`](kernel/shared_memory.header#L11) | Absolute start of the [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) shared-memory data region | First initialized by [`open_shared_memory()`](kernel/shared_memory.picoc#L92), returned by [`map_shared_memory()`](kernel/shared_memory.picoc#L130) and freed by [`destroy_shared_memory_entry()`](kernel/shared_memory.picoc#L69) |
| [`SharedMemoryEntry.reference_count`](kernel/shared_memory.header#L12) | Attachment count, not distinct PID count | First initialized by [`open_shared_memory()`](kernel/shared_memory.picoc#L92), changed by [`map_shared_memory()`](kernel/shared_memory.picoc#L130) and [`release_process_shared_memory()`](kernel/shared_memory.picoc#L172), checked by [`unlink_shared_memory()`](kernel/shared_memory.picoc#L151) |
| [`SharedMemoryEntry.unlink_requested`](kernel/shared_memory.header#L13) | Defers destruction until the last attachment disappears | First initialized by [`open_shared_memory()`](kernel/shared_memory.picoc#L92), set by [`unlink_shared_memory()`](kernel/shared_memory.picoc#L151) and checked by [`release_process_shared_memory()`](kernel/shared_memory.picoc#L172) |
| [`SharedMemoryEntry.next`](kernel/shared_memory.header#L14) | Link to the next entry in the kernel's linked list | First initialized by [`open_shared_memory()`](kernel/shared_memory.picoc#L92), traversed by [`find_shared_memory_by_name()`](kernel/shared_memory.picoc#L45) and [`find_shared_memory_by_id()`](kernel/shared_memory.picoc#L57), traversed and updated by [`destroy_shared_memory_entry()`](kernel/shared_memory.picoc#L69) |

The attachment table shows how a mapping records its contribution to the entry’s lifetime without
owning the entry itself.

| Attribute | Meaning | Used by |
| --- | --- | --- |
| [`SharedMemoryAttachment.entry`](kernel/shared_memory.header#L18) | Non-owning pointer to the linked-list entry whose reference count this mapping contributes to | First initialized by [`map_shared_memory()`](kernel/shared_memory.picoc#L130), read by [`release_process_shared_memory()`](kernel/shared_memory.picoc#L172) to decrement the entry's count before freeing the attachment |
| [`SharedMemoryAttachment.next`](kernel/shared_memory.header#L19) | Link in one PCB's [`shared_memory_attachments`](kernel/process/process.header#L55) list | First initialized by [`map_shared_memory()`](kernel/shared_memory.picoc#L130), traversed by [`release_process_shared_memory()`](kernel/shared_memory.picoc#L172) |

### 5.1.1 Global shared-memory list and entry names
[\[↑ TOC\]](#contents)

The diagram shows how [`shared_memory_list_head`](kernel/shared_memory.picoc#L6) and
[`SharedMemoryEntry.next`](kernel/shared_memory.header#L14) link entries in SRAM and as a linked list.
Each entry's [`name`](kernel/shared_memory.header#L9) points to a separately allocated Kernel Heap string.

![The global shared-memory list head reaches two linked entries in SRAM, each with a name pointer to a separate string. The lower view repeats the same two entries as a linked list.](documentation/images/memory-shared-list.svg)

#### 5.1.1.1 From Shared Memory Entries to Shared Data Payloads in SRAM
[\[↑ TOC\]](#contents)

[`address`](kernel/shared_memory.header#L11) points from the Kernel Heap entry to its Shared Data Payload.
This parallels a PCB's [`base_address`](kernel/process/process.header#L34) in [`4.1.2.1 From PCBs to Process Payloads in SRAM`](#4121-from-pcbs-to-process-payloads-in-sram).

The green arrows connect entries 1 and 2 to Shared Data Payloads A and C.
The middle Process Payload shows that both kinds of data use the same outer
heap:

![Three blocks in each heap: Shared Memory Entries 1 and 2 point through address to Shared Data Payloads A and C. PCB 1 and Process Payload B provide context.](documentation/images/memory-shared-mappings.svg)

[`open_shared_memory()`](kernel/shared_memory.picoc#L92) stores the [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) address, and
[`map_shared_memory()`](kernel/shared_memory.picoc#L130) returns it unchanged. [`5.1.2 Per-process attachment lists in SRAM`](#512-per-process-attachment-lists-in-sram) shows mapping records.

### 5.1.2 Per-process attachment lists in SRAM
[\[↑ TOC\]](#contents)

Each PCB's [`shared_memory_attachments`](kernel/process/process.header#L55) links the mapping records belonging
to that process. The upper view places these lists in SRAM, and the lower view
shows their pointers, with dashed lines connecting the same objects in both views:

![Two PCBs, three attachments and two shared entries in the Kernel Heap, followed by the same two per-process attachment lists with shared_memory_attachments, next and entry arrows. The Process and Shared Data Heap is one box.](documentation/images/memory-shared-attachments.svg)

## 5.2 Mapping, unlinking, and deferred destruction
[\[↑ TOC\]](#contents)

Every [`mmap()`](library/sys/mman/mman.picoc#L23) adds an attachment and increments [`reference_count`](kernel/shared_memory.header#L12), even
for repeated mappings by one process. PicoOS has no `munmap()`, so removal
of the process releases them.

[`shm_unlink()`](library/sys/mman/mman.picoc#L27) frees the name and requests destruction. Existing mappings
and their addresses remain valid. The numeric ID remains usable while the
entry exists, and opening the old name creates a new entry. With no mappings,
unlink destroys the entry immediately.

[`release_process_shared_memory()`](kernel/shared_memory.picoc#L172) frees each attachment and decrements
its entry's count. Destruction requires both an unlink request and a zero
reference count.

This timeline follows Entry 1 and Shared Data Payload A, mapped by two
processes. Opening creates the entry, mapping adds references, unlinking
removes its name, and process removal releases the references. The data
stays allocated until both destruction conditions hold:

![Shared-memory lifetime from left to right: shm_open creates Entry 1 with count 0, mmap in two processes raises the count to 2, shm_unlink removes the name while the count stays 2, removal of PCB 1 lowers it to 1, and removal of PCB 2 lowers it to 0 and frees the unlinked entry and its data.](documentation/images/memory-shared-destruction.svg)

The conditions can occur in either order. A named region with no mappings
stays allocated. Unlinking it later destroys it. The timeline omits PCB 1's
other mapping, which is also released on removal.

A retained zombie keeps its attachments. They are released at final PCB
removal, as explained in [`7.1.2.2 Parent collection and final removal`](#7122-parent-collection-and-final-removal).

The entry is also the registry node. [`destroy_shared_memory_entry()`](kernel/shared_memory.picoc#L69) unlinks
it, frees its data with [`PSDFree()`](kernel/psdmalloc.picoc#L47), and frees its metadata with [`kfree()`](kernel/kmalloc.picoc#L38).
Freeing the already-null name is harmless. Freed cells become reusable
without being erased.

[`shm_open()`](library/sys/mman/mman.picoc#L15) returns an ID, and [`mmap()`](library/sys/mman/mman.picoc#L23) returns its address. This launcher
shares one cell containing `7`, then waits for a worker to change it:

```c
// dependencies: ../../library/unistd/libunistd.reti_blocks ../../library/sys/wait/libwait.reti_blocks ../../library/sys/mman/libmman.reti_blocks

#include "../../library/unistd/unistd.header"
#include "../../library/sys/wait/wait.header"
#include "../../library/sys/mman/mman.header"

int main(void) {
    int shared_memory_id;
    int *shared_value;
    int worker_pid;
    int result = 1;

    shared_memory_id = shm_open("shared-value", 1);
    shared_value = (int *)mmap(shared_memory_id);
    shared_value[0] = 7;

    worker_pid = load("test/shared_value/worker.bin");
    run(worker_pid, "shared-value", NULL);
    waitpid(worker_pid);

    if (shared_value[0] == 8) {
        result = 0;
    }
    shm_unlink("shared-value");
    return result;
}
```

The worker opens the same name, maps the existing region, and changes
`7` to `8`:

```c
// dependencies: ../../library/sys/mman/libmman.reti_blocks

#include "../../library/sys/mman/mman.header"

int main(int argc, char **argv) {
    int shared_memory_id;
    int *shared_value;

    shared_memory_id = shm_open(argv[1], 1);
    shared_value = (int *)mmap(shared_memory_id);
    shared_value[0] = shared_value[0] + 1;
    return 0;
}
```

Worker removal releases its attachment. Unlinking removes the name, but the
launcher's attachment keeps the data alive until the launcher is removed.

Shared memory provides visibility, not mutual exclusion. [`15.2 Real-time operating-systems topics`](#152-real-time-operating-systems-topics)
shows how a shared [`mutex`](library/mutex/mutex.header#L6) protects data accessed by more than one
process.

## 5.3 Shared Memory function reference
[\[↑ TOC\]](#contents)

These functions implement lookup, mapping, and deferred destruction.
Syscall-backed operations come first, followed by lifecycle helpers:

<table>
<thead>
<tr><th>Kernel function</th><th>Return value / status</th><th>Effects</th><th>Calls</th><th>Called by</th></tr>
</thead>
<tbody>
<tr><td><a href="kernel/shared_memory.picoc#L92"><code>open_shared_memory(request)</code></a></td><td>Existing/new ID, <code>-1</code> for a null request/name, a nonpositive new size, or insufficient Process and Shared Data Heap space</td><td>If the name already exists, returns its <a href="kernel/shared_memory.header#L10"><code>SharedMemoryEntry.id</code></a> without creating a structure. Otherwise creates a <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a> and copied name with <a href="kernel/kmalloc.picoc#L23"><code>kmalloc()</code></a>, creates its data region with <a href="kernel/psdmalloc.picoc#L20"><code>PSDMalloc()</code></a>, and prepends the <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a> to the kernel&#39;s linked list</td><td><a href="kernel/shared_memory.picoc#L45"><code>find_shared_memory_by_name()</code></a>, <a href="kernel/kmalloc.picoc#L23"><code>kmalloc()</code></a>, <a href="kernel/shared_memory.picoc#L27"><code>copy_shared_memory_name()</code></a>, <a href="kernel/psdmalloc.picoc#L20"><code>PSDMalloc()</code></a>, <a href="kernel/kmalloc.picoc#L38"><code>kfree()</code></a></td><td><strong>Library functions:</strong> <a href="library/sys/mman/mman.picoc#L15"><code>shm_open()</code></a><br><strong>Kernel functions (syscall dispatch):</strong> <a href="kernel/syscall.picoc#L16"><code>handle_syscall()</code></a></td></tr>
<tr><td><a href="kernel/shared_memory.picoc#L130"><code>map_shared_memory(shared_memory_id)</code></a></td><td>Address, or <code>NULL</code> for an unknown ID or no current process</td><td>For every successful mapping, creates one <a href="kernel/shared_memory.header#L17"><code>SharedMemoryAttachment</code></a> with <a href="kernel/kmalloc.picoc#L23"><code>kmalloc()</code></a>, links it from the current PCB&#39;s <a href="kernel/process/process.header#L55"><code>shared_memory_attachments</code></a> field, points it at the existing <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a>, and increments that entry&#39;s count</td><td><a href="kernel/process/process.picoc#L62"><code>current_process()</code></a>, <a href="kernel/shared_memory.picoc#L57"><code>find_shared_memory_by_id()</code></a>, <a href="kernel/kmalloc.picoc#L23"><code>kmalloc()</code></a></td><td><strong>Library functions:</strong> <a href="library/sys/mman/mman.picoc#L23"><code>mmap()</code></a><br><strong>Kernel functions (syscall dispatch):</strong> <a href="kernel/syscall.picoc#L16"><code>handle_syscall()</code></a></td></tr>
<tr><td><a href="kernel/shared_memory.picoc#L151"><code>unlink_shared_memory(name)</code></a></td><td><code>0</code> on unlink, <code>-1</code> for a null or unknown name</td><td>Frees the name and marks the existing <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a> for removal, destroys that <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a> immediately only when its mapping count is zero</td><td><a href="kernel/shared_memory.picoc#L45"><code>find_shared_memory_by_name()</code></a>, <a href="kernel/kmalloc.picoc#L38"><code>kfree()</code></a>, <a href="kernel/shared_memory.picoc#L69"><code>destroy_shared_memory_entry()</code></a></td><td><strong>Library functions:</strong> <a href="library/sys/mman/mman.picoc#L27"><code>shm_unlink()</code></a><br><strong>Kernel functions (syscall dispatch):</strong> <a href="kernel/syscall.picoc#L16"><code>handle_syscall()</code></a></td></tr>
</tbody>
<tbody>
<tr><td colspan="5"><hr><hr></td></tr>
<tr><td><a href="kernel/shared_memory.picoc#L9"><code>initialize_shared_memory(void)</code></a></td><td>Returns no value</td><td>Initializes the shared-memory list head and next ID</td><td>—</td><td><strong>Kernel functions:</strong> <a href="kernel/kernel.picoc#L31"><code>main()</code></a></td></tr>
<tr><td><a href="kernel/shared_memory.picoc#L172"><code>release_process_shared_memory(process)</code></a></td><td>Returns no value</td><td>Walks one PCB&#39;s <a href="kernel/shared_memory.header#L17"><code>SharedMemoryAttachment</code></a> list, frees every <a href="kernel/shared_memory.header#L17"><code>SharedMemoryAttachment</code></a>, and decrements the referenced <a href="kernel/shared_memory.header#L12"><code>SharedMemoryEntry.reference_count</code></a>, destroys an unlinked <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a> after its last attachment is released</td><td><a href="kernel/kmalloc.picoc#L38"><code>kfree()</code></a>, <a href="kernel/shared_memory.picoc#L69"><code>destroy_shared_memory_entry()</code></a></td><td><strong>Kernel functions:</strong> <a href="kernel/process/process.picoc#L209"><code>remove_process()</code></a></td></tr>
<tr><td><a href="kernel/shared_memory.picoc#L69"><code>destroy_shared_memory_entry(entry)</code></a></td><td>Returns no value</td><td>Removes one <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a> from the kernel&#39;s linked list, frees its <a href="kernel/shared_memory.header#L11"><code>SharedMemoryEntry.address</code></a> data region with <a href="kernel/psdmalloc.picoc#L47"><code>PSDFree()</code></a>, and frees the <a href="kernel/shared_memory.header#L8"><code>SharedMemoryEntry</code></a> and its name with <a href="kernel/kmalloc.picoc#L38"><code>kfree()</code></a></td><td><a href="kernel/psdmalloc.picoc#L47"><code>PSDFree()</code></a>, <a href="kernel/kmalloc.picoc#L38"><code>kfree()</code></a></td><td><strong>Kernel functions:</strong> <a href="kernel/shared_memory.picoc#L151"><code>unlink_shared_memory()</code></a>, <a href="kernel/shared_memory.picoc#L172"><code>release_process_shared_memory()</code></a></td></tr>
</tbody>
</table>

# 6. Scheduling and context switching
[\[↑ TOC\]](#contents)

The scheduler chooses the next runnable process. The dispatcher saves the
outgoing registers and restores the selected process. They share PCB
information but have separate jobs.

PicoOS represents states with integer constants. The scheduler accepts
[`PROCESS_STATE_READY`](kernel/process/process.header#L13) and [`PROCESS_STATE_RUNNING`](kernel/process/process.header#L14), returning the selected
process's PCB. The dispatcher uses its saved activation to resume execution.

## 6.1 Scheduler implementation
[\[↑ TOC\]](#contents)

PicoOS schedules directly from the process list. The algorithm below
explains that policy, followed by a function reference.

### 6.1.1 Algorithm and Round Robin comparison
[\[↑ TOC\]](#contents)

PicoOS calls its policy *Lazy Round Robin*. It scans the list from [`4.1.2 Global process list and current process`](#412-global-process-list-and-current-process)
starting after the current process, wraps at the tail, and examines each
PCB at most once. It maintains no separate ready queue.

[`scheduler_can_run()`](kernel/scheduler.picoc#L4) accepts [`READY`](kernel/process/process.header#L13) and [`RUNNING`](kernel/process/process.header#L14). It skips [`NEW`](kernel/process/process.header#L12),
[`BLOCKED`](kernel/process/process.header#L15), [`STOPPED`](kernel/process/process.header#L16), and [`ZOMBIE`](kernel/process/process.header#L17).

Continuously runnable processes receive cyclic turns. A textbook FIFO ready
queue appends newly awakened processes at its tail. PicoOS leaves each PCB
in its existing position, which can give that process an earlier turn.
Selection also scans records that a ready queue would exclude.

The 5,000-instruction timer dispatches from userspace and defers a switch
from kernel work. Voluntary switches do not restart it. A selected process
may therefore receive only the rest of the current interval, rather than
a fresh quantum.

#### 6.1.1.1 Selecting the next runnable process
[\[↑ TOC\]](#contents)

The example starts with PCB 3 as the current process. Each
[`ProcessControlBlock`](kernel/process/process.header#L31) is allocated in the
Kernel Heap. Its [`next`](kernel/process/process.header#L53) field points to
the following PCB, and PCB 5's [`next`](kernel/process/process.header#L53)
is `NULL`.

The diagram shows the PCB list from left to right, with each link labeled
[`next`](kernel/process/process.header#L53). The two global variables appear
on the left. [`process_list_head`](kernel/process/process.picoc#L16) points
to PCB 1, and [`active_process`](kernel/process/process.picoc#L18) points to
PCB 3, whose [`state`](kernel/process/process.header#L33) is
[`RUNNING`](kernel/process/process.header#L14):

![PCB 1 through PCB 5 form a left-to-right list connected by next fields, ending in NULL. The global variables on the left point into the list: process_list_head to PCB 1 and active_process to PCB 3.](documentation/images/scheduler-overview.svg)

When PCB 3 yields or its timer interrupt causes a switch,
[`dispatcher_switch_from_context(caller_context)`](kernel/dispatcher.picoc#L71)
saves its registers and sets its
[`state`](kernel/process/process.header#L33) to
[`READY`](kernel/process/process.header#L13).
[`active_process`](kernel/process/process.picoc#L18) still points to PCB 3.
The walkthrough starts here, with the same list order and the other process
states unchanged.

[`scheduler_next_process()`](kernel/scheduler.picoc#L12) uses two local
pointers. [`start`](kernel/scheduler.picoc#L13) records where this search
began so the scan can stop after one pass.
[`candidate`](kernel/scheduler.picoc#L14) points to the PCB currently being
checked. The teal arrow shows
[`process_list_head`](kernel/process/process.picoc#L16). The green arrow shows
[`active_process`](kernel/process/process.picoc#L18), and the amber arrows
show [`start`](kernel/scheduler.picoc#L13) and
[`candidate`](kernel/scheduler.picoc#L14) separately so their positions remain
visible as the scan advances. Steps 1–3 follow the scan
past PCB 4 to PCB 5 and the subsequent dispatch:

![Steps 1–3: active_process remains at PCB 3 while start and candidate begin at PCB 4, candidate advances past its STOPPED state to PCB 5 in state READY, then the dispatcher moves active_process to PCB 5 and sets its state to RUNNING](documentation/images/scheduler-select.svg)

[`scheduler_can_run(candidate)`](kernel/scheduler.picoc#L4) rejects PCB 4
because its [`state`](kernel/process/process.header#L33) is
[`STOPPED`](kernel/process/process.header#L16), then accepts PCB 5 in state
[`READY`](kernel/process/process.header#L13). Returning PCB 5 changes neither
[`active_process`](kernel/process/process.picoc#L18) nor either process's
[`state`](kernel/process/process.header#L33).
[`dispatcher_switch_to_process(process)`](kernel/dispatcher.picoc#L43)
then calls [`set_current_process(process)`](kernel/process/process.picoc#L66)
to move [`active_process`](kernel/process/process.picoc#L18) to PCB 5, sets
its [`state`](kernel/process/process.header#L33) to
[`RUNNING`](kernel/process/process.header#L14), and resumes it.

#### 6.1.1.2 Starting at the head after the last process
[\[↑ TOC\]](#contents)

At the next switch, the dispatcher saves PCB 5 and sets its
[`state`](kernel/process/process.header#L33) to
[`READY`](kernel/process/process.header#L13), leaving
[`active_process`](kernel/process/process.picoc#L18) at PCB 5 until another
process is selected. Steps 4–5 show what happens when the current process
is last in the list. Since PCB 5's
[`next`](kernel/process/process.header#L53) is `NULL`, the scheduler starts
at [`first_process()`](kernel/process/process.picoc#L28), which returns
[`process_list_head`](kernel/process/process.picoc#L16), PCB 1:

![Steps 4–5: with active_process at PCB 5 and its next pointer NULL, the scheduler starts at PCB 1 and returns it in state READY, then the dispatcher moves active_process to PCB 1 and sets its state to RUNNING](documentation/images/scheduler-next-turn.svg)

The wraparound is a choice of where to search. PCB 5's
[`next`](kernel/process/process.header#L53) stays `NULL`, and the PCB list
order does not change. A textbook FIFO ready queue would take its head
directly, without traversing records whose processes cannot run.

#### 6.1.1.3 Reaching the list end during a scan
[\[↑ TOC\]](#contents)

The scan can also reach the list end before finding a runnable process.
The following variation starts with PCB 3's context saved as before, but
assumes PCB 5's [`state`](kernel/process/process.header#L33) is now
[`BLOCKED`](kernel/process/process.header#L15). The first loop skips both
PCB 4 and PCB 5, so [`candidate`](kernel/scheduler.picoc#L14) becomes `NULL`.
The second loop resets [`candidate`](kernel/scheduler.picoc#L14) to
[`first_process()`](kernel/process/process.picoc#L28) and checks the part
of the list before [`start`](kernel/scheduler.picoc#L13). The amber arrow
leaves `NULL` and leads back to PCB 1, showing this reassignment:

![List-end variation: with start at PCB 4 and active_process at PCB 3, the scan skips PCB 4 in state STOPPED and PCB 5 in state BLOCKED, reaches candidate NULL, resets candidate to the list head, and returns PCB 1 in state READY](documentation/images/scheduler-scan-end.svg)

Here PCB 1 can run, so the second loop returns PCB 1. If it also had to skip
PCB 1 and PCB 2, it would check PCB 3 next. This lets the current process run
again when it is the only runnable process. If every process were unable
to run, advancing past PCB 3 would bring
[`candidate`](kernel/scheduler.picoc#L14) back to
[`start`](kernel/scheduler.picoc#L13), PCB 4. The loop stops before checking
PCB 4 twice and returns `NULL`.

With no runnable process, the scheduler returns `NULL`. The dispatcher
retries while PCBs exist, allowing device interrupts to wake one. It can
wait indefinitely if no event does so and returns when the list is empty.
PicoOS has no idle process.

#### 6.1.1.4 Implementation
[\[↑ TOC\]](#contents)

Scanning the PCB list avoids maintaining a second queue at each state
change. The cost is a worst-case O(number of PCBs) selection.

The implementation separates the state check from the cyclic scan:

```c
bool scheduler_can_run(struct ProcessControlBlock *process) {
    return process != NULL &&
           (process->state == PROCESS_STATE_READY ||
            // A still-current RUNNING process may be the only runnable process
            // when scheduler_next_process() wraps around to it
            process->state == PROCESS_STATE_RUNNING);
}

struct ProcessControlBlock *scheduler_next_process(void) {
    struct ProcessControlBlock *start;
    struct ProcessControlBlock *candidate;

    if (first_process() == NULL) {
        return NULL;
    }
    if (current_process() == NULL || current_process()->next == NULL) {
        start = first_process();
    } else {
        start = current_process()->next;
    }

    candidate = start;
    while (candidate != NULL) {
        if (scheduler_can_run(candidate)) {
            return candidate;
        }
        candidate = candidate->next;
    }

    candidate = first_process();
    while (candidate != start) {
        if (scheduler_can_run(candidate)) {
            return candidate;
        }
        candidate = candidate->next;
    }
    return NULL;
}
```

### 6.1.2 Scheduler function reference
[\[↑ TOC\]](#contents)

These two functions implement the policy. [`6.5 Dispatcher function reference`](#65-dispatcher-function-reference) covers the dispatcher:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`scheduler_can_run(process)`](kernel/scheduler.picoc#L4) | `true` for a non-`NULL` PCB whose state is [`READY`](kernel/process/process.header#L13) or [`RUNNING`](kernel/process/process.header#L14), otherwise `false` | Reads the candidate PCB's [`state`](kernel/process/process.header#L33) | None | **Kernel functions:** [`scheduler_next_process()`](kernel/scheduler.picoc#L12) |
| [`scheduler_next_process(void)`](kernel/scheduler.picoc#L12) | PCB representing the first runnable process found during one cyclic scan, or `NULL` when the process list is empty or no process can run | Reads [`process_list_head`](kernel/process/process.picoc#L16), [`active_process`](kernel/process/process.picoc#L18), and PCB [`next`](kernel/process/process.header#L53) and [`state`](kernel/process/process.header#L33) fields, does not change process state | [`first_process()`](kernel/process/process.picoc#L28), [`current_process()`](kernel/process/process.picoc#L62), [`scheduler_can_run()`](kernel/scheduler.picoc#L4) | **Kernel functions:** [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55) |

## 6.2 Saved process registers
[\[↑ TOC\]](#contents)

After the scheduler chooses a process, the dispatcher needs its saved
registers to resume execution. Each [`ProcessControlBlock`](kernel/process/process.header#L31)
stores these registers directly in its [`activation`](kernel/process/process.header#L40)
field, an embedded [`ActivationRecord`](kernel/process/process.header#L21).
The record shares the PCB's allocation and lifetime.

The diagram enlarges these seven fields within one PCB's Kernel Heap
allocation, with dashed lines connecting the embedded record directly to
its enlarged cells. All layouts, including the process stack, run from
lower addresses on the left to higher addresses on the right. Offsets count RETI memory cells from
the PCB's start, and the field order must match the fixed
offsets read by [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21).
The saved `PC` remains on the process stack at
[`activation.sp`](kernel/process/process.header#L25) + 1, where `RTI` reads it
after the dispatcher restores `SP`:

![PCB 1 contains activation at offsets 8 through 14, connected directly to enlarged in1, in2, acc, sp, baf, cs, and ds cells. active_process points to PCB 1. Saved sp points one cell below the saved PC on the process stack.](documentation/images/process-activation-record.svg)

[`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) writes the
record in the PCB returned by [`current_process()`](kernel/process/process.picoc#L62).
[`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) reads the record
in the PCB selected by [`scheduler_next_process()`](kernel/scheduler.picoc#L12).
The definition and table below explain each saved register and where it is
initialized, updated, and restored:

```c
struct ActivationRecord {
    int in1;
    int in2;
    int acc;
    int sp;
    int baf;
    int cs;
    int ds;
};
```

| Attribute | Meaning | Used by |
| --- | --- | --- |
| [`in1`](kernel/process/process.header#L22), [`in2`](kernel/process/process.header#L23), [`acc`](kernel/process/process.header#L24) | General argument/result registers at the suspension point | First initialized by [`create_process()`](kernel/process/process.picoc#L89), saved by [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) and restored by [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21). [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182) and [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) update [`in2`](kernel/process/process.header#L23) with the completed read's result before the process resumes |
| [`sp`](kernel/process/process.header#L25) | Stack position immediately below the saved return PC, the return PC remains at `sp + 1` | First initialized by [`create_process()`](kernel/process/process.picoc#L89), rebuilt by [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125), saved by [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71), and restored by [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) |
| [`baf`](kernel/process/process.header#L26) | Base address of the interrupted PicoC function frame | First initialized by [`create_process()`](kernel/process/process.picoc#L89), rebuilt by [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125), saved by [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71), and restored by [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) |
| [`cs`](kernel/process/process.header#L27) | Absolute code-segment base used for instruction addresses | First initialized by [`create_process()`](kernel/process/process.picoc#L89), saved by [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) and restored by [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) |
| [`ds`](kernel/process/process.header#L28) | Absolute data-segment base used for globals/static data | First initialized by [`create_process()`](kernel/process/process.picoc#L89), saved by [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) and restored by [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) |

[`2.4.2.4 Restoring process context with RTI`](#2424-restoring-process-context-with-rti)
shows how this record and the saved PC on the process stack work together.

## 6.3 Saving the current process and selecting the next process
[\[↑ TOC\]](#contents)

The save path preserves the outgoing process before selecting another one.
The syscall and timer paths in [`2.4.2.3 Selecting the return path`](#2423-selecting-the-return-path) and [`2.5.1 Timer interrupt path`](#251-timer-interrupt-path) lead here.

These entry paths provide the saved frame from [`2.3 Saved interrupt stack frame`](#23-saved-interrupt-stack-frame):

- Userspace timer preemption and [`yield()`](library/schedule/schedule.picoc#L4) switch immediately.
- [`sleep()`](library/unistd/blocking.picoc#L9), a blocking [`waitpid()`](library/sys/wait/wait.picoc#L14) or terminal [`read()`](library/unistd/io.picoc#L6), and a DMA-backed
  [`load()`](library/unistd/process.picoc#L17) switch after recording the wait.
- A deferred timer or termination request switches at syscall return when
  [`reschedule_requested`](kernel/dispatcher.picoc#L8) is set.

A syscall can restore its caller directly, save it for a switch, or abandon
it during termination. [`2.4.2 System-call entry, execution, and return to userspace`](#242-system-call-entry-execution-and-return-to-userspace) shows the shared entry and return paths.

[`dispatcher_switch_from_context(caller_context)`](kernel/dispatcher.picoc#L71)
uses [`current_process()`](kernel/process/process.picoc#L62) to obtain the
PCB still referenced by [`active_process`](kernel/process/process.picoc#L18).
In the layout below, this is PCB 3 in the Kernel Heap. Its
[`activation`](kernel/process/process.header#L40) receives the saved register
values from that process's stack in the Process and Shared Data Heap.
The kernel-call argument
[`caller_context`](kernel/dispatcher.picoc#L71) points to the free cell just
below the saved `DS`.

The lower panels connect each stack offset to the field it updates. Gray
arrows copy the values at offsets 1 through 6. The teal address arrow shows
why [`activation.sp`](kernel/process/process.header#L25) receives
`caller_context + 6`, the address of the saved `ACC` cell. The saved `PC`
remains at `caller_context + 7`, which is
[`activation.sp`](kernel/process/process.header#L25) + 1. PCB offsets locate
the destination fields, while the assignment rows follow the source stack:

![caller_context points into PCB 3's user stack. Six arrows copy DS, CS, BAF, IN2, IN1 and ACC from offsets 1 through 6 to PCB 3.activation in the Kernel Heap. A separate address arrow saves caller_context + 6 as activation.sp. PC remains on the stack at offset 7.](documentation/images/process-dispatcher-save.svg)

The implementation saves these fields before adjusting
[`state`](kernel/process/process.header#L33) and selecting the next process:

```c
void dispatcher_switch_from_context(int *caller_context) {
    struct ProcessControlBlock *process = current_process();

    if (process != NULL) {
        process->activation.sp = (int)(caller_context + 6);
        process->activation.ds = caller_context[1];
        process->activation.cs = caller_context[2];
        process->activation.baf = caller_context[3];
        process->activation.in2 = caller_context[4];
        process->activation.in1 = caller_context[5];
        process->activation.acc = caller_context[6];

        if (process->state == PROCESS_STATE_RUNNING) {
            process->state = PROCESS_STATE_READY;
        }
    }
    dispatcher_start_next_process();
}
```

The state change is separate from the register copies. Timer preemption,
[`yield()`](library/schedule/schedule.picoc#L4), and a deferred reschedule
normally reach this function with
[`state`](kernel/process/process.header#L33) set to
[`RUNNING`](kernel/process/process.header#L14), so it writes
[`READY`](kernel/process/process.header#L13). Blocking paths set
[`BLOCKED`](kernel/process/process.header#L15) before entry, and signal
handling can set [`STOPPED`](kernel/process/process.header#L16), for example
when a background terminal [`read()`](library/unistd/io.picoc#L6) triggers
[`SIGTTIN`](common/signal.header#L9). Both states must survive the save so the
scheduler does not resume a process that is still waiting or stopped.

The diagram shows these cases for the outgoing PCB. An existing
[`READY`](kernel/process/process.header#L13), for example after a wakeup or
[`SIGCONT`](common/signal.header#L6), also stays unchanged. The condition
would leave [`NEW`](kernel/process/process.header#L12) and
[`ZOMBIE`](kernel/process/process.header#L17) unchanged, but startup and
termination normally enter
[`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55) directly.
If [`current_process()`](kernel/process/process.picoc#L62) is `NULL`, the
function skips both the activation and state writes. During saving, the
other PCB states and [`active_process`](kernel/process/process.picoc#L18)
stay unchanged until selection and dispatch:

![The outgoing PCB's state changes from RUNNING to READY. BLOCKED, STOPPED and an existing READY remain unchanged.](documentation/images/process-dispatcher-state.svg)

[`7.1.1 Blocking with sleep and waking with wakeup`](#711-blocking-with-sleep-and-waking-with-wakeup)
and [`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid)
explain how wakeups make a waiting process runnable again. Selecting the
next process clears
[`reschedule_requested`](kernel/dispatcher.picoc#L8), even if that selection
returns the same process.

Before restoration, [`prepare_process_termination()`](kernel/signal.picoc#L126) can reject a candidate
with a pending terminating signal. The loop retries selection. Device
interrupts can wake a process while it waits:

```c
void dispatcher_start_next_process(void) {
    struct ProcessControlBlock *next_process = scheduler_next_process();

    // Waits in kernel context when every process is blocked. A hardware
    // interrupt can make one of them runnable without a separate idle process
    while (first_process() != NULL &&
           (next_process == NULL ||
            !prepare_process_termination(next_process))) {
        next_process = scheduler_next_process();
    }

    if (next_process != NULL) {
        dispatcher_switch_to_process(next_process);
    }
}
```

[`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55) selects the
next context in these steps:

1. Ask [`scheduler_next_process()`](kernel/scheduler.picoc#L12) for a candidate.
2. While the process list is nonempty, retry if no candidate is runnable or
   [`prepare_process_termination()`](kernel/signal.picoc#L126) rejects it.
   UART or DMA can make a waiting process runnable while this kernel loop runs.
3. Pass an accepted candidate to
   [`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43). If there
   is no candidate and the process list is empty, return to the caller.

[`6.1.1 Algorithm and Round Robin comparison`](#611-algorithm-and-round-robin-comparison) covers empty-list and no-runnable cases. [`2.4.2.3 Selecting the return path`](#2423-selecting-the-return-path) covers deferred
requests.

## 6.4 Restoring the selected process and returning with `RTI`
[\[↑ TOC\]](#contents)

After selection,
[`dispatcher_switch_to_process(process)`](kernel/dispatcher.picoc#L43) moves
[`active_process`](kernel/process/process.picoc#L18) to the selected PCB and
sets its [`state`](kernel/process/process.header#L33) to
[`RUNNING`](kernel/process/process.header#L14). It then calls
[`dispatcher_jump_to_process(process, stack_boundary)`](kernel/dispatcher.picoc#L21)
with the boundary computed by
[`process_stack_boundary(process)`](kernel/exception.picoc#L18).

The diagram uses **PCB 1** as the selected process in a standalone example.
The scheduler can select any runnable PCB; the number 1 is just an example
label. Its left region is SRAM in the Kernel Heap. PCB 1 contains an embedded
[`activation`](kernel/process/process.header#L40) of type
[`ActivationRecord`](kernel/process/process.header#L21), whose fields hold
saved register values. The middle region contains the actual CPU registers.
`SP` holds a stack address, `CS` and `DS` hold the code and data base
addresses, and `IN1`, `IN2`, `ACC`, and `BAF` hold the remaining process
context. Arrows copy values from PCB fields into these CPU registers.
The fields appear in struct order, with offsets relative to the PCB pointer.
Both the PCB-field table and the stack-cell table show **lower addresses at
the top** and **higher addresses at the bottom**, marked with downward arrows.
The process allocation follows the same address direction: the **User Process
Image** (including `.text`) appears above the **User Process Heap**, followed
by the **User Process Stack** at higher addresses.
The circled numbers **1** through **4** show the restoration sequence;
these numbers identify actions, not processes. In **Step 4: Execute RTI**,
the CPU executes `RTI` (**return from interrupt**) after the registers have
been restored. This instruction reads the saved return address from the
selected process's stack and resumes that process:

![PCB 1's activation fields live in SRAM's Kernel Heap and are copied into a separate CPU register bank. Steps 1–4 identify the restoration actions, not process numbers. Restored SP points to the saved ACC cell in PCB 1's user stack in SRAM's Process Payload A. In Step 4 the CPU executes RTI, meaning return from interrupt: it reads the saved PC from the next stack cell at SP + 1, updates CPU PC and SP, and resumes process 1 in its .text. The stack boundary is installed in a separate periphery register.](documentation/images/process-dispatcher-restore.svg)

The right region is PCB 1's user process allocation in SRAM. Its stack rows
show **addresses and stored values**, so `SP + 1` names the memory cell one
address above the cell selected by the CPU's `SP`. Before `RTI`, `SP` points
to the saved `ACC` cell and the next cell contains the saved `PC`.
`RTI` actually reads that next cell, advances `SP` by one, and sets the CPU's
`PC` to the saved value plus one. Execution resumes at that address in the
process's `.text`. The return address remains on the user stack, with no
`PC` field in [`activation`](kernel/process/process.header#L40).

The separate [`STACK_HEAP_BOUNDARY_REGISTER`](kernel/exception.header#L5)
is a memory-mapped periphery register. It holds the address limit used to
detect stack growth into the user heap. Its position in the diagram is
separate from both SRAM and the CPU register bank.

Before the pictured loads, the kernel call places the PCB pointer and
boundary on the **kernel stack**, at entry `SP + 2` and `SP + 3`.
[`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) reads the
pointer into `BAF` and the boundary into `IN1`. Here entry `SP` still selects
the kernel stack. Loading [`activation.sp`](kernel/process/process.header#L25)
then changes the CPU's `SP` to select the pictured user stack.

The naked function creates no additional PicoC frame. Its complete
restoration sequence is:

```c
__attribute__((naked))
void dispatcher_jump_to_process(struct ProcessControlBlock *process, int stack_boundary) {
    // Reads the process pointer and its precomputed stack boundary from the call frame
    asm("LOADIN SP BAF 2");
    asm("LOADIN SP IN1 3");

    // Restores SP before the process boundary so an interrupt cannot compare the
    // kernel stack against the process heap during this context-switch window
    asm("LOADIN BAF SP 11");
    write_stack_heap_boundary_from_in1();

    // Restores the remaining activation record while BAF still points to the process
    asm("LOADIN BAF CS 13");
    asm("LOADIN BAF DS 14");
    asm("LOADIN BAF IN1 8");
    asm("LOADIN BAF IN2 9");
    asm("LOADIN BAF ACC 10");
    asm("LOADIN BAF BAF 12");

    // Restores the saved program counter from the selected process's restored stack and resumes there
    asm("RTI");
}
```

[`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) restores the
selected process in these steps:

1. Load [`activation.sp`](kernel/process/process.header#L25) into `SP` before
   changing the boundary. Reversing this order could make a nested interrupt
   compare the still-active kernel stack against a user-process limit.
2. Call [`write_stack_heap_boundary_from_in1()`](common/periphery_asm.header#L2)
   to install the selected process's limit. This inline helper has no C frame,
   so it is usable after selecting the process stack. Its complete explanation
   is in [`2.4.2.1.1 Stack-boundary helpers`](#24211-stack-boundary-helpers).
3. Load `CS`, `DS`, `IN1`, `IN2`, and `ACC` from the selected PCB's
   [`activation`](kernel/process/process.header#L40). Restore `BAF` last,
   because it holds the PCB pointer while the other values are read.
4. Execute `RTI` (return from interrupt) to load the saved return address
   from the selected process's stack and resume execution, as explained in
   [`2.4.2.4 Restoring process context with RTI`](#2424-restoring-process-context-with-rti).
   For a new process, its prepared PC is `CS - 1`, so execution starts at `CS`.

Resumable switches save the outgoing activation first. Startup and
termination begin directly with [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55) because
there is no outgoing context to preserve. Both use the same selection and
restoration path.

## 6.5 Dispatcher function reference
[\[↑ TOC\]](#contents)

The table covers all dispatcher functions and their roles in requesting a
switch, selecting a process, saving context, and restoring execution:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`dispatcher_switch_from_context(caller_context)`](kernel/dispatcher.picoc#L71) | Returns only if the process list becomes empty. Otherwise the dispatch path leaves through `RTI` | Copies [`caller_context`](kernel/dispatcher.picoc#L71) into the current PCB's activation and changes only [`RUNNING`](kernel/process/process.header#L14) to [`READY`](kernel/process/process.header#L13) | [`current_process()`](kernel/process/process.picoc#L62), [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55) | **Library functions:** [`yield()`](library/schedule/schedule.picoc#L4), blocking [`sleep()`](library/unistd/blocking.picoc#L9), waiting [`waitpid()`](library/sys/wait/wait.picoc#L14), blocking terminal [`read()`](library/unistd/io.picoc#L6), and DMA-backed [`load()`](library/unistd/process.picoc#L17), all through syscalls<br>**Hardware interrupts:** userspace timer via [`timer_interrupt_process()`](interrupt_service_routines/os_isrs.picoc#L74)<br>**Kernel functions:** [`dispatcher_reschedule_if_requested()`](kernel/dispatcher.picoc#L14), [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390), [`start_dma_uart_receive()`](kernel/dma.picoc#L18), and the yield branch in [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`dispatcher_request_reschedule(void)`](kernel/dispatcher.picoc#L10) | Returns no value | Sets [`reschedule_requested`](kernel/dispatcher.picoc#L8) after a timer interrupts kernel work or a terminating signal targets the running process | None | **Hardware interrupts:** timer interrupting kernel work through [`timer_interrupt()`](interrupt_service_routines/os_isrs.picoc#L32)<br>**Kernel functions:** [`send_signal_to_process()`](kernel/signal.picoc#L75) |
| [`dispatcher_reschedule_if_requested(caller_context)`](kernel/dispatcher.picoc#L14) | Returns when no request is pending, otherwise returns only if dispatch finds an empty process list | Sends the saved syscall frame into the dispatcher when a deferred request is pending | [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) | **System-call return:** every normally returning syscall through [`syscall_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L133) |
| [`dispatcher_start_next_process(void)`](kernel/dispatcher.picoc#L55) | Leaves through `RTI` for a runnable process, waits while existing processes cannot run, or returns for an empty process list | Repeatedly requests a scheduler choice, consumes deferred termination for a selected process, and starts dispatch | [`scheduler_next_process()`](kernel/scheduler.picoc#L12), [`first_process()`](kernel/process/process.picoc#L28), [`prepare_process_termination()`](kernel/signal.picoc#L126), [`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43) | **Kernel functions:** [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71), [`exit_process()`](kernel/process/process.picoc#L430), [`main()`](kernel/kernel.picoc#L31) |
| [`dispatcher_switch_to_process(process)`](kernel/dispatcher.picoc#L43) | Does not return normally | Changes an old [`RUNNING`](kernel/process/process.header#L14) process to [`READY`](kernel/process/process.header#L13), clears the reschedule request, updates [`active_process`](kernel/process/process.picoc#L18), marks the selected process [`RUNNING`](kernel/process/process.header#L14), and begins restoration | [`current_process()`](kernel/process/process.picoc#L62), [`set_current_process()`](kernel/process/process.picoc#L66), [`process_stack_boundary()`](kernel/exception.picoc#L18), [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) | **Kernel functions:** [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55) |
| [`dispatcher_jump_to_process(process, stack_boundary)`](kernel/dispatcher.picoc#L21) | Leaves through `RTI`, it has no normal C return | Installs the selected process's `SP` and stack boundary, restores the other activation registers, then restores `PC` from the process stack | [`write_stack_heap_boundary_from_in1()`](common/periphery_asm.header#L2) | **Kernel functions:** [`dispatcher_switch_to_process()`](kernel/dispatcher.picoc#L43) |

# 7. Blocking, wait queues, signals, and mutexes
[\[↑ TOC\]](#contents)

A process blocks when it must wait for an event. A
[`wait_queue`](common/wait_queue.header#L5) records which processes are waiting,
and each PCB's [`state`](kernel/process/process.header#L33) determines whether
the process can run. This chapter explains the queue operations, how signals
stop, continue, or terminate processes, and how mutexes use queues when a lock
is held.

## 7.1 Wait queues and PCB links
[\[↑ TOC\]](#contents)

[`wait_queue`](common/wait_queue.header#L5) stores the head and tail of a PCB FIFO. Its shared header
defines the layout. The library functions [`sleep()`](library/unistd/blocking.picoc#L9)
and [`wakeup()`](library/unistd/blocking.picoc#L19) invoke syscalls to reach the
kernel's queue operations. Kernel events call those operations directly.
The functions in [`kernel/process/process.picoc`](kernel/process/process.picoc)
maintain the links.

The definition shows the endpoints. The links between them live in PCBs:

```c
struct wait_queue {
    struct ProcessControlBlock *head;
    struct ProcessControlBlock *tail;
};
```

| Attribute | Meaning | Used by |
| --- | --- | --- |
| [`head`](common/wait_queue.header#L6) | First blocked PCB to wake, or `NULL` when empty | First initialized by [`create_process()`](kernel/process/process.picoc#L89) for child waiters, [`initialize_terminal()`](kernel/filesystem/terminal.picoc#L14) for terminal input, [`wait_queue_init()`](library/unistd/blocking.picoc#L4) for userspace queues, or [`initialize_dma()`](kernel/dma.picoc#L9) for DMA, maintained by [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375), [`enqueue_terminal_reader()`](kernel/filesystem/terminal.picoc#L61), [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), and [`remove_from_wait_queue()`](kernel/process/process.picoc#L176) |
| [`tail`](common/wait_queue.header#L7) | Last blocked PCB, allowing constant-time append, also `NULL` when empty | First initialized by [`create_process()`](kernel/process/process.picoc#L89) for child waiters, [`initialize_terminal()`](kernel/filesystem/terminal.picoc#L14) for terminal input, [`wait_queue_init()`](library/unistd/blocking.picoc#L4) for userspace queues, or [`initialize_dma()`](kernel/dma.picoc#L9) for DMA, maintained by [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375), [`enqueue_terminal_reader()`](kernel/filesystem/terminal.picoc#L61), [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), and [`remove_from_wait_queue()`](kernel/process/process.picoc#L176) |

Embedded [`waiters`](kernel/process/process.header#L46) fields are complete queue objects. DMA uses a standalone
queue. The table identifies their owners:

PicoOS's shared address space lets the kernel store PCB pointers in a
userspace mutex queue. Child waiting instead uses a queue inside the child
PCB. Its request and result are local to the parent's suspended call.
[`9.4 Wait requests and queue storage`](#94-wait-requests-and-queue-storage) compares their storage.

The field table brings together queue links and saved wait arguments:

| Field and containing storage | Meaning and why it exists | Used by and important relationships |
| --- | --- | --- |
| [`WaitPidRequest.pid`](common/syscall.header#L62), in [`request`](library/sys/wait/wait.picoc#L16) on the parent's userspace stack | Exact child PID requested by the public API. It prevents another child's state change from completing this wait. | Set by [`waitpid()`](library/sys/wait/wait.picoc#L14). Read by [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348), which also checks the child's [`parent_pid`](kernel/process/process.header#L57). The kernel does not retain this field after blocking. |
| [`WaitPidRequest.status`](common/syscall.header#L63), in the same stack-local request | Points to the separate stack-local [`status`](library/sys/wait/wait.picoc#L15) result. The indirection lets the kernel use one request argument for both PID and result storage. | Set to `&status` by [`waitpid()`](library/sys/wait/wait.picoc#L14). Immediate paths write through it. The blocking path copies its value into the parent PCB's [`waiting_status_ptr`](kernel/process/process.header#L44). Neither the request nor status is allocated on the kernel heap. |
| [`wait_queue.head`](common/wait_queue.header#L6) and [`wait_queue.tail`](common/wait_queue.header#L7), embedded in an owner or stored as a global/userspace object | First and last PCB in a FIFO. [`tail`](common/wait_queue.header#L7) makes append constant-time. Both are `NULL` when empty. | Initialized by each queue owner. Maintained by [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375), [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), and [`remove_from_wait_queue()`](kernel/process/process.picoc#L176). The nodes are PCBs linked through [`wait_next`](kernel/process/process.header#L51). |
| [`ProcessControlBlock.waiters`](kernel/process/process.header#L46), embedded in each kernel-heap PCB | Queue of other processes waiting for this process to stop or terminate. It is queue ownership, not the queue containing this process. | Initialized empty by [`create_process()`](kernel/process/process.picoc#L89). The target child is found from the PID and its address `&child->waiters` is passed to [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390). Drained by [`notify_process_stopped()`](kernel/signal.picoc#L23) or [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261). |
| [`ProcessControlBlock.waiting_status_ptr`](kernel/process/process.header#L44), pointer stored in the waiting parent's kernel-heap PCB | Reaches the `status` integer in the suspended parent's userspace [`waitpid()`](library/sys/wait/wait.picoc#L14) frame. It exists because the child may finish while that call is not executing. | Initialized to `NULL` by [`create_process()`](kernel/process/process.picoc#L89). Set from [`WaitPidRequest.status`](common/syscall.header#L63) by [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348). Written and cleared through the parent PCB by [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) or [`notify_process_stopped()`](kernel/signal.picoc#L23). |
| [`ProcessControlBlock.waiting_queue_ptr`](kernel/process/process.header#L48), pointer stored in every kernel-heap PCB | Back-reference to the one queue currently containing this PCB, or `NULL`. It lets code unlink a blocked process without already knowing whether the owner is a child, mutex, terminal, or DMA subsystem. | Set on insertion and cleared on wake/removal. [`remove_process()`](kernel/process/process.picoc#L209) follows it through [`remove_from_wait_queue()`](kernel/process/process.picoc#L176) before freeing the PCB. This prevents a later wakeup from following a dangling PCB pointer. It is also used when terminal reads are stopped or resumed. |
| [`ProcessControlBlock.wait_next`](kernel/process/process.header#L51), embedded in every kernel-heap PCB | Intrusive link to the next PCB in whichever wait queue contains this process. One field is sufficient because a blocked process can join only one queue at a time. | Initialized to `NULL` by [`create_process()`](kernel/process/process.picoc#L89). Linked through the old queue tail by [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375). Traversed by [`remove_from_wait_queue()`](kernel/process/process.picoc#L176). Cleared on wake/removal. It is independent of global-list [`next`](kernel/process/process.header#L53). |
| [`ProcessControlBlock.state`](kernel/process/process.header#L33) and [`ProcessControlBlock.stopped_from_state`](kernel/process/process.header#L62), in the PCB | Record whether the waiter is [`BLOCKED`](kernel/process/process.header#L15), runnable, or visibly [`STOPPED`](kernel/process/process.header#L16), including whether a stopped wait completed. | Enqueue changes [`state`](kernel/process/process.header#L33) to [`BLOCKED`](kernel/process/process.header#L15). [`wakeup_wait_queue()`](kernel/process/process.picoc#L395) changes an ordinary waiter to [`READY`](kernel/process/process.header#L13), or keeps `state == STOPPED` and changes [`stopped_from_state`](kernel/process/process.header#L62) to [`READY`](kernel/process/process.header#L13) so [`continue_process()`](kernel/signal.picoc#L50) can resume it correctly. |
| [`ProcessControlBlock.parent_pid`](kernel/process/process.header#L57), [`ProcessControlBlock.exit_status`](kernel/process/process.header#L60), and [`ProcessControlBlock.stop_signal`](kernel/process/process.header#L61), in the child PCB | Verify that only the parent can wait and retain the child state needed by immediate/zombie/stopped [`waitpid`](library/sys/wait/wait.picoc#L14) paths. | Initialized by [`create_process()`](kernel/process/process.picoc#L89). Read by [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348). Termination writes [`exit_status`](kernel/process/process.header#L60), stopping writes [`stop_signal`](kernel/process/process.header#L61), and later collection reads the corresponding value. |

[`head`](common/wait_queue.header#L6) starts the [`wait_next`](kernel/process/process.header#L51) chain, and [`tail`](common/wait_queue.header#L7) points to its last PCB.
Both are `NULL` for an empty queue. Queue owners initialize the endpoints,
and [`create_process()`](kernel/process/process.picoc#L89) initializes PCB membership fields.

Blocking appends the current PCB, sets [`waiting_queue_ptr`](kernel/process/process.header#L48) and [`wait_next`](kernel/process/process.header#L51),
and changes [`state`](kernel/process/process.header#L33) to [`BLOCKED`](kernel/process/process.header#L15). The back-reference lets removal find its
queue without already knowing the owner. It is separate from the PCB's
own [`waiters`](kernel/process/process.header#L46).

Wakeup and removal clear membership links. A stopped waiter keeps [`STOPPED`](kernel/process/process.header#L16)
but records when its wait finishes. Terminal stops detach their read waiter,
while other stopped waits stay linked. Final process removal clears any
remaining membership. A retained zombie can stay linked until then.

One queue can hold many PCBs, but a blocked process can join only one queue
at a time. One [`wait_next`](kernel/process/process.header#L51) field is sufficient. It can still own a separate
queue for its parent.

Here PCB A is the child and embeds the queue. B, C, and D illustrate
intrusive waiter links. Normal [`waitpid()`](library/sys/wait/wait.picoc#L14) allows only A's parent to wait,
but the queue representation supports several entries:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    subgraph A["PCB A: process being waited on<br/>kernel heap"]
        AW["waiters: embedded wait_queue"]
    end
    AW -->|head| B["PCB B: waiting process<br/>kernel heap"]
    B -->|wait_next| C["PCB C: waiting process<br/>kernel heap"]
    C -->|wait_next| D["PCB D: waiting process<br/>kernel heap"]
    D -->|wait_next| N["NULL"]
    AW -->|tail| D
    B -. waiting_queue_ptr .-> AW
    C -. waiting_queue_ptr .-> AW
    D -. waiting_queue_ptr .-> AW
```

In the diagram, A's [`waiters`](kernel/process/process.header#L46) is the queue
object embedded in the child PCB. Each waiting PCB's
[`wait_next`](kernel/process/process.header#L51) links to the next waiter, and its
[`waiting_queue_ptr`](kernel/process/process.header#L48) points back to
`&child->waiters`. No separate queue allocation is needed.
[`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid) adds the request and result handoff.

### 7.1.1 Blocking with `sleep` and waking with `wakeup`
[\[↑ TOC\]](#contents)

[`sleep(queue)`](library/unistd/blocking.picoc#L9) waits for an event on an
existing [`wait_queue`](common/wait_queue.header#L5), rather than delaying for
a fixed time. Its syscall calls
[`sleep_on_wait_queue()`](kernel/process/process.picoc#L390), which appends the
current PCB to the queue and sets its [`state`](kernel/process/process.header#L33)
to [`BLOCKED`](kernel/process/process.header#L15). The
[`dispatcher`](kernel/dispatcher.picoc#L71) saves the process's
[`activation`](kernel/process/process.header#L40) and switches away.

[`wakeup(queue)`](library/unistd/blocking.picoc#L19) reaches
[`wakeup_wait_queue()`](kernel/process/process.picoc#L395), which removes at most
the FIFO [`head`](common/wait_queue.header#L6), clears the waiter's
[`wait_next`](kernel/process/process.header#L51) and
[`waiting_queue_ptr`](kernel/process/process.header#L48), and sets its
[`state`](kernel/process/process.header#L33) to
[`READY`](kernel/process/process.header#L13). An empty queue has no waiter to
wake. Wakeup itself does not switch processes.

If the waiter's [`state`](kernel/process/process.header#L33) is
[`STOPPED`](kernel/process/process.header#L16), wakeup leaves that state in
place and sets [`stopped_from_state`](kernel/process/process.header#L62) to
[`READY`](kernel/process/process.header#L13). The process can become runnable
when [`SIGCONT`](common/signal.header#L6) reaches
[`continue_process()`](kernel/signal.picoc#L50).

#### 7.1.1.1 From blocking to resumed execution
[\[↑ TOC\]](#contents)

For a wait without a stop signal, the cycle follows one process's PCB
[`state`](kernel/process/process.header#L33) from
[`BLOCKED`](kernel/process/process.header#L15) through
[`READY`](kernel/process/process.header#L13) to
[`RUNNING`](kernel/process/process.header#L14). Waking ends the wait for an
event. The process then waits for CPU time until the
[`scheduler`](kernel/scheduler.picoc#L12) selects it and the
[`dispatcher`](kernel/dispatcher.picoc#L43) restores its saved execution:

![Waiting cycle: sleep() joins a wait queue with PCB state BLOCKED, wakeup() removes the waiter and sets state READY, then the scheduler selects the process and the dispatcher resumes it with state RUNNING.](documentation/images/blocking-cycle.svg)

Other blocking operations use the same queue mechanism or update the same
PCB state through their own completion functions. The table pairs each wait
with its queue and the event that completes it:

| Blocking event | Wait queue | Wakeup event |
| --- | --- | --- |
| A process calls [`sleep(queue)`](library/unistd/blocking.picoc#L9) through a syscall | Caller-supplied [`wait_queue`](common/wait_queue.header#L5) | Another process calls [`wakeup(queue)`](library/unistd/blocking.picoc#L19) through a syscall, waking one waiter |
| A parent calls [`waitpid(child_pid)`](library/sys/wait/wait.picoc#L14) while the child is still running | Child PCB's embedded [`waiters`](kernel/process/process.header#L46) | Child [`exit(status)`](library/stdlib/exit.picoc#L3) or [`kill_process(child, signal)`](kernel/signal.picoc#L71) reaches [`terminate_process(child, status)`](kernel/process/process.picoc#L304), which delivers status and wakes the parent through [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) |
| A held lock makes [`mutex_lock(m)`](library/mutex/mutex.picoc#L18) call [`sleep(&m->waiters)`](library/unistd/blocking.picoc#L9) | Mutex's embedded [`waiters`](library/mutex/mutex.header#L8) | [`mutex_unlock(m)`](library/mutex/mutex.picoc#L25) releases the lock and calls [`wakeup(&m->waiters)`](library/unistd/blocking.picoc#L19) |
| A terminal [`read()`](library/unistd/io.picoc#L6) finds no input in [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134) | [`Terminal.input_waiters`](kernel/filesystem/terminal.header#L14) | A UART byte triggers [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213), then [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182) delivers input and sets the reader's [`state`](kernel/process/process.header#L33) to [`READY`](kernel/process/process.header#L13) |
| [`start_dma_uart_receive()`](kernel/dma.picoc#L18) starts a transfer during process loading | Global [`dma_waiters`](kernel/dma.picoc#L6) | DMA completion triggers [`handle_dma_interrupt()`](kernel/dma.picoc#L40), which calls [`wakeup_wait_queue()`](kernel/process/process.picoc#L395) |

A child's stop event also wakes a waiting parent through
[`notify_process_stopped()`](kernel/signal.picoc#L23). Signal-specific handling
is described in [`7.2 Process signals`](#72-process-signals).

### 7.1.2 Child waiting with `waitpid`
[\[↑ TOC\]](#contents)

[`waitpid(pid)`](library/sys/wait/wait.picoc#L14) uses the same blocking and wakeup
primitives as [`sleep()`](library/unistd/blocking.picoc#L9) and
[`wakeup()`](library/unistd/blocking.picoc#L19), but selects the child's embedded
[`waiters`](kernel/process/process.header#L46) queue. Only the process whose
[`pid`](kernel/process/process.header#L32) matches the child's
[`parent_pid`](kernel/process/process.header#L57) may wait for it.
[`10.1 From a library call to the kernel: waitpid`](#101-from-a-library-call-to-the-kernel-waitpid)
shows the complete library implementation, its files, and the syscall path.

When the child has neither stopped nor terminated, [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348)
saves the result address in the parent's
[`waiting_status_ptr`](kernel/process/process.header#L44) and calls
[`sleep_on_wait_queue()`](kernel/process/process.picoc#L390) with the child's queue.
The parent's [`waiting_queue_ptr`](kernel/process/process.header#L48) points back
to that queue, and its [`state`](kernel/process/process.header#L33) becomes
[`BLOCKED`](kernel/process/process.header#L15). The result integer remains in
the parent's suspended userspace stack frame until the wait completes.

Child termination delivers the result through the saved pointer, as shown
in [`7.1.2.1 Recording termination status`](#7121-recording-termination-status).
A child stop delivers its status through
[`notify_process_stopped()`](kernel/signal.picoc#L23) without removing the child.
Both paths use [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), which clears the parent's
[`waiting_queue_ptr`](kernel/process/process.header#L48) and
[`wait_next`](kernel/process/process.header#L51). An ordinary parent's
[`state`](kernel/process/process.header#L33) becomes
[`READY`](kernel/process/process.header#L13). If the parent itself is stopped,
its state stays [`STOPPED`](kernel/process/process.header#L16), while
[`stopped_from_state`](kernel/process/process.header#L62) becomes
[`READY`](kernel/process/process.header#L13). It resumes only after
[`SIGCONT`](common/signal.header#L6).

An already stopped child or zombie supplies its status immediately without
queuing the parent. Invalid PIDs and non-children return `-1`.
[`7.1.2.2 Parent collection and final removal`](#7122-parent-collection-and-final-removal)
explains how the order of waiting and termination determines when the
child's PCB and resources are freed. If the parent is removed during a
wait, [`remove_process()`](kernel/process/process.picoc#L209) follows
[`waiting_queue_ptr`](kernel/process/process.header#L48) to unlink it before
freeing its PCB, preventing a later wakeup from following freed memory.

#### 7.1.2.1 Recording termination status
[\[↑ TOC\]](#contents)

The child's [`exit_status`](kernel/process/process.header#L60) must reach the
parent even if its [`waitpid()`](library/sys/wait/wait.picoc#L14) call is suspended.
The child's [`waiters`](kernel/process/process.header#L46) queue identifies the
waiting parent, and the parent's
[`waiting_status_ptr`](kernel/process/process.header#L44) identifies where to
write the result. If the child terminates first, its PCB retains the status
until the parent collects it.

The library call creates two separate objects on the parent's User Process
Stack: a local [`int status = 0`](library/sys/wait/wait.picoc#L15) and a two-cell
[`WaitPidRequest request`](library/sys/wait/wait.picoc#L16). The request's
[`pid`](common/syscall.header#L62) selects the child. Its
[`status`](common/syscall.header#L63) field stores `&status`, the address of the
separate integer. When the child calls [`exit(7)`](library/stdlib/exit.picoc#L3),
the kernel writes the value `7` into that integer, and
[`waitpid()`](library/sys/wait/wait.picoc#L14) returns it.

The diagram uses the SRAM hierarchy from
[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy).
PCB A is the parent and PCB B is its child. It expands their Kernel Heap
records and the parent's Process Payload, then shows the suspended call's
stack frames. `BAF_wait` denotes the frame base of
[`waitpid()`](library/sys/wait/wait.picoc#L14), and each labeled field occupies
one 32-bit RETI cell. The three local-cell offsets follow the generated
[`waitpid()` code](library/sys/wait/libwait.reti_blocks). The PCB fields show
status delivery before child removal. Solid arrows locate the result cell
through stored pointers, the dashed gray arrow shows the kernel's write
when the parent is already waiting, and gray dashed lines connect expanded
views of the same memory:

![SRAM layout with PCB A for the parent and PCB B for its child, Process Payload A with the parent's User Process Heap and expanded User Process Stack, showing WaitPidRequest.status and PCB A's waiting_status_ptr pointing to the separate int status cell that receives 7](documentation/images/process-termination-status.svg)

The detailed handoff for a parent already waiting is:

1. [`waitpid()`](library/sys/wait/wait.picoc#L14) puts its local status address in a [`WaitPidRequest`](common/syscall.header#L61).
2. [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) saves that address in the parent's
   [`waiting_status_ptr`](kernel/process/process.header#L44) and calls
   [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390). This queues the parent's PCB on the child's
   [`waiters`](kernel/process/process.header#L46) and sets the parent's
   [`state`](kernel/process/process.header#L33) to [`BLOCKED`](kernel/process/process.header#L15).
3. [`terminate_process()`](kernel/process/process.picoc#L304) stores the child's
   [`exit_status`](kernel/process/process.header#L60) and sets its
   [`state`](kernel/process/process.header#L33) to [`ZOMBIE`](kernel/process/process.header#L17).
   [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) writes the result through the parent's
   [`waiting_status_ptr`](kernel/process/process.header#L44), clears that pointer,
   and wakes the parent through [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), which clears its wait links.
4. When the parent resumes, [`waitpid()`](library/sys/wait/wait.picoc#L14) returns the updated local value.
   The child can already have been removed.

If the child terminates before the parent calls
[`waitpid()`](library/sys/wait/wait.picoc#L14),
[`terminate_process()`](kernel/process/process.picoc#L304) retains its
[`exit_status`](kernel/process/process.header#L60) in the child PCB with
[`state`](kernel/process/process.header#L33) set to
[`ZOMBIE`](kernel/process/process.header#L17). The later
[`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) call writes
that value through [`request.status`](common/syscall.header#L63) into the same
local [`status`](library/sys/wait/wait.picoc#L15) cell and removes the child.
This path does not save [`waiting_status_ptr`](kernel/process/process.header#L44)
or block the parent.

Only the recorded parent may collect a child. The kernel checks that
relationship before reading the status or queuing the caller:

- [`create_process()`](kernel/process/process.picoc#L89) records the loading
  process's [`pid`](kernel/process/process.header#L32) in the new child's
  [`parent_pid`](kernel/process/process.header#L57). It also initializes
  [`waiting_status_ptr`](kernel/process/process.header#L44) to `NULL` and
  [`waiters`](kernel/process/process.header#L46) to an empty queue.
- [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) gets the
  caller PCB from [`current_process()`](kernel/process/process.picoc#L62),
  which reads the global [`active_process`](kernel/process/process.picoc#L18).
  It finds the target using [`find_process_by_pid()`](kernel/process/process.picoc#L162),
  which scans the global [`process_list_head`](kernel/process/process.picoc#L16)
  through PCB [`next`](kernel/process/process.header#L53) links. The request
  supplies only a target PID and result pointer, not the caller's identity.
- The child's [`parent_pid`](kernel/process/process.header#L57) must equal
  the caller's [`pid`](kernel/process/process.header#L32). If they differ, or
  the target does not exist, the kernel writes `-1` through
  [`WaitPidRequest.status`](common/syscall.header#L63) and completes the syscall.
  [`waitpid()`](library/sys/wait/wait.picoc#L14) returns `-1` without blocking
  or removing the target. Knowing another process's PID is insufficient.
  [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261)
  also checks the queued process's PID against the child's
  [`parent_pid`](kernel/process/process.header#L57) before delivering a status.

This is an API check. Without memory isolation, it cannot stop a program
from overwriting kernel memory.

[`10.1.2 Packing arguments and executing the syscall`](#1012-packing-arguments-and-executing-the-syscall)
shows the complete wrapper. [`7.2.1 Supported signals and fixed actions`](#721-supported-signals-and-fixed-actions)
and [`2.8 CPU exceptions and runtime errors`](#28-cpu-exceptions-and-runtime-errors)
explain signal and exception statuses. Explicit [`unload()`](library/unistd/process.picoc#L47)
uses status `0` and forces removal through
[`unload_process_by_pid()`](kernel/process/process.picoc#L328), even if the
parent has not collected the status.

#### 7.1.2.2 Parent collection and final removal
[\[↑ TOC\]](#contents)

Delivering the termination status lets the waiting parent's
[`waitpid()`](library/sys/wait/wait.picoc#L14) call return when the parent
resumes. The kernel can remove the child before that happens because the
result already resides in the parent's stack. If the parent has not waited
yet, the child must retain its
[`exit_status`](kernel/process/process.header#L60) and resources for later
collection. Final collection and removal is called *reaping*.

[`exit(status)`](library/stdlib/exit.picoc#L3) ends the calling process.
[`start_process()`](library/start/start.picoc#L7) also calls it when the
application's entry function returns. The exit path connects the child's
[`waiters`](kernel/process/process.header#L46) queue to status collection
and removal in this order:

- **Enter the kernel:** The exit syscall reaches
  [`exit_process(status)`](kernel/process/process.picoc#L430), which calls
  [`terminate_process()`](kernel/process/process.picoc#L304) for the current process.
- **Handle children:** [`orphan_and_signal_children()`](kernel/process/process.picoc#L279)
  sets direct children's [`parent_pid`](kernel/process/process.header#L57) to `0`,
  removes existing zombie children, and sends live children their nonzero
  [`parent_death_signal`](kernel/process/process.header#L59). They are not reparented to init.
- **Check waiters:** [`process_has_waiting_parent()`](kernel/process/process.picoc#L249)
  checks whether the parent's PCB is in the exiting process's
  [`waiters`](kernel/process/process.header#L46) queue before it is drained.
  [`terminate_process()`](kernel/process/process.picoc#L304) saves this result
  in its local [`parent_is_waiting`](kernel/process/process.picoc#L306) so it
  can decide whether to remove the child after status delivery empties the queue.
- **Store and deliver status:** The kernel records
  [`exit_status`](kernel/process/process.header#L60) and sets
  [`state`](kernel/process/process.header#L33) to [`ZOMBIE`](kernel/process/process.header#L17).
  [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) writes
  through the waiting parent's [`waiting_status_ptr`](kernel/process/process.header#L44),
  clears that pointer, and wakes all waiters. Stopped waiters remain stopped.
- **Remove or retain the PCB:** Removal happens immediately if no parent exists
  or the parent was already waiting. Otherwise, the PCB and its resources
  remain allocated until collection, as shown below.
- **Clean up on removal:** [`remove_process()`](kernel/process/process.picoc#L209)
  unlinks the PCB from its wait queue and the process list, releases shared-memory
  attachments, cancels unfinished loading, and frees the Process Payload,
  descriptor table, owned paths, and PCB. See
  [`5.2 Mapping, unlinking, and deferred destruction`](#52-mapping-unlinking-and-deferred-destruction)
  for shared-memory lifetime rules.
- **Dispatch:** [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55)
  starts another runnable process or waits while the process list is nonempty.
  The exiting process never resumes. If the list becomes empty,
  [`exit_process()`](kernel/process/process.picoc#L430) calls [`shutdown()`](kernel/kernel.picoc#L15).

The order of waiting and termination determines when the PCB is deleted:

| Lifecycle order | Status delivery | PCB removal |
| --- | --- | --- |
| Parent is already waiting in [`waitpid()`](library/sys/wait/wait.picoc#L14) | Termination delivers the status and wakes the parent. | [`terminate_process()`](kernel/process/process.picoc#L304) removes the PCB before dispatch. |
| Child exits before the parent waits | The PCB retains [`exit_status`](kernel/process/process.header#L60) with [`state`](kernel/process/process.header#L33) set to [`ZOMBIE`](kernel/process/process.header#L17). | A later [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) delivers the status and removes the PCB before returning. |
| No parent exists | Nobody can collect the status. | [`terminate_process()`](kernel/process/process.picoc#L304) removes the PCB immediately. |

A zombie retains its full PCB and owned resources, including any unfinished
image load. A later [`waitpid()`](library/sys/wait/wait.picoc#L14) collects its
status and removes it without joining its
[`waiters`](kernel/process/process.header#L46) queue. Reporting a child stop
also completes the wait, but leaves the child and its resources available
for continuation.

### 7.1.3 Wait queue function reference
[\[↑ TOC\]](#contents)

The table maps the library operations to their kernel queue primitives:

| Public/library operation | Syscall and kernel call path | Completion path |
| --- | --- | --- |
| [`sleep(wq)`](library/unistd/blocking.picoc#L9) | [`SYSCALL_SLEEP`](common/syscall.header#L19) → [`handle_syscall()`](kernel/syscall.picoc#L16) → [`sleep_on_wait_queue(wq, caller_context)`](kernel/process/process.picoc#L390) → [`enqueue_current_process_on_wait_queue(wq)`](kernel/process/process.picoc#L375) | An event owner reaches [`wakeup_wait_queue(wq)`](kernel/process/process.picoc#L395), often through [`wakeup(wq)`](library/unistd/blocking.picoc#L19). |
| [`wakeup(wq)`](library/unistd/blocking.picoc#L19) | [`SYSCALL_WAKEUP`](common/syscall.header#L20) → [`handle_syscall()`](kernel/syscall.picoc#L16) → [`wakeup_wait_queue(wq)`](kernel/process/process.picoc#L395) | Clears the removed PCB's intrusive membership fields and makes it [`READY`](kernel/process/process.header#L13), or records completion beneath [`STOPPED`](kernel/process/process.header#L16). |
| [`waitpid(pid)`](library/sys/wait/wait.picoc#L14) | [`SYSCALL_WAITPID`](common/syscall.header#L13) → [`handle_syscall()`](kernel/syscall.picoc#L16) → [`wait_for_process_by_pid(request, caller_context)`](kernel/process/process.picoc#L348) → the same [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390) used by [`sleep`](library/unistd/blocking.picoc#L9) | Child termination calls [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261), which writes the status and calls the same [`wakeup_wait_queue()`](kernel/process/process.picoc#L395) used by public [`wakeup`](library/unistd/blocking.picoc#L19). Child stopping uses [`notify_process_stopped()`](kernel/signal.picoc#L23) and that same wake primitive. |

The function reference starts with syscall-backed operations, followed by
queue and child-lifecycle helpers:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`wait_for_process_by_pid(request, caller_context)`](kernel/process/process.picoc#L348) | Returns `true` after an immediate invalid, zombie, or stopped result. The normal blocking path switches away and resumes userspace with the successful `IN2 = 1` preset by [`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94). The source-level `false` fallback is reached only if dispatch returns instead of restoring a process. | Validates the parent-child relationship. Immediately collects a zombie or stopped status. Otherwise copies `request->status` into the parent PCB and blocks it on `&child->waiters`. | [`current_process()`](kernel/process/process.picoc#L62), [`find_process_by_pid()`](kernel/process/process.picoc#L162), [`remove_process()`](kernel/process/process.picoc#L209), [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390) | **Library functions:** [`waitpid()`](library/sys/wait/wait.picoc#L14) through [`SYSCALL_WAITPID`](common/syscall.header#L13)<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`sleep_on_wait_queue(queue, caller_context)`](kernel/process/process.picoc#L390) | Returns no value. Normally dispatch leaves through `RTI` and the saved userspace context resumes after a later wakeup. A C return is possible only if dispatch finds an empty process list. | Links the current PCB to `queue`, changes it to [`BLOCKED`](kernel/process/process.header#L15), saves its activation, and dispatches another process. | [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375), [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) | **Library functions:** [`sleep()`](library/unistd/blocking.picoc#L9) through [`SYSCALL_SLEEP`](common/syscall.header#L19). [`waitpid()`](library/sys/wait/wait.picoc#L14) through [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348)<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16), [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) |
| [`wakeup_wait_queue(queue)`](kernel/process/process.picoc#L395) | `false` when empty. `true` after waking one FIFO head. | Advances [`head`](common/wait_queue.header#L6), fixes [`tail`](common/wait_queue.header#L7), clears the removed PCB's [`wait_next`](kernel/process/process.header#L51) and [`waiting_queue_ptr`](kernel/process/process.header#L48), and makes it ready or records a completed wait under [`STOPPED`](kernel/process/process.header#L16). | None | **Library functions:** [`wakeup()`](library/unistd/blocking.picoc#L19) through [`SYSCALL_WAKEUP`](common/syscall.header#L20)<br>**Kernel functions:** [`handle_syscall()`](kernel/syscall.picoc#L16), [`handle_dma_interrupt()`](kernel/dma.picoc#L40), [`notify_process_stopped()`](kernel/signal.picoc#L23), [`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261) |
|  |  |  |  |  |
| [`enqueue_current_process_on_wait_queue(queue)`](kernel/process/process.picoc#L375) | Returns no value. | Appends the current PCB in constant time, sets its [`waiting_queue_ptr`](kernel/process/process.header#L48), clears its [`wait_next`](kernel/process/process.header#L51), and changes it to [`BLOCKED`](kernel/process/process.header#L15). | [`current_process()`](kernel/process/process.picoc#L62) | **Library functions:** [`sleep()`](library/unistd/blocking.picoc#L9) and [`waitpid()`](library/sys/wait/wait.picoc#L14) through [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390)<br>**Kernel functions:** [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390), [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`start_dma_uart_receive()`](kernel/dma.picoc#L18) |
| [`remove_from_wait_queue(process)`](kernel/process/process.picoc#L176) | Returns no value. No change when `waiting_queue_ptr == NULL` or the PCB is not found. | Follows the PCB's queue back-reference, finds its predecessor, reconnects the intrusive list, fixes queue endpoints, and clears membership fields. This is the arbitrary-member removal path, unlike FIFO wakeup. | None | **Kernel functions:** [`remove_process()`](kernel/process/process.picoc#L209), [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84), [`suspend_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L75) |
| [`process_has_waiting_parent(process)`](kernel/process/process.picoc#L249) | `true` when the target process's queue contains a PCB whose PID equals its [`parent_pid`](kernel/process/process.header#L57). Otherwise `false`. | Traverses `process->waiters` through [`wait_next`](kernel/process/process.header#L51) without mutation. The result tells termination whether status delivery permits immediate child removal. | None | **Kernel functions:** [`terminate_process()`](kernel/process/process.picoc#L304) |
| [`wake_parent_waiting_for_process(process, status)`](kernel/process/process.picoc#L261) | Returns no value. | Drains the process's waiter queue. For its parent PCB, writes through [`waiting_status_ptr`](kernel/process/process.header#L44) and clears that pointer before waking. | [`wakeup_wait_queue()`](kernel/process/process.picoc#L395) | **Kernel functions:** [`terminate_process()`](kernel/process/process.picoc#L304) |
| [`notify_process_stopped(process)`](kernel/signal.picoc#L23) | Returns no value. | Drains the stopped process's waiter queue, writes `128 + stop_signal` through each non-`NULL` [`waiting_status_ptr`](kernel/process/process.header#L44), clears it, and wakes each waiter. | [`wakeup_wait_queue()`](kernel/process/process.picoc#L395) | **Kernel functions:** [`stop_process()`](kernel/signal.picoc#L37) |

## 7.2 Process signals
[\[↑ TOC\]](#contents)

Signals add stop, continue, and termination actions to ordinary waiting.
PicoOS uses fixed actions, with their state stored in each PCB.

### 7.2.1 Supported signals and fixed actions
[\[↑ TOC\]](#contents)

Signals have fixed kernel actions and cannot be caught or ignored. The small
amount of per-process signal state is embedded in each PCB:

| Attribute | Meaning | Used by |
| --- | --- | --- |
| [`pending_termination_signal`](kernel/process/process.header#L63) | [`SIGINT`](common/signal.header#L4)/[`SIGKILL`](common/signal.header#L5) deferred while the target is the running process | First initialized to 0 by [`create_process()`](kernel/process/process.picoc#L89), set by [`send_signal_to_process()`](kernel/signal.picoc#L75), consumed by [`prepare_process_termination()`](kernel/signal.picoc#L126) |
| [`stop_signal`](kernel/process/process.header#L61) | Identifies the signal reported for the current stopped state | First initialized to 0 by [`create_process()`](kernel/process/process.picoc#L89), set by [`stop_process()`](kernel/signal.picoc#L37) and the input-ownership check in [`continue_process()`](kernel/signal.picoc#L50), read by [`notify_process_stopped()`](kernel/signal.picoc#L23) and [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) |
| [`stopped_from_state`](kernel/process/process.header#L62) | State reconsidered on [`SIGCONT`](common/signal.header#L6) | First initialized to [`READY`](kernel/process/process.header#L13) by [`create_process()`](kernel/process/process.picoc#L89), set by [`stop_process()`](kernel/signal.picoc#L37), [`wakeup_wait_queue()`](kernel/process/process.picoc#L395), and [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84), read by [`continue_process()`](kernel/signal.picoc#L50) |
| [`parent_death_signal`](kernel/process/process.header#L59) | Signal delivered when the parent terminates | First initialized by [`create_process()`](kernel/process/process.picoc#L89), set by [`set_parent_death_signal()`](kernel/signal.picoc#L137) |
| [`pending_terminal_read_buffer`](kernel/process/process.header#L65), [`pending_terminal_read_count`](kernel/process/process.header#L66) | Terminal request retained across any stop while the read is pending | First initialized to `NULL`/0 by [`create_process()`](kernel/process/process.picoc#L89), set by [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), consumed by [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182) or [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) |

[`foreground_process_target`](kernel/signal.picoc#L12) selects terminal input ownership and signal
delivery. [`8.4 Foreground input ownership and terminal-generated signals`](#84-foreground-input-ownership-and-terminal-generated-signals) explains its signed encoding and the [`SIGTTIN`](common/signal.header#L9) read path.

PicoOS implements six signals. Signal `0` is an additional existence probe
for [`kill()`](library/signal/signal.picoc#L14). The table lists their actions and statuses:

| Number | Name | Kernel action | Reported status/state |
| ---: | --- | --- | --- |
| 0 | Probe | Validates that a non-zombie PID exists | No change |
| 2 | [`SIGINT`](common/signal.header#L4) | Terminates the target | Exit status 130 |
| 9 | [`SIGKILL`](common/signal.header#L5) | Terminates the target | Exit status 137 |
| 18 | [`SIGCONT`](common/signal.header#L6) | Resumes a stopped target | [`READY`](kernel/process/process.header#L13), or [`BLOCKED`](kernel/process/process.header#L15) if its original wait is still active |
| 19 | [`SIGSTOP`](common/signal.header#L7) | Stops the target | [`STOPPED`](kernel/process/process.header#L16), status 147 |
| 20 | [`SIGTSTP`](common/signal.header#L8) | Stops the target | [`STOPPED`](kernel/process/process.header#L16), status 148 |
| 21 | [`SIGTTIN`](common/signal.header#L9) | Stops the target, generated when a background process reads the terminal | [`STOPPED`](kernel/process/process.header#L16), status 149 |

[`signal_number_is_valid()`](kernel/signal.picoc#L14) accepts only the six named constants.
[`kill(pid, 0)`](library/signal/signal.picoc#L14) or `kill.bin 0 PID` probes existence without delivering a
signal. It returns `0` for an existing non-zombie process and `-1` otherwise.
The [`parent_death_signal`](kernel/process/process.header#L59) test uses this to check whether children survived.

[POSIX](https://pubs.opengroup.org/onlinepubs/9799919799/functions/kill.html) calls signal `0` the *null signal*. [Linux `kill(2)`](https://man7.org/linux/man-pages/man2/kill.2.html) checks existence
and permission without sending a signal. PicoOS keeps the existence check
but has no identities, permissions, or process-group PID forms. It also
rejects zombies, which POSIX counts as existing until collection.

### 7.2.2 Stopping and continuing a process
[\[↑ TOC\]](#contents)

Stopping records [`stop_signal`](kernel/process/process.header#L61) and [`stopped_from_state`](kernel/process/process.header#L62), sets [`STOPPED`](kernel/process/process.header#L16),
and reports the stopped status to a waiting parent. [`WIFSTOPPED()`](library/sys/wait/wait.picoc#L25) recognizes
all three stop signals. Terminal reads detach from their queue but retain
the buffer and count. [`SIGCONT`](common/signal.header#L6) makes an ordinary stopped process ready.
An unfinished nonterminal wait instead returns to [`BLOCKED`](kernel/process/process.header#L15).

A background reader receives [`SIGTTIN`](common/signal.header#L9) even when input is buffered. The
kernel retains its read request without queueing it. Foreground ownership
and [`SIGCONT`](common/signal.header#L6) are needed to resume that read. [`8.4 Foreground input ownership and terminal-generated signals`](#84-foreground-input-ownership-and-terminal-generated-signals) follows this case.

### 7.2.3 Termination, `Ctrl-C`, and parent collection
[\[↑ TOC\]](#contents)

Normal exit and signal termination reach [`terminate_process()`](kernel/process/process.picoc#L304). Normal exit
uses the application's status, while signals use `128 + signal_number`.
[`kill.bin`](user/kill.picoc#L69) defaults to [`SIGKILL`](common/signal.header#L5) and yields after an accepted request.
[`7.1.2.1 Recording termination status`](#7121-recording-termination-status) explains how the status reaches the parent's result cell.

`Ctrl+C` sends [`SIGINT`](common/signal.header#L4) through the UART handler to the foreground target.
A noncurrent target can terminate immediately. For the current running
process, [`pending_termination_signal`](kernel/process/process.header#L63) and a reschedule request defer it
until dispatch. [`prepare_process_termination()`](kernel/signal.picoc#L126) consumes that signal
before the process can be selected again.

If its parent is already waiting, termination delivers the status, wakes
the parent, and removes the child. This is the usual foreground `Ctrl+C`
case: the shell resumes with status `130` and reclaims terminal ownership.

Otherwise the child retains [`exit_status`](kernel/process/process.header#L60) as a zombie until a later
[`waitpid()`](library/sys/wait/wait.picoc#L14) collects it. [`7.1.2.2 Parent collection and final removal`](#7122-parent-collection-and-final-removal) explains final cleanup.

### 7.2.4 Fixed PicoOS signal actions compared with Unix
[\[↑ TOC\]](#contents)

Unix and Linux allow catching or ignoring [`SIGINT`](common/signal.header#L4), [`SIGTSTP`](common/signal.header#L8), and [`SIGTTIN`](common/signal.header#L9).
[`SIGKILL`](common/signal.header#L5) and [`SIGSTOP`](common/signal.header#L7) cannot be caught. PicoOS instead gives fixed actions
to all six signals. Termination of the current process waits for dispatch,
while stop and continue update state immediately.

### 7.2.5 Signal function reference
[\[↑ TOC\]](#contents)

The table connects validation, state changes, deferred termination, and
parent-death settings to their functions:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`send_signal_by_pid(request)`](kernel/signal.picoc#L108) | `0` on delivery/probe, `-1` for an invalid signal, missing PID, or zombie | Finds target, signal 0 only checks existence | [`signal_number_is_valid()`](kernel/signal.picoc#L14), [`find_process_by_pid()`](kernel/process/process.picoc#L162), [`send_signal_to_process()`](kernel/signal.picoc#L75) | **Library functions:** [`kill()`](library/signal/signal.picoc#L14)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`set_parent_death_signal(request)`](kernel/signal.picoc#L137) | `0` on success, `-1` for an unsupported option or invalid signal | Changes current PCB parent-death setting | [`signal_number_is_valid()`](kernel/signal.picoc#L14), [`current_process()`](kernel/process/process.picoc#L62) | **Library functions:** [`prctl()`](library/sys/prctl/prctl.picoc#L14)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
|  |  |  |  |  |
| [`send_signal_to_process(process, signal_number)`](kernel/signal.picoc#L75) | Returns no value | Continues, stops, terminates, or defers running-target termination and requests a safe reschedule | [`signal_number_is_valid()`](kernel/signal.picoc#L14), [`continue_process()`](kernel/signal.picoc#L50), [`stop_process()`](kernel/signal.picoc#L37), [`current_process()`](kernel/process/process.picoc#L62), [`dispatcher_request_reschedule()`](kernel/dispatcher.picoc#L10), [`kill_process()`](kernel/signal.picoc#L71) | **Kernel functions:** [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`handle_terminal_signal_character()`](kernel/signal.picoc#L192), [`orphan_and_signal_children()`](kernel/process/process.picoc#L279), [`send_signal_by_pid()`](kernel/signal.picoc#L108) |
| [`kill_process(process, signal_number)`](kernel/signal.picoc#L71) | Returns no value | Calls the general termination path with that termination signal's status | [`terminate_process()`](kernel/process/process.picoc#L304) | **Kernel functions:** [`prepare_process_termination()`](kernel/signal.picoc#L126), [`send_signal_to_process()`](kernel/signal.picoc#L75) |
| [`stop_process(process, signal_number)`](kernel/signal.picoc#L37) | Returns no value | Saves signal/prior state, changes to [`STOPPED`](kernel/process/process.header#L16), reports to waiters | [`suspend_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L75), [`notify_process_stopped()`](kernel/signal.picoc#L23) | **Kernel functions:** [`send_signal_to_process()`](kernel/signal.picoc#L75) |
| [`continue_process(process)`](kernel/signal.picoc#L50) | Returns no value | Resumes ordinary stops, a pending terminal read additionally requires input ownership | [`process_has_terminal_input()`](kernel/signal.picoc#L173), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) | **Kernel functions:** [`send_signal_to_process()`](kernel/signal.picoc#L75) |
| [`prepare_process_termination(process)`](kernel/signal.picoc#L126) | `true` when no termination is pending, `false` after applying deferred termination | Applies deferred termination | [`kill_process()`](kernel/signal.picoc#L71) | **Kernel functions:** [`dispatcher_start_next_process()`](kernel/dispatcher.picoc#L55) |

Parent termination sets direct children's [`parent_pid`](kernel/process/process.header#L57) to `0`, removes
zombie children, and signals live children when configured. Children inherit
[`parent_death_signal`](kernel/process/process.header#L59). [`prctl(PR_SET_PDEATHSIG, 0)`](library/sys/prctl/prctl.picoc#L14) disables it. There is no
background reaper or separate child-exit notification signal.

## 7.3 Mutexes with test-and-set and wait queues
[\[↑ TOC\]](#contents)

A mutex combines atomic `TSL` with a wait queue. Contention sleeps instead
of spinning. Unlock clears the lock and wakes one waiter.

The declaration in [`mutex.header`](library/mutex/mutex.header#L6) shows that
both fields belong to [`struct mutex`](library/mutex/mutex.header#L6).
[`lock`](library/mutex/mutex.header#L7) records whether the mutex is held.
[`waiters`](library/mutex/mutex.header#L8) is an embedded
[`struct wait_queue`](common/wait_queue.header#L5) whose pointers link the
PCBs of processes waiting to acquire this mutex:

```c
struct mutex {
    bool lock;
    struct wait_queue waiters;
};
```

In shared memory, participants see the same lock and queue. The linked
PCBs remain kernel objects. [`9.4 Wait requests and queue storage`](#94-wait-requests-and-queue-storage) compares queue storage.

[`mutex_init()`](library/mutex/mutex.picoc#L12) initializes both fields before use. [`mutex_lock()`](library/mutex/mutex.picoc#L18) retries
[`testset()`](library/mutex/mutex.picoc#L3) after each wakeup. These are the complete library functions:

```c
bool testset(bool *lock_addr) {
    int old;

    asm("LOADIN BAF IN2 3");
    asm("TSL IN2 ACC 0");
    asm("STOREIN BAF ACC 0");
    return old;
}

void mutex_init(struct mutex *m) {
    m->lock = false;
    wait_queue_init(&(m->waiters));
    return;
}

void mutex_lock(struct mutex *m) {
    while (testset(&(m->lock))) {
        sleep(&(m->waiters));
    }
    return;
}

void mutex_unlock(struct mutex *m) {
    m->lock = false;
    wakeup(&(m->waiters));
    return;
}
```

[`testset()`](library/mutex/mutex.picoc#L3) returns the old lock value while atomically writing `1`.
An old `0` means acquisition. An old `1` means contention. Its result uses
the normal PicoC return register.

The flowchart shows acquisition and unlock. During
[`mutex_unlock()`](library/mutex/mutex.picoc#L25),
[`wakeup_wait_queue()`](kernel/process/process.picoc#L395) checks the
[`head`](common/wait_queue.header#L6) of the mutex's
[`waiters`](library/mutex/mutex.header#L8) queue. An empty queue means nobody
is woken. Otherwise, it removes the first PCB and wakes that process.
The dotted arrow shows this effect on the waiting process, which retries
[`testset()`](library/mutex/mutex.picoc#L3) when scheduled. The unlocking
process returns from [`mutex_unlock()`](library/mutex/mutex.picoc#L25):

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart TD
    A["mutex_lock: call testset"] --> B{"Old lock value?"}
    B -->|false| C["Lock changed from 0 to 1<br/>enter critical section"]
    B -->|true| D["sleep on mutex.waiters"]
    D --> E["Waiting process resumes when scheduled"]
    E --> A
    C --> F["mutex_unlock: clear lock, then call wakeup"]
    F --> G{"Queue empty?<br/>mutex.waiters.head == NULL"}
    G -->|Yes| H["Wake nobody"]
    G -->|No| W["Remove first PCB from mutex.waiters<br/>wake that process"]
    H --> R["mutex_unlock returns"]
    W --> R
    W -.-> E
```

The field table describes the shared state, followed by the library
operations and their queue syscalls:

| Attribute | Meaning | Used by |
| --- | --- | --- |
| [`lock`](library/mutex/mutex.header#L7) | False when unlocked, `TSL` stores true and returns the old value | First initialized by [`mutex_init()`](library/mutex/mutex.picoc#L12), tested/set by [`testset()`](library/mutex/mutex.picoc#L3) from [`mutex_lock()`](library/mutex/mutex.picoc#L18), cleared by [`mutex_unlock()`](library/mutex/mutex.picoc#L25) |
| [`waiters`](library/mutex/mutex.header#L8) | Embedded FIFO of contending PCBs | First initialized by [`mutex_init()`](library/mutex/mutex.picoc#L12) through [`wait_queue_init()`](library/unistd/blocking.picoc#L4), passed to [`sleep()`](library/unistd/blocking.picoc#L9) and [`wakeup()`](library/unistd/blocking.picoc#L19) |

| Library function | Return value / status and purpose | Syscalls |
| --- | --- | --- |
| [`testset(lock_addr)`](library/mutex/mutex.picoc#L3) | Returns the previous lock value while atomically storing true | None, uses RETI `TSL` |
| [`mutex_init(m)`](library/mutex/mutex.picoc#L12) | No value, clears the lock and initializes the queue | None |
| [`mutex_lock(m)`](library/mutex/mutex.picoc#L18) | No value, returns after acquiring the lock, sleeping and retrying while it is held | [`SYSCALL_SLEEP`](common/syscall.header#L19) through [`sleep()`](library/unistd/blocking.picoc#L9) |
| [`mutex_unlock(m)`](library/mutex/mutex.picoc#L25) | No value, clears the lock and makes at most one waiter eligible | [`SYSCALL_WAKEUP`](common/syscall.header#L20) through [`wakeup()`](library/unistd/blocking.picoc#L19) |

Only `TSL` is atomic. Unlock can happen between a failed test and [`sleep()`](library/unistd/blocking.picoc#L9),
waking nobody before the contender joins the queue. This lost wakeup can
leave it blocked under preemption. A woken contender must test again when
scheduled.

# 8. Terminal, file descriptors, and host filesystem
[\[↑ TOC\]](#contents)

The kernel manages descriptors, paths, terminal input, and UART requests.
The emulator host stores files. This chapter connects the process-local
I/O state to terminal devices and host-backed operations.

## 8.1 Per-process file-descriptor table
[\[↑ TOC\]](#contents)

The PCB's [`file_descriptors`](kernel/process/process.header#L42) points to a
[`FileDescriptorTable`](kernel/filesystem/file_descriptor.header#L22). Its
[`entries`](kernel/filesystem/file_descriptor.header#L23) points to one contiguous
array of eight [`FileDescriptor`](kernel/filesystem/file_descriptor.header#L15)
entries, indexed by descriptor number.

The diagram expands the Kernel Heap from
[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy).
The PCB, table, array, and copied [`path`](kernel/filesystem/file_descriptor.header#L19)
strings each occupy separate [`BlockHeader`](common/heap.header#L5) payloads.
Descriptor 3 shows an opened file, with other allocations omitted:

![SRAM layout with an expanded Kernel Heap showing PCB 1 pointing to a separately allocated FileDescriptorTable, its entries pointer reaching a single eight-element array, and descriptor 3 pointing to a separately allocated path string](documentation/images/process-file-descriptors.svg)

[`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35) initializes all entries and assigns the
three standard terminal streams. Run setup replaces it with an inherited
copy, except for init. [`9.2 Containment and reference relationships`](#92-containment-and-reference-relationships) shows the allocation boundaries.

The wrapper names the object that owns the array. Like [`Heap`](common/heap.header#L11), it adds
indirection, but its [`entries`](kernel/filesystem/file_descriptor.header#L23) pointer never changes after construction.
The source records no additional runtime requirement for that wrapper.

[`FILE_DESCRIPTOR_COUNT`](kernel/filesystem/file_descriptor.header#L6) permits indices 0–7. Ordinary [`open()`](library/fcntl/fcntl.picoc#L5) searches
only 0–4, leaving three slots for the shell's saved descriptors:

| Index | Initial or conventional use | Availability to [`open()`](library/fcntl/fcntl.picoc#L5) |
| ---: | --- | --- |
| 0 | [`STDIN_FILENO`](common/file.header#L5), initially terminal input | Reused if closed |
| 1 | [`STDOUT_FILENO`](common/file.header#L6), initially terminal output | Reused if closed |
| 2 | [`STDERR_FILENO`](common/file.header#L7), initially terminal error output | Reused if closed |
| 3 | Free initially, first additional opened file or device | Available |
| 4 | Free initially, second additional opened file or device | Available |
| 5 | Reserved shell save slot for stdin during `<` | Never returned by [`open()`](library/fcntl/fcntl.picoc#L5) |
| 6 | Reserved shell save slot for stdout during `>` or `>>` | Never returned by [`open()`](library/fcntl/fcntl.picoc#L5) |
| 7 | Reserved shell save slot for stderr during `2>` or `2>>` | Never returned by [`open()`](library/fcntl/fcntl.picoc#L5) |

Inheritance always copies 0–2. It copies 3–4 only when their [`kind`](kernel/filesystem/file_descriptor.header#L16) is
[`FILE_DESCRIPTOR_FILE`](kernel/filesystem/file_descriptor.header#L13), and skips 5–7. Each entry and path is independent,
unlike Unix shared open-file descriptions.

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    subgraph PARENT["parent entries[0..7]"]
        P02["0, 1, 2<br/>always copy"]
        P34["3, 4<br/>copy only FILE kind"]
        P57["5, 6, 7<br/>never examine"]
    end
    subgraph CHILD["new child table and array"]
        C02["0, 1, 2<br/>deep copies"]
        C34["3, 4<br/>FILE deep copies or FREE"]
        C57["5, 6, 7<br/>FREE"]
    end
    P02 --> C02
    P34 -->|"conditional"| C34
    P57 -. "not inherited" .-> C57
```

[`free_file_descriptor()`](kernel/filesystem/filesystem.picoc#L27) selects the lowest free slot in 0–4. With standard
streams open, two slots remain. Closing a standard stream makes its slot
available too. Exhaustion returns `-1`. [`dup2()`](library/unistd/io.picoc#L58) can explicitly use 5–7.
The shell closes nonstandard inherited descriptors at startup and releases
its temporary saves after redirection. [`12.6 Input/output redirection`](#126-inputoutput-redirection) follows that sequence.

[`kind`](kernel/filesystem/file_descriptor.header#L16), access flags, offset, and path all affect I/O. The field table
shows their roles:

| Field | Meaning | Used by |
| --- | --- | --- |
| [`FileDescriptor.kind`](kernel/filesystem/file_descriptor.header#L16) | Integer constant, not an enum: [`FILE_DESCRIPTOR_FREE`](kernel/filesystem/file_descriptor.header#L9) = 0, [`FILE_DESCRIPTOR_STDIN`](kernel/filesystem/file_descriptor.header#L10) = 1, [`FILE_DESCRIPTOR_STDOUT`](kernel/filesystem/file_descriptor.header#L11) = 2, [`FILE_DESCRIPTOR_STDERR`](kernel/filesystem/file_descriptor.header#L12) = 3, and [`FILE_DESCRIPTOR_FILE`](kernel/filesystem/file_descriptor.header#L13) = 4. The three standard kinds preserve stream identity. Every explicit open, including a device path, uses [`FILE_DESCRIPTOR_FILE`](kernel/filesystem/file_descriptor.header#L13). Slots 3–4 are inherited only for this last kind. | First initialized by [`initialize_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L24), read by [`inherit_file_descriptors()`](kernel/filesystem/file_descriptor.picoc#L99), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), and [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |
| [`FileDescriptor.flags`](kernel/filesystem/file_descriptor.header#L17) | Integer bit field containing the read/write mode and create, truncate, or append choices. It decides whether later reads and writes are allowed. | First initialized by [`initialize_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L24), set by [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), read by [`file_descriptor_can_read()`](kernel/filesystem/file_descriptor.picoc#L134) and [`file_descriptor_can_write()`](kernel/filesystem/file_descriptor.picoc#L140) |
| [`FileDescriptor.offset`](kernel/filesystem/file_descriptor.header#L18) | Per-entry logical byte position, initialized to 0. Regular reads and successful writes advance it, append writes replace it with the resulting end position, and [`lseek()`](library/unistd/io.picoc#L66) can replace it. | First initialized by [`initialize_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L24), changed by [`read_regular_file()`](kernel/filesystem/filesystem.picoc#L90), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217), and [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268) |
| [`FileDescriptor.path`](kernel/filesystem/file_descriptor.header#L19) | Kernel-owned normalized absolute PicoOS path, or `NULL` for a free entry. Exact terminal/null paths select device behavior before ordinary-file dispatch. | First initialized to `NULL` by [`initialize_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L24), standard paths assigned by [`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35), copied by [`copy_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L82), and freed by close/destruction |
| [`FileDescriptorTable.entries`](kernel/filesystem/file_descriptor.header#L23) | Owned eight-entry array of descriptor state | First allocated by [`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35), copied by [`inherit_file_descriptors()`](kernel/filesystem/file_descriptor.picoc#L99), indexed by I/O, and freed by [`destroy_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L118) |

The case table shows how [`kind`](kernel/filesystem/file_descriptor.header#L16) and path select behavior. There is no pipe
kind because pipelines use temporary files:

| Descriptor case | [`kind`](kernel/filesystem/file_descriptor.header#L16) | [`path`](kernel/filesystem/file_descriptor.header#L19) | Read/write behavior |
| --- | --- | --- | --- |
| Initial standard input | [`FILE_DESCRIPTOR_STDIN`](kernel/filesystem/file_descriptor.header#L10) | `/device/terminal.dev` | Read-only, consumes the global terminal ring and may block |
| Initial standard output | [`FILE_DESCRIPTOR_STDOUT`](kernel/filesystem/file_descriptor.header#L11) | `/device/terminal.dev` | Write-only, sends ordinary UART output to emulator stdout |
| Initial standard error | [`FILE_DESCRIPTOR_STDERR`](kernel/filesystem/file_descriptor.header#L12) | `/device/terminal.dev` | Write-only, selects emulator stderr for the bytes, then restores emulator stdout |
| Opened regular file | [`FILE_DESCRIPTOR_FILE`](kernel/filesystem/file_descriptor.header#L13) | Normalized absolute path | Access flags gate I/O, `read-range` and `write-at` use the saved offset, while `file-size` supports existence checks, append, and [`SEEK_END`](common/file.header#L19), and [`write`](library/unistd/io.picoc#L32) creates or truncates |
| Explicitly opened terminal device | [`FILE_DESCRIPTOR_FILE`](kernel/filesystem/file_descriptor.header#L13) | `/device/terminal.dev` | Access flags gate I/O, reads use the terminal ring and writes use emulator stdout because the kind is not [`FILE_DESCRIPTOR_STDERR`](kernel/filesystem/file_descriptor.header#L12) |
| Explicitly opened null device | [`FILE_DESCRIPTOR_FILE`](kernel/filesystem/file_descriptor.header#L13) | `/device/null.dev` | Reads return 0, writes discard bytes and return the requested count |

Reads and writes validate flags and check device paths before regular-file
I/O. Terminal writes use `STDERR` kind to select error output. Copying stderr
to another index preserves that behavior, while opening the terminal at
index 2 does not create a stderr-kind entry.

Copied offsets later diverge, rather than sharing a Unix open-file
description. The kernel terminal remains one global object, selected by
its special path.

[`dup2()`](library/unistd/io.picoc#L58) copies fields and path before releasing the old target. A copy
onto itself changes nothing. Close resets one entry. Table destruction
frees paths, array, and wrapper. Zombies retain these until collection.

## 8.2 Global terminal input buffer
[\[↑ TOC\]](#contents)

All descriptors naming the terminal device share the global
[`terminal`](kernel/filesystem/terminal.picoc#L12). This
[`Terminal`](kernel/filesystem/terminal.header#L9) lives in kernel `.data`,
with its 128-cell [`input_buffer`](kernel/filesystem/terminal.header#L10)
and [`input_waiters`](kernel/filesystem/terminal.header#L14) queue embedded inside it.

The diagram expands `.data` and the Kernel Heap from
[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy).
The example shows an empty ring and one waiting foreground reader. Both
queue pointers reference its PCB in a heap payload, and its
[`waiting_queue_ptr`](kernel/process/process.header#L48) points back to the embedded queue:

![SRAM layout with the global Terminal embedded in kernel .data, containing its 128-cell input ring, integer indices, count, and reader queue. The queue's head and tail point to PCB 1 in a Kernel Heap payload after Block Header A, and waiting_queue_ptr points back to the embedded queue](documentation/images/process-terminal-input-buffer.svg)

The field table explains how input and reads update this shared state:

| Field | Meaning | Used by |
| --- | --- | --- |
| [`Terminal.input_buffer`](kernel/filesystem/terminal.header#L10) | Embedded ring storage | First written by [`enqueue_terminal_byte()`](kernel/filesystem/terminal.picoc#L49), read by [`pop_terminal_byte()`](kernel/filesystem/terminal.picoc#L26) (only occupied cells are meaningful) |
| [`Terminal.input_head`](kernel/filesystem/terminal.header#L11) | Index of next unread byte to consume | First initialized by [`initialize_terminal()`](kernel/filesystem/terminal.picoc#L14), advanced only by [`pop_terminal_byte()`](kernel/filesystem/terminal.picoc#L26) |
| [`Terminal.input_tail`](kernel/filesystem/terminal.header#L12) | Index of next insertion | First initialized by [`initialize_terminal()`](kernel/filesystem/terminal.picoc#L14), advanced by [`enqueue_terminal_byte()`](kernel/filesystem/terminal.picoc#L49) |
| [`Terminal.input_count`](kernel/filesystem/terminal.header#L13) | Distinguishes full from empty when indices match | First initialized by [`initialize_terminal()`](kernel/filesystem/terminal.picoc#L14), read and changed by [`enqueue_terminal_byte()`](kernel/filesystem/terminal.picoc#L49), [`copy_terminal_bytes()`](kernel/filesystem/terminal.picoc#L35), and [`pop_terminal_byte()`](kernel/filesystem/terminal.picoc#L26) |
| [`Terminal.input_waiters`](kernel/filesystem/terminal.header#L14) | Generic blocking queue containing the active foreground reader while it waits for input | First initialized by [`initialize_terminal()`](kernel/filesystem/terminal.picoc#L14), [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134) and [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) queue readers, completion/suspension remove them |

Kernel startup calls [`initialize_terminal()`](kernel/filesystem/terminal.picoc#L14). Descriptors select it by
`/device/terminal.dev` rather than a pointer. [`kernel_terminal()`](kernel/filesystem/terminal.picoc#L22) returns
the object, while [`foreground_process_target`](kernel/signal.picoc#L12) identifies its input owner.

PicoC lacks usable `extern` variable declarations, so the accessor exposes
the instance to other files. [`input_count`](kernel/filesystem/terminal.header#L13) distinguishes empty from full
when [`input_head`](kernel/filesystem/terminal.header#L11) and [`input_tail`](kernel/filesystem/terminal.header#L12) coincide. Both indices wrap modulo 128,
and all 128 cells are usable.

A full ring drops the incoming byte and preserves older input. The ISR
cannot block for space. There is no overflow counter or flow control.
Reads return available bytes without waiting to fill the requested count.

The UART ISR is the insertion path. It reads and acknowledges one byte,
handles signal characters, and otherwise enqueues it. It then tries to
complete the input owner's pending read.

The device paths below select this terminal behavior without host-file
requests.

## 8.3 Blocking and completing terminal reads
[\[↑ TOC\]](#contents)

A foreground read returns buffered input immediately. With an empty ring,
it records the request in the PCB and blocks until UART input arrives.

[`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134) masks UART delivery while saving the buffer and
count and joining [`input_waiters`](kernel/filesystem/terminal.header#L14). This prevents a lost wakeup. It restores
routing before dispatch. The UART ISR later copies bytes, saves the count
in [`activation.in2`](kernel/process/process.header#L23), and wakes the reader.

[`pending_terminal_read_buffer`](kernel/process/process.header#L65) points to the caller's actual destination.
The Process Payload stays allocated during the wait. Completing the read
clears pending fields and queue links and sets [`READY`](kernel/process/process.header#L13). When restored,
the original syscall returns the saved count without being reissued.

There is one input owner, so only its active read belongs in [`input_waiters`](kernel/filesystem/terminal.header#L14).
Stopping detaches it. Each stopped reader still needs its own buffer and
count for a later `fg`, even though it is absent from the queue.

Background reads stop with [`SIGTTIN`](common/signal.header#L9), as explained
in [`8.4 Foreground input ownership and terminal-generated signals`](#84-foreground-input-ownership-and-terminal-generated-signals).
[`12.5.1 Foreground processes, background processes, and job-control signals`](#1251-foreground-processes-background-processes-and-job-control-signals)
shows how the shell selects and resumes the job.

For a concrete call, consider this PicoC source in a user process:

```c
int main(void) {
    // ...
    char buffer[16];
    read(STDIN_FILENO, buffer, 16);
    // ...
}
```

`buffer` occupies the caller's stack. Its physical address goes into the
wrapper's local [`IoRequest`](common/file.header#L31), along with the requested count:

```c
int read(int file_descriptor, void *buffer, int count) {
    struct IoRequest request;
    // ...
    request.file_descriptor = file_descriptor;
    request.buffer = (char *)buffer;
    request.count = count;
    // ...
    request.transferred = 0;
    request.complete = false;
    // ...
}
```

[`invoke_syscall()`](library/unistd/process.picoc#L7) passes the request address in `IN1`. The read syscall
validates the descriptor and passes the destination buffer to
[`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134):

```c
int read_file_descriptor(struct IoRequest *request, int *caller_context) {
    // ...
    if (is_terminal_device_path(descriptor->path)) {
        request->complete = true;
        return begin_terminal_read(
            kernel_terminal(),
            request->buffer + request->transferred,
            request->count - request->transferred,
            caller_context
        );
    }
    // ...
}
```

Buffered input returns up to 16 bytes immediately. Terminal reads are not
line-oriented. With an empty ring, this code saves the destination and
count, queues the reader, and switches processes:

```c
int begin_terminal_read(
    struct Terminal *terminal,
    char *buffer,
    int count,
    int *caller_context
) {
    struct ProcessControlBlock *process = current_process();
    // ...
    process->pending_terminal_read_buffer = buffer;
    process->pending_terminal_read_count = count;
    enqueue_current_process_on_wait_queue(&(terminal->input_waiters));
    interrupt_controller_assign_device(
        INTERRUPT_DEVICE_UART,
        uart_interrupt_index,
        uart_interrupt_priority
    );
    dispatcher_switch_from_context(caller_context);
    // ...
}
```

The PCB retains the buffer rather than the [`IoRequest`](common/file.header#L31). Every ordinary
UART byte enters the ring first, then this delivery code completes a
pending read. [`9.1 Memory layout, allocation sources, and lifetimes`](#91-memory-layout-allocation-sources-and-lifetimes) lists possible buffer locations:

```c
void complete_pending_terminal_read(
    struct ProcessControlBlock *process,
    struct Terminal *terminal
) {
    int result;
    // ...
    result = copy_terminal_bytes(
        terminal,
        process->pending_terminal_read_buffer,
        process->pending_terminal_read_count
    );

    process->activation.in2 = result;
    process->pending_terminal_read_buffer = NULL;
    process->pending_terminal_read_count = 0;
    remove_from_wait_queue(process);
    process->state = PROCESS_STATE_READY;
}
```

Restoring [`activation`](kernel/process/process.header#L40) makes the syscall return that count. An empty-ring
wait normally completes with one byte because the ISR delivers one at a time.

## 8.4 Foreground input ownership and terminal-generated signals
[\[↑ TOC\]](#contents)

[`foreground_process_target`](kernel/signal.picoc#L12) combines input ownership with signal delivery.
A positive PID receives both. A negative PID owns input but receives no
terminal-generated signals. The table shows the shell's ownership changes:

| Situation | Saved [`foreground_process_target`](kernel/signal.picoc#L12) value | Ordinary input | `Ctrl+C`/`Ctrl+Z` |
| --- | ---: | --- | --- |
| Before shell registration | `0` | No process passes the ownership check, bytes are buffered, while [`terminal_input_process()`](kernel/signal.picoc#L178) uses the current PCB only as a possible pending-read completion target | Consumed without signal delivery |
| Shell prompt, including while background work runs | Negative shell process ID | Delivered to the shell | Consumed without signal delivery, so the shell is not terminated or stopped |
| Foreground child runs or resumes through `fg` | Positive child process ID | Delivered to the child | Delivered to the child as [`SIGINT`](common/signal.header#L4) or [`SIGTSTP`](common/signal.header#L8) |

`Ctrl+C` and `Ctrl+Z` arrive as bytes 3 and 26. The ISR consumes them
before ring insertion and sends [`SIGINT`](common/signal.header#L4) or [`SIGTSTP`](common/signal.header#L8) to a positive target.
Zero, a negative target, or a missing PID produces no signal. `Ctrl+D` is
handled by cat instead, as this table distinguishes:

| Input byte | Detection and action | Buffered? |
| ---: | --- | --- |
| 3 (`Ctrl+C`) | [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213) passes it to [`handle_terminal_signal_character()`](kernel/signal.picoc#L192), which sends [`SIGINT`](common/signal.header#L4) to a valid positive foreground target | No, always consumed |
| 26 (`Ctrl+Z`) | The same path sends [`SIGTSTP`](common/signal.header#L8) | No, always consumed |
| 4 (`Ctrl+D`) | Not special to the kernel, follows the ordinary byte path into the ring | Stored as ordinary value 4 when space exists, dropped if the ring is full |
| Any other byte | [`enqueue_terminal_byte()`](kernel/filesystem/terminal.picoc#L49) stores it when space exists and [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182) may deliver it | Stored unless the ring is full, an already pending read consumes available bytes immediately after insertion |

The shell calls `set_foreground_process(child_pid)` before foreground waiting and
`set_foreground_process(0)` afterward to reclaim input. The zero argument stores
the shell's negative PID in `foreground_process_target`, not zero.
[`12.5.1 Foreground processes, background processes, and job-control signals`](#1251-foreground-processes-background-processes-and-job-control-signals)
documents these calls and the corresponding `fg` sequence. While the shell owns
input, background work does not receive prompt-time terminal signals.

Reads compare the caller with the target's magnitude. A nonowner receives
[`SIGTTIN`](common/signal.header#L9) before consuming even buffered input. The shell's `fg` assigns
ownership before continuing the process. Input arrival alone neither
selects nor continues a stopped reader.

The read remains suspended. `bg` leaves a pending reader stopped because
it still lacks ownership. After `fg`, [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84)
returns buffered input or queues the reader until a byte arrives. It masks
UART around that check and insertion. The application need not retry.

`Ctrl+D` is cat's EOF convention. Terminal-mode [`edit_standard_input()`](user/cat.picoc#L81)
consumes byte 4, flushes its partial line, and exits. The kernel does not
turn it into a zero-length read. Thus `cat.bin > file.txt` ends when cat
recognizes it. Regular-file reads instead reach EOF when `read-range`
returns zero bytes.

These functions choose the input owner and translate terminal control
bytes into signals:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`set_foreground_process(pid)`](kernel/signal.picoc#L148) | `0` for PID 0 or an existing direct child, `-1` otherwise | PID 0 saves the negative current-process ID to [`foreground_process_target`](kernel/signal.picoc#L12), giving the caller input without terminal-generated signals, a child PID saves that positive process ID, giving the child input and those signals | [`current_process()`](kernel/process/process.picoc#L62), [`find_process_by_pid()`](kernel/process/process.picoc#L162) | **Library functions:** [`set_foreground_process()`](library/unistd/process.picoc#L59)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
|  |  |  |  |  |
| [`continue_process(process)`](kernel/signal.picoc#L50) | Returns no value | Resumes ordinary stops, a pending terminal read additionally requires input ownership | [`process_has_terminal_input()`](kernel/signal.picoc#L173), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) | **Kernel functions:** [`send_signal_to_process()`](kernel/signal.picoc#L75) |
| [`terminal_input_owner_id(void)`](kernel/signal.picoc#L166) | `0` for a saved 0, otherwise the positive process ID represented by the saved positive or negative value | Reads [`foreground_process_target`](kernel/signal.picoc#L12) and removes its sign to identify the input owner | None | **Kernel functions:** [`process_has_terminal_input()`](kernel/signal.picoc#L173), [`terminal_input_process()`](kernel/signal.picoc#L178) |
| [`process_has_terminal_input(process)`](kernel/signal.picoc#L173) | `true` only for the PCB whose process ID matches the represented input owner | Checks terminal-input ownership regardless of whether [`foreground_process_target`](kernel/signal.picoc#L12) contains a positive or negative process ID | [`terminal_input_owner_id()`](kernel/signal.picoc#L166) | **Kernel functions:** [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`continue_process()`](kernel/signal.picoc#L50) |
| [`terminal_input_process(void)`](kernel/signal.picoc#L178) | Represented input-owner PCB, or current PCB when 0 is saved or the represented process cannot be used | Selects the PCB whose pending read the UART handler may try to complete, the fallback does not itself grant read ownership | [`terminal_input_owner_id()`](kernel/signal.picoc#L166), [`find_process_by_pid()`](kernel/process/process.picoc#L162), [`current_process()`](kernel/process/process.picoc#L62) | **Kernel functions:** [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213) |
| [`handle_terminal_signal_character(value)`](kernel/signal.picoc#L192) | `true` when it consumed `Ctrl+C`/`Ctrl+Z`, otherwise `false` | Sends the mapped signal when [`foreground_process_target`](kernel/signal.picoc#L12) contains a positive process ID, a saved 0 or negative process ID suppresses delivery while still consuming the byte | [`find_process_by_pid()`](kernel/process/process.picoc#L162), [`send_signal_to_process()`](kernel/signal.picoc#L75) | **Kernel functions:** [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213) |

## 8.5 Virtual terminal and null-device paths
[\[↑ TOC\]](#contents)

Unlike a conventional device inode, these paths have no host-side device
type. [`device_paths_match()`](kernel/filesystem/device.picoc#L3) recognizes their exact normalized names and
selects kernel behavior. Other `/device` paths use ordinary host files:

The release tree includes marker files so listings show the device names.
Their text stores no device state. Reading those exact paths selects the
device behavior, regardless of marker contents.

| Device path | Role | Used by |
| --- | --- | --- |
| `/device/terminal.dev` | The terminal device. It is the initial path for standard input, output, and error, reads use the global terminal input ring and may block, writes go to UART output, and seeking fails. | [`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35), [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217), [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268) |
| `/device/null.dev` | The null device. Reads return EOF immediately, writes report success after discarding their bytes, and seeking fails. | [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217), [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268) |

`echo.bin test > /device/terminal.dev` writes directly to UART. It sends no
host-file write request. Redirecting to `/device/null.dev` reports the count
and advances the logical offset without transmitting data.

## 8.6 File-descriptor creation, inheritance, duplication, and cleanup
[\[↑ TOC\]](#contents)

The table shows descriptor creation, copying, replacement, and cleanup.
The later I/O table covers operations that consume these entries:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`close_file_descriptor(file_descriptor)`](kernel/filesystem/file_descriptor.picoc#L146) | `0` on close, `-1` for an invalid or already free descriptor | Frees the path and resets the selected entry | [`current_process()`](kernel/process/process.picoc#L62), [`file_descriptor_is_valid()`](kernel/filesystem/file_descriptor.picoc#L129), [`kfree()`](kernel/kmalloc.picoc#L38), [`initialize_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L24) | **Library functions:** [`close()`](library/unistd/io.picoc#L54), [`fclose()`](library/stdio/stdio.picoc#L155)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`duplicate_file_descriptor(request)`](kernel/filesystem/file_descriptor.picoc#L163) | Target descriptor, `-1` for out-of-range descriptors or a free source, panics on allocation failure | Replaces any valid target slot 0–7 with an independent copy | [`current_process()`](kernel/process/process.picoc#L62), [`file_descriptor_is_valid()`](kernel/filesystem/file_descriptor.picoc#L129), [`copy_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L82) | **Library functions:** [`dup2()`](library/unistd/io.picoc#L58)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
|  |  |  |  |  |
| [`create_file_descriptor_table(void)`](kernel/filesystem/file_descriptor.picoc#L35) | New table, panics if kernel allocation fails | Allocates table/entries and gives standard descriptors terminal paths | [`kmalloc()`](kernel/kmalloc.picoc#L23), [`initialize_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L24), [`copy_file_path()`](kernel/filesystem/file_descriptor.picoc#L6) | **Kernel functions:** [`create_process()`](kernel/process/process.picoc#L89), [`inherit_file_descriptors()`](kernel/filesystem/file_descriptor.picoc#L99) |
| [`inherit_file_descriptors(source)`](kernel/filesystem/file_descriptor.picoc#L99) | Independent table copy, panics if kernel allocation fails | Deep-copies 0–2 and [`FILE_DESCRIPTOR_FILE`](kernel/filesystem/file_descriptor.header#L13) entries in 3–4, leaves every other nonstandard entry free, including reserved slots 5–7 | [`create_file_descriptor_table()`](kernel/filesystem/file_descriptor.picoc#L35), [`copy_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L82) | **Kernel functions:** [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241) |
| [`destroy_file_descriptor_table(table)`](kernel/filesystem/file_descriptor.picoc#L118) | Returns no value | Frees paths, entry array, and table | [`kfree()`](kernel/kmalloc.picoc#L38) | **Kernel functions:** [`mark_process_ready_with_arguments()`](kernel/process/process_arguments.picoc#L241), [`remove_process()`](kernel/process/process.picoc#L209) |
| [`file_descriptor_is_valid(file_descriptor)`](kernel/filesystem/file_descriptor.picoc#L129) | `true` for descriptor 0–7, including a currently free entry, otherwise `false` | Reads fixed descriptor-number range | None | **Kernel functions:** [`close_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L146), [`duplicate_file_descriptor()`](kernel/filesystem/file_descriptor.picoc#L163), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |
| [`file_descriptor_can_read(descriptor)`](kernel/filesystem/file_descriptor.picoc#L134), [`file_descriptor_can_write(descriptor)`](kernel/filesystem/file_descriptor.picoc#L140) | Boolean access permission | Read descriptor access bits | None | **Kernel functions:** [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |
| [`is_terminal_device_path(path)`](kernel/filesystem/device.picoc#L16), [`is_null_device_path(path)`](kernel/filesystem/device.picoc#L12), [`is_device_path(path)`](kernel/filesystem/device.picoc#L20) | Boolean path classification | Recognize kernel device paths | [`device_paths_match()`](kernel/filesystem/device.picoc#L3), [`is_null_device_path()`](kernel/filesystem/device.picoc#L12), [`is_terminal_device_path()`](kernel/filesystem/device.picoc#L16) | **Kernel functions:** [`is_device_path()`](kernel/filesystem/device.picoc#L20), [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268), [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |

## 8.7 Terminal-buffer and pending-read function reference
[\[↑ TOC\]](#contents)

The following functions maintain the global input ring and the request saved
while a terminal reader is blocked or stopped.

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`initialize_terminal(void)`](kernel/filesystem/terminal.picoc#L14) | Returns no value | Resets global ring and reader queue | None | **Kernel functions:** [`main()`](kernel/kernel.picoc#L31) |
| [`kernel_terminal(void)`](kernel/filesystem/terminal.picoc#L22) | Pointer to the global terminal | No mutation | None | **Kernel functions:** [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213), [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84), [`suspend_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L75) |
| [`pop_terminal_byte(terminal)`](kernel/filesystem/terminal.picoc#L26) | Next byte, caller must ensure the ring is nonempty | Advances head and decrements count | None | **Kernel functions:** [`copy_terminal_bytes()`](kernel/filesystem/terminal.picoc#L35) |
| [`copy_terminal_bytes(terminal, buffer, count)`](kernel/filesystem/terminal.picoc#L35) | Number of bytes copied | Pops terminal bytes into a process buffer | [`pop_terminal_byte()`](kernel/filesystem/terminal.picoc#L26) | **Kernel functions:** [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182), [`resume_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L84) |
| [`enqueue_terminal_byte(terminal, value)`](kernel/filesystem/terminal.picoc#L49) | Returns no value | Inserts at tail when space exists, drops the new byte without changing unread data when full | None | **Kernel functions:** [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213) |
| [`suspend_pending_terminal_read(process)`](kernel/filesystem/terminal.picoc#L75) | Returns no value | Detaches a stopped reader from active terminal waiters while retaining its PCB request | [`kernel_terminal()`](kernel/filesystem/terminal.picoc#L22), [`remove_from_wait_queue()`](kernel/process/process.picoc#L176) | **Kernel functions:** [`stop_process()`](kernel/signal.picoc#L37) |
| [`begin_terminal_read(terminal, buffer, count, caller_context)`](kernel/filesystem/terminal.picoc#L134) | Immediate available count, or a saved result on later resumption after blocking/stopping, it does not wait to fill `count` | Reads ring or fills pending fields, queues PCB, saves activation, and dispatches | [`current_process()`](kernel/process/process.picoc#L62), [`process_has_terminal_input()`](kernel/signal.picoc#L173), [`send_signal_to_process()`](kernel/signal.picoc#L75), [`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71), [`periphery_read_register()`](kernel/periphery.picoc#L5), [`interrupt_controller_disable_device()`](kernel/interrupt_controller.picoc#L23), [`interrupt_controller_assign_device()`](kernel/interrupt_controller.picoc#L59), [`copy_terminal_bytes()`](kernel/filesystem/terminal.picoc#L35), [`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375) | **Kernel functions:** [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150) |
| [`resume_pending_terminal_read(process)`](kernel/filesystem/terminal.picoc#L84) | Returns no value | With UART delivery temporarily disabled, fills a stopped foreground reader’s buffer immediately or requeues it, sets [`ProcessControlBlock.stopped_from_state`](kernel/process/process.header#L62) for continuation | [`kernel_terminal()`](kernel/filesystem/terminal.picoc#L22), [`periphery_read_register()`](kernel/periphery.picoc#L5), [`interrupt_controller_disable_device()`](kernel/interrupt_controller.picoc#L23), [`copy_terminal_bytes()`](kernel/filesystem/terminal.picoc#L35), [`remove_from_wait_queue()`](kernel/process/process.picoc#L176), [`interrupt_controller_assign_device()`](kernel/interrupt_controller.picoc#L59), [`enqueue_terminal_reader()`](kernel/filesystem/terminal.picoc#L61) | **Kernel functions:** [`continue_process()`](kernel/signal.picoc#L50) |
| [`complete_pending_terminal_read(process, terminal)`](kernel/filesystem/terminal.picoc#L182) | Returns no value | Copies available input, writes saved [`activation.in2`](kernel/process/process.header#L23), clears pending fields, and marks the selected reader ready | [`copy_terminal_bytes()`](kernel/filesystem/terminal.picoc#L35), [`remove_from_wait_queue()`](kernel/process/process.picoc#L176) | **Kernel functions:** [`handle_uart_interrupt()`](kernel/filesystem/terminal.picoc#L213) |
| [`handle_uart_interrupt(void)`](kernel/filesystem/terminal.picoc#L213) | Returns no value | Acknowledges one byte, consumes a terminal signal character or offers ordinary input to the ring, then tries to complete the selected reader | [`terminal_input_process()`](kernel/signal.picoc#L178), [`kernel_terminal()`](kernel/filesystem/terminal.picoc#L22), [`periphery_read_register()`](kernel/periphery.picoc#L5), [`periphery_write_register()`](kernel/periphery.picoc#L11), [`handle_terminal_signal_character()`](kernel/signal.picoc#L192), [`enqueue_terminal_byte()`](kernel/filesystem/terminal.picoc#L49), [`complete_pending_terminal_read()`](kernel/filesystem/terminal.picoc#L182) | **Hardware interrupts:** UART receive via [`uart_interrupt()`](interrupt_service_routines/os_isrs.picoc#L185) |

## 8.8 Opening, reading, writing, and seeking
[\[↑ TOC\]](#contents)

[`OpenRequest.flags`](common/file.header#L28) selects access and creation behavior. The entry retains
these in [`FileDescriptor.flags`](kernel/filesystem/file_descriptor.header#L17) for later I/O:

| Flag | Value | Meaning in [`OpenRequest.flags`](common/file.header#L28) |
| --- | ---: | --- |
| [`O_RDONLY`](common/file.header#L9) | 0 | Permit reads |
| [`O_WRONLY`](common/file.header#L10) | 1 | Permit writes |
| [`O_RDWR`](common/file.header#L11) | 2 | Permit reads and writes, [`O_ACCMODE`](common/file.header#L12) = 3 extracts these two access bits |
| [`O_CREAT`](common/file.header#L13) | 64 | Allow a missing regular path to be created |
| [`O_TRUNC`](common/file.header#L14) | 512 | With writable access, create/empty the regular host file during open |
| [`O_APPEND`](common/file.header#L15) | 1024 | Resolve the current file size before every write and use it as that write's offset |

The kernel validates only the access value masked by
[`O_ACCMODE`](common/file.header#L12). It stores other flag bits unchanged, but only
[`O_CREAT`](common/file.header#L13), [`O_TRUNC`](common/file.header#L14), and
[`O_APPEND`](common/file.header#L15) have implemented behavior.

Opening normalizes the path, chooses a free descriptor, and copies the
path. Writable [`O_TRUNC`](common/file.header#L14) creates or truncates immediately. Otherwise a
missing file requires [`O_CREAT`](common/file.header#L13). The two device paths bypass host operations.

These modes produce the following host requests. New descriptors start
at offset zero. A protected write adds `literal-output` when data contains
`<ESC>`:

| Operation or mode | Descriptor flags/state | Offset handling | PicoOS functions | RETI emulator host requests and result |
| --- | --- | --- | --- | --- |
| Open existing without truncation | Any valid access mode, no [`O_TRUNC`](common/file.header#L14) | Initializes 0 | [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`file_exists()`](kernel/filesystem/filesystem.picoc#L18) | `file-size <path>` verifies that the regular file is readable by the host service, the contents are unchanged |
| Create missing file | [`O_CREAT`](common/file.header#L13) with any valid access mode | Initializes 0 | [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39) | `file-size <path>` returns failure, then `write <path>`, `write stdout`, the emulator creates/truncates the path while selecting and restoring its output destination |
| Truncate/overwrite open | Writable mode plus [`O_TRUNC`](common/file.header#L14), usually with [`O_CREAT`](common/file.header#L13) | Initializes 0 | [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39) | `write <path>`, `write stdout`, the file is created if needed and emptied immediately |
| Read | Readable descriptor | Starts at saved offset, advances by returned bytes | [`read_file_descriptor()`](kernel/filesystem/filesystem.picoc#L150), [`read_regular_file()`](kernel/filesystem/filesystem.picoc#L90) | `read-range <offset> <count> <path>` returns a count and up to 1 KiB per syscall, zero bytes is EOF |
| Ordinary overwrite/write | Writable regular descriptor without [`O_APPEND`](common/file.header#L15) | Uses saved offset, advances by requested count | [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217), [`write_uart_bytes()`](kernel/filesystem/filesystem.picoc#L195) | `write-at <offset> <path>`, optional `literal-output <count>`, data bytes, `write stdout`, existing bytes outside the written range remain |
| Append write | Writable regular descriptor with [`O_APPEND`](common/file.header#L15) | Ignores the prior offset for placement, saves file size plus requested count afterward | [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217), [`receive_file_size()`](kernel/filesystem/filesystem.picoc#L13) | `file-size <path>`, `write-at <size> <path>`, optional `literal-output <count>`, data bytes, `write stdout`, a missing file must first have been created by the open sequence |
| Seek from end | Regular non-device descriptor | File size plus requested displacement becomes the new nonnegative offset | [`seek_file_descriptor()`](kernel/filesystem/filesystem.picoc#L268), [`receive_file_size()`](kernel/filesystem/filesystem.picoc#L13) | `file-size <path>`, no data transfer |

Terminal reads can block, and null reads return EOF. Regular files use
ranged requests of at most 1 KiB and advance the offset. The wrapper repeats
until the requested count, EOF, or failure. An error after earlier chunks
returns the transferred count. Otherwise it returns `-1`. Each syscall
return permits deferred scheduling.

Terminal stdout sends bytes directly. Terminal stderr selects `write stderr`
and restores stdout afterward. Regular files use `write-at` with the path
and offset for each write, then restore stdout. The host retains one global
output destination rather than per-descriptor identities.

[`write_uart_bytes()`](kernel/filesystem/filesystem.picoc#L195) protects data containing `<ESC>` with `literal-output`.
Cat also displays nonprintable terminal output as `\xHH`, while file
redirection preserves the original bytes.

[`write_without_uart_escape_check()`](library/unistd/io.picoc#L43) skips the scan by clearing
[`IoRequest.protect_uart_control`](common/file.header#L35). Use it only for data known to contain no
escape byte. Arbitrary data requires [`write()`](library/unistd/io.picoc#L32).

Regular writes overwrite at the current offset. [`O_APPEND`](common/file.header#L15) obtains the
current file size before each write, overriding an earlier seek. Terminal
and null writes also advance their logical offsets, but both reject seeking.

Append uses separate `file-size` and `write-at` requests, so concurrent
writers to one file are unsupported. Host reads acknowledge failures, but
[`write`](library/unistd/io.picoc#L32) and `write-at` do not. A host write failure can therefore produce
an emulator warning while PicoOS still reports success. Append can fail
earlier on its acknowledged size request.

PicoOS rejects invalid descriptors, access modes, paths, counts, and device
seeks with `-1`. EOF returns `0`. The function table shows validation, offset
changes, blocking, and host requests:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`open_file_descriptor(request)`](kernel/filesystem/filesystem.picoc#L39) | Descriptor, or `-1` for invalid path/mode, no free entry, or a missing file without create/truncate | Allocates a path and changes a free entry to a file or device | [`current_process()`](kernel/process/process.picoc#L62), [`free_file_descriptor()`](kernel/filesystem/filesystem.picoc#L27), [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`copy_file_path()`](kernel/filesystem/file_descriptor.picoc#L6), [`is_device_path()`](kernel/filesystem/device.picoc#L20), [`kfree()`](kernel/kmalloc.picoc#L38), [`uart_send_host_request()`](common/uart_protocol.picoc#L82), [`file_exists()`](kernel/filesystem/filesystem.picoc#L18)<br>**Host requests:** `file-size <path>` for existence, `write <path>` then `write stdout` for create/truncate | **Library functions:** [`open()`](library/fcntl/fcntl.picoc#L5), [`fopen()`](library/stdio/stdio.picoc#L125)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`read_file_descriptor(request, caller_context)`](kernel/filesystem/filesystem.picoc#L150) | Count, `0` at EOF, or `-1` for an invalid request, unreadable descriptor, or failed host range request | Advances regular-file offset, or changes terminal queue/activation state | [`current_process()`](kernel/process/process.picoc#L62), [`file_descriptor_is_valid()`](kernel/filesystem/file_descriptor.picoc#L129), [`file_descriptor_can_read()`](kernel/filesystem/file_descriptor.picoc#L134), [`is_terminal_device_path()`](kernel/filesystem/device.picoc#L16), [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134), [`kernel_terminal()`](kernel/filesystem/terminal.picoc#L22), [`is_null_device_path()`](kernel/filesystem/device.picoc#L12), [`read_regular_file()`](kernel/filesystem/filesystem.picoc#L90)<br>**Host request:** `read-range <offset> <count> <path>` for a regular file | **Library functions:** [`read()`](library/unistd/io.picoc#L6), [`fgetc()`](library/stdio/stdio.picoc#L178)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`write_file_descriptor(request)`](kernel/filesystem/filesystem.picoc#L217) | Count, or `-1` for an invalid/unwritable descriptor or failed append-size request | Routes UART output, applies the request's [`IoRequest.protect_uart_control`](common/file.header#L35) choice, and advances the descriptor offset | [`current_process()`](kernel/process/process.picoc#L62), [`file_descriptor_is_valid()`](kernel/filesystem/file_descriptor.picoc#L129), [`file_descriptor_can_write()`](kernel/filesystem/file_descriptor.picoc#L140), [`is_null_device_path()`](kernel/filesystem/device.picoc#L12), [`is_terminal_device_path()`](kernel/filesystem/device.picoc#L16), [`uart_send_host_request()`](common/uart_protocol.picoc#L82), [`receive_file_size()`](kernel/filesystem/filesystem.picoc#L13), [`uart_send_file_write_command()`](common/uart_protocol.picoc#L102), [`write_uart_bytes()`](kernel/filesystem/filesystem.picoc#L195)<br>**Host requests:** optional `file-size <path>` for append, `write-at <offset> <path>` and `write stdout` for a regular file, `write stderr` and `write stdout` for terminal stderr, optional `literal-output <count>` | **Library functions:** [`write()`](library/unistd/io.picoc#L32), [`write_without_uart_escape_check()`](library/unistd/io.picoc#L43), [`fputc()`](library/stdio/stdio.picoc#L204), [`fputs()`](library/stdio/stdio.picoc#L229)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16)<br>**Kernel functions:** [`write_process_exception_message()`](kernel/exception.picoc#L29), [`list_processes()`](kernel/process/process.picoc#L32) |
| [`seek_file_descriptor(request)`](kernel/filesystem/filesystem.picoc#L268) | New offset, or `-1` for invalid descriptor/origin/device/negative result | Replaces a regular-file descriptor offset | [`current_process()`](kernel/process/process.picoc#L62), [`file_descriptor_is_valid()`](kernel/filesystem/file_descriptor.picoc#L129), [`is_device_path()`](kernel/filesystem/device.picoc#L20), [`receive_file_size()`](kernel/filesystem/filesystem.picoc#L13)<br>**Host request:** `file-size <path>` for [`SEEK_END`](common/file.header#L19) | **Library functions:** [`lseek()`](library/unistd/io.picoc#L66)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
|  |  |  |  |  |
| [`free_file_descriptor(table)`](kernel/filesystem/filesystem.picoc#L27) | Lowest free slot in 0–4, or `-1` when all ordinary slots are occupied | Reads descriptor kinds without changing the table, slots 5–7 are reserved and never considered | None | **Kernel functions:** [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39) |
| [`write_uart_bytes(buffer, count, protect_uart_control)`](kernel/filesystem/filesystem.picoc#L195) | Returns no value | When protection is enabled, scans for `<ESC>` and starts a counted literal-output region if found, then sends exactly `count` bytes to the selected host destination | [`uart_send_literal_output_command()`](common/uart_protocol.picoc#L112), [`uart_print_character()`](common/uart_protocol.picoc#L21)<br>**Host request:** optional `literal-output <count>` | **Kernel functions:** [`write_file_descriptor()`](kernel/filesystem/filesystem.picoc#L217) |

## 8.9 PicoOS paths, working directories, and host operations
[\[↑ TOC\]](#contents)

The emulator's launch directory becomes PicoOS `/`. Launchers select
[`binary/`](binary/) or the extracted runtime directory. [`init_guest_filesystem()`](../RETI-Emulator/source/guest_filesystem.c#L113)
retains that root. PicoOS [`chdir()`](library/unistd/working_directory.picoc#L4) changes only the caller's PCB, not the
host working directory. PicoOS `/tmp` is a path within that root.

PicoOS normalizes paths with [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92). The emulator checks
them independently relative to its retained root. POSIX-host traversal
refuses symbolic links. Linux additionally uses `RESOLVE_BENEATH`,
`RESOLVE_NO_SYMLINKS`, and `RESOLVE_NO_XDEV`. Regular-file opens reject
special files and multiple hard links. Windows rejects reparse points
including junctions.

All filesystem host requests use that sandbox. Root mutation is rejected.
Explicit emulator inputs, debug metadata, logs, and configuration remain
host-side features outside it.

[`working_directory`](kernel/process/process.header#L39) is an owned Kernel Heap string. Init gets `/`, and
children copy the loader's value at creation. A successful change allocates
a replacement before freeing the old string. Final removal frees it. [`9.1 Memory layout, allocation sources, and lifetimes`](#91-memory-layout-allocation-sources-and-lifetimes)
shows its lifetime.

Normalization prepends the working directory for relative paths, removes
repeated separators and `.`, clamps `..` at root, and enforces [`PATH_MAX`](common/file.header#L21).
These cases use the same helper:

| Requested path | Base and normalization | Example result from current directory `/a/b` |
| --- | --- | --- |
| Relative child `dir` | Append to the PCB directory | `/a/b/dir` |
| `.` or repeated separators | Ignore `.` and empty segments | `/a/b` |
| `..` | Remove one existing result segment, but never remove root | `/a`, from `/`, still `/` |
| `../dir` and longer combinations | Apply segments from left to right | `/a/dir` |
| Absolute `/dir` | Ignore the PCB directory and start at root | `/dir` |
| Empty or result at least [`PATH_MAX`](common/file.header#L21) cells | Reject before contacting the emulator | Operation returns failure |

[`chdir()`](library/unistd/working_directory.picoc#L4) sends `is-directory` for the normalized candidate. Only a zero
response replaces the PCB's directory. Failure preserves the old value.
The table distinguishes kernel-state copies from host operations:

| Kernel function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`get_working_directory(request)`](kernel/filesystem/host_filesystem.picoc#L156) | `0` on success, `-1` when the stored directory is missing or the destination capacity is too small | Copies the PCB directory into the caller buffer | [`copy_working_directory()`](kernel/filesystem/host_filesystem.picoc#L135), [`current_process()`](kernel/process/process.picoc#L62) | **Library functions:** [`getcwd()`](library/unistd/working_directory.picoc#L11)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`change_working_directory(path)`](kernel/filesystem/host_filesystem.picoc#L163) | `0` on success, `-1` for an invalid path or host failure | Validates host directory and replaces current PCB string | [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`uart_send_host_request()`](common/uart_protocol.picoc#L82), [`receive_word()`](common/uart_protocol.picoc#L7), [`set_process_working_directory()`](kernel/filesystem/host_filesystem.picoc#L128), [`current_process()`](kernel/process/process.picoc#L62)<br>**Host request:** `is-directory <path>` | **Library functions:** [`chdir()`](library/unistd/working_directory.picoc#L4)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`make_host_directory(path)`](kernel/filesystem/host_filesystem.picoc#L177) | `0` on success, `-1` on invalid path or host failure | Normalizes and sends [`mkdir`](library/sys/stat/stat.picoc#L5), no kernel table mutation | [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`uart_send_host_request()`](common/uart_protocol.picoc#L82), [`receive_word()`](common/uart_protocol.picoc#L7)<br>**Host request:** `mkdir <path>` | **Library functions:** [`mkdir()`](library/sys/stat/stat.picoc#L5)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`read_host_directory(request)`](kernel/filesystem/host_filesystem.picoc#L187) | Listing count, or `-1` for invalid request/host failure | Writes host listing into caller buffer | [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`uart_send_host_request()`](common/uart_protocol.picoc#L82), [`uart_receive_string()`](kernel/filesystem/host_filesystem.picoc#L10)<br>**Host request:** `ls <path>` | **Library functions:** [`opendir()`](library/dirent/dirent.picoc#L8)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`unlink_host_file(path)`](kernel/filesystem/host_filesystem.picoc#L208), [`remove_host_directory(path)`](kernel/filesystem/host_filesystem.picoc#L212) | `0` on success, `-1` on invalid path or host failure | Send bounded host unlink/rmdir requests | [`request_host_path_operation()`](kernel/filesystem/host_filesystem.picoc#L198)<br>**Host requests:** `unlink <path>` or `rmdir <path>` | **Library functions:** [`unlink()`](library/unistd/file_removal.picoc#L4), [`rmdir()`](library/unistd/file_removal.picoc#L8)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`move_host_path(request)`](kernel/filesystem/host_filesystem.picoc#L216) | `0` on success, `-1` on invalid path or host failure | Normalizes both paths and sends a two-path move request to the emulator | [`build_process_path()`](kernel/filesystem/host_filesystem.picoc#L92), [`uart_print_character()`](common/uart_protocol.picoc#L21), [`uart_print_string()`](common/uart_protocol.picoc#L73), [`receive_word()`](common/uart_protocol.picoc#L7)<br>**Host request:** `move <old path>\n<new path>` | **Library functions:** [`move()`](library/unistd/file_removal.picoc#L12)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
| [`touch_host_file(path)`](kernel/filesystem/host_filesystem.picoc#L234) | `0` on success, `-1` on invalid path or host failure | Sends a touch request to create a host file or update its timestamps | [`request_host_path_operation()`](kernel/filesystem/host_filesystem.picoc#L198)<br>**Host request:** `touch <path>` | **Library functions:** [`touch()`](library/unistd/file_removal.picoc#L20)<br>**System calls:** via [`handle_syscall()`](kernel/syscall.picoc#L16) |
|  |  |  |  |  |
| [`build_process_path(path, result, capacity)`](kernel/filesystem/host_filesystem.picoc#L92) | `true` on a nonempty normalized path that fits, otherwise `false` | Writes an absolute PicoOS path, relative input starts from the current PCB directory, or from `/` before the first process exists | [`append_path_segments()`](kernel/filesystem/host_filesystem.picoc#L37), [`current_process()`](kernel/process/process.picoc#L62) | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`change_working_directory()`](kernel/filesystem/host_filesystem.picoc#L163), [`load_process()`](kernel/process/process_loader.picoc#L305), [`make_host_directory()`](kernel/filesystem/host_filesystem.picoc#L177), [`move_host_path()`](kernel/filesystem/host_filesystem.picoc#L216), [`open_file_descriptor()`](kernel/filesystem/filesystem.picoc#L39), [`read_host_directory()`](kernel/filesystem/host_filesystem.picoc#L187), [`request_host_path_operation()`](kernel/filesystem/host_filesystem.picoc#L198) |
| [`system_relative_path(path)`](kernel/filesystem/host_filesystem.picoc#L121) | Pointer to the input path or the text after its leading `/` | Removes the leading `/` for program names and loading labels | None | **Kernel functions:** [`begin_process_load()`](kernel/process/process_loader.picoc#L109), [`finish_process_load()`](kernel/process/process_loader.picoc#L90), [`list_processes()`](kernel/process/process.picoc#L32), [`load_process()`](kernel/process/process_loader.picoc#L305) |
| [`set_process_working_directory(process, path)`](kernel/filesystem/host_filesystem.picoc#L128) | Returns no value | Allocates a new kernel copy, frees old string, and replaces PCB pointer | [`copy_process_path()`](kernel/process/process.picoc#L70), [`kfree()`](kernel/kmalloc.picoc#L38) | **Kernel functions:** [`change_working_directory()`](kernel/filesystem/host_filesystem.picoc#L163) |

[`getcwd()`](library/unistd/working_directory.picoc#L11) copies the PCB's stored
directory through [`get_working_directory()`](kernel/filesystem/host_filesystem.picoc#L156)
without a host request. The kernel returns a status integer, which the wrapper
converts to the caller's buffer pointer on success.

# 9. Kernel data structures: relationships, storage, and lifetimes
[\[↑ TOC\]](#contents)

This chapter gathers the storage and references explained earlier. It
distinguishes fields embedded in objects from separately allocated objects
and shows who releases each allocation.

*Containment* means a field is part of an object. *Reference* means a pointer
reaches another object. *Ownership* identifies responsibility for cleanup.
A wait queue references PCBs without owning their allocations.

## 9.1 Memory layout, allocation sources, and lifetimes
[\[↑ TOC\]](#contents)

The table locates objects in the SRAM regions from [`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy) and distinguishes
allocations from embedded fields. Pointer fields live with their containing
objects, even when their targets are elsewhere. [`9.4 Wait requests and queue storage`](#94-wait-requests-and-queue-storage) expands wait storage:

| Object | Storage and allocation | References / access | Lifetime or release |
| --- | --- | --- | --- |
| [`ProcessControlBlock`](kernel/process/process.header#L31), the PCB | One kernel-heap allocation per process via [`create_process()`](kernel/process/process.picoc#L89) | Global list through [`next`](kernel/process/process.header#L53). Current pointer and queue links also reach these same PCBs | Until [`remove_process()`](kernel/process/process.picoc#L209), possibly after a zombie period |
| [`ActivationRecord`](kernel/process/process.header#L21), child [`waiters`](kernel/process/process.header#L46), and PCB scalar/pointer fields | Embedded in the PCB, no separate allocation | [`activation`](kernel/process/process.header#L40) contains saved registers. [`waiting_queue_ptr`](kernel/process/process.header#L48) references the queue containing this PCB | PCB lifetime. Queue membership and pending-operation fields change during it |
| Complete Process Payload | One [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) payload, including program sections, heap and stack reservation | PCB [`base_address`](kernel/process/process.header#L34), [`size`](kernel/process/process.header#L35), relative [`heap_start`](kernel/process/process.header#L36) and absolute saved register addresses | Released with [`PSDFree()`](kernel/psdmalloc.picoc#L47) on PCB removal |
| [`ProcessLoad`](kernel/process/process_loader.picoc#L14) and copied path | Separate kernel-heap allocations, plus a reserved Process Payload | Loading caller's [`pending_load`](kernel/process/process.header#L68). [`ProcessLoad.base_address`](kernel/process/process_loader.picoc#L15) reaches the unfinished image | Completion transfers the Process Payload to the new PCB and frees load metadata. Cancellation also frees the Process Payload |
| PCB [`binary_path`](kernel/process/process.header#L38) and [`working_directory`](kernel/process/process.header#L39) | Separate kernel-heap strings via [`copy_process_path()`](kernel/process/process.picoc#L70) | PCB pointers | PCB removal. Changing directory replaces its string |
| [`FileDescriptorTable`](kernel/filesystem/file_descriptor.header#L22) | One kernel-heap wrapper allocation | [`ProcessControlBlock.file_descriptors`](kernel/process/process.header#L42) | Table replacement or PCB removal |
| Eight [`FileDescriptor`](kernel/filesystem/file_descriptor.header#L15) entries | **One separate contiguous kernel-heap array**. Each descriptor is an element, not its own allocation and not embedded in the wrapper | Table [`entries`](kernel/filesystem/file_descriptor.header#L23) points to the array. Descriptor number selects an element | Array lasts with table. Closing resets one element |
| Descriptor [`path`](kernel/filesystem/file_descriptor.header#L19) strings | Separate kernel-heap copies, including standard terminal paths | Each occupied descriptor references its own path | Close, duplication/replacement, or table destruction |
| [`Terminal`](kernel/filesystem/terminal.header#L9) | Global [`terminal`](kernel/filesystem/terminal.picoc#L12) in kernel `.data`. Ring array and input wait queue are embedded | [`kernel_terminal()`](kernel/filesystem/terminal.picoc#L22) returns its address | Whole kernel run |
| [`SharedMemoryEntry`](kernel/shared_memory.header#L8), name, and [`SharedMemoryAttachment`](kernel/shared_memory.header#L17) nodes | Separate kernel-heap allocations | Registry links entries. Each PCB links its attachments. Each attachment references one entry | Attachment released at process removal. Name on unlink. Entry after unlink and final attachment release |
| Shared data | Separate [`PSDMalloc()`](kernel/psdmalloc.picoc#L20) payload | Entry [`address`](kernel/shared_memory.header#L11). Mapping returns the same absolute address to each process | Entry destruction. The data is not tied to one mapper's image |
| Kernel Heap and Process and Shared Data Heap [`Heap`](common/heap.header#L11) descriptors | Two kernel `.data` globals | Each [`first_block`](common/heap.header#L12) points into its own managed region | Whole kernel run |
| Per-process [`process_heap`](library/stdlib/malloc.picoc#L6) and [`environ`](library/stdlib/env.picoc#L4) | Process `.data` globals when the libraries are linked | Descriptor reaches process-heap blocks. Environment pointer reaches the process's environment array | Image lifetime. Environment contents can be replaced |
| [`BlockHeader`](common/heap.header#L5) | Inside **each managed heap**, immediately before its payload. It is not separately allocated metadata | Heap descriptor → first header → [`next`](common/heap.header#L8) header | Split/merged by allocator. Outer heap headers and inner User Process Heap headers belong to different lists |
| Userspace library objects, buffers, and caller-created mutexes/queues | Process heap via [`malloc()`](library/stdlib/malloc.picoc#L35), process `.data`, process stack, or mapped shared data according to the caller | Examples include [`DirectoryStream`](library/dirent/dirent.header#L14), environment copies, and [`mutex`](library/mutex/mutex.header#L6) | Caller/library controls lifetime. Any kernel-retained pointer must remain valid until completion |
| Syscall requests and result cells | Library wrappers use user-process stack locals. Kernel internal calls also use kernel-stack requests, e.g. [`init_request`](kernel/kernel.picoc#L33) and [`IoRequest`](kernel/process/process.picoc#L34) | Syscall pointer argument or direct function argument | Call lifetime. Retained status/buffer addresses can outlast one syscall entry while the user call stays suspended |
| Pending terminal-read state and destination | Buffer pointer/count are PCB fields. Destination is caller storage, potentially stack, `.data`, heap, or shared data | [`pending_terminal_read_buffer`](kernel/process/process.header#L65) and [`pending_terminal_read_count`](kernel/process/process.header#L66) | Fields cleared at completion/cancellation. Caller buffer stays alive through the blocked call |
| Kernel local variables and scratch buffers | Live kernel stack frames in normal kernel calls, e.g. [`absolute_path`](kernel/process/process_loader.picoc#L114) | Parameters and local pointers | Until return or context-switch abandonment of that kernel call chain |
| Interrupt saved frames and handler locals | The **interrupted stack**: process stack for a user interruption, kernel stack for a kernel interruption | [`caller_context`](kernel/dispatcher.picoc#L71). Saved PC remains at [`activation.sp`](kernel/process/process.header#L25) + 1 after dispatch | Until restoration. UART/DMA handlers retain the interrupted `SP`, so their kernel C locals can also occupy a user-process stack |

Syscall and userspace-timer entry switch to the kernel stack. UART and DMA
borrow the interrupted stack, so kernel code's locals can live there too.
Kernel metadata uses [`kmalloc()`](kernel/kmalloc.picoc#L23), while user synchronization objects can
be referenced directly.

## 9.2 Containment and reference relationships
[\[↑ TOC\]](#contents)

Nested boxes show containment, and arrows identify pointer fields. The
dotted terminal edge means path-based selection, rather than a pointer:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    subgraph PCB["ProcessControlBlock / PCB: one Kernel Heap allocation"]
        P["PCB fields"]
        A["activation: embedded ActivationRecord"]
        W["waiters: embedded wait_queue<br/>other processes waiting for this process"]
    end
    W -->|head| WA["first waiting PCB"]
    WA -->|wait_next| WZ["last waiting PCB"]
    W -->|tail| WZ
    WA -->|waiting_queue_ptr| W
    P -->|next| PN["next PCB in global process list"]
    P -->|base_address| IMG["Process Payload: PSDMalloc<br/>User Process Image / User Process Heap / User Process Stack"]
    A -->|"sp and baf"| ST["saved process stack frame and return PC<br/>inside that Process Payload"]
    P -->|file_descriptors| FDT["FileDescriptorTable<br/>separate kmalloc allocation"]
    subgraph ARRAY["one separate kmalloc allocation: FileDescriptor entries 0–7"]
        FD["entries[fd]<br/>kind / flags / offset / path"]
    end
    FDT -->|entries| FD
    FD -->|path| PATH["separate kmalloc path string"]
    subgraph TERM["global Terminal object: kernel .data"]
        TROOT["Terminal fields"]
        INPUT["input_buffer[128]<br/>embedded ring storage"]
        INPUTQ["input_waiters<br/>embedded wait_queue"]
    end
    TROOT -->|contains| INPUT
    TROOT -->|contains| INPUTQ
    INPUTQ -->|head / tail| READER["waiting reader PCB<br/>kernel heap"]
    READER -->|waiting_queue_ptr| INPUTQ
    PATH -. "terminal-device path selects" .-> TROOT
    P -->|"binary_path / working_directory"| STR["separate kmalloc strings"]
    P -->|pending_load| LOAD["ProcessLoad: kmalloc<br/>path copy and unfinished PSDMalloc Process Payload"]
    P -->|shared_memory_attachments| ATT["SharedMemoryAttachment: kmalloc"]
    ATT -->|next| ATT2["next attachment or NULL"]
    ATT -->|entry| SE["SharedMemoryEntry: kmalloc"]
    SE -->|next| SE2["next registry entry or NULL"]
    SE -->|name| NAME["kmalloc name or NULL after unlink"]
    SE -->|address| SH["shared data: PSDMalloc"]
    P -->|waiting_queue_ptr| Q["queue currently containing this PCB<br/>may belong to another PCB, terminal, DMA, or userspace"]
    P -->|wait_next| WP["next PCB in that wait queue or NULL"]
    P -->|waiting_status_ptr| STATUS["parent's stack-local waitpid status<br/>inside its Process Payload, or NULL"]
    P -->|pending_terminal_read_buffer| BUF["pending read destination<br/>caller stack, .data, heap, or shared data"]
```

Call-local requests remain in the calling function's stack frame. In
[`waitpid()`](library/sys/wait/wait.picoc#L14), the
[`WaitPidRequest`](common/syscall.header#L61) and the separate
[`status`](library/sys/wait/wait.picoc#L15) integer both live on the parent's
User Process Stack. The request occupies two memory cells, one for the child
PID and one for the result address. The separate integer occupies a third
cell. The diagram shows how the request's
[`status`](common/syscall.header#L63) pointer and the parent PCB's
[`waiting_status_ptr`](kernel/process/process.header#L44) reference the same
integer while the parent waits for its child:

![User stack memory cells show the two-cell WaitPidRequest and separate integer status cell, with request.status and PCB 1 waiting_status_ptr both pointing to the integer](documentation/images/process-waitpid-references.svg)

[`invoke_waitpid_syscall()`](library/sys/wait/wait.picoc#L4) passes `&request`
through `IN1`, leaving the request on the User Process Stack. When the parent
must wait, [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348)
copies the request's [`status`](common/syscall.header#L63) pointer into
[`waiting_status_ptr`](kernel/process/process.header#L44).
[`wake_parent_waiting_for_process()`](kernel/process/process.picoc#L261)
writes the result through that pointer and clears the PCB field. The stack
frame stays alive until [`waitpid()`](library/sys/wait/wait.picoc#L14) returns.

Kernel functions can also construct requests in their own frames, such as
[`init_request`](kernel/kernel.picoc#L33) and the [`IoRequest`](common/file.header#L31)
in [`list_processes()`](kernel/process/process.picoc#L32). Neither case needs a Kernel Heap allocation.

`next` belongs to the process list, and [`wait_next`](kernel/process/process.header#L51) to a wait queue.
A PCB's [`waiters`](kernel/process/process.header#L46) contains processes waiting for it. Its [`waiting_queue_ptr`](kernel/process/process.header#L48)
identifies the queue containing that PCB. Both relationships can coexist.

Descriptor paths select devices, and [`parent_pid`](kernel/process/process.header#L57) stores an ID. Neither is
a PCB or terminal pointer. Cleanup frees owned descriptor paths but only
decrements shared-entry references, allowing other mappings to survive.

## 9.3 Kernel global variables and process-list roots
[\[↑ TOC\]](#contents)

These globals have static storage in kernel `.data`, except for the handler
pointer array in `.ivt`. Macros and peripheral registers are not additional
global allocations:

| Global | Type | Stored value / referenced structure and role |
| --- | --- | --- |
| [`process_list_head`](kernel/process/process.picoc#L16) | `struct ProcessControlBlock *` | First PCB, or `NULL`. It is the starting point for process lookup and scheduling |
| [`process_list_tail`](kernel/process/process.picoc#L17) | `struct ProcessControlBlock *` | Final PCB, or `NULL`. Appending sets the old tail's [`next`](kernel/process/process.header#L53) then updates this pointer |
| [`active_process`](kernel/process/process.picoc#L18) | `struct ProcessControlBlock *` | Selected/current PCB returned by [`current_process()`](kernel/process/process.picoc#L62). It is also the scheduler's position in the list. Initially `NULL`. Removal may replace it with the preceding PCB, so it does not always designate a [`RUNNING`](kernel/process/process.header#L14) process |
| [`next_process_id`](kernel/process/process.picoc#L19) | `int` | Next ID assigned by [`create_process()`](kernel/process/process.picoc#L89), initially 1. It is not a process count or PCB pointer |
| [`kernel_heap`](kernel/kmalloc.picoc#L7) | [`struct Heap`](common/heap.header#L11) | Embedded descriptor whose first-block pointer reaches the kernel heap |
| [`process_shared_data_heap`](kernel/psdmalloc.picoc#L7) | [`struct Heap`](common/heap.header#L11) | Descriptor for the larger Process and Shared Data Heap allocator. It is not a user's local heap |
| [`terminal`](kernel/filesystem/terminal.picoc#L12) | `struct Terminal` | Contains the 128-cell ring, three ring indices/count fields, and embedded input wait queue. It is shared by all terminal descriptors |
| [`shared_memory_list_head`](kernel/shared_memory.picoc#L6) | `struct SharedMemoryEntry *` | First named entry or first unlinked entry that is still used. The registry follows [`SharedMemoryEntry.next`](kernel/shared_memory.header#L14) |
| [`next_shared_memory_id`](kernel/shared_memory.picoc#L7) | `int` | Next registry ID, initially 1. It is independent of process IDs |
| [`dma_waiters`](kernel/dma.picoc#L6) | [`struct wait_queue`](common/wait_queue.header#L5) | Standalone queue whose endpoints reference PCBs waiting for UART DMA completion |
| [`dma_initialized`](kernel/dma.picoc#L7) | `bool` | Initially false. It prevents reinitializing the DMA queue after setup |
| [`reschedule_requested`](kernel/dispatcher.picoc#L8) | `bool` | Deferred rescheduling flag for a timer interrupting kernel work or a terminating signal targeting the running process. It is set by [`dispatcher_request_reschedule()`](kernel/dispatcher.picoc#L10) and cleared on process selection |
| [`foreground_process_target`](kernel/signal.picoc#L12) | `int` | Signed process ID for terminal control: 0 means no registered owner, positive ID permits terminal signal delivery, negative ID retains input ownership while suppressing that delivery. It is not a PCB pointer |
| [`interrupt_device_isrs`](kernel/interrupt_controller.picoc#L3) | `int[INTERRUPT_DEVICE_COUNT]` (3 entries) | Timer/DMA/UART service-routine indices `{1, 4, 2}` copied into periphery configuration. They are not function pointers |
| [`interrupt_device_priorities`](kernel/interrupt_controller.picoc#L9) | `int[INTERRUPT_DEVICE_COUNT]` (3 entries) | Timer/DMA/UART priorities `{1, 1, 2}` used during controller initialization |
| [`loading_bar_enabled`](config/config.header#L5) | `bool` | Initially true. This kernel-image copy controls the init transfer. The separately linked bootloader and init images each have their own copy, as explained in [`4.2.2.2.2 Loading-bar environment variable`](#42222-loading-bar-environment-variable) |
| [`interrupt_vector_table`](interrupt_service_routines/os_isrs.picoc#L23) | `void (*[OS_INTERRUPT_VECTOR_COUNT])(void)` (5 entries) | `.ivt` array of syscall, timer, UART, exception and DMA handler addresses. The CPU reads these to enter kernel `.text` |

## 9.4 Wait requests and queue storage
[\[↑ TOC\]](#contents)

[`wait_queue`](common/wait_queue.header#L5) stores two PCB pointers. [`WaitPidRequest`](common/syscall.header#L61) supplies a child
PID and result address. Direct sleeping needs no request structure, and
neither primitive allocates a waiter node.

The table follows each call to its queue and request storage. A queue must
outlive every linked waiter, including when it is stack-local:

| Call path | Request and queue storage | Retained references and reason |
| --- | --- | --- |
| [`sleep(wq)`](library/unistd/blocking.picoc#L9) → [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390) | Passes the existing queue address directly in `IN1`. The wrapper creates no request struct and no queue. The caller can supply a queue/mutex in a process stack frame, process `.data`, process heap, or shared data | The PCB retains [`waiting_queue_ptr`](kernel/process/process.header#L48). Queue endpoints and [`wait_next`](kernel/process/process.header#L51) link the PCB until wake/removal |
| [`mutex_lock()`](library/mutex/mutex.picoc#L18) → [`sleep()`](library/unistd/blocking.picoc#L9) | Uses embedded [`mutex.waiters`](library/mutex/mutex.header#L8). The [local-mutex test](test/mutex_lock_unlock/mutex_lock_unlock.picoc#L7) puts the mutex in a user stack frame. The [shared-mutex test](test/shared_memory_mutex/shared.header#L5) embeds it in shared data | The kernel writes PCB pointers into that caller-owned queue. PicoOS has no address isolation |
| [`waitpid()`](library/sys/wait/wait.picoc#L14) → [`wait_for_process_by_pid()`](kernel/process/process.picoc#L348) → [`sleep_on_wait_queue()`](kernel/process/process.picoc#L390), when blocking | Both [`request`](library/sys/wait/wait.picoc#L16) and [`status`](library/sys/wait/wait.picoc#L15) are in the **parent's user-process stack frame**. The queue is the **child's embedded [`ProcessControlBlock.waiters`](kernel/process/process.header#L46)**, already within its kernel-heap PCB | [`WaitPidRequest.status`](common/syscall.header#L63) is copied into the parent's [`waiting_status_ptr`](kernel/process/process.header#L44). The suspended frame stays alive for the later status write. The kernel does not retain the request pointer or call [`kmalloc`](kernel/kmalloc.picoc#L23) here |
| [`begin_terminal_read()`](kernel/filesystem/terminal.picoc#L134) | Uses embedded [`terminal.input_waiters`](kernel/filesystem/terminal.header#L14) in kernel `.data` | PCB retains caller buffer/count for delivery after an input interrupt |
| [`start_dma_uart_receive()`](kernel/dma.picoc#L18) | Uses standalone [`dma_waiters`](kernel/dma.picoc#L6) in kernel `.data` | Intrusive PCB links wait for completion. The persistent [`ProcessLoad`](kernel/process/process_loader.picoc#L14) record separately preserves the partial executable state |

[`waitpid()`](library/sys/wait/wait.picoc#L14) uses the existing child PCB's embedded queue. Immediate error,
stopped-child, and zombie-child cases write the status without queueing.
[`7.1 Wait queues and PCB links`](#71-wait-queues-and-pcb-links) explains mutation and wakeup.

# 10. Userspace libraries
[\[↑ TOC\]](#contents)

Libraries give applications reusable process, memory, and I/O operations.
Some run entirely in the user image. Others prepare syscalls for the kernel.
This chapter follows one call, then lists the available interfaces.

Syscalls avoid hardcoded kernel addresses, subject to the ABI requirements
in [`2.4 System-call interface and execution`](#24-system-call-interface-and-execution). Standard library interfaces can make source portable across systems,
without making compiled executables portable. PicoOS implements only the
parameters and behavior documented here.

## 10.1 From a library call to the kernel: waitpid
[\[↑ TOC\]](#contents)

[`waitpid(pid)`](library/sys/wait/wait.picoc#L14) waits for one exact child and
returns its exit or stopped status, or `-1` for an invalid PID or non-child.
This example connects the application's header include, linked library,
syscall entry, kernel wait, and return to the caller. It also shows which files make up the library and why the
kernel can deliver a result into a suspended library call.

### 10.1.1 Header, implementation, and linking
[\[↑ TOC\]](#contents)

A header declares how to call a function. Its implementation supplies the
executable code. PicoOS uses `.header` and `.picoc` in place of `.h` and `.c`.
The [`sys/wait`](library/sys/wait/) library separates its public declarations,
implementation, and compilation unit. Shared headers supply the types and
constants that the library and kernel must agree on.

The table connects each source file and generated artifact to its role in
calling [`waitpid()`](library/sys/wait/wait.picoc#L14):

| File | Role in the wait library |
| --- | --- |
| [`wait.header`](library/sys/wait/wait.header) | Public declarations of [`waitpid(pid)`](library/sys/wait/wait.picoc#L14) and [`WIFSTOPPED(status)`](library/sys/wait/wait.picoc#L25). Includes the shared type and signal headers. `#pragma once` prevents repeated declarations through multiple includes |
| [`wait.picoc`](library/sys/wait/wait.picoc) | Includes the public header and syscall definitions. Implements both public functions and [`invoke_waitpid_syscall(number, argument)`](library/sys/wait/wait.picoc#L4), the assembly helper that enters the kernel |
| [`libwait.picoc`](library/sys/wait/libwait.picoc) | Compilation unit containing only `#include "wait.picoc"`. Compiling this file collects the implementation and its included headers into one reusable library artifact |
| [`common/stddef.header`](common/stddef.header) | Defines [`bool`](common/stddef.header#L3), [`true`](common/stddef.header#L9), and [`false`](common/stddef.header#L8), used by the stopped-status test and kernel completion result |
| [`common/signal.header`](common/signal.header) | Defines the stopped-status constants inspected by [`WIFSTOPPED()`](library/sys/wait/wait.picoc#L25). They match statuses delivered from the child's [`stop_signal`](kernel/process/process.header#L61) |
| [`common/syscall.header`](common/syscall.header) | Defines [`SYSCALL_WAITPID`](common/syscall.header#L13) and [`WaitPidRequest`](common/syscall.header#L61). The shared layout lets the kernel read the child PID and result address prepared by the library |
| [`libwait.reti_blocks`](library/sys/wait/libwait.reti_blocks) | Generated RETI code blocks for the library functions, supplied to the linker |
| [`libwait.st`](library/sys/wait/libwait.st) | Generated symbol table containing function signatures and type information. The compiler reads it alongside the code blocks when linking calls from an application |

The complete public header, [`library/sys/wait/wait.header`](library/sys/wait/wait.header),
establishes the caller's view of the library:

```c
#pragma once

#include "../../../common/stddef.header"
#include "../../../common/signal.header"

int waitpid(int pid);
bool WIFSTOPPED(int status);
```

For example, [`user/shell.picoc`](user/shell.picoc) includes this header and calls
[`waitpid()`](library/sys/wait/wait.picoc#L14) for its foreground child. The file
outline below shows the include, the result variable, and
[`run_process()`](user/shell.picoc#L1034), which stores the returned status in
[`last_command_exit_status`](user/shell.picoc#L29). Unrelated declarations,
redirection setup, and status reporting are omitted with `// ...`:

```c
#include "../library/sys/wait/wait.header"
// ...

int last_command_exit_status = 0;
// ...

bool run_process(
    int pid,
    char *arguments,
    bool background,
    char *stdin_path,
    char *stdout_path,
    bool append_stdout,
    char *stderr_path,
    bool append_stderr
) {
    char expanded_arguments[SHELL_COMMAND_BUFFER_CAPACITY];
    // ...
    bool started;

    // ...
    started = run(pid, expand_variables(
                           arguments,
                           expanded_arguments,
                           SHELL_COMMAND_BUFFER_CAPACITY),
                  NULL);
    // ...

    if (!started) {
        // ...
    } else if (background) {
        last_background_process_id = pid;
    } else {
        set_foreground_process(pid);
        last_command_exit_status = waitpid(pid);
        set_foreground_process(0);
        // ...
    }
    return started;
}
// ...
```

Including the header gives the compiler the signature. The implementation
is supplied during linking.

The library compilation unit, [`library/sys/wait/libwait.picoc`](library/sys/wait/libwait.picoc),
collects the implementation through a single include. Its complete contents are:

```c
#include "wait.picoc"
```

Compile it from the repository root to produce the two reusable artifacts:

```console
$ picoc_compiler -c -O1 library/sys/wait/libwait.picoc
```

Supply [`libwait.reti_blocks`](library/sys/wait/libwait.reti_blocks) as a linker
input alongside the application's compiled code and other required libraries.
Keep [`libwait.st`](library/sys/wait/libwait.st) beside it. The linker resolves
calls to [`waitpid()`](library/sys/wait/wait.picoc#L14) to code inside the user
image. The kernel is built separately and is reached at runtime through
`INT 0`. This library has its own syscall helper, so it does not need to link
[`unistd`](library/unistd/) to enter the kernel.

[`1.1.2 Separate compilation, reusable artifacts, and linking`](#112-separate-compilation-reusable-artifacts-and-linking)
shows complete linking commands. An executable also needs the startup code
explained in
[`1.1.5 Selecting a startup function with -C / --startup-source`](#115-selecting-a-startup-function-with--c----startup-source).

### 10.1.2 Packing arguments and executing the syscall
[\[↑ TOC\]](#contents)

The syscall interface passes one value or address in `IN1`. To supply both a
child PID and a result destination, [`waitpid()`](library/sys/wait/wait.picoc#L14)
uses [`WaitPidRequest`](common/syscall.header#L61), defined in the shared syscall
header:

```c
struct WaitPidRequest {
    int pid;
    int *status;
};
```

The complete [`wait.picoc`](library/sys/wait/wait.picoc) implementation below
shows the ordinary library call, both stack-local objects, and the assembly
that enters the kernel. It also includes
[`WIFSTOPPED()`](library/sys/wait/wait.picoc#L25), which inspects the returned
integer entirely in userspace:

```c
#include "wait.header"
#include "../../../common/syscall.header"

int invoke_waitpid_syscall(int number, int argument) {
    int result;

    asm("LOADIN BAF ACC 3");
    asm("LOADIN BAF IN1 4");
    asm("INT 0");
    asm("STOREIN BAF IN2 0");
    return result;
}

int waitpid(int pid) {
    int status = 0;
    struct WaitPidRequest request;

    request.pid = pid;
    request.status = &status;
    while (!invoke_waitpid_syscall(SYSCALL_WAITPID, (int)&request)) {
    }
    return status;
}

bool WIFSTOPPED(int status) {
    return status == SIGNAL_STOP_STATUS ||
           status == SIGNAL_STOPPED_STATUS ||
           status == SIGNAL_TERMINAL_INPUT_STATUS;
}
```

[`request.pid`](common/syscall.header#L62) selects the exact child, and
[`request.status`](common/syscall.header#L63) points to the separate local
[`status`](library/sys/wait/wait.picoc#L15) integer. Both the
[`request`](library/sys/wait/wait.picoc#L16) and the result remain on the
parent's userspace stack for the duration of the call. Neither requires heap
allocation. The helper receives the request's absolute address as its
second argument.

The register table connects the helper's instructions to the request and
kernel result. The `BAF` offsets follow
[`1.1.3 System V ABI stack frames and call cleanup`](#113-system-v-abi-stack-frames-and-call-cleanup):

| Register | Prepared or read by the helper | Meaning for this call |
| --- | --- | --- |
| `ACC` | `LOADIN BAF ACC 3` reads the first argument | [`SYSCALL_WAITPID`](common/syscall.header#L13) selects the wait branch in [`handle_syscall()`](kernel/syscall.picoc#L16) |
| `IN1` | `LOADIN BAF IN1 4` reads the second argument | Address of the stack-local [`WaitPidRequest`](common/syscall.header#L61), containing the child PID and status destination |
| `IN2` | After `INT 0`, `STOREIN BAF IN2 0` saves it in the helper's local [`result`](library/sys/wait/wait.picoc#L5) | Completion indication returned by the syscall. The child status is written separately through [`WaitPidRequest.status`](common/syscall.header#L63) |

The wrapper retries if the helper returns zero, then returns its updated
local [`status`](library/sys/wait/wait.picoc#L15). A normal blocking wait
resumes with `IN2 = 1`, so it does not poll while the child runs. PicoOS's
public API takes only the child PID and returns the status directly. It has
no options argument or caller-supplied status pointer.

### 10.1.3 Interrupt entry, waiting, and return
[\[↑ TOC\]](#contents)

`INT 0` enters [`syscall_interrupt()`](interrupt_service_routines/os_isrs.picoc#L94),
which saves the userspace registers and switches to the kernel's code, data,
and stack context. It calls
[`handle_syscall(syscall_number, argument, caller_context)`](kernel/syscall.picoc#L16)
with the saved selector, request address, and register-frame address. The
[`SYSCALL_WAITPID`](common/syscall.header#L13) branch casts the argument back to
[`WaitPidRequest *`](common/syscall.header#L61) and calls
[`wait_for_process_by_pid()`](kernel/process/process.picoc#L348).

The kernel reads [`WaitPidRequest.pid`](common/syscall.header#L62), finds the
child PCB, and checks its [`parent_pid`](kernel/process/process.header#L57)
against the caller's [`pid`](kernel/process/process.header#L32).

The diagram contrasts immediate completion with waiting for a child event.
Both paths resume after `INT 0` in the same userspace helper. During a wait,
the parent's [`activation`](kernel/process/process.header#L40) preserves the
registers to restore, and [`waiting_status_ptr`](kernel/process/process.header#L44)
retains the result address. The lower boxes show the parent's
[`ProcessControlBlock`](kernel/process/process.header#L31) fields:

![Immediate completion restores the caller after writing status. Waiting saves the parent's activation and sets its state to BLOCKED. A child event writes status through waiting_status_ptr and sets the parent's state to READY, then dispatch restores activation. Both paths use RTI and waitpid returns status.](documentation/images/waitpid-return-paths.svg)

For an invalid PID or non-child, the kernel writes `-1` through
[`WaitPidRequest.status`](common/syscall.header#L63). If the child's
[`state`](kernel/process/process.header#L33) is
[`ZOMBIE`](kernel/process/process.header#L17), it copies
[`exit_status`](kernel/process/process.header#L60) and calls
[`remove_process()`](kernel/process/process.picoc#L209). If the child is
[`STOPPED`](kernel/process/process.header#L16), it writes `128 +`
[`stop_signal`](kernel/process/process.header#L61) and leaves the child
allocated. Each immediate path returns [`true`](common/stddef.header#L9) to
the syscall handler, which returns the completion indication in `IN2`.
[`syscall_interrupt_return()`](interrupt_service_routines/os_isrs.picoc#L133)
saves that result before checking for pending rescheduling. The caller
returns through `RTI`, either after
[`syscall_interrupt_restore()`](interrupt_service_routines/os_isrs.picoc#L148)
restores its registers or after the dispatcher selects it again.

Otherwise the kernel copies [`WaitPidRequest.status`](common/syscall.header#L63)
into the parent's [`waiting_status_ptr`](kernel/process/process.header#L44).
It retains this result pointer rather than the request address.
[`sleep_on_wait_queue()`](kernel/process/process.picoc#L390) links the parent to
the child's [`waiters`](kernel/process/process.header#L46) and changes the
parent's [`state`](kernel/process/process.header#L33) to
[`BLOCKED`](kernel/process/process.header#L15).
[`dispatcher_switch_from_context()`](kernel/dispatcher.picoc#L71) saves the
caller's registers in its [`activation`](kernel/process/process.header#L40)
and dispatches another process. Before calling the handler, the interrupt
service routine presets the saved `IN2` result to `1`. This becomes the
parent's [`activation.in2`](kernel/process/process.header#L23) when it blocks.

Child termination or stopping later writes the status into the parent's
suspended stack frame and wakes it. When the dispatcher selects the parent
again, [`dispatcher_jump_to_process()`](kernel/dispatcher.picoc#L21) restores
its activation and executes `RTI`. Execution resumes immediately after
`INT 0` in [`invoke_waitpid_syscall()`](library/sys/wait/wait.picoc#L4), with
`IN2 = 1`. The helper returns that completion indication, and
[`waitpid()`](library/sys/wait/wait.picoc#L14) returns the integer written by
the kernel. The blocked call resumes through its saved userspace context.
It does not resume the kernel wait function to reach its final
`return false`.

[`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid) explains
queue cleanup and the case where the waiting parent itself is stopped.
[`2.4.2 System-call entry, execution, and return to userspace`](#242-system-call-entry-execution-and-return-to-userspace)
details register saving and both syscall return paths.

## 10.2 Library overview and dependencies
[\[↑ TOC\]](#contents)

PicoOS provides **15 libraries** under [`library/`](library/). The table identifies their
sources and link dependencies. [`common/`](common/) supplies shared code and
declarations. A dependency adds code to the user image:

| Library | Main facilities | Library or common code used |
| --- | --- | --- |
| [`unistd`](library/unistd/) | Processes, descriptors, paths, and wait queues | [`stdlib`](library/stdlib/) for environment access |
| [`fcntl`](library/fcntl/) | Opening and creating files | [`unistd`](library/unistd/) syscall helper |
| [`sys/wait`](library/sys/wait/) | Child waiting and stopped-status inspection | Own syscall helper |
| [`mutex`](library/mutex/) | Atomic lock with a wait queue | [`unistd`](library/unistd/) queue functions |
| [`sys/mman`](library/sys/mman/) | Named shared memory | Own syscall helper |
| [`dirent`](library/dirent/) | Directory streams | [`unistd`](library/unistd/) and [`stdlib`](library/stdlib/) |
| [`stdlib`](library/stdlib/) | Process heap, environment, conversion, and exit | [`common/heap.picoc`](common/heap.picoc) included in its compilation unit |
| [`string`](library/string/) | String copying, comparison, and length | [`common/string.picoc`](common/string.picoc) included in its compilation unit |
| [`stdio`](library/stdio/) | Streams, formatting, and scanning | [`common/decimal.picoc`](common/decimal.picoc) included in its compilation unit and its own syscall helper |
| [`start`](library/start/) | Program entry and runtime initialization | [`stdlib`](library/stdlib/) |
| [`schedule`](library/schedule/) | Voluntary scheduling | Direct inline syscall |
| [`signal`](library/signal/) | Sending signals | Own syscall helper |
| [`sys/prctl`](library/sys/prctl/) | Parent-death signal setup | Own syscall helper |
| [`sys/reboot`](library/sys/reboot/) | Restart and power-off | [`unistd`](library/unistd/) syscall helper |
| [`sys/stat`](library/sys/stat/) | Directory creation | [`unistd`](library/unistd/) syscall helper |

The function tables list syscalls and conditional UART host requests.
`file-size <path>`, for example, abbreviates the complete
`<ESC>file-size <path><ESC>/` frame. These are host protocol operations,
defined in [`1.2.3 UART host-service protocol`](#123-uart-host-service-protocol).

Output routing depends on the descriptor and flags. Terminal stdout and
null output need no destination request. Redirected output can write files
even when the function opens none itself. [`8.8 Opening, reading, writing, and seeking`](#88-opening-reading-writing-and-seeking) explains this routing.

### 10.2.1 unistd: processes, descriptors, paths, and wait queues
[\[↑ TOC\]](#contents)

[`unistd`](library/unistd/) provides process, descriptor, path, and wait-queue operations.
The following tables follow its implementation files.

#### 10.2.1.1 Process operations in `process.picoc`
[\[↑ TOC\]](#contents)

[`process.picoc`](library/unistd/process.picoc) contains the syscall bridge and operations for loading,
starting, terminating, and querying processes:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`invoke_syscall(number, argument)`](library/unistd/process.picoc#L7) | Result returned by the selected syscall in `IN2`. Internal bridge used by [`unistd`](library/unistd/) and libraries that depend on it | Forwards the supplied selector and argument. The wrapper rows in this section identify each concrete syscall and host request |
| [`load(path)`](library/unistd/process.picoc#L17) | PID, or 0 on failure. Repeats bounded transfers and creates a process whose [`ProcessControlBlock.state`](kernel/process/process.header#L33) is [`PROCESS_STATE_NEW`](kernel/process/process.header#L12) | [`SYSCALL_LOAD_PROCESS`](common/syscall.header#L8) with [`LoadProcessRequest`](common/syscall.header#L50)<br>**Host Requests:** `file-size <path>`, then one or more `read-range <offset> <count> <path>` requests |
| [`run(pid, arguments, environment)`](library/unistd/process.picoc#L31) | Whether the process was initialized and its [`ProcessControlBlock.state`](kernel/process/process.header#L33) was changed from [`PROCESS_STATE_NEW`](kernel/process/process.header#L12) to [`PROCESS_STATE_READY`](kernel/process/process.header#L13). A `NULL` environment selects the current [`environ`](library/stdlib/env.picoc#L4) | [`SYSCALL_RUN_PROCESS_WITH_ARGUMENTS`](common/syscall.header#L9) with [`RunProcessRequest`](common/syscall.header#L55) |
| [`unload(pid)`](library/unistd/process.picoc#L47) | Whether a non-current target was terminated and removed | [`SYSCALL_UNLOAD_PROCESS`](common/syscall.header#L11) with the PID directly |
| [`list_processes(void)`](library/unistd/process.picoc#L51) | Prints every known PID and binary path | [`SYSCALL_LIST_PROCESSES`](common/syscall.header#L10) with no request structure<br>**Host Requests through descriptor 1:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>No `literal-output` request |
| [`getpid(void)`](library/unistd/process.picoc#L55) | PID stored in the current [`ProcessControlBlock`](kernel/process/process.header#L31) | [`SYSCALL_GETPID`](common/syscall.header#L14) with no request structure |
| [`set_foreground_process(pid)`](library/unistd/process.picoc#L59) | 0 or `-1`. A direct child PID stores that positive value in [`foreground_process_target`](kernel/signal.picoc#L12) for input and terminal-generated signals. PID 0 stores the caller's negative PID for input without those signals | [`SYSCALL_SET_FOREGROUND_PROCESS`](common/syscall.header#L15) with the PID directly |

[`invoke_syscall(number, argument)`](library/unistd/process.picoc#L7) passes the selected operation in `ACC`
and its argument in `IN1`. Its effects depend on that selector, just like
the wait helper in [`10.1.2 Packing arguments and executing the syscall`](#1012-packing-arguments-and-executing-the-syscall).

#### 10.2.1.2 Descriptor operations in `io.picoc`
[\[↑ TOC\]](#contents)

[`io.picoc`](library/unistd/io.picoc) packs descriptor requests and repeats partial regular-file
reads. The descriptor determines host routing:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`read(file_descriptor, buffer, count)`](library/unistd/io.picoc#L6) | Number read or `-1`. Repeats bounded regular-file chunks and may wait for terminal input | [`SYSCALL_READ`](common/syscall.header#L32) with [`IoRequest`](common/file.header#L31)<br>**Host Request:** `read-range <offset> <count> <path>` for a regular-file descriptor |
| [`write(file_descriptor, buffer, count)`](library/unistd/io.picoc#L32) | Number written or `-1`. Protects arbitrary data from UART control parsing | [`SYSCALL_WRITE`](common/syscall.header#L33) with [`IoRequest`](common/file.header#L31)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>`literal-output <count>` before output containing `<ESC>`, except for the null device |
| [`write_without_uart_escape_check(file_descriptor, buffer, count)`](library/unistd/io.picoc#L43) | Number written or `-1`. Skips the UART `<ESC>` scan and therefore requires a buffer known not to contain `<ESC>` | [`SYSCALL_WRITE`](common/syscall.header#L33) with [`IoRequest`](common/file.header#L31)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>No `literal-output` request |
| [`close(file_descriptor)`](library/unistd/io.picoc#L54) | 0 or `-1`. Releases the descriptor entry's path and state | [`SYSCALL_CLOSE`](common/syscall.header#L34) with the descriptor directly |
| [`dup2(old_file_descriptor, new_file_descriptor)`](library/unistd/io.picoc#L58) | New descriptor or `-1`. Copies the entry independently. Later inheritance depends on the target slot and copied descriptor kind | [`SYSCALL_DUP2`](common/syscall.header#L36) with [`Dup2Request`](common/file.header#L48) |
| [`lseek(file_descriptor, offset, origin)`](library/unistd/io.picoc#L66) | New logical offset or `-1` | [`SYSCALL_LSEEK`](common/syscall.header#L35) with [`SeekRequest`](common/file.header#L42)<br>**Host Request:** `file-size <path>` only for [`SEEK_END`](common/file.header#L19) |

#### 10.2.1.3 Working-directory operations in `working_directory.picoc`
[\[↑ TOC\]](#contents)

[`working_directory.picoc`](library/unistd/working_directory.picoc) gets or changes the caller's PCB directory.
Changing it validates the path with the host:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`chdir(path)`](library/unistd/working_directory.picoc#L4) | 0 or `-1`. Replaces [`ProcessControlBlock.working_directory`](kernel/process/process.header#L39) | [`SYSCALL_CHDIR`](common/syscall.header#L39) with the path pointer directly<br>**Host Request:** `is-directory <path>` |
| [`getcwd(buffer, size)`](library/unistd/working_directory.picoc#L11) | The supplied buffer, or `NULL` on failure | [`SYSCALL_GETCWD`](common/syscall.header#L40) with [`GetCwdRequest`](common/syscall.header#L83) |

#### 10.2.1.4 Path operations in `file_removal.picoc`
[\[↑ TOC\]](#contents)

[`file_removal.picoc`](library/unistd/file_removal.picoc) forwards path operations after kernel normalization:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`unlink(path)`](library/unistd/file_removal.picoc#L4) | Host status for removing a file | [`SYSCALL_UNLINK`](common/syscall.header#L43) with the path pointer directly<br>**Host Request:** `unlink <path>` |
| [`rmdir(path)`](library/unistd/file_removal.picoc#L8) | Host status for removing an empty directory | [`SYSCALL_RMDIR`](common/syscall.header#L44) with the path pointer directly<br>**Host Request:** `rmdir <path>` |
| [`move(old_path, new_path)`](library/unistd/file_removal.picoc#L12) | Host status for moving or renaming a file or directory | [`SYSCALL_MOVE`](common/syscall.header#L45) with [`MoveRequest`](common/syscall.header#L94)<br>**Host Request:** `move <old path>\n<new path>` |
| [`touch(path)`](library/unistd/file_removal.picoc#L20) | Host status for creating a file or updating its timestamps | [`SYSCALL_TOUCH`](common/syscall.header#L46) with the path pointer directly<br>**Host Request:** `touch <path>` |

#### 10.2.1.5 Wait-queue operations in `blocking.picoc`
[\[↑ TOC\]](#contents)

[`blocking.picoc`](library/unistd/blocking.picoc) initializes queues directly and uses syscalls for sleeping
and waking:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`wait_queue_init(wq)`](library/unistd/blocking.picoc#L4) | Initializes [`wait_queue.head`](common/wait_queue.header#L6) and [`wait_queue.tail`](common/wait_queue.header#L7) to `NULL` | No syscall |
| [`sleep(wq)`](library/unistd/blocking.picoc#L9) | Sets the process's [`ProcessControlBlock.state`](kernel/process/process.header#L33) to [`PROCESS_STATE_BLOCKED`](kernel/process/process.header#L15) and places it on the queue | [`SYSCALL_SLEEP`](common/syscall.header#L19) with the queue pointer directly |
| [`wakeup(wq)`](library/unistd/blocking.picoc#L19) | Wakes at most the process at the FIFO head | [`SYSCALL_WAKEUP`](common/syscall.header#L20) with the queue pointer directly |

### 10.2.2 fcntl: opening and creating files
[\[↑ TOC\]](#contents)

[`fcntl`](library/fcntl/) opens or creates descriptors. Device paths are handled inside the
kernel:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`open(path, flags)`](library/fcntl/fcntl.picoc#L5) | Lowest free descriptor or `-1` | [`SYSCALL_OPEN`](common/syscall.header#L31) with [`OpenRequest`](common/file.header#L26)<br>**Host Requests:** `file-size <path>` for every nontruncating regular open. After failure with [`O_CREAT`](common/file.header#L13), or for [`O_TRUNC`](common/file.header#L14), the requests are `write <path>` then `write stdout` |
| [`creat(path)`](library/fcntl/fcntl.picoc#L13) | Equivalent to an open for writing, creation, and truncation | Calls [`open()`](library/fcntl/fcntl.picoc#L5), which uses [`SYSCALL_OPEN`](common/syscall.header#L31)<br>**Host Requests:** `write <path>`, then `write stdout` for a regular path |

### 10.2.3 sys/wait: waiting for children
[\[↑ TOC\]](#contents)

[`sys/wait`](library/sys/wait/) provides child waiting and a stopped-status test. [`10.1 From a library call to the kernel: waitpid`](#101-from-a-library-call-to-the-kernel-waitpid) follows
the implementation. The table summarizes their results:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`waitpid(pid)`](library/sys/wait/wait.picoc#L14) | Exact child's exit or stopped status, or `-1` | [`SYSCALL_WAITPID`](common/syscall.header#L13) with [`WaitPidRequest`](common/syscall.header#L61). Waiting may suspend its stack frame |
| [`WIFSTOPPED(status)`](library/sys/wait/wait.picoc#L25) | Whether status represents [`SIGSTOP`](common/signal.header#L7), [`SIGTSTP`](common/signal.header#L8), or [`SIGTTIN`](common/signal.header#L9) | No syscall |

### 10.2.4 mutex: locking and waking contenders
[\[↑ TOC\]](#contents)

[`mutex`](library/mutex/) combines `TSL` with [`unistd`](library/unistd/) wait queues:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`testset(lock_addr)`](library/mutex/mutex.picoc#L3) | Atomically writes 1 and returns the old lock value | No syscall, one RETI `TSL` instruction |
| [`mutex_init(m)`](library/mutex/mutex.picoc#L12) | Clears lock and initializes embedded wait queue | No syscall |
| [`mutex_lock(m)`](library/mutex/mutex.picoc#L18) | Acquires the lock. Contenders wait instead of spinning | Uses [`testset()`](library/mutex/mutex.picoc#L3), then [`SYSCALL_SLEEP`](common/syscall.header#L19) through [`sleep()`](library/unistd/blocking.picoc#L9) when the lock is held |
| [`mutex_unlock(m)`](library/mutex/mutex.picoc#L25) | Clears the lock and wakes one contender | Uses [`SYSCALL_WAKEUP`](common/syscall.header#L20) through [`wakeup()`](library/unistd/blocking.picoc#L19) |

`mutex` contains a lock and embedded queue. Placing it in shared memory
lets participants use both, while the queue references kernel-owned PCBs.
[`7.3 Mutexes with test-and-set and wait queues`](#73-mutexes-with-test-and-set-and-wait-queues) explains acquisition and its lost-wakeup limitation.

### 10.2.5 sys/mman: named shared memory
[\[↑ TOC\]](#contents)

[`sys/mman`](library/sys/mman/) opens shared regions by name, maps them by ID, and removes their
names. [`5. Shared Memory Entries and Mappings`](#5-shared-memory-entries-and-mappings) explains deferred destruction:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`shm_open(name, size)`](library/sys/mman/mman.picoc#L15) | Existing or new shared-memory ID, or `-1` | [`SYSCALL_SHM_OPEN`](common/syscall.header#L26) with [`ShmOpenRequest`](common/syscall.header#L78) |
| [`mmap(shared_memory_id)`](library/sys/mman/mman.picoc#L23) | Shared absolute address or `NULL`. Creates a [`SharedMemoryAttachment`](kernel/shared_memory.header#L17) for the calling process | [`SYSCALL_MMAP`](common/syscall.header#L27) with the ID directly |
| [`shm_unlink(name)`](library/sys/mman/mman.picoc#L27) | 0 or `-1`. Removes the name and requests deferred destruction | [`SYSCALL_SHM_UNLINK`](common/syscall.header#L28) with the name pointer directly |

### 10.2.6 dirent: directory streams
[\[↑ TOC\]](#contents)

[`dirent`](library/dirent/) fetches a listing once and parses it in userspace. A
[`DirectoryStream`](library/dirent/dirent.header#L14) owns the buffer and reuses an embedded result entry:

```c
struct dirent {
    int d_type;
    char d_name[DIRENT_NAME_MAX];
};

struct DirectoryStream {
    char *contents;
    int length;
    int offset;
    struct dirent entry;
};
```

[`DIR`](library/dirent/dirent.header#L21) is a User Process Heap object. [`contents`](library/dirent/dirent.header#L15) points to a separate
512-cell listing, and [`offset`](library/dirent/dirent.header#L17) selects the next record. [`readdir()`](library/dirent/dirent.picoc#L40) overwrites
the embedded [`entry`](library/dirent/dirent.header#L18). The table identifies initialization and use:

| Field | Meaning | Used by |
| --- | --- | --- |
| [`DirectoryStream.contents`](library/dirent/dirent.header#L15) | Owned 512-cell listing buffer | First allocated by [`opendir()`](library/dirent/dirent.picoc#L8) and filled by [`read_host_directory()`](kernel/filesystem/host_filesystem.picoc#L187), parsed by [`readdir()`](library/dirent/dirent.picoc#L40) and freed by [`closedir()`](library/dirent/dirent.picoc#L66) |
| [`DirectoryStream.length`](library/dirent/dirent.header#L16) | Received listing length, excluding its terminator | First initialized by [`opendir()`](library/dirent/dirent.picoc#L8), bounds reads in [`readdir()`](library/dirent/dirent.picoc#L40) |
| [`DirectoryStream.offset`](library/dirent/dirent.header#L17) | Position of the next listing record | First initialized to 0 by [`opendir()`](library/dirent/dirent.picoc#L8), advanced by [`readdir()`](library/dirent/dirent.picoc#L40) |
| [`DirectoryStream.entry`](library/dirent/dirent.header#L18) | Embedded result reused for each directory entry | First populated by [`readdir()`](library/dirent/dirent.picoc#L40), its returned pointer stays valid only while the stream exists and its contents change on the next read |
| [`dirent.d_type`](library/dirent/dirent.header#L10) | Directory or regular-file type | First initialized by [`readdir()`](library/dirent/dirent.picoc#L40) from the record’s leading character |
| [`dirent.d_name`](library/dirent/dirent.header#L11) | Terminated name, limited to 127 characters | First initialized by [`readdir()`](library/dirent/dirent.picoc#L40), long names are truncated |

Opening requests the listing, reading parses it, and closing frees it.
Allocation failures follow the diagnostic path in [`10.2.7 stdlib: process heap, environment, conversion, and exit`](#1027-stdlib-process-heap-environment-conversion-and-exit):

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`opendir(path)`](library/dirent/dirent.picoc#L8) | Stream pointer, or `NULL` for a null path or listing failure. Allocates the stream and buffer. Allocation failure terminates the process in PicoOS | [`SYSCALL_READ_DIRECTORY`](common/syscall.header#L42) with [`ReadDirectoryRequest`](common/syscall.header#L88)<br>[`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through [`malloc()`](library/stdlib/malloc.picoc#L35) on allocation failure<br>**Host Requests:** `ls <path>`<br>For the heap-full message, `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`readdir(directory)`](library/dirent/dirent.picoc#L40) | Pointer to the reused [`entry`](library/dirent/dirent.header#L18), or `NULL` at end/for a null stream | No syscall |
| [`closedir(directory)`](library/dirent/dirent.picoc#L66) | `0` after freeing buffer/stream, `-1` for a null stream | No syscall |

### 10.2.7 stdlib: process heap, environment, conversion, and exit
[\[↑ TOC\]](#contents)

[`stdlib`](library/stdlib/) supplies the process heap, environment, conversion, and exit
operations. Each image has its own [`process_heap`](library/stdlib/malloc.picoc#L6) and [`environ`](library/stdlib/env.picoc#L4) globals.

#### 10.2.7.1 Heap operations in `malloc.picoc`
[\[↑ TOC\]](#contents)

Failed positive allocations invoke [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25). The kernel
prints through descriptor 1 and terminates the process. Redirected output
can therefore issue host requests even during allocation or environment
operations. The table includes that failure path:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`require_process_heap_allocation(memory, size)`](library/stdlib/malloc.picoc#L8) | Returns `memory`. A `NULL` result for a positive size terminates the process | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) only for a failed positive allocation<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`init_process_heap(void)`](library/stdlib/malloc.picoc#L18) | Initializes [`process_heap`](library/stdlib/malloc.picoc#L6) over the region recorded in the current [`ProcessControlBlock`](kernel/process/process.header#L31) | [`SYSCALL_PROCESS_HEAP_START`](common/syscall.header#L23) and [`SYSCALL_PROCESS_HEAP_SIZE`](common/syscall.header#L24) |
| [`malloc(size)`](library/stdlib/malloc.picoc#L35) | Pointer to a first-fit allocation. Returns `NULL` for a nonpositive size. A failed positive allocation terminates the process | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through [`require_process_heap_allocation()`](library/stdlib/malloc.picoc#L8) only on failure<br>**Host Requests:** The heap-full diagnostic requests listed above |
| [`realloc(ptr, size)`](library/stdlib/malloc.picoc#L42) | Resized or moved pointer. Size 0 frees the block and returns `NULL`. A failed positive allocation terminates the process | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through [`require_process_heap_allocation()`](library/stdlib/malloc.picoc#L8) only on failure<br>**Host Requests:** The heap-full diagnostic requests listed above |
| [`free(ptr)`](library/stdlib/malloc.picoc#L49) | Releases and coalesces a process-heap block | No syscall |

#### 10.2.7.2 Decimal conversion in `atoi.picoc`
[\[↑ TOC\]](#contents)

[`atoi.picoc`](library/stdlib/atoi.picoc) converts text by reading the supplied string directly. It
does not allocate memory or enter the kernel.

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`atoi(text)`](library/stdlib/atoi.picoc#L4) | Converts optional sign and decimal characters | No syscall |

#### 10.2.7.3 Environment operations in `env.picoc`
[\[↑ TOC\]](#contents)

[`env.picoc`](library/stdlib/env.picoc) manages [`environ`](library/stdlib/env.picoc#L4). Creating or enlarging entries uses the process
heap, including the failure path in [`10.2.7.1 Heap operations in malloc.picoc`](#10271-heap-operations-in-mallocpicoc).

At startup, [`start_process()`](library/start/start.picoc#L7) locates the initial
[`envp`](kernel/process/process_arguments.picoc#L141) array at `argv + argc + 1`.
The [`argc`](kernel/process/process_arguments.picoc#L131) argument pointers are
followed by the [`argv[argc] = NULL`](kernel/process/process_arguments.picoc#L180) sentinel,
then the environment pointers. [`initialize_environment()`](library/stdlib/env.picoc#L97)
copies that array and its strings into the process heap and assigns
[`environ`](library/stdlib/env.picoc#L4). The stack address therefore comes from
the known argument layout, not a search for `=`. [`4.2.2.1.2 Initial argc, argv, and envp`](#42212-initial-argc-argv-and-envp)
shows the stack layout, and [`4.2.2.2.1 Environment origin and propagation`](#42221-environment-origin-and-propagation)
explains how the selected environment reaches it.

[`getenv()`](library/stdlib/env.picoc#L115) subsequently searches the heap-owned
[`environ`](library/stdlib/env.picoc#L4) array without a syscall or another stack
lookup. [`environment_variable_length()`](library/stdlib/env.picoc#L10) determines
the requested name's length. [`environment_variable_index()`](library/stdlib/env.picoc#L51)
visits entries until it finds a match or reaches the array's `NULL` sentinel.
For each entry, [`environment_variable_matches()`](library/stdlib/env.picoc#L37)
compares exactly the requested name characters and requires the next character
to be `=`. For example, `PATH=/user` matches `PATH`, while `PATH_EXTRA=/test`
does not. It does not scan for an arbitrary `=`. After a match, the returned
pointer skips the name and that one separator, as the complete lookup function
shows:

```c
char *getenv(char *name) {
    int name_length = environment_variable_length(name);
    int index = environment_variable_index(name, name_length);

    if (index == -1) {
        return NULL;
    }

    return environ[index] + name_length + 1;
}
```

The result points into the existing environment string, rather than a new
allocation. An empty value returns a pointer to its `\0` terminator, while a
missing name returns `NULL`. The table summarizes lookup and modification:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`getenv(name)`](library/stdlib/env.picoc#L115) | Pointer to value within matching `NAME=value` string, or `NULL` | No syscall |
| [`current_environment(void)`](library/stdlib/env.picoc#L6) | Current process-global [`environ`](library/stdlib/env.picoc#L4) pointer | No syscall |
| [`copy_environment_variable(variable)`](library/stdlib/env.picoc#L20) | Pointer to an allocated copy. A failed positive allocation terminates the process | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through [`malloc()`](library/stdlib/malloc.picoc#L35) only on failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`store_environment_variable(variable, name_length)`](library/stdlib/env.picoc#L67) | 0 after replacing or adding an entry. A failed positive reallocation terminates the process | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through [`realloc()`](library/stdlib/malloc.picoc#L42) only on failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`initialize_environment(environment)`](library/stdlib/env.picoc#L97) | Creates [`environ`](library/stdlib/env.picoc#L4) and copies the initial strings. Used internally during process startup | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through allocation helpers only on failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`setenv(name, value, overwrite)`](library/stdlib/env.picoc#L126) | 0 on success or when overwrite is disabled for an existing name. Allocates or replaces one owned string | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through allocation helpers only on failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`unsetenv(name)`](library/stdlib/env.picoc#L157) | 0. Frees a matching string and compacts the pointer array | No syscall |
| [`putenv(variable)`](library/stdlib/env.picoc#L174) | 0 after copying and storing `NAME=value`, or `-1` when `=` is missing | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through allocation helpers only on failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`clearenv(void)`](library/stdlib/env.picoc#L194) | 0. Frees all strings but retains an empty array | No syscall |
| [`clone_environment(void)`](library/stdlib/env.picoc#L205) | Deep process-heap copy of the current environment. Exposed to applications but not used by PicoOS programs | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through allocation helpers only on failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`destroy_environment(environment)`](library/stdlib/env.picoc#L230) | Frees a cloned array and its strings | No syscall |
| [`restore_environment(environment)`](library/stdlib/env.picoc#L243) | 0 after recreating current [`environ`](library/stdlib/env.picoc#L4), or `-1` for an invalid entry | [`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) through allocation helpers only on failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |

[`initialize_environment(environment)`](library/stdlib/env.picoc#L97) is declared internally by
[`start.picoc`](library/start/start.picoc#L5), not in the public
[`stdlib.header`](library/stdlib/stdlib.header).

#### 10.2.7.4 Process exit in `exit.picoc`
[\[↑ TOC\]](#contents)

[`exit.picoc`](library/stdlib/exit.picoc) contains the terminating operation used both directly and
when the application entry function returns. The kernel's status delivery,
PCB removal, resource cleanup, and dispatch are explained step by step in
[`7.1.2.2 Parent collection and final removal`](#7122-parent-collection-and-final-removal).

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`exit(status)`](library/stdlib/exit.picoc#L3) | Terminates the current process and does not normally return | [`SYSCALL_EXIT`](common/syscall.header#L12) with the status directly |

### 10.2.8 string: copying, comparison, and length
[\[↑ TOC\]](#contents)

[`string`](library/string/) operates directly on caller-provided memory. It allocates nothing
and makes no syscalls. Sizes count RETI cells, and copies need room for
the terminator:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`strcpy(destination, source)`](library/string/string.picoc#L4) | Copies a terminated string and returns the destination | No syscall |
| [`strcat(destination, source)`](library/string/string.picoc#L16) | Appends a terminated string and returns the destination | No syscall |
| [`strcmp(left, right)`](library/string/string.picoc#L34) | Difference between the first unequal cells, or 0 for equal strings | No syscall |
| [`strncmp(left, right, count)`](library/string/string.picoc#L44) | Comparison limited to `count` cells. Returns a negative value, zero, or a positive value | No syscall |
| [`strlen(string)`](library/string/string.picoc#L60) | Number of cells before the terminator | No syscall |

### 10.2.9 stdio: streams, formatting, and scanning
[\[↑ TOC\]](#contents)

[`stdio`](library/stdio/) builds streams and formatting on descriptors. A [`PicoFile`](library/stdio/stdio.header#L3) stores
only the descriptor number:

```c
struct PicoFile {
    int file_descriptor;
};
```

Each image has standard stream objects, five additional stream slots, and
usage flags. Streams have no private buffer or EOF/error flags. Scanning
uses [`has_unread_input`](library/stdio/scanf.picoc#L4) and [`unread_input`](library/stdio/scanf.picoc#L5) for one-character pushback.
The field table describes the descriptor stored in each stream:

| Field | Meaning | Used by |
| --- | --- | --- |
| [`PicoFile.file_descriptor`](library/stdio/stdio.header#L4) | Entry number in the current process’s descriptor table | First initialized by [`prepare_standard_streams()`](library/stdio/stdio.picoc#L45) for standard streams and [`fopen()`](library/stdio/stdio.picoc#L125) for extra streams, used by [`fgetc()`](library/stdio/stdio.picoc#L178), [`fputc()`](library/stdio/stdio.picoc#L204), [`fputs()`](library/stdio/stdio.picoc#L229), and [`fclose()`](library/stdio/stdio.picoc#L155) |

The following tables separate output and stream operations from scanning.

#### 10.2.9.1 Streams and output in `stdio.picoc`
[\[↑ TOC\]](#contents)

[`stdio.picoc`](library/stdio/stdio.picoc) prepares streams and performs descriptor I/O and formatting.
First use calls [`prepare_standard_streams()`](library/stdio/stdio.picoc#L45), which queries descriptor
availability once:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`standard_input(void)`](library/stdio/stdio.picoc#L79) | Address of the process-global input stream | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) only on first stream preparation. No host request |
| [`standard_output(void)`](library/stdio/stdio.picoc#L84) | Address of the process-global output stream | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) only on first stream preparation. No host request |
| [`standard_error(void)`](library/stdio/stdio.picoc#L89) | Address of the process-global error stream | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) only on first stream preparation. No host request |
| [`fopen(path, mode)`](library/stdio/stdio.picoc#L125) | One of five stream slots or `NULL`. Supports `r`, `w`, `a`, and `+` | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation<br>[`SYSCALL_OPEN`](common/syscall.header#L31) with [`OpenRequest`](common/file.header#L26)<br>**Host Requests:** `file-size <path>` for a nontruncating regular open<br>`write <path>`, then `write stdout` for truncation or creation after a failed existence check |
| [`fclose(stream)`](library/stdio/stdio.picoc#L155) | 0 on close, or `-1` for an invalid stream or descriptor. Releases an additional stream slot | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation<br>[`SYSCALL_CLOSE`](common/syscall.header#L34) with the descriptor directly |
| [`fgetc(stream)`](library/stdio/stdio.picoc#L178) | Read character or `-1` | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation<br>[`SYSCALL_READ`](common/syscall.header#L32) with [`IoRequest`](common/file.header#L31)<br>**Host Request:** `read-range <offset> <count> <path>` for a regular-file stream |
| [`fputc(character, stream)`](library/stdio/stdio.picoc#L204) | Written character or `-1` | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation<br>[`SYSCALL_WRITE`](common/syscall.header#L33) with [`IoRequest`](common/file.header#L31)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>`literal-output <count>` before output containing `<ESC>`, except for the null device |
| [`fputs(text, stream)`](library/stdio/stdio.picoc#L229) | Written count or `-1` | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation<br>[`SYSCALL_WRITE`](common/syscall.header#L33) with [`IoRequest`](common/file.header#L31)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>`literal-output <count>` before output containing `<ESC>`, except for the null device |
| [`write_decimal(stream, value)`](library/stdio/stdio.picoc#L259) | Count written, or `-1` if writing a digit fails. Internal formatting helper | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation and [`SYSCALL_WRITE`](common/syscall.header#L33) through [`fputc()`](library/stdio/stdio.picoc#L204)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>No `literal-output` request because decimal output contains no `<ESC>` |
| [`format_stream(stream, format, argument_base, first_argument)`](library/stdio/stdio.picoc#L277) | Formatted count, or `-1` if output fails. Internal formatting helper | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation and [`SYSCALL_WRITE`](common/syscall.header#L33) through [`fputc()`](library/stdio/stdio.picoc#L204) or [`fputs()`](library/stdio/stdio.picoc#L229)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>`literal-output <count>` before an output value containing `<ESC>`, except for the null device |
| [`fprintf(stream, format, ...)`](library/stdio/stdio.picoc#L346) | Written count or `-1` | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation and [`SYSCALL_WRITE`](common/syscall.header#L33) through [`format_stream()`](library/stdio/stdio.picoc#L277)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` for regular files<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr<br>`literal-output <count>` before an output value containing `<ESC>`, except for the null device |
| [`printf(format, ...)`](library/stdio/stdio.picoc#L354) | Written count or `-1` to [`stdout`](library/stdio/stdio.header#L10) | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first preparation and [`SYSCALL_WRITE`](common/syscall.header#L33) through [`format_stream()`](library/stdio/stdio.picoc#L277)<br>**Host Requests:** `write-at <offset> <path>`, then `write stdout` when descriptor 1 is a regular file<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` when descriptor 1 is a copied terminal-stderr entry<br>`literal-output <count>` before an output value containing `<ESC>`, except for the null device |

Formatting supports `%d`, `%c`, `%s`, and `%%`.
[`1.1.3 System V ABI stack frames and call cleanup`](#113-system-v-abi-stack-frames-and-call-cleanup)
gives the stack locations used for variadic arguments.

#### 10.2.9.2 Scanning in `scanf.picoc`
[\[↑ TOC\]](#contents)

[`scanf.picoc`](library/stdio/scanf.picoc) parses `%d`, `%c`, `%s`, literal characters, and
whitespace. It reads through [`fgetc()`](library/stdio/stdio.picoc#L178) and uses
[`has_unread_input`](library/stdio/scanf.picoc#L4) with
[`unread_input`](library/stdio/scanf.picoc#L5) as one-character pushback state.

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`read_input(void)`](library/stdio/scanf.picoc#L16) | Returns the saved pushback character when present, otherwise reads one character from [`stdin`](library/stdio/stdio.header#L9). Internal scanning helper | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first stream preparation and [`SYSCALL_READ`](common/syscall.header#L32) through [`fgetc()`](library/stdio/stdio.picoc#L178) when no character is saved<br>**Host Request:** `read-range <offset> <count> <path>` when descriptor 0 is a regular file |
| [`skip_whitespace(void)`](library/stdio/scanf.picoc#L30) | Consumes whitespace and saves the first following character. Internal scanning helper | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first stream preparation and [`SYSCALL_READ`](common/syscall.header#L32) through [`read_input()`](library/stdio/scanf.picoc#L16)<br>**Host Request:** `read-range <offset> <count> <path>` when descriptor 0 is a regular file |
| [`read_decimal(target)`](library/stdio/scanf.picoc#L40) | Whether a signed decimal value was read into `target`. Internal scanning helper | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first stream preparation and [`SYSCALL_READ`](common/syscall.header#L32) through [`read_input()`](library/stdio/scanf.picoc#L16)<br>**Host Request:** `read-range <offset> <count> <path>` when descriptor 0 is a regular file |
| [`read_string(target)`](library/stdio/scanf.picoc#L83) | Whether a nonempty, whitespace-delimited string was read into `target`. Internal scanning helper | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first stream preparation and [`SYSCALL_READ`](common/syscall.header#L32) through [`read_input()`](library/stdio/scanf.picoc#L16)<br>**Host Request:** `read-range <offset> <count> <path>` when descriptor 0 is a regular file |
| [`scanf(format, ...)`](library/stdio/scanf.picoc#L112) | Number of assigned arguments | [`SYSCALL_FILE_DESCRIPTORS_AVAILABLE`](common/syscall.header#L30) on first stream preparation and [`SYSCALL_READ`](common/syscall.header#L32) through the scanning helpers above<br>**Host Request:** `read-range <offset> <count> <path>` when descriptor 0 is a regular file |

### 10.2.10 start: entering and leaving a user program
[\[↑ TOC\]](#contents)

[`start`](library/start/) supplies the `-C` entry point and the helper that prepares the
runtime before calling `main`. It has no public header. [`1.1.5.2 PicoOS libstart startup sequence`](#1152-picoos-libstart-startup-sequence) gives its
complete source:

| Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- |
| [`_start(argc, first_argument)`](library/start/start.picoc#L14) | Entry point without a generated stack frame. Calls [`start_process()`](library/start/start.picoc#L7) | Through [`start_process()`](library/start/start.picoc#L7), [`SYSCALL_PROCESS_HEAP_START`](common/syscall.header#L23), [`SYSCALL_PROCESS_HEAP_SIZE`](common/syscall.header#L24), and [`SYSCALL_EXIT`](common/syscall.header#L12)<br>[`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) on environment allocation failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |
| [`start_process(argc, argv)`](library/start/start.picoc#L7) | Initializes the heap and environment, calls the application entry function, then exits with its status | [`SYSCALL_PROCESS_HEAP_START`](common/syscall.header#L23), [`SYSCALL_PROCESS_HEAP_SIZE`](common/syscall.header#L24), and [`SYSCALL_EXIT`](common/syscall.header#L12)<br>[`SYSCALL_PROCESS_HEAP_FULL`](common/syscall.header#L25) on environment allocation failure<br>**Host Requests for the heap-full message:** `write-at <offset> <path>`, then `write stdout` for a regular descriptor 1<br>Optional `file-size <path>` before append<br>`write stderr`, then `write stdout` for terminal stderr |

### 10.2.11 Single-function libraries
[\[↑ TOC\]](#contents)

Five libraries expose one public function each: [`schedule`](library/schedule/), [`signal`](library/signal/),
[`sys/prctl`](library/sys/prctl/), [`sys/reboot`](library/sys/reboot/), and [`sys/stat`](library/sys/stat/). Private assembly helpers are
implementation details. This table groups the public interfaces:

| Library | Library function | Return value / status and purpose | Syscalls / Host Requests |
| --- | --- | --- | --- |
| [`schedule`](library/schedule/) | [`yield(void)`](library/schedule/schedule.picoc#L4) | Voluntarily saves the current activation and schedules another runnable process | [`SYSCALL_YIELD`](common/syscall.header#L21) with no request structure |
| [`signal`](library/signal/) | [`kill(pid, signal_number)`](library/signal/signal.picoc#L14) | 0 or `-1`. Signal 0 only probes existence | [`SYSCALL_KILL`](common/syscall.header#L16) with [`KillRequest`](common/syscall.header#L66) |
| [`sys/prctl`](library/sys/prctl/) | [`prctl(option, argument)`](library/sys/prctl/prctl.picoc#L14) | 0 or `-1`. Supports [`PR_SET_PDEATHSIG`](common/prctl.header#L3) | [`SYSCALL_PRCTL`](common/syscall.header#L17) with [`PrctlRequest`](common/syscall.header#L71) |
| [`sys/reboot`](library/sys/reboot/) | [`reboot(command)`](library/sys/reboot/reboot.picoc#L5) | Does not return for [`REBOOT_CMD_RESTART`](library/sys/reboot/reboot.header#L3) or [`REBOOT_CMD_POWER_OFF`](library/sys/reboot/reboot.header#L4). Returns `-1` for any other command | [`SYSCALL_REBOOT`](common/syscall.header#L6) for restart or [`SYSCALL_SHUTDOWN`](common/syscall.header#L5) for power-off<br>**Host Requests after firmware restart:** `load kernel/kernel.bin` from the bootloader, then `load /system/init.bin` from kernel startup<br>None for power-off |
| [`sys/stat`](library/sys/stat/) | [`mkdir(path)`](library/sys/stat/stat.picoc#L5) | 0 on success, or `-1` for an invalid path or host failure | [`SYSCALL_MKDIR`](common/syscall.header#L41) with the path pointer directly<br>**Host Request:** `mkdir <path>` |

Restart enters the EPROM bootloader again, which reloads the kernel and
init. These are consequences of [`reboot()`](library/sys/reboot/reboot.picoc#L5), without a separate UART restart
command. [`11. Complete startup: bootloader, kernel, init, shell, and user applications`](#11-complete-startup-bootloader-kernel-init-shell-and-user-applications) follows the boot sequence.

Signal requests are read synchronously. A self-directed terminating signal can return before the
dispatcher applies termination. The actions and timing are explained in
[`7.2 Process signals`](#72-process-signals).

# 11. Complete startup: bootloader, kernel, init, shell, and user applications
[\[↑ TOC\]](#contents)

Startup follows a loading chain: bootloader → kernel → init → shell →
application. Each step places an image in memory before transferring
execution to its entry point.

The diagram connects that chain to memory. EPROM holds the bootloader,
and SRAM holds its temporary stack and all later runtime state. The kernel
comes from the host over UART, with DMA when enabled. Solid arrows show
loading, and dotted arrows show register setup and control transfer:

```mermaid
%%{init: {"sequence":{"height":90},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }","theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"}}}%%
sequenceDiagram
    box #f4f8f8 EPROM
        participant B as Bootloader<br/>.text and .data
    end
    box #f4f8f8 Kernel-reserved SRAM
        participant K as Kernel image<br/>0–41485<br/>.ivt: 0–4<br/>.text from 5<br/>.data from 40755
        participant KH as Kernel heap<br/>41486–45581
        participant KS as Kernel stack<br/>45582–48297
    end
    box #f4f8f8 Process and Shared Data Heap
        participant I as Init image<br/>libstart startup
        participant SH as Shell image<br/>libstart startup
        participant A as Application A<br/>libstart startup
        participant C as Application B<br/>libstart startup
    end
    B->>K: boot_main loads the kernel payload at SRAM offset 0
    B-->>KS: start_loaded_kernel sets SP and BAF from stack_start
    B-->>K: MOVE CS PC transfers control to kernel _start
    K->>KS: main calls activate_kernel_stack_boundary
    K->>KH: main calls init_kernel_heap, then heap_init_region
    K->>I: load_process loads init
    I->>SH: init loads the shell
    SH->>A: shell loads application A
    SH->>C: shell loads application B
```

The offsets come from the current kernel layout. The bootloader starts
with a temporary stack at SRAM offset `262143`. [`start_loaded_kernel()`](boot/bootloader.picoc#L21)
replaces it with the kernel stack at `48297`. Kernel startup initializes
heap cells `41486..45581` and installs `45581` as the stack boundary.

The Process and Shared Data Heap starts at `48298`. It is managed by
[`PSDMalloc()`](kernel/psdmalloc.picoc#L20), separately from the preceding Kernel Heap managed by [`kmalloc()`](kernel/kmalloc.picoc#L23).

Init, the shell, and applications occupy separate Process Payloads, with
PCBs in the Kernel Heap. Their allocation addresses vary. [`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy) shows the
full map, and [`9.1 Memory layout, allocation sources, and lifetimes`](#91-memory-layout-allocation-sources-and-lifetimes) explains ownership.

These entry functions have different jobs despite sharing the name `_start`:

| Component | Startup implementation | Execution path |
| --- | --- | --- |
| Bootloader | Custom naked [`_start(void)`](boot/bootloader.picoc#L9), defined in the bootloader itself | Sets the initial registers, then jumps to [`boot_main()`](boot/bootloader.picoc#L41) |
| Kernel | Default PicoC compiler-generated [`_start`](kernel/kernel.reti#L7), linked without `-C` | Calls kernel [`main()`](kernel/kernel.picoc#L31) and halts if it returns |
| Init process | [`libstart`](library/start/libstart.picoc), selected with `-C library/start/libstart.picoc` | [`_start()`](library/start/start.picoc#L14) → [`start_process()`](library/start/start.picoc#L7) → init [`main()`](system/init.picoc#L100) → [`exit()`](library/stdlib/exit.picoc#L3) if it returns |
| Shell | The same [`libstart`](library/start/libstart.picoc) selection | [`_start()`](library/start/start.picoc#L14) → [`start_process()`](library/start/start.picoc#L7) → shell [`main()`](user/shell.picoc#L1448) → [`exit()`](library/stdlib/exit.picoc#L3) |
| User applications | The same [`libstart`](library/start/libstart.picoc) selection | [`_start()`](library/start/start.picoc#L14) → [`start_process()`](library/start/start.picoc#L7) → the application's `main` → [`exit()`](library/stdlib/exit.picoc#L3) |

## 11.1 Loading the kernel from the EPROM bootloader
[\[↑ TOC\]](#contents)

The bootloader's naked [`_start()`](boot/bootloader.picoc#L9) sets EPROM `CS` and `DS` and a temporary
SRAM stack, then jumps to [`boot_main()`](boot/bootloader.picoc#L41). It uses neither a generated entry
nor userspace [`libstart`](library/start/libstart.picoc).

These three functions implement loading and control transfer:

<!-- TODO: Consider removing this function table once the prose and source examples are sufficient. -->

| Bootloader function | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`_start(void)`](boot/bootloader.picoc#L9) | Does not return | Establishes EPROM `CS`/`DS` and a temporary stack at the top of SRAM | Jumps to [`boot_main()`](boot/bootloader.picoc#L41) | **Machine entry:** PC 0 at boot. Kernel [`reboot()`](kernel/kernel.picoc#L19) |
| [`boot_main(void)`](boot/bootloader.picoc#L41) | Jumps into the kernel on success, halts on a missing or undersized image | Requests [`kernel/kernel.bin`](binary/kernel/kernel.bin), consumes the five header words, and copies the payload to SRAM | [`uart_send_host_request()`](common/uart_protocol.picoc#L82), [`receive_word()`](common/uart_protocol.picoc#L7), [`uart_print_string()`](common/uart_protocol.picoc#L73), [`uart_print_loading_bar_label()`](common/loading_bar.picoc#L6), [`receive_words_to_sram()`](common/sram_loader.picoc#L6), jumps to [`start_loaded_kernel()`](boot/bootloader.picoc#L21)<br>**Host request:** `load kernel/kernel.bin` | **Bootloader functions:** [`_start()`](boot/bootloader.picoc#L9) |
| [`start_loaded_kernel(void)`](boot/bootloader.picoc#L21) | Does not return | Adds the SRAM base to the header's code/data/stack offsets, replaces the boot stack, and sets kernel `CS`, `DS`, `SP`, and `BAF` | Jumps to the generated kernel [`_start`](kernel/kernel.reti#L7), which calls [`main()`](kernel/kernel.picoc#L31) | **Bootloader functions:** [`boot_main()`](boot/bootloader.picoc#L41) |

The initial entry establishes the segments and temporary stack before any
ordinary PicoC call frames are needed:

```c
__attribute__((naked))
void _start(void) {
    asm("LOADI CS 0"); // Sets CS to the EPROM base
    asm(EPROM_STACK_START_ASM); // LOADI32 SP eprom_stack_start
    asm("MOVE SP BAF"); // BAF = eprom_stack_start
    asm(EPROM_DS_START_ASM); // LOADI32 DS eprom_ds_start
    asm("ADD DS CS"); // DS = CS + eprom_ds_start
    asm("LOADI32 ACC boot_main"); // ACC = boot_main in EPROM
    asm("ADD ACC CS"); // ACC = CS + boot_main
    asm("MOVE ACC PC"); // JUMP to boot_main in EPROM
}
```

[`boot_main()`](boot/bootloader.picoc#L41) requests [`kernel/kernel.bin`](binary/kernel/kernel.bin), reads its header, and loads
only the payload at [`SRAM_BASE`](kernel/memory_constants.header#L1). The first five payload words are `.ivt`,
followed by code and data. [`receive_words_to_sram()`](common/sram_loader.picoc#L6) selects polling or DMA:

```c
void boot_main(void) {
    int code_start;
    int data_start;
    int stack_start;
    int word_count;
    int payload_word_count;

    uart_send_host_request("load ", "kernel/kernel.bin");

    word_count = receive_word();
    if (word_count == -1) {
        uart_print_string("error: could not load kernel\n");
        asm("JUMP 0");
    }
    if (word_count < 5) {
        uart_print_string("error: invalid kernel image\n");
        asm("JUMP 0");
    }
    code_start = receive_word();
    data_start = receive_word();
    receive_word(); // Discards heap_start because the kernel uses memory_constants.header
    receive_word(); // Discards heap_size because the kernel uses memory_constants.header
    stack_start = receive_word();
    if (stack_start == -1) {
        stack_start = SRAM_MAX_ADDRESS;
    }

    payload_word_count = word_count - 5;
    uart_print_loading_bar_label(
        loading_bar_enabled,
        "load ",
        "kernel/kernel.bin"
    );
    receive_words_to_sram(
        SRAM_BASE,
        payload_word_count,
        loading_bar_enabled
    );
    asm("LOADI32 ACC start_loaded_kernel"); // ACC = start_loaded_kernel
    asm("ADD ACC CS"); // ACC = CS + start_loaded_kernel in EPROM
    asm("MOVE ACC PC"); // JUMP to start_loaded_kernel in EPROM
}
```

[`start_loaded_kernel()`](boot/bootloader.picoc#L21) still runs in EPROM. It adds the SRAM base to the
header offsets, installs kernel registers, and writes `CS` to `PC`:

```c
__attribute__((naked))
void start_loaded_kernel(void) {
    // BAF points behind the kernel metadata
    asm("LOADIN BAF ACC 0"); // ACC = code_start
    asm("LOADIN BAF IN1 -1"); // IN1 = data_start
    asm("LOADIN BAF IN2 -2"); // IN2 = stack_start

    asm("LOADI32 CS -2147483648"); // -2^31, SRAM base
    asm("MOVE CS DS"); // DS = SRAM base
    asm("MOVE CS SP"); // SP = SRAM base

    asm("ADD CS ACC"); // CS = SRAM base + code_start

    asm("ADD DS IN1"); // DS = SRAM base + data_start

    asm("ADD SP IN2"); // SP = SRAM base + stack_start
    asm("MOVE SP BAF"); // BAF = SP

    asm("MOVE CS PC"); // JUMP to CS
}
```

`MOVE CS PC` enters the generated kernel [`_start`](kernel/kernel.reti#L7) at `0x80000005`. It is
a jump without a bootloader return address. Changing segment registers
alone does not transfer execution.

## 11.2 Kernel startup
[\[↑ TOC\]](#contents)

The generated entry from [`1.1.5.1 Default compiler-generated _start`](#1151-default-compiler-generated-_start) calls kernel [`main()`](kernel/kernel.picoc#L31). Both execute from
`.text`. Globals and constants occupy `.data`. [`kernel/kernel.reti`](kernel/kernel.reti#L7) shows
the entry just after `.ivt`.

<!-- Presentation generation: Reproduce the default compiler-generated _start source from 1.1.5.1 here, directly before kernel main. Show the main call and exit operation again at this presentation stage. Do not require navigation back to earlier presentation stages. -->

Kernel [`main()`](kernel/kernel.picoc#L31) initializes allocators, terminal and process state, DMA,
and interrupt routing before loading init and scheduling it:

```c
int main(void) {
    int init_pid;
    struct RunProcessRequest init_request;

    activate_kernel_stack_boundary();
    init_kernel_heap();
    initialize_terminal();
    initialize_process_table();
    init_process_shared_data_heap();
    initialize_shared_memory();
    if (dma_is_active()) {
        initialize_dma();
    }
    interrupt_controller_initialize();
    init_pid = load_process("system/init.bin", loading_bar_enabled);
    init_request.pid = init_pid;
    init_request.arguments = NULL;
    init_request.environment = NULL;
    if (mark_process_ready_with_arguments(&init_request)) {
        interrupt_controller_activate_timer();
        dispatcher_start_next_process();
    }
    return 0;
}
```

The globals reside in kernel `.data`, while [`init_request`](kernel/kernel.picoc#L33) is local to the
kernel stack. It supplies the initial arguments to run setup. [`9.3 Kernel global variables and process-list roots`](#93-kernel-global-variables-and-process-list-roots) lists
the globals.

### 11.2.1 Loading init and entering normal execution
[\[↑ TOC\]](#contents)

[`load_process()`](kernel/process/process_loader.picoc#L305) allocates init's payload and creates PID 1. Its PCB stores
the memory bounds and initial activation. Init gets directory `/`, no
parent, `argv[0]`, and an empty environment.

Run setup changes init from [`NEW`](kernel/process/process.header#L12) to [`READY`](kernel/process/process.header#L13). After timer activation, the
dispatcher selects it, sets [`RUNNING`](kernel/process/process.header#L14), and restores its registers. `RTI`
consumes the prepared PC and enters init's `libstart` entry. It does not
call init's [`main()`](system/init.picoc#L100) directly.

Successful dispatch leaves kernel [`main()`](kernel/kernel.picoc#L31) through `RTI`. Later interrupts
and syscalls reenter the kernel. The dispatcher waits if no process is
runnable. Failure to load or prepare init returns to the generated halt.

[`shutdown()`](kernel/kernel.picoc#L15) stops with `JUMP 0` without freeing objects first. [`reboot()`](kernel/kernel.picoc#L19)
disables device interrupts, clears the timer and stack boundary, and sets
`PC = 0` to rerun the EPROM bootloader. Their implementations are:

```c
void shutdown(void) {
    asm("JUMP 0");
}

void reboot(void) {
    int device = 0;

    while (device < INTERRUPT_DEVICE_COUNT) {
        interrupt_controller_disable_device(device);
        device = device + 1;
    }
    periphery_write_register(INTERRUPT_CONTROLLER_TIMER_INTERVAL_REGISTER, 0);
    periphery_write_register(STACK_HEAP_BOUNDARY_REGISTER, 0);
    asm("LOADI PC 0");
}
```

Userspace selects these actions through [`reboot()`](library/sys/reboot/reboot.picoc#L5). Kernel failure paths
and final-process exit can also halt. [`11.3.7 When init terminates`](#1137-when-init-terminates) describes the signal-path
limitation.

## 11.3 Init process
[\[↑ TOC\]](#contents)

Init uses the ordinary `libstart` entry from [`1.1.5.2 PicoOS libstart startup sequence`](#1152-picoos-libstart-startup-sequence). It prepares init's
heap and environment, calls [`main()`](system/init.picoc#L100), and exits with its result.

<!-- Presentation generation: Reproduce the libstart source from 1.1.5.2 here, directly before init's main/session loop. Show _start and start_process, including heap/environment initialization and exit(main(...)). Do not require navigation back to earlier presentation stages. -->

### 11.3.1 Init responsibilities
[\[↑ TOC\]](#contents)

The kernel manages execution and resources. Init configures the userspace
session and keeps a shell available. The table separates their jobs:

| Component | Responsibility |
| --- | --- |
| Kernel [`main()`](kernel/kernel.picoc#L31) | Initialize kernel state and devices, load PID 1, prepare its first execution, and dispatch |
| [`Init`](system/init.picoc#L100) | Read environment configuration, load and start a shell, wait for it, and load a new shell afterward |
| [`Shell`](user/shell.picoc#L1448) | Read commands, find and load applications, redirect input/output, and manage foreground execution |

Before any current process exists, the kernel resolves init's path from
`/` and creates its own directory copy. No `pwd` host request is needed.
Init otherwise uses ordinary libraries and syscalls.

### 11.3.2 Initial environment configuration
[\[↑ TOC\]](#contents)

[`read_environment()`](system/init.picoc#L19) reads [`config/environment.txt`](config/environment.txt) into a 257-cell buffer.
It rejects files of 256 or more cells and parses newline or CRLF-separated
`NAME=value` records with [`setenv()`](library/stdlib/env.picoc#L126). The file supplies `PATH=/user`, and
init optionally adds [`PICOOS_LOADING_BAR`](common/loading_bar.header#L5). The table follows these calls:

| Init function | Return value / status | Library functions |
| --- | --- | --- |
| [`init_write_error(text)`](system/init.picoc#L10) | No value | [`write()`](library/unistd/io.picoc#L32) sends the diagnostic to standard error without changing persistent init state |
| [`read_environment(void)`](system/init.picoc#L19) | `true` when the complete file was read into the environment, `false` after an allocation, file, size, or syntax failure | [`malloc()`](library/stdlib/malloc.picoc#L35), [`open()`](library/fcntl/fcntl.picoc#L5), [`read()`](library/unistd/io.picoc#L6), [`close()`](library/unistd/io.picoc#L54), [`setenv()`](library/stdlib/env.picoc#L126), and [`free()`](library/stdlib/malloc.picoc#L49), changes the process-global [`environ`](library/stdlib/env.picoc#L4) array |
| [`main(void)`](system/init.picoc#L100) | Returns status 1 when setup or shell launch fails, otherwise does not return | [`setenv()`](library/stdlib/env.picoc#L126), [`load()`](library/unistd/process.picoc#L17), [`run()`](library/unistd/process.picoc#L31), and exact-child [`waitpid()`](library/sys/wait/wait.picoc#L14) |

Missing, unreadable, oversized, or malformed configuration returns status
`1`. Init loads the shell by direct path. Run setup copies its environment
and descriptors, while loading already copied the directory.

### 11.3.3 Loading, starting, and waiting for the shell
[\[↑ TOC\]](#contents)

After configuration, init repeatedly loads, starts, and waits for one shell:

```c
int main(void) {
    int shell_pid;

    if (!read_environment()) {
        return 1;
    }
    if (loading_bar_enabled) {
        if (setenv(
                LOADING_BAR_ENVIRONMENT_VARIABLE,
                "true",
                true
            ) != 0) {
            init_write_error("init: could not configure loading bar\n");
            return 1;
        }
    }

    while (true) {
        shell_pid = load("./user/shell.bin");
        if (shell_pid == 0) {
            init_write_error("init: could not load shell\n");
            return 1;
        }

        if (!run(shell_pid, NULL, NULL)) {
            init_write_error("init: could not start shell\n");
            return 1;
        }

        waitpid(shell_pid);
    }
}
```

[`waitpid()`](library/sys/wait/wait.picoc#L14) selects that exact shell. Loading uses the polling or DMA path
from [`4.2.1 Loading a process (load library call)`](#421-loading-a-process-load-library-call), while [`11.3.2 Initial environment configuration`](#1132-initial-environment-configuration) explains configuration parsing.

### 11.3.4 Shell startup
[\[↑ TOC\]](#contents)

The dispatcher enters the shell through the same `libstart` sequence.
It initializes its own heap and inherited environment before [`main()`](user/shell.picoc#L1448).

<!-- Presentation generation: Show the libstart source from 1.1.5.2 again at shell startup when this stage has its own presentation stage. Place it here rather than sending the audience back to the earlier startup presentation stage. -->

The shell sets up descriptors and terminal ownership, then reads commands
while init waits. Returning from the shell lets init start another session.
[`12.2 Shell startup and command loop`](#122-shell-startup-and-command-loop) follows the command loop.

### 11.3.5 Loading user applications
[\[↑ TOC\]](#contents)

External commands get new Process Payloads through [`load()`](library/unistd/process.picoc#L17). [`run_process()`](user/shell.picoc#L1034)
prepares arguments, environment, and descriptors and makes them ready.
Built-ins run inside the shell without loading an image.

Applications also enter through `libstart` and exit with their `main`
result. The shell waits for foreground work and keeps accepting commands
for background work. [`12.4 Command parsing, expansion, and execution`](#124-command-parsing-expansion-and-execution) covers execution, and [`13. User applications and commands`](#13-user-applications-and-commands) lists the applications.

<!-- Presentation generation: Reproduce the libstart source from 1.1.5.2 directly at this application-startup stage in its presentation stage. Show the application's main call and the exit path here. Do not rely on navigation back to earlier presentation stages. -->

### 11.3.6 Shell exit and restart policy
[\[↑ TOC\]](#contents)

The shell's `exit` ends a session, letting init load another shell.
[`poweroff.bin`](user/poweroff.picoc#L12) halts the system, and [`reboot.bin`](user/reboot.picoc#L12) starts it again from
EPROM. Since [`waitpid()`](library/sys/wait/wait.picoc#L14) also reports stops, stopping the shell itself
can make init begin another session.

[`init`](system/init.picoc) lives under [`system`](system/) because it implements
system policy. It is not exposed through the normal `PATH=/user` command directory.

### 11.3.7 When init terminates
[\[↑ TOC\]](#contents)

PID 1 has no special signal protection. [`kill`](user/kill.picoc) can terminate init,
immediately or at dispatch if it is current.

Init has no parent, so termination removes it immediately. Kernel cleanup
releases its resources even though killing bypasses userspace cleanup.
Shared data still follows the unlink and reference-count rules.

Children become parentless and receive their configured parent-death signal.
The shell sets [`SIGKILL`](common/signal.header#L5), and applications inherit it, so termination
normally propagates. Children that change the setting can survive, and
a shell killed before setting it can behave differently.

The kernel does not restart init or its shell loop. Survivors can continue.
If init returns on startup failure, [`exit_process()`](kernel/process/process.picoc#L430) halts when no
processes remain.

Signal-driven final-process removal has a dispatcher limitation. If
[`prepare_process_termination()`](kernel/signal.picoc#L126) removes the last candidate, [`next_process`](kernel/dispatcher.picoc#L56)
can still point to its freed PCB and reach restoration. Killing the whole
init tree therefore does not guarantee clean shutdown. There is no
special PID-1 panic or reboot policy.

# 12. Shell
[\[↑ TOC\]](#contents)

The shell turns terminal input into commands and process operations. It is
one of **18 user applications**, alongside 17 standalone commands. This
chapter follows its state, input handling, parsing, job control, and I/O.

## 12.1 Shell-owned state
[\[↑ TOC\]](#contents)

The shell keeps command history, input retained for later commands, and
pipeline scratch buffers in its image's `.data`. These globals survive
between commands without occupying the User Process Stack:

| Global | Meaning and storage |
| --- | --- |
| [`last_command_exit_status`](user/shell.picoc#L29) | One integer used for `$?` |
| [`last_background_process_id`](user/shell.picoc#L30) | Most recently tracked background/stopped PID used for `$!`, `fg`, and `bg` |
| [`shell_executable_path`](user/shell.picoc#L31) | Embedded scratch buffer for one `PATH` candidate |
| [`shell_pipe_left_command`](user/shell.picoc#L32), [`shell_pipe_right_command`](user/shell.picoc#L33), [`shell_pipe_path`](user/shell.picoc#L34) | Embedded command and temporary-path storage for one two-command pipeline |
| [`command_history`](user/shell.picoc#L36) | Embedded ring containing at most eight recent commands, only consecutive duplicates are suppressed |
| [`command_history_draft`](user/shell.picoc#L39) | Current unfinished line preserved while navigating history |
| [`shell_line_erase_sequence`](user/shell.picoc#L41) | Embedded scratch array holding one batched terminal erase sequence |
| [`shell_input_buffer`](user/shell.picoc#L42) | Up to 128 input bytes retained across command lines so one [`read()`](library/unistd/io.picoc#L6) can drain the kernel terminal ring |
| [`command_history_start`](user/shell.picoc#L43), [`command_history_count`](user/shell.picoc#L44) | History ring indices/count |
| [`shell_input_index`](user/shell.picoc#L45), [`shell_input_count`](user/shell.picoc#L46) | Next retained input byte and number of valid bytes in [`shell_input_buffer`](user/shell.picoc#L42) |

The current [`command`](user/shell.picoc#L1449) is an 80-cell local array in
[`main()`](user/shell.picoc#L1448). The shell's
[`ProcessControlBlock`](kernel/process/process.header#L31),
[`FileDescriptorTable`](kernel/filesystem/file_descriptor.header#L22), and
eight-element [`entries`](kernel/filesystem/file_descriptor.header#L23) array
occupy separate Kernel Heap allocations. Descriptor slots 5–7 save standard
streams during redirection, as described in
[`8.1 Per-process file-descriptor table`](#81-per-process-file-descriptor-table).

The SRAM view below uses the hierarchy from
[`3.2 SRAM image and heap hierarchy`](#32-sram-image-and-heap-hierarchy).
Its upper row locates the kernel terminal buffer and shell metadata. The lower
row expands the shell's Process Payload to show the globals, environment
allocations, and stack locals. Arrows represent stored pointers. Input indices
and counts are integers stored alongside the buffer.

![Wide SRAM layout showing the kernel terminal buffer in kernel .data, shell PCB and descriptor allocations in the Kernel Heap, and the shell Process Payload expanded into its image globals, User Process Heap environment allocations, and stack locals](documentation/images/process-shell-state.svg)

[`process_heap`](library/stdlib/malloc.picoc#L6) and
[`environ`](library/stdlib/env.picoc#L4) are linked-library globals in the shell's
`.data`. [`initialize_environment()`](library/stdlib/env.picoc#L97) allocates
the environment pointer array and copies its strings into separate User Process
Heap blocks. The diagram shows two example blocks. PCB path strings and
descriptor path strings occupy other Kernel Heap blocks.
[`10.2.7.3 Environment operations in env.picoc`](#10273-environment-operations-in-envpicoc)
explains how environment commands update these allocations.

Input passes through three arrays: the kernel's [`Terminal.input_buffer`](kernel/filesystem/terminal.header#L10),
the shell's global [`shell_input_buffer`](user/shell.picoc#L42), and the stack-local [`command`](user/shell.picoc#L1449)
built by [`read_line()`](user/shell.picoc#L271). None is a User Process Heap allocation.

## 12.2 Shell startup and command loop
[\[↑ TOC\]](#contents)

Startup closes descriptors 3–7 but keeps inherited standard streams.
[`set_foreground_process(0)`](library/unistd/process.picoc#L59) gives the shell input ownership without
terminal-generated signals by storing the shell's negative PID in
[`foreground_process_target`](kernel/signal.picoc#L12).
[`12.5.1 Foreground processes, background processes, and job-control signals`](#1251-foreground-processes-background-processes-and-job-control-signals)
explains how the shell later hands ownership to a child and reclaims it.
[`prctl()`](library/sys/prctl/prctl.picoc#L14) selects parent-death [`SIGKILL`](common/signal.header#L5).
The loop reads lines, records history, and evaluates commands. Redirected
stdin works through the same loop, so `shell.bin < commands.txt` executes
lines until EOF.

If one read supplies two lines, [`read_line()`](user/shell.picoc#L271) consumes the first and keeps
the rest for the next prompt. This example shows the read-ahead state:

| Buffer state | Cell 0 | Cell 1 | Cell 2 | Cell 3 | Cell 4 | Cell 5 | Cell 6 | [`shell_input_index`](user/shell.picoc#L45) | [`shell_input_count`](user/shell.picoc#L46) |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| After [`read()`](library/unistd/io.picoc#L6) | `p` | `w` | `d` | `\n` | `l` | `s` | `\n` | 0 | 7 |
| After [`read_line()`](user/shell.picoc#L271) returns `pwd` | `p` | `w` | `d` | `\n` | `l` | `s` | `\n` | 4 | 7 |

Cells 4–6 retain the next command, `ls\n`.

This helper consumes buffered characters before making another read:

```c
int read_shell_character(char *character) {
    if (shell_input_index >= shell_input_count) {
        shell_input_count = read(
            STDIN_FILENO,
            shell_input_buffer,
            SHELL_INPUT_BUFFER_CAPACITY
        );
        shell_input_index = 0;
        if (shell_input_count <= 0) {
            return shell_input_count;
        }
    }

    *character = shell_input_buffer[shell_input_index];
    shell_input_index = shell_input_index + 1;
    return 1;
}
```

The function table below links the main loop’s operations to their library calls and local effects.

| Shell function | Return value / status | Library functions |
| --- | --- | --- |
| [`read_shell_character(character)`](user/shell.picoc#L252) | 1 after returning one byte, 0 at EOF, or the negative [`read()`](library/unistd/io.picoc#L6) error | Refills [`shell_input_buffer`](user/shell.picoc#L42) with one [`read()`](library/unistd/io.picoc#L6) and returns retained bytes one at a time across command lines |
| [`read_line(buffer, capacity)`](user/shell.picoc#L271) | Command length, or `-1` at EOF | Calls [`read_shell_character()`](user/shell.picoc#L252), batches consecutive printable echoes through [`flush_shell_line_echo()`](user/shell.picoc#L240), flushes them before editing controls, edits the stack buffer, and updates history-navigation state |
| [`remember_shell_command(command)`](user/shell.picoc#L147) | No value | [`strcmp()`](library/string/string.picoc#L34) and [`strcpy()`](library/string/string.picoc#L4), mutates the global eight-entry history ring and skips consecutive duplicates |
| [`expand_variables(arguments, result, capacity)`](user/shell.picoc#L466) | Expanded buffer (truncated to capacity minus one), or `NULL` for a null input | Uses [`getenv()`](library/stdlib/env.picoc#L115) and the `$?`/`$!` globals while preserving quotes for argument parsing, expansion also occurs inside single quotes |
| [`load_from_path(name)`](user/shell.picoc#L1186) | Loaded PID, or 0 | Reads `PATH` with [`getenv()`](library/stdlib/env.picoc#L115), builds candidates, and calls [`load()`](library/unistd/process.picoc#L17) in order |
| [`run_process(pid, arguments, background, stdin_path, stdout_path, append_stdout, stderr_path, append_stderr)`](user/shell.picoc#L1034) | `true` when [`run()`](library/unistd/process.picoc#L31) succeeds, otherwise `false` | [`run()`](library/unistd/process.picoc#L31), [`WIFSTOPPED()`](library/sys/wait/wait.picoc#L25), [`open()`](library/fcntl/fcntl.picoc#L5), [`dup2()`](library/unistd/io.picoc#L58), [`close()`](library/unistd/io.picoc#L54), [`set_foreground_process()`](library/unistd/process.picoc#L59), and [`waitpid()`](library/sys/wait/wait.picoc#L14), changes `$?`/`$!` state |
| [`continue_background_process(foreground)`](user/shell.picoc#L1127) | `true` when the tracked process was continued, otherwise `false` | [`kill()`](library/signal/signal.picoc#L14) and, for `fg`, [`set_foreground_process()`](library/unistd/process.picoc#L59) and [`waitpid()`](library/sys/wait/wait.picoc#L14) |
| [`eval(command)`](user/shell.picoc#L1224) | `false` only for `exit`, otherwise `true` | Selects a built-in or external execution path |
| [`main(argc, argv)`](user/shell.picoc#L1448) | Shell exit status | [`prctl()`](library/sys/prctl/prctl.picoc#L14), [`set_foreground_process()`](library/unistd/process.picoc#L59), [`lseek()`](library/unistd/io.picoc#L66), [`unsetenv()`](library/stdlib/env.picoc#L157), [`close()`](library/unistd/io.picoc#L54), [`read_line()`](user/shell.picoc#L271), and [`eval()`](user/shell.picoc#L1224), closes 3–7 at startup and owns the interactive or redirected-input execution path |

## 12.3 Interactive line editing and command history
[\[↑ TOC\]](#contents)

[`read_line()`](user/shell.picoc#L271) interprets editing and history keys in the 80-cell command
buffer, leaving room for 79 characters and a terminator. The table maps
keys to their helpers:

| Input | Shell behavior | Implementation |
| --- | --- | --- |
| Line feed or carriage return | Echo one newline and finish the command | [`read_line()`](user/shell.picoc#L271) calls [`shell_write_character()`](user/shell.picoc#L50) and ends its loop |
| Backspace (8) or Delete (127) | Remove one buffered character and erase it visually | [`read_line()`](user/shell.picoc#L271) calls [`erase_shell_line_suffix()`](user/shell.picoc#L125) with `length - 1` |
| `Ctrl+U` (21) | Erase the complete current line | [`read_line()`](user/shell.picoc#L271) calls [`erase_shell_line_suffix()`](user/shell.picoc#L125) with retained length 0 |
| `Ctrl+V` (22) | Ignore the byte because PicoOS has no literal-next-character mode | It matches no [`read_line()`](user/shell.picoc#L271) branch and is below the printable range, so it is not appended |
| `Ctrl+W` (23) | Erase trailing whitespace and the previous word | [`read_line()`](user/shell.picoc#L271) finds the retained prefix, then calls [`erase_shell_line_suffix()`](user/shell.picoc#L125) |
| Up arrow (`ESC [ A` or `ESC O A`) | Move toward older entries in the eight-command history ring | [`read_line()`](user/shell.picoc#L271) decodes the sequence, then calls [`navigate_command_history(..., 1)`](user/shell.picoc#L194) |
| Down arrow (`ESC [ B` or `ESC O B`) | Move toward newer entries and finally restore the draft | [`read_line()`](user/shell.picoc#L271) calls [`navigate_command_history(..., -1)`](user/shell.picoc#L194) |
| Left/right arrows (`ESC [ C/D` or `ESC O C/D`) | Consume the escape sequence but do not move the cursor | [`read_line()`](user/shell.picoc#L271) sets [`process_character`](user/shell.picoc#L281) to `false` without changing the line |
| Tab | Append one space if room remains | [`read_line()`](user/shell.picoc#L271) converts it to a space, then calls [`append_shell_line_character()`](user/shell.picoc#L227) |
| Printable byte | Append it if room remains | [`read_line()`](user/shell.picoc#L271) calls [`append_shell_line_character()`](user/shell.picoc#L227) |

These excerpts distinguish history navigation from ordinary editing:

```c
int read_line(char *buffer, int capacity) {
    // ...
    while (!complete) {
        read_result = read_shell_character(&character);
        if (read_result == 1) {
            // ...
            if (escape_sequence_state == 1) {
                // ...
            } else if (escape_sequence_state == 2) {
                // ...
                if (character == 'A') {
                    length = navigate_command_history(
                        buffer, length, capacity, &history_position, 1
                    );
                    process_character = false;
                } else if (character == 'B') {
                    length = navigate_command_history(
                        buffer, length, capacity, &history_position, -1
                    );
                    process_character = false;
                }
                // ...
            }
            // ...
            if (process_character) {
                if (character == '\n' || character == '\r') {
                    // ...
                } else if (character == '\b' || character == 127) {
                    // ...
                } else if (character == SHELL_CTRL_U) {
                    length = erase_shell_line_suffix(length, 0);
                } else if (character == SHELL_CTRL_W) {
                    // ...
                    length = erase_shell_line_suffix(length, retained_length);
                }
                // ...
            }
            // ...
        }
        // ...
    }
    // ...
}
```

`Ctrl+C` and `Ctrl+Z` are consumed by the UART signal handler before
reaching the editable line. [`12.5.1 Foreground processes, background processes, and job-control signals`](#1251-foreground-processes-background-processes-and-job-control-signals) follows their foreground effects.

[`read_shell_character()`](user/shell.picoc#L252) can refill 128 cells in one read, keeping bytes
after a newline for the next command. [`read_line()`](user/shell.picoc#L271) batches printable
echoes and flushes before editing controls. Its helpers use
[`write_without_uart_escape_check()`](library/unistd/io.picoc#L43) only for known escape-free output.
This reduces syscalls and repeated scans when input has accumulated.

## 12.4 Command parsing, expansion, and execution
[\[↑ TOC\]](#contents)

Parsing checks balanced quotes and one unquoted `|`. For external commands
and the [`run` built-in](user/shell.picoc#L1224), it removes a trailing `&` and final redirections before separating
the command from its arguments. [`run_process()`](user/shell.picoc#L1034) expands `$NAME`, `$?`, and
`$!` in arguments. Names and redirection paths are not expanded. Names
containing `/` load directly, while others use colon-separated `PATH`.

With `NAME=Ada` and `$? = 0`, this trace shows in-place parsing. Returned
pointers refer into the same command array:

| Stage | Result | What changed |
| --- | --- | --- |
| Input | `echo.bin "hello $NAME ($?)" > result.txt &` | Nothing yet |
| [`strip_background_operator()`](user/shell.picoc#L804) | `echo.bin "hello $NAME ($?)" > result.txt` and [`background`](user/shell.picoc#L1236) set to `true` | Removed only the trailing `&` and adjacent whitespace |
| [`strip_command_redirections()`](user/shell.picoc#L926) | Command prefix `echo.bin "hello $NAME ($?)"`<br>[`stdout_path`](user/shell.picoc#L1228) points at `result.txt` | Parsed the final `>` suffix and terminated the command before it. The path is not expanded |
| [`command_arguments()`](user/shell.picoc#L426) | Name `echo.bin`<br>Raw arguments `"hello $NAME ($?)"` | Replaced the separator after the name with `\0` and returned a pointer to the remainder |
| [`load_from_path()`](user/shell.picoc#L1186) | Loaded `/user/echo.bin`, returning a [`NEW`](kernel/process/process.header#L12) PID | Used `PATH`. This step does **not** copy descriptors |
| [`expand_variables()`](user/shell.picoc#L466) | `"hello Ada (0)"` | Replaced `$NAME` and `$?`, deliberately retaining quote bytes |
| [`run()`](library/unistd/process.picoc#L31) | Child [`argv[1]`](kernel/process/process_arguments.picoc#L200) is `hello Ada (0)` | Kernel run setup removed matching quotes while building [`argv`](kernel/process/process_arguments.picoc#L140), inherited the temporarily redirected descriptors, and made the child [`READY`](kernel/process/process.header#L13) |

Unlike a conventional shell, expansion does not track quotes.
`echo.bin '$NAME'` still expands to `Ada`. Quotes preserve whitespace
within an argument and are removed during kernel run setup. There is no
general backslash escape pass.

The configured `PATH=/user` uses the PicoOS root, so commands remain discoverable after `cd`
and from nested shells. A relative entry supplied by the user is resolved from the shell's current
[`ProcessControlBlock.working_directory`](kernel/process/process.header#L39), just like other relative paths.

Built-ins execute in the shell. External commands use [`load_from_path()`](user/shell.picoc#L1186)
and [`run_process()`](user/shell.picoc#L1034) to load, expand, redirect, and start. [`4.2.1 Loading a process (load library call)`](#421-loading-a-process-load-library-call) explains
transfer, and [`12.5.1 Foreground processes, background processes, and job-control signals`](#1251-foreground-processes-background-processes-and-job-control-signals) explains foreground waiting.

Background execution skips terminal transfer and waiting. The shell
restores its descriptors, records the PID in `$!`, and returns to the prompt.

[`echo.bin`](user/echo.picoc#L20) interprets `\n` itself. It is not a shell escape rule.

## 12.5 Shell built-in commands
[\[↑ TOC\]](#contents)

The **9 built-ins** run inside the shell. This lets `cd` and `export` change
its own directory and environment. A child could change only its copies:

| Built-in | Behavior | Library functions / host requests |
| --- | --- | --- |
| `exit` | Accepts no argument and returns false from [`eval()`](user/shell.picoc#L1224), ending this shell session | No immediate syscall, [`libstart`](library/start/libstart.picoc) later calls [`exit(main_result)`](library/stdlib/exit.picoc#L3) |
| `eval COMMAND` | Recursively evaluates the remaining text in the same shell state | Re-enters [`eval()`](user/shell.picoc#L1224), resulting command calls apply normally |
| `export NAME=value` | Expands the complete assignment and stores/replaces the variable | [`getenv`](library/stdlib/env.picoc#L115) during expansion and [`setenv(..., true)`](library/stdlib/env.picoc#L126) |
| `cd DIRECTORY` | Changes this shell PCB's working-directory string after host validation | [`chdir()`](library/unistd/working_directory.picoc#L4)<br>**Host request:** `is-directory <absolute-path>` |
| `load PATH` | Loads a binary but leaves its PCB in [`NEW`](kernel/process/process.header#L12) | [`load()`](library/unistd/process.picoc#L17)<br>**Host requests:** `file-size <path>`, then `read-range <offset> <count> <path>` for the header and executable payload |
| `run PID [ARGUMENTS]` | Starts a previously loaded PCB, supports `&`, `<`, `>`, `>>`, `2>`, and `2>>` | [`run()`](library/unistd/process.picoc#L31), and possibly [`open()`](library/fcntl/fcntl.picoc#L5)/[`dup2()`](library/unistd/io.picoc#L58)/[`close()`](library/unistd/io.picoc#L54), [`set_foreground_process()`](library/unistd/process.picoc#L59), [`waitpid()`](library/sys/wait/wait.picoc#L14)<br>**Host requests when opening redirections:** `file-size <path>` for input/append existence checks, or `write <path>` followed by `write stdout` to create/truncate output |
| `unload PID` | Terminates/removes the selected non-current process | [`unload()`](library/unistd/process.picoc#L47) |
| `fg` | Makes the most recently tracked PID foreground, sends [`SIGCONT`](common/signal.header#L6), and waits | [`set_foreground_process`](library/unistd/process.picoc#L59), [`kill`](library/signal/signal.picoc#L14), [`waitpid`](library/sys/wait/wait.picoc#L14) |
| `bg` | Sends [`SIGCONT`](common/signal.header#L6) to the most recently tracked PID without waiting | [`kill()`](library/signal/signal.picoc#L14) |

Built-ins check required operands. `exit`, `fg`, and `bg` reject extras,
and `cd` requires one directory or help argument. [`load`](user/shell.picoc#L1224) takes the remaining
path text, while [`run`](user/shell.picoc#L1224) accepts arguments after its PID. Bare `NAME=value`
is treated as an external command, and there is no `unset` built-in.

### 12.5.1 Foreground processes, background processes, and job-control signals
[\[↑ TOC\]](#contents)

Foreground execution gives the child terminal ownership and waits for its
exact PID. The shell then reclaims input and stores the returned status
in `$?`. A stopped child becomes the tracked `$!` target for `fg` or `bg`.

The SRAM view shows `fg` resuming tracked child PID 2 while shell PID 1
waits. [`foreground_process_target`](kernel/signal.picoc#L12) lives in kernel
`.data`. [`last_background_process_id`](user/shell.picoc#L30) and
[`last_command_exit_status`](user/shell.picoc#L29) live in the shell's `.data`.
All three are integers. The dashed arrow shows a PID lookup, while solid
arrows show each PCB's [`base_address`](kernel/process/process.header#L34)
reaching its allocated Process Payload. The bottom comparison shows how
ownership controls terminal input and signals.

![SRAM allocation and address links for shell and child, inline job-control PIDs and status, and foreground versus background terminal signals](documentation/images/process-job-control.svg)

The shell's `$?` still holds the previous result during this wait.
[`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid)
explains the queue and stack-result pointers omitted from this overview.

This excerpt shows descriptor restoration before ownership transfer,
followed by waiting and ownership reset:

```c
bool run_process(
    int pid,
    char *arguments,
    bool background,
    char *stdin_path,
    char *stdout_path,
    bool append_stdout,
    char *stderr_path,
    bool append_stderr
) {
    // ...
    started = run(pid, expand_variables(
                           arguments,
                           expanded_arguments,
                           SHELL_COMMAND_BUFFER_CAPACITY),
                  NULL);
    restore_standard_descriptors(
        stdin_redirected, stdout_redirected, stderr_redirected
    );

    if (!started) {
        shell_write_error_string("error: could not start process\n");
    } else if (background) {
        last_background_process_id = pid;
    } else {
        set_foreground_process(pid);
        last_command_exit_status = waitpid(pid);
        set_foreground_process(0);
        // ...
    }
    return started;
}
```

The shell changes the kernel's [`foreground_process_target`](kernel/signal.picoc#L12)
through the library call [`set_foreground_process()`](library/unistd/process.picoc#L59).
Passing a positive PID stores that PID after the kernel verifies that it names
an existing direct child. Passing `0` means “give input ownership to the calling
process”: the kernel stores `-current_process()->pid`, which is the shell's
negative PID for these calls. The zero argument does not store zero or select
PID 0. The kernel implementation is:

```c
int set_foreground_process(int pid) {
    struct ProcessControlBlock *process;

    if (pid == 0) {
        foreground_process_target = -current_process()->pid;
        return 0;
    }

    process = find_process_by_pid(pid);
    if (process == NULL ||
        process->parent_pid != current_process()->pid) {
        return -1;
    }

    foreground_process_target = pid;
    return 0;
}
```

The negative value keeps shell input ownership while suppressing terminal
signals. At startup, [`main()`](user/shell.picoc#L1448) also calls
`set_foreground_process(0)` to establish this ownership before reading commands.
For a new foreground command, [`run_process()`](user/shell.picoc#L1034) sets the
child PID, waits, and restores shell ownership after `waitpid()` reports either
termination or a stop. For `fg`,
[`continue_background_process()`](user/shell.picoc#L1127) sets the child PID before
sending `SIGCONT`, then waits and calls `set_foreground_process(0)`; it also
restores shell ownership if sending `SIGCONT` fails. `bg` and commands started
with `&` leave ownership unchanged and do not wait.

`$!` remembers one background or stopped PID. Several jobs may exist, but
there is no job table. Successful external background starts leave `$?`
unchanged, while `run PID &` sets it to zero. Failures set it to one.
Background completion does not update these values asynchronously.

Redirection is copied during [`run()`](library/unistd/process.picoc#L31) before the shell restores itself,
so a background child keeps its files afterward. A terminal read by a
background child receives [`SIGTTIN`](common/signal.header#L9). File input needs no terminal ownership.

Every child has an independent descriptor table. Later commands cannot
overwrite an earlier child's redirection. Background exits become zombies
until collected, unloaded, or removed as orphans. The shell does not
automatically wait for them.

The library can collect an exact PID with [`waitpid()`](library/sys/wait/wait.picoc#L14), but the shell has
no `wait` built-in. `fg` handles the tracked running or stopped process.
For a zombie, its preceding [`SIGCONT`](common/signal.header#L6) fails, so it does not collect that
status. Older PIDs replaced in `$!` are also unavailable to `fg`. Their
zombies remain until explicit unloading or shell termination.

For a stopped reader, `fg` assigns ownership before continuing its pending
read. [`8.4 Foreground input ownership and terminal-generated signals`](#84-foreground-input-ownership-and-terminal-generated-signals) shows the buffer and queue changes. Children normally inherit
the shell's parent-death [`SIGKILL`](common/signal.header#L5), allowing termination to propagate.

## 12.6 Input/output redirection
[\[↑ TOC\]](#contents)

A conventional Unix shell uses `fork()`, redirects the child's descriptors,
and calls `exec()` to replace its image. The parent keeps its own table.

PicoOS has neither process cloning nor image replacement. Its [`load()`](library/unistd/process.picoc#L17)
creates a [`NEW`](kernel/process/process.header#L12) process, and [`run()`](library/unistd/process.picoc#L31) copies caller state before setting
[`READY`](kernel/process/process.header#L13). The shell therefore redirects its own descriptors, starts the
child with that snapshot, and restores itself. Paging is not inherently
required for `fork()`, so its absence alone does not explain this design.

[`dup2()`](library/unistd/io.picoc#L58) deep-copies the path and scalar fields into the target entry.
The source stays unchanged, and offsets evolve independently. Equal
descriptor numbers leave the entry unchanged.

The shell reserves slot 5 for stdin, 6 for stdout, and 7 for stderr.
Ordinary opens use only 0–4. If those are full, redirection fails before
starting the child.

This `COMMAND > OUT` trace shows complete descriptor entries and their
own path copies, rather than Unix shared open-file descriptions. `T-in`,
`T-out`, and `T-err` label the terminal streams:

| Descriptor | 1. Initial shell | 2. After opening `OUT` as 3, then saving 1 as 6 | 3. After installing 3 as 1 and closing 3 | 4. Child after run setup | 5. Shell after restoring 6 as 1 and closing 6 |
| ---: | --- | --- | --- | --- | --- |
| 0 | `T-in` | `T-in` | `T-in` | independent `T-in` copy | `T-in` |
| 1 | `T-out` | `T-out` | `OUT` | independent `OUT` copy | `T-out` |
| 2 | `T-err` | `T-err` | `T-err` | independent `T-err` copy | `T-err` |
| 3 | free | `OUT` opened here | free | free | free |
| 4 | free | free | free | free | free |
| 5 | free | free | free | free because inheritance never examines it | free |
| 6 | free | saved `T-out` copy | saved `T-out` copy | free because inheritance never examines it | free |
| 7 | free | free | free | free because inheritance never examines it | free |

In step 2, [`open()`](library/fcntl/fcntl.picoc#L5) opens `OUT` as descriptor 3 before
[`dup2(1, 6)`](library/unistd/io.picoc#L58) saves stdout. If opening fails, the shell's
descriptor table remains unchanged:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    OUT["OUT"] -->|"open()"| S3["shell fd 3: OUT"]
    S1["shell fd 1: T-out"] -->|"dup2(1, 6)"| S6["shell fd 6: saved T-out"]
```

In step 3, [`dup2(3, 1)`](library/unistd/io.picoc#L58) installs an independent copy of
`OUT` as stdout. [`close(3)`](library/unistd/io.picoc#L54) then frees the temporary entry.
Descriptor 6 keeps the saved terminal output for later restoration:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    O3["shell fd 3: OUT"] -->|"dup2(3, 1)"| O1["shell fd 1: OUT"]
    O3 -->|"close(3)"| OF["shell fd 3: free"]
    O6["shell fd 6: saved T-out"]
```

In step 4, [`run()`](library/unistd/process.picoc#L31) gives the child a separate
[`FileDescriptorTable`](kernel/filesystem/file_descriptor.header#L22), reached through its
PCB's [`file_descriptors`](kernel/process/process.header#L42) pointer.
[`inherit_file_descriptors()`](kernel/filesystem/file_descriptor.picoc#L99) always copies
0–2, copies only [`FILE`](kernel/filesystem/file_descriptor.header#L13) entries in 3–4,
and never examines 5–7. The diagram follows stdout and its saved copy:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    ST["PCB 1 · shell<br/>fd 1: OUT<br/>fd 6: saved T-out"]
    CT["PCB 2 · child<br/>fd 1: OUT copy<br/>fd 6: free"]
    ST -->|"run(): independent copies"| CT
```

In step 5, [`restore_standard_descriptors()`](user/shell.picoc#L966) copies the saved
stdout back with [`dup2(6, 1)`](library/unistd/io.picoc#L58) and then calls
[`close(6)`](library/unistd/io.picoc#L54). The child's descriptor 1 still names `OUT`,
because its entry and path were copied independently:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    R6["shell fd 6: saved T-out"] -->|"dup2(6, 1)"| R1["shell fd 1: T-out"]
    R1 -->|"close(6)"| RF["shell fd 6: free"]
    C1["child fd 1: OUT<br/>unchanged"]
```

Descriptor inheritance happens in run setup, before the child is scheduled:

```c
bool mark_process_ready_with_arguments(struct RunProcessRequest *request) {
    struct ProcessControlBlock *process;
    struct FileDescriptorTable *file_descriptors;

    process = find_process_by_pid(request->pid);
    if (process == NULL || process->state != PROCESS_STATE_NEW) {
        return false;
    }
    if (current_process() != NULL) {
        file_descriptors = inherit_file_descriptors(
            current_process()->file_descriptors
        );
        destroy_file_descriptor_table(process->file_descriptors);
        process->file_descriptors = file_descriptors;
    }

    store_process_arguments(process, request->arguments, request->environment);
    process->state = PROCESS_STATE_READY;
    return true;
}
```

The copy examines only 0–4 and skips saved originals in 5–7. [`8.1 Per-process file-descriptor table`](#81-per-process-file-descriptor-table) gives
the full inheritance rule.

The table follows each redirection. Startup has already closed 3–7,
including in a nested shell:

| Shell form | Opens/creates | Copies and replacements before [`run()`](library/unistd/process.picoc#L31) | Child endpoints and shell cleanup |
| --- | --- | --- | --- |
| `COMMAND` | None | None | Child receives independent copies of 0–2 and opened-file entries in 3–4 |
| `COMMAND < IN` | Save 0 in reserved slot 5, close 0, then [`open(IN, O_RDONLY)`](library/fcntl/fcntl.picoc#L5) must return 0 | [`dup2(0, 5)`](library/unistd/io.picoc#L58) saves current stdin | Child reads `IN` on 0 but does not inherit slot 5, shell restores 5 to 0, then closes 5 |
| `COMMAND > OUT` | [`open(OUT, O_WRONLY \| O_CREAT \| O_TRUNC)`](library/fcntl/fcntl.picoc#L5), normally temporary slot 3 | [`dup2(1, 6)`](library/unistd/io.picoc#L58) saves stdout, [`dup2(temporary, 1)`](library/unistd/io.picoc#L58) installs `OUT`, close temporary | Child writes `OUT` on 1 but does not inherit slot 6, shell restores 6 to 1, then closes 6 |
| `COMMAND >> OUT` | Same, with [`O_APPEND`](common/file.header#L15) instead of [`O_TRUNC`](common/file.header#L14) | Same stdout operations | Each child write appends using a `file-size` request |
| `COMMAND 2> ERR` / `2>> ERR` | Open with the corresponding truncate/append flags | [`dup2(2, 7)`](library/unistd/io.picoc#L58) saves stderr, [`dup2(temporary, 2)`](library/unistd/io.picoc#L58) installs `ERR`, close temporary | Child writes `ERR` on 2 but does not inherit slot 7, shell restores 7 to 2, then closes 7 |
| `COMMAND < IN > OUT 2> ERR` | Perform stdout, stderr, then stdin setup, append variants may replace either output operator | Combines the operations above, using reserved slots 5, 6, and 7 | Child receives all redirected 0/1/2 endpoints but none of the saved originals, shell restores and closes every used save slot after [`run()`](library/unistd/process.picoc#L31) |
| `LEFT \| RIGHT` | Create `.picoos-pipe-PID.tmp` through `LEFT > temporary`, then open it through `RIGHT < temporary` | Uses stdout save slot 6 for `LEFT` and stdin save slot 5 for `RIGHT`, no pipe descriptor kind exists | `LEFT` writes the host-backed file and exits before `RIGHT` reads it, each command's shell descriptors are restored, then the shell unlinks the temporary path |

Combined operators must appear in input, stdout, stderr order. Parsing
removes them in reverse because each must be the current command suffix.

Temporary output descriptors close before [`run()`](library/unistd/process.picoc#L31). Saved originals remain
until restoration, then close before foreground waiting. The child's
independent copies survive. UART destination selection happens for each
write in the kernel, as explained in [`8.8 Opening, reading, writing, and seeking`](#88-opening-reading-writing-and-seeking).

`cat.bin < input.txt` uses cat's ordinary stdin behavior.
`shell.bin < commands.txt` similarly reads commands until EOF. A nested
shell retains redirected 0–2 while closing 3–7. Device targets use the
behavior described in [`8.5 Virtual terminal and null-device paths`](#85-virtual-terminal-and-null-device-paths).

For `program > file.txt`, [`redirect_output()`](user/shell.picoc#L1003) saves stdout in slot 6
and installs a truncating output descriptor. These lines show rollback
on partial failure:

```c
bool redirect_output(
    int target_file_descriptor,
    int saved_file_descriptor,
    char *path,
    bool append
) {
    // ...
    opened_file_descriptor = open(path, flags);
    if (opened_file_descriptor < 0) {
        return false;
    }
    if (dup2(target_file_descriptor, saved_file_descriptor) < 0) {
        close(opened_file_descriptor);
        return false;
    }
    if (dup2(opened_file_descriptor, target_file_descriptor) < 0) {
        close(opened_file_descriptor);
        close(saved_file_descriptor);
        return false;
    }
    close(opened_file_descriptor);
    return true;
}
```

`>>` selects [`O_APPEND`](common/file.header#L15), while `>` selects [`O_TRUNC`](common/file.header#L14). Stderr uses the
same helper with target 2 and save slot 7. Append checks file size for
each write.

Input redirection saves stdin in slot 5, closes slot 0, and relies on
lowest-free allocation to reopen the input there:

```c
bool redirect_standard_input(char *path) {
    int file_descriptor;

    if (dup2(STDIN_FILENO, SHELL_SAVED_STDIN_FILENO) < 0) {
        return false;
    }
    close(STDIN_FILENO);
    file_descriptor = open(path, O_RDONLY);
    if (file_descriptor != STDIN_FILENO) {
        if (file_descriptor >= 0) {
            close(file_descriptor);
        }
        restore_standard_descriptors(true, false, false);
        return false;
    }
    return true;
}
```

The child's copies also preserve background redirection after shell
restoration. [`12.5.1 Foreground processes, background processes, and job-control signals`](#1251-foreground-processes-background-processes-and-job-control-signals) covers background status. Operators can combine,
for example `sed.bin "5iNEW" < input.txt > output.txt 2> str_err_file.txt`.

## 12.7 Sequential file-backed pipelines
[\[↑ TOC\]](#contents)

PicoOS supports one pipeline operator using a temporary host file. The
producer finishes before the consumer starts.

[`run_pipeline()`](user/shell.picoc#L762) stores the temporary path
`.picoos-pipe-<shell PID>.tmp` in
[`shell_pipe_path`](user/shell.picoc#L34). The file is created in the current
directory. It adds output redirection to the left command in
[`shell_pipe_left_command`](user/shell.picoc#L32) and input redirection to
the right in [`shell_pipe_right_command`](user/shell.picoc#L33). The code
shows how these buffers pass through execution and temporary-file removal:

```c
bool run_pipeline(char *command, int pipeline) {
    // ...
    build_shell_pipe_path();
    if (!insert_redirection(
            command,
            ">",
            shell_pipe_path,
            strlen(command),
            shell_pipe_left_command
        ) || !insert_redirection(
            right_command,
            "<",
            shell_pipe_path,
            find_output_redirection(right_command),
            shell_pipe_right_command
        )) {
        shell_write_error_string("error: pipeline is too long\n");
        last_command_exit_status = 1;
        return true;
    }

    eval(shell_pipe_left_command);
    evaluating = eval(shell_pipe_right_command);
    unlink(shell_pipe_path);
    return evaluating;
}
```

For `LEFT | RIGHT > OUT`, the diagram follows `LEFT > TMP` across the
producer row, then `RIGHT < TMP > OUT` across the consumer row. It shows
how each child's descriptors remain redirected while the shell restores
its own descriptors before waiting. The snapshots show
[`FileDescriptorTable.entries`](kernel/filesystem/file_descriptor.header#L23),
reached through each process's
[`ProcessControlBlock.file_descriptors`](kernel/process/process.header#L42).

Here `TMP` is the generated temporary path and `OUT` is the requested
output file. `T-in`, `T-out`, and `T-err` are the shell's original terminal
endpoints in slots 0, 1, and 2. Slots 3–7 are initially free. The numbered
steps show successful redirection and foreground execution.

![Two horizontal stages showing pipeline redirection, child descriptor inheritance, shell restoration, waiting, and temporary-file removal](documentation/images/process-pipeline.svg)

The producer's [`waitpid()`](library/sys/wait/wait.picoc#L14) separates the two stages. Each child inherits
its final endpoints, and the shell restores itself before waiting.

The left [`eval()`](user/shell.picoc#L1224) creates or truncates the file and waits for the producer.
The right opens it as stdin and waits for the consumer. Then [`unlink()`](library/unistd/file_removal.picoc#L4)
removes it. The two descriptors use the same path without a kernel pipe.
An existing file with that generated name is also truncated and removed.

Finite pipelines such as `cat.bin file.txt | sed.bin "5aNEW" > file2.txt`
work. Longer pipelines and `&` combinations are unsupported. A background
consumer can lose its input pathname on unlink, and a background producer
can expose partial output.

A conventional pipe has a bounded kernel buffer and concurrent processes.
Empty reads and full writes block, with EOF after the last writer closes.
That provides backpressure and streaming. PicoOS instead stores the whole
producer result before starting the consumer, so it cannot support
unbounded or interactive streams.

The file-backed design reuses [`open()`](library/fcntl/fcntl.picoc#L5), redirection, [`waitpid()`](library/sys/wait/wait.picoc#L14), and
[`unlink()`](library/unistd/file_removal.picoc#L4). A kernel pipe would need shared endpoint state, a buffer,
reader/writer queues, EOF rules, and concurrent startup. These are visible
tradeoffs. The source does not record the historical reason for the choice.

This session creates input, runs one pipeline, displays the result, and
removes the files. Use a writable directory. The shell removes its temporary
file:

```console
PicoOS> echo.bin "first\nsecond" > pipeline-input.txt
PicoOS> cat.bin pipeline-input.txt | sed.bin "1aINSERTED" > pipeline-output.txt
PicoOS> cat.bin pipeline-output.txt
PicoOS> rm.bin pipeline-input.txt pipeline-output.txt
```

# 13. User applications and commands
[\[↑ TOC\]](#contents)

[`user/`](user/) contains **18 applications**, the shell and 17 standalone commands.
Init lives separately in [`system/`](system/). Applications normally change only
their own environment, directory, and descriptors. This chapter first shows
how to write and build a user application, then lists commands, options,
and error behavior.

## 13.1 Writing a simple user application
[\[↑ TOC\]](#contents)

A user application includes library headers and defines its program in
`main`. This example starts the existing [`ls.bin`](user/ls.picoc) command
as a child process to list the current directory, waits for it to finish,
and returns its exit status. Save the following code as `list_directory.picoc`
in [`user/`](user/):

```c
#include "../library/unistd/unistd.header"
#include "../library/sys/wait/wait.header"

int main(void) {
    int pid = load("/user/ls.bin");

    if (pid == 0) {
        return 1;
    }
    if (!run(pid, NULL, NULL)) {
        unload(pid);
        return 1;
    }
    return waitpid(pid);
}
```

[`load()`](library/unistd/process.picoc#L17) loads the binary and creates a
child [`ProcessControlBlock`](kernel/process/process.header#L31), with
[`parent_pid`](kernel/process/process.header#L57) set to the caller's PID and
[`state`](kernel/process/process.header#L33) set to
[`NEW`](kernel/process/process.header#L12). It returns the child PID or `0`
on failure. [`run()`](library/unistd/process.picoc#L31) sets the child's state
to [`READY`](kernel/process/process.header#L13) so the scheduler can select it.
The two `NULL` arguments mean no command arguments and inheritance of the
parent's environment. If starting fails, [`unload()`](library/unistd/process.picoc#L47)
removes the child that was loaded.

[`waitpid(pid)`](library/sys/wait/wait.picoc#L14) waits on this child's
[`waiters`](kernel/process/process.header#L46) queue if it has not yet terminated,
then collects its termination status and releases its remaining process
resources. Here, that status becomes the application's return value.
[`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid)
also explains status delivery when a child is stopped by a signal.

From the repository root, compile the source and its libraries into
`binary/user/list_directory.reti`, then assemble it into
`binary/user/list_directory.bin`:

```console
$ mkdir -p binary/user
$ picoc_compiler --direct-source-link -O1 -s \
    user/list_directory.picoc library/unistd/libunistd.picoc \
    library/sys/wait/libwait.picoc library/stdlib/libstdlib.picoc \
    -C library/start/libstart.picoc -o binary/user/list_directory.reti
$ reti_emulator -a binary/user/list_directory.reti
```

`--direct-source-link` compiles and links the listed sources in one step.
The headers declare the library functions, while the `.picoc` library
sources provide their implementations. `-C` selects
[`libstart`](library/start/libstart.picoc), which initializes the process
heap and environment and calls [`exit()`](library/stdlib/exit.picoc#L3)
with the return value from `main`. The compiler also writes the `.sections`
file that `reti_emulator -a` uses to create the loadable `.bin` file.

With PicoOS running from [`binary/`](binary/), invoke the application at the
shell prompt. The shell finds the new binary in `/user`:

```console
PicoOS> list_directory.bin
```

## 13.2 Applications, library calls, and host requests
[\[↑ TOC\]](#contents)

The table links each entry point and identifies its library calls and host
requests. [`10.2 Library overview and dependencies`](#102-library-overview-and-dependencies) lists the 15 libraries, and [`2.4.2.2.1 System-call groups`](#24221-system-call-groups) groups the 37 syscalls.
Loading the command itself is the parent shell's operation:

**Shared output requests** mean the descriptor routing from [`8.8 Opening, reading, writing, and seeking`](#88-opening-reading-writing-and-seeking). Regular
files use `write-at` and restore stdout, with `file-size` for append. Terminal
stderr selects and restores its destination. Data containing an escape
byte uses `literal-output`. Terminal stdout and null output need no
destination request.

| Binary (source link) | Behavior | Library functions / Host Requests |
| --- | --- | --- |
| [`shell.bin`](user/shell.picoc#L1448) | Interactive command interpreter that can read newline-separated commands from redirected stdin | [`read()`](library/unistd/io.picoc#L6), [`write_without_uart_escape_check()`](library/unistd/io.picoc#L43), [`lseek()`](library/unistd/io.picoc#L66), [`load()`](library/unistd/process.picoc#L17), [`run()`](library/unistd/process.picoc#L31), [`waitpid()`](library/sys/wait/wait.picoc#L14), [`kill()`](library/signal/signal.picoc#L14), [`prctl()`](library/sys/prctl/prctl.picoc#L14), [`getenv()`](library/stdlib/env.picoc#L115), [`setenv()`](library/stdlib/env.picoc#L126), [`strlen()`](library/string/string.picoc#L60), [`open()`](library/fcntl/fcntl.picoc#L5), [`dup2()`](library/unistd/io.picoc#L58), [`close()`](library/unistd/io.picoc#L54), [`unlink()`](library/unistd/file_removal.picoc#L4), [`chdir()`](library/unistd/working_directory.picoc#L4), [`getcwd()`](library/unistd/working_directory.picoc#L11). See [`12. Shell`](#12-shell) for the other calls<br>**Host Requests:** `file-size <path>` and `read-range <offset> <count> <path>` for process loading and regular-file stdin<br>`write <path>` then `write stdout` when creating/truncating redirected output<br>`is-directory <path>` for `cd`<br>`unlink <path>` for the pipeline file<br>Shared output requests when its own descriptors require them |
| [`echo.bin`](user/echo.picoc#L20) | Prints [`argv[1..]`](user/echo.picoc#L20) separated by spaces, converts `\n` inside an argument, and adds a newline | [`printf()`](library/stdio/stdio.picoc#L354)<br>**Host Requests:** shared output requests only |
| [`count.bin`](user/count.picoc#L20) | Counts forever with an optional busy-loop delay and yields after each displayed value | [`printf()`](library/stdio/stdio.picoc#L354), [`atoi()`](library/stdlib/atoi.picoc#L4), [`yield()`](library/schedule/schedule.picoc#L4)<br>**Host Requests:** shared output requests only |
| [`cat.bin`](user/cat.picoc#L136) | Copies named files or stdin to stdout, terminal stdin supports line editing | [`open()`](library/fcntl/fcntl.picoc#L5), [`read()`](library/unistd/io.picoc#L6), [`write()`](library/unistd/io.picoc#L32), [`lseek()`](library/unistd/io.picoc#L66), [`close()`](library/unistd/io.picoc#L54), [`unsetenv()`](library/stdlib/env.picoc#L157)<br>**Host Requests:** `file-size <path>` on named-file open, `read-range <offset> <count> <path>` for regular input, plus shared output requests |
| [`touch.bin`](user/touch.picoc#L11) | Creates each named file or updates its timestamps while preserving contents | [`touch()`](library/unistd/file_removal.picoc#L20)<br>**Host Request:** `touch <path>`<br>Shared output requests only for help/diagnostics |
| [`cp.bin`](user/cp.picoc#L16) | Copies one file to another in 64-cell chunks | [`open()`](library/fcntl/fcntl.picoc#L5), [`read()`](library/unistd/io.picoc#L6), [`write()`](library/unistd/io.picoc#L32), [`close()`](library/unistd/io.picoc#L54), [`unsetenv()`](library/stdlib/env.picoc#L157)<br>**Host Requests:** source `file-size <path>` and `read-range <offset> <count> <path>`<br>Destination `write <path>`, `write stdout`, then `write-at <offset> <path>` and `write stdout`<br>Shared output requests for diagnostics |
| [`mv.bin`](user/mv.picoc#L11) | Moves or renames one file or directory | [`move()`](library/unistd/file_removal.picoc#L12)<br>**Host Request:** `move <old path>\n<new path>`<br>Shared output requests for help/diagnostics |
| [`sed.bin`](user/sed.picoc#L67) | Reads stdin and inserts, changes, appends, or substitutes text at selected lines | [`lseek()`](library/unistd/io.picoc#L66), [`read()`](library/unistd/io.picoc#L6), [`write()`](library/unistd/io.picoc#L32), [`malloc()`](library/stdlib/malloc.picoc#L35), [`free()`](library/stdlib/malloc.picoc#L49), [`unsetenv()`](library/stdlib/env.picoc#L157)<br>**Host Requests:** `file-size <path>` for its [`SEEK_END`](common/file.header#L19), `read-range <offset> <count> <path>` for regular stdin, plus shared output requests |
| [`ps.bin`](user/ps.picoc#L11) | Prints every process PID and canonical system-relative binary path | [`list_processes()`](library/unistd/process.picoc#L51)<br>**Host Requests:** shared output requests only |
| [`ls.bin`](user/ls.picoc#L13) | Lists `.` or one directory, hides dot entries by default, and supports `-a` | [`opendir()`](library/dirent/dirent.picoc#L8), [`readdir()`](library/dirent/dirent.picoc#L40), [`closedir()`](library/dirent/dirent.picoc#L66)<br>**Host Request:** `ls <path>`<br>Shared output requests |
| [`mkdir.bin`](user/mkdir.picoc#L12) | Creates every supplied directory and reports individual failures | [`mkdir()`](library/sys/stat/stat.picoc#L5)<br>**Host Request:** `mkdir <path>` for each operand<br>Shared output requests for help/diagnostics |
| [`pwd.bin`](user/pwd.picoc#L11) | Prints [`working_directory`](kernel/process/process.header#L39) from the current [`ProcessControlBlock`](kernel/process/process.header#L31) | [`getcwd()`](library/unistd/working_directory.picoc#L11)<br>**Host Requests:** shared output requests only |
| [`rm.bin`](user/rm.picoc#L11) | Removes every supplied file and continues after errors | [`unlink()`](library/unistd/file_removal.picoc#L4)<br>**Host Request:** `unlink <path>` for each operand<br>Shared output requests for help/diagnostics |
| [`rmdir.bin`](user/rmdir.picoc#L11) | Removes every supplied empty directory and continues after errors | [`rmdir()`](library/unistd/file_removal.picoc#L8)<br>**Host Request:** `rmdir <path>` for each operand<br>Shared output requests for help/diagnostics |
| [`kill.bin`](user/kill.picoc#L69) | Sends [`SIGKILL`](common/signal.header#L5) by default, a named/numbered signal, or signal 0 as a PID probe | [`kill()`](library/signal/signal.picoc#L14), [`atoi()`](library/stdlib/atoi.picoc#L4), [`yield()`](library/schedule/schedule.picoc#L4)<br>**Host Requests:** none on success<br>Shared output requests for help/diagnostics |
| [`poweroff.bin`](user/poweroff.picoc#L12) | Halts PicoOS | [`reboot(REBOOT_CMD_POWER_OFF)`](library/sys/reboot/reboot.picoc#L5)<br>**Host Requests:** none on shutdown<br>Shared output requests for help/diagnostics |
| [`reboot.bin`](user/reboot.picoc#L12) | Requests a kernel-controlled reboot | [`reboot(REBOOT_CMD_RESTART)`](library/sys/reboot/reboot.picoc#L5)<br>**Host Requests after restart:** `load kernel/kernel.bin`, then `load /system/init.bin`<br>Shared output requests for help/diagnostics before a valid reboot |
| [`uname.bin`](user/uname.picoc#L15) | Prints the PicoOS version stored in [`config/os-release.txt`](config/os-release.txt) | [`open()`](library/fcntl/fcntl.picoc#L5), [`read()`](library/unistd/io.picoc#L6), [`write()`](library/unistd/io.picoc#L32), [`close()`](library/unistd/io.picoc#L54)<br>**Host Requests:** `file-size <path>`, `read-range <offset> <count> <path>`, plus shared output requests |

[`common/user_command.picoc`](common/user_command.picoc) supplies these two stateless command helpers:

| Kernel function (shared helper) | Return value / status | Effects | Calls | Called by |
| --- | --- | --- | --- | --- |
| [`command_write(file_descriptor, text)`](common/user_command.picoc#L4) | No return value, the write result is ignored | Counts the text and writes it to the selected descriptor, such as stdout or stderr, the call creates an [`IoRequest`](common/file.header#L31) inside the library | [`write()`](library/unistd/io.picoc#L32)<br>**Host requests:** descriptor-dependent `file-size`, `write-at`, `write stderr`, `write stdout`, and optional `literal-output` requests described in [`8.8 Opening, reading, writing, and seeking`](#88-opening-reading-writing-and-seeking) | **User applications:** [`cat_usage()`](user/cat.picoc#L21), [`count_usage()`](user/count.picoc#L12), [`cp_usage()`](user/cp.picoc#L11), [`edit_standard_input()`](user/cat.picoc#L81), [`kill_write_usage()`](user/kill.picoc#L58), [`ls_usage()`](user/ls.picoc#L7), [`main()`](user/kill.picoc#L69), [`main()`](user/mkdir.picoc#L12), [`main()`](user/pwd.picoc#L11), [`main()`](user/rm.picoc#L11), [`main()`](user/rmdir.picoc#L11), [`main()`](user/cp.picoc#L16), [`main()`](user/ls.picoc#L13), [`main()`](user/mv.picoc#L11), [`main()`](user/touch.picoc#L11), [`main()`](user/uname.picoc#L15), [`main()`](user/cat.picoc#L136), [`main()`](user/count.picoc#L20), [`main()`](user/sed.picoc#L67), [`mkdir_usage()`](user/mkdir.picoc#L7), [`mv_usage()`](user/mv.picoc#L6), [`poweroff_usage()`](user/poweroff.picoc#L7), [`print_path_error()`](user/cat.picoc#L13), [`ps_usage()`](user/ps.picoc#L6), [`pwd_usage()`](user/pwd.picoc#L6), [`reboot_usage()`](user/reboot.picoc#L7), [`rm_usage()`](user/rm.picoc#L6), [`rmdir_usage()`](user/rmdir.picoc#L6), [`sed_usage()`](user/sed.picoc#L62), [`shell_usage()`](user/shell.picoc#L71), [`touch_usage()`](user/touch.picoc#L6), [`uname_usage()`](user/uname.picoc#L10), [`write_replacement()`](user/sed.picoc#L57) |
| [`command_is_help(argument)`](common/user_command.picoc#L13) | `true` for exactly `-h` or `--help`, `false` otherwise | Reads the argument without changing it | None | **User applications:** [`eval()`](user/shell.picoc#L1224), [`main()`](user/kill.picoc#L69), [`main()`](user/mkdir.picoc#L12), [`main()`](user/pwd.picoc#L11), [`main()`](user/rm.picoc#L11), [`main()`](user/rmdir.picoc#L11), [`main()`](user/cp.picoc#L16), [`main()`](user/ls.picoc#L13), [`main()`](user/mv.picoc#L11), [`main()`](user/poweroff.picoc#L12), [`main()`](user/ps.picoc#L11), [`main()`](user/reboot.picoc#L12), [`main()`](user/touch.picoc#L11), [`main()`](user/uname.picoc#L15), [`main()`](user/cat.picoc#L136), [`main()`](user/count.picoc#L20), [`main()`](user/sed.picoc#L67), [`main()`](user/shell.picoc#L1448) |

All applications except [`echo.bin`](user/echo.picoc) use [`command_is_help()`](common/user_command.picoc#L13) for a sole help
argument. Echo prints `-h` and `--help` as ordinary text.

### 13.2.1 Command behavior and supported options
[\[↑ TOC\]](#contents)

The following list records accepted operands and differences from familiar
Unix commands. `cd` is a shell built-in because it changes the shell itself:

- [`echo.bin`](user/echo.picoc) converts each literal `\n` pair inside an
  argument to a newline, separates arguments with spaces, adds a final
  newline, and always returns 0. It has no `-n` option.
- [`count.bin`](user/count.picoc) accepts at most one nonnegative busy-loop
  delay. The value is not milliseconds. [`yield()`](library/schedule/schedule.picoc#L4)
  after every displayed number makes the infinite loop a visible scheduler
  example.
- [`cat.bin`](user/cat.picoc) copies each named path in 64-cell chunks. When
  stdout is seekable, it copies every byte unchanged. Terminal output preserves
  printable ASCII, newline, carriage return, and tab, and displays all other
  bytes as `\xHH`. The same rules apply to seekable stdin with no operands,
  including `cat.bin < input.txt`. Terminal stdin is line-buffered: Backspace/Delete
  edits, Enter emits the line, and Ctrl+D finishes. With redirected stdout,
  editing feedback stays on stderr. An open, read, or write failure returns 1.
- [`touch.bin`](user/touch.picoc) accepts one or more paths and stops at the
  first failure. [`cp.bin`](user/cp.picoc) and [`mv.bin`](user/mv.picoc) accept
  exactly one source and destination and no options. [`cp.bin`](user/cp.picoc)
  copies in 64-cell chunks and disables
  [`PICOOS_LOADING_BAR`](common/loading_bar.header#L5). [`mv.bin`](user/mv.picoc)
  uses one [`move()`](library/unistd/file_removal.picoc#L12) call and matching
  [`move`](library/unistd/file_removal.picoc#L12) Host Request. [`ps.bin`](user/ps.picoc) takes no operands and lists
  every [`ProcessControlBlock`](kernel/process/process.header#L31), including its own and
  any process whose [`state`](kernel/process/process.header#L33) is
  [`ZOMBIE`](kernel/process/process.header#L17) and has not yet been removed.
- [`sed.bin`](user/sed.picoc) has no path operand: `sed.bin EXPRESSION` reads
  seekable stdin and writes stdout. `5iNEW LINE`, `5cNEW LINE`, `5aNEW LINE`,
  and `/pattern/iNEW LINE` insert before, change, append after, or insert before
  each matching line. `s/pattern/replacement/` replaces the first literal
  occurrence on every line. It reads all input into memory and disables the
  loading bar.
- [`ls.bin`](user/ls.picoc) lists `.` or one directory. Its only special option
  is `-a`, which includes names beginning with `.`. Directories receive `d `
  and other entries `- `. There is no long or recursive mode.
  [`mkdir.bin`](user/mkdir.picoc) has no `-p`, [`rm.bin`](user/rm.picoc) has no
  force/recursive mode, and [`rmdir.bin`](user/rmdir.picoc) removes only empty
  directories. Those three commands accept multiple operands and continue
  after an individual error.
- [`kill.bin`](user/kill.picoc) defaults to [`SIGKILL`](common/signal.header#L5).
  It accepts `0`, or [`SIGINT`](common/signal.header#L4),
  [`SIGKILL`](common/signal.header#L5), [`SIGCONT`](common/signal.header#L6),
  [`SIGSTOP`](common/signal.header#L7), [`SIGTSTP`](common/signal.header#L8), and
  [`SIGTTIN`](common/signal.header#L9) by exact name without a leading `-`, or
  by number. Probe 0 checks for a non-zombie PID without delivering anything.
  See [`7.2 Process signals`](#72-process-signals). After an accepted
  request, the command yields so the target can be selected promptly.
- [`poweroff.bin`](user/poweroff.picoc) invokes
  [`SYSCALL_SHUTDOWN`](common/syscall.header#L5) and halts PicoOS.
  Unlike the shell's [`exit`](user/shell.picoc#L1257), it does not let init
  start a replacement shell. [`reboot.bin`](user/reboot.picoc) invokes
  [`SYSCALL_REBOOT`](common/syscall.header#L6) for full bootloader and kernel
  startup without ending the emulator process.
  [`uname.bin`](user/uname.picoc) prints `PicoOS-` plus the installed
  [`config/os-release.txt`](config/os-release.txt) version. These commands take
  no operands.

This session builds a report and a five-command PicoOS script, then runs
it through [`shell.bin`](user/shell.picoc) stdin. It also stops an infinite background counter.
Loading messages and unrelated output are omitted. The example counter
is PID 14, while `$!` selects it without hardcoding the PID:

```console
PicoOS> mkdir.bin demo
PicoOS> cd demo
PicoOS> echo.bin "todo\nreview" > n
PicoOS> cat.bin n | sed.bin "s/todo/done/" > r
PicoOS> echo.bin "pwd.bin\ntouch.bin e\ncp.bin n c\nmv.bin c b\nls.bin -a" > x
PicoOS> shell.bin < x
/demo
PicoOS> count.bin 0 > /device/null.dev &
PicoOS> ps.bin
14 user/count.bin
PicoOS> kill.bin SIGSTOP $!
PicoOS> kill.bin SIGCONT $!
PicoOS> kill.bin $!
PicoOS> kill.bin 0 $!
kill: process not found
PicoOS> echo.bin $?
1
PicoOS> ps.bin
14 user/count.bin
PicoOS> cd ..
PicoOS> rm.bin demo/n demo/b demo/e demo/r demo/x
PicoOS> rmdir.bin demo
```

After [`SIGKILL`](common/signal.header#L5), the existence probe fails, but [`ps.bin`](user/ps.picoc) still shows the
uncollected zombie. The pipeline uses the temporary-file sequence from [`12.7 Sequential file-backed pipelines`](#127-sequential-file-backed-pipelines).

### 13.2.2 Command errors and exit statuses
[\[↑ TOC\]](#contents)

Commands write results to stdout and diagnostics to stderr. Multi-path
commands continue after an individual error but retain failure status.
The shell stores foreground exit status in `$?`, diagnoses parsing and
process errors, and reports signal stops or termination by PID and name.

[`cp.bin`](user/cp.picoc), [`sed.bin`](user/sed.picoc), and [`echo.bin`](user/echo.picoc) do not check every output failure.
A zero status therefore does not guarantee complete output. [`7.1.2 Child waiting with waitpid`](#712-child-waiting-with-waitpid)
explains child-status delivery.

# 14. Test system
[\[↑ TOC\]](#contents)

Tests compile code, run it in the emulator, and compare the output with
a stored expectation. This chapter explains the four categories, their
fixtures, and how to run them.

## 14.1 Library, OS, shell, and boot test categories
[\[↑ TOC\]](#contents)

The repository has **63 test classes**: **13 library**, **23 OS**,
**26 shell**, and **1 boot**. OS and shell classes form the 49 System tests
selected by `make test-sys`. Each class can check several behaviors.

These counts follow the runner's selection and fixture-validation rules.
Directories without both `input.txt` and `expected_output.txt` are excluded.
The current `cat_binary` fixture is a shell test because its input differs
from the exact OS launcher sequence.

The diagram shows category targets and expected-output sources. Boot, OS,
and shell tests all execute the full startup chain:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart TD
    T["63 Tests<br/><code>make test</code>"] --> L["13 Library Tests<br/><code>make test-lib</code>"]
    T --> B["1 Boot Test<br/><code>make test-boot</code>"]
    T --> S["49 System Tests<br/><code>make test-sys</code>"]
    S --> O["23 OS Tests<br/><code>make test-os</code>"]
    S --> H["26 Shell Tests<br/><code>make test-shell</code>"]
    L --> LM["Expected output from<br/><code>// expected:</code> source metadata"]
    B --> EF["Expected output from<br/><code>expected_output.txt</code>"]
    O --> EF
    H --> EF
    LM --> LC["Compare actual Library output<br/>with expected output"]
    EF --> SC["Compare normalized <code>output.txt</code><br/>with <code>expected_output.txt</code>"]
```

### 14.1.1 Files that make up a test
[\[↑ TOC\]](#contents)

A library class is one top-level `.picoc` file. Other classes use a
directory of fixtures. These examples show one library and one OS class:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart TD
    T["<code>test/</code>"] --> L["<code>basic_printf_newline_escape.picoc</code><br/>one Library test"]
    T --> O["<code>hello_world/</code><br/>one OS test"]
    O --> I["<code>input.txt</code>"]
    O --> E["<code>expected_output.txt</code>"]
    O --> A["<code>launcher.picoc</code>"]
    O --> P["<code>hello_world.picoc</code>"]
```

Boot, OS, and shell classes require input and expected-output files.
Private programs, headers, and data are optional. The table distinguishes
source fixtures from generated files:

| File or generated file | Role | Test categories |
| --- | --- | --- |
| [`test/*.picoc`](test/) | One top-level file is one Library test. Its opening comments declare emulator input, expected output, and linked `.reti_blocks` dependencies. The Library tests have no separate test-specific `.header` files. | Library |
| `test/<name>/input.txt` | Host-side UTF-8 text read by [`run_os_tests.py`](run_os_tests.py#L522). Each line becomes one command or encoded key sequence sent to the shell after the runner sees `PicoOS> `. | Boot, OS, Shell |
| `test/<name>/expected_output.txt` | Source-controlled UTF-8 output that the test expects after terminal output has been normalized. | Boot, OS, Shell |
| `test/<name>/launcher.picoc` | A test-specific user program that coordinates an OS test by loading, starting, waiting for, or checking other programs. Its presence alone does not classify a directory as an OS test. | Every OS test and the [`shell_exit_status_pid` Shell test](test/shell_exit_status_pid/) |
| `test/<name>/<program>.picoc` | Optional test application or worker. Every `.picoc` file in the directory is compiled and assembled into a `.bin` file under `binary/test/<name>/`. | OS, Shell |
| `test/<name>/*.header` | Optional definitions shared by test programs. The current shared-memory mutex tests use this form. | OS when needed |
| Other `test/<name>/*.txt` source files | Optional guest-visible data, command script, or expected-output variant used by the test. The runner copies these files below `binary/test/<name>/`. | OS, Shell |
| `test/<name>/raw_output.txt` | Generated complete RETI-Emulator stdout, including prompts, typed commands, control characters, and loading bars. | Boot, OS, Shell |
| `test/<name>/output.txt` | Generated readable output after prompt lines, loading bars, terminal cursor effects, and empty lines have been removed. This is the actual value used for comparison. | Boot, OS, Shell |
| `test/<library-name>.input`, `.expected_output`, `.output`, `.error`, [`.reti`](../PicoC-Compiler/source/passes/linking/reti_pass.py), and compiler files | Generated files derived from a top-level Library source. The `.input` and `.expected_output` values come from its first two metadata comments. | Library |

[`stage_test_directories()`](run_os_tests.py#L176) copies fixtures below `binary/test/`.
[`build_test_programs()`](run_os_tests.py#L725) compiles and assembles private applications there.
The runner reads the original input file, while guest programs open the
staged data.

### 14.1.2 Library test example
[\[↑ TOC\]](#contents)

This complete library test declares no input, an expected newline, and
a stdio dependency in its comments:

```c
// in:
// expected:newline\n
// dependencies: ../library/stdio/libstdio.reti_blocks

#include "../library/stdio/stdio.header"

int main() {
    printf("newline\n");
    return 0;
}
```

[`run_sys_tests.sh`](run_sys_tests.sh#L112) extracts the input and expected-output comments. The
linked test runs with [`interrupt_service_routines/isrs.picoc`](interrupt_service_routines/isrs.picoc), without
the PicoOS kernel. Emulator test mode records its output.

Staged mode rewrites supported metadata comments into the linked RETI.
Direct mode compiles source and dependencies together. Both compare against
the expectation extracted from the second source line.

The runner ignores trailing whitespace per line. A differing output,
compiler or emulator error, missing output, or five-second timeout fails
the test.

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    M["Source metadata in <code>.picoc</code>"] --> R["Compiled RETI program"]
    M --> E["Generated <code>.expected_output</code>"]
    R --> A["Actual <code>.output</code>"]
    E --> C["Exact line comparison"]
    A --> C
    C --> P["Pass or fail"]
```

### 14.1.3 OS test example
[\[↑ TOC\]](#contents)

An OS class puts process orchestration in `launcher.picoc`. Classification
requires that source and exactly this three-line input sequence:

```text
load test/hello_world/launcher.bin
run 3
poweroff.bin
```

The shell loads the launcher as PID 3 and waits for it. The launcher
starts the application under test:

```c
// test/hello_world/launcher.picoc
// dependencies: ../../library/unistd/libunistd.reti_blocks ../../library/sys/wait/libwait.reti_blocks

#include "../../library/unistd/unistd.header"
#include "../../library/sys/wait/wait.header"
#include "../../common/stddef.header"

int main(void) {
    int pid = load("test/hello_world/hello_world.bin");

    run(pid, NULL, NULL);
    waitpid(pid);
    return 0;
}
```

The launched application is also a complete test-local source file:

```c
// test/hello_world/hello_world.picoc
// dependencies: ../../library/stdio/libstdio.reti_blocks

#include "../../library/stdio/stdio.header"

int main(void) {
    printf("hello world");
    return 0;
}
```

The expected output includes shell messages as well as application output:

```text
process with pid 3 created
hello world
process with pid 5 created
```

The complete path is therefore:

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    I["<code>input.txt</code>"] --> S["Shell <code>load</code> and <code>run</code> built-ins"]
    S --> L["<code>launcher.bin</code>"]
    L --> H["<code>hello_world.bin</code>"]
    H --> C["Captured emulator stdout"]
    C --> O["Normalized <code>output.txt</code>"]
    O --> D["Comparison"]
    E["<code>expected_output.txt</code>"] --> D
    D --> P["Pass or fail"]
```

A launcher can coordinate multiple processes, shared memory, signals,
and scheduler events without adding host input commands.

### 14.1.4 Shell test example
[\[↑ TOC\]](#contents)

Shell classes use commands and encoded keys in `input.txt`, without the
exact OS launcher sequence. [`decode_test_input()`](run_os_tests.py#L461) recognizes arrows, Home,
Escape, Backspace, and the supported control-key spellings. The runner
waits for a new prompt before sending each line.

The `ps` shell class uses only the two required files. Its input runs
[`ps.bin`](user/ps.picoc#L11) and powers off:

```text
ps.bin
poweroff.bin
```

Its [`expected_output.txt`](test/ps/expected_output.txt) checks both the shell's
process-creation messages and the command's process listing:

```text
process with pid 3 created
1 system/init.bin
2 user/shell.bin
3 user/ps.bin
process with pid 4 created
```

Each command passes through shell parsing and execution. The runner waits
for the next prompt before continuing. More complex classes can include
private applications and data.

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    I["<code>input.txt</code>"] --> R["Runner waits for <code>PicoOS&gt;</code>"]
    R --> S["Shell"]
    S --> A["Command or test application"]
    A --> C["Captured UART output"]
    C --> O["Normalized <code>output.txt</code>"]
    O --> D["Comparison"]
    E["<code>expected_output.txt</code>"] --> D
    D --> P["Pass or fail"]
```

### 14.1.5 Boot test example
[\[↑ TOC\]](#contents)

The one [`boot` test directory](test/boot/) has no private PicoC program. Its
[`input.txt`](test/boot/input.txt) runs a release command after startup:

```text
echo.bin hello world
poweroff.bin
```

Its [`expected_output.txt`](test/boot/expected_output.txt) is:

```text
process with pid 3 created
hello world
process with pid 4 created
```

`make test-boot` selects this fixture. `reti_emulator -e` starts the EPROM
bootloader, followed by kernel, init, and shell. The runner sends `echo.bin`
and [`poweroff.bin`](user/poweroff.picoc#L12) after their prompts.

```mermaid
%%{init: {"theme":"base","fontFamily":"Cantarell, sans-serif","themeVariables":{"fontFamily":"Cantarell, sans-serif","background":"#ffffff","primaryColor":"#f4f8f8","primaryTextColor":"#17313a","primaryBorderColor":"#637983","secondaryColor":"#eaf3f4","secondaryTextColor":"#17313a","secondaryBorderColor":"#637983","tertiaryColor":"#f4f8f8","tertiaryTextColor":"#17313a","tertiaryBorderColor":"#637983","lineColor":"#637983","textColor":"#17313a","edgeLabelBackground":"#ffffff","clusterBkg":"#f4f8f8","clusterBorder":"#637983","titleColor":"#17313a","actorBkg":"#f4f8f8","actorBorder":"#637983","actorTextColor":"#17313a","actorLineColor":"#637983","signalColor":"#637983","signalTextColor":"#17313a","labelBoxBkgColor":"#f4f8f8","labelBoxBorderColor":"#637983","labelTextColor":"#17313a","loopTextColor":"#17313a","noteBkgColor":"#eaf3f4","noteBorderColor":"#637983","noteTextColor":"#17313a","activationBkgColor":"#eaf3f4","activationBorderColor":"#637983","stateBkg":"#f4f8f8","stateBorder":"#637983","stateLabelColor":"#17313a","labelColor":"#17313a","altBackground":"#eaf3f4"},"themeCSS":"rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }"}}%%
flowchart LR
    B["EPROM <code>bootloader.reti</code>"] --> K["<code>kernel.bin</code>"]
    K --> I["<code>init.bin</code>"]
    I --> S["<code>shell.bin</code>"]
    S --> E["<code>echo.bin</code>"]
    E --> C["Captured UART output"]
    C --> O["Normalized <code>output.txt</code>"]
    O --> D["Comparison"]
    X["<code>expected_output.txt</code>"] --> D
    D --> P["Pass or fail"]
```

The separate boot target provides a small startup check. OS and shell tests
use the same [`RUNTIME_BOOT_ARGUMENTS`](run_os_tests.py#L28) and full boot sequence.

## 14.2 Test execution
[\[↑ TOC\]](#contents)

Each class gets its own emulator and temporary peripheral directory.
Boot, OS, and shell classes each boot a fresh system. Independent classes
can run in parallel. The table follows input through comparison:

| Test representation | Started by | Input path | Code that runs | Output and pass condition |
| --- | --- | --- | --- | --- |
| Top-level Library `.picoc` file | [`run_sys_tests.sh`](run_sys_tests.sh), then [`run_lib_test_case.sh`](run_lib_test_case.sh) | `// in:` is extracted from the source and supplied by RETI-Emulator test mode | The compiled test and declared library dependencies run with the generated [`config/isrs.reti`](config/isrs.reti) test interrupt service routines, without PicoOS | Emulator output in `<name>.output` is compared with the value extracted from `// expected:`. Trailing whitespace is removed per line. Compile, emulator, timeout, missing-file, or comparison failure prevents a pass. |
| OS directory | [`run_os_tests.py`](run_os_tests.py) with `--kind os` | The runner waits for `PicoOS> ` before sending each decoded `input.txt` line to emulator stdin. The shell loads and runs `launcher.bin`. | EPROM bootloader, kernel, Init, shell, launcher, and any worker or application binaries | Complete stdout is saved as `raw_output.txt`. [`normalize_os_output()`](run_os_tests.py#L440) applies terminal cursor effects and removes prompts, typed commands, loading bars, and empty lines to produce `output.txt`. [`outputs_match()`](run_os_tests.py#L633) removes trailing whitespace from the complete expected and actual strings and requires equality. |
| Shell directory | [`run_os_tests.py`](run_os_tests.py) with `--kind shell` | The same prompt-controlled `input.txt` path feeds shell commands and encoded keys. | EPROM bootloader, kernel, Init, shell, and commands or test-local applications named by those lines | The same `raw_output.txt`, normalized `output.txt`, and `expected_output.txt` comparison as an OS test. |
| [`test/boot/`](test/boot/) | [`run_os_tests.py`](run_os_tests.py) with `--kind boot` | The same prompt-controlled path sends `echo.bin hello world` and [`poweroff.bin`](user/poweroff.picoc#L12) from `input.txt` | EPROM bootloader, kernel, Init, shell, and release applications. There is no test-local binary. | The same `raw_output.txt`, normalized `output.txt`, and `expected_output.txt` comparison as OS and Shell tests. |

Private user programs use `libstart`. Staged mode reuses `.reti_blocks`
and `.st`, while `TEST_BUILD_MODE=direct` links sources directly. Both
use the same execution and comparison. Timeouts are five seconds for
library tests and 120 seconds for the other categories.

The [CI workflow](.github/workflows/run_tests.yml) calls `make test` with direct
source linking and DMA enabled. It therefore runs all four categories through
the same target hierarchy described below.

### 14.2.1 Make targets
[\[↑ TOC\]](#contents)

These Make targets select categories, patterns, or previously failed tests:

| Command | Tests run |
| --- | --- |
| `make test` | Builds the release tree, then runs `make test-lib`, `make test-sys`, and `make test-boot`, in that order. With the default empty patterns, this is all 63 tests. |
| `make test-all` | Alias for `make test`. |
| `make test-lib` | The 13 top-level Library tests, or the subset selected by `TEST_PATTERN`. |
| `make test-sys` | Aggregate for `make test-os` followed by `make test-shell`. It does not invoke `make test-boot`. |
| `make test-os` | The 23 directories recognized by the exact `launcher.picoc` and three-line `input.txt` rule. |
| `make test-shell` | The 26 runnable non-Boot directories that do not match the OS rule. |
| `make test-boot` | Only [`test/boot/`](test/boot/), using one emulator job. This target is called directly by `make test`, not by `make test-sys`. |
| `make test_not_passed` | Only Library source paths recorded in [`config/not_passed_tests.txt`](config/not_passed_tests.txt) by the preceding Library run. |

`make run-os` runs `OS_RUN_PATH` for inspection and skips expected-output
comparison. Outside debug mode, it still records output files.

# 15. Use in operating-systems and real-time operating-systems lectures
[\[↑ TOC\]](#contents)

PicoOS lets students inspect lecture concepts in source code and live
execution. The examples below cover OS mechanisms first, then scheduling
and synchronization topics from RTOS lectures.

## 15.1 Operating-systems topics
[\[↑ TOC\]](#contents)

The table connects lecture topics to inspectable code and state. Filesystem
examples cover descriptors and UART host requests:

| Operating-systems lecture topic | What students can inspect in PicoOS |
| --- | --- |
| Parent/child relationships and process loading | [`load()`](library/unistd/process.picoc#L17), [`run()`](library/unistd/process.picoc#L31), [`ProcessControlBlock`](kernel/process/process.header#L31), its [`parent_pid`](kernel/process/process.header#L57), process images, zombies, [`waitpid()`](library/sys/wait/wait.picoc#L14), and cleanup |
| Signals | [`7.2 Process signals`](#72-process-signals) in [`ProcessControlBlock`](kernel/process/process.header#L31) |
| interrupt service routines tables and ISRs | The IVT and interrupt service routines in [`2.1 RETI interrupt entry and the interrupt service routine table`](#21-reti-interrupt-entry-and-the-interrupt-service-routine-table), the saved [`ActivationRecord`](kernel/process/process.header#L21), timer/UART handlers, and `RTI` |
| Software, hardware, and synchronous interrupts | System calls, timer and UART interrupts, and CPU exceptions with their fixed exception entry |
| [`malloc()`](library/stdlib/malloc.picoc#L35) / [`free()`](library/stdlib/malloc.picoc#L49) | Heap headers, first-fit allocation, block splitting, freeing, and merging adjacent free blocks |
| Filesystem boundary | Per-process file descriptors, descriptor inheritance, and UART host requests instead of an on-device filesystem |

Generated [`.reti`](../PicoC-Compiler/source/passes/linking/reti_pass.py), `.sections`, and debug files allow PicoC source, symbolic
RETI, binary layout, and live machine state to be compared.

### 15.1.1 Inspecting PicoOS execution in the RETI-Emulator
[\[↑ TOC\]](#contents)

To compare PicoC with generated RETI, enable intermediate output (`-i -w`),
debug metadata (`-g`), and annotations (`-v`). Open the result with the
commented debugger and matching metadata:

```console
$ picoc_compiler -O1 -i -w -g -v -o program.reti program.picoc
$ reti_emulator -d -c -D program.debuginfo program.reti
```

For a built PicoOS checkout, start the bootloader with kernel layout and
debug metadata from the runtime directory:

```console
$ cd binary
$ reti_emulator -n 5 -O -r 262144 -e boot/bootloader.reti -S kernel/kernel.sections -D kernel/kernel.debuginfo -d -c
```

The following controls help trace the running system. The
[RETI-Emulator documentation](../RETI-Emulator/README.md) lists the remaining
controls:

| Keys or option | What students can inspect or do |
| --- | --- |
| `c`, then `E` (`Enter again`) | Continue execution and stop it at any point to see the RETI instruction of the kernel/PicoOS code currently being executed |
| `d` (`debug source`) | Show the PicoC source code from which the current RETI instruction resulted |
| `A` (`Assign value`) | Correct a wrong register or memory cell and continue without starting again |
| `r` (`restart`) | Quickly restart the emulator |
| `S` / `R` (`Snapshot` / `Restore`) | Save/restore emulator state to repeat a scheduler decision, system call, or interrupt |
| `e`, then `T` | Trigger and inspect an interrupt handler without waiting for a timer event or UART input |

Source view uses `.debuginfo` and matching `.pre` files to annotate globals
and stack frames. These example annotations show the format rather than
fixed PicoOS addresses:

| SRAM address | Value | Annotation in the debug TUI |
| ---: | ---: | --- |
| `8012` | `3` | `global current_pid@12` |
| `8179` | `42` | `var timeslice@0` |
| `8182` | `9001` | `return addr.` |
| `8183` | `7` | `arg next_pid@0` |

Their exact form is documented in the
[RETI-Emulator README](../RETI-Emulator/README.md).

The [PicoC-Compiler](../PicoC-Compiler/README.md) and
[RETI-Emulator](../RETI-Emulator/README.md) documentation describe their
command-line options.

<!-- TODO: Add the details for trying out memory-mapped devices with `(A)ssign value`. -->

### 15.1.2 Exploring userspace heap allocation
[\[↑ TOC\]](#contents)

[`test/exercise_sheet_4_heap/launcher.picoc`](test/exercise_sheet_4_heap/launcher.picoc) adapts OS exercise sheet 4.
This complete test contrasts stack objects, aliases, and a heap allocation
with its cleanup:

```c
// dependencies: ../../library/stdlib/libstdlib.reti_blocks

#include "../../library/stdlib/stdlib.header"

struct point {
    int x;
    int y;
};

int main(void) {
    struct point *p1;
    struct point *p3;
    int *a;
    struct point p2;

    a = &(p2.x);
    p2.x = 7;
    p2.y = 4;

    p1 = (struct point *)malloc(sizeof(struct point));
    (*p1).y = *a;
    p3 = p1;
    p1 = &p2;

    if ((*p1).y > 5) {
        *a = 42;
    } else {
        *a = 1;
    }

    free(p3);
    return 0;
}
```

Predict the storage and aliasing first, then single-step the test. Explain
why `p3` retains the allocation, what is written through `a`, and which
address must be freed.

[`3.1 Heap block layout and allocation algorithm`](#31-heap-block-layout-and-allocation-algorithm) explains allocation and merging, [`9.1 Memory layout, allocation sources, and lifetimes`](#91-memory-layout-allocation-sources-and-lifetimes) compares stack and heap
lifetimes, and [`1.1.5.2 PicoOS libstart startup sequence`](#1152-picoos-libstart-startup-sequence) shows heap initialization before [`main()`](test/exercise_sheet_4_heap/launcher.picoc#L10).

After the one-allocation exercise, students can use
[`basic_free.picoc`](test/basic_free.picoc) and
[`basic_free_block_merging.picoc`](test/basic_free_block_merging.picoc) to
test their understanding of reuse and merging with longer allocation traces.

### 15.1.3 Editing and executing symbolic RETI assembly
[\[↑ TOC\]](#contents)

Write symbolic RETI assembly directly in a `.reti_blocks` file. The compiler
turns it into **resolved RETI assembly** in `.reti`, replacing labels with
numeric addresses and expanding pseudoinstructions. The emulator then
assembles the concrete instructions into machine code.

This example saves `3` on the stack, counts down to zero, and restores the
saved `3` into `IN2`. Write the following complete program in
[`documentation/countdown.reti_blocks`](documentation/countdown.reti_blocks).
The `.text` section contains the instructions. `.ivt` and `.data` remain empty
because the program defines no interrupt service routines or global variables:

```reti
  .ivt
  .text
_start:
  LOADI32 IN1 3
  # Save the starting value on the stack.
  PUSH IN1
loop:
  SUBI IN1 1
  MOVE IN1 ACC
  JUMP32> loop
done:
  # Restore the saved value into IN2.
  POP IN2
  JUMP 0
  .data
```

`LOADI32` loads the starting value and `PUSH` saves it. Each pass through
`loop` subtracts one from `IN1`. `MOVE IN1 ACC` supplies the condition for
`JUMP32> loop`, which repeats while the counter is greater than zero.
The label lets the linker calculate the target after expanding the
pseudoinstructions. `JUMP32` uses `ACC` as scratch space, so the counter stays
in `IN1`. At `done`, `POP` restores the saved value into `IN2`.

These are all four pseudoinstructions from
[`1.1.7 RETI pseudoinstructions`](#117-reti-pseudoinstructions).
PicoOS uses the same stack convention to save registers in
[`timer_interrupt()`](interrupt_service_routines/os_isrs.picoc#L32) and restore
them in [`timer_interrupt_kernel_return()`](interrupt_service_routines/os_isrs.picoc#L62).

Compile the assembly with `-v` to include comments for labels and
pseudoinstructions. `-C` selects the supplied `_start` entry. The emulator
uses the generated `.sections` file to initialize `CS`, `DS`, and `SP`:

```console
$ cd documentation
$ picoc_compiler -v -C countdown.reti_blocks -o countdown.reti countdown.reti_blocks
$ reti_emulator -d -c -K countdown.reti
```

The complete `countdown.reti` output below shows the expanded stack operations
and the resolved `loop` target. The comments identify the original labels
and instructions:

```reti
# // Block('_start', [])
# Instr(LOADI32, [IN1, 3])
# write large immediate into IN1
LOADI IN1 0
MULTI IN1 1024
ORI IN1 3
# Save the starting value on the stack.
SUBI SP 1
STOREIN SP IN1 1
# // Block('loop', [])
SUBI IN1 1
MOVE IN1 ACC
# Jump32(>, loop)
JUMP<= 6
# write large immediate into ACC
LOADI ACC 0
MULTI ACC 1024
ORI ACC 5
ADD ACC CS
MOVE ACC PC
# // Block('done', [])
# Restore the saved value into IN2.
LOADIN SP IN2 1
ADDI SP 1
JUMP 0
```

Single-step the program and watch `IN1` go from `3` to `2`, `1`, and `0`.
After `POP`, `IN2` contains `3` and `SP` has returned to its initial value.
`JUMP 0` jumps to itself and ends emulator execution. `-K` keeps the debugger
open so the final state can be inspected.

## 15.2 Real-time operating-systems topics
[\[↑ TOC\]](#contents)

The RTOS lecture topics below connect to process state, scheduling, waiting,
and mutexes. PicoOS demonstrates these mechanisms without deadline
guarantees:

| Real-time operating-systems lecture topic | What students can inspect in PicoOS |
| --- | --- |
| Process states | New, ready, running, blocked, stopped, and zombie entries in the [`ProcessControlBlock`](kernel/process/process.header#L31) list, [`7.1.2.2 Parent collection and final removal`](#7122-parent-collection-and-final-removal) explains why termination and removal are separate steps |
| Scheduling and dispatching | The scheduler chooses a ready process, the dispatcher saves and restores its activation record |
| [`waitpid()`](library/sys/wait/wait.picoc#L14), [`sleep()`](library/unistd/blocking.picoc#L9), and [`wakeup()`](library/unistd/blocking.picoc#L19) | A process blocks in a wait queue until a child, mutex, or other event wakes it |
| Mutexes | [`mutex_lock()`](library/mutex/mutex.picoc#L18) blocks a contending process and [`mutex_unlock()`](library/mutex/mutex.picoc#L25) wakes a waiting process |

### 15.2.1 Parent, workers, and shared memory
[\[↑ TOC\]](#contents)

The [`shared_memory_mutex`](test/shared_memory_mutex/) example has three
processes. The parent runs [`launcher.picoc`](test/shared_memory_mutex/launcher.picoc),
creates a named shared-memory region, and starts two children from the same
[`worker.picoc`](test/shared_memory_mutex/worker.picoc) binary. Each child
increments the shared counter once, so the final value should be `2`.
PicoOS uses [`load()`](library/unistd/process.picoc#L18) to create each child
and [`run()`](library/unistd/process.picoc#L31) to make it ready to execute.
Each child's [`parent_pid`](kernel/process/process.header#L57) records the
launcher's PID.

The diagram shows the whole setup. Dashed arrows show the parent starting
the children and passing arguments. Teal arrows show the three processes'
local pointers reaching **one shared region**, whose fields are shown with
their initial values. The green arrow is the kernel's stored payload address:

![A parent launcher creates and initializes one SharedState region, starts two child workers with the same shared-memory ID, and waits for both. All three local shared_state pointers reach the same counter, lock, and wait queue. A kernel SharedMemoryEntry stores the name, ID, and payload address.](documentation/images/process-shared-mutex.svg)

The parent calls [`shm_open("shared-memory-mutex", sizeof(struct SharedState))`](library/sys/mman/mman.picoc#L15).
The kernel creates a [`SharedMemoryEntry`](kernel/shared_memory.header#L8)
with that [`name`](kernel/shared_memory.header#L9), a numeric
[`id`](kernel/shared_memory.header#L10), and an
[`address`](kernel/shared_memory.header#L11) pointing to the allocated data.
The parent passes the same ID to both children as a command-line argument.
The children do not create or name another region.

All three call [`mmap(id)`](library/sys/mman/mman.picoc#L23).
In PicoOS, this returns the same physical address stored in the entry.
Their local [`shared_state`](test/shared_memory_mutex/worker.picoc#L11)
pointers are separate variables, but they point
to the same [`SharedState`](test/shared_memory_mutex/shared.header#L5).
Each mapping is recorded through the process's
[`shared_memory_attachments`](kernel/process/process.header#L55).
[`5.1.2 Per-process attachment lists in SRAM`](#512-per-process-attachment-lists-in-sram)
shows those kernel records in detail.

The shared region contains both the [`workers`](test/shared_memory_mutex/shared.header#L6)
counter and the [`mutex`](test/shared_memory_mutex/shared.header#L7).
Putting the mutex there makes both children use the same
[`lock`](library/mutex/mutex.header#L7) and
[`waiters`](library/mutex/mutex.header#L8) queue. Separate local mutexes
would let both children enter the critical section at the same time.

### 15.2.2 Complete launcher and worker code
[\[↑ TOC\]](#contents)

The three files below show the shared declaration, parent setup, child
execution, and cleanup. They are the complete example sources, with only
AI attribution comments omitted. The shared
[`shared.header`](test/shared_memory_mutex/shared.header) gives the parent
and children the same data layout:

```c
#pragma once

#include "../../library/mutex/mutex.header"

struct SharedState {
    int workers;
    struct mutex mutex;
};
```

The parent in [`launcher.picoc`](test/shared_memory_mutex/launcher.picoc)
maps the region, sets [`workers`](test/shared_memory_mutex/shared.header#L6)
to `0`, and calls [`mutex_init()`](library/mutex/mutex.picoc#L12) **before
starting either child**. Its
[`build_worker_arguments()`](test/shared_memory_mutex/launcher.picoc#L10)
helper constructs `"1 <id>"` and `"2 <id>"`, where `<id>` is the ID returned
by [`shm_open()`](library/sys/mman/mman.picoc#L15):

```c
// dependencies: ../../common/decimal.reti_blocks ../../library/stdlib/libstdlib.reti_blocks ../../library/unistd/libunistd.reti_blocks ../../library/sys/wait/libwait.reti_blocks ../../library/sys/mman/libmman.reti_blocks ../../library/mutex/libmutex.reti_blocks

#include "shared.header"
#include "../../common/decimal.header"
#include "../../library/unistd/unistd.header"
#include "../../library/sys/wait/wait.header"
#include "../../library/sys/mman/mman.header"

void build_worker_arguments(
    char *arguments,
    int worker_number,
    int shared_memory_id
) {
    int length;

    length = append_decimal(arguments, worker_number);

    arguments[length] = ' ';
    length = length + 1;
    length = length + append_decimal(arguments + length, shared_memory_id);
    arguments[length] = '\0';
}

void write_text(char *text) {
    int length = 0;

    while (text[length] != '\0') {
        length = length + 1;
    }
    write(STDOUT_FILENO, text, length);
}

int main(void) {
    int shared_memory_id;
    int first_worker;
    int second_worker;
    struct SharedState *shared_state;
    char first_worker_arguments[16];
    char second_worker_arguments[16];

    shared_memory_id = shm_open(
        "shared-memory-mutex",
        sizeof(struct SharedState)
    );
    shared_state = (struct SharedState *)mmap(shared_memory_id);
    shared_state->workers = 0;
    mutex_init(&(shared_state->mutex));
    build_worker_arguments(first_worker_arguments, 1, shared_memory_id);
    build_worker_arguments(second_worker_arguments, 2, shared_memory_id);

    first_worker = load("test/shared_memory_mutex/worker.bin");
    second_worker = load("test/shared_memory_mutex/worker.bin");
    run(first_worker, first_worker_arguments, NULL);
    run(second_worker, second_worker_arguments, NULL);

    waitpid(first_worker);
    waitpid(second_worker);
    if (shared_state->workers == 2) {
        write_text("workers: 2\n");
    } else {
        write_text("workers: invalid\n");
    }
    shm_unlink("shared-memory-mutex");
    return 0;
}
```

Both children execute [`worker.picoc`](test/shared_memory_mutex/worker.picoc).
The kernel's [`store_process_arguments()`](kernel/process/process_arguments.picoc#L125)
supplies the executable path in `argv[0]`, the worker number in `argv[1]`,
and the shared-memory ID in `argv[2]`. The
[`startup code`](library/start/start.picoc#L7) passes them to the worker.
[`atoi()`](library/stdlib/atoi.picoc#L4) converts those argument strings
into integers. The critical section extends from
[`mutex_lock()`](library/mutex/mutex.picoc#L18) to
[`mutex_unlock()`](library/mutex/mutex.picoc#L25), protecting the entire
read, add, and write operation. Worker 1 calls
[`yield()`](library/schedule/schedule.picoc#L4) while still holding the mutex:

```c
// dependencies: ../../library/stdlib/libstdlib.reti_blocks ../../library/mutex/libmutex.reti_blocks ../../library/schedule/libschedule.reti_blocks ../../library/sys/mman/libmman.reti_blocks

#include "shared.header"
#include "../../library/schedule/schedule.header"
#include "../../library/stdlib/stdlib.header"
#include "../../library/sys/mman/mman.header"

int main(int argc, char **argv) {
    struct SharedState *shared_state;

    shared_state = (struct SharedState *)mmap(atoi(argv[2]));
    mutex_lock(&(shared_state->mutex));
    shared_state->workers = shared_state->workers + 1;
    if (atoi(argv[1]) == 1) {
        yield();
    }
    mutex_unlock(&(shared_state->mutex));
    return 0;
}
```

After both children finish, the parent's
[`waitpid()`](library/sys/wait/wait.picoc#L14) calls have collected them,
and [`write_text()`](test/shared_memory_mutex/launcher.picoc#L25) prints
`workers: 2`. The parent then calls
[`shm_unlink()`](library/sys/mman/mman.picoc#L27) to remove the region's name.
Its own mapping keeps the data alive until the parent is removed.
[`5.2 Mapping, unlinking, and deferred destruction`](#52-mapping-unlinking-and-deferred-destruction)
explains this lifetime.

### 15.2.3 Following the counter and mutex through execution
[\[↑ TOC\]](#contents)

The following trace shows one possible execution in which worker 1 acquires
the mutex first and worker 2 attempts to acquire it before worker 1 unlocks.
Scheduling can produce a different order. Calling
[`yield()`](library/schedule/schedule.picoc#L4) permits another process to
run, but does not guarantee that worker 2 runs next.

The columns track the shared [`workers`](test/shared_memory_mutex/shared.header#L6),
[`mutex.lock`](library/mutex/mutex.header#L7), and
[`mutex.waiters`](library/mutex/mutex.header#L8) fields.
Process states are stored in each
[`ProcessControlBlock.state`](kernel/process/process.header#L33):

| Step | Action | Counter | Lock | Queue / process state |
| --- | --- | --- | --- | --- |
| 1 | Parent initializes the shared region | `0` | `false` | Queue empty, neither child has started |
| 2 | Worker 1 acquires the mutex and increments the counter | `0 → 1` | `true` | Worker 1's state is [`PROCESS_STATE_RUNNING`](kernel/process/process.header#L14) |
| 3 | Worker 1 yields while holding the mutex | `1` | `true` | Worker 1's state becomes [`PROCESS_STATE_READY`](kernel/process/process.header#L13), the lock remains held |
| 4 | Worker 2 tries to lock, finds it held, and sleeps | `1` | `true` | Worker 2's PCB is linked into the shared queue, its state becomes [`PROCESS_STATE_BLOCKED`](kernel/process/process.header#L15) |
| 5 | Worker 1 resumes and unlocks | `1` | `false` | Worker 2 is removed from the queue, its state becomes [`PROCESS_STATE_READY`](kernel/process/process.header#L13) |
| 6 | Worker 2 resumes, retries acquisition, increments, and unlocks | `1 → 2` | `true → false` | Queue empty, both children can finish |
| 7 | Parent finishes waiting and reads the shared counter | `2` | `false` | Prints `workers: 2`, then unlinks the name |

At step 4, [`sleep()`](library/unistd/blocking.picoc#L9) reaches
[`enqueue_current_process_on_wait_queue()`](kernel/process/process.picoc#L375).
The kernel sets worker 2's
[`waiting_queue_ptr`](kernel/process/process.header#L48) to the shared mutex's
queue and sets the queue's [`head`](common/wait_queue.header#L6) and
[`tail`](common/wait_queue.header#L7) to worker 2's PCB. The queue is in
shared memory, while the PCB remains in the Kernel Heap.

At step 5, [`mutex_unlock()`](library/mutex/mutex.picoc#L25) clears the lock
and calls [`wakeup()`](library/unistd/blocking.picoc#L19).
[`wakeup_wait_queue()`](kernel/process/process.picoc#L395) removes worker 2
from the queue and makes its state [`PROCESS_STATE_READY`](kernel/process/process.header#L13). Worker 2 must be scheduled
again and retry [`testset()`](library/mutex/mutex.picoc#L3) before it owns
the mutex. Waking it does not transfer ownership of the lock.

To demonstrate a lost update, split the increment into reading the counter
into a local variable and writing that value plus one, then put
[`yield()`](library/schedule/schedule.picoc#L4) between the read and write
and remove both mutex calls. If both children read `0` before either writes,
both write `1`. With the mutex protecting the same operations, the second
child reads `1` and writes `2`. Removing the mutex from the original worker
alone may still print `2`, because its yield comes after the write.

Predict the counter, lock, queue, and process states at yield and unlock,
then compare them in the debugger.
[`7.3 Mutexes with test-and-set and wait queues`](#73-mutexes-with-test-and-set-and-wait-queues)
gives the mutex flow, and
[`6.1.1 Algorithm and Round Robin comparison`](#611-algorithm-and-round-robin-comparison)
gives the scheduling policy. The
[`shared_memory_mutual_exclusion`](test/shared_memory_mutual_exclusion/)
test adds messages to trace acquisition.

# 16. Use of AI in the project
[\[↑ TOC\]](#contents)

This section applies the University of Freiburg's transparency and documentation
principles from its
[Academic Writing Guide](https://uni-freiburg.de/ska/wp-content/uploads/sites/186/AcademicWritingGuide_2025.09.29.pdf)
to PicoOS. The guide is about academic writing, not source-code creation, and
does not explicitly cover code generation. For this project, I apply its
distinction between work done on one's own and help with repetitive or
time-consuming tasks to source-code work. Its recommendation to state the
tool, stage, use, and result also gives a useful way to document AI use in this
project.

I developed all core concepts, the architecture, structural decisions,
and the understanding behind PicoOS on my own. AI was not used
to decide how the operating system should work or how its core mechanisms
should be structured.

A **substantial part of the work consisted of manual debugging**. I had to add
my own source-code debugger to the RETI-Emulator, which I had previously used
as an assembly-level debugger. GDB cannot be used with this custom RETI
architecture. RETI assembly is the assembly language of a custom, little-known
educational CPU architecture, for which little public training material exists.
The PicoC-Compiler compiles PicoC into this RETI assembly, and its code
generation, including its stack-frame layout and other runtime conventions, is
also highly custom. AI could not directly use my RETI-Emulator or its
source-code debugger: AI companies obviously wouldn't and also couldn't use such non-established custom
tools to train their models. AI could not reliably see how all these parts fit
together: the generated RETI assembly and the way the
compiler's stack-frame layout and runtime conventions arrange data on the
stack. There is no established debugging ecosystem for this architecture, so I
had to debug the code myself with my own tools.

I used AI only to speed up repetitive or very time-consuming work, or work
that was not important to the core operating system and not directly related to
the results I had to present at the end. In each case, the intended behavior,
implementation approach, and expected result were already clear. This work did
not involve AI doing the work that a Master's project is meant to assess:
understanding a complex system in detail, keeping an overview of it, and
planning and integrating new features into it. It reduced the time spent on
repetitive tasks and made small extra additions possible that I otherwise would
not have had time to create.

Low-level pointer arithmetic is one example. I may already understand the
solution and required memory layout, but writing the exact address calculations
and fixing small arithmetic mistakes by hand can take a lot of time. When the
requirements were known, AI could often produce an almost correct
implementation immediately, leaving only a few small changes or fixes. In
these cases, I did not use AI to find the solution, but to write an already
understood solution more quickly.

Compared with the core operating-system mechanisms, user applications, tests,
Makefiles, Python and shell scripts, and similar supporting code are generally
simple and do not contribute to understanding how an operating system works.
I would simply not have created some of these applications and tests without
AI. They are the cherry on top of the project, not a central part of it. The
[AI usage record](documentation/ai_usage.md) lists where AI was used in this repository.

Towards the end of the project, the models in GitHub Copilot through GitHub
Education became better, so I started using AI more. At other university chairs
(especially AI chairs), I saw that supervisors even told students to use AI. I
therefore thought that using the newest technical advances was entirely normal,
as people similarly began using computers instead of typewriters and the
internet instead of going to libraries.
By then, I was already far beyond the 18 ECTS mark: I had worked on this
Master's project for three semesters and spent the last one doing nothing but
coding this operating system, so I thought it was reasonable to use AI a bit
more extensively.

# 17. Limitations
[\[↑ TOC\]](#contents)

These limits matter when interpreting the lecture examples and tests.
Each reference gives the relevant implementation details:

- one physical address space with no MMU, hardware memory isolation, or virtual
  memory, as described in [`3. Memory management and shared memory`](#3-memory-management-and-shared-memory)
- host-backed UART files rather than a resident filesystem, as described in
  [`8.9 PicoOS paths, working directories, and host operations`](#89-picoos-paths-working-directories-and-host-operations)
- eight descriptors per process (0–7), set by
  [`FILE_DESCRIPTOR_COUNT`](kernel/filesystem/file_descriptor.header#L6), with
  copied descriptor state rather than shared open-file descriptions, as
  described in [`8.1 Per-process file-descriptor table`](#81-per-process-file-descriptor-table)
- cyclic process selection (Lazy Round Robin) rather than ready-queue rotation (Round Robin), as described in
  [`6.1.1 Algorithm and Round Robin comparison`](#611-algorithm-and-round-robin-comparison)
- non-preemptive kernel execution and deferred rescheduling, as explained in
  [`2.5.2 Kernel non-preemption and deferred rescheduling`](#252-kernel-non-preemption-and-deferred-rescheduling)
- fixed/default process heap and stack sizing with no dynamic stack growth, as
  described in [`4.2.2.1 Initial user process stack`](#4221-initial-user-process-stack)
- limited formatting and scanning, shell parsing, and standard-library subsets,
  as described in [`10.2.9 stdio: streams, formatting, and scanning`](#1029-stdio-streams-formatting-and-scanning),
  [`12.4 Command parsing, expansion, and execution`](#124-command-parsing-expansion-and-execution), and
  [`10.2 Library overview and dependencies`](#102-library-overview-and-dependencies)
- no implemented PicoOS-specific physical RETI CPU or hardware timer: the
  emulator's instruction-count timer provides reproducible preemption, not
  exact elapsed-time behavior, so programs that require exact timing, such as
  games, cannot be supported reliably
- no sound hardware or dedicated LCD monitor: terminal I/O and host-backed
  files are provided through the emulator and host operating system rather
  than PicoOS devices
- statically linked program images, with no dynamic loader, shared libraries,
  or dynamically linked libc, the C library is a reduced PicoOS subset linked
  through [`libstart`](library/start/libstart.picoc)
- familiar POSIX-like names without full POSIX semantics

# Appendix: Inspecting `.bin` files with `hexyl`
[\[↑ TOC\]](#contents)

[`hexyl`](https://github.com/sharkdp/hexyl) shows how image offsets become file bytes. RETI words use four
big-endian bytes. The five-word loader header occupies the first 20 bytes,
with cell-based addresses and sizes stored at these byte offsets:

| File byte offset | Header word | Meaning |
| --- | --- | --- |
| `0x00` | Code start | Offset of executable code within the loaded image |
| `0x04` | Data start | Offset used to initialize the data-segment register |
| `0x08` | Heap start | Start of the process heap within its allocated memory |
| `0x0c` | Heap size | Number of cells reserved for the process heap, `ff ff ff ff` selects the kernel default |
| `0x10` | Stack start | Initial stack offset, `ff ff ff ff` denotes automatic stack placement |

The UART [`load`](#123-uart-host-service-protocol) word count precedes the file transfer. It is not stored
in the `.bin` file. Process loading reads the same five-word header.

These commands show the header and first 64 payload bytes. `-g 4` groups
words, `-s` skips bytes, and `-n` limits output:

```console
$ hexyl -g 4 -n 20 binary/user/echo.bin
$ hexyl -g 4 -s 20 -n 64 binary/user/echo.bin
```

A header value `00000020` means 32 cells. Image word 32 is at file byte
`20 + 4 × 32 = 148`, including the header.

A negative skip counts from the file end. This command displays the last
64 bytes, following [hexyl's negative-offset examples](https://github.com/sharkdp/hexyl/releases/tag/v0.9.0) and keeping the negative value attached to its option:

```console
$ hexyl --skip=-64 -n 64 binary/user/echo.bin
```
