"""Generate two wide pipeline snapshots with fixed process and file rows.

Both figures read left to right and reserve fixed rows for shell, producer,
consumer, and the temporary host file. Child rows stay blank before run.
Reaped processes have no descriptor table. Successful foreground execution
and initially free shell slots 3–7 are assumed. Redirection calls are expanded
in section 12.6 rather than repeated here. No external packages are required.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import ALLOCATED, FOCUS, METADATA, MUTED, POINTER


PCB = "kernel/process/process.header"
FD = "kernel/filesystem/file_descriptor.header"
SHELL = "user/shell.picoc"
RUN = "library/unistd/process.picoc#L31"
WAIT = "library/sys/wait/wait.picoc#L15"
XS = (260, 600, 940, 1280)
WIDTH = 300
ROW_TOPS = (108, 298, 488, 678)
ROW_HEIGHT = 150
TERMINAL = ("terminal", "terminal", "terminal")


def arrow(figure, path, colour=METADATA, dashed=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    figure.parts.append(
        f'<path d="{path}" fill="none" stroke="{colour}" '
        f'stroke-width="2.5"{dash} marker-end="url(#{colour[1:]})"/>'
    )


def descriptors(figure, x, y, standard, *, saved=(), focus=()):
    """Snapshot of entries: three standard paths and all other slot states."""
    figure.box(x, y, WIDTH, ROW_HEIGHT, ALLOCATED)
    for index, (role, destination) in enumerate(zip(("stdin", "stdout", "stderr"), standard)):
        line_y = y + 28 + index * 27
        if index in focus:
            figure.box(x + 4, line_y - 21, WIDTH - 8, 27, "none", FOCUS, 2)
        figure.label(x + 14, line_y, f"{index} · {role}", size=20,
                     bold=True, anchor="start", link=f"{FD}#L15")
        figure.label(x + WIDTH - 14, line_y, destination, size=20,
                     bold=True, anchor="end", link=f"{FD}#L19")
    if saved == (6,):
        other = "3–5 free · 6 terminal · 7 free"
    elif saved == (5, 6):
        other = "3–4 free · 5–6 terminal · 7 free"
    else:
        other = "3–7 free"
    figure.label(x + WIDTH / 2, y + 116, other, size=18, link=f"{FD}#L23")


def absent(figure, x, y, status):
    figure.box(x, y, WIDTH, ROW_HEIGHT, MUTED)
    figure.label(x + WIDTH / 2, y + 84, status, size=22)


def generate(*, consumer=False):
    slug = "pipeline-consumer" if consumer else "pipeline"
    figure = Figure(
        slug, "Consumer stage" if consumer else "Producer stage",
        "LEFT | RIGHT > OUT is executed sequentially using a temporary host file. "
        "Four columns read left to right. The rows always mean shell PCB 1, "
        "producer PCB 2 for LEFT, consumer PCB 3 for RIGHT, and temporary host "
        "file TMP. Descriptor cells show FileDescriptorTable.entries reached "
        "through ProcessControlBlock.file_descriptors. Terminal abbreviates "
        "/device/terminal.dev. Saved shell slots 5 and 6 are not inherited. "
        "Gray dashed arrows show run copying descriptor entries 0–2. Amber "
        "outlines mark changed standard paths. Child rows are blank before "
        "run, with no process boxes or placeholders. A child's first table "
        "appears when run copies the shell descriptors. Reaped processes "
        "keep their rows without descriptor cells. Each "
        "waitpid column shows the result after the child exits and is reaped. "
        + ("The producer has already been reaped. The shell redirects stdout "
           "to OUT before redirecting stdin to TMP. The consumer reads complete "
           "producer output. TMP is removed after the consumer wait."
           if consumer else
           "The consumer has not been created. The shell redirects stdout to "
           "TMP, starts the producer, restores terminal output, then waits for "
           "the producer to exit. TMP then contains the complete producer output."),
        width=1612, height=794, show_address_direction=False,
    )
    for row, name, number, command in (
        (0, "Shell", 1, ""),
        (1, "Producer", 2, "LEFT > TMP"),
        (2, "Consumer", 3, "RIGHT < TMP > OUT"),
    ):
        y = ROW_TOPS[row]
        figure.label(32, y + 38, name, size=25, bold=True, anchor="start")
        if command:
            figure.label(32, y + 70, command, size=21, bold=True,
                         anchor="start", link=f"{SHELL}#L{32 if row == 1 else 33}")
        offset = 28 if command else 0
        figure.label(32, y + 70 + offset, f"PCB {number}",
                     size=21, anchor="start", link=f"{PCB}#L31")
        figure.label(32, y + 101 + offset, "file_descriptors", size=18,
                     anchor="start", link=f"{PCB}#L42")
    figure.label(32, ROW_TOPS[3] + 35, "TMP", size=25, bold=True,
                 anchor="start", link=f"{SHELL}#L34")
    figure.label(32, ROW_TOPS[3] + 67, "host file", size=21, anchor="start")

    first = 5 if consumer else 1
    target = "consumer" if consumer else "producer"
    headings = (
        ("load(RIGHT)" if consumer else "load(LEFT)", "library/unistd/process.picoc#L17"),
        (f"run({target})", RUN),
        ("Restore shell", f"{SHELL}#L971"),
        ("Wait and remove TMP" if consumer else "Wait for producer", WAIT),
    )
    for column, (heading, link) in enumerate(headings):
        x = XS[column]
        figure.label(x + WIDTH / 2, 40, f"{first + column}. {heading}",
                     size=23, bold=True, link=link)
        if column < 3:
            arrow(figure, f"M {x + WIDTH + 5} 38 H {XS[column + 1] - 5}", POINTER)
    figure.label(XS[0] + WIDTH / 2, 78,
                 "stdin ← TMP · stdout → OUT" if consumer else "stdout → TMP",
                 size=18, link=f"{SHELL}#L1039")
    figure.label(XS[3] + WIDTH / 2, 78, f"waitpid({target})", size=20, link=WAIT)
    if consumer:
        figure.label(XS[3] + WIDTH / 2, 100, "unlink(TMP)", size=17,
                     link="library/unistd/file_removal.picoc#L4")

    redirected = ("TMP", "OUT", "terminal") if consumer else ("terminal", "TMP", "terminal")
    active_row = 2 if consumer else 1
    inactive_row = 1 if consumer else 2
    saved = (5, 6) if consumer else (6,)
    changed = (0, 1) if consumer else (1,)
    for column, x in enumerate(XS):
        descriptors(figure, x, ROW_TOPS[0], redirected if column < 2 else TERMINAL,
                    saved=saved if column < 2 else (),
                    focus=changed if column in (0, 2) else ())
        if consumer:
            absent(figure, x, ROW_TOPS[inactive_row], "Reaped")
        if column == 3:
            absent(figure, x, ROW_TOPS[active_row], "Exited · reaped")
        elif column > 0:
            descriptors(figure, x, ROW_TOPS[active_row], redirected,
                        focus=changed if column == 1 else ())

        y = ROW_TOPS[3]
        figure.box(x, y, WIDTH, 88, MUTED if consumer and column == 3 else ALLOCATED)
        file_status = ("Removed" if column == 3 else "Complete producer output") if consumer else (
            "Created / truncated", "Producer writes", "Producer writes", "Complete producer output"
        )[column]
        figure.label(x + WIDTH / 2, y + 50, file_status, size=20,
                     bold=True, link=f"{SHELL}#L34")

    # Copy arrows travel in the gaps. The consumer arrow bypasses the producer
    # row, which remains present after the producer has been reaped.
    x = XS[1]
    if consumer:
        arrow(figure, f"M {x + WIDTH} {ROW_TOPS[0] + 70} H {x + WIDTH + 20} "
              f"V {ROW_TOPS[2] + 70} H {x + WIDTH}", dashed=True)
    else:
        arrow(figure, f"M {x + WIDTH / 2} {ROW_TOPS[0] + ROW_HEIGHT} "
              f"V {ROW_TOPS[1]}", dashed=True)
    figure.save()


def main():
    generate()
    generate(consumer=True)


if __name__ == "__main__":
    main()
