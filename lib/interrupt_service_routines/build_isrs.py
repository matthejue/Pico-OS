#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


FILENAME_RE = re.compile(
    r"^(?P<index>\d{3})_(?P<name>[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)"
    r"(?:_(?P<device>KEYPRESS|INTTIMER)_(?P<priority>\d+))?\.reti$"
)


@dataclass(frozen=True)
class IsrFile:
    index: int
    name: str
    device: str | None
    priority: int | None
    path: Path
    lines: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Combine numbered ISR files such as 000_name.reti into a single "
            "isrs.reti file with IVTE entries at the top."
        )
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=Path("."),
        help="Directory containing the numbered .reti files. Defaults to the current directory.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("isrs.reti"),
        help="Output file path. Defaults to ./isrs.reti.",
    )
    return parser.parse_args()


def load_isr_files(directory: Path) -> list[IsrFile]:
    isr_files: list[IsrFile] = []

    for path in sorted(directory.glob("*.reti")):
        match = FILENAME_RE.fullmatch(path.name)
        if not match:
            continue

        raw_lines = path.read_text(encoding="utf-8").splitlines()
        if not raw_lines:
            raise ValueError(f"{path.name} is empty.")

        isr_files.append(
            IsrFile(
                index=int(match.group("index")),
                name=match.group("name"),
                device=match.group("device"),
                priority=int(match.group("priority")) if match.group("priority") else None,
                path=path,
                lines=raw_lines,
            )
        )

    if not isr_files:
        raise ValueError(
            f"No ISR files matching NNN_<name>.reti were found in {directory}."
        )

    expected = list(range(isr_files[0].index, isr_files[0].index + len(isr_files)))
    actual = [entry.index for entry in isr_files]
    if actual != expected:
        raise ValueError(
            "ISR file indices must be consecutive. "
            f"Found {actual}, expected {expected}."
        )

    return isr_files


def build_ivte_line(address: int, entry: IsrFile) -> str:
    parts = ["IVTE", str(address)]
    if entry.device is not None:
        parts.append(entry.device)
        parts.append(str(entry.priority))
    return " ".join(parts)


def build_output(entries: list[IsrFile]) -> str:
    header_size = len(entries)
    current_address = header_size
    ivte_lines: list[str] = []
    body_lines: list[str] = []

    for entry in entries:
        ivte_lines.append(build_ivte_line(current_address, entry))
        body_lines.extend(entry.lines)
        current_address += len(entry.lines)

    return "\n".join(ivte_lines + body_lines) + "\n"


def main() -> int:
    args = parse_args()
    directory = args.directory.resolve()
    output = args.output

    try:
        entries = load_isr_files(directory)
        output_text = build_output(entries)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output.write_text(output_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
