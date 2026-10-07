"""Generate the contiguous, editable memory layouts used in README Section 3.

All widths are illustrative. Cells share one divider, and only stored pointers
get arrows. Dashed lines expand a payload into its internal layout. The grouping
bands are part of the same memory rectangle.
"""

from dataclasses import dataclass
from html import escape
from pathlib import Path

from diagram_style import style_svg


OUTPUT = Path(__file__).parent / "images"
HEADER = "#fff0cc"
ALLOCATED = "#deecff"
FREE = "#e5f3de"
MUTED = "#f0f3f6"
FOCUS = "#9c3d15"
HEAP_EMPHASIS = "#ffd08a"
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
    def __init__(self, slug, title, description, cells, bands=(), *, emphasized_heaps=()):
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
        emphasized_regions = []
        for level, groups in enumerate(bands):
            y = TOP + CELL_HEIGHT + level * BAND_HEIGHT
            for first, last, label, fill in groups:
                x, width = self.span(first, last)
                emphasized = label in emphasized_heaps
                if emphasized:
                    fill = HEAP_EMPHASIS
                    emphasized_regions.append((first, last))
                self.parts.append(self.rect(x, y, width, BAND_HEIGHT, fill))
                self.parts.append(self.text(x + width / 2, y + 20, label, size=15,
                                            bold=True, max_width=width - 8,
                                            color=FOCUS if emphasized else "#172b3a"))
                if x != LEFT:
                    self.parts.append(self.path(f"M {x} {y} v {BAND_HEIGHT}", LINE))
            self.parts.append(self.path(f"M {LEFT} {y} H {self.right}", LINE))
        x = LEFT
        for cell in cells[:-1]:
            x += cell.width
            self.parts.append(self.path(f"M {x} {TOP} v {CELL_HEIGHT}", LINE))
        self.parts.append(self.rect(LEFT, TOP, self.right - LEFT, self.bottom - TOP,
                                    "none", stroke=LINE, stroke_width=1.5))
        for first, last in emphasized_regions:
            self.highlight(first, last)

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

    def chain(self, prefix, count=4, *, below=False):
        names = [prefix + chr(65 + i) for i in range(count)]
        if below:
            lane = self.bottom + 35
            for source, target in zip(names, names[1:]):
                self.arrow(source, target, "next", lane=lane, below=True)
            self.parts.append(self.text(self.center(names[-1]), lane + 32,
                                        "next = NULL", size=13, color=POINTER))
            self.height = max(self.height, lane + 75)
            return
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

    def expand(self, source, detail, first, last):
        """Expand one payload below the SRAM row, without implying a pointer."""
        scale = (self.right - LEFT) / (detail.right - LEFT)
        detail_top = self.bottom + 330
        dx = LEFT * (1 - scale)
        dy = detail_top - TOP * scale
        source_x, source_width = self.positions[source]
        source_bottom = TOP + CELL_HEIGHT
        detail_x, detail_width = detail.span(first, last)
        target_left = dx + detail_x * scale
        target_right = target_left + detail_width * scale
        self.parts.append(
            f'<path d="M {source_x} {source_bottom} L {target_left} {detail_top} '
            f'M {source_x + source_width} {source_bottom} L {target_right} {detail_top}" '
            'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')
        self.parts.append(
            f'<g transform="translate({dx} {dy}) scale({scale})">'
            + "\n".join(detail.parts) + '</g>')
        self.height = int(detail_top + (detail.bottom - TOP) * scale) + 85

    def save(self, *, notes=True, top=0, bottom=None):
        width = self.right + LEFT
        height = (self.height if bottom is None else bottom) - top
        defs = "".join(
            f'<marker id="{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
            for color in (POINTER, METADATA, ADDRESS))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
               f'height="{height}" viewBox="0 {top} {width} {height}" '
               'role="img" aria-labelledby="title desc">\n'
               f'<title id="title">{escape(self.title)}</title>\n'
               f'<desc id="desc">{escape(self.description)}</desc>\n'
               f'<defs>{defs}</defs>\n'
               '<g font-family="DejaVu Sans, sans-serif">\n'
               + (self.text(LEFT, 28, "Low to high addresses →   ·   Widths are illustrative",
                            size=15, anchor="start") if notes else "")
               + "\n".join(self.parts)
               + (self.text(LEFT, self.height - 20,
                            "Gray: block headers   ·   Teal: allocated payloads   ·   Green: free payloads",
                            size=14, anchor="start") if notes else "")
               + "\n</g>\n</svg>\n")
        (OUTPUT / f"memory-{self.slug}.svg").write_text(style_svg(svg, name=f"memory-{self.slug}"))


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
         kernel_header_width=70, outer_header_width=75, heap_links_below=False,
         emphasize_heaps=False, show_heap_links=True):
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
    diagram = Diagram(slug, title, description, cells, bands,
                      emphasized_heaps=("Kernel Heap", "Process and Shared Data Heap")
                      if emphasize_heaps else ())
    if kernel_payloads and show_heap_links:
        diagram.chain("k", len(kernel_payloads), below=heap_links_below)
    if outer_payloads and show_heap_links:
        diagram.chain("o", len(outer_payloads), below=heap_links_below)
    if focus:
        diagram.highlight(*( (first_k, last_k) if focus == "kernel" else (first_o, last_o)))
    return diagram


def process_layout(slug, expanded=False, *, include_outer_header=True, highlight_heap=True,
                   emphasize_heap=False):
    cells = ([Cell("outer_header", 90, ("Outer Block", "Header A"), HEADER,
                   "common/heap.header#L5")] if include_outer_header else [])
    cells.extend([
        Cell("ivt", 100, ("optional", ".ivt"), MUTED),
        Cell("text", 165, (".text", "program + libraries"), MUTED),
        Cell("data", 220, (".data", "global data", "process_heap"), MUTED,
             "library/stdlib/malloc.picoc#L6"),
    ])
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
        [("ivt", "data", "User Process Image", MUTED),
         (first, last, "User Process Heap", ALLOCATED),
         ("stack", "stack", "User Process Stack", MUTED)],
        [("ivt", "stack", "Process Payload A · one allocation in the Process and Shared Data Heap", MUTED)],
    ]
    if include_outer_header:
        bands[0].insert(0, ("outer_header", "outer_header", "Metadata", HEADER))
        bands[1].insert(0, ("outer_header", "outer_header", "Outer header", HEADER))
    diagram = Diagram(slug, "Inside Process Payload A" if not expanded else "Per-process User Process Heap",
                      "An outer header is followed by one Process Payload. Only optional .ivt, .text and .data "
                      "belong to the User Process Image. The User Process Heap and User Process Stack follow it. "
                      "process_heap is a global in process .data and its first_block points to an inner heap header.",
                      cells, bands, emphasized_heaps=("User Process Heap",) if emphasize_heap else ())
    diagram.arrow("data", "uA", "process_heap.first_block", lane=175)
    diagram.chain("u", len(payloads))
    if expanded and highlight_heap:
        diagram.highlight(first, last)
    return diagram


def process(slug, expanded=False):
    process_layout(slug, expanded).save()


def shared_memory_list():
    """Show the shared-memory registry in SRAM and as the same logical list."""
    entries = [
        ("Shared Memory Entry 1", "SharedMemoryEntry", "id = 2", "name · address",
         "reference_count = 2", "unlink_requested = false", "next"),
        ("Shared Memory Entry 2", "SharedMemoryEntry", "id = 1", "name · address",
         "reference_count = 1", "unlink_requested = false", "next = NULL"),
    ]
    fig = sram(
        "shared-list", "Global shared-memory list and entry names in SRAM",
        "Kernel .ivt, .text and .data form the Kernel Image. Only .data is outlined "
        "to mark the kernel globals containing the shared-memory list head. "
        "The global shared_memory_list_head in kernel .data points to Shared Memory Entry 1. "
        "SharedMemoryEntry.next links Entry 1 to Entry 2, whose next is NULL. Each entry and "
        "its copied name occupy separate Kernel Heap payloads. name points to the corresponding "
        "string, skipping allocator headers. Entry 1 has two attachments and Entry 2 has one. "
        "Both are named and unlink_requested is false. Below SRAM, the same two entry objects "
        "appear as a logical registry list with the same global head and next link. Dashed "
        "lines identify those objects across the two views. Allocator pointer arrows are omitted.",
        data=(".data · kernel globals", "shared_memory_list_head"),
        kernel_payloads=[entries[0], ("Entry 1 name string", '"shared-alpha"'),
                         entries[1], ("Entry 2 name string", '"shared-beta"')],
        data_width=300, kernel_payload_width=230, show_heap_links=False,
    )
    fig.arrow("data", "kpA", "shared_memory_list_head", lane=150, source_shift=-35)
    fig.arrow("kpA", "kpC", "next", lane=225, color=METADATA, source_shift=60,
              target_shift=60)
    for source, target in (("kpA", "kpB"), ("kpC", "kpD")):
        fig.arrow(source, target, "name", lane=275, color=ADDRESS, source_shift=-50)
    for key in ("data", "kpA", "kpC"):
        x, width = fig.positions[key]
        fig.parts.append(fig.rect(x, TOP, width, CELL_HEIGHT, "none", stroke=FOCUS,
                                  stroke_width=3))

    lower_y = fig.bottom + 250
    lower_height = 156
    root_x, root_width = LEFT, 350
    fig.parts.append(fig.rect(root_x, lower_y, root_width, lower_height, MUTED,
                              stroke=FOCUS, stroke_width=3))
    fig.parts.append(fig.text(root_x + root_width / 2, lower_y + 55,
                              "Kernel registry global", size=16, bold=True))
    fig.parts.append(fig.text(root_x + root_width / 2, lower_y + 85,
                              "shared_memory_list_head", size=14))
    node_width = 420
    node_xs = (650, 1400)
    for number, (source, x) in enumerate(zip(("kpA", "kpC"), node_xs), start=1):
        lines = (f"Shared Memory Entry {number}", "SharedMemoryEntry", f"id = {3 - number}",
                 f"reference_count = {3 - number}", "unlink_requested = false",
                 "next = NULL" if number == 2 else "next")
        fig.parts.append(
            f'<path d="M {fig.center(source)} {TOP + CELL_HEIGHT} L {x + node_width / 2} {lower_y}" '
            'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')
        fig.parts.append(fig.rect(x, lower_y, node_width, lower_height, ALLOCATED,
                                  stroke=FOCUS, stroke_width=3))
        labels = "".join(fig.text(x + node_width / 2, lower_y + 26 + index * 21,
                                  value, size=15, bold=index == 0)
                         for index, value in enumerate(lines))
        fig.parts.append(f'<a href="../../kernel/shared_memory.header#L8">{labels}</a>')
    root_center = root_x + root_width / 2
    first_center = node_xs[0] + node_width / 2
    lane = fig.bottom + 130
    fig.parts.append(fig.path(
        f"M {root_center} {lower_y} V {lane + 12} Q {root_center} {lane} "
        f"{root_center + 12} {lane} H {first_center - 12} Q {first_center} {lane} "
        f"{first_center} {lane + 12} V {lower_y - 3}", POINTER, arrow=True))
    fig.parts.append(fig.rect(410, lane - 13, 220, 18, "white"))
    fig.parts.append(fig.text(520, lane + 1, "shared_memory_list_head", size=14,
                              color=POINTER))
    edge_y = lower_y + 130
    first_right = node_xs[0] + node_width
    fig.parts.append(fig.path(f"M {first_right} {edge_y} H {node_xs[1] - 3}",
                              METADATA, arrow=True))
    fig.parts.append(fig.text((first_right + node_xs[1]) / 2, edge_y - 12,
                              "next", size=14, color=METADATA))
    fig.height = lower_y + lower_height + 85
    fig.save(notes=False, top=120, bottom=lower_y + lower_height + 20)


def shared_memory_payload_links():
    """Mirror the PCB payload view with two entries pointing to shared data."""
    mapping = sram(
        "shared-mappings", "From Shared Memory Entries to Shared Data Payloads in SRAM",
        "Kernel .ivt, .text and .data form the Kernel Image, followed by the Kernel Heap "
        "and Kernel Stack. The Process and Shared Data Heap follows the Kernel area. "
        "Each depicted heap has three Block Headers A, B and C. Kernel Heap Payloads A and C "
        "contain Shared Memory Entry 1 and Shared Memory Entry 2. Their address fields reach "
        "Shared Data Payloads A and C, immediately after their outer headers. Kernel Heap "
        "Payload B contains PCB 1, whose Process Payload B is shown for context. Only the "
        "two shared-data address pointers are drawn. Other allocations are omitted.",
        data=(".data · kernel globals", "global data"),
        kernel_payloads=[
            ("Payload A", "Shared Memory Entry 1", "SharedMemoryEntry", "address"),
            ("Payload B", "PCB 1", "ProcessControlBlock", "base_address"),
            ("Payload C", "Shared Memory Entry 2", "SharedMemoryEntry", "address"),
        ],
        outer_payloads=[("Shared Data Payload A", "shared cells"),
                        ("Process Payload B", "PCB 1's user process", "image · heap · stack"),
                        ("Shared Data Payload C", "shared cells")],
        data_width=310, kernel_payload_width=210, outer_payload_width=210,
        show_heap_links=False,
    )
    mapping.arrow("kpA", "opA", "address", lane=80, color=ADDRESS, source_shift=-55)
    mapping.arrow("kpC", "opC", "address", lane=150, color=ADDRESS, source_shift=-55)
    for key in ("kpA", "kpC"):
        x, width = mapping.positions[key]
        mapping.parts.append(mapping.rect(x, TOP, width, CELL_HEIGHT, "none", stroke=FOCUS,
                                          stroke_width=3))
    mapping.save(notes=False, top=50, bottom=mapping.bottom + 20)


def shared_memory_attachments():
    """Show the same PCB attachment lists in SRAM and as logical lists."""
    fig = sram(
        "shared-attachments", "Per-process shared-memory attachment lists within SRAM",
        "Kernel .ivt, .text and .data form the Kernel Image. Only .data is outlined "
        "to mark the kernel globals containing the shared-memory list head. "
        "Two PCBs, three SharedMemoryAttachment objects and two SharedMemoryEntry objects "
        "occupy seven separate Kernel Heap payloads. PCB 1 links Attachment 1 then Attachment 2, "
        "which reference Entry 1 and Entry 2. PCB 2 links Attachment 3, which also references "
        "Entry 1. Entry 1 has reference_count 2 and Entry 2 has reference_count 1. "
        "Both entries have unlink_requested false. The global shared_memory_list_head reaches "
        "Entry 1 and SharedMemoryEntry.next reaches Entry 2. Below SRAM, the same seven objects "
        "are repeated as two per-process attachment lists. Dashed lines identify the same objects "
        "across views, not additional allocations or stored pointers. The Process and Shared Data "
        "Heap is one box. Name strings, other kernel allocations, process-list pointers and "
        "payload address arrows are omitted.",
        data=(".data · kernel globals", "shared_memory_list_head"),
        kernel_payloads=[
            ("PCB 1", "ProcessControlBlock", "shared_memory_attachments"),
            ("PCB 2", "ProcessControlBlock", "shared_memory_attachments"),
            ("Shared Memory", "Attachment 1", "SharedMemoryAttachment", "entry", "next"),
            ("Shared Memory", "Attachment 2", "SharedMemoryAttachment", "entry", "next = NULL"),
            ("Shared Memory", "Attachment 3", "SharedMemoryAttachment", "entry", "next = NULL"),
            ("Shared Memory Entry 1", "SharedMemoryEntry", "id = 2", "address",
             "reference_count = 2", "unlink_requested = false", "next"),
            ("Shared Memory Entry 2", "SharedMemoryEntry", "id = 1", "address",
             "reference_count = 1", "unlink_requested = false", "next = NULL"),
        ],
        data_width=280, kernel_payload_width=220, kernel_header_width=60,
        show_heap_links=False,
    )
    fig.arrow("data", "kpF", "shared_memory_list_head", lane=90, source_shift=-40,
              target_shift=40, label_x=1020)
    fig.arrow("kpA", "kpC", "shared_memory_attachments", lane=165, color=METADATA,
              source_shift=-70, target_shift=-50, label_x=740)
    fig.arrow("kpB", "kpE", "shared_memory_attachments", lane=200, color=METADATA,
              source_shift=-70, label_x=1170)
    fig.arrow("kpC", "kpD", "next", lane=245, color=METADATA, source_shift=50,
              target_shift=50)
    fig.arrow("kpF", "kpG", "next", lane=245, color=METADATA, source_shift=65,
              target_shift=65)
    for source, target, lane, shift in (("kpC", "kpF", 565, -65),
                                      ("kpD", "kpG", 605, 0),
                                      ("kpE", "kpF", 645, 65)):
        fig.arrow(source, target, "entry", lane=lane, color=METADATA, below=True,
                  target_shift=shift)
    for key in ("data", "kpA", "kpB", "kpC", "kpD", "kpE", "kpF", "kpG"):
        x, width = fig.positions[key]
        fig.parts.append(fig.rect(x, TOP, width, CELL_HEIGHT, "none", stroke=FOCUS,
                                  stroke_width=3))

    first_y, second_y, node_height = 870, 1120, 130
    nodes = (
        ("kpA", LEFT, first_y, 250, ("PCB 1", "ProcessControlBlock", "shared_memory_attachments"),
         "kernel/process/process.header#L31"),
        ("kpB", LEFT, second_y, 250, ("PCB 2", "ProcessControlBlock", "shared_memory_attachments"),
         "kernel/process/process.header#L31"),
        ("kpC", 650, first_y, 300, ("Shared Memory Attachment 1", "SharedMemoryAttachment", "entry · next"),
         "kernel/shared_memory.header#L17"),
        ("kpD", 1300, first_y, 300, ("Shared Memory Attachment 2", "SharedMemoryAttachment", "entry · next = NULL"),
         "kernel/shared_memory.header#L17"),
        ("kpE", 650, second_y, 300, ("Shared Memory Attachment 3", "SharedMemoryAttachment", "entry · next = NULL"),
         "kernel/shared_memory.header#L17"),
        ("kpF", 2030, first_y, 320, ("Shared Memory Entry 1", "SharedMemoryEntry · id = 2",
                                   "reference_count = 2", "unlink_requested = false", "next"),
         "kernel/shared_memory.header#L8"),
        ("kpG", 2440, second_y, 320, ("Shared Memory Entry 2", "SharedMemoryEntry · id = 1",
                                    "reference_count = 1", "unlink_requested = false", "next = NULL"),
         "kernel/shared_memory.header#L8"),
    )
    # Identity guides go behind the logical objects and their pointer arrows.
    for source, x, y, width, _, _ in nodes:
        fig.parts.append(
            f'<path d="M {fig.center(source)} {fig.bottom} L {x + width / 2} {y}" '
            'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')
    for _, x, y, width, lines, link in nodes:
        fig.parts.append(fig.rect(x, y, width, node_height, ALLOCATED,
                                  stroke=FOCUS, stroke_width=3))
        first_line = y + (node_height - len(lines) * 22) / 2 + 17
        labels = "".join(fig.text(x + width / 2, first_line + index * 22, value,
                                  size=16, bold=index == 0, max_width=width - 12)
                         for index, value in enumerate(lines))
        fig.parts.append(f'<a href="../../{link}">{labels}</a>')

    def edge(path, label, x, y):
        fig.parts.append(fig.path(path, METADATA, arrow=True))
        label_width = len(label) * 9 + 16
        fig.parts.append(fig.rect(x - label_width / 2, y - 17, label_width, 23, "white"))
        fig.parts.append(fig.text(x, y, label, size=16, color=METADATA))

    for y in (first_y, second_y):
        edge(f"M {LEFT + 250} {y + 65} H 647", "shared_memory_attachments", 466, y + 52)
    edge(f"M 950 {first_y + 65} H 1297", "next", 1125, first_y + 52)
    edge(f"M 800 {first_y} V 800 H 2190 V {first_y - 3}", "entry", 1770, 794)
    edge(f"M 1450 {first_y + node_height} V 1060 H 1822 Q 1830 1048 1838 1060 H 2600 V {second_y - 3}",
         "entry", 2280, 1054)
    edge(f"M 950 {second_y + 65} H 1830 V {first_y + 65} H 2027",
         "entry", 1920, first_y + 52)
    fig.height = second_y + node_height + 32
    fig.save(notes=False, top=60)


def shared_memory_destruction():
    """Show one entry's lifetime as five snapshots, without cleanup branches."""
    panel_width, gap = 316, 28
    width, height = 2 * LEFT + 5 * panel_width + 4 * gap, 738
    parts = []

    def label(x, y, value, *, size=17, bold=False, link="", color="#172b3a",
              anchor="middle", max_width=None):
        text = Diagram.text(x, y, value, size=size, bold=bold, color=color,
                            anchor=anchor, max_width=max_width)
        parts.append(f'<a href="../../{link}">{text}</a>' if link else text)

    def box(x, y, w, h, fill=ALLOCATED):
        parts.append(Diagram.rect(x, y, w, h, fill, stroke=LINE, stroke_width=1.5))

    stages = (
        ("1  Open", "shm_open(name, size)", "Create Entry 1 and its data",
         "library/sys/mman/mman.picoc#L16", 0, False, ()),
        ("2  Map", "mmap(id) in each process", "Both receive the same address",
         "library/sys/mman/mman.picoc#L24", 2, False, (1, 2)),
        ("3  Unlink", "shm_unlink(name)", "Remove the name, keep the data",
         "library/sys/mman/mman.picoc#L28", 2, True, (1, 2)),
        ("4  Release one mapping", "remove_process(PCB 1)", "Release PCB 1's attachment",
         "kernel/process/process.picoc#L209", 1, True, (2,)),
        ("5  Release the last mapping", "remove_process(PCB 2)", "Release PCB 2's attachment",
         "kernel/process/process.picoc#L209", 0, True, ()),
    )
    for index, (title, function, effect, link, count, unlinked, pcbs) in enumerate(stages):
        x = LEFT + index * (panel_width + gap)
        center = x + panel_width / 2
        box(x, 90, panel_width, 96, HEADER)
        label(center, 116, title, bold=True, max_width=panel_width - 16)
        label(center, 143, function, link=link, max_width=panel_width - 16)
        label(center, 169, effect, size=16, max_width=panel_width - 16)
        if index < len(stages) - 1:
            # Horizontal arrows indicate time, vertical arrows are stored pointers.
            parts.append(Diagram.path(
                f"M {x + panel_width} 138 H {x + panel_width + gap - 3}",
                POINTER, arrow=True))

        if pcbs:
            attachment_width = 142
            for pcb in pcbs:
                ax = x + (10 if pcb == 1 else panel_width - attachment_width - 10)
                box(ax, 220, attachment_width, 54)
                label(ax + attachment_width / 2, 242, f"PCB {pcb}", bold=True,
                      link="kernel/process/process.header#L55")
                label(ax + attachment_width / 2, 264, "attachment", size=16,
                      link="kernel/shared_memory.header#L17")
                parts.append(Diagram.path(
                    f"M {ax + attachment_width / 2} 274 V 317", METADATA, arrow=True))
                label(ax + attachment_width / 2 + 8, 300, "entry", size=15,
                      anchor="start", color=METADATA,
                      link="kernel/shared_memory.header#L18")
        else:
            label(center, 245, "No attachments remain" if index == 4 else "No attachments yet",
                  size=18, bold=True)
            if index == 4:
                label(center, 276, "reference_count: 1 → 0", size=18,
                      link="kernel/shared_memory.header#L12")

        box(x, 320, panel_width, 182, MUTED if index == 4 else ALLOCATED)
        label(center, 347, "Entry 1 removed" if index == 4 else "Shared Memory Entry 1",
              bold=True, link="kernel/shared_memory.header#L8")
        if index == 4:
            label(center, 384, "Destroy the unlinked entry", size=19, bold=True)
            label(center, 417, "destroy_shared_memory_entry(entry)", size=15,
                  link="kernel/shared_memory.picoc#L69", max_width=panel_width - 12)
            label(center, 451, "PSDFree((int)entry->address)", size=16,
                  link="kernel/psdmalloc.picoc#L47", max_width=panel_width - 12)
            label(center, 480, "kfree(entry)", link="kernel/kmalloc.picoc#L38")
        else:
            label(center, 386, str(count), size=32, bold=True,
                  link="kernel/shared_memory.header#L12")
            label(center, 412, "reference_count", size=17,
                  link="kernel/shared_memory.header#L12")
            label(center, 449, 'name = NULL' if unlinked else 'name = "shared"',
                  link="kernel/shared_memory.header#L9")
            label(center, 479, "unlink_requested = " + ("true" if unlinked else "false"),
                  link="kernel/shared_memory.header#L13", max_width=panel_width - 16)
            parts.append(Diagram.path(f"M {center} 502 V 559", ADDRESS, arrow=True))
            label(center + 10, 538, "address", size=16, color=ADDRESS,
                  anchor="start", link="kernel/shared_memory.header#L11")

        box(x, 562, panel_width, 58, FREE if index == 4 else ALLOCATED)
        label(center, 586, "Freed cells" if index == 4 else "Shared Data Payload A", bold=True)
        label(center, 609, "Reusable by the heap" if index == 4 else "Same allocation stays alive",
              size=16, max_width=panel_width - 16)

    box(LEFT, 649, width - 2 * LEFT, 62, HEADER)
    label(width / 2, 674, "Free the entry and data only when BOTH conditions hold", size=21, bold=True)
    label(width / 2 - 22, 699, "unlink_requested == true", size=19, anchor="end",
          link="kernel/shared_memory.header#L13")
    label(width / 2, 699, "and", size=19)
    label(width / 2 + 22, 699, "reference_count == 0", size=19, anchor="start",
          link="kernel/shared_memory.header#L12")

    defs = "".join(
        f'<marker id="{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
        for color in (POINTER, METADATA, ADDRESS))
    description = (
        "Five snapshots of one shared-memory entry. shm_open creates Entry 1 and Shared Data Payload A "
        "with reference_count zero and unlink_requested false. mmap in the processes represented by "
        "PCB 1 and PCB 2 creates one attachment each, bringing reference_count to two. Both receive "
        "the same address. shm_unlink frees the name, sets name to NULL and unlink_requested to true, "
        "but leaves both attachments and the shared data alive. Final removal of PCB 1 releases its "
        "attachment and reduces reference_count to one. Final removal of PCB 2 reduces the count to "
        "zero, removes Entry 1 from the registry and frees the shared data and entry. Each PCB's "
        "shared_memory_attachments list owns its attachment, whose entry pointer reaches Entry 1. "
        "Horizontal arrows show time. Vertical arrows show entry and address pointers. This example "
        "tracks Entry 1 only, without additional mappings after unlink. Cleanup requires both "
        "unlink_requested true and reference_count zero, regardless of their order.")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
           '<title id="title">Shared-memory lifetime: open, map, unlink, release</title>\n'
           f'<desc id="desc">{escape(description)}</desc>\n<defs>{defs}</defs>\n'
           '<g font-family="DejaVu Sans, sans-serif">\n' + "\n".join(parts) + '\n</g></svg>\n')
    (OUTPUT / "memory-shared-destruction.svg").write_text(style_svg(svg, name="memory-shared-destruction"))


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
                    "the entire Kernel region. Dashed lines expand Process Payload A into its User Process Image, "
                    "User Process Heap and User Process Stack, excluding the outer header. All three heaps "
                    "contain four illustrative blocks linked by BlockHeader.next. Kernel payloads A, B and C "
                    "contain PCB 1 (struct ProcessControlBlock), its binary_path string (PCB-owned path copy), "
                    "and a Shared Memory Entry (struct SharedMemoryEntry); payload D is free. "
                    "Dashed lines connect the bottom corners of the teal Process Payload A box to its "
                    "expanded layout. Amber outlines and amber grouping bands mark "
                    "the Kernel Heap, Process and Shared Data Heap, and nested User Process Heap. "
                    "Process Payload C belongs to another process and outer Payload D is free. "
                    "Both kernel-managed heap descriptors and list roots "
                    "are globals in kernel .data; process_heap is in the process's own .data.",
                    data=(".data · global data", "kernel_heap", "process_shared_data_heap",
                          "process_list_head", "active_process", "shared_memory_list_head"),
                    kernel_payloads=[("Payload A", "PCB 1", "struct", "ProcessControlBlock"),
                                     ("Payload B", "binary_path string", "PCB-owned path copy"),
                                     ("Payload C", "Shared Memory Entry", "struct", "SharedMemoryEntry"),
                                     ("Free Payload D",)],
                    outer_payloads=[("Process Payload A", "one user process", "image · heap · stack"),
                                    ("Shared Data Payload B", "shared cells", "shared by processes"),
                                    ("Process Payload C", "another user process", "image · heap · stack"),
                                    ("Free Payload D",)],
                    data_width=280, kernel_payload_width=210, outer_payload_width=200,
                    emphasize_heaps=True)
    overview.arrow("data", "kA", "kernel_heap.first_block", lane=195, source_shift=-55)
    overview.arrow("data", "oA", "process_shared_data_heap.first_block", lane=135, source_shift=55)
    detail = process_layout("overview-process-payload", expanded=True,
                            include_outer_header=False, highlight_heap=False,
                            emphasize_heap=True)
    overview.expand("opA", detail, "ivt", "stack")
    overview.save(notes=False, top=90, bottom=overview.height - 53)
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

    shared_memory_list()
    shared_memory_payload_links()
    shared_memory_attachments()
    shared_memory_destruction()


if __name__ == "__main__":
    main()
