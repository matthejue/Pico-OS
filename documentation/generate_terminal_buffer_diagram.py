"""Generate the SRAM and embedded terminal view in README section 8.2.

The example has an empty ring and one foreground reader waiting for input.
Only stored pointers receive arrows. Ring indices are integer values.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import (
    ALLOCATED, FOCUS, FREE, HEADER, HEAP_EMPHASIS, METADATA, MUTED, POINTER,
)


def pointer(path, colour=POINTER):
    return (f'<path d="{path}" fill="none" stroke="{colour}" '
            f'stroke-width="2.5" marker-end="url(#{colour[1:]})"/>')


def main():
    figure = Figure(
        "terminal-input-buffer",
        "Global terminal storage and reader queue in SRAM",
        "The Kernel Image contains .ivt, .text and .data, followed by the "
        "Kernel Heap, Kernel Stack, and Process and Shared Data Heap. The "
        "expanded view shows the global struct Terminal terminal embedded in "
        "kernel .data. Its input_buffer is an embedded 128-cell array, followed "
        "by the integer indices input_head and input_tail, input_count, and the "
        "embedded wait_queue input_waiters. None of this terminal storage is "
        "allocated on a heap or preceded by a BlockHeader. In this example the "
        "ring is empty, both indices are zero, and input_count is zero. Buffer "
        "contents are unspecified. input_waiters.head and input_waiters.tail "
        "both point to PCB 1, the one foreground process waiting for input. "
        "PCB 1 is a separate Kernel Heap payload after Block Header A. Its "
        "state is PROCESS_STATE_BLOCKED, wait_next is NULL, and "
        "waiting_queue_ptr points back to the embedded input_waiters queue. "
        "Other globals, heap allocations and PCB fields are omitted. "
        "Descriptors select the terminal by device path, not a stored pointer.",
        width=1669, height=612, show_address_direction=False,
    )
    # Trim the space formerly reserved for the surrounding notes.
    figure.parts.append('<g transform="translate(0 -48)">')

    # Keep the overview's regions and widths consistent with section 8.1.
    figure.row(80, 90, [
        ("ivt", 60, (".ivt",), MUTED),
        ("text", 110, (".text",), MUTED),
        ("data", 180, (".data", "terminal"), MUTED,
         "kernel/filesystem/terminal.picoc#L12"),
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
    figure.focus("data")

    figure.row(360, 210, [
        ("other_globals_left", 70, ("…",), MUTED),
        ("terminal", 930, (), MUTED),
        ("other_globals_right", 40, ("…",), MUTED),
        ("header_a", 70, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("pcb", 425, (), ALLOCATED),
        ("other_allocations", 70, ("…",), MUTED),
    ])
    figure.band("other_globals_left", "other_globals_right", 570, "Kernel Image · .data")
    figure.band("header_a", "other_allocations", 570, "Kernel Heap", HEAP_EMPHASIS)
    # Connect the actual storage-box corners to their expanded regions.
    figure.expand("data", "other_globals_left", "other_globals_right")
    # Offset the heap's left guide along both box edges so it does not
    # coincide with the .data guide at their shared boundary.
    x, y, width, height = figure.cells["kernel_heap"]
    left, top, _, _ = figure.cells["header_a"]
    right, _, right_width, _ = figure.cells["other_allocations"]
    figure.parts.append(
        f'<path d="M {x + 24} {y + height} L {left + 24} {top} '
        f'M {x + width} {y + height} L {right + right_width} {top}" '
        'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>'
    )
    figure.box(102, 360, 930, 210, "none", FOCUS, 3)
    figure.label(567, 401, "terminal · struct Terminal", size=24, bold=True,
                 link="kernel/filesystem/terminal.picoc#L12")

    figure.box(102, 418, 470, 152, MUTED)
    figure.label(337, 448, "input_buffer[128]", size=21, bold=True,
                 link="kernel/filesystem/terminal.header#L10")
    x = 118
    for index, width in (("0", 70), ("1", 70), ("2", 70), ("…", 138), ("127", 90)):
        figure.box(x, 488, width, 42, MUTED)
        figure.label(x + width / 2, 479, index, size=17)
        if index == "0":
            figure.box(x, 488, width, 42, "none", FOCUS, 2)
        x += width
    figure.label(337, 552, "empty ring", size=17)

    for index, (name, line, unit) in enumerate((
        ("input_head", 11, "index"), ("input_tail", 12, "index"),
        ("input_count", 13, "bytes"),
    )):
        x = 572 + index * 95
        figure.box(x, 418, 95, 152, MUTED)
        figure.label(x + 47.5, 448, name, size=14,
                     link=f"kernel/filesystem/terminal.header#L{line}")
        figure.label(x + 47.5, 502, "0", size=29, bold=True)
        figure.label(x + 47.5, 540, unit, size=17)

    figure.box(857, 418, 175, 152, MUTED)
    figure.label(944.5, 444, "input_waiters", size=20, bold=True,
                 link="kernel/filesystem/terminal.header#L14")
    for name, y, line in (("head", 457, 6), ("tail", 509, 7)):
        figure.box(877, y, 135, 38, ALLOCATED)
        figure.label(944.5, y + 26, name, size=20,
                     link=f"common/wait_queue.header#L{line}")

    figure.label(1354.5, 400, "PCB 1", size=24, bold=True,
                 link="kernel/process/process.header#L31")
    figure.label(1354.5, 436, "state = BLOCKED", size=21,
                 link="kernel/process/process.header#L33")
    figure.box(1185, 458, 320, 40, MUTED)
    figure.label(1345, 485, "waiting_queue_ptr", size=23,
                 link="kernel/process/process.header#L48")
    figure.label(1354.5, 543, "wait_next = NULL", size=21,
                 link="kernel/process/process.header#L51")

    # Both queue ends reference the same PCB allocation, skipping its header.
    figure.parts.append(pointer("M 1012 476 H 1032 V 296 H 1160 V 360"))
    figure.parts.append(pointer("M 1012 528 H 1072 V 324 H 1190 V 360"))
    figure.parts.append(pointer("M 1185 478 H 1142 V 628 H 874 V 570", METADATA))
    figure.parts.append('</g>')
    figure.save()


if __name__ == "__main__":
    main()
