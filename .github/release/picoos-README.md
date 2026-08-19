# PicoOS release

- Linux and macOS: run `./download-tools.sh`, then `./start-picoos.sh`
- Windows: run `.\download-tools.ps1`, then `.\start-picoos.ps1` in PowerShell
- Android: install Termux, then run `./download-tools.sh` and `./start-picoos.sh`

The download scripts select the current operating system and architecture, then
install the latest RETI Emulator and PicoC Compiler GitHub release binaries in
this directory. Run the download script again at any time to update both tools.

The launchers look for `reti_emulator` in this directory and then in `PATH`.
Use `--reti-emulator PATH` with the shell script or `-RetiEmulator PATH` with
the PowerShell script to select a custom emulator executable.

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
Programs access the terminal through the virtual path `/device/terminal`; the
dummy file does not contain terminal data.
