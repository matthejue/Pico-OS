"""Generate README chapter 4 diagrams from the verified PicoOS memory model.

Run from any directory with Python 3. All widths are illustrative. Neighboring
regions share boundaries, pointers use curved arrows, and orange outlines mark
the region or fields discussed. No raster assets or external packages are used.
"""

from html import escape
from pathlib import Path

from generate_memory_layout_diagrams import (
    ADDRESS, ALLOCATED, FOCUS, HEADER, LINE, METADATA, MUTED, POINTER, sram,
)

OUTPUT = Path(__file__).parent / "images"


class Figure:
    def __init__(self, slug, title, description, width=1760, height=880):
        self.slug, self.title, self.description = slug, title, description
        self.width, self.height = width, height
        self.parts, self.cells = [], {}
        self.label(32, 32, title, size=23, bold=True, anchor="start")
        self.label(32, 61, "Lower addresses → higher addresses · widths are illustrative",
                   size=16, anchor="start")

    def label(self, x, y, value, size=15, bold=False, color=LINE,
              anchor="middle", link=""):
        text = (f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
                f'font-size="{size}" font-weight="{"bold" if bold else "normal"}" '
                f'fill="{color}">{escape(str(value))}</text>')
        if link:
            text = f'<a href="../../{escape(link, quote=True)}">{text}</a>'
        self.parts.append(text)

    def box(self, x, y, w, h, fill=MUTED, stroke=LINE, thickness=1):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{thickness}"/>')

    def row(self, y, height, cells, x=32):
        """Each cell is (key, width, lines, fill[, source link])."""
        start = x
        for cell in cells:
            key, w, lines, fill, *link = cell
            self.cells[key] = (x, y, w, height)
            self.box(x, y, w, height, fill)
            for i, line in enumerate(lines):
                font = min(15, (w - 12) / max(1, len(line) * 0.59))
                self.label(x + w / 2, y + height / 2 + (i - (len(lines) - 1) / 2) * 21 + 5,
                           line, size=font, bold=i == 0, link=link[0] if link else "")
            x += w
        self.box(start, y, x - start, height, "none", thickness=1.5)

    def band(self, first, last, y, text, fill=MUTED):
        x, _, _, _ = self.cells[first]
        end, _, w, _ = self.cells[last]
        self.box(x, y, end + w - x, 30, fill)
        font = min(15, (end + w - x - 10) / max(1, len(text) * 0.64))
        self.label((x + end + w) / 2, y + 21, text, size=font, bold=True)

    def focus(self, key):
        x, y, w, h = self.cells[key]
        self.box(x, y, w, h, "none", FOCUS, 3)

    def focus_lines(self, key, first, last, total):
        x, y, w, h = self.cells[key]
        top = y + h / 2 + (first - (total - 1) / 2) * 21 - 12
        self.box(x + 3, top, w - 6, (last - first) * 21 + 22, "none", FOCUS, 2)

    def arrow(self, source, target, label, lane, color=POINTER, below=False,
              source_shift=0, target_shift=0, label_x=None, dashed=False):
        x, y, w, h = self.cells[source]
        tx, ty, tw, th = self.cells[target]
        x += w / 2 + source_shift
        tx += tw / 2 + target_shift
        y += h if below else 0
        ty += th if ty < y else 0
        style = ' stroke-dasharray="7 4"' if dashed else ""
        self.parts.append(f'<path d="M {x} {y} C {x} {lane}, {tx} {lane}, {tx} {ty}" '
                          f'fill="none" stroke="{color}" stroke-width="2"{style} '
                          f'marker-end="url(#{color[1:]})"/>')
        lx = (x + tx) / 2 if label_x is None else label_x
        ly = (y + ty) / 8 + lane * 3 / 4
        self.box(lx - len(label) * 4.2 - 8, ly - 15, len(label) * 8.4 + 16, 22,
                 "white", "none")
        self.label(lx, ly + 1, label, size=14, color=color)

    def expand(self, source, first, last, caption):
        x, y, w, h = self.cells[source]
        tx, ty, _, _ = self.cells[first]
        ex, _, ew, _ = self.cells[last]
        self.parts.append(f'<path d="M {x} {y+h} L {tx} {ty} M {x+w} {y+h} L {ex+ew} {ty}" '
                          'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')
        self.label(32, ty - 20, caption, anchor="start", size=16, bold=True)

    def copy_to_right_edge(self, source, target, label, lane, corridor,
                           target_shift, label_x, color):
        """Keep input-copy arrows outside the child's hierarchy labels."""
        x, y, w, _ = self.cells[source]
        tx, ty, tw, th = self.cells[target]
        sx, tx, ty = x + w / 2, tx + tw, ty + th / 2 + target_shift
        path = (f"M {sx} {y} C {sx} {lane}, {corridor} {lane}, {corridor} {lane-25} "
                f"V {ty+15} Q {corridor} {ty} {corridor-15} {ty} H {tx}")
        self.parts.append(f'<path d="{path}" fill="none" stroke="{color}" '
                          f'stroke-width="2" stroke-dasharray="7 4" '
                          f'marker-end="url(#{color[1:]})"/>')
        self.box(label_x - len(label) * 4.2 - 8, lane - 14,
                 len(label) * 8.4 + 16, 22, "white", "none")
        self.label(label_x, lane + 2, label, size=14, color=color)

    def around_row(self, source, target, label, corridor, top_lane, bottom_lane,
                   color=POINTER):
        """Route a pointer around intervening memory rather than through its cells."""
        x, y, w, h = self.cells[source]
        tx, ty, tw, _ = self.cells[target]
        sx, sy, tx = x + w / 2, y + h, tx + tw / 2
        radius = 12
        d = (f"M {sx} {sy} V {top_lane-radius} Q {sx} {top_lane} {sx+radius} {top_lane} "
             f"H {corridor-radius} Q {corridor} {top_lane} {corridor} {top_lane+radius} "
             f"V {bottom_lane-radius} Q {corridor} {bottom_lane} {corridor-radius} {bottom_lane} "
             f"H {tx+radius} Q {tx} {bottom_lane} {tx} {bottom_lane+radius} V {ty}")
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
                          f'marker-end="url(#{color[1:]})"/>')
        lx = (tx + corridor) / 2
        self.box(lx - 40, bottom_lane - 13, 80, 20, "white", "none")
        self.label(lx, bottom_lane + 2, label, size=14, color=color)

    def save(self):
        defs = "".join(f'<marker id="{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                       f'markerWidth="6" markerHeight="6" orient="auto">'
                       f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>'
                       for c in (POINTER, ADDRESS, METADATA, FOCUS))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
               f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
               'role="img" aria-labelledby="title desc">'
               f'<title id="title">{escape(self.title)}</title>'
               f'<desc id="desc">{escape(self.description)}</desc><defs>{defs}</defs>'
               f'<rect width="{self.width}" height="{self.height}" fill="white"/>'
               '<g font-family="DejaVu Sans, sans-serif">' + "".join(self.parts) + '</g></svg>\n')
        (OUTPUT / f"process-{self.slug}.svg").write_text(svg)


def process_list():
    fig = sram("process-list", "Global process list within SRAM",
               "Kernel .ivt, .text and .data form the Kernel Image, followed by the Kernel Heap and "
               "Kernel Stack. The Process and Shared Data Heap follows the Kernel area. Global "
               "process_list_head, process_list_tail and active_process point to heap-allocated PCBs. "
               "Four schematic neighboring blocks contain PCB 1, its working_directory string, PCB 2 "
               "and PCB 3. BlockHeader.next links A, B, C, D, NULL. ProcessControlBlock.next links "
               "PCB 1, PCB 2, PCB 3, NULL, skipping the directory allocation.",
               data=(".data · kernel globals", "kernel_heap", "process_list_head",
                     "process_list_tail", "active_process"),
               kernel_payloads=[("Payload A", "PCB 1", "next"),
                                ("Payload B", "working_directory", "PCB 1 owns this string"),
                                ("Payload C", "PCB 2", "next"),
                                ("Payload D", "PCB 3", "next = NULL")],
               kernel_payload_width=210, data_width=310)
    fig.arrow("data", "kA", "kernel_heap.first_block", lane=80, source_shift=-90, label_x=480)
    fig.arrow("data", "kpA", "process_list_head", lane=115, source_shift=-35, label_x=590)
    fig.arrow("data", "kpD", "process_list_tail", lane=150, source_shift=20, label_x=1250)
    fig.arrow("data", "kpC", "active_process", lane=185, source_shift=95, label_x=1030)
    fig.arrow("kpA", "kpC", "next", lane=560, color=METADATA, below=True)
    fig.arrow("kpC", "kpD", "next", lane=560, color=METADATA, below=True)
    fig.arrow("kpA", "kpB", "working_directory", lane=610, color=ADDRESS, below=True)
    fig.highlight("data", "data")
    for key in ("kpA", "kpC", "kpD"):
        x, w = fig.positions[key]
        fig.parts.append(fig.rect(x, 310, w, 156, "none", stroke=FOCUS, stroke_width=3))
    fig.save()


def placement():
    f = Figure("stack-placement", "One user-process stack in the SRAM hierarchy",
               "The complete SRAM contains a Kernel area and the Process and Shared Data Heap. "
               "Each process is one independent allocator payload containing a User Process Image, "
               "User Process Heap and User Process Stack. Only the stack in Payload A is highlighted.",
               height=490)
    f.row(100, 90, [("kernel", 430, ("Kernel area", "image · heap · stack"), MUTED),
                    ("ha", 100, ("Block", "Header A"), HEADER),
                    ("pa", 360, ("Process Payload A", "one user process"), MUTED),
                    ("hb", 100, ("Block", "Header B"), HEADER),
                    ("pb", 330, ("Process Payload B", "another user process"), MUTED),
                    ("other", 370, ("Other outer blocks", "processes · shared data · free space"), MUTED)])
    f.band("kernel", "kernel", 190, "Kernel area")
    f.band("ha", "other", 190, "Process and Shared Data Heap")
    f.row(320, 100, [("ivt", 150, ("optional .ivt",), MUTED),
                     ("text", 300, (".text", "program + libraries"), MUTED),
                     ("data", 260, (".data", "process globals"), MUTED),
                     ("heap", 470, ("User Process Heap", "independent allocator"), MUTED),
                     ("stack", 510, ("User Process Stack", "grows toward lower addresses ←"), ALLOCATED)])
    f.band("ivt", "data", 420, "User Process Image")
    f.band("heap", "heap", 420, "User Process Heap")
    f.band("stack", "stack", 420, "User Process Stack", ALLOCATED)
    f.expand("pa", "ivt", "stack", "Expand Process Payload A · outer header remains outside the payload")
    f.focus("stack")
    f.save()


def memory_snapshot(f, running=False):
    """Common post-load/pre-dispatch layout for the load and run figures."""
    descriptor = ("Payload C", "child descriptor table", "new inherited copy") if running else (
        "Payload C", "child descriptor table", "fresh standard entries")
    child = ("Payload B · PCB 2", "state: NEW → READY", "sp = E − 1", "baf = E − 2",
             "file_descriptors replaced") if running else (
        "Payload B · PCB 2", "state = NEW", "sp = H − 1 · baf = H", "cs = base + code_start",
        "ds = base + data_start", "next = NULL")
    f.row(250, 170, [("ivt", 70, (".ivt",), MUTED), ("text", 110, (".text",), MUTED),
                     ("data", 260, (".data · kernel globals", "process_list_head = PCB 1",
                                    "process_list_tail = PCB 2", "active_process = PCB 1"), MUTED),
                     ("ha", 65, ("Block", "Header A"), HEADER),
                     ("caller", 200, ("Payload A · PCB 1", "caller / previous tail", "next = PCB 2",
                                      "pending_load = NULL"), MUTED),
                     ("hb", 65, ("Block", "Header B"), HEADER),
                     ("child", 270, child, ALLOCATED),
                     ("hc", 65, ("Block", "Header C"), HEADER),
                     ("fds", 210, descriptor, ALLOCATED),
                     ("other", 130, ("Other blocks", "paths · entries"), MUTED),
                     ("kstack", 90, ("Kernel", "Stack"), MUTED),
                     ("outer", 150, ("Process and", "Shared Data", "Heap"), MUTED)])
    f.band("ivt", "data", 420, "Kernel Image")
    f.band("ha", "other", 420, "Kernel Heap")
    f.band("kstack", "kstack", 420, "Kernel Stack")
    f.band("outer", "outer", 420, "Outer heap")
    f.band("ivt", "kstack", 450, "Kernel area")
    f.band("outer", "outer", 450, "After kernel")
    f.arrow("child", "fds", "file_descriptors", 180, source_shift=80, color=METADATA)
    f.arrow("caller", "child", "next", 155, source_shift=-30)
    if running:
        f.focus_lines("child", 1, 4, 5)
    else:
        f.focus("child")
    stack = ("User Process Stack", "E: entry PC = cs − 1", "E + 1: argc", "argv[] · NULL · envp[] · NULL",
             "copied path, arguments, NAME=value strings", "H: final string terminator (overwrites old entry PC)") if running else (
        "User Process Stack", "lower cells: uninitialized", "H = base_address + size − 1",
        "M[H] = activation.cs − 1", "no argc, argv[] or envp[] yet", "stack grows ←")
    f.row(615, 160, [("oh", 100, ("Outer Block", "Header B"), HEADER),
                     ("uivt", 130, ("optional .ivt",), MUTED),
                     ("utext", 270, (".text", "received instructions"), MUTED),
                     ("udata", 230, (".data", "received globals"), MUTED),
                     ("uheap", 310, ("User Process Heap", "reserved, uninitialized"), MUTED),
                     ("ustack", 720, stack, ALLOCATED)])
    f.band("oh", "oh", 775, "Metadata", HEADER)
    f.band("uivt", "udata", 775, "User Process Image")
    f.band("uheap", "uheap", 775, "User Process Heap")
    f.band("ustack", "ustack", 775, "User Process Stack", ALLOCATED)
    f.band("uivt", "ustack", 805, "Process Payload B · one allocation for the new user process")
    f.arrow("child", "uivt", "base_address", 540, below=True, source_shift=-85, color=ADDRESS)
    f.arrow("child", "ustack", "activation.sp / activation.baf", 560, below=True,
            source_shift=70, color=POINTER, label_x=1370)
    f.label(32, 605, "Expand the new Process Payload B from the outer heap", anchor="start", size=16)


def load_transfer():
    f = Figure("load-transfer", "Load step 1 · receive the linked image before creating its PCB",
               "EPROM, the mapped peripherals and SRAM appear in address order. The host responds "
               "through UART RX. CPU polling or optional DMA copies only binary payload words into "
               "the allocated User Process Image. A temporary ProcessLoad in the Kernel Heap is "
               "referenced by the caller PCB's pending_load field. No child PCB exists yet.",
               width=1824, height=850)
    f.row(175, 100, [("eprom", 140, ("EPROM", "0x00000000", "bootloader"), MUTED),
                     ("uart", 220, ("UART", "+0 TX · +1 RX", "+2 status"), ALLOCATED,
                      "../RETI-Emulator/include/uart.h"),
                     ("ic", 230, ("Interrupt controller", "+3…8 routing / priority", "+9 timer interval"), MUTED),
                     ("cpu", 190, ("CPU support", "+10 exception status", "+11 stack boundary"), MUTED),
                     ("dma", 200, ("DMA", "+12…16 registers", "optional --dma"), ALLOCATED,
                      "common/dma.header#L5"),
                     ("reserved", 140, ("Reserved", "peripheral cells"), MUTED),
                     ("sram", 640, ("SRAM · 0x80000000", "Kernel area | Process and Shared Data Heap"), MUTED)])
    f.band("uart", "reserved", 275, "Peripheral region · base 0x40000000")
    f.box(220, 80, 310, 55, ALLOCATED)
    f.cells["host"] = (220, 80, 310, 55)
    f.label(375, 102, "Host computer / executable .bin", bold=True)
    f.label(375, 124, "UART protocol response", size=14)
    f.arrow("host", "uart", "encoded words → UART RX", 145, below=True, color=ADDRESS)
    f.row(460, 140, [("ivt", 65, (".ivt",), MUTED), ("text", 90, (".text",), MUTED),
                     ("data", 180, (".data", "list roots"), MUTED),
                     ("ha", 70, ("Block", "Header A"), HEADER),
                     ("caller", 210, ("Payload A · PCB 1", "caller", "pending_load"), MUTED),
                     ("hb", 70, ("Block", "Header B"), HEADER),
                     ("load", 245, ("Payload B · ProcessLoad", "base_address · path", "loaded_word_count",
                                    "uses_dma"), ALLOCATED),
                     ("kstack", 100, ("Kernel", "Stack"), MUTED),
                     ("oh", 90, ("Outer Block", "Header B"), HEADER),
                     ("uimage", 275, ("User Process Image", "optional .ivt | .text | .data",
                                      "payload words being written"), ALLOCATED),
                     ("heap", 150, ("User Process", "Heap", "reserved"), MUTED),
                     ("stack", 215, ("User Process Stack", "reserved, uninitialized", "child PCB not created yet"), MUTED)])
    f.band("ivt", "data", 600, "Kernel Image")
    f.band("ha", "load", 600, "Kernel Heap")
    f.band("kstack", "kstack", 600, "Kernel Stack")
    f.band("uimage", "stack", 600, "New Process Payload B")
    f.band("ivt", "kstack", 630, "Kernel area")
    f.band("oh", "stack", 630, "Process and Shared Data Heap · other outer blocks omitted")
    f.arrow("caller", "load", "pending_load", 690, below=True)
    f.arrow("load", "uimage", "base_address", 760, below=True, color=METADATA)
    f.arrow("uart", "uimage", "CPU polling: receive_word() → SRAM store", 355,
            below=True, color=ADDRESS, label_x=635, dashed=True)
    f.arrow("dma", "uimage", "DMA: source = UART RX → destination = base_address", 390,
            below=True, color=POINTER, label_x=1320, dashed=True)
    f.focus("uimage")
    f.label(32, 823, "The five-word header is consumed by the kernel. It is not copied into the User Process Image.",
            anchor="start", size=16)
    f.save()


def load_complete():
    f = Figure("load-complete", "Load step 2 · completed image, appended PCB, preliminary stack",
               "After transfer, create_process allocates PCB 2 in the Kernel Heap and initializes state "
               "to NEW. The previous tail PCB 1 receives next = PCB 2 and process_list_tail changes "
               "to PCB 2. The new PCB points to a fresh standard descriptor table and its Process "
               "Payload. create_process writes cs minus one into the highest stack cell H. "
               "The argument and environment layout does not exist yet.", width=1824, height=890)
    f.label(32, 99, "create_process(): old tail.next = new PCB · process_list_tail = new PCB · next_process_id increments",
            anchor="start", size=16, color=FOCUS)
    memory_snapshot(f)
    f.focus_lines("data", 2, 2, 4)
    f.focus_lines("caller", 2, 2, 4)
    f.focus("ustack")
    f.label(32, 869, "finish_process_load(): caller.pending_load = NULL, temporary ProcessLoad and its path are freed.",
            anchor="start", size=16)
    f.save()


def run_setup():
    f = Figure("run-setup", "Run · inherit descriptors, build the initial stack, then set state to READY",
               "The same SRAM layout as the completed-load figure now highlights only the run "
               "effects: replace file_descriptors with an inherited independent table, write the "
               "initial User Process Stack, and change activation.sp, activation.baf and state. "
               "Arguments and environment are copied from the caller's user memory. Globals "
               "process_list_head, process_list_tail and active_process do not change during run setup. "
               "E is the new entry PC cell, H is the final stack cell. Caller input buffers "
               "are shown separately below the child's contiguous memory layout.", width=1824, height=1040)
    f.label(32, 99, "mark_process_ready_with_arguments(): descriptor copy → stack copy → state = READY",
            anchor="start", size=16, color=FOCUS)
    memory_snapshot(f, running=True)
    f.focus("fds")
    f.focus("ustack")
    f.row(900, 70, [("environment", 820, ("Caller environment pointer array and strings",
                                         "heap-backed environ or an explicitly supplied array"), MUTED)])
    f.row(900, 70, [("arguments", 820, ("Caller argument string",
                                       'shell stack array expanded_arguments: "2 3"'), MUTED)], x=972)
    f.copy_to_right_edge("environment", "ustack", "request.environment → NAME=value copies",
                         858, 1809, -25, 650, METADATA)
    f.copy_to_right_edge("arguments", "ustack", "request.arguments → token copies",
                         883, 1817, 25, 1430, ADDRESS)
    f.label(32, 1005, "Caller inputs are separate buffers. libstart initializes the child heap and clones its environment after dispatch.",
            anchor="start", size=16)
    f.save()


def initial_example():
    f = Figure("initial-stack-example", "Concrete initial stack · user/add.bin, arguments 2 and 3",
               "Every box is one 32-bit RETI cell. E is base_address plus size minus 36. "
               "The first nine cells contain the entry PC, argc, three argument pointers and NULL, "
               "two environment pointers and NULL. Higher cells contain user/add.bin, 2, 3, ADD=1 "
               "and X=0 with a zero cell after every string. argv is E+2 and envp is E+6. "
               "SP is E-1 and BAF is E-2. String rows expand the following contiguous string area "
               "in increasing address order, rather than being separate allocations.", width=1760, height=855)
    f.label(32, 92, "Stack grows ← toward lower addresses · SP = E − 1 · BAF = E − 2 · H = E + 35",
            anchor="start", size=16)
    cells = [
        ("entry", 180, ("E + 0", "entry PC", "activation.cs − 1"), MUTED),
        ("argc", 160, ("E + 1", "argc = 3", "value"), ALLOCATED),
        ("argv0", 185, ("E + 2 · argv[0]", "E + 9", "address of path"), ALLOCATED),
        ("argv1", 185, ("E + 3 · argv[1]", "E + 22", "address of 2"), ALLOCATED),
        ("argv2", 185, ("E + 4 · argv[2]", "E + 24", "address of 3"), ALLOCATED),
        ("argvnull", 160, ("E + 5", "argv[3] = NULL", "0x00000000"), MUTED),
        ("env0", 200, ("E + 6 · envp[0]", "E + 26", "address of ADD=1"), ALLOCATED),
        ("env1", 200, ("E + 7 · envp[1]", "E + 32", "address of X=0"), ALLOCATED),
        ("envnull", 190, ("E + 8", "envp[2] = NULL", "0x00000000"), MUTED),
    ]
    f.row(140, 110, cells)
    f.band("argv0", "argvnull", 250, "argv = E + 2 · address of argv[0]")
    f.band("env0", "envnull", 250, "envp = E + 6 = argv + argc + 1")

    def string_row(y, start, values, title):
        f.label(32, y - 15, title, anchor="start", size=16, bold=True)
        row = []
        for index, value in enumerate(values):
            offset = start + index
            row.append((f"s{offset}", 116, (f"E + {offset}", f"0x{ord(value):08x}",
                                            "'\\0'" if value == "\0" else repr(value)), ALLOCATED))
        f.row(y, 88, row)

    string_row(410, 9, "user/add.bin\0", "Path string · argv[0] points to its first cell")
    string_row(605, 22, "2\0" + "3\0" + "ADD=1\0" + "X=0\0",
               "Arguments, then environment strings · one cell per character, including each terminator")
    f.arrow("argv0", "s9", "argv[0]", 330, below=True, source_shift=-20)
    f.around_row("argv1", "s22", "argv[1]", 1580, 320, 520, ADDRESS)
    f.around_row("argv2", "s24", "argv[2]", 1620, 340, 540, ADDRESS)
    f.around_row("env0", "s26", "envp[0]", 1660, 360, 560, METADATA)
    f.around_row("env1", "s32", "envp[1]", 1700, 380, 580, METADATA)
    f.label(32, 752, "The string rows expand E + 9…E + 35 in the same allocation. Every pointer is an absolute SRAM cell address.",
            anchor="start", size=16)
    f.label(32, 786, "No separate argv or envp pointer cell is stored. The last X=0 terminator overwrites the preliminary entry PC at H.",
            anchor="start", size=16)
    f.save()


def inheritance():
    f = Figure("inheritance", "Parent-derived state · copies at load completion and at run setup",
               "A schematic contiguous Kernel Heap contains separate allocator blocks for parent "
               "and child PCBs, parent and child working-directory strings, and independent parent "
               "and child descriptor tables. Solid curved arrows are stored pointer fields. Dashed "
               "arrows mark copying operations, rather than shared pointers. parent_pid and "
               "parent_death_signal are copied integer values during creation.", height=720)
    f.label(32, 100, "Load completion: child.parent_pid = parent.pid · child.parent_death_signal = parent.parent_death_signal",
            anchor="start", size=16)
    f.row(280, 150, [
        ("ha", 60, ("Block", "Header A"), HEADER),
        ("parent", 290, ("Payload A · PCB 1", "parent / usual caller", "pid · parent_death_signal",
                         "working_directory", "file_descriptors"), MUTED),
        ("hb", 60, ("Block", "Header B"), HEADER),
        ("child", 290, ("Payload B · PCB 2", "new child", "parent_pid · parent_death_signal",
                        "working_directory", "file_descriptors"), ALLOCATED),
        ("hc", 60, ("Block", "Header C"), HEADER),
        ("pcwd", 185, ("Payload C", "parent directory", '"/user"'), MUTED),
        ("hd", 60, ("Block", "Header D"), HEADER),
        ("ccwd", 185, ("Payload D", "child directory", '"/user" copy'), ALLOCATED),
        ("he", 60, ("Block", "Header E"), HEADER),
        ("pfd", 200, ("Payload E", "parent table", "entries → own array"), MUTED),
        ("hf", 60, ("Block", "Header F"), HEADER),
        ("cfd", 200, ("Payload F", "child table", "entries → own array"), ALLOCATED),
    ])
    f.band("ha", "cfd", 430, "Kernel Heap · each header is immediately adjacent to its own payload")
    f.arrow("parent", "pcwd", "working_directory", 130, source_shift=-70, color=ADDRESS, label_x=550)
    f.arrow("child", "ccwd", "working_directory", 195, source_shift=-70, color=ADDRESS, label_x=945)
    f.arrow("pcwd", "ccwd", "copy string during load", 500, below=True, color=ADDRESS, dashed=True)
    f.arrow("parent", "pfd", "file_descriptors", 610, below=True, source_shift=70, label_x=610)
    f.arrow("child", "cfd", "file_descriptors", 690, below=True, source_shift=70, label_x=1180)
    f.arrow("pfd", "cfd", "deep copy during run", 490, below=True, color=METADATA, dashed=True)
    f.focus("child")
    f.label(32, 698, "Descriptor entry arrays and their path allocations are omitted. These copy operations never share those objects.",
            anchor="start", size=16)
    f.save()


def main():
    OUTPUT.mkdir(exist_ok=True)
    process_list()
    placement()
    load_transfer()
    load_complete()
    run_setup()
    initial_example()
    inheritance()


if __name__ == "__main__":
    main()
