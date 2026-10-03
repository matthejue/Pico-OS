"""Generate the contiguous, editable memory layouts used in README Section 3.

All widths are illustrative. Cells share one divider, and only stored pointers
get arrows. The grouping bands are part of the same memory rectangle.
"""

from dataclasses import dataclass
from html import escape
from pathlib import Path


OUTPUT = Path(__file__).parent / "images"
HEADER = "#fff0cc"
ALLOCATED = "#deecff"
FREE = "#e5f3de"
MUTED = "#f0f3f6"
FOCUS = "#9c3d15"
POINTER = "#405ea8"
METADATA = "#785099"
ADDRESS = "#26715b"
LINE = "#43576a"
TOP = 310
CELL_HEIGHT = 156
BAND_HEIGHT = 30
LEFT = 32


@dataclass
class Cell:
    key: str
    width: int
    lines: tuple
    fill: str = ALLOCATED
    link: str = ""
    bold_lines: int = 1


class Diagram:
    def __init__(self, slug, title, description, cells, bands=()):
        self.slug = slug
        self.title = title
        self.description = description
        self.cells = cells
        self.bands = bands
        self.parts = []
        self.positions = {}
        self.bottom = TOP + CELL_HEIGHT + len(bands) * BAND_HEIGHT
        self.height = self.bottom + 85
        self.right = LEFT + sum(c.width for c in cells)
        x = LEFT
        for cell in cells:
            self.positions[cell.key] = (x, cell.width)
            self.parts.append(self.rect(x, TOP, cell.width, CELL_HEIGHT, cell.fill))
            start_y = TOP + (CELL_HEIGHT - len(cell.lines) * 21) / 2 + 17
            labels = "".join(self.text(x + cell.width / 2, start_y + i * 21,
                                       value, size=14, bold=i < cell.bold_lines, max_width=cell.width - 10)
                             for i, value in enumerate(cell.lines))
            link = cell.link
            for type_name, location in (
                ("ProcessControlBlock", "kernel/process/process.header#L31"),
                ("SharedMemoryEntry", "kernel/shared_memory.header#L8"),
                ("SharedMemoryAttachment", "kernel/shared_memory.header#L17"),
            ):
                if type_name in cell.lines:
                    link = location
            if cell.lines[0].startswith("PCB "):
                link = "kernel/process/process.header#L31"
            elif cell.lines[0] == "Shared Memory" and cell.lines[1].startswith("Attachment"):
                link = "kernel/shared_memory.header#L17"
            elif cell.lines[0] == "Shared Memory" and cell.lines[1].startswith("Entry"):
                link = "kernel/shared_memory.header#L8"
            if link:
                labels = f'<a href="../../{escape(link, quote=True)}">{labels}</a>'
            self.parts.append(labels)
            x += cell.width
        # Fill the hierarchy bands, then draw each boundary exactly once.
        for level, groups in enumerate(bands):
            y = TOP + CELL_HEIGHT + level * BAND_HEIGHT
            for first, last, label, fill in groups:
                x, width = self.span(first, last)
                self.parts.append(self.rect(x, y, width, BAND_HEIGHT, fill))
                self.parts.append(self.text(x + width / 2, y + 20, label, size=15,
                                            bold=True, max_width=width - 8))
                if x != LEFT:
                    self.parts.append(self.path(f"M {x} {y} v {BAND_HEIGHT}", LINE))
            self.parts.append(self.path(f"M {LEFT} {y} H {self.right}", LINE))
        x = LEFT
        for cell in cells[:-1]:
            x += cell.width
            self.parts.append(self.path(f"M {x} {TOP} v {CELL_HEIGHT}", LINE))
        self.parts.append(self.rect(LEFT, TOP, self.right - LEFT, self.bottom - TOP,
                                    "none", stroke=LINE, stroke_width=1.5))

    @staticmethod
    def rect(x, y, width, height, fill, stroke="none", stroke_width=1):
        return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    @staticmethod
    def text(x, y, value, size=15, bold=False, color="#172b3a", anchor="middle", max_width=None):
        # Long exact identifiers must remain inside their physical memory cells.
        if max_width and value:
            size = min(size, max_width / (len(value) * (0.68 if bold else 0.62)))
        fit = (f' textLength="{max_width}" lengthAdjust="spacingAndGlyphs"'
               if max_width and len(value) * size * 0.59 > max_width else "")
        return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
                f'font-size="{size}" font-weight="{"bold" if bold else "normal"}" '
                f'fill="{color}"{fit}>{escape(value)}</text>')

    @staticmethod
    def path(d, color, arrow=False):
        marker = f' marker-end="url(#{color[1:]})"' if arrow else ""
        return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{marker}/>'

    def center(self, key):
        x, width = self.positions[key]
        return x + width / 2

    def span(self, first, last):
        x, _ = self.positions[first]
        end, width = self.positions[last]
        return x, end + width - x

    def arrow(self, source, target, label, lane=235, color=POINTER,
              below=False, label_x=None, source_shift=0, target_shift=0):
        x1 = self.center(source) + source_shift
        x2 = self.center(target) + target_shift
        y = self.bottom if below else TOP
        end_y = y + 3 if below else y - 3
        # Vertical stems and a rounded horizontal route keep labels on a level lane.
        radius = 12
        sign = 1 if x2 >= x1 else -1
        vertical = 1 if below else -1
        d = (f"M {x1} {y} V {lane - vertical * radius} "
             f"Q {x1} {lane} {x1 + sign * radius} {lane} "
             f"H {x2 - sign * radius} "
             f"Q {x2} {lane} {x2} {lane - vertical * radius} V {end_y}")
        self.parts.append(self.path(d, color, arrow=True))
        tx = (x1 + x2) / 2 if label_x is None else label_x
        label_width = len(label) * 8 + 14
        self.parts.append(self.rect(tx - label_width / 2, lane - 13, label_width, 18, "white"))
        self.parts.append(self.text(tx, lane + 1, label, size=14, color=color))
        if below:
            self.height = max(self.height, lane + 60)

    def chain(self, prefix, count=4):
        names = [prefix + chr(65 + i) for i in range(count)]
        for source, target in zip(names, names[1:]):
            left, right = self.center(source), self.center(target)
            self.parts.append(self.path(
                f"M {left} {TOP} C {left} 260, {right} 260, {right} {TOP - 3}",
                POINTER, arrow=True))
            middle = (left + right) / 2
            self.parts.append(self.rect(middle - 23, 258, 46, 18, "white"))
            self.parts.append(self.text(middle, 273, "next", size=14, color=POINTER))
        self.parts.append(self.text(self.center(names[-1]), TOP - 12,
                                    "next = NULL", size=13, color=POINTER))

    def highlight(self, first, last):
        x, width = self.span(first, last)
        self.parts.append(self.rect(x, TOP, width, CELL_HEIGHT + BAND_HEIGHT,
                                    "none", stroke=FOCUS, stroke_width=3))

    def save(self):
        width = self.right + LEFT
        defs = "".join(
            f'<marker id="{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
            for color in (POINTER, METADATA, ADDRESS))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
               f'height="{self.height}" viewBox="0 0 {width} {self.height}" '
               'role="img" aria-labelledby="title desc">\n'
               f'<title id="title">{escape(self.title)}</title>\n'
               f'<desc id="desc">{escape(self.description)}</desc>\n'
               f'<defs>{defs}</defs>\n'
               f'<rect width="{width}" height="{self.height}" fill="white"/>\n'
               '<g font-family="DejaVu Sans, sans-serif">\n'
               + self.text(LEFT, 28, self.title, size=21, bold=True, anchor="start")
               + self.text(LEFT, 55, "Low to high addresses →   ·   Widths are illustrative",
                           size=15, anchor="start")
               + "\n".join(self.parts)
               + self.text(LEFT, self.height - 20,
                           "Yellow: block headers   ·   Blue: allocated payloads   ·   Green: free payloads",
                           size=14, anchor="start")
               + "\n</g>\n</svg>\n")
        (OUTPUT / f"memory-{self.slug}.svg").write_text(svg)


def blocks(prefix, payloads, header_width=80, payload_width=170):
    cells = []
    for index, lines in enumerate(payloads):
        letter = chr(65 + index)
        free = lines[0].startswith("Free")
        cells.extend([
            Cell(prefix + letter, header_width,
                 ("Block", "Header " + letter, "size · free", "next"), HEADER,
                 "common/heap.header#L5"),
            Cell(prefix + "p" + letter, payload_width, tuple(lines), FREE if free else ALLOCATED),
        ])
    return cells


def sram(slug, title, description, *, data=(".data", "global data"),
         kernel_payloads=None, outer_payloads=None, focus=None,
         data_width=270, kernel_payload_width=170, outer_payload_width=175,
         kernel_header_width=70, outer_header_width=75):
    cells = [Cell("ivt", 70, (".ivt", "5 cells"), MUTED),
             Cell("text", 100, (".text", "kernel code"), MUTED),
             Cell("data", data_width, tuple(data), MUTED)]
    if kernel_payloads:
        cells.extend(blocks("k", kernel_payloads, kernel_header_width, kernel_payload_width))
        first_k, last_k = "kA", "kp" + chr(64 + len(kernel_payloads))
    else:
        cells.extend(blocks("k", [("Kernel objects", "other blocks", "omitted"),], 75, 130))
        first_k, last_k = "kA", "kpA"
    cells.append(Cell("stack", 115, ("Kernel", "Stack", "grows ←"), MUTED))
    if outer_payloads:
        cells.extend(blocks("o", outer_payloads, outer_header_width, outer_payload_width))
        first_o, last_o = "oA", "op" + chr(64 + len(outer_payloads))
    else:
        cells.append(Cell("outer", 260, ("Process and", "Shared Data Heap", "process + shared data"),
                          MUTED, bold_lines=2))
        first_o = last_o = "outer"
    bands = [
        [("ivt", "data", "Kernel Image", MUTED),
         (first_k, last_k, "Kernel Heap", ALLOCATED if focus == "kernel" else MUTED),
         ("stack", "stack", "Kernel Stack", MUTED),
         (first_o, last_o, "Process and Shared Data Heap", ALLOCATED if focus == "outer" else MUTED)],
        [("ivt", "stack", "Kernel", MUTED),
         (first_o, last_o, "After the Kernel region", MUTED)],
    ]
    diagram = Diagram(slug, title, description, cells, bands)
    if kernel_payloads:
        diagram.chain("k", len(kernel_payloads))
    if outer_payloads:
        diagram.chain("o", len(outer_payloads))
    if focus:
        diagram.highlight(*( (first_k, last_k) if focus == "kernel" else (first_o, last_o)))
    return diagram


def process(slug, expanded=False):
    cells = [Cell("outer_header", 90, ("Outer Block", "Header A"), HEADER,
                  "common/heap.header#L5"),
             Cell("ivt", 100, ("optional", ".ivt"), MUTED),
             Cell("text", 165, (".text", "program + libraries"), MUTED),
             Cell("data", 220, (".data", "global data", "process_heap"), MUTED,
                  "library/stdlib/malloc.picoc#L6")]
    payloads = ([("Payload A", "application object"),
                 ("Free Payload B",),
                 ("Payload C", "library object"),
                 ("Free Payload D",)] if expanded else
                [("Payload A", "application object"),
                 ("Payload B", "library object"),
                 ("Free Payload C",)])
    cells.extend(blocks("u", payloads, 85, 160))
    first, last = "uA", "up" + chr(64 + len(payloads))
    cells.append(Cell("stack", 260, ("User Process Stack", "arguments + saved state", "grows ←"), MUTED))
    bands = [
        [("outer_header", "outer_header", "Metadata", HEADER),
         ("ivt", "data", "User Process Image", MUTED),
         (first, last, "User Process Heap", ALLOCATED),
         ("stack", "stack", "User Process Stack", MUTED)],
        [("outer_header", "outer_header", "Outer header", HEADER),
         ("ivt", "stack", "Process Payload A · one allocation in the Process and Shared Data Heap", MUTED)],
    ]
    diagram = Diagram(slug, "Inside Process Payload A" if not expanded else "Per-process User Process Heap",
                      "An outer header is followed by one Process Payload. Only optional .ivt, .text and .data "
                      "belong to the User Process Image. The User Process Heap and User Process Stack follow it. "
                      "process_heap is a global in process .data and its first_block points to an inner heap header.",
                      cells, bands)
    diagram.arrow("data", "uA", "process_heap.first_block", lane=175)
    diagram.chain("u", len(payloads))
    if expanded:
        diagram.highlight(first, last)
    diagram.save()


def main():
    OUTPUT.mkdir(exist_ok=True)
    generic = Diagram("generic-heap", "Common heap block layout",
                      "One contiguous heap with four directly adjacent headers and payloads. "
                      "Heap.first_block points to Block Header A. Each next pointer links headers, never payloads.",
                      blocks("h", [("Allocated Payload A",), ("Free Payload B",),
                                   ("Allocated Payload C",), ("Free Payload D",)], 100, 210),
                      [[("hA", "hpD", "One managed heap region", MUTED)]])
    generic.parts.append(generic.rect(LEFT, 90, 370, 62, MUTED, stroke=LINE))
    generic.parts.append(generic.text(LEFT + 185, 115, "struct Heap descriptor", bold=True))
    generic.parts.append(generic.text(LEFT + 185, 138, "Placement depends on the heap", size=14))
    generic.parts.append(generic.path(
        f"M {LEFT + 185} 152 C {LEFT + 185} 210, {generic.center('hA')} 210, "
        f"{generic.center('hA')} {TOP - 3}", POINTER, arrow=True))
    generic.parts.append(generic.text(LEFT + 220, 200, "first_block", color=POINTER))
    generic.chain("h")
    generic.save()

    outer = [("Process Payload A",), ("Shared Data Payload B",),
             ("Process Payload C",), ("Free Payload D",)]
    overview = sram("sram-overview", "SRAM layout and heap hierarchy",
                    "Kernel .ivt, .text and .data are adjacent linked sections. The Kernel Heap follows "
                    "the Kernel Image, then the Kernel Stack. The Process and Shared Data Heap follows "
                    "the entire Kernel region. Each heap contains three illustrative blocks linked by next, "
                    "with a free payload behind its final header. Both kernel heap "
                    "descriptors and process-list and shared-memory roots are globals in kernel .data.",
                    data=(".data · global data", "kernel_heap", "process_shared_data_heap",
                          "process_list_head", "active_process", "shared_memory_list_head"),
                    kernel_payloads=[("Payload A", "kernel objects"),
                                     ("Payload B", "kernel objects"),
                                     ("Free Payload C",)],
                    outer_payloads=[("Process Payload A",), ("Shared Data Payload B",),
                                    ("Free Payload C",)],
                    data_width=280, outer_payload_width=200)
    overview.arrow("data", "kA", "kernel_heap.first_block", lane=195, source_shift=-55)
    overview.arrow("data", "oA", "process_shared_data_heap.first_block", lane=135, source_shift=55)
    overview.save()
    process("process-payload")

    kernel = sram("kernel-heap", "Kernel Heap blocks and concrete kernel objects",
                  "kernel_heap is in kernel .data and first_block points to Block Header A in the Kernel Heap. "
                  "The illustrative payloads are a ProcessControlBlock, its copied binary_path, "
                  "a SharedMemoryEntry and a free block. These are separate kmalloc allocations.",
                  data=(".data · global data", "kernel_heap"), focus="kernel",
                  kernel_payloads=[("PCB 1", "struct", "ProcessControlBlock"),
                                   ("binary_path string", "PCB-owned path copy"),
                                   ("Shared Memory Entry", "struct", "SharedMemoryEntry"),
                                   ("Free Payload D",)], kernel_payload_width=210)
    kernel.arrow("data", "kA", "kernel_heap.first_block", lane=175)
    kernel.arrow("kpA", "kpB", "binary_path", lane=225, color=METADATA)
    kernel.save()

    processes = sram("process-allocations", "PCBs manage Process Payloads in the outer heap",
                     "PCB 1 and PCB 2 are separate Kernel Heap payloads linked by ProcessControlBlock.next. "
                     "Their base_address fields point to Process Payload A and Process Payload C. "
                     "process_shared_data_heap is in kernel .data and first_block points to outer Block Header A.",
                     data=(".data · global data", "process_shared_data_heap", "process_list_head"),
                     kernel_payloads=[("PCB 1", "ProcessControlBlock", "base_address"), ("binary_path string",),
                                      ("PCB 2", "ProcessControlBlock", "base_address"), ("Free Payload D",)],
                     outer_payloads=outer, focus="outer", data_width=280, kernel_payload_width=180)
    processes.arrow("data", "oA", "process_shared_data_heap.first_block", lane=90, source_shift=45)
    processes.arrow("data", "kpA", "process_list_head", lane=135, source_shift=-45)
    processes.arrow("kpA", "kpC", "next", lane=230, color=METADATA)
    processes.arrow("kpA", "kpB", "binary_path", lane=250, color=METADATA)
    processes.arrow("kpA", "opA", "base_address", lane=170, color=ADDRESS, source_shift=-45)
    processes.arrow("kpC", "opC", "base_address", lane=205, color=ADDRESS, source_shift=-45)
    processes.save()

    shared = sram("shared-allocations", "Shared Memory Entries manage Shared Data Payloads",
                  "Two SharedMemoryEntry objects are separate Kernel Heap payloads. The independent global "
                  "shared_memory_list_head in kernel .data points to the first entry, linked to the second "
                  "by next. Their address fields point to separate Shared Data Payloads behind outer headers A and C.",
                  data=(".data · global data", "process_shared_data_heap", "shared_memory_list_head"),
                  kernel_payloads=[("Shared Memory Entry 1", "SharedMemoryEntry", "address"),
                                   ("Entry 1 name string",),
                                   ("Shared Memory Entry 2", "SharedMemoryEntry", "address"), ("Free Payload D",)],
                  outer_payloads=[("Shared Data Payload A",), ("Process Payload B",),
                                  ("Shared Data Payload C",), ("Free Payload D",)],
                  focus="outer", data_width=280, kernel_payload_width=190)
    shared.arrow("data", "oA", "process_shared_data_heap.first_block", lane=90, source_shift=45)
    shared.arrow("data", "kpA", "shared_memory_list_head", lane=135, source_shift=-45)
    shared.arrow("kpA", "kpC", "next", lane=230, color=METADATA)
    shared.arrow("kpA", "kpB", "name", lane=250, color=METADATA)
    shared.arrow("kpA", "opA", "address", lane=170, color=ADDRESS, source_shift=-45)
    shared.arrow("kpC", "opC", "address", lane=205, color=ADDRESS, source_shift=-45)
    shared.save()
    process("user-heap", expanded=True)

    mapping = sram("shared-mappings", "Two processes, three mappings, two Shared Data Payloads",
                   "All seven depicted metadata objects are separate Kernel Heap payloads. PCB 1 links "
                   "Shared Memory Attachment 1 then 2, referencing Shared Memory Entry 1 then 2. "
                   "PCB 2 links Shared Memory Attachment 3, also referencing Entry 1. Entry 1 has reference_count 2 "
                   "and Entry 2 has reference_count 1. Entries are linked by next from the independent global "
                   "shared_memory_list_head in kernel .data. address reaches each corresponding Shared Data Payload.",
                   data=(".data · global data", "process_shared_data_heap", "shared_memory_list_head"),
                   kernel_payloads=[("PCB 1",), ("PCB 2", "next = NULL"),
                                    ("Shared Memory", "Attachment 1"),
                                    ("Shared Memory", "Attachment 2", "next = NULL"),
                                    ("Shared Memory", "Attachment 3", "next = NULL"),
                                    ("Shared Memory", "Entry 1", "reference_count = 2"),
                                    ("Shared Memory", "Entry 2", "reference_count = 1", "next = NULL")],
                   outer_payloads=[("Shared Data", "Payload A"), ("Process", "Payload B"),
                                   ("Shared Data", "Payload C"), ("Process", "Payload D")],
                   data_width=280, kernel_payload_width=155, outer_payload_width=120,
                   kernel_header_width=60, outer_header_width=65,
                   focus="kernel")
    mapping.arrow("data", "kpF", "shared_memory_list_head", lane=90, source_shift=-40, label_x=720)
    mapping.arrow("data", "oA", "process_shared_data_heap.first_block", lane=125,
                  source_shift=45, label_x=1650)
    mapping.arrow("kpA", "kpB", "next", lane=220, color=METADATA)
    mapping.arrow("kpA", "kpC", "shared_memory_attachments", lane=165,
                  color=METADATA, label_x=740)
    mapping.arrow("kpB", "kpE", "shared_memory_attachments", lane=200,
                  color=METADATA, label_x=1020)
    mapping.arrow("kpC", "kpD", "next", lane=245, color=METADATA)
    mapping.arrow("kpF", "kpG", "next", lane=245, color=METADATA)
    mapping.arrow("kpF", "opA", "address", lane=165, color=ADDRESS)
    mapping.arrow("kpG", "opC", "address", lane=200, color=ADDRESS)
    for source, target, lane in [("kpC", "kpF", 565), ("kpD", "kpG", 605), ("kpE", "kpF", 645)]:
        mapping.arrow(source, target, "entry", lane=lane, color=METADATA, below=True)
    mapping.arrow("kpA", "opB", "base_address", lane=695, color=ADDRESS, below=True, label_x=1950)
    mapping.arrow("kpB", "opD", "base_address", lane=735, color=ADDRESS, below=True, label_x=2370)
    mapping.save()


if __name__ == "__main__":
    main()
