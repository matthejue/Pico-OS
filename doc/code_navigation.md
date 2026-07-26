# PicoC code navigation

VS Code treats `*.picoc` and `*.header` files as C and uses clangd as the only
code-navigation provider. Microsoft C/C++ IntelliSense is disabled for this
workspace because running both providers can produce conflicting F12 results.

`compile_commands.json` is generated from the current source tree rather than
maintained by hand. The `PicoOS: Refresh code index` VS Code task runs whenever
the repository folder opens. VS Code may ask once for permission to run
automatic tasks.

After adding, moving, renaming, or deleting PicoC files during an open session,
run:

```sh
make code-index
```

clangd normally notices the changed compilation database. If an old result
remains in memory, run `clangd: Restart language server` from the VS Code
command palette once.
