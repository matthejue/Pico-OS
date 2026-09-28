# PicoOS release

- Linux and macOS: run `./start-picoos.sh`
- Windows: run `.\start-picoos.ps1` in PowerShell
- Android: install Termux, then run `./start-picoos.sh`

The launchers check for the RETI Emulator and PicoC Compiler and offer to
download their latest GitHub release binaries when either tool is missing. The
download scripts select the correct binaries for the current operating system
and architecture.

The launchers look for `reti_emulator` in this directory and then in `PATH`.
Use `--reti-emulator PATH` with the shell script or `-RetiEmulator PATH` with
the PowerShell script to select a custom emulator executable. The complete
launcher choices are:

| Behavior | `start-picoos.sh` | `start-picoos.ps1` |
| --- | --- | --- |
| Enable DMA loading | `--dma` or `-M` | `-Dma` or `-M` |
| Start without the Debug TUI | `--notui` or `-N` | `-NoTui` or `-N` |
| Show help | `--help` or `-h` | `-Help` or `-h` |
| Pass remaining emulator options | `-- EMULATOR_ARGS...` | `-- EMULATOR_ARGS...` |

If DMA was not selected as an option, the launcher asks whether to enable it.
DMA copies executable words from UART directly into SRAM and lets the CPU do
other work while a process image arrives. Answer no to use the simpler polling
path.

The launcher also offers the latest PicoOS cheat sheet. Accepting downloads
`picoos-cheatsheet.pdf` into this directory. Declining adds its release link to
the end of this README. Either choice is recorded there so the question is not
repeated on later starts.

To reach the terminal through the Debug TUI, use `(c)ontinue` by pressing `c`
to run the bootloader, kernel, and init process startup. Then select `(V)iew
raw terminal`. Press `Ctrl+]` to return to the Debug TUI.

At the `PicoOS>` prompt, a program can be run by its executable name, a
relative path, or an absolute PicoOS path inside the runtime directory. The
shell finds names such as `echo.bin` in `/user`. For example, this pipeline redirects its final
standard output to a file and reads it back:

```console
PicoOS> echo.bin "kernel\ncontext switch\nscheduler" | sed.bin s/context switch/dispatcher/ > topics.txt
PicoOS> cat.bin topics.txt
kernel
dispatcher
scheduler
```

The extracted release directory is PicoOS `/`: `/kernel`, `/boot`, `/system`,
`/user`, `/config`, and `/device` refer to directories inside this runtime.
PicoOS can create, read, write, move, and remove files there. Host `/tmp` is
not mounted, and directory listings contain no artificial `tmp` entry. If you
create a `tmp` directory inside this runtime, PicoOS can access it at `/tmp`
as an ordinary directory.

`..` cannot move above PicoOS `/`. The emulator rejects symlinks, Windows
junctions, and file access through hard links or special host files. Use the
updated RETI-Emulator with these binaries. Older emulator builds do not
provide this filesystem boundary.

`device/terminal.dev` is a dummy release marker for PicoOS's kernel terminal.
Programs access the terminal through the virtual path `/device/terminal.dev`, the
dummy file does not contain terminal data.
