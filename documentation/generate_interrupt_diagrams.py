"""Generate the README's interrupt-controller and context-classification diagrams."""

from html import escape
import json
from pathlib import Path

from diagram_style import style_svg
from generate_memory_layout_diagrams import ALLOCATED, HEADER, MUTED, Cell, Diagram, TOP


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "documentation/images"
SECTIONS = json.loads((ROOT / "kernel/kernel.sections").read_text())
BASE = 0x80000000
CS = BASE + SECTIONS["codesegment_start"]
DS = BASE + SECTIONS["datasegment_start"]
K = BASE + SECTIONS["stack_start"]
PM = K + 1
COLORS = {"saved": "#fff1c7", "pc": "#eadffa", "active": "#dceefa",
          "free": "#ffffff", "unused": "#f1f3f5", "kernel": "#e6efe5"}


class Figure:
    def __init__(self, width, height, title, description):
        self.width = width
        self.height = height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                      f'height="{height}" viewBox="0 0 {width} {height}" '
                      'role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title>',
                      f'<desc id="desc">{escape(description)}</desc>',
                      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" '
                      'refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                      '<path d="M 0 0 L 10 5 L 0 10 z" fill="#27617b"/></marker></defs>',
                      '<rect width="100%" height="100%" fill="white"/>',
                      '<g font-family="DejaVu Sans, sans-serif" fill="#192c38">']

    def text(self, x, y, lines, size=18, bold=False, anchor="start"):
        for index, line in enumerate(lines.split("\n")):
            self.parts.append(f'<text x="{x}" y="{y + index * (size + 5)}" '
                              f'font-size="{size}" font-weight="{"bold" if bold else "normal"}" '
                              f'text-anchor="{anchor}">{escape(line)}</text>')

    def box(self, x, y, width, height, fill="free", label=None, size=18):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                          f'fill="{COLORS.get(fill, fill)}" stroke="#526472" stroke-width="1.5"/>')
        if label:
            self.text(x + 12, y + 26, label, size)

    def arrow(self, points, dashed=False, *, color="#27617b", marker="arrow"):
        d = "M " + " L ".join(f"{x} {y}" for x, y in points)
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
                          f'{"stroke-dasharray=\"5 4\"" if dashed else ""} marker-end="url(#{marker})"/>')

    def save(self, name):
        self.parts.append("</g></svg>")
        OUTPUT.mkdir(exist_ok=True)
        (OUTPUT / name).write_text(style_svg("\n".join(self.parts) + "\n"))


def memory_map():
    f = Figure(1720, 800, 'Interrupt-controller initialization in the RETI memory map',
               'EPROM, periphery and SRAM in address order. Individual entries of two int[3] arrays in kernel .data write the six controller registers. The kernel image contains .ivt, .text and .data, followed by kernel heap and stack. Process and shared data occupy the remaining heap.')
    f.text(1455, 38, 'Addresses →', 21)
    # Context stays unfilled. Only the cells taking part in the writes use color.
    f.box(24, 90, 205, 690, 'free')
    f.text(36, 125, 'EPROM', 23, True)
    f.text(36, 160, '0x00000000', 18)
    f.text(36, 215, 'Bootloader', 21)
    f.box(249, 90, 540, 690, 'free')
    f.text(263, 125, 'Periphery', 23, True)
    f.text(263, 160, '0x40000000', 18)
    f.text(267, 215, '…', 22)
    f.text(267, 267, 'Controller registers', 22, True)
    f.text(275, 329, 'ISR mapping', 21, True)
    f.text(275, 493, 'Priority', 21, True)
    f.text(267, 674, '…', 22)
    f.box(910, 90, 786, 690, 'free')
    f.text(924, 125, 'SRAM', 23, True)
    f.text(1470, 125, '0x80000000', 18)
    f.box(924, 143, 758, 580, 'free')
    f.text(938, 174, 'Kernel', 22, True)
    f.box(936, 188, 734, 460, 'free')
    f.text(950, 216, 'Kernel image', 21, True)
    f.box(950, 229, 240, 42, 'free', '.ivt', 21)
    f.box(1190, 229, 466, 42, 'free', '.text', 21)
    f.box(950, 281, 706, 353, 'free')
    f.text(964, 308, '.data', 21, True)
    f.text(964, 329, 'interrupt_device_isrs', 19)
    f.text(964, 493, 'interrupt_device_priorities', 19)
    rows = []
    for i in range(6):
        index = i % 3
        value = [1,4,2,1,1,2][i]
        top = (343 if i < 3 else 507) + index * 40
        fill = 'active' if i < 3 else 'saved'
        device = ['Timer', 'DMA', 'UART'][index]
        f.box(264, top, 510, 40, fill)
        f.text(275, top+28, f'0x4000000{i+3:x}', 21)
        f.text(482, top+28, device, 21)
        f.text(744, top+28, str(value), 23, True, anchor='end')
        f.box(964, top, 678, 40, fill)
        f.text(980, top+28, f'[{index}] = {value}', 23)
        rows.append(top + 20)
    f.box(936, 665, 367, 42, 'free', 'Kernel heap', 21)
    f.box(1303, 665, 367, 42, 'free', 'Kernel stack', 21)
    f.box(924, 737, 758, 32, 'free', 'Process and Shared Data Heap', 20)
    # Neutral arrows keep the emphasis on the matching source/destination cells.
    f.parts.append('<defs><marker id="write-arrow" viewBox="0 0 10 10" refX="9" '
                   'refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                   '<path d="M 0 0 L 10 5 L 0 10 z" fill="#526472"/></marker></defs>')
    for y in rows:
        f.parts.append(f'<path d="M 964 {y} L 776 {y}" fill="none" '
                       'stroke="#526472" stroke-width="2" marker-end="url(#write-arrow)"/>')
    f.save('interrupt-controller-initialization.svg')


def context_memory_cells():
    """Keep kernel regions identical in the timer and exception SRAM rows."""
    hs = SECTIONS["heap_start"]
    he = hs + SECTIONS["heap_size"] - 1
    return [
        Cell("ivt", 85, (".ivt", "0–4"), MUTED),
        Cell("text", 279, (".text · kernel code", f"5–{SECTIONS['datasegment_start']-1}"), ALLOCATED),
        Cell("data", 269, (".data · kernel globals", f"{SECTIONS['datasegment_start']}–{hs-1}"), MUTED),
        Cell("heap", 208, ("Kernel objects", f"{hs}–{he}"), MUTED),
        Cell("stack", 208, ("grows ←", f"{he+1}–{K-BASE}"), MUTED, bold_lines=0),
    ]


def context_memory_bands(outer_first="outer"):
    return [
        [("ivt", "data", "Kernel Image", MUTED),
         ("heap", "heap", "Kernel Heap", MUTED),
         ("stack", "stack", "Kernel Stack", MUTED),
         (outer_first, "outer", "Process and Shared Data Heap", MUTED)],
        [("ivt", "stack", "Kernel", MUTED),
         (outer_first, "outer", "After the Kernel region", MUTED)],
    ]


def timer_memory():
    description = (
        "Continuous SRAM in increasing offset order, with illustrative widths. "
        "Adjacent .ivt, .text and .data sections form the Kernel Image, followed "
        "immediately by the Kernel Heap, Kernel Stack and Process and Shared Data Heap. "
        "Kernel DS points to the start of .data. Kernel code is below this boundary "
        "and user-process code is above it. Grouping bands match the Section 3 memory layouts."
    )
    cells = context_memory_cells() + [
        Cell("outer", 466, ("Process .text (normal user PCs)", "Shared Data Payloads",
                            f"{PM-BASE}–262143"), MUTED),
    ]
    layout = Diagram("timer-pc", "Why the timer compares the saved PC with kernel DS",
                     description, cells, context_memory_bands())
    f = Figure(layout.right + 32, 360, layout.title, description)
    # Reuse Section 3's cells and shared dividers without its heading or legend.
    f.parts.append(f'<g transform="translate(0 {80-TOP})">')
    f.parts.extend(layout.parts)
    f.parts.append('</g>')
    ds_x, _ = layout.positions["data"]
    f.arrow([(ds_x, 24), (ds_x, 78)], True)
    f.text(ds_x + 12, 48, f"kernel DS = {DS:#010x}", 18, True)
    f.text(32, 335, "saved PC ≤ kernel DS → kernel branch", 19, True)
    f.text(layout.positions["outer"][0], 335, "saved PC > kernel DS → process branch", 19, True)
    f.save("timer-pc-memory-layout.svg")


def exception_cs():
    description = (
        "Continuous SRAM in increasing offset order with the same kernel cells and "
        "grouping bands as the timer and Section 3 memory layouts. Kernel CS points "
        "to kernel .text. ProcessControlBlock.activation.cs points to .text inside "
        "Process Payload A, following its outer Block Header A. This example omits "
        "the optional process .ivt. Other process and shared-data blocks are omitted. "
        "Exception entry preserves interrupted CS in BAF, installs kernel CS, and "
        "pushes their difference for handle_cpu_exception. A gray value-transfer "
        "arrow points directly to diff, the abbreviated interrupted_kernel_cs_difference "
        "parameter. Zero selects kernel panic and a nonzero value selects process termination."
    )
    cells = context_memory_cells() + [
        Cell("outer_header", 80, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        Cell("process_text", 180, ("Process Payload A", ".text · process code"), ALLOCATED,
             "kernel/process/process.header#L27"),
        Cell("process_rest", 150, (".data", "User Process Heap", "User Process Stack"), ALLOCATED,
             bold_lines=0),
        Cell("outer", 56, ("…",), MUTED, bold_lines=0),
    ]
    layout = Diagram("exception-cs", "How exception entry compares interrupted CS with kernel CS",
                     description, cells, context_memory_bands("outer_header"))
    f = Figure(layout.right + 32, 518, layout.title, description)
    for marker, color in (("address-arrow", "#26715b"), ("value-arrow", "#526472")):
        f.parts.append(f'<defs><marker id="{marker}" viewBox="0 0 10 10" refX="9" '
                       'refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                       f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker></defs>')
    f.parts.append(f'<g transform="translate(0 {80-TOP})">')
    f.parts.extend(layout.parts)
    f.parts.append('</g>')
    kernel_cs_x, _ = layout.positions["text"]
    process_cs_x, _ = layout.positions["process_text"]
    for x in (kernel_cs_x, process_cs_x):
        f.arrow([(x, 24), (x, 78)], True, color="#26715b", marker="address-arrow")
    f.text(kernel_cs_x + 12, 48, f"kernel CS = {CS:#010x}", 18, True)
    f.text(process_cs_x + 12, 48, "process->activation.cs", 18, True)
    f.text(32, 327, "SRAM offsets increase →   ·   Widths are illustrative", 15)

    # Value transfers use gray, matching the shared README diagram convention.
    y = 360
    step_width = 340
    step_gap = 36
    step_x = tuple(32 + i * (step_width + step_gap) for i in range(4))
    for x in step_x[:3]:
        f.box(x, y, step_width, 134, "unused")
        f.arrow([(x + step_width + 2, y + 47), (x + step_width + step_gap - 2, y + 47)],
                color="#526472", marker="value-arrow")
    f.text(step_x[0] + 12, y + 30, "A · MOVE BAF ACC", 20, True)
    f.text(step_x[0] + 12, y + 63, "ACC = interrupted CS", 18)
    f.text(step_x[1] + 12, y + 30, "B · SUB ACC CS", 20, True)
    f.text(step_x[1] + 12, y + 63, "ACC = interrupted CS − kernel CS", 18)
    f.text(step_x[2] + 12, y + 30, "C · PUSH ACC", 20, True)
    f.text(step_x[2] + 12, y + 63, "Kernel-stack argument = difference", 17)
    handler_x = step_x[3]
    f.box(handler_x, y, layout.right - handler_x, 134, "free")
    # Anchor the parameter independently of the rendered function-name width.
    diff_x = layout.right - 58
    f.text(diff_x - 18, y + 30, "D · handle_cpu_exception(", 20, True, anchor="end")
    f.text(diff_x, y + 30, "diff", 20, True, anchor="middle")
    f.text(diff_x + 18, y + 30, ")", 20, True)
    f.text(handler_x + 12, y + 63, "pushed ACC", 17)
    f.arrow([(handler_x + 120, y + 57), (diff_x, y + 57), (diff_x, y + 37)],
            color="#526472", marker="value-arrow")
    f.text(handler_x + 12, y + 90, "diff = 0 → kernel panic\ndiff ≠ 0 → process termination", 17)
    f.save("exception-cs-comparison.svg")


if __name__ == "__main__":
    memory_map()
    timer_memory()
    exception_cs()
