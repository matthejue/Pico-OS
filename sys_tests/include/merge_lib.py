#!/usr/bin/env python3

from pathlib import Path
import sys

PROJECT_ROOT = Path("/home/areo/Documents/Studium/Pico-OS")
OUTPUT_DIR = PROJECT_ROOT / "sys_tests" / "include"

MODES = {
    "1": {
        "picoc": PROJECT_ROOT / "lib" / "malloc" / "malloc.picoc",
        "header": PROJECT_ROOT / "lib" / "malloc" / "malloc.h",
        "output": OUTPUT_DIR / "malloc.h",
    },
    "2": {
        "picoc": PROJECT_ROOT / "lib" / "mutex" / "mutex.picoc",
        "header": PROJECT_ROOT / "lib" / "mutex" / "mutex.h",
        "output": OUTPUT_DIR / "mutex.h",
    },
    "3": {
        "picoc": PROJECT_ROOT / "lib" / "stdio" / "stdio.picoc",
        "header": PROJECT_ROOT / "lib" / "stdio" / "stdio.h",
        "output": OUTPUT_DIR / "stdio.h",
    },
    "4": {
        "picoc": PROJECT_ROOT / "lib" / "unistd" / "unistd.picoc",
        "header": PROJECT_ROOT / "lib" / "unistd" / "unistd.h",
        "output": OUTPUT_DIR / "unistd.h",
    },
    "5": {
        "picoc": PROJECT_ROOT / "lib" / "string" / "string.picoc",
        "header": PROJECT_ROOT / "lib" / "string" / "string.h",
        "output": OUTPUT_DIR / "string.h",
    },
}

TEST_HEAP_DEFINE = "#define HEAP_SIZE  (5 * 4)     // heap size in words"


def merge_files(picoc_path: Path, header_path: Path, output_path: Path) -> None:
    picoc_text = picoc_path.read_text()
    header_text = header_path.read_text().rstrip("\n")

    include_line = f'#include "{header_path.name}"'
    if include_line not in picoc_text:
        raise ValueError(f'Could not find {include_line!r} in {picoc_path}')

    merged_text = picoc_text.replace(include_line, header_text, 1)
    if output_path.name == "malloc.h":
        merged_text = merged_text.replace(
            "#define HEAP_SIZE  (1024 * 256)     // heap size in words",
            TEST_HEAP_DEFINE,
            1,
        )
    output_path.write_text(merged_text)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "1"
    config = MODES.get(mode)
    if config is None:
        print("usage: merge_lib.py [1|2|3|4|5]", file=sys.stderr)
        return 1

    try:
        merge_files(config["picoc"], config["header"], config["output"])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote merged file to {config['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
