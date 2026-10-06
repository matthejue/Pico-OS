"""Generate README chapter 4 diagrams from the verified PicoOS memory model.

Run from any directory with Python 3. All widths are illustrative. Neighboring
regions share boundaries, pointers use curved arrows, and orange outlines mark
the region or fields discussed. No raster assets or external packages are used.
"""

from html import escape
from pathlib import Path

from generate_memory_layout_diagrams import (
    ADDRESS, ALLOCATED, FOCUS, FREE, HEADER, HEAP_EMPHASIS, LINE, METADATA, MUTED, POINTER, sram,
)

OUTPUT = Path(__file__).parent / "images"


class Figure:
    def __init__(self, slug, title, description, width=1760, height=880,
                 show_address_direction=True):
        self.slug, self.title, self.description = slug, title, description
        self.width, self.height = width, height
        self.parts, self.cells = [], {}
        if show_address_direction:
            self.label(32, 32, "Lower addresses → higher addresses · widths are illustrative",
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

    def expand(self, source, first, last):
        x, y, w, h = self.cells[source]
        tx, ty, _, _ = self.cells[first]
        ex, _, ew, _ = self.cells[last]
        self.parts.append(f'<path d="M {x} {y+h} L {tx} {ty} M {x+w} {y+h} L {ex+ew} {ty}" '
                          'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')

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


def process_list_diagram(slug, *, with_payloads=False):
    """Show process-list records in SRAM, optionally with their outer payloads."""
    data = (".data · kernel globals", "kernel_heap", "process_list_head",
            "process_list_tail", "active_process")
    kernel_payloads = [("Payload A", "PCB 1", "ProcessControlBlock", "next", "working_directory"),
                       ("Payload B", "working_directory", "PCB 1 owns this string"),
                       ("Payload C", "PCB 2", "ProcessControlBlock", "next"),
                       ("Payload D", "PCB 3", "ProcessControlBlock", "next = NULL")]
    outer_payloads = None
    title = "Global process list within SRAM"
    description = (
        "Kernel .ivt, .text and .data form the Kernel Image, followed by the Kernel Heap and "
        "Kernel Stack. The Process and Shared Data Heap follows the Kernel area. Global "
        "process_list_head, process_list_tail and active_process point to PCB 1, PCB 3 and PCB 2. "
        "Four schematic neighboring Kernel Heap blocks contain PCB 1, its working_directory string, "
        "PCB 2 and PCB 3. Above SRAM, ProcessControlBlock.next links PCB 1, PCB 2, PCB 3, NULL, "
        "skipping the directory allocation. The working_directory arrow also stays above SRAM. ")
    if with_payloads:
        title = "From PCBs to Process Payloads in SRAM"
        data = (".data · kernel globals", "global data")
        kernel_payloads = [("Payload A", "PCB 1", "ProcessControlBlock", "base_address"),
                           ("Payload B", "Shared Memory Entry", "SharedMemoryEntry", "address"),
                           ("Payload C", "PCB 2", "ProcessControlBlock", "base_address")]
        outer_payloads = [("Process Payload A", "PCB 1's user process", "image · heap · stack"),
                          ("Shared Data Payload B", "shared cells"),
                          ("Process Payload C", "PCB 2's user process", "image · heap · stack")]
        description = (
            "Kernel .ivt, .text and .data form the Kernel Image, followed by the Kernel Heap and "
            "Kernel Stack. The Process and Shared Data Heap follows the Kernel area. Each depicted "
            "heap has three Block Headers A, B and C. Kernel Heap Payloads A and C contain PCB 1 "
            "and PCB 2. Kernel Heap Payload B contains one SharedMemoryEntry. "
            "The PCBs' base_address fields reach Process Payloads "
            "A and C. Both addresses identify "
            "payload cells immediately after the corresponding outer headers.")
    else:
        data = (".data · kernel globals", "process_list_head", "process_list_tail", "active_process")
        description += (
            "Below SRAM, the same three PCB objects appear as a logical process list. "
            "process_list_head reaches PCB 1, process_list_tail reaches PCB 3, and active_process "
            "reaches PCB 2 in both views. PCB next links connect 1 to 2 to 3 to NULL. Dashed lines "
            "identify the same PCB objects across the two views. Allocator pointer arrows are omitted.")
    fig = sram(slug, title, description, data=data, kernel_payloads=kernel_payloads,
               outer_payloads=outer_payloads, kernel_payload_width=210,
               outer_payload_width=210, data_width=310, show_heap_links=False)
    if with_payloads:
        for source, target, lane in (("kpA", "opA", 80), ("kpC", "opC", 150)):
            fig.arrow(source, target, "base_address", lane=lane, color=ADDRESS,
                      source_shift=-55)
    else:
        fig.arrow("data", "kpA", "process_list_head", lane=175, source_shift=-35,
                  target_shift=5, label_x=590)
        fig.arrow("data", "kpD", "process_list_tail", lane=205,
                  source_shift=20, label_x=1390)
        fig.arrow("data", "kpC", "active_process", lane=245, source_shift=95,
                  label_x=1030)
        fig.arrow("kpA", "kpC", "next", lane=225, color=METADATA,
                  source_shift=55, target_shift=55)
        fig.arrow("kpC", "kpD", "next", lane=225, color=METADATA,
                  source_shift=55, target_shift=55)
        fig.arrow("kpA", "kpB", "working_directory", lane=275, color=ADDRESS)
        fig.highlight("data", "data")
    for key in (("kpA", "kpB", "kpC") if with_payloads else ("kpA", "kpC", "kpD")):
        x, w = fig.positions[key]
        fig.parts.append(fig.rect(x, 310, w, 156, "none", stroke=FOCUS, stroke_width=3))
    return fig


def process_list():
    fig = process_list_diagram("process-list")
    add_logical_process_list(fig)
    fig.save(notes=False, top=145)


def add_logical_process_list(fig):
    """Project the PCB allocations into a list without allocator cells."""
    lower_y = fig.bottom + 250
    logical = Figure("logical-process-list", "", "", width=fig.right + 32)
    logical.parts.clear()
    logical.box(32, lower_y, 330, 110, MUTED)
    logical.cells["roots"] = (32, lower_y, 330, 110)
    logical.label(197, lower_y + 25, "Kernel process-list globals", size=16, bold=True)
    for index, (label, line) in enumerate((("process_list_head", 16), ("process_list_tail", 17),
                                          ("active_process", 18))):
        logical.label(197, lower_y + 49 + index * 21, label,
                      link=f"kernel/process/process.picoc#L{line}")
    for number, x in enumerate((550, 1070, 1590), start=1):
        key = f"pcb{number}"
        logical.row(lower_y, 110, [
            (key, 300, (f"PCB {number}", "ProcessControlBlock",
                        "next = NULL" if number == 3 else "next"),
             ALLOCATED, "kernel/process/process.header#L31"),
        ], x=x)
        logical.focus(key)
        source = ("kpA", "kpC", "kpD")[number - 1]
        logical.parts.append(
            f'<path d="M {fig.center(source)} {fig.bottom} L {x + 150} {lower_y}" '
            'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')
    logical.focus("roots")
    for target, label, lane, shift in (("pcb1", "process_list_head", fig.bottom + 70, -60),
                                       ("pcb3", "process_list_tail", fig.bottom + 115, 0),
                                       ("pcb2", "active_process", fig.bottom + 160, 60)):
        logical.arrow("roots", target, label, lane, source_shift=shift)
    for source, target in (("pcb1", "pcb2"), ("pcb2", "pcb3")):
        x, y, width, _ = logical.cells[source]
        target_x, _, _, _ = logical.cells[target]
        x += width
        arrow_y = y + 78
        logical.parts.append(
            f'<path d="M {x} {arrow_y} C {x + 45} {arrow_y}, '
            f'{target_x - 45} {arrow_y}, {target_x} {arrow_y}" '
            f'fill="none" stroke="{METADATA}" stroke-width="2" '
            f'marker-end="url(#{METADATA[1:]})"/>')
        logical.label((x + target_x) / 2, arrow_y - 12, "next", size=14, color=METADATA,
                      link="kernel/process/process.header#L53")
    logical.box(32, fig.bottom + 34, 720, 30, "white", "none")
    fig.parts.extend(logical.parts)
    fig.height = lower_y + 110 + 32


def process_payload_links():
    fig = process_list_diagram("process-payload-links", with_payloads=True)
    fig.save(notes=False, top=55, bottom=fig.bottom + 20)


def placement():
    highlight_fill = ALLOCATED
    highlight_border = FOCUS
    outer_heap_fill = "#f6e8d5"
    f = Figure("stack-placement", "One user-process stack in the SRAM hierarchy",
               "The complete SRAM contains a Kernel area and the Process and Shared Data Heap. "
               "Each process is one independent allocator payload containing a User Process Image, "
               "User Process Heap and User Process Stack. A pale peach grouping band and thick red "
               "outline mark the entire Process and Shared Data Heap. Process Payload A and its User Process "
               "Stack are highlighted with matching blue fills and thick red outlines.",
               height=490, show_address_direction=False)
    f.row(100, 90, [("kernel", 430, ("Kernel area", "image · heap · stack"), MUTED),
                    ("ha", 100, ("Block", "Header A"), HEADER),
                    ("pa", 360, ("Process Payload A", "one user process"), highlight_fill),
                    ("hb", 100, ("Block", "Header B"), HEADER),
                    ("pb", 330, ("Process Payload B", "another user process"), MUTED),
                    ("other", 370, ("Other outer blocks", "processes · shared data · free space"), MUTED)])
    f.band("kernel", "kernel", 190, "Kernel area")
    f.band("ha", "other", 190, "Process and Shared Data Heap", outer_heap_fill)
    f.row(320, 100, [("ivt", 150, ("optional .ivt",), MUTED),
                     ("text", 300, (".text", "program + libraries"), MUTED),
                     ("data", 260, (".data", "process globals"), MUTED),
                     ("heap", 470, ("User Process Heap", "independent allocator"), MUTED),
                     ("stack", 510, ("User Process Stack", "grows toward lower addresses ←"), highlight_fill)])
    f.band("ivt", "data", 420, "User Process Image")
    f.band("heap", "heap", 420, "User Process Heap")
    f.band("stack", "stack", 420, "User Process Stack", highlight_fill)
    f.expand("pa", "ivt", "stack")
    x, y, _, h = f.cells["ha"]
    end, _, w, _ = f.cells["other"]
    f.box(x, y, end + w - x, h + 30, "none", highlight_border, 4)
    for key, band_height in (("pa", 0), ("stack", 30)):
        x, y, w, h = f.cells[key]
        f.box(x, y, w, h + band_height, "none", highlight_border, 4)
    f.save()


def memory_snapshot(f, running=False):
    """Common post-load/pre-dispatch layout for the load and run figures."""
    descriptor = ("Payload C", "child descriptor table", "new inherited copy") if running else (
        "Payload C", "child descriptor table", "fresh standard entries")
    child = ("Payload B · PCB 2", "state: NEW → READY", "sp = entry_pc_address − 1", "baf = entry_pc_address − 2",
             "file_descriptors replaced") if running else (
        "Payload B · PCB 2", "state = NEW", "sp = highest_stack_address − 1",
        "baf = highest_stack_address", "cs = base + code_start",
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
    stack = ("User Process Stack", "entry_pc_address: entry PC = cs − 1",
             "entry_pc_address + 1: argc", "argv[] · NULL · envp[] · NULL",
             "copied path, arguments, NAME=value strings",
             "highest_stack_address: final string terminator (overwrites old entry PC)") if running else (
        "User Process Stack", "lower cells: uninitialized", "highest_stack_address = base_address + size − 1",
        "M[highest_stack_address] = activation.cs − 1", "no argc, argv[] or envp[] yet", "stack grows ←")
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


def load_transfer():
    f = Figure("load-transfer", "Load step 1 · receive the linked image before creating its PCB",
               "EPROM, the mapped peripherals and SRAM appear in address order. The host responds "
               "through UART RX. CPU polling or optional DMA copies only binary payload words into "
               "the allocated User Process Image. A temporary ProcessLoad in the Kernel Heap is "
               "referenced by the caller PCB's pending_load field. No child PCB exists yet.",
               width=1824, height=725, show_address_direction=False)
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
    # Keep only the diagram, with a small margin around the host and transfer paths.
    f.parts = ['<g transform="translate(0,-55)">', *f.parts, '</g>']
    f.save()


def load_complete():
    f = Figure("load-complete", "Load step 2 · completed image, appended PCB, preliminary stack",
               "After transfer, create_process allocates PCB 2 in the Kernel Heap and initializes state "
               "to NEW. The previous tail PCB 1 receives next = PCB 2 and process_list_tail changes "
               "to PCB 2. The new PCB points to a fresh standard descriptor table and its Process "
               "Payload. create_process writes cs minus one into the cell at highest_stack_address. "
               "The argument and environment layout does not exist yet.", width=1824, height=735, show_address_direction=False)
    memory_snapshot(f)
    f.focus_lines("data", 2, 2, 4)
    f.focus_lines("caller", 2, 2, 4)
    f.focus("ustack")
    # Crop the space formerly occupied by the surrounding explanatory lines.
    f.parts = ['<g transform="translate(0,-125)">', *f.parts, '</g>']
    f.save()


def loaded_stack():
    f = Figure("loaded-stack", "Child stack after load · one preliminary entry-PC cell",
               "After a successful load, the child is NEW. Only the highest reserved stack cell, "
               "highest_stack_address = base_address + size - 1, is initialized to activation.cs - 1. "
               "Like the run stack table, the stack is drawn vertically with lower addresses at "
               "the top and higher addresses at the bottom. Direct arrows "
               "from the saved PCB registers show activation.baf pointing to that initialized cell "
               "and activation.sp pointing to the uninitialized cell immediately above it. "
               "Each of the bottom two stack boxes is one 32-bit cell; the top box represents all "
               "remaining reserved stack cells. Stack growth goes upward toward lower addresses. "
               "Arguments and environment are built later by run.",
               width=1060, height=458, show_address_direction=False)

    # Keep saved PCB fields separate from stack memory; each arrow ends at a cell.
    for field, y, color in (("activation.sp", 228, POINTER),
                            ("activation.baf", 328, METADATA)):
        f.box(24, y, 250, 54, MUTED)
        f.label(149, y + 34, field, size=20, bold=True, color=color)
        f.parts.append(
            f'<path d="M 274 {y+27} H 340" fill="none" stroke="{color}" '
            f'stroke-width="2" marker-end="url(#{color[1:]})"/>')

    # Equal-size single cells followed by a visibly larger collapsed region.
    f.box(340, 55, 360, 150, MUTED)
    f.box(340, 205, 360, 100, MUTED)
    f.box(340, 305, 360, 100, ALLOCATED)
    f.box(340, 305, 360, 100, "none", FOCUS, 3)
    f.label(520, 118, "Remaining cells", size=21, bold=True)
    f.label(520, 150, "Uninitialized", size=21)
    f.label(520, 261, "Uninitialized", size=22)
    f.label(520, 361, "activation.cs − 1", size=22, bold=True)

    f.label(520, 30, "↑ Lower addresses", size=20, bold=True)
    f.label(520, 438, "↓ Higher addresses", size=20, bold=True)
    f.label(724, 261, "highest_stack_address − 1", size=20, anchor="start")
    f.label(724, 361, "highest_stack_address", size=20, anchor="start")
    f.parts.append(
        f'<path d="M 742 176 V 87" fill="none" stroke="{ADDRESS}" '
        f'stroke-width="2" marker-end="url(#{ADDRESS[1:]})"/>')
    f.label(762, 137, "Stack grows", size=18, anchor="start", color=ADDRESS)
    f.save()


def run_setup():
    f = Figure("run-setup", "Run · inherit descriptors, build the initial stack, then set state to READY",
               "The same SRAM layout as the completed-load figure now highlights only the run "
               "effects: replace file_descriptors with an inherited independent table, write the "
               "initial User Process Stack, and change activation.sp, activation.baf and state. "
               "Arguments and environment are copied from the caller's user memory. Globals "
               "process_list_head, process_list_tail and active_process do not change during run setup. "
               "entry_pc_address identifies the new entry PC cell; highest_stack_address identifies "
               "the final stack cell. Caller input buffers "
               "are shown separately below the child's contiguous memory layout.", width=1824, height=870, show_address_direction=False)
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
    # Match the completed-load diagram's origin and leave room for the caller buffers.
    f.parts = ['<g transform="translate(0,-125)">', *f.parts, '</g>']
    f.save()


def initial_example():
    f = Figure("initial-stack-example", "Concrete initial stack · add.bin · two arguments · two environment variables",
               "Every box is one 32-bit RETI cell, labeled by its offset from entry_pc_address, "
               "which is base_address plus size minus 29. "
               "The first nine cells contain the entry PC, argc, three argument pointers and NULL, "
               "two environment pointers and NULL. Higher cells contain add.bin, 2, 3, X=1 "
               "and Y=0 with a zero cell after every string. argv is entry_pc_address + 2 "
               "and envp is entry_pc_address + 6. Pointer targets are shown as offsets 9, 17, 19, "
               "21 and 25, but stored pointers are absolute addresses: entry_pc_address plus that offset. "
               "Read rows in order, with increasing addresses "
               "to the right and stack growth to the left. Continuation arrows connect cell offsets "
               "8 to 9 and 16 to 17. "
               "All cells belong to the same contiguous stack.",
               width=1264, height=516, show_address_direction=False)
    cells = [
        ("entry", 100, ("offset 0", "entry PC", "cs − 1"), MUTED),
        ("argc", 100, ("offset 1", "argc", "3"), ALLOCATED),
        ("argv0", 100, ("offset 2", "argv[0]", "→ offset 9"), ALLOCATED),
        ("argv1", 100, ("offset 3", "argv[1]", "→ offset 17"), ALLOCATED),
        ("argv2", 100, ("offset 4", "argv[2]", "→ offset 19"), ALLOCATED),
        ("argvnull", 100, ("offset 5", "argv[3]", "NULL = 0"), MUTED),
        ("env0", 100, ("offset 6", "envp[0]", "→ offset 21"), ALLOCATED),
        ("env1", 100, ("offset 7", "envp[1]", "→ offset 25"), ALLOCATED),
        ("envnull", 100, ("offset 8", "envp[2]", "NULL = 0"), MUTED),
    ]
    f.row(32, 90, cells)
    f.band("argv0", "argvnull", 122, "argv")
    f.band("env0", "envnull", 122, "envp")

    def string_row(y, start, values):
        row = []
        for index, value in enumerate(values):
            offset = start + index
            character = "'\\0'" if value == "\0" else repr(value)
            row.append((f"s{offset}", 100, (f"offset {offset}", f"{character} = {ord(value)}"),
                        MUTED if value == "\0" else ALLOCATED))
        f.row(y, 72, row)

    string_row(216, 9, "add.bin\0")
    f.band("s9", "s16", 288, 'argv[0] → "add.bin\\0"')
    string_row(382, 17, "2\0" + "3\0" + "X=1\0" + "Y=0\0")
    for first, last, label in ((17, 18, 'argv[1] → "2\\0"'),
                               (19, 20, 'argv[2] → "3\\0"'),
                               (21, 24, 'envp[0] → "X=1\\0"'),
                               (25, 28, 'envp[1] → "Y=0\\0"')):
        f.band(f"s{first}", f"s{last}", 454, label)

    def continuation(source, target, lane):
        """Join consecutive memory cells across a line break in the drawing."""
        x, y, w, h = f.cells[source]
        tx, ty, _, th = f.cells[target]
        sx, sy, ty = x + w, y + h / 2, ty + th / 2
        right, left, radius = sx + 24, 12, 12
        path = (f"M {sx} {sy} H {right-radius} Q {right} {sy} {right} {sy+radius} "
                f"V {lane-radius} Q {right} {lane} {right-radius} {lane} "
                f"H {left+radius} Q {left} {lane} {left} {lane+radius} "
                f"V {ty-radius} Q {left} {ty} {left+radius} {ty} H {tx}")
        f.parts.append(f'<path d="{path}" fill="none" stroke="{FOCUS}" stroke-width="3" '
                       f'marker-end="url(#{FOCUS[1:]})"/>')

    continuation("envnull", "s9", 184)
    continuation("s16", "s17", 350)
    f.save()


def inheritance():
    heap_fill = "#f6e8d5"
    f = Figure("inheritance", "Parent-derived state · copies at load completion and at run setup",
               "The complete SRAM map shows a compact Kernel Image, a detailed Kernel Heap, "
               "a compact Kernel Stack, and the Process and Shared Data Heap as one compact region. "
               "The schematic contiguous Kernel Heap contains separate allocator blocks for parent "
               "and child PCBs, parent and child working-directory strings, and independent parent "
               "and child descriptor tables. Solid curved arrows are stored pointer fields. Dashed "
               "arrows mark copying operations, rather than shared pointers. parent_pid and "
               "parent_death_signal are copied integer values during creation.",
               width=2274, height=530, show_address_direction=False)
    f.row(150, 150, [
        ("image", 150, ("Kernel Image",), MUTED),
        ("ha", 60, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("parent", 290, ("Payload A · PCB 1", "parent / usual caller", "pid · parent_death_signal",
                         "working_directory", "file_descriptors"), MUTED,
         "kernel/process/process.header#L31"),
        ("hb", 60, ("Block", "Header B"), HEADER, "common/heap.header#L5"),
        ("child", 290, ("Payload B · PCB 2", "new child", "parent_pid · parent_death_signal",
                        "working_directory", "file_descriptors"), ALLOCATED,
         "kernel/process/process.header#L31"),
        ("hc", 60, ("Block", "Header C"), HEADER, "common/heap.header#L5"),
        ("pcwd", 185, ("Payload C", "parent directory", '"/user"'), MUTED,
         "kernel/process/process.header#L39"),
        ("hd", 60, ("Block", "Header D"), HEADER, "common/heap.header#L5"),
        ("ccwd", 185, ("Payload D", "child directory", '"/user" copy'), ALLOCATED,
         "kernel/process/process.header#L39"),
        ("he", 60, ("Block", "Header E"), HEADER, "common/heap.header#L5"),
        ("pfd", 200, ("Payload E", "parent table", "entries → own array"), MUTED,
         "kernel/filesystem/file_descriptor.header#L22"),
        ("hf", 60, ("Block", "Header F"), HEADER, "common/heap.header#L5"),
        ("cfd", 200, ("Payload F", "child table", "entries → own array"), ALLOCATED,
         "kernel/filesystem/file_descriptor.header#L22"),
        ("kstack", 130, ("Kernel Stack",), MUTED),
        ("outerheap", 220, ("Process and", "Shared Data Heap"), heap_fill,
         "kernel/psdmalloc.picoc#L7"),
    ])
    f.band("image", "image", 300, "Kernel Image")
    f.band("ha", "cfd", 300, "Kernel Heap", heap_fill)
    f.band("kstack", "kstack", 300, "Kernel Stack")
    f.band("outerheap", "outerheap", 300, "Process and Shared Data Heap", heap_fill)
    f.arrow("parent", "pcwd", "working_directory", 0, source_shift=-70, color=ADDRESS, label_x=700)
    f.arrow("child", "ccwd", "working_directory", 65, source_shift=-70, color=ADDRESS, label_x=1095)
    # Route the lower arrows from beneath the hierarchy band to keep it clear.
    pointer_cells = ("parent", "child", "pcwd", "ccwd", "pfd", "cfd")
    for key in pointer_cells:
        x, y, w, h = f.cells[key]
        f.cells[key] = (x, y, w, h + 30)
    f.arrow("pcwd", "ccwd", "copy string during load", 370, below=True, color=ADDRESS, dashed=True)
    f.arrow("parent", "pfd", "file_descriptors", 480, below=True, source_shift=70, label_x=760)
    f.arrow("child", "cfd", "file_descriptors", 560, below=True, source_shift=70, label_x=1330)
    f.arrow("pfd", "cfd", "deep copy during run", 360, below=True, color=METADATA, dashed=True)
    for key in pointer_cells:
        x, y, w, h = f.cells[key]
        f.cells[key] = (x, y, w, h - 30)
    f.focus("child")
    f.save()


def termination_status():
    """Locate the retained result pointer and the distinct waitpid stack objects.

    BAF_wait offsets follow libwait.reti_blocks: the three local cells are
    request.pid at -2, request.status at -1, and status at 0. The helper and
    interrupt context are grouped because their individual cells are not the
    result storage. PCB fields are selected, not a physical field-order view.
    """
    heap_fill = "#f6e8d5"
    status_fill = "#f6eee5"
    f = Figure("termination-status", "Where a child's termination status is stored",
               "Continuous SRAM has a Kernel Image, Kernel Heap with separate parent and child "
               "PCB allocations, Kernel Stack, and Process and Shared Data Heap with separate "
               "parent and child payloads. Expanded PCB fields show the parent's saved status "
               "pointer and the child's exit_status. The parent payload expands into image, "
               "heap, and stack, then into the suspended syscall and waitpid frames. "
               "WaitPidRequest occupies two cells containing pid and a pointer. A distinct "
               "int status cell receives 7. Solid arrows represent pointers and a dashed "
               "arrow represents the write of 7. After delivery the kernel clears the saved "
               "pointer and wait queue, wakes the parent, and removes the child.",
               width=1904, height=900, show_address_direction=False)
    f.row(130, 110, [
        ("ivt", 70, (".ivt",), MUTED),
        ("text", 100, (".text", "kernel code"), MUTED),
        ("data", 130, (".data", "kernel globals"), MUTED),
        ("kha", 60, ("Block", "Header A"), HEADER),
        ("parent", 190, ("Payload A", "PCB 1 · parent", "ProcessControlBlock"), ALLOCATED,
         "kernel/process/process.header#L31"),
        ("khb", 60, ("Block", "Header B"), HEADER),
        ("child", 190, ("Payload B", "PCB 2 · child", "ProcessControlBlock"), ALLOCATED,
         "kernel/process/process.header#L31"),
        ("kother", 60, ("Other", "blocks"), MUTED),
        ("kstack", 130, ("Kernel Stack", "kernel calls", "grows ←"), MUTED),
        ("oha", 60, ("Block", "Header A"), HEADER),
        ("pa", 300, ("Process Payload A · parent", "image · heap · stack"), ALLOCATED),
        ("ohb", 60, ("Block", "Header B"), HEADER),
        ("pb", 270, ("Process Payload B · child", "image · heap · stack"), ALLOCATED),
        ("other", 160, ("Other outer blocks", "shared data · free space"), MUTED),
    ])
    f.band("ivt", "data", 240, "Kernel Image")
    f.band("kha", "kother", 240, "", heap_fill)
    f.label(737, 261, "Kernel Heap", bold=True)
    f.band("kstack", "kstack", 240, "Kernel Stack")
    f.band("oha", "other", 240, "", heap_fill)
    f.label(1627, 261, "Process and Shared Data Heap", bold=True)
    f.arrow("parent", "pa", "base_address", 75, color=ADDRESS, label_x=840)
    f.arrow("child", "pb", "base_address", 95, color=ADDRESS, label_x=1190)

    # Show selected attributes inside their allocated PCBs, linked to definitions.
    for name, x, title, fields in (
        ("p", 32, "PCB 1 · parent", [
            ("pid", "pid = 1", 32),
            ("state", "state = BLOCKED → READY", 33),
            ("ptr", "waiting_status_ptr = &status", 44),
            ("base", "base_address → Process Payload A", 34),
        ]),
        ("c", 422, "PCB 2 · child", [
            ("pid", "pid = 2 · parent_pid = 1", 57),
            ("exit", "exit_status = 7", 60),
            ("state", "state = ZOMBIE", 33),
            ("waiters", "waiters.head / tail = &PCB 1", 46),
        ]),
    ):
        f.row(390, 42, [(name + "title", 350, (title,), ALLOCATED,
                         "kernel/process/process.header#L31")], x=x)
        for i, (key, value, line) in enumerate(fields):
            f.row(432 + i * 36, 36, [(name + key, 350, (value,), ALLOCATED,
                                     f"kernel/process/process.header#L{line}")], x=x)
    # Connect actual box corners, including the short section through each band.
    # The band labels sit clear of these lines.
    def expand_box(source, first, last):
        x, y, w, h = f.cells[source]
        tx, ty, _, _ = f.cells[first]
        ex, _, ew, _ = f.cells[last]
        bottom = y + h
        f.parts.append(
            f'<path d="M {x} {bottom} V {bottom + 30} L {tx} {ty} '
            f'M {x + w} {bottom} V {bottom + 30} L {ex + ew} {ty}" '
            'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')

    expand_box("parent", "ptitle", "ptitle")
    expand_box("child", "ctitle", "ctitle")

    f.row(390, 130, [
        ("ptext", 160, (".text", "program + libraries"), MUTED),
        ("pdata", 160, (".data", "process globals"), MUTED),
        ("pheap", 220, ("User Process Heap", "own allocator"), heap_fill),
        ("pstack", 512, ("User Process Stack", "suspended waitpid() call", "grows toward lower addresses ←"),
         ALLOCATED, "library/sys/wait/wait.picoc#L14"),
    ], x=820)
    f.band("ptext", "pdata", 520, "User Process Image")
    f.band("pheap", "pheap", 520, "User Process Heap", heap_fill)
    f.band("pstack", "pstack", 520, "User Process Stack", ALLOCATED)
    expand_box("pa", "ptext", "pstack")

    f.row(780, 120, [
        ("unused", 100, ("Unused", "stack cells"), FREE),
        ("context", 210, ("Saved syscall context", "registers + return PC"), MUTED,
         "interrupt_service_routines/os_isrs.picoc#L94"),
        ("helper", 210, ("invoke_waitpid_syscall", "frame + arguments", "argument = &request"), MUTED,
         "library/sys/wait/wait.picoc#L4"),
        ("rpid", 150, ("BAF_wait - 2", "request.pid = 2"), ALLOCATED,
         "common/syscall.header#L62"),
        ("rstatus", 200, ("BAF_wait - 1", "request.status", "= &status (address)"), ALLOCATED,
         "common/syscall.header#L63"),
        ("status", 200, ("BAF_wait + 0", "int status", "0 → 7 (integer value)"), status_fill,
         "library/sys/wait/wait.picoc#L15"),
        ("savedbaf", 130, ("BAF_wait + 1", "Saved caller BAF"), MUTED),
        ("returnpc", 140, ("BAF_wait + 2", "Return PC"), MUTED),
        ("pidarg", 130, ("BAF_wait + 3", "pid argument = 2"), MUTED),
        ("caller", 170, ("Caller frames", "e.g. main()"), MUTED),
        ("startup", 200, ("Startup values", "argc · argv · envp", "strings"), MUTED),
    ])
    f.band("unused", "unused", 900, "Free cells", FREE)
    f.band("context", "context", 900, "Interrupt frame")
    f.band("helper", "helper", 900, "Helper call")
    f.band("rpid", "rstatus", 900, "struct WaitPidRequest request · 2 cells", ALLOCATED)
    f.band("status", "status", 900, "Separate int · 1 cell", status_fill)
    f.band("savedbaf", "pidarg", 900, "Saved frame + argument")
    f.band("caller", "startup", 900, "Older stack contents")
    f.band("rpid", "pidarg", 930, "waitpid() stack frame")
    expand_box("pstack", "unused", "startup")
    f.arrow("helper", "rpid", "IN1 = &request at INT 0", 712,
            color=ADDRESS, label_x=610)
    f.arrow("rstatus", "status", "request.status = &status", 706,
            color=POINTER, label_x=800)
    # Leave PCB fields through their right edges rather than crossing lower fields.
    def result_arrow(source, corridor, lane, target_shift, color, dashed=False):
        x, y, w, h = f.cells[source]
        tx, ty, tw, _ = f.cells["status"]
        sx, sy, tx = x + w, y + h / 2, tx + tw / 2 + target_shift
        d = (f"M {sx} {sy} H {corridor - 8} Q {corridor} {sy} {corridor} {sy + 8} "
             f"V {lane - 12} Q {corridor} {lane} {corridor + 12} {lane} "
             f"H {tx - 12} Q {tx} {lane} {tx} {lane + 12} V {ty}")
        style = ' stroke-dasharray="7 4"' if dashed else ""
        f.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{style} '
                       f'marker-end="url(#{color[1:]})"/>')

    result_arrow("pptr", 402, 658, -55, POINTER)
    f.label(402, 643, "1. Save request.status in parent PCB", size=14,
            color=POINTER, anchor="start", link="kernel/process/process.picoc#L370")
    result_arrow("cexit", 792, 618, 45, METADATA, dashed=True)
    f.label(812, 585, "2. Kernel writes 7 through waiting_status_ptr", size=14,
            color=METADATA, anchor="start", link="kernel/process/process.picoc#L271")
    # Crop the space formerly occupied by the heading and surrounding notes.
    f.parts = ['<g transform="translate(0,-75)">', *f.parts, '</g>']
    f.save()


def main():
    OUTPUT.mkdir(exist_ok=True)
    process_list()
    process_payload_links()
    placement()
    load_transfer()
    load_complete()
    loaded_stack()
    run_setup()
    initial_example()
    inheritance()
    termination_status()


if __name__ == "__main__":
    main()
