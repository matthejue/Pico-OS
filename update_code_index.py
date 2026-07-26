#!/usr/bin/env python3

import json
import shutil
from pathlib import Path


root = Path(__file__).resolve().parent
compiler = shutil.which("gcc") or "gcc"
sources = sorted(
    path
    for path in root.rglob("*.picoc")
    if not any(part.startswith(".") for part in path.relative_to(root).parts)
)

commands = []
for source in sources:
    commands.append(
        {
            "directory": str(root),
            "arguments": [
                compiler,
                "-x",
                "c",
                "-std=gnu11",
                "-fno-builtin",
                "-Dasm(...)=",
                "-Ddebug=",
                f"-I{root}",
                "-fsyntax-only",
                str(source),
            ],
            "file": str(source),
        }
    )

output = root / "compile_commands.json"
temporary_output = output.with_suffix(".json.tmp")
temporary_output.write_text(json.dumps(commands, indent=4) + "\n")
temporary_output.replace(output)
print(f"Indexed {len(sources)} PicoC source files")
