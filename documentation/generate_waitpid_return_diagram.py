"""Generate the CPU/SRAM location and return-path views for README 10.1.3.

Run with Python 3. Region names, address order, colors and expansion guides
match chapter 3. Execution steps have their own view so that memory allocations
cannot be mistaken for executing components.
"""

from html import escape
from pathlib import Path

from diagram_style import style_svg
from generate_memory_layout_diagrams import ALLOCATED, FREE, HEADER, MUTED, POINTER, METADATA
from generate_process_diagrams import Figure


OUTPUT = Path(__file__).resolve().parent / "images"
PCB = "kernel/process/process.header"
ISR = "interrupt_service_routines/os_isrs.picoc"
WAIT = "library/sys/wait/wait.picoc"
PROCESS = "kernel/process/process.picoc"
DISPATCHER = "kernel/dispatcher.picoc"
WAITING = "#fff1d6"


class WaitFigure(Figure):
    def __init__(self, slug, title, description, height):
        super().__init__(slug, title, description, width=1760, height=height,
                         show_address_direction=False)

    def path(self, d, *, color=POINTER, arrow=True, dashed=False):
        marker = f' marker-end="url(#{color[1:]})"' if arrow else ""
        dash = ' stroke-dasharray="6 5"' if dashed else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" '
                          f'stroke-width="2.5"{marker}{dash}/>')

    def save(self):
        defs = "".join(
            f'<marker id="{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>'
            for c in (POINTER, METADATA)
        )
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
               f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
               'role="img" aria-labelledby="title desc">'
               f'<title id="title">{escape(self.title)}</title>'
               f'<desc id="desc">{escape(self.description)}</desc><defs>{defs}</defs>'
               '<g font-family="Cantarell, sans-serif">' + "".join(self.parts) + '</g></svg>\n')
        OUTPUT.mkdir(exist_ok=True)
        (OUTPUT / f"{self.slug}.svg").write_text(style_svg(svg), encoding="utf-8")


def locations():
    f = WaitFigure(
        "waitpid-memory-context", "Where waitpid executes and keeps its state",
        "One CPU executes kernel and userspace instructions at different times. "
        "It fetches the syscall ISR, wait handler and dispatcher from kernel .text, "
        "and waitpid and its helper from the parent's .text. Live registers belong "
        "to the CPU. SRAM is shown in increasing address order: Kernel Image, "
        "Kernel Heap, Kernel Stack, Process and Shared Data Heap. Kernel .data "
        "contains active_process. PCB 1 for the parent and PCB 2 for the child "
        "are Kernel Heap allocations. PCB 1 embeds activation and waiting_status_ptr. "
        "PCB 2 embeds waiters, whose head points to PCB 1 during the wait. "
        "The parent's Process Payload A contains its image, heap and stack. "
        "The expanded user stack contains the saved interrupt registers, the saved "
        "PC, WaitPidRequest request, and the separate int status. request.status "
        "and waiting_status_ptr point to status. activation.sp points to the saved "
        "ACC cell, immediately below the saved PC. Dashed guides enlarge the same "
        "storage. Other allocations and stack cells are omitted. Widths are illustrative.",
        800,
    )
    f.box(32, 20, 1696, 136, "white", thickness=2)
    f.label(52, 51, "CPU · kernel and user code execute here at different times",
            size=25, bold=True, anchor="start")
    for x, w, title, detail, link in (
        (52, 620, "Kernel code", "syscall_interrupt → wait handler → dispatcher", f"{ISR}#L94"),
        (692, 620, "Parent's user code", "waitpid → helper → INT 0 → resumed helper", f"{WAIT}#L14"),
        (1332, 376, "Live CPU registers", "PC · CS · DS · SP · BAF …", ""),
    ):
        f.box(x, 66, w, 74, MUTED)
        f.label(x + w / 2, 94, title, size=22, bold=True, link=link)
        f.label(x + w / 2, 124, detail, size=20, link=link)

    f.label(32, 215, "SRAM · lower addresses → higher addresses", size=25,
            bold=True, anchor="start")
    f.label(1728, 215, "Widths are illustrative", size=17, anchor="end")
    f.row(236, 90, [
        ("ivt", 60, (".ivt",), MUTED, f"{ISR}#L23"),
        ("text", 180, (".text", "kernel instructions"), MUTED, f"{ISR}#L94"),
        ("data", 170, (".data", "active_process"), MUTED, f"{PROCESS}#L18"),
        ("kheap", 290, ("PCB 1 · PCB 2", "other allocations"), ALLOCATED, f"{PCB}#L31"),
        ("kstack", 160, ("kernel calls", "grows ←"), MUTED),
        ("header", 60, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("image", 260, ("User Process Image", ".text: waitpid + helper", ".data"), MUTED, f"{WAIT}#L4"),
        ("uheap", 160, ("User Process Heap",), MUTED),
        ("ustack", 236, ("saved interrupt frame", "request · status", "grows ←"), ALLOCATED, f"{WAIT}#L15"),
        ("other", 120, ("other blocks", "child payload …"), MUTED),
    ])
    for first, last, label in (
        ("ivt", "data", "Kernel Image"),
        ("kheap", "kheap", "Kernel Heap"),
        ("kstack", "kstack", "Kernel Stack"),
        ("image", "image", "User Process Image"),
        ("uheap", "uheap", "User Process Heap"),
        ("ustack", "ustack", "User Process Stack"),
    ):
        f.band(first, last, 326, label)
    f.band("ivt", "kstack", 356, "Kernel")
    f.band("header", "other", 356, "Process and Shared Data Heap")
    f.band("image", "ustack", 386, "Process Payload A · parent")

    # Instructions are stored in SRAM and fetched by the one CPU above it.
    f.path("M 182 236 V 225 H 650 V 179 H 362 V 140", color=METADATA)
    f.label(362, 174, "fetch kernel instructions", size=18)
    f.path("M 1082 236 V 179 H 1002 V 140", color=METADATA)
    f.label(1170, 174, "fetch parent instructions", size=18)

    for key, x, w, title in (
        ("heap_detail", 32, 700, "Kernel Heap · PCB fields used by the wait"),
        ("stack_detail", 820, 908, "Parent's User Process Stack · retained during the wait"),
    ):
        f.cells[key] = (x, 472, w, 260)
        f.box(x, 472, w, 260, "white", thickness=2)
        f.box(x, 472, w, 44, MUTED)
        f.label(x + w / 2, 501, title, size=21, bold=True)
    for source, target in (("kheap", "heap_detail"), ("ustack", "stack_detail")):
        x, _, w, _ = f.cells[source]
        f.cells[source] = (x, 236, w, 150 if source == "kheap" else 180)
        f.expand(source, target, target)

    f.box(52, 530, 390, 170, ALLOCATED)
    f.label(247, 560, "PCB 1 · parent", size=23, bold=True, link=f"{PCB}#L31")
    f.label(247, 594, "activation: saved user registers", size=21, link=f"{PCB}#L40")
    f.label(247, 626, "activation.sp", size=21, link=f"{PCB}#L25")
    f.label(247, 658, "waiting_status_ptr", size=21, link=f"{PCB}#L44")
    f.label(247, 687, "state = BLOCKED", size=20, link=f"{PCB}#L33")
    f.box(462, 530, 250, 170, MUTED)
    f.label(587, 560, "PCB 2 · child", size=23, bold=True, link=f"{PCB}#L31")
    f.label(587, 594, "waiters.head", size=21, link=f"{PCB}#L46")
    f.path("M 462 608 H 442")
    f.label(587, 630, "→ PCB 1", size=21)
    f.label(587, 674, "child payload omitted", size=17)

    for x, w, fill, lines in (
        (840, 290, ALLOCATED, (
            ("Saved registers", f"{ISR}#L94"), ("DS · CS · BAF", ""),
            ("IN2 = 1 · IN1 · ACC", ""),
            ("caller_context[1..6]", f"{DISPATCHER}#L71"))),
        (1130, 168, HEADER, (
            ("Saved PC", ""), ("INT 0 address", ""),
            ("read by RTI", f"{DISPATCHER}#L40"), ("[7]", ""))),
        (1298, 250, ALLOCATED, (
            ("WaitPidRequest", "common/syscall.header#L61"),
            ("request.pid = child PID", "common/syscall.header#L62"),
            ("request.status = &status", "common/syscall.header#L63"))),
        (1548, 160, WAITING, (
            ("int status", f"{WAIT}#L15"), ("0 → result", ""))),
    ):
        f.box(x, 530, w, 142, fill)
        for i, (label, link) in enumerate(lines):
            f.label(x + w / 2, 559 + 30 * i, label, size=19 if i else 21,
                    bold=i == 0, link=link)
    f.label(1370, 701, "Other stack frames / cells omitted", size=18)
    f.label(1370, 727, "Stack grows toward lower addresses ←", size=18)
    # Address arrows use dedicated lanes outside the memory panels.
    f.path("M 52 626 H 16 V 752 H 1000 V 672")
    f.label(650, 745, "activation.sp → saved ACC cell", size=19, link=f"{DISPATCHER}#L75")
    f.path("M 442 658 H 774 V 778 H 1628 V 672")
    f.label(1050, 774, "waiting_status_ptr → status", size=19, link=f"{PCB}#L44")
    f.path("M 1423 530 V 523 H 1628 V 530")
    f.save()


def return_paths():
    f = WaitFigure(
        "waitpid-return-paths", "Waitpid execution steps and the corresponding SRAM changes",
        "Read numbered columns 1 through 5 from left to right. The top row "
        "shows successive execution on the same CPU. The lower row shows the "
        "corresponding SRAM changes, not another CPU. Step 1 is parent user code "
        "calling INT 0. Step 2 is kernel interrupt entry and wait handling. "
        "Immediate completion writes status and skips to step 5 through register "
        "restoration and RTI, possibly after rescheduling. A blocking wait saves "
        "PCB 1.activation, retains waiting_status_ptr, queues PCB 1 on PCB 2.waiters, "
        "and changes PCB 1.state to BLOCKED. Step 3 is execution of the child or "
        "other processes while the parent's stack stays allocated. Step 4 is kernel "
        "notification of child termination or stopping: it writes through the "
        "retained pointer, clears that pointer and removes the parent from the "
        "queue, making PCB 1.state READY. When the parent is selected, the "
        "dispatcher restores activation and executes RTI. Step 5 resumes the "
        "parent after INT 0 with IN2 equal to 1 and waitpid returns stack-local "
        "status. This timeline assumes the parent itself is not stopped.",
        524,
    )
    f.path("M 542 140 V 78 H 1554 V 140", color=METADATA)

    cards = (
        ("1", "Parent user code", "waitpid → helper", "INT 0", f"{WAIT}#L4", MUTED),
        ("2", "Kernel code", "syscall_interrupt", "wait_for_process_by_pid", f"{PROCESS}#L348", MUTED),
        ("3", "Child / other user code", "parent waits", "CPU runs other processes", f"{DISPATCHER}#L55", WAITING),
        ("4", "Kernel code", "child stops / terminates", "notify waiting parent", f"{PROCESS}#L261", MUTED),
        ("5", "Parent user code", "helper resumes after INT 0", "waitpid returns status", f"{WAIT}#L14", FREE),
    )
    # Identical columns align CPU actions with the SRAM changes below.
    for i, (number, title, line1, line2, link, fill) in enumerate(cards):
        x = 32 + 344 * i
        f.box(x, 140, 320, 132, fill, thickness=2)
        f.label(x + 20, 126, f"Step {number}", size=22, bold=True, anchor="start")
        for j, label in enumerate((title, line1, line2)):
            f.label(x + 160, 172 + 34 * j, label, size=20, bold=j == 0, link=link)
        if i < 4:
            f.path(f"M {x + 320} 206 H {x + 344}", color=METADATA)
        f.path(f"M {x + 160} 272 V 338", color=METADATA, arrow=False, dashed=True)

    changes = (
        (("Parent stack", f"{WAIT}#L15"),
         ("request.pid = child PID", "common/syscall.header#L62"),
         ("request.status = &status", "common/syscall.header#L63"),
         ("status = 0", f"{WAIT}#L15")),
        (("Parent stack → PCB 1", f"{DISPATCHER}#L71"),
         ("save frame → activation", f"{PCB}#L40"),
         ("retain waiting_status_ptr", f"{PCB}#L44"),
         ("state = BLOCKED", f"{PCB}#L33")),
        (("PCB 2.waiters → PCB 1", f"{PCB}#L46"),
         ("parent stays queued", f"{PROCESS}#L375"),
         ("parent stack stays allocated", f"{WAIT}#L15"),
         ("saved IN2 = 1", f"{ISR}#L121")),
        (("PCB 1 → parent stack", f"{PCB}#L44"),
         ("*waiting_status_ptr = result", f"{PROCESS}#L261"),
         ("clear pointer, leave queue", f"{PROCESS}#L395"),
         ("state = READY", f"{PCB}#L33")),
        (("Parent resumes", f"{DISPATCHER}#L21"),
         ("saved registers → CPU", f"{PCB}#L40"),
         ("RTI reads stack's saved PC", f"{DISPATCHER}#L40"),
         ("waitpid reads status", f"{WAIT}#L22")),
    )
    for i, lines in enumerate(changes):
        x = 32 + 344 * i
        f.box(x, 338, 320, 166, ALLOCATED if i != 2 else WAITING)
        for j, (label, link) in enumerate(lines):
            f.label(x + 160, 370 + 34 * j, label, size=20, bold=j == 0, link=link)

    f.save()


def generate():
    locations()
    return_paths()


if __name__ == "__main__":
    generate()
