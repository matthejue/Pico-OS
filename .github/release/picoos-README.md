# PicoOS release

- Linux and macOS: run `./start-picoos.sh`
- Windows: run `.\start-picoos.ps1` in PowerShell
- Android: install Termux, then run `./start-picoos.sh`

The launchers look for `reti_emulator` in this directory and then in `PATH`.
Use `--reti-emulator PATH` with the shell script or `-RetiEmulator PATH` with
the PowerShell script to select a custom emulator executable.
