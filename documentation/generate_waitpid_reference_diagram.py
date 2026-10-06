"""Generate the SRAM and stack-reference diagram in README section 9.2.

Run with Python 3. Reuse section 3's address order and memory hierarchy.
Dashed guides expand storage, and arrows show the two stored status pointers.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import ALLOCATED, FREE, HEADER, MUTED, POINTER


def main():
    figure = Figure(
        "waitpid-references",
        "Waitpid request and PCB reference the same stack-local status",
        "SRAM runs from lower addresses on the left to higher addresses on the "
        "right: Kernel Image, Kernel Heap, Kernel Stack, and Process and Shared "
        "Data Heap. Process Payload A contains the parent's User Process Image, "
        "User Process Heap, and User Process Stack. Dashed guides expand the "
        "Kernel Heap on the left and User Process Stack on the right. PCB 1 "
        "occupies a Kernel Heap payload after Block Header A. "
        "The parent process's User Process Stack contains a waitpid frame with "
        "a two-cell WaitPidRequest request and a separate one-cell int status. "
        "The request cells contain an integer pid and the address of status. "
        "The separate status cell contains the integer result. request.status and "
        "PCB 1's waiting_status_ptr both point to that integer. The parent PCB "
        "is a separate Kernel Heap allocation. The request remains on the user "
        "stack while the kernel retains only the result address for wakeup. "
        "Other allocations, PCB fields, and stack cells are omitted. "
        "Widths and local placement are illustrative.",
        width=1640, height=632,
    )

    figure.row(70, 82, [
        ("ivt", 50, (".ivt",), MUTED),
        ("text", 90, (".text",), MUTED),
        ("data", 110, (".data", "kernel globals"), MUTED),
        ("kernel_heap", 350, ("PCB 1 · other kernel allocations",), ALLOCATED),
        ("kernel_stack", 100, ("Kernel", "Stack", "grows ←"), MUTED),
        ("outer_a", 60, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("image", 160, ("User Process Image", ".text · .data", "optional .ivt"), MUTED),
        ("user_heap", 160, ("User Process Heap",), MUTED),
        ("user_stack", 326, ("User Process Stack", "waitpid() locals · grows ←"), ALLOCATED,
         "library/sys/wait/wait.picoc#L14"),
        ("outer_b", 60, ("Block", "Header B"), HEADER, "common/heap.header#L5"),
        ("free", 110, ("Free", "Payload B"), FREE),
    ])
    for first, last, name in (
        ("ivt", "data", "Kernel Image"),
        ("kernel_heap", "kernel_heap", "Kernel Heap"),
        ("kernel_stack", "kernel_stack", "Kernel Stack"),
        ("outer_a", "outer_a", "Header A"),
        ("image", "user_stack", "Process Payload A · parent"),
        ("outer_b", "free", "Other blocks"),
    ):
        figure.band(first, last, 152, name)
    figure.band("ivt", "kernel_stack", 182, "Kernel")
    figure.band("outer_a", "free", 182, "Process and Shared Data Heap")

    # Matching region headers make the allocation boundaries explicit.
    for key, x, width, name in (
        ("heap_detail", 32, 540, "Kernel Heap"),
        ("stack_detail", 668, 940, "User Process Stack"),
    ):
        figure.cells[key] = (x, 300, width, 300)
        figure.box(x, 300, width, 300, "white", thickness=2)
        figure.box(x, 300, width, 50, MUTED)
        figure.label(x + width / 2, 334, name, size=24, bold=True)

    # Guide lines connect each expanded panel to its actual SRAM region.
    for source, detail in (("kernel_heap", "heap_detail"),
                           ("user_stack", "stack_detail")):
        x, _, width, _ = figure.cells[source]
        figure.cells[source] = (x, 70, width, 142)
        figure.expand(source, detail, detail)

    figure.row(360, 208, [
        ("header_a", 70, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("pcb", 400, (), ALLOCATED, "kernel/process/process.header#L31"),
        ("other_allocations", 30, ("…",), MUTED),
    ], x=52)
    figure.label(322, 397, "PCB 1 · parent", size=24, bold=True,
                 link="kernel/process/process.header#L31")
    figure.box(142, 432, 360, 104, MUTED)
    figure.label(322, 462, "int *waiting_status_ptr", size=21, bold=True,
                 link="kernel/process/process.header#L44")
    figure.label(322, 493, "&status", size=22)
    figure.label(322, 521, "address", size=18)
    figure.label(322, 557, "Other PCB fields omitted", size=17)

    figure.box(688, 360, 900, 208, "white")
    figure.label(1138, 397, "waitpid() locals", size=24, bold=True,
                 link="library/sys/wait/wait.picoc#L14")
    status_fill = "#f6eee5"
    for x, name, value, kind, fill, link in (
        (718, "int request.pid", "2", "integer value", ALLOCATED,
         "common/syscall.header#L62"),
        (998, "int *request.status", "&status", "address", ALLOCATED,
         "common/syscall.header#L63"),
        (1278, "int status", "0 → child status", "integer value", status_fill,
         "library/sys/wait/wait.picoc#L15"),
    ):
        figure.box(x, 432, 280, 104, fill)
        figure.label(x + 140, 462, name, size=21, bold=True, link=link)
        figure.label(x + 140, 493, value, size=22)
        figure.label(x + 140, 521, kind, size=18)
    figure.box(718, 536, 560, 30, ALLOCATED)
    figure.label(998, 557, "WaitPidRequest request · 2 cells", size=20,
                 bold=True, link="common/syscall.header#L61")
    figure.box(1278, 536, 280, 30, status_fill)
    figure.label(1418, 557, "Separate int · 1 cell", size=20, bold=True)

    for path in ("M 1138 432 C 1138 407, 1418 407, 1418 432",
                 "M 502 484 H 612 V 588 H 1418 V 566"):
        figure.parts.append(
            f'<path d="{path}" fill="none" '
            f'stroke="{POINTER}" stroke-width="2.5" '
            f'marker-end="url(#{POINTER[1:]})"/>'
        )
    figure.save()


if __name__ == "__main__":
    main()
