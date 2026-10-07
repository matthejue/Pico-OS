"""Generate the register destinations at the two README Section 11.1 jumps.

Run with Python 3 from any directory. Layout values come from the linked
section files and generated boot constants. Memory widths are illustrative.
"""

from html import escape
import json
from pathlib import Path
import re

from diagram_style import FONT, GREEN, INK, LINE, PANEL, STARTUP_MEMORY_COLORS, STARTUP_MEMORY_OPACITY


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "documentation/images"
SRAM_BASE = 0x80000000
EPROM = json.loads((ROOT / "boot/bootloader.sections").read_text())
KERNEL = json.loads((ROOT / "kernel/kernel.sections").read_text())
BOOT_CONSTANTS = (ROOT / "boot/memory_constants.header").read_text()
SRAM_LAST = int(re.search(r"^#define SRAM_MAX_ADDRESS (\d+)",
                          BOOT_CONSTANTS, re.MULTILINE)[1])


class Figure:
    def __init__(self, title, description):
        description += (" Addresses increase from left to right. SRAM labels are cell offsets. "
                        "Memory widths are illustrative.")
        self.parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="420" '
            'viewBox="0 0 1800 420" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            '<defs><marker id="address" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{GREEN}"/></marker></defs>',
            '<rect width="1800" height="420" fill="white"/>',
            f'<g font-family="{FONT}" fill="{INK}">',
        ]

    def text(self, x, y, value, size=18, bold=False, anchor="start", link="", color=INK):
        element = (f'<text x="{x}" y="{y}" font-size="{size}" '
                   f'font-weight="{"bold" if bold else "normal"}" '
                   f'text-anchor="{anchor}" fill="{color}">{escape(str(value))}</text>')
        if link:
            element = f'<a href="../../{escape(link, quote=True)}">{element}</a>'
        self.parts.append(element)

    def rect(self, x, y, width, height, fill=PANEL, outline=False, *, opacity=1):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                          f'fill="{fill}" stroke="{LINE if outline else "none"}" '
                          f'stroke-width="1.5" fill-opacity="{opacity}"/>')

    def path(self, d, color=LINE, arrow=False, dashed=False):
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" '
                          f'stroke-width="{2 if arrow else 1.5}" '
                          f'{"stroke-dasharray=\"5 4\"" if dashed else ""}'
                          f'{" marker-end=\"url(#address)\"" if arrow else ""}/>')

    def pointer(self, target, y, label, formula, *, right=True, link=""):
        self.path(f"M {target} {y - 20} V 178", GREEN, arrow=True, dashed=True)
        x = target + 14 if right else target - 14
        anchor = "start" if right else "end"
        self.text(x, y, label, 21, True, anchor, color=GREEN)
        self.text(x, y + 25, formula, 17, anchor=anchor, link=link)

    def memory_map(self, kernel=False):
        # Match the overview's storage-domain colors across both boot stages.
        # The SRAM colors show the kernel layout even before it is loaded.
        for x, width, region in ((32, 500, "eprom"), (532, 160, "periphery"),
                                  (692, 818, "kernel_sram"),
                                  (1510, 258, "process_shared_sram")):
            self.rect(x, 144, width, 198, STARTUP_MEMORY_COLORS[region],
                      opacity=STARTUP_MEMORY_OPACITY)
        # Adjacent address spaces share one outline and one divider.
        for x, width, label in ((32, 500, "EPROM · 0x00000000"),
                                (532, 160, "Periphery"),
                                (692, 1076, "SRAM · 0x80000000")):
            self.rect(x, 144, width, 36, "none")
            self.text(x + width / 2, 169, label, 19, True, "middle")
        ds = EPROM["datasegment_start"]
        data_end = EPROM["heap_start"] - 1
        cells = [
            (32, 138, ("_start()", "offset 0"), "boot/bootloader.picoc#L9"),
            (170, 212, ("boot_main()", "entry in .text"), "boot/bootloader.picoc#L41"),
            (382, 150, ("Bootloader data", f"{ds}–{data_end}"), "boot/bootloader.sections"),
            (532, 160, ("Memory-mapped", "I/O", "0x40000000"), ""),
        ]
        if kernel:
            cs, ds = KERNEL["codesegment_start"], KERNEL["datasegment_start"]
            hs = KERNEL["heap_start"]
            he = hs + KERNEL["heap_size"] - 1
            ss = KERNEL["stack_start"]
            cells += [
                (692, 68, (".ivt", f"0–{cs - 1}"), "kernel/kernel.sections"),
                (760, 220, (".text", "generated _start", f"{cs}–{ds - 1}"), "kernel/kernel.reti#L7"),
                (980, 200, (".data", "kernel globals", f"{ds}–{hs - 1}"), "kernel/kernel.sections"),
                (1180, 170, ("Kernel Heap", f"{hs}–{he}"), "kernel/kmalloc.picoc#L7"),
                (1350, 128, ("Kernel Stack", "grows ←", f"{he + 1}–{ss}"), "kernel/memory_constants.header#L8"),
                (1478, 32, (), ""),
                (1510, 258, ("Process and", "Shared Data Heap", f"{ss + 1}–{SRAM_LAST}"), "kernel/psdmalloc.picoc#L7"),
            ]
        else:
            cells += [
                (692, 1044, ("Available SRAM", "Temporary bootloader stack grows ←",
                              f"SRAM offsets 0–{SRAM_LAST}"), "boot/memory_constants.header#L3"),
                (1736, 32, (), ""),
            ]
        for x, width, lines, link in cells:
            self.rect(x, 180, width, 130, "none")
            for index, line in enumerate(lines):
                self.text(x + width / 2, 247 + (index - (len(lines) - 1) / 2) * 24,
                          line, 16, index == 0 or (kernel and x == 1510 and index == 1),
                          "middle", link)
            if x not in (32, 532, 692):
                self.path(f"M {x} 180 V 310")
        bands = [(32, 350, ".text · bootloader code"), (382, 150, ".data"),
                 (532, 160, ""), (692, 488, "Kernel Image"),
                 (1180, 170, "Kernel Heap"), (1350, 160, "Kernel Stack"),
                 (1510, 258, "Process and Shared Data Heap")] if kernel else [
                     (32, 350, ".text · bootloader code"), (382, 150, ".data"),
                     (532, 160, ""), (692, 1076, "Temporary stack starts at the highest SRAM cell")]
        for x, width, label in bands:
            self.rect(x, 310, width, 32, "none")
            self.text(x + width / 2, 332, label, 15, True, "middle")
            if x not in (32, 532, 692):
                self.path(f"M {x} 310 V 342")
        self.path("M 32 180 H 1768 M 32 310 H 1768 M 532 144 V 342 M 692 144 V 342")
        self.rect(32, 144, 1736, 198, "none", outline=True)

    def save(self, name):
        OUTPUT.mkdir(exist_ok=True)
        (OUTPUT / name).write_text("\n".join(self.parts + ["</g></svg>"]) + "\n")


def boot_entry():
    figure = Figure("Register destinations after bootloader _start",
                    "Immediately after MOVE ACC PC, before boot_main creates its stack frame. "
                    "CS points to EPROM offset zero, ACC and PC to boot_main in bootloader .text, "
                    "DS to bootloader .data, and SP and BAF to the highest SRAM cell. "
                    "Green dashed arrows show absolute register addresses. The narrow final "
                    "SRAM cell is the initial temporary stack location.")
    figure.memory_map()
    figure.pointer(32, 48, "CS = 0x00000000", "EPROM base")
    figure.pointer(170, 104, "ACC = PC", "CS + boot_main", link="boot/bootloader.picoc#L41")
    figure.pointer(382, 48, f"DS = {EPROM['datasegment_start']:#010x}",
                   "CS + eprom_ds_start", link="boot/memory_constants.header#L2")
    figure.pointer(1752, 48, f"SP = BAF = {SRAM_BASE + SRAM_LAST:#010x}",
                   f"SRAM base + {SRAM_LAST}", right=False, link="boot/memory_constants.header#L3")
    figure.text(32, 387, "At the jump to boot_main(), before its stack frame changes SP and BAF.",
                18, link="boot/bootloader.picoc#L41")
    figure.save("boot-eprom-registers.svg")


def kernel_handoff():
    cs, ds, ss = (KERNEL[key] for key in ("codesegment_start", "datasegment_start", "stack_start"))
    figure = Figure("Register destinations after start_loaded_kernel",
                    "Immediately after MOVE CS PC, before generated kernel startup runs. "
                    "CS and PC point to kernel .text, DS to kernel .data, and SP and BAF "
                    "to the highest kernel stack cell. The narrow cell at the end of the "
                    "Kernel Stack marks stack_start. ACC, IN1 and IN2 retain the code, "
                    "data and stack offsets, not absolute addresses. The old temporary "
                    "stack is in the later Process and Shared Data Heap area.")
    figure.memory_map(kernel=True)
    figure.pointer(760, 48, f"CS = PC = {SRAM_BASE + cs:#010x}", "SRAM base + code_start",
                   link="boot/bootloader.picoc#L42")
    figure.pointer(980, 104, f"DS = {SRAM_BASE + ds:#010x}", "SRAM base + data_start",
                   link="boot/bootloader.picoc#L43")
    figure.pointer(1494, 48, f"SP = BAF = {SRAM_BASE + ss:#010x}", "SRAM base + stack_start",
                   right=False, link="boot/bootloader.picoc#L44")
    for x, label, link in (
        (692, f"ACC = code_start = {cs}", "boot/bootloader.picoc#L42"),
        (1044, f"IN1 = data_start = {ds}", "boot/bootloader.picoc#L43"),
        (1396, f"IN2 = stack_start = {ss}", "boot/bootloader.picoc#L44"),
    ):
        figure.rect(x, 365, 336, 36, PANEL, outline=True)
        figure.text(x + 168, 389, label, 17, anchor="middle", link=link, color=LINE)
    figure.text(32, 389, "Offsets retained in registers:", 18)
    figure.save("boot-kernel-registers.svg")


if __name__ == "__main__":
    boot_entry()
    kernel_handoff()
