# VSCode File Associations C

#### You:
I have certain fles in vscode that are c code, but I'm not allowed to call those files with extension .c, but I have to call those files .picoc and .header for .h files. Can I somehow make vscode still treat those files likes normal C Files with language server support etc?

#### ChatGPT:
I’ll verify the current VS Code settings names, then give you the minimal setup for syntax highlighting and C/C++ language server behavior for `.picoc` and `.header`.

Yes. Add file associations so VS Code opens those extensions in C language mode.

In your workspace, create or edit:

```json
// .vscode/settings.json
{
  "files.associations": {
    "*.picoc": "c",
    "*.header": "c"
  }
}
```

VS Code’s `files.associations` setting maps glob patterns to language identifiers, and the C language identifier is `c`. The identifier is case-sensitive. ([Visual Studio Code](https://code.visualstudio.com/docs/languages/identifiers?utm_source=chatgpt.com), [Visual Studio Code](https://code.visualstudio.com/docs/editor/glob-patterns?utm_source=chatgpt.com))

That should give you normal C syntax highlighting, formatting hooks, and C/C++ extension IntelliSense behavior, assuming you have Microsoft’s **C/C++** extension installed. The Microsoft C/C++ extension uses VS Code file extension associations to map files to C, C++, or CUDA. ([GitHub](https://github.com/microsoft/vscode-cpptools/issues/10494?utm_source=chatgpt.com))

For better language-server results, also make sure your project has one of these:

```json
// .vscode/c_cpp_properties.json
{
  "configurations": [
    {
      "name": "Linux",
      "includePath": [
        "${workspaceFolder}/**"
      ],
      "defines": [],
      "compilerPath": "/usr/bin/gcc",
      "cStandard": "c11",
      "intelliSenseMode": "linux-gcc-x64"
    }
  ],
  "version": 4
}
```

or, preferably, a `compile_commands.json` if your project has a real build system.

One important distinction: this only makes **VS Code** treat the files as C. Your compiler or build system may still ignore `.picoc` files unless configured separately. For example, in CMake you can force a source file’s language with:

```cmake
set_source_files_properties(main.picoc PROPERTIES LANGUAGE C)
```

CMake determines a source file’s language from the extension unless the `LANGUAGE` property is set. ([CMake](https://cmake.org/cmake/help/latest/prop_sf/LANGUAGE.html?utm_source=chatgpt.com))

For `.header`, mapping it to `"c"` is fine if these are C headers. If they are sometimes included from C++ files, map them to `"cpp"` instead, or keep separate naming patterns if possible.
