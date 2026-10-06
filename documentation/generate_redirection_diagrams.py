"""Generate the four descriptor snapshots in README section 12.6.

Each snapshot expands the same SRAM Kernel Heap into separately allocated
PCBs, tables, entry arrays and path strings. Only stored pointers have arrows.
Block letters and widths are illustrative, not allocator order or addresses.
Run with Python 3 from any directory. No external packages are required.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import (
    ALLOCATED, FOCUS, FREE, HEADER, HEAP_EMPHASIS, MUTED, POINTER,
)


FD = "kernel/filesystem/file_descriptor.header"
PCB = "kernel/process/process.header"
BLOCK = "common/heap.header#L5"
TERMINAL = "/device/terminal.dev"
OUTPUT = "/output.txt"


def pointer(figure, path):
    figure.parts.append(
        f'<path d="{path}" fill="none" stroke="{POINTER}" '
        f'stroke-width="2" marker-end="url(#{POINTER[1:]})"/>'
    )


def heap_block(figure, x, y, width, height, letter, lines):
    figure.box(x, y, 40, height, HEADER)
    for index, value in enumerate(("Block", "Header", letter)):
        figure.label(x + 20, y + height / 2 - 16 + index * 18,
                     value, size=11, bold=True, link=BLOCK)
    figure.box(x + 40, y, width, height, ALLOCATED)
    for index, (value, link) in enumerate(lines):
        figure.label(x + 40 + width / 2, y + 29 + index * 28,
                     value, size=16, bold=index == 0, link=link)


def descriptor_row(figure, y, process_number, entries, letters, changed):
    """Keep the eight array cells fixed across snapshots and both processes."""
    a, b, c, *path_letters = letters
    role = "shell" if process_number == 1 else "child"
    heap_block(figure, 32, y, 180, 104, a, (
        (f"PCB {process_number} · {role}", f"{PCB}#L31"),
        ("file_descriptors", f"{PCB}#L42"),
    ))
    heap_block(figure, 288, y, 170, 104, b, (
        ("FileDescriptorTable", f"{FD}#L22"),
        ("entries", f"{FD}#L23"),
    ))
    heap_block(figure, 534, y, 1192, 104, c, ())
    figure.label(1170, y - 13, "FileDescriptor entries[0..7] · one array allocation",
                 size=17, bold=True, link=f"{FD}#L15")
    pointer(figure, f"M 244 {y + 57} H 266 V {y - 25} H 342 V {y}")
    pointer(figure, f"M 470 {y + 57} H 510 V {y - 25} H 589 V {y}")

    roles = {0: "stdin", 1: "stdout", 2: "stderr", 3: "temporary", 6: "saved stdout"}
    kinds = {0: "STDIN", 1: "STDOUT", 2: "STDERR"}
    # Other standard paths exist, but only the three relevant slots are expanded.
    for index in range(8):
        x = 574 + index * 149
        destination = entries.get(index)
        fill = ALLOCATED if destination else FREE
        figure.box(x, y, 149, 104, fill)
        figure.label(x + 74.5, y + 25,
                     f"{index} · {roles[index]}" if index in roles else str(index),
                     size=16, bold=True)
        kind = "FILE" if destination == OUTPUT else kinds.get(index, "STDOUT")
        if destination is None:
            kind = "FREE"
        line = {"FREE": 9, "STDIN": 10, "STDOUT": 11, "STDERR": 12, "FILE": 13}[kind]
        figure.label(x + 74.5, y + 53, kind, size=16, link=f"{FD}#L{line}")
        figure.label(x + 74.5, y + 81,
                     "path" if destination else "path = NULL", size=16,
                     link=f"{FD}#L19")
        if index in changed:
            figure.box(x + 2, y + 2, 145, 100, "none", FOCUS, 3)

    for index, letter in zip((1, 3, 6), path_letters):
        center = 574 + index * 149 + 74.5
        destination = entries.get(index)
        if destination is None:
            figure.label(center, y + 164, "No path allocation", size=15)
            continue
        heap_block(figure, center - 145, y + 140, 250, 62, letter, (
            (f'"{destination}\\0"', f"{FD}#L19"),
        ))
        pointer(figure, f"M {center} {y + 88} V {y + 140}")
    figure.label(32, y + 180, "… other Kernel Heap blocks …", size=15, anchor="start")


def snapshot(slug, title, shell, *, child=None, changed=(), child_changed=()):
    figure = Figure(
        f"redirection-{slug}", title,
        "The SRAM overview contains the Kernel Image, Kernel Heap, Kernel Stack "
        "and Process and Shared Data Heap. The emulator host stores /output.txt "
        "outside SRAM. Dashed guides expand the Kernel Heap into PCB 1 for the "
        "shell, its FileDescriptorTable and its contiguous eight-entry array. "
        "Each object and each path string has its own BlockHeader. "
        "Only entries 1, 3 and 6 have their path allocations expanded. "
        "STDIN, STDOUT, STDERR, FILE and FREE abbreviate FILE_DESCRIPTOR constants. "
        "Amber outlines mark changed entries. Other allocations, flags and "
        "offsets are omitted. Pointers are solid arrows, not file-data transfers. "
        + ("PCB 2 and its independent descriptor allocations are expanded in "
           "the second row. " if child else "The child's pre-run table is omitted. ")
        + "Block letters and widths do not specify allocation order or sizes.",
        width=1800, height=795 if child else 535,
        show_address_direction=False,
    )
    figure.label(32, 28, "SRAM · lower addresses → higher addresses", size=16, anchor="start")
    figure.row(45, 70, [
        ("ivt", 55, (".ivt",), MUTED),
        ("text", 100, (".text",), MUTED),
        ("data", 130, (".data",), MUTED),
        ("kernel_heap", 480, ("PCBs · descriptor tables · entries · path strings",), ALLOCATED),
        ("stack", 105, ("Kernel", "Stack"), MUTED),
        ("outer_a", 45, ("Block", "Header A"), HEADER, BLOCK),
        ("shell", 180, ("Process Payload A", "shell image · heap · stack"), ALLOCATED),
        ("outer_b", 45, ("Block", "Header B"), HEADER, BLOCK),
        ("child", 150, ("Process Payload B", "child image · heap · stack"), ALLOCATED),
        ("other", 58, ("…",), MUTED),
    ])
    figure.band("ivt", "data", 115, "Kernel Image")
    figure.band("kernel_heap", "kernel_heap", 115, "Kernel Heap · kmalloc", HEAP_EMPHASIS)
    figure.band("stack", "stack", 115, "Kernel Stack")
    figure.band("outer_a", "other", 115, "Process and Shared Data Heap")
    figure.band("ivt", "stack", 145, "Kernel")
    figure.band("outer_a", "other", 145, "After the Kernel region")
    figure.focus("kernel_heap")

    figure.box(1430, 45, 338, 130, MUTED)
    figure.label(1599, 71, "Emulator host · outside SRAM", size=17, bold=True)
    figure.label(1599, 111, '"/output.txt"', size=20)
    figure.label(1599, 145, "File contents are stored here", size=17)

    figure.parts.append(
        '<path d="M 317 175 L 32 218 M 797 175 L 1766 218" '
        'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>'
    )
    descriptor_row(figure, 265, 1, shell, "ABCDEF", changed)
    if child:
        descriptor_row(figure, 525, 2, child, "GHIJKL", child_changed)
    figure.box(32, 218, 1734, 523 if child else 263, "none")
    figure.label(899, 768 if child else 508,
                 "Kernel Heap · expanded · each path box is a separate copied string",
                 size=17, bold=True)
    figure.save()


def main():
    initial = {0: TERMINAL, 1: TERMINAL, 2: TERMINAL}
    saved = {**initial, 3: OUTPUT, 6: TERMINAL}
    installed = {**initial, 1: OUTPUT, 6: TERMINAL}
    child = {**initial, 1: OUTPUT}
    snapshot("save", "Open the output file and save shell stdout", saved,
             changed=(3, 6))
    snapshot("install", "Install redirected shell stdout and close the temporary descriptor",
             installed, changed=(1, 3))
    snapshot("inherit", "Copy descriptors into the child's independent Kernel Heap allocations",
             installed, child=child, child_changed=(1,))
    snapshot("restore", "Restore shell stdout while the child keeps its output file",
             initial, child=child, changed=(1, 6))


if __name__ == "__main__":
    main()
