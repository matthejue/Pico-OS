"""Draw the startup sequence over adjacent EPROM, periphery and SRAM regions.

Memory bands are schematic, not proportional to address-space capacity.
Periphery has no execution lifeline. Keep the startup steps separate from the
memory layout, which is represented by the bands and participant placement.
"""

from html import escape
import json
from pathlib import Path

from diagram_style import ALLOCATED, FOCUS_FILL, FONT, FREE, INK, LINE, PANEL


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "documentation/images/startup-memory-sequence.svg"


def generate():
    sections = json.loads((ROOT / "kernel/kernel.sections").read_text())
    heap_start = sections["heap_start"]
    heap_end = heap_start + sections["heap_size"] - 1
    stack_end = sections["stack_start"]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="2460" height="866" '
        'viewBox="0 0 2460 866" role="img" aria-labelledby="title desc">',
        '<title id="title">Startup sequence across the memory map</title>',
        '<desc id="desc">Adjacent EPROM, periphery and SRAM bands show address order, '
        'with schematic widths. EPROM contains the bootloader. The periphery band '
        'contains UART and has no lifeline. SRAM is split into the kernel-reserved '
        'area, containing the kernel image, heap and stack, and the Process and '
        'Shared Data Heap, containing separate process payloads for init, shell '
        'and applications. Nine arrows follow loading and initialization from '
        'bootloader to kernel, init, shell and two applications. Dashed arrows '
        'show register setup and transfer of control.</desc>',
        '<defs>',
    ]
    for name, color in (("load", INK), ("control", INK)):
        parts.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                     'markerWidth="7" markerHeight="7" orient="auto">'
                     f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{color}"/></marker>')
    parts.extend(['</defs>', '<rect width="2460" height="866" fill="white"/>',
                  f'<g font-family="{FONT}" fill="{INK}">'])

    def rect(x, y, width, height, fill, *, opacity=1):
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                     f'fill="{fill}" fill-opacity="{opacity}"/>')

    def text(x, y, value, *, size=22, bold=False, link=""):
        element = (f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
                   f'font-weight="{"bold" if bold else "normal"}">{escape(value)}</text>')
        if link:
            element = f'<a href="../../{escape(link, quote=True)}">{element}</a>'
        parts.append(element)

    # One continuous memory map, with one shared line at each boundary.
    for x, width, color in ((20, 250, FOCUS_FILL), (270, 220, PANEL),
                             (490, 790, FREE), (1280, 1160, ALLOCATED)):
        rect(x, 14, width, 840, color, opacity=0.3)
    parts.append(f'<path d="M 20 14 H 2440 V 854 H 20 Z M 270 14 V 854 '
                 f'M 490 14 V 854 M 1280 70 V 854 M 490 70 H 2440" '
                 f'fill="none" stroke="{LINE}" stroke-width="1.5"/>')
    text(145, 43, "EPROM", size=28, bold=True)
    text(145, 64, "0x00000000", size=18)
    text(380, 43, "Periphery", size=24, bold=True)
    text(380, 64, "0x40000000", size=18)
    text(1465, 43, "SRAM", size=28, bold=True)
    text(1465, 64, "0x80000000", size=18)
    text(885, 101, "Kernel-reserved area", size=28, bold=True)
    text(885, 125, f"SRAM offsets 0–{stack_end}", size=18)
    text(1860, 101, "Process / Shared Data Heap", size=28, bold=True,
         link="kernel/psdmalloc.picoc#L10")
    text(1860, 125, f"From SRAM offset {stack_end + 1} · each process payload: image → user heap → stack",
         size=18)
    text(380, 185, "UART", size=24, bold=True, link="common/uart_protocol.picoc#L7")
    text(380, 211, "Memory-mapped I/O", size=18)

    actors = (
        (145, ("Bootloader", ".text and .data"), "boot/bootloader.picoc#L9"),
        (620, ("Kernel image", f"0–{heap_start - 1}", ".ivt: 0–4",
               f".text from {sections['codesegment_start']}",
               f".data from {sections['datasegment_start']}"), "kernel/kernel.picoc#L31"),
        (870, ("Kernel heap", f"{heap_start}–{heap_end}"), "kernel/kmalloc.picoc#L17"),
        (1120, ("Kernel stack", f"{heap_end + 1}–{stack_end}"), "kernel/memory_constants.header"),
        (1430, ("Init image", "libstart startup"), "system/init.picoc#L101"),
        (1720, ("Shell image", "libstart startup"), "user/shell.picoc#L1453"),
        (2010, ("Application A", "libstart startup"), "library/start/start.picoc#L13"),
        (2300, ("Application B", "libstart startup"), "library/start/start.picoc#L13"),
    )
    for x, labels, link in actors:
        rect(x - 110, 143, 220, 130, "white", opacity=0.65)
        parts.append(f'<rect x="{x - 110}" y="143" width="220" height="130" '
                     f'fill="none" stroke="{LINE}" stroke-width="1.5"/>')
        first_y = 208 - (len(labels) - 1) * 12 + 7
        for index, label in enumerate(labels):
            text(x, first_y + index * 24, label, size=22 if index == 0 else 18,
                 bold=index == 0, link=link if index == 0 else "")
        parts.append(f'<path d="M {x} 273 V 838" fill="none" stroke="{LINE}" '
                     'stroke-width="2" stroke-dasharray="6 6"/>')

    steps = (
        (145, 620, 318, ("boot_main: load kernel at SRAM offset 0",), "boot/bootloader.picoc#L41", False),
        (145, 1120, 382, ("start_loaded_kernel: SP / BAF ← stack_start",), "boot/bootloader.picoc#L21", True),
        (145, 620, 446, ("MOVE CS PC → kernel _start",), "boot/bootloader.picoc#L38", True),
        (620, 1120, 510, ("main: activate_kernel_stack_boundary",), "kernel/exception.picoc#L11", False),
        (620, 870, 574, ("main: init_kernel_heap", "→ heap_init_region"), "kernel/kmalloc.picoc#L17", False),
        (620, 1430, 638, ("load_process → init",), "kernel/kernel.picoc#L47", False),
        (1430, 1720, 702, ("init loads shell",), "system/init.picoc#L119", False),
        (1720, 2010, 766, ("shell loads application A",), "user/shell.picoc#L1213", False),
        (1720, 2300, 830, ("shell loads application B",), "user/shell.picoc#L1213", False),
    )
    for start, end, y, labels, link, dashed in steps:
        kind = "control" if dashed else "load"
        color = INK
        dash = ' stroke-dasharray="6 5"' if dashed else ""
        for index, label in enumerate(labels):
            text((start + end) / 2, y - 12 - (len(labels) - index - 1) * 23,
                 label, size=22, link=link)
        parts.append(f'<path d="M {start} {y} H {end - 3}" fill="none" '
                     f'stroke="{color}" stroke-width="3"{dash} marker-end="url(#{kind})"/>')
    parts.append('</g></svg>')
    OUTPUT.write_text("\n".join(parts) + "\n")


if __name__ == "__main__":
    generate()
