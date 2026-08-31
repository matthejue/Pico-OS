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

PicoOS exposes the host filesystem through RETI-Emulator UART services,
including per-process working directories, directory listing, creation, and
removal. The emulator uses `getcwd` once to provide its startup directory and
checks later `chdir()` targets without changing its own working directory.
Linux and macOS use `getcwd`, `stat`, `mkdir`, `opendir`, `unlink`, and `rmdir`
directly. The Windows emulator build uses the corresponding
underscore-prefixed functions where necessary; directory listing requires the
`dirent` compatibility supplied by the supported MSYS2 build environment.
Native Windows emulator builds without that compatibility are not supported
for these host-filesystem services.

`device/terminal.dev` is a dummy release marker for PicoOS's kernel terminal.
Programs access the terminal through the virtual path `/device/terminal.dev`; the
dummy file does not contain terminal data.
