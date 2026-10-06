"""Generate the horizontal stack-reference diagram in README section 9.2.

Run with Python 3. Reuse the README's SVG style and show only the two
pointers to waitpid's stack-local result, with each local shown as memory cells.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import ALLOCATED, MUTED, POINTER


def main():
    figure = Figure(
        "waitpid-references",
        "Waitpid request and PCB reference the same stack-local status",
        "The parent process's User Process Stack contains a waitpid frame with "
        "a two-cell WaitPidRequest request and a separate one-cell int status. "
        "The request cells contain an integer pid and the address of status. "
        "The separate status cell contains the integer result. request.status and "
        "PCB 1's waiting_status_ptr both point to that integer. The parent PCB "
        "is a separate Kernel Heap allocation. The request remains on the user "
        "stack while the kernel retains only the result address for wakeup.",
        width=1300, height=324, show_address_direction=False,
    )

    status_fill = "#f6eee5"
    figure.box(32, 24, 790, 276, "white", thickness=2)
    figure.label(427, 62, "waitpid() locals · User Process Stack", size=24,
                 bold=True, link="library/sys/wait/wait.picoc#L14")
    figure.label(427, 88, "Lower addresses → higher addresses", size=16)
    for x, name, value, kind, fill, link in (
        (52, "int request.pid", "2", "integer value", ALLOCATED,
         "common/syscall.header#L62"),
        (302, "int *request.status", "&status", "address", ALLOCATED,
         "common/syscall.header#L63"),
        (552, "int status", "0 → child status", "integer value", status_fill,
         "library/sys/wait/wait.picoc#L15"),
    ):
        figure.box(x, 154, 250, 104, fill)
        figure.label(x + 125, 184, name, size=21, bold=True, link=link)
        figure.label(x + 125, 215, value, size=22)
        figure.label(x + 125, 243, kind, size=18)
    figure.box(52, 258, 500, 30, ALLOCATED)
    figure.label(302, 279, "WaitPidRequest request · 2 cells", size=20,
                 bold=True, link="common/syscall.header#L61")
    figure.box(552, 258, 250, 30, status_fill)
    figure.label(677, 279, "Separate int · 1 cell", size=20, bold=True)

    figure.box(932, 24, 336, 276, "white", thickness=2)
    figure.label(1100, 62, "PCB 1 · parent", size=24, bold=True,
                 link="kernel/process/process.header#L31")
    figure.label(1100, 92, "Kernel Heap", size=22)
    figure.box(952, 154, 296, 104, MUTED)
    figure.label(1100, 184, "int *waiting_status_ptr", size=21, bold=True,
                 link="kernel/process/process.header#L44")
    figure.label(1100, 215, "&status", size=22)
    figure.label(1100, 243, "address", size=18)

    for path in ("M 427 154 C 427 100, 677 100, 677 154",
                 "M 952 206 H 802"):
        figure.parts.append(
            f'<path d="{path}" fill="none" '
            f'stroke="{POINTER}" stroke-width="2.5" '
            f'marker-end="url(#{POINTER[1:]})"/>'
        )
    figure.save()


if __name__ == "__main__":
    main()
