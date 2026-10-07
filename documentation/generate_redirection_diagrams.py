"""Generate the five descriptor snapshots in README section 12.6.

Start with the shell alone, then show save, install, inherit and restore.
The child first appears when run copies the shell's descriptors.
Each descriptor gets a row and every non-NULL path gets its own allocation.
Teal arrows follow pointers; amber call arrows identify changed objects.
Run with Python 3 from any directory. No external packages are required.
"""

from diagram_style import AMBER, FOCUS_FILL, INK
from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import (
    ALLOCATED, FOCUS, FREE, HEADER, HEAP_EMPHASIS, MUTED, POINTER,
)


FD = "kernel/filesystem/file_descriptor.header"
PCB = "kernel/process/process.header"
BLOCK = "common/heap.header#L5"
TERMINAL = "/device/terminal.dev"
OUTPUT = "/output.txt"
GROUP_HEIGHT = 510
ROW_HEIGHT = 48
ARRAY_X = 430
PATH_X = 1010
BACKUP_FILL = FOCUS_FILL
BACKUP_INK = AMBER


def pointer(figure, path, color=POINTER):
    figure.parts.append(
        f'<path d="{path}" fill="none" stroke="{color}" '
        f'stroke-width="2" marker-end="url(#{color[1:]})"/>'
    )


def heap_block(figure, x, y, width, height, lines):
    """Draw an allocation header above a PCB or descriptor table."""
    figure.box(x, y, width, 24, HEADER)
    figure.label(x + width / 2, y + 17, "BlockHeader", size=14, link=BLOCK)
    figure.box(x, y + 24, width, height - 24, ALLOCATED)
    for index, (value, link) in enumerate(lines):
        figure.label(x + width / 2, y + 52 + index * 27,
                     value, size=18, bold=index == 0, link=link)


def descriptor_group(figure, top, process_number, entries, changed, *,
                     calls=(), child_state="READY"):
    """Show one contiguous entry array beside all its separate path allocations."""
    role = "Shell" if process_number == 1 else "Child"
    figure.box(32, top, 1336, GROUP_HEIGHT, "none")
    pcb_lines = [
        (f"PCB {process_number} · {role.lower()}", f"{PCB}#L31"),
        ("file_descriptors", f"{PCB}#L42"),
    ]
    if process_number == 2:
        pcb_lines.append((f"state = {child_state}", f"{PCB}#L33"))
    heap_block(figure, 52, top + 44, 278, 138, pcb_lines)
    heap_block(figure, 52, top + 230, 278, 104, (
        ("FileDescriptorTable", f"{FD}#L22"),
        ("entries", f"{FD}#L23"),
    ))
    pointer(figure, f"M 308 {top + 123} H 350 V {top + 210} H 38 V {top + 282} H 52")
    pointer(figure, f"M 308 {top + 309} H 378 V {top + 103} H {ARRAY_X}")

    figure.label(680, top + 32, "entries[0..7]",
                 size=18, bold=True, link=f"{FD}#L15")
    figure.box(ARRAY_X, top + 44, 500, 24, HEADER)
    figure.label(680, top + 61, "BlockHeader", size=14, link=BLOCK)
    figure.box(ARRAY_X, top + 68, 500, 28, MUTED)
    for center, label, link in (
        (525, "Descriptor", ""),
        (695, "kind", f"{FD}#L16"),
        (850, "path", f"{FD}#L19"),
    ):
        figure.label(center, top + 88, label, size=16, bold=True, link=link)

    roles = {0: "stdin", 1: "stdout", 2: "stderr", 3: "temporary",
             5: "backup stdin", 6: "backup stdout", 7: "backup stderr"}
    kinds = {0: "STDIN", 1: "STDOUT", 2: "STDERR",
             5: "STDIN", 6: "STDOUT", 7: "STDERR"}
    for index in range(8):
        y = top + 96 + index * ROW_HEIGHT
        center_y = y + ROW_HEIGHT / 2
        destination = entries.get(index)
        is_backup = index >= 5
        fill = ALLOCATED if destination else FREE
        if is_backup:
            fill = BACKUP_FILL
        figure.box(ARRAY_X, y, 500, ROW_HEIGHT, fill)
        for divider in (620, 770):
            figure.parts.append(
                f'<path d="M {divider} {y} v {ROW_HEIGHT}" stroke="#637983"/>'
            )
        figure.label(444, center_y + 6,
                     f"{index} · {roles[index]}" if index in roles else str(index),
                     size=18, bold=True, anchor="start",
                     color=BACKUP_INK if is_backup else INK)
        kind = "FILE" if destination == OUTPUT else kinds.get(index, "STDOUT")
        if destination is None:
            kind = "FREE"
        line = {"FREE": 9, "STDIN": 10, "STDOUT": 11, "STDERR": 12, "FILE": 13}[kind]
        figure.label(695, center_y + 6, kind, size=18, link=f"{FD}#L{line}")
        figure.label(850, center_y + 6, "pointer" if destination else "NULL",
                     size=18, link=f"{FD}#L19")
        if index in changed:
            figure.box(ARRAY_X + 2, y + 2, 496, ROW_HEIGHT - 4, "none", FOCUS, 3)

        if destination is None:
            continue
        figure.box(PATH_X, y + 5, 42, ROW_HEIGHT - 10, HEADER)
        figure.label(PATH_X + 21, center_y + 5, "BH", size=13, bold=True, link=BLOCK)
        figure.box(PATH_X + 42, y + 5, 306, ROW_HEIGHT - 10,
                   BACKUP_FILL if is_backup else ALLOCATED)
        figure.label(PATH_X + 195, center_y + 6, f'"{destination}"',
                     size=18, bold=True, link=f"{FD}#L19")
        pointer(figure, f"M 916 {center_y} H 974 V {y + 1} H {PATH_X + 60} V {y + 5}")

    for order, (text, link, target) in enumerate(calls, start=1):
        y = top + 362 + (order - 1) * 64
        figure.box(52, y, 278, 36, HEAP_EMPHASIS, FOCUS)
        figure.label(191, y + 24, f"{order}. {text}", size=16,
                     bold=True, color=FOCUS, link=link)
        if target == "table":
            pointer(figure, f"M 191 {y} V {top + 334}", FOCUS)
        else:
            target_y = top + 120 + target * ROW_HEIGHT
            lane = 394 + (order - 1) * 14
            pointer(figure, f"M 330 {y + 18} H {lane} V {target_y} H {ARRAY_X}", FOCUS)


def overview(figure, expanded_top):
    """Locate the kernel heap before any child has been created."""
    figure.row(32, 66, [
        ("ivt", 55, (".ivt",), MUTED),
        ("text", 90, (".text",), MUTED),
        ("data", 100, (".data",), MUTED),
        ("kernel_heap", 345, ("PCBs · descriptor tables", "entries · path strings"), ALLOCATED),
        ("stack", 120, ("Kernel", "Stack"), MUTED),
        ("outer_a", 60, ("Block", "Header"), HEADER, BLOCK),
        ("shell", 180, ("Shell Process Payload", "image · heap · stack"), ALLOCATED),
        ("other", 70, ("…",), MUTED),
    ])
    figure.band("ivt", "data", 98, "Kernel Image")
    figure.band("kernel_heap", "kernel_heap", 98, "Kernel Heap · kmalloc", HEAP_EMPHASIS)
    figure.band("stack", "stack", 98, "Kernel Stack")
    figure.band("outer_a", "other", 98, "Process and Shared Data Heap")
    figure.focus("kernel_heap")
    figure.box(1072, 32, 296, 96, MUTED)
    figure.label(1220, 58, "Emulator host · outside SRAM", size=17, bold=True)
    figure.label(1220, 87, '"/output.txt"', size=19)
    figure.label(1220, 114, "Not opened yet", size=17)
    x, _, width, _ = figure.cells["kernel_heap"]
    figure.parts.append(
        f'<path d="M {x} 128 L 32 {expanded_top} '
        f'M {x + width} 128 L 1368 {expanded_top}" '
        'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>'
    )


def snapshot(slug, title, shell, *, child=None, changed=(), child_changed=(),
             show_overview=False, shell_calls=(), child_calls=()):
    top = 178 if show_overview else 24
    expanded_height = GROUP_HEIGHT * (2 if child else 1) + (28 if child else 0)
    figure = Figure(
        f"redirection-{slug}", title,
        f"{title}. Each outlined group belongs to one process. Its PCB points "
        "to a separately allocated FileDescriptorTable, which points to one "
        "contiguous eight-entry array drawn as eight rows. Every non-NULL path "
        "points to a separate allocation displayed in full on its row, including "
        "stdin and stderr. FREE entries have path NULL and no path allocation. "
        "Quoted paths use C string literal notation with an implicit terminating "
        "null character. BH abbreviates BlockHeader. STDIN, STDOUT, STDERR, FILE "
        "and FREE abbreviate FILE_DESCRIPTOR constants. Pale amber rows 5–7 identify "
        "reserved backup slots even when FREE, "
        "and their allocated path strings use the same pale amber fill. Teal arrows follow stored "
        "pointers. Amber call arrows identify changed objects; amber outlines mark "
        "changed entries. Flags, offsets and unrelated allocations are omitted. "
        "Sizes and allocation positions are illustrative. "
        + ("The starting SRAM overview shows only the shell; no child exists yet. "
           if show_overview else "Only the expanded Kernel Heap is shown. ")
        + ("The child's independent allocations appear in the lower group."
           if child else "Only the shell's allocations are expanded."),
        width=1400, height=top + expanded_height + 24,
        show_address_direction=False,
    )
    if show_overview:
        overview(figure, top)
    descriptor_group(figure, top, 1, shell, changed,
                     calls=shell_calls)
    if child:
        descriptor_group(figure, top + GROUP_HEIGHT + 28, 2, child, child_changed,
                         calls=child_calls)
    figure.save()


def main():
    initial = {0: TERMINAL, 1: TERMINAL, 2: TERMINAL}
    saved = {**initial, 3: OUTPUT, 6: TERMINAL}
    installed = {**initial, 1: OUTPUT, 6: TERMINAL}
    child = {**initial, 1: OUTPUT}
    snapshot("initial", "0. Before load(): no child yet", initial,
             show_overview=True)
    snapshot("save", "2. Open the output file and save shell stdout", saved,
             changed=(3, 6),
             shell_calls=(
                 ('open("output.txt", flags) → 3', "library/fcntl/fcntl.picoc#L15", 3),
                 ("dup2(1, 6)", "library/unistd/io.picoc#L58", 6),
             ))
    snapshot("install", "3. Redirect shell stdout and close the temporary descriptor",
             installed, changed=(1, 3),
             shell_calls=(
                 ("dup2(3, 1)", "library/unistd/io.picoc#L58", 1),
                 ("close(3)", "library/unistd/io.picoc#L54", 3),
             ))
    snapshot("inherit", "4. run(): copy shell descriptors into the child, then mark it READY",
             installed, child=child, child_changed=(1,),
             child_calls=(("run(pid, arguments, NULL)", "library/unistd/process.picoc#L31", "table"),))
    snapshot("restore", "5. Restore shell stdout: the child keeps its own output-file path",
             initial, child=child, changed=(1, 6),
             shell_calls=(
                 ("dup2(6, 1)", "library/unistd/io.picoc#L58", 1),
                 ("close(6)", "library/unistd/io.picoc#L54", 6),
             ))


if __name__ == "__main__":
    main()
