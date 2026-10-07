"""Generate the stack-boundary memory diagram in README section 2.8.

The boundary is the last heap cell, not the first stack cell. SP points to
the next free cell below the occupied stack. The emulator rejects an
instruction that decreases SP below a nonzero boundary, but allows equality.
"""

from html import escape
from pathlib import Path

from diagram_style import (
    ALLOCATED, AMBER, FONT, FREE, GREEN, HEADER, INK, LINE, PANEL, style_svg,
)
from generate_memory_layout_diagrams import Diagram


OUTPUT = Path(__file__).parent / "images" / "stack-heap-boundary.svg"


def generate():
    parts = []

    def label(x, y, value, *, size=20, bold=False, anchor="middle", link="", color=INK):
        text = Diagram.text(x, y, value, size=size, bold=bold, anchor=anchor, color=color)
        if link:
            text = f'<a href="../../{escape(link, quote=True)}">{text}</a>'
        parts.append(text)

    def box(x, y, width, height, fill=PANEL, *, stroke=LINE, thickness=1.5):
        parts.append(Diagram.rect(x, y, width, height, fill, stroke, thickness))

    def arrow(path, *, color=GREEN, dashed=False):
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" '
                     f'stroke-width="2"{dash} marker-end="url(#{color[1:]})"/>')

    # The PCB supplies the boundary value to the separate periphery register.
    box(32, 24, 510, 110, HEADER)
    label(287, 54, "process_stack_boundary(PCB 1)", bold=True,
          link="kernel/exception.picoc#L18")
    label(52, 88, "B =", anchor="start")
    label(92, 88, "base_address", anchor="start", link="kernel/process/process.header#L34")
    label(230, 88, "+", anchor="start")
    label(253, 88, "heap_start", anchor="start", link="kernel/process/process.header#L36")
    label(370, 88, "+", anchor="start")
    label(92, 117, "heap_size", anchor="start", link="kernel/process/process.header#L37")
    label(203, 117, "− 1", anchor="start")

    box(610, 24, 470, 110, HEADER)
    label(845, 57, "STACK_HEAP_BOUNDARY_REGISTER", bold=True,
          link="kernel/exception.header#L5")
    label(845, 89, "B", size=26, bold=True, color=AMBER)
    label(845, 117, "Periphery register 10", size=18)
    arrow("M 542 79 H 610", color=LINE)
    arrow("M 845 134 V 160 H 512 V 250", color=AMBER)
    label(492, 191, "Boundary B", bold=True, anchor="end", color=AMBER)

    # SP is a CPU register containing an address, not a cell of stack memory.
    box(1110, 24, 338, 110, FREE)
    label(1279, 57, "CPU register SP", bold=True)
    label(1279, 95, "B + 1", size=26, bold=True, color=GREEN)
    arrow("M 1279 134 V 177 H 662 V 250")

    label(32, 228, "Lower addresses", anchor="start")
    label(1448, 228, "Higher addresses", anchor="end")
    label(995, 207, "Stack grows", bold=True)
    arrow("M 1175 224 H 815")

    cells = (
        (32, 300, ALLOCATED, ("…", "Heap cells")),
        (332, 120, ALLOCATED, ("B − 1",)),
        (452, 120, ALLOCATED, ("B",)),
        (572, 180, FREE, ("B + 1", "Next free cell")),
        (752, 180, ALLOCATED, ("B + 2", "Occupied")),
        (932, 180, ALLOCATED, ("B + 3", "Occupied")),
        (1112, 336, ALLOCATED, ("…", "Occupied stack cells")),
    )
    for x, width, fill, lines in cells:
        box(x, 250, width, 106, fill)
        for index, line in enumerate(lines):
            label(x + width / 2, 297 + (index - (len(lines) - 1) / 2) * 29,
                  line, bold=index == 0)
    box(452, 250, 120, 106, "none", stroke=AMBER, thickness=3)
    box(32, 356, 540, 34, HEADER)
    label(302, 380, "User Process Heap", bold=True)
    box(572, 356, 876, 34, PANEL)
    label(1010, 380, "User Process Stack", bold=True)

    # A dashed arrow denotes a rejected proposed address, never an updated SP.
    arrow("M 662 390 V 420 H 392 V 390", color=AMBER, dashed=True)
    label(527, 453, "SUBI SP 2", bold=True, color=AMBER)
    label(392, 490, "Proposed SP = B − 1", color=AMBER)
    label(392, 518, "Rejected by CPU", bold=True, color=AMBER)
    label(392, 557, "SP = B is still allowed", size=18)

    box(780, 432, 668, 132, HEADER)
    label(1114, 466, "CPU check: new SP < B → stack overflow", bold=True)
    label(1114, 502, "CPU_EXCEPTION_CAUSE_REGISTER = 2", size=19,
          link="kernel/exception.header#L6")
    arrow("M 1114 510 V 527", color=LINE)
    label(1114, 549, "cpu_exception_interrupt()", bold=True,
          link="interrupt_service_routines/os_isrs.picoc#L161")

    description = (
        "Process stack protection in SRAM. Addresses increase from left to right. "
        "PCB 1 supplies base_address, heap_start and heap_size to process_stack_boundary, "
        "which computes B as the last heap cell. Periphery register 10 contains B and "
        "points to that cell. CPU register SP contains B + 1 and points to the next free "
        "stack cell, immediately below occupied cells starting at B + 2. The stack grows "
        "toward lower addresses. SUBI SP 2 proposes B - 1, below B, so the emulator rejects "
        "the instruction's SP update, records stack-overflow cause 2 in periphery register "
        "11 and enters cpu_exception_interrupt. The dashed arrow is a proposed address, "
        "not an updated SP. SP equal to B is allowed. Exception entry subsequently changes "
        "SP to save its PC, then the handler resets the kernel stack. A zero boundary "
        "disables protection. Memory widths are illustrative."
    )
    defs = "".join(
        f'<marker id="{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
        for color in (GREEN, AMBER, LINE)
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1480" height="590" '
        'viewBox="0 0 1480 590" role="img" aria-labelledby="title desc">'
        '<title id="title">Stack pointer and heap boundary protection</title>'
        f'<desc id="desc">{escape(description)}</desc><defs>{defs}</defs>'
        f'<g font-family="{FONT}">' + "".join(parts) + '</g></svg>\n'
    )
    OUTPUT.write_text(style_svg(svg, name="stack-heap-boundary"))


if __name__ == "__main__":
    generate()
