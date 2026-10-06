"""Generate the environment diagrams in README section 4.2.2.2.1.

Run with Python 3. Reuse the chapter 4 SVG style. The propagation tree keeps
one variable and labels process-start arrows with concrete run calls.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import ALLOCATED, MUTED, POINTER


ENV = "library/stdlib/env.picoc#L4"
RUN = "library/unistd/process.picoc#L31"
INIT = "system/init.picoc#L19"
SETENV = "library/stdlib/env.picoc#L126"
REQUEST = "common/syscall.header#L55"
INITIALIZE = "library/stdlib/env.picoc#L97"


def arrow(f, x1, y1, x2, y2, *, copy=False):
    style = ' stroke-dasharray="8 5"' if copy else ""
    f.parts.append(
        f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" '
        f'stroke="{POINTER}" stroke-width="2.5"{style} '
        f'marker-end="url(#{POINTER[1:]})"/>'
    )


def frame(f, x, width, title, link):
    f.box(x, 60, width, 400, "white", thickness=2)
    f.label(x + width / 2, 94, title, size=26, bold=True, link=link)


def environment(f, x, y, width, *, stack=False):
    f.box(x, y, width, 135, ALLOCATED)
    center = x + width / 2
    f.label(center, y + 28,
            "Child's initial stack: envp" if stack else ".data: environ",
            size=23, bold=True,
            link="kernel/process/process_arguments.picoc#L141" if stack else ENV)
    arrow(f, center, y + 37, center, y + 55)
    f.label(center, y + 79, '"PATH=/user"', size=22)
    f.label(center, y + 108, '"PICOOS_LOADING_BAR=true"', size=22,
            link="common/loading_bar.header#L5")
    f.label(center, y + 129,
            "Stack: pointer array + strings + NULL" if stack else
            "Heap: pointer array + strings + NULL", size=17)


def origin():
    f = Figure(
        "environment-origin", "Init reads configuration, then starts the shell",
        "Init starts with an empty environ array. Its read_environment function opens "
        "config/environment.txt and reads PATH=/user, then setenv stores an independent "
        "string in init's User Process Heap. With loading_bar_enabled true, init also "
        "stores PICOOS_LOADING_BAR=true. Init calls run(shell_pid, NULL, NULL), selecting "
        "its own environ. The shell receives independent stack and heap copies. "
        "Leftward arrows are read requests, rightward arrows return file contents "
        "or copy environment data. The file performs no operation itself.",
        width=1800, height=440, show_address_direction=False,
    )
    f.box(32, 145, 300, 180, MUTED, thickness=2)
    f.label(182, 183, "Configuration file", size=25, bold=True)
    f.label(182, 223, "config/environment.txt", size=22,
            link="config/environment.txt")
    f.label(182, 270, "PATH=/user", size=25)

    frame(f, 660, 500, "init process", "system/init.picoc#L100")
    f.label(910, 129, "Starts with an empty environ array", size=22, link=ENV)
    f.box(680, 148, 460, 99, MUTED)
    f.label(910, 178, "read_environment()", size=24, bold=True, link=INIT)
    f.label(910, 208, "Parses NAME=value entries", size=22)
    f.label(910, 237, 'setenv("PATH", "/user", true)', size=22, link=SETENV)
    arrow(f, 680, 192, 332, 192)
    f.label(506, 154, "open(path, O_RDONLY)", size=21,
            link="library/fcntl/fcntl.picoc#L5")
    f.label(506, 180, "read(fd, contents, 256)", size=21,
            link="library/unistd/io.picoc#L6")
    arrow(f, 332, 236, 680, 236)
    f.label(506, 223, "returns contents: PATH=/user", size=20)

    f.label(910, 277, "if (loading_bar_enabled)", size=21,
            link="config/config.header#L5")
    f.label(910, 302, 'setenv("PICOOS_LOADING_BAR", "true", true)',
            size=19, link=SETENV)
    arrow(f, 910, 309, 910, 325)
    environment(f, 680, 325, 460)

    frame(f, 1460, 308, "shell process", "user/shell.picoc")
    f.label(1614, 175, "Own environ array", size=23, link=ENV)
    f.label(1614, 208, "and string copies", size=23)
    f.label(1614, 246, "Same values as init", size=22)
    f.box(1480, 325, 268, 135, ALLOCATED)
    f.label(1614, 355, ".data: environ", size=23, bold=True, link=ENV)
    arrow(f, 1614, 366, 1614, 390)
    f.label(1614, 421, "User Process Heap", size=23, bold=True)
    f.label(1614, 447, "Array + strings", size=22)

    f.label(1310, 279, "init calls", size=22)
    f.label(1310, 308, "run(shell_pid, NULL, NULL)", size=21, link=RUN)
    f.label(1310, 345, "copies init's values", size=21)
    arrow(f, 1140, 400, 1480, 400, copy=True)
    f.label(1310, 433, "via shell stack → heap", size=20)
    # Keep the process frames and copy paths, with a small margin around them.
    f.parts = ['<g transform="translate(0,-40)">', *f.parts, '</g>']
    f.save()


def propagation():
    """Show independent environment changes across two child generations."""
    f = Figure(
        "environment-propagation", "Environment inheritance through three process branches",
        "Init passes PATH=/user to the shell with run(shell_pid, NULL, NULL). "
        "The shell starts three processes using run with a NULL environment argument. "
        "Process 1 removes PATH with unsetenv, process 2 changes PATH to /test with "
        "setenv, and process 3 leaves PATH=/user unchanged. Each starts its own child. "
        "Process 4 inherits no PATH, process 5 inherits PATH=/test, and process 6 "
        "inherits PATH=/user. Every box shows only PATH from its own environ after the local "
        "operation. Arrows show concrete run calls, not shared pointers.",
        width=1920, height=1080, show_address_direction=False,
    )

    def process(x, y, width, name, value, *, operation="", operation_link="",
                changed=False, link=ENV):
        height = 170 if operation else 130
        stroke = "#9c3d15" if changed else POINTER
        f.box(x, y, width, height, ALLOCATED, stroke, thickness=2.5)
        center = x + width / 2
        f.label(center, y + 44, name, size=32, bold=True, link=link)
        if operation:
            f.label(center, y + 91, operation, size=28,
                    color=stroke if changed else "#43576a", link=operation_link)
        f.label(center, y + height - 28, value, size=32, bold=changed,
                color=stroke, link=ENV)

    def edge(path, x, y, call):
        f.parts.append(
            f'<path d="{path}" fill="none" stroke="{POINTER}" '
            f'stroke-width="3" marker-end="url(#{POINTER[1:]})"/>'
        )
        # Keep the function call on the edge readable where it crosses the line.
        f.box(x - 260, y - 29, 520, 39, "white", "none")
        f.label(x, y, call, size=28, link=RUN)

    process(710, 24, 500, "init", "PATH=/user", link="system/init.picoc#L100")
    process(710, 250, 500, "shell", "PATH=/user", link="user/shell.picoc")
    edge("M 960 154 V 250", 960, 211, "run(shell_pid, NULL, NULL)")

    # Each cpid identifies a separately loaded process, not a fixed PID value.
    branches = (
        (90, 1, 4, 'unsetenv("PATH")', "library/stdlib/env.picoc#L157", "PATH absent"),
        (710, 2, 5, 'setenv("PATH", "/test", true)', SETENV, "PATH=/test"),
        (1330, 3, 6, "no change", "", "PATH=/user"),
    )
    # A shared junction makes the shell's three direct children clear at a glance.
    f.parts.append(
        f'<path d="M 960 380 V 427 M 340 427 H 1580" fill="none" '
        f'stroke="{POINTER}" stroke-width="3"/>'
    )
    for x, child, grandchild, operation, operation_link, value in branches:
        center = x + 250
        process(x, 540, 500, f"Process {child}", value,
                operation=operation, operation_link=operation_link, changed=child != 3)
        process(x, 916, 500, f"Process {grandchild}", value, changed=child != 3)
        edge(f"M {center} 427 V 540", center, 493,
             f'run(cpid{child}, "arg1", NULL)')
        edge(f"M {center} 710 V 916", center, 817,
             f'run(cpid{grandchild}, "arg1", NULL)')
    f.save()


if __name__ == "__main__":
    origin()
    propagation()
