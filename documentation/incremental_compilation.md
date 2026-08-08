# Incremental PicoC compilation

PicoOS calls `picoc_compiler --show-input-files` directly. The reported input
list makes every build show whether the compiler used a `.picoc` source or a
cached `.reti_blocks`/`.st` pair.

## Cache ownership

The compiler stores cache metadata in the first line of each generated
`.reti_blocks` file. It records the source, all transitively included files,
their content hashes, relevant compiler settings, and a cache-format version.
The compiler reuses the matching `.reti_blocks` and `.st` files only when that
metadata still matches.

PicoOS no longer runs a separate Python wrapper to scan includes, hash files,
or validate artifact digests. Cache decisions therefore have one owner: the
PicoC compiler.

## Library tests

`make test-lib` uses `test/Makefile` to model each unique source and declared
dependency as one compilation unit. Compile-only commands use
`--dependency-file`, so Make also tracks the headers and included PicoC files
reported by the compiler. Unchanged units do not need another compiler
process; when a compiler process is required, its embedded cache validation
still decides whether compilation work can be reused.

After the units are ready, independent link and emulator jobs run in parallel.
`TEST_JOBS` controls their number and defaults to `nproc`. Each emulator gets a
new temporary `-f` directory, preventing concurrent jobs from sharing
`sram.bin`.

`TEST_BUILD_MODE=direct` remains available for comparison. It bypasses staged
artifacts and compiles each library test with its declared dependency sources.

## OS tests

Normal OS tests compile and assemble their programs before starting the test
sessions. In the default staged mode, each compilation unit is invoked
separately so shared libraries can be safely reused, then the final program is
linked only from `.reti_blocks` files. `TEST_BUILD_MODE=direct` instead builds
each merged `.reti` from `.picoc` inputs and does not read `.reti_blocks` or
`.st` files. Ready test directories run concurrently with `TEST_JOBS` workers.

Assembly and OS emulator processes both use private temporary peripheral
directories. Fast OS tests still intentionally use one shared boot per group,
but that boot also has its own temporary directory.

## Invalidation

The compiler recompiles a unit when its source, an included file, a relevant
option, or the cache format changes, or when either reusable artifact is
missing. `-i` and `-w` explicitly request compiler output and therefore force
compilation. Normal staged test compilation omits those options so valid
artifacts remain reusable.
