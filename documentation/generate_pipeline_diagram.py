"""Generate the wide, two-row pipeline sequence in README section 12.7.

Each row reads left to right. The return arrow connects the completed
producer wait to consumer setup. Descriptor snapshots assume an ordinary
terminal shell with slots 3–7 initially free and successful redirection.
Run with Python 3, using the existing sharp-corner SVG style and colours.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import ALLOCATED, FOCUS, MUTED, POINTER


def main():
    figure = Figure(
        "pipeline", "Sequential file-backed pipeline",
        "LEFT | RIGHT > OUT becomes LEFT > TMP followed by RIGHT < TMP > OUT. "
        "TMP is .picoos-pipe-<shell PID>.tmp. Read the producer row left to "
        "right, then the consumer row left to right. Each row shows shell "
        "redirection, run copying the child descriptors, immediate shell "
        "restoration, and waitpid. The producer wait completes before the "
        "consumer starts. All eight descriptor slots are accounted for in "
        "each snapshot. T-in, T-out and T-err are the original terminal "
        "endpoints. The shell saves stdin in slot 5 and stdout in slot 6. "
        "Neither saved slot is inherited by the child. The consumer setup "
        "applies stdout redirection before stdin redirection. TMP holds the "
        "complete producer output during the consumer stage and is unlinked "
        "after the consumer wait. The snapshots show each process's PCB "
        "file_descriptors table entries, not memory allocation order.",
        width=1840, height=740, show_address_direction=False,
    )
    xs = (32, 488, 944, 1400)
    width, height = 408, 286

    def arrow(path, colour=POINTER):
        figure.parts.append(
            f'<path d="{path}" fill="none" stroke="{colour}" '
            f'stroke-width="2.5" marker-end="url(#{colour[1:]})"/>'
        )

    def card(column, y, title, link, fill=MUTED):
        x = xs[column]
        figure.box(x, y, width, height, fill)
        figure.label(x + width / 2, y + 34, title, size=23, bold=True, link=link)
        return x + width / 2

    def operation(x, y, text, link):
        figure.label(x, y, text, size=21, link=link)

    def snapshot(column, y, owner, standard, other):
        x = xs[column]
        figure.box(x, y + 194, width, 92, ALLOCATED)
        figure.label(x + width / 2, y + 218, owner + " descriptors", size=19,
                     bold=True, link="kernel/process/process.header#L42")
        figure.label(x + width / 2, y + 247, standard, size=21,
                     link="kernel/filesystem/file_descriptor.header#L23")
        figure.label(x + width / 2, y + 274, other, size=20,
                     link="kernel/filesystem/file_descriptor.header#L23")

    figure.label(32, 40, "Producer · LEFT > TMP", size=24, bold=True,
                 anchor="start", link="user/shell.picoc#L32")
    figure.label(32, 410, "Consumer · RIGHT < TMP > OUT", size=24, bold=True,
                 anchor="start", link="user/shell.picoc#L33")

    # Stage 1: redirect the shell, start the producer, restore, then wait.
    y = 60
    x = card(0, y, "1  Redirect stdout", "user/shell.picoc#L1003")
    operation(x, y + 74, "open(TMP) → 3", "library/fcntl/fcntl.picoc#L5")
    operation(x, y + 109, "dup2(1, 6)", "library/unistd/io.picoc#L58")
    operation(x, y + 144, "dup2(3, 1)", "library/unistd/io.picoc#L58")
    operation(x, y + 179, "close(3)", "library/unistd/io.picoc#L54")
    snapshot(0, y, "shell", "0 T-in · 1 TMP · 2 T-err",
             "3–5 free · 6 T-out · 7 free")

    x = card(1, y, "2  Start producer", "library/unistd/process.picoc#L31")
    operation(x, y + 86, "run() copies descriptors 0–2",
              "library/unistd/process.picoc#L31")
    figure.label(x, y + 130, "Saved slot 6 stays in the shell", size=21,
                 link="kernel/filesystem/file_descriptor.picoc#L99")
    snapshot(1, y, "producer", "0 T-in · 1 TMP · 2 T-err", "3–7 free")

    x = card(2, y, "3  Restore shell", "user/shell.picoc#L966")
    operation(x, y + 86, "dup2(6, 1)", "library/unistd/io.picoc#L58")
    operation(x, y + 130, "close(6)", "library/unistd/io.picoc#L54")
    snapshot(2, y, "shell", "0 T-in · 1 T-out · 2 T-err", "3–7 free")

    x = card(3, y, "4  Wait for producer", "library/sys/wait/wait.picoc#L14")
    operation(x, y + 95, "waitpid(producer)", "library/sys/wait/wait.picoc#L14")
    figure.label(x, y + 150, "Producer has finished", size=23, bold=True)
    figure.box(xs[3], y + 194, width, 92, ALLOCATED, FOCUS, 2)
    figure.label(x, y + 230, "TMP", size=24, bold=True,
                 link="user/shell.picoc#L34")
    figure.label(x, y + 266, "Complete producer output", size=23, bold=True)

    # The return path stays outside the cards and their stage labels.
    arrow("M 1604 346 V 375 H 16 V 573 H 32", FOCUS)
    figure.label(920, 369, "Producer finishes before consumer starts", size=21,
                 bold=True, color=FOCUS, link="user/shell.picoc#L798")

    # Stage 2: stdout is set up first, then stdin, reusing free slot 3.
    y = 430
    x = card(0, y, "5  Redirect stdout and stdin", "user/shell.picoc#L1034")
    for centre, label, operations in (
        (x - 100, "stdout first", (
            ("open(OUT) → 3", "library/fcntl/fcntl.picoc#L5"),
            ("dup2(1, 6)", "library/unistd/io.picoc#L58"),
            ("dup2(3, 1)", "library/unistd/io.picoc#L58"),
            ("close(3)", "library/unistd/io.picoc#L54"),
        )),
        (x + 100, "stdin next", (
            ("dup2(0, 5)", "library/unistd/io.picoc#L58"),
            ("close(0)", "library/unistd/io.picoc#L54"),
            ("open(TMP) → 0", "library/fcntl/fcntl.picoc#L5"),
        )),
    ):
        figure.label(centre, y + 67, label, size=19, bold=True)
        for index, (text, link) in enumerate(operations):
            figure.label(centre, y + 94 + index * 28, text, size=19, link=link)
    snapshot(0, y, "shell", "0 TMP · 1 OUT · 2 T-err",
             "3–4 free · 5 T-in · 6 T-out · 7 free")

    x = card(1, y, "6  Start consumer", "library/unistd/process.picoc#L31")
    operation(x, y + 86, "run() copies descriptors 0–2",
              "library/unistd/process.picoc#L31")
    figure.label(x, y + 130, "Saved slots 5–6 stay in the shell", size=21,
                 link="kernel/filesystem/file_descriptor.picoc#L99")
    snapshot(1, y, "consumer", "0 TMP · 1 OUT · 2 T-err", "3–7 free")

    x = card(2, y, "7  Restore shell", "user/shell.picoc#L966")
    operation(x, y + 74, "dup2(5, 0)", "library/unistd/io.picoc#L58")
    operation(x, y + 109, "close(5)", "library/unistd/io.picoc#L54")
    operation(x, y + 144, "dup2(6, 1)", "library/unistd/io.picoc#L58")
    operation(x, y + 179, "close(6)", "library/unistd/io.picoc#L54")
    snapshot(2, y, "shell", "0 T-in · 1 T-out · 2 T-err", "3–7 free")

    x = card(3, y, "8  Wait, then remove TMP", "user/shell.picoc#L799")
    operation(x, y + 86, "waitpid(consumer)", "library/sys/wait/wait.picoc#L14")
    arrow(f"M {x} {y + 102} V {y + 132}")
    operation(x, y + 162, "unlink(TMP)", "library/unistd/file_removal.picoc#L4")
    figure.box(xs[3], y + 194, width, 92, ALLOCATED)
    figure.label(x, y + 230, "OUT", size=24, bold=True)
    figure.label(x, y + 266, "Consumer output", size=23, bold=True)

    for y in (60, 430):
        for column in range(3):
            arrow(f"M {xs[column] + width} {y + height / 2} "
                  f"H {xs[column + 1]}")
    figure.save()


if __name__ == "__main__":
    main()
