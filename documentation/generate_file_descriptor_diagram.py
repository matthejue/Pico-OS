"""Generate the SRAM and descriptor-allocation view in README section 8.1.

Run with Python 3. Reuse the existing memory colours and sharp-corner SVG
style. The lower row expands the Kernel Heap, with omitted allocations
marked explicitly. Descriptor 3 is an example opened regular file.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import (
    ALLOCATED, FOCUS, FREE, HEADER, HEAP_EMPHASIS, MUTED, POINTER,
)


def main():
    figure = Figure(
        "file-descriptors",
        "Per-process file-descriptor allocations in SRAM",
        "The Kernel Image contains .ivt, .text and .data, followed by the "
        "Kernel Heap, Kernel Stack, and Process and Shared Data Heap. Dashed "
        "lines expand the Kernel Heap below. PCB 1, FileDescriptorTable, the "
        "eight-element FileDescriptor array, and copied path strings occupy "
        "separate kmalloc payloads, each preceded by a BlockHeader. PCB 1's "
        "file_descriptors pointer reaches the table payload. Its entries "
        "pointer reaches the start of the contiguous array, whose elements "
        "have no individual block headers. Descriptor 3's path points to a "
        "copied /notes.txt string. Standard descriptors have separate terminal "
        "path copies, omitted along with other allocations. Header letters "
        "identify the illustrated blocks, not a fixed allocation order.",
        width=1669, height=686,
    )

    figure.row(80, 90, [
        ("ivt", 60, (".ivt",), MUTED),
        ("text", 110, (".text",), MUTED),
        ("data", 180, (".data", "kernel globals"), MUTED),
        ("kernel_heap", 690, ("PCBs · tables · entries · paths",), ALLOCATED),
        ("stack", 115, ("Kernel", "Stack", "grows ←"), MUTED),
        ("outer_a", 65, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("process", 230, ("Process Payload A", "image · user heap · stack"), ALLOCATED),
        ("outer_b", 65, ("Block", "Header B"), HEADER, "common/heap.header#L5"),
        ("free", 90, ("Free", "Payload B"), FREE),
    ])
    figure.band("ivt", "data", 170, "Kernel Image")
    figure.band("kernel_heap", "kernel_heap", 170, "Kernel Heap", HEAP_EMPHASIS)
    figure.band("stack", "stack", 170, "Kernel Stack")
    figure.band("outer_a", "free", 170, "Process and Shared Data Heap")
    figure.band("ivt", "stack", 200, "Kernel")
    figure.band("outer_a", "free", 200, "After the Kernel region")
    figure.box(382, 80, 690, 120, "none", FOCUS, 3)

    cells = []
    for letter, key, width in (
        ("A", "pcb", 210), ("B", "table", 245),
        ("C", "array", 560), ("D", "path", 210),
    ):
        cells.append((
            "header_" + letter, 70, ("Block", "Header " + letter),
            HEADER, "common/heap.header#L5",
        ))
        cells.append((key, width, (), ALLOCATED))
        if key == "pcb":
            cells.append(("omitted_before", 50, ("…",), MUTED))
    cells.append(("omitted_after", 50, ("…",), MUTED))
    figure.row(360, 210, cells)
    figure.band("header_A", "omitted_after", 570, "Kernel Heap · expanded", HEAP_EMPHASIS)
    # Start expansion guides below the SRAM hierarchy bands.
    figure.cells["kernel_heap"] = (382, 80, 690, 150)
    figure.expand("kernel_heap", "header_A", "omitted_after")

    def payload_label(key, value, y, link, size=19):
        x, _, width, _ = figure.cells[key]
        figure.label(x + width / 2, y, value, size=size, bold=True, link=link)

    payload_label("pcb", "PCB 1", 401, "kernel/process/process.header#L31", 22)
    payload_label("pcb", "ProcessControlBlock", 429,
                  "kernel/process/process.header#L31", 17)
    payload_label("table", "FileDescriptorTable", 414,
                  "kernel/filesystem/file_descriptor.header#L22", 20)
    payload_label("array", "FileDescriptor entries[0..7]", 400,
                  "kernel/filesystem/file_descriptor.header#L15", 21)
    payload_label("path", "Copied path", 418,
                  "kernel/filesystem/file_descriptor.header#L19", 21)
    path_x, _, path_width, _ = figure.cells["path"]
    figure.label(path_x + path_width / 2, 463, '"/notes.txt\\0"', size=22)
    figure.label(path_x + path_width / 2, 508, "path string", size=17)

    for key, name, link in (
        ("pcb", "file_descriptors", "kernel/process/process.header#L42"),
        ("table", "entries", "kernel/filesystem/file_descriptor.header#L23"),
    ):
        x, _, width, _ = figure.cells[key]
        figure.box(x + 14, 452, width - 28, 40, MUTED)
        figure.label(x + width / 2, 478, name, size=19, link=link)

    array_x, _, _, _ = figure.cells["array"]
    for index in range(8):
        x = array_x + index * 70
        figure.box(x, 418, 70, 152, ALLOCATED)
        figure.label(x + 35, 443, str(index), size=20, bold=True)
        for row, (name, line) in enumerate((
            ("kind", 16), ("flags", 17), ("offset", 18), ("path", 19),
        )):
            figure.label(x + 35, 469 + row * 25, name, size=16,
                         link=f"kernel/filesystem/file_descriptor.header#L{line}")
        if index == 3:
            figure.box(x + 2, 420, 66, 148, "none", FOCUS, 3)

    # These pointers terminate at payload addresses, immediately after headers.
    for source, target, lane in (("pcb", "table", 296), ("table", "array", 324)):
        x, _, width, _ = figure.cells[source]
        target_x, _, _, _ = figure.cells[target]
        figure.parts.append(
            figure_pointer(
                f"M {x + width - 14} 472 H {x + width} "
                f"V {lane} H {target_x + 12} V 360"
            )
        )
    figure.parts.append(figure_pointer(
        f"M {array_x + 3 * 70 + 35} 552 V 628 H {path_x + 24} V 570"
    ))
    figure.label(32, 660, "Other allocations omitted · one descriptor path shown", size=16,
                 anchor="start")
    figure.save()


def figure_pointer(path):
    return (f'<path d="{path}" fill="none" stroke="{POINTER}" '
            f'stroke-width="2.5" marker-end="url(#{POINTER[1:]})"/>')


if __name__ == "__main__":
    main()
