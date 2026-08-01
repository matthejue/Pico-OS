# Incremental PicoC compilation

PicoC compilation produces two reusable files for each translation unit:

- `<name>.reti_blocks` contains the compiled RETI blocks
- `<name>.st` contains the symbol table needed when those blocks are linked

The PicoC compiler can load this pair through the same path used for explicit
`.reti_blocks` linker inputs. Incremental compilation therefore does not need
a second representation of a compiled unit: when a `.picoc` source is still
up to date, the compiler replaces that source's compilation target internally
with its existing `.reti_blocks` and `.st` target.

## Compiler-level cache

The compiler stores the cache description in the first line of the generated
`.reti_blocks` file. Its form is:

```text
# @picoc-cache {"inputs":[...],"options":{...},"source":"...","version":1}
```

The rest of the file remains ordinary RETI-block text. When the file is loaded,
the compiler removes this private line before parsing the RETI blocks. The
`.st` format is unchanged.

The cache description contains:

- the canonical path of the `.picoc` source
- a SHA-256 hash for the source and every transitively included file
- the compilation options that can affect preprocessing or the generated
  artifact
- a cache-format version

The relevant options currently are the optimization level, debug-metadata
generation, normal and double verbosity, include paths, and maximum include
depth. Include paths are stored as canonical absolute paths so equivalent
relative spellings are compared consistently.

### Recording dependencies

Dependency information comes from the compiler's preprocessor rather than a
second include scanner. As the preprocessor reads the root source and follows
each `#include`, it records the canonical path and content hash of every file
that actually contributed to that translation unit. This also records nested
headers and the header selected through `-I` search paths.

The collected hashes are held in thread-local compilation state. This matters
because independent PicoC files are normally compiled in parallel. When the
RETI-block pass writes a per-source `.reti_blocks` file, it prepends the cache
description belonging to that worker's source.

### Reuse decision

Before syntax checking or starting compilation workers, the compiler examines
each `.picoc` build target:

1. Both the matching `.reti_blocks` and `.st` files must exist.
2. The `.reti_blocks` file must begin with valid cache metadata of the current
   version.
3. The recorded source path and compilation options must match the current
   invocation.
4. Every recorded input must still exist and have the same content hash.
5. If all checks pass, the `.picoc` target is replaced with an external
   `.reti_blocks` target using the matching `.st` file.

Only the remaining stale `.picoc` targets are passed to the external C syntax
check and through the PicoC compilation passes. Cached and newly compiled
translation units then produce the same `(RETI-block AST, symbol table, block
map)` result, so linking does not need separate cache-specific behavior.

While loading a cached artifact, the compiler also restores any serialized
source locations, call targets, and return markers used for debug information.
Thus an artifact compiled with `-g` remains usable by a later debug link.

### Invalidation rules

| Change | Compiler action |
| --- | --- |
| Source contents change | Recompile |
| A directly or transitively included file changes | Recompile |
| A relevant compilation option changes | Recompile |
| Either `.reti_blocks` or `.st` is missing | Recompile |
| Cache metadata is absent, malformed, or from another version | Recompile |
| Only a file timestamp changes while its contents remain identical | Reuse |
| `-i` or `-w` is requested directly from the compiler | Recompile |

The last rule preserves the meaning of `-i` and `-w`: the compiler must run
when the caller asks it to print intermediate stages or rewrite intermediate
stage files. Artifacts created before cache metadata was introduced are
compiled once and become reusable afterward.

`COMPILE_CACHE_VERSION` in
[`src/option_handler.py`](../../PicoC-Compiler/src/option_handler.py) invalidates
older embedded metadata when the cache format or artifact compatibility
changes. The embedded cache does not automatically hash the compiler
executable; a compiler change that affects reusable artifacts must therefore
also advance this version.

## Pico-OS build wrapper

Pico-OS normally invokes the compiler through
[`compile_picoc.py`](../compile_picoc.py). This wrapper performs staged builds:
it orders sources using `// dependencies:`, compiles each source separately,
and links only the resulting `.reti_blocks` files.

The wrapper currently has its own outer cache. For each source it writes
`<name>.picoc_build.json`, containing a signature over:

- all forwarded compiler arguments
- the compiler executable's resolved path, modification time, and size
- the source and recursively discovered include files, including their paths
  and contents
- the wrapper's cache version

It also records digests of the generated `.reti_blocks` and `.st` files so a
link-modified or otherwise changed artifact is not reused as a compilation
unit.

If that signature and both artifact digests still match, the wrapper does not
invoke `picoc_compiler` for that source. Otherwise it removes the old wrapper
cache record, runs `picoc_compiler -c`, verifies that both artifacts were
produced, and writes the new record only after successful compilation.

Consequently Pico-OS builds can have two cache checks:

1. `compile_picoc.py` may reuse a translation unit before starting the
   compiler.
2. If the wrapper invokes `picoc_compiler`, the compiler can independently
   reuse embedded artifact metadata when its own rules allow it.

The wrapper layer is specific to Pico-OS's dependency ordering and staged link
workflow. The embedded compiler layer also works for direct compiler calls,
other projects, and arbitrary mixtures of `.picoc`, `.reti_blocks`, and `.st`
inputs.

## Why no generated Makefiles

The repository Makefile remains useful for project-level relationships such as
building the kernel, user programs, binary images, and emulator runs. Generated
Makefiles were not used for per-source reuse because the compiler already has
the authoritative preprocessing and artifact information, while compiler
commands can also be issued outside a fixed project directory layout.

A generated Makefile solution would need generated header-dependency data and
a separate representation of compiler arguments to avoid stale artifacts. It
would also create and maintain build files in every source directory. Keeping
the decision in the compiler makes `.reti_blocks` self-describing and gives
direct CLI calls the same behavior as Make-driven builds. Make can still decide
which final programs need linking; the compiler and wrapper decide whether an
individual translation unit needs compiling.

## Implementation locations

- Embedded metadata creation, validation, target replacement, and artifact
  loading: [`src/option_handler.py`](../../PicoC-Compiler/src/option_handler.py)
- Transitive include hashing:
  [`src/preprocessor.py`](../../PicoC-Compiler/src/preprocessor.py)
- Thread-local cache state:
  [`src/global_vars.py`](../../PicoC-Compiler/src/global_vars.py)
- Pico-OS staged compilation and outer signature cache:
  [`compile_picoc.py`](../compile_picoc.py)
- Pico-OS project targets using the wrapper: [`Makefile`](../Makefile)
