"""Generate the README's interrupt-controller and timer memory-layout diagrams."""

from html import escape
import json
from pathlib import Path


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

    def arrow(self, points, dashed=False):
        d = "M " + " L ".join(f"{x} {y}" for x, y in points)
        self.parts.append(f'<path d="{d}" fill="none" stroke="#27617b" stroke-width="2" '
                          f'{"stroke-dasharray=\"5 4\"" if dashed else ""} marker-end="url(#arrow)"/>')

    def save(self, name):
        self.parts.append("</g></svg>")
        OUTPUT.mkdir(exist_ok=True)
        (OUTPUT / name).write_text("\n".join(self.parts) + "\n")


def memory_map():
    f = Figure(1720, 800, 'Interrupt-controller initialization in the RETI memory map',
               'EPROM, periphery and SRAM in address order. Individual entries of two int[3] arrays in kernel .data write the six controller registers. The kernel image contains .ivt, .text and .data, followed by kernel heap and stack. Process and shared data occupy the remaining heap.')
    f.text(24, 38, 'Interrupt-controller initialization', 28, True)
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


def timer_memory():
    f = Figure(1640, 340, "Why the timer compares the saved PC with kernel DS",
               "The kernel .text lies before .data and its DS boundary. User process .text lies in the Process and Shared Data Heap above the kernel region.")
    f.text(24, 32, "Timer classification: kernel execution below kernel DS, user processes above it", 23, True)
    f.text(24, 66, "SRAM offsets increase left to right · widths are schematic", 18)
    f.box(24, 86, 1125, 170, "kernel")
    f.text(36, 113, "Kernel region", 20, True)
    f.box(40, 127, 660, 113, "free")
    f.text(52, 153, "Kernel image", 18, True)
    for x, w, label, color in [(52, 85, ".ivt\n0–4", "pc"),
                               (137, 279, f".text · kernel code\n5–{SECTIONS['datasegment_start']-1}", "active"),
                               (416, 269, f".data · kernel globals\n{SECTIONS['datasegment_start']}–{SECTIONS['heap_start']-1}", "saved")]:
        f.box(x, 164, w, 62, color, label, 17)
    hs = SECTIONS["heap_start"]
    he = hs + SECTIONS["heap_size"] - 1
    f.box(716, 127, 208, 113, "kernel", f"Kernel heap\n{hs}–{he}", 17)
    f.box(924, 127, 208, 113, "kernel", f"Kernel stack\n{he+1}–{K-BASE}", 17)
    f.box(1165, 86, 450, 170, "unused", f"Process and Shared Data Heap\n{PM-BASE}–262143\n\nProcess .text (normal user PCs)\nShared-data payloads", 18)
    f.arrow([(416, 296), (416, 228)], True)
    f.text(428, 283, f"kernel DS = {DS:#010x}", 18, True)
    f.text(24, 323, "saved PC < kernel DS → kernel execution", 19, True)
    f.text(910, 323, "saved PC > kernel DS → user process", 19, True)
    f.save("timer-pc-memory-layout.svg")


if __name__ == "__main__":
    memory_map()
    timer_memory()
