"""Generate the horizontal stack-reference diagram in README section 9.2.

Run with Python 3. Reuse the README's SVG style and show only the two
pointers to waitpid's stack-local result, with containment shown by boxes.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import MUTED, POINTER


def main():
    figure = Figure(
        "waitpid-references",
        "Waitpid request and PCB reference the same stack-local status",
        "The parent process's User Process Stack contains a waitpid frame with "
        "a WaitPidRequest request and a separate int status. request.status and "
        "PCB 1's waiting_status_ptr both point to that integer. The parent PCB "
        "is a separate Kernel Heap allocation. The request remains on the user "
        "stack while the kernel retains only the result address for wakeup.",
        width=1300, height=236, show_address_direction=False,
    )

    figure.box(32, 24, 720, 188, "white", thickness=2)
    figure.label(392, 62, "waitpid() frame · User Process Stack", size=24,
                 bold=True, link="library/sys/wait/wait.picoc#L14")
    figure.box(52, 94, 310, 96, MUTED)
    figure.label(207, 124, "WaitPidRequest request", size=22, bold=True,
                 link="common/syscall.header#L61")
    figure.label(207, 152, "pid", size=22, link="common/syscall.header#L62")
    figure.label(207, 178, "status", size=22, link="common/syscall.header#L63")
    figure.label(642, 174, "int status", size=24, bold=True,
                 link="library/sys/wait/wait.picoc#L15")

    figure.box(1012, 24, 256, 188, "white", thickness=2)
    figure.label(1140, 62, "PCB 1 · parent", size=24, bold=True,
                 link="kernel/process/process.header#L31")
    figure.label(1140, 92, "Kernel Heap", size=22)
    figure.box(1032, 132, 216, 58, MUTED)
    figure.label(1140, 168, "waiting_status_ptr", size=21,
                 link="kernel/process/process.header#L44")

    for source, target in ((362, 552), (1032, 732)):
        figure.parts.append(
            f'<path d="M {source} 166 H {target}" fill="none" '
            f'stroke="{POINTER}" stroke-width="2.5" '
            f'marker-end="url(#{POINTER[1:]})"/>'
        )
    figure.save()


if __name__ == "__main__":
    main()
