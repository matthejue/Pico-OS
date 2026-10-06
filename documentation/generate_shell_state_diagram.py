"""Generate the wide shell storage view in README section 12.1.

The upper row is continuous SRAM. The lower row expands the shell's
Process Payload using the same regions and colours as section 3.
Only stored pointers receive arrows. Widths and block order are illustrative.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import (
    ADDRESS, ALLOCATED, HEADER, HEAP_EMPHASIS, MUTED, POINTER,
)


def main():
    figure = Figure(
        "shell-state", "Shell-owned state in SRAM",
        "Continuous SRAM contains the Kernel Image, Kernel Heap, Kernel Stack, "
        "and Process and Shared Data Heap. The global terminal input buffer is "
        "embedded in kernel .data. PCB 1 manages the shell. Its file_descriptors "
        "pointer reaches a separately allocated FileDescriptorTable, whose "
        "entries pointer reaches an eight-element array. PCB and descriptor "
        "path strings occupy other Kernel Heap blocks. PCB 1.base_address "
        "reaches the shell Process Payload after its outer Block Header A. "
        "The lower view expands that payload into .text, .data, User Process "
        "Heap and User Process Stack. All shell globals are stored inline in "
        ".data, together with linked-library globals process_heap and environ. "
        "process_heap.first_block reaches the inner allocator header, while "
        "environ reaches the environment pointer array, whose entries reach "
        "separately allocated strings. Only two example user-heap blocks are "
        "shown. The stack holds command[80], call-frame locals such as "
        "expanded_arguments[80], and startup arguments and environment. "
        "No shell input, history or pipeline array is a malloc allocation. "
        "Indices and counts are integers, not pointers. Other processes and "
        "allocations are omitted, and header letters do not fix allocation order.",
        width=1800, height=610, show_address_direction=False,
    )

    figure.row(105, 105, [
        ("ivt", 50, (".ivt",), MUTED),
        ("text", 75, (".text",), MUTED),
        ("data", 185, (".data", "terminal.input_buffer[128]"), MUTED,
         "kernel/filesystem/terminal.header#L10"),
        ("kh_a", 45, ("Block", "Header", "A"), HEADER, "common/heap.header#L5"),
        ("pcb", 170, ("PCB 1 · shell", "file_descriptors", "base_address"), ALLOCATED,
         "kernel/process/process.header#L31"),
        ("kh_b", 45, ("Block", "Header", "B"), HEADER, "common/heap.header#L5"),
        ("table", 155, ("FileDescriptorTable", "entries"), ALLOCATED,
         "kernel/filesystem/file_descriptor.header#L22"),
        ("kh_c", 45, ("Block", "Header", "C"), HEADER, "common/heap.header#L5"),
        ("entries", 160, ("FileDescriptor[8]", "0–2: standard I/O", "5–7: saved I/O"), ALLOCATED,
         "kernel/filesystem/file_descriptor.header#L15"),
        ("paths", 110, ("… path strings …", "other blocks"), ALLOCATED),
        ("kernel_stack", 95, ("Kernel", "Stack", "grows ←"), MUTED),
        ("outer_a", 50, ("Block", "Header", "A"), HEADER, "common/heap.header#L5"),
        ("shell", 280, ("Process Payload A", "shell image · user heap · stack"), ALLOCATED,
         "user/shell.picoc#L1453"),
        ("outer_b", 50, ("Block", "Header", "B"), HEADER, "common/heap.header#L5"),
        ("other", 220, ("… other payloads …",), MUTED),
    ])
    figure.band("ivt", "data", 210, "Kernel Image")
    figure.band("kh_a", "paths", 210, "Kernel Heap · kmalloc", HEAP_EMPHASIS)
    figure.band("kernel_stack", "kernel_stack", 210, "Kernel Stack")
    figure.band("outer_a", "other", 210, "Process and Shared Data Heap · PSDMalloc",
                HEAP_EMPHASIS)
    figure.band("ivt", "kernel_stack", 240, "Kernel")
    figure.band("outer_a", "other", 240, "After the Kernel region")

    def pointer(path, colour=POINTER):
        figure.parts.append(
            f'<path d="{path}" fill="none" stroke="{colour}" '
            f'stroke-width="2" marker-end="url(#{colour[1:]})"/>'
        )

    # Three distinct heap payloads, with pointers terminating after headers.
    pointer("M 520 105 V 78 H 615 V 105")
    figure.label(566, 69, "file_descriptors", size=14,
                 link="kernel/process/process.header#L42")
    pointer("M 730 105 V 78 H 815 V 105")
    figure.label(772, 69, "entries", size=14,
                 link="kernel/filesystem/file_descriptor.header#L23")
    pointer("M 395 105 V 46 H 1262 V 105", ADDRESS)
    figure.label(1055, 67, "base_address", size=15, color=ADDRESS,
                 link="kernel/process/process.header#L34")

    figure.row(350, 190, [
        ("user_text", 95, (".text", "shell +", "libraries"), MUTED),
        ("user_data", 930, (), MUTED),
        ("user_heap", 380, (), ALLOCATED),
        ("user_stack", 331, (), MUTED),
    ])
    figure.band("user_text", "user_data", 540, "User Process Image")
    figure.band("user_heap", "user_heap", 540, "User Process Heap · malloc", HEAP_EMPHASIS)
    figure.band("user_stack", "user_stack", 540, "User Process Stack · grows ←")
    figure.band("user_text", "user_stack", 570, "Process Payload A · expanded")
    # Begin the expansion below the overview's grouping bands.
    sx, sy, sw, _ = figure.cells["shell"]
    figure.cells["shell"] = (sx, sy, sw, 165)
    figure.expand("shell", "user_text", "user_stack")

    figure.label(592, 375, ".data · globals stored inline", size=17, bold=True)
    columns = [
        [
            ("shell_input_buffer[128]", "user/shell.picoc#L42"),
            ("shell_input_index / shell_input_count", "user/shell.picoc#L45"),
            ("command_history[8][80]", "user/shell.picoc#L36"),
            ("command_history_start / command_history_count", "user/shell.picoc#L43"),
            ("command_history_draft[80]", "user/shell.picoc#L39"),
            ("shell_line_erase_sequence[237]", "user/shell.picoc#L41"),
        ],
        [
            ("shell_pipe_left_command[160]", "user/shell.picoc#L32"),
            ("shell_pipe_right_command[160]", "user/shell.picoc#L33"),
            ("shell_pipe_path[80]", "user/shell.picoc#L34"),
            ("shell_executable_path[PATH_MAX]", "user/shell.picoc#L31"),
        ],
        [
            ("last_command_exit_status", "user/shell.picoc#L29"),
            ("last_background_process_id", "user/shell.picoc#L30"),
            ("process_heap.first_block", "common/heap.header#L12"),
            ("environ", "library/stdlib/env.picoc#L4"),
        ],
    ]
    # Paired scalar labels link each identifier to its own definition.
    for column, labels in enumerate(columns):
        x = 137 + (0, 390, 690)[column]
        for row, (label, link) in enumerate(labels):
            y = 402 + row * 24
            if " / " in label:
                first, second = label.split(" / ")
                figure.label(x, y, first + " /", size=12, anchor="start", link=link)
                figure.label(x + len(first + " / ") * 6.5, y, second, size=12,
                             anchor="start", link=link.rsplit("L", 1)[0] + str(int(link.rsplit("L", 1)[1]) + 1))
            else:
                figure.label(x, y, label, size=14, anchor="start", link=link)

    # The environment is the shell's actual library-managed heap storage.
    figure.row(388, 152, [
        ("uh_a", 45, ("Block", "Header", "A"), HEADER, "common/heap.header#L5"),
        ("env_array", 100, ("environ[]", "pointers", "… NULL"), ALLOCATED,
         "library/stdlib/env.picoc#L110"),
        ("uh_b", 45, ("Block", "Header", "B"), HEADER, "common/heap.header#L5"),
        ("env_string", 190, ("Environment string", '"PATH=…\\0"'), ALLOCATED,
         "library/stdlib/env.picoc#L22"),
    ], x=1057)
    figure.label(1290, 375, "Environment", size=17, bold=True)
    pointer("M 1029 445 H 1041 V 301 H 1080 V 388", ADDRESS)
    pointer("M 1029 474 H 1050 V 325 H 1165 V 388")
    pointer("M 1185 510 H 1260")

    for row, (label, link) in enumerate([
        ("command[80] · main()", "user/shell.picoc#L1454"),
        ("expanded_arguments[80]", "user/shell.picoc#L1049"),
        ("Other call-frame locals", "user/shell.picoc#L276"),
        ("Initial argv + envp strings", "kernel/process/process_arguments.picoc#L125"),
    ]):
        figure.label(1602.5, 408 + row * 32, label, size=16, link=link)
    figure.save()


if __name__ == "__main__":
    main()
