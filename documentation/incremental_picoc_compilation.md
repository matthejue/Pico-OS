# Incremental PicoC compilation implementation

PicoC compilation produces a reusable pair for every translation unit:

- `<name>.reti_blocks` contains RETI blocks and embedded cache metadata
- `<name>.st` contains the symbol table used while linking those blocks

The compiler validates this pair before syntax checking or starting a
compilation worker. It compares the embedded source path, compiler settings,
cache version, and hashes of the source and every file reached by preprocessing.
On a hit, the source target is replaced internally by its existing artifact
pair. `--show-input-files` prints that choice.

PicoOS deliberately does not duplicate this validation. Its Make rules only
coordinate unique units, final links, and parallel test jobs. Library-test
compile-only rules pass `--dependency-file`; the compiler writes an exact Make
dependency rule from the same preprocessing metadata used by its cache.

The relevant PicoOS implementation locations are:

- `test/Makefile`: unique staged units and parallel library-test jobs
- `run_lib_test_case.sh`: staged linking and isolated library emulation
- `run_sys_tests.sh`: test selection, parallel Make invocation, and summaries
- `run_os_tests.py`: staged OS-program builds and parallel isolated OS sessions
- `Makefile`: `TEST_JOBS`, build-mode selection, and direct compiler calls

Every RETI emulator invocation used by the test runners receives a freshly
created peripheral directory through `-f`. This isolates `sram.bin` even when
several emulator processes execute at the same time.
