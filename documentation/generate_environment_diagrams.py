"""Generate the environment diagrams in README section 4.2.2.2.1.

Run with Python 3. Reuse the chapter 4 SVG style and keep read requests,
returned file contents, stored pointers, and copies explicitly labeled.
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
        width=1800, height=510, show_address_direction=False,
    )
    f.label(32, 32, "1. Init reads configuration and starts the shell", size=26,
            bold=True, anchor="start")
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
    f.label(910, 491, "Array and strings in init's User Process Heap", size=22)

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
    f.label(1614, 491, "Independent storage", size=22)
    f.save()


def propagation():
    f = Figure(
        "environment-propagation", "A run call copies the caller's environment twice",
        "The shell calls run(child_pid, arg1 arg2, NULL). The library stores the caller's "
        "environ pointer in the caller-local RunProcessRequest.environment. The kernel "
        "store_process_arguments function copies strings into the child's initial "
        "stack and builds the envp pointer array for them. At first dispatch, start_process calls "
        "initialize_environment, which creates the child's independent heap array and "
        "strings and assigns the child's environ global. Solid arrows are stored "
        "pointers and dashed arrows are copies. The PCB stores activation.sp, "
        "activation.baf and state, but no environment pointer.",
        width=1800, height=535, show_address_direction=False,
    )
    f.label(32, 32, "2. One run() call: caller → child stack → child heap", size=26,
            bold=True, anchor="start")
    frame(f, 32, 520, "Caller: shell process", "user/shell.picoc#L1034")
    f.label(292, 132, 'run(child_pid, "arg1 arg2", NULL)', size=24,
            bold=True, link=RUN)
    f.box(52, 148, 480, 109, MUTED)
    f.label(292, 176, "RunProcessRequest request (caller stack)", size=19,
            bold=True, link=REQUEST)
    f.label(292, 204, 'pid = child_pid, arguments = "arg1 arg2"',
            size=22, link=REQUEST)
    f.label(292, 234, "environment = current_environment()", size=22,
            link="library/unistd/process.picoc#L37")
    f.label(292, 298, "current_environment() returns environ", size=21,
            link="library/stdlib/env.picoc#L6")
    # request.environment and environ point to the same caller heap array.
    f.parts.append(
        f'<path d="M 52 234 H 16 V 403 H 52" fill="none" '
        f'stroke="{POINTER}" stroke-width="2.5" '
        f'marker-end="url(#{POINTER[1:]})"/>'
    )
    environment(f, 52, 325, 480)
    f.label(292, 491, "Caller keeps its own heap array and strings", size=21)

    frame(f, 720, 480, "Kernel: prepares child stack", "kernel/process/process_arguments.picoc#L125")
    f.label(960, 154, "store_process_arguments(", size=23, bold=True,
            link="kernel/process/process_arguments.picoc#L125")
    f.label(960, 190, "process, request.arguments,", size=23,
            link="kernel/process/process_arguments.picoc#L125")
    f.label(960, 226, "request.environment)", size=23,
            link="common/syscall.header#L58")
    f.label(960, 285, "Writes into the child's User Process Stack", size=21)
    environment(f, 740, 325, 440, stack=True)
    f.label(626, 363, "1. copy", size=23, bold=True, color=POINTER)
    arrow(f, 532, 403, 740, 403, copy=True)

    frame(f, 1330, 438, "Child: first dispatch", "library/start/start.picoc#L7")
    f.label(1549, 155, "start_process() calls", size=23,
            link="library/start/start.picoc#L7")
    f.label(1549, 192, "initialize_environment(envp)", size=23,
            bold=True, link=INITIALIZE)
    f.label(1549, 243, "Assigns child's own environ", size=23, link=ENV)
    f.label(1549, 285, "Allocates in child's User Process Heap", size=21)
    environment(f, 1350, 325, 398)
    f.label(1265, 363, "2. copy", size=23, bold=True, color=POINTER)
    arrow(f, 1180, 403, 1350, 403, copy=True)
    f.label(1549, 491, "Later setenv() affects only this process", size=21, link=SETENV)

    f.label(960, 491, "PCB: activation.sp / activation.baf updated",
            size=20, link="kernel/process/process_arguments.picoc#L241")
    f.label(960, 525, "state = READY, no environment pointer", size=21,
            link="kernel/process/process.header#L31")
    f.save()


if __name__ == "__main__":
    origin()
    propagation()
