"""Generate the slide-oriented SRAM view for README section 12.5.1.

Solid arrows are stored addresses. The dashed arrow is a PID lookup.
The snapshot shows fg resuming a previously tracked child, before waitpid
returns. Allocator order and widths are illustrative, as in section 3.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import (
    ADDRESS, ALLOCATED, FOCUS, HEADER, HEAP_EMPHASIS, MUTED, POINTER,
)


def main():
    figure = Figure(
        "job-control", "Foreground and background job storage in SRAM",
        "An illustrative foreground snapshot after fg resumes tracked child "
        "PID 2. Shell PID 1 is waiting for it. Kernel .data stores the integer "
        "foreground_process_target = +2. The dashed arrow represents "
        "find_process_by_pid, which scans the global PCB list, not a stored "
        "PCB pointer. PCB 1 and PCB 2 are separate kmalloc payloads in the "
        "Kernel Heap, each after a BlockHeader. Their base_address integers "
        "store addresses of separate PSDMalloc Process Payloads in the "
        "Process and Shared Data Heap. The lower row expands the shell "
        "payload into .text, .data, User Process Heap and User Process Stack. "
        "The shell globals last_background_process_id = 2 and "
        "last_command_exit_status = 0 are inline integers, not allocations "
        "or pointers. The exit status is an example previous command result, "
        "not the result of the pending wait. PID 2 remains tracked during fg. "
        "Other PCB fields, "
        "wait links, descriptor allocations and allocator links are omitted.",
        width=1834, height=670, show_address_direction=False,
    )

    def arrow(path, colour=POINTER, dashed=False):
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        figure.parts.append(
            f'<path d="{path}" fill="none" stroke="{colour}" '
            f'stroke-width="2.5"{dash} marker-end="url(#{colour[1:]})"/>'
        )

    figure.row(190, 140, [
        ("ivt_text", 120, (".ivt", ".text"), MUTED),
        ("data", 330, (), MUTED),
        ("kh_a", 50, ("Block", "Header", "A"), HEADER, "common/heap.header#L5"),
        ("pcb1", 270, (), ALLOCATED),
        ("kh_b", 50, ("Block", "Header", "B"), HEADER, "common/heap.header#L5"),
        ("pcb2", 270, (), ALLOCATED),
        ("kernel_stack", 100, ("Kernel", "Stack"), MUTED),
        ("outer_a", 50, ("Block", "Header", "A"), HEADER, "common/heap.header#L5"),
        ("shell", 280, ("Process Payload A", "shell", "image · heap · stack"), ALLOCATED,
         "user/shell.picoc#L1453"),
        ("outer_b", 50, ("Block", "Header", "B"), HEADER, "common/heap.header#L5"),
        ("child", 200, ("Process Payload B", "child", "image · heap · stack"), ALLOCATED),
    ])
    figure.band("ivt_text", "data", 330, "Kernel Image")
    figure.band("kh_a", "pcb2", 330, "Kernel Heap · kmalloc", HEAP_EMPHASIS)
    figure.band("kernel_stack", "kernel_stack", 330, "Kernel Stack")
    figure.band("outer_a", "child", 330, "Process and Shared Data Heap · PSDMalloc",
                HEAP_EMPHASIS)
    figure.band("ivt_text", "kernel_stack", 360, "Kernel")
    figure.band("outer_a", "child", 360, "After the Kernel region")

    figure.label(317, 219, ".data", size=21, bold=True)
    figure.label(317, 259, "foreground_process_target", size=19,
                 link="kernel/signal.picoc#L12")
    figure.label(317, 301, "+2", size=30, bold=True, color=FOCUS)
    for number, x, role in ((1, 667, "shell"), (2, 987, "child")):
        figure.label(x, 219, f"PCB {number} · {role}", size=22, bold=True,
                     link="kernel/process/process.header#L31")
        figure.label(x, 250, f"pid = {number}", size=19,
                     link="kernel/process/process.header#L32")
        figure.label(x, 280, "base_address", size=20, color=ADDRESS,
                     link="kernel/process/process.header#L34")
    figure.label(667, 311, "state = BLOCKED", size=19,
                 link="kernel/process/process.header#L33")
    figure.label(987, 311, "parent_pid = 1", size=19,
                 link="kernel/process/process.header#L57")

    # Both base addresses reach the first image cell after the outer header.
    arrow("M 590 274 H 552 V 70 H 1272 V 190", ADDRESS)
    figure.label(1295, 59, "base_address", size=18, color=ADDRESS,
                 link="kernel/process/process.header#L34")
    arrow("M 910 274 H 872 V 110 H 1602 V 190", ADDRESS)
    figure.label(1625, 99, "base_address", size=18, color=ADDRESS,
                 link="kernel/process/process.header#L34")
    # Ownership stores a PID. The kernel resolves it by searching the PCB list.
    arrow("M 350 301 H 470 V 153 H 1015 V 190", FOCUS, dashed=True)
    figure.label(738, 144, "PID lookup", size=18, color=FOCUS,
                 link="kernel/process/process.picoc#L162")

    # A compact expansion shows which state belongs to the shell itself.
    figure.row(475, 125, [
        ("user_text", 160, (".text", "shell + libraries"), MUTED),
        ("user_data", 900, (), MUTED),
        ("user_heap", 350, ("User Process Heap",), ALLOCATED),
        ("user_stack", 360, ("User Process Stack", "waitpid() call frame"), MUTED,
         "library/sys/wait/wait.picoc#L15"),
    ])
    figure.band("user_text", "user_data", 600, "User Process Image")
    figure.band("user_heap", "user_heap", 600, "User Process Heap · malloc", HEAP_EMPHASIS)
    figure.band("user_stack", "user_stack", 600, "User Process Stack")
    figure.band("user_text", "user_stack", 630, "Process Payload A · shell · expanded")
    # Connect the payload's bottom corners to the expanded view's top corners.
    figure.expand("shell", "user_text", "user_stack")
    figure.label(642, 502, ".data · inline integers", size=20, bold=True)
    for x, name, value, meaning, line in (
        (420, "last_background_process_id", "2", "$!", 30),
        (865, "last_command_exit_status", "0", "$? · previous result", 29),
    ):
        figure.label(x, 540, name, size=20, link=f"user/shell.picoc#L{line}")
        figure.label(x, 579, f"{value}   ({meaning})", size=23, bold=True)

    figure.save()


if __name__ == "__main__":
    main()
