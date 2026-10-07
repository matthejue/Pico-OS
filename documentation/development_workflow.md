# PicoOS development workflow

This guide covers building and running PicoOS from a source checkout. Readers
who only want to run a published version should use the release-archive steps
in the main [README](../README.md#build-and-run).

## Export the README as PDF

The VS Code task `PicoOS: Create README PDF` runs the same export as this
command from the repository root:

```console
$ make readme-pdf
```

The export requires Pandoc 3.6, XeLaTeX, Chromium or Google Chrome, Node.js 24
or newer, Yarn, and the DejaVu Serif and DejaVu Sans Mono fonts. Set
`README_PDF_BROWSER=/path/to/browser` to select another browser executable.
The target installs pinned Mermaid CLI and Puppeteer versions into the ignored
`.readme-pdf/` directory when needed. The
[`Mermaid filter`](readme_pdf_mermaid.lua) renders diagrams as vector PDFs
using the [`rendering configuration`](readme_pdf_mermaid.json), then XeLaTeX
embeds them into `README.pdf`. The
[`PDF header`](readme_pdf_header.tex) selects fonts, supports the six nested
list levels in the contents, and allows long code lines to wrap without
changing the Markdown source.

Ubuntu CI installs `lmodern` explicitly because the Pandoc LaTeX template
requires it and the minimal TeX installation omits recommended packages.
Terminal recordings appear as text links in the PDF, so exporting does not
fetch their external preview images.

## Build and boot from source

The build expects `picoc_compiler`, `reti_emulator`, and `make` on `PATH`.
From the repository root, the normal bootloader path is:

```console
$ make bootload
```

This builds the verified release tree under [`binary/`](../binary/), including
the bootloader, kernel, system programs, user programs, configuration, launcher
scripts, and device markers. It then starts RETI Emulator in the Debug TUI with
the EPROM bootloader. The final emulator invocation is equivalent to:

```console
$ cd binary
$ ../run_reti_emulator_isolated.sh -n 5 -e ./boot/bootloader.reti \
    -d -c -O -r 262144 \
    -S kernel/kernel.sections -D kernel/kernel.debuginfo
```

The command runs inside `binary/` because that directory becomes PicoOS `/`
for runtime host-file requests. Its emulator options establish the boot and
debug environment:

| Option | Purpose |
| --- | --- |
| `-e ./boot/bootloader.reti` | Loads the PicoOS bootloader into the modeled EPROM |
| `-r 262144` | Provides 2^18 addressable 32-bit SRAM words |
| `-d -c` | Opens the commented Debug TUI |
| `-S kernel/kernel.sections` | Supplies the compiler-generated kernel memory layout |
| `-D kernel/kernel.debuginfo` | Supplies source and debug metadata |
| `-O` | Enables the modeled operating-system context needed by the dispatcher's first `RTI` |
| `-n 5` | Declares the five interrupt service routine entries installed by the bootloader |

[`run_reti_emulator_isolated.sh`](../run_reti_emulator_isolated.sh) gives each
run a temporary peripheral-state directory and removes it afterward. This
prevents one development run's emulated device state from affecting another.

## Reaching the shell from a source checkout

The source workflow can open either the debugger or the PicoOS terminal
directly. These targets all boot through the generated EPROM image:

- `make bootload` opens the Debug TUI. Press `c`, then Enter, to continue. Press
  capital `V` for the raw UART terminal, where arrow keys, `Ctrl+C`, and
  `Ctrl+Z` reach PicoOS. `Ctrl+]` returns to the debugger. Lowercase `v` opens
  the normal terminal and Escape returns from it.
- `make bootload-dma` uses the same Debug TUI path and enables DMA process
  loading.
- `make bootload-notui` omits the Debug TUI and connects the invoking terminal
  directly to PicoOS.
- `make bootload-notui DMA=1` combines the direct terminal with DMA loading.

At the `PicoOS>` prompt, executable names are normally resolved through
`PATH=/user` and run directly. For kernel development, the shell also exposes
the lower-level `load` and `run` built-ins. They make the two process phases
visible. A fresh boot normally gives init PID 1 and the shell PID 2, so this
example creates PID 3. Use the PID printed by your own session if it differs:

```console
PicoOS> load user/echo.bin
process with pid 3 created
PicoOS> run 3 hello PicoOS
hello PicoOS
```

`load` creates a PCB whose state attribute is `NEW`. `run` prepares its initial
arguments, changes the state attribute to `READY`, and waits for the foreground
process. [`4.1.1 Process States and Transitions`](../README.md#411-process-states-and-transitions)
and [`4.2 Loading and Starting a Process`](../README.md#42-loading-and-starting-a-process)
connect these shell operations to the kernel structures.

## Build and run targets

The following table records the Make targets used for firmware development.
Test targets remain with their execution model in
[`14.2.1 Make targets`](../README.md#1421-make-targets).

| Command | Actual behavior |
| --- | --- |
| `make firmware` | Alias for `release-tree`, so it builds the complete verified runtime tree rather than only the bootloader and kernel |
| `make release-tree` | Builds all release binaries, configuration, scripts, README, and device markers under `binary/`, then removes files that do not belong to the release |
| `make verify-release-tree` | Rebuilds the release tree and checks that every expected file exists, the shell scripts are executable, and no unexpected files remain |
| `make release-archive` | Verifies the release tree and creates `pico-os-runtime.tar.gz` from its contents |
| `make rebuild-release` | Runs `make clean`, then creates the release archive again |
| `make clean-firmware` / `make rebuild-firmware` | Removes generated firmware files, or removes and rebuilds the complete firmware tree |
| `make device` / `make devices` | Adds the terminal and null device markers under `binary/device/` |
| `make eprom` | Builds `boot/bootloader.reti` |
| `make kernel` | Builds `binary/kernel/kernel.bin` and its prerequisites |
| `make system` / `make user` | Both depend on `release-tree`, so either command builds the complete release tree |
| `make run-firmware` | Builds the direct kernel image and its minimum runtime files, then starts that kernel in the Debug TUI without the EPROM boot path |
| `make bootload` | Builds the release tree and boots through `binary/boot/bootloader.reti` in the Debug TUI |
| `make bootload-debug` | Recompiles the bootloader and kernel directly with source/debug metadata, refreshes the release tree, and boots in the Debug TUI |
| `make bootload-dma` | Runs `make bootload DMA=1` |
| `make bootload-notui` | Builds the release tree and boots through the EPROM image without the Debug TUI |
| `make bootload-notui DMA=1` | Uses the direct terminal path with DMA process loading enabled |

Older documentation referred to `make run-kernel`, but that phony name has no
recipe or prerequisites. Use `make run-firmware` for the implemented
direct-kernel workflow.

## Building the release tree and archive

`make release-tree` copies only the files named by `RELEASE_FILES` into
`binary/`. `make verify-release-tree` checks that set before packaging. The
local archive command is:

```console
$ make release-archive
```

This writes `pico-os-runtime.tar.gz` with the runtime directories and the four
launcher/download-script variants at the archive root. The tagged-release job
in [`.github/workflows/build.yml`](../.github/workflows/build.yml) performs the
same release-tree build and verification, then publishes that archive as a
GitHub release asset. A separate job generates `README.pdf` from the tagged
source, including its diagrams, and uploads it to the same release. Publishing
waits for both builds to succeed and fails if either asset is missing. Manual
workflow runs also build both artifacts; publishing requires a `v*` tag.

## Documentation diagrams

Keep README diagrams wide, use boxes with sharp corners, and use consistent
labels across related figures. Show relationships from the implementation and
keep the diagrams readable on presentation slides. Use Mermaid for flowcharts
and SVG for precise memory layouts, then render the result to check text and
arrows.

All README visuals share the palette and typography in
[`diagram_style.py`](diagram_style.py): Cantarell, sharp rectangular corners,
dark ink, gray outlines and grouping, pale teal allocated data, and pale green
free data. Keep the SVG canvas transparent; generators must omit full-canvas
background rectangles. Teal arrows show references, green arrows show addresses
or the active process, and gray arrows show copies. Amber is reserved for an existing focus,
changed field/block, or waiting state; ordinary headers and containers stay
neutral. Keep explicit labels and line patterns so meaning does not depend on
color alone.

After editing that style, run `python3 documentation/style_readme_diagrams.py`
and `python3 documentation/generate_timer_interval_plot.py` from the repository
root. This updates the existing SVGs, Mermaid appearance directives and PDF
rendering configuration without rebuilding diagram content. Mermaid spacing,
directions and sequence options are retained. SVG generators apply the same
style when saving, so future content updates retain the appearance. Review
emphasis in the surrounding README context rather than treating every old
accent as necessary.
