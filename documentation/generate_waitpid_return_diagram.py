"""Generate the wide waitpid return-path diagram for README 10.1.3.

Run with Python 3. The SVG can be used directly in presentation slides.
Detailed syscall entry and queue mechanics belong in the README prose.
"""

from html import escape
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent / "images" / "waitpid-return-paths.svg"
INK = "#192c38"
LINE = "#526472"
PCB = "kernel/process/process.header"


def generate():
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1680" height="560" '
        'viewBox="0 0 1680 560" role="img" aria-labelledby="title desc">',
        '<title id="title">Immediate and blocking waitpid return paths</title>',
        '<desc id="desc">The kernel wait has two paths. When no wait is needed, '
        'it writes through request.status and restores the caller. Otherwise it '
        'retains request.status in the parent PCB waiting_status_ptr, sets the '
        'parent state to BLOCKED, and saves activation while other processes run. '
        'Child stopping or termination writes through waiting_status_ptr and '
        'makes the parent state READY. When selected, the dispatcher restores '
        'activation. Both paths use RTI to resume after INT 0 in the userspace '
        'helper, and waitpid returns the stack-local status. The waiting path '
        'assumes the parent is not itself stopped.</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{LINE}"/></marker></defs>',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<g font-family="DejaVu Sans, sans-serif" fill="{INK}">',
    ]

    def text(x, y, value, size=24, *, bold=False, link=""):
        element = (f'<text x="{x}" y="{y}" text-anchor="middle" '
                   f'font-size="{size}" font-weight="{"bold" if bold else "normal"}">'
                   f'{escape(value)}</text>')
        if link:
            element = f'<a href="../../{escape(link, quote=True)}">{element}</a>'
        parts.append(element)

    def box(x, y, width, height, fill):
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                     f'fill="{fill}" stroke="{LINE}" stroke-width="2"/>')

    def arrow(path):
        parts.append(f'<path d="{path}" fill="none" stroke="{LINE}" '
                     'stroke-width="3" marker-end="url(#arrow)"/>')

    box(24, 210, 240, 110, "#e6efe5")
    text(144, 273, "Kernel wait", 30, bold=True,
         link="kernel/process/process.picoc#L348")

    box(420, 40, 790, 110, "#e6efe5")
    text(815, 85, "Write status", 30, bold=True)
    text(815, 124, "*request.status", link="common/syscall.header#L63")
    arrow("M 264 265 H 300 V 95 H 410")
    text(430, 192, "No wait needed")

    box(330, 340, 450, 150, "#fff1c7")
    text(555, 398, "Save activation", 30, bold=True,
         link=f"{PCB}#L40")
    text(555, 448, "state = BLOCKED", link=f"{PCB}#L33")
    arrow("M 264 265 H 300 V 415 H 320")
    text(392, 310, "Wait required")

    box(860, 340, 350, 150, "#dceefa")
    text(1035, 380, "Write status", 30, bold=True)
    text(1035, 424, "*waiting_status_ptr", link=f"{PCB}#L44")
    text(1035, 463, "state = READY", link=f"{PCB}#L33")
    arrow("M 780 415 H 850")
    text(820, 310, "Child stops / terminates")

    box(1350, 210, 300, 110, "#eadffa")
    text(1500, 255, "RTI", 32, bold=True,
         link="kernel/dispatcher.picoc#L40")
    text(1500, 295, "waitpid() returns status", 23,
         link="library/sys/wait/wait.picoc#L14")
    arrow("M 1210 95 H 1500 V 200")
    text(1340, 178, "Restore caller", link="interrupt_service_routines/os_isrs.picoc#L148")
    arrow("M 1210 415 H 1500 V 330")
    text(1430, 466, "Restore activation", link="kernel/dispatcher.picoc#L21")
    text(1430, 505, "when parent is selected", 22,
         link="kernel/dispatcher.picoc#L55")

    parts.append("</g></svg>")
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate()
