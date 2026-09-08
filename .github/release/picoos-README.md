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
the PowerShell script to select a custom emulator executable. Add `--dma` to
the shell command or `-Dma` to the PowerShell command to enable DMA loading.
Add `--notui` to the shell command or `-NoTui` to the PowerShell command to
start directly in the terminal without the Debug TUI.

To reach the terminal through the Debug TUI, use `(c)ontinue` by pressing `c`
to run the bootloader, kernel, and init process startup. Then select `(V)iew
raw terminal`. Press `Ctrl+]` to return to the Debug TUI.

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
Programs access the terminal through the virtual path `/device/terminal.dev`; the
dummy file does not contain terminal data.
