"""Generate the simple waiting cycle in README chapter 7.

Run with Python 3. The SVG is the editable master, in 16:9 slide proportions.
Use rsvg-convert to export a 1920-by-1080 PNG for presentations. This shows an
ordinary wait, without a stop signal. All boxes have sharp corners.
"""

from html import escape
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent / "images" / "blocking-cycle.svg"
INK = "#172b3a"
LINE = "#43576a"
BLOCKED = "#995b0b"
READY = "#285fa3"
RUNNING = "#26715b"
STATE = "kernel/process/process.header#L33"
SLEEP = "library/unistd/blocking.picoc#L9"
WAKEUP = "library/unistd/blocking.picoc#L19"
QUEUE = "common/wait_queue.header#L5"
SELECT = "kernel/scheduler.picoc#L12"
RESTORE = "kernel/dispatcher.picoc#L43"


class Figure:
    def __init__(self):
        self.parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" '
            'viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">',
            '<title id="title">Sleep, wakeup, resume: the waiting cycle</title>',
            '<desc id="desc">A clockwise cycle shows one process\'s PCB state. '
            'BLOCKED: waiting for an event on a wait queue after sleep(). '
            'An event triggers wakeup(), removing the waiter and making its state '
            'READY: waiting for CPU time. The scheduler selects it and the dispatcher '
            'resumes it with state RUNNING. If it needs another event, sleep() joins '
            'the wait queue again. Kernel events use the corresponding queue helpers '
            'directly. The central message is READY does not mean RUNNING.</desc>',
            '<defs>',
            '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{LINE}"/></marker>',
            '</defs>',
            '<rect width="1600" height="900" fill="white"/>',
            '<g font-family="DejaVu Sans, sans-serif">',
        ]

    def text(self, x, y, value, size=28, *, bold=False, color=INK, link=""):
        text = (f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
                f'font-weight="{"bold" if bold else "normal"}" fill="{color}">'
                f'{escape(value)}</text>')
        if link:
            text = f'<a href="../../{escape(link, quote=True)}">{text}</a>'
        self.parts.append(text)

    def box(self, x, y, width, height, fill="white", stroke=LINE, thickness=2.5):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                          f'fill="{fill}" stroke="{stroke}" stroke-width="{thickness}"/>')

    def path(self, points, *, arrow=False, color=LINE, thickness=4):
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.parts.append(f'<path d="{points}" fill="none" stroke="{color}" '
                          f'stroke-width="{thickness}" stroke-linejoin="miter"{marker}/>')

    def state(self, x, y, name, meaning, fill, color, link):
        self.box(x, y, 360, 160, fill, color)
        self.text(x + 180, y + 66, name, 38, bold=True, color=color, link=link)
        self.text(x + 180, y + 114, meaning, 26)

    def save(self):
        self.parts.append("</g></svg>")
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text("\n".join(self.parts) + "\n", encoding="utf-8")


def generate():
    f = Figure()
    f.text(800, 88, "sleep() → wakeup() → resume", 48, bold=True)
    f.text(800, 148, "One process · its PCB state", 26, color=LINE, link=STATE)

    f.state(160, 260, "BLOCKED", "Waiting for an event", "#fff5e3", BLOCKED,
            "kernel/process/process.header#L15")
    f.state(1080, 260, "READY", "Waiting for CPU time", "#eef5ff", READY,
            "kernel/process/process.header#L13")
    f.state(620, 620, "RUNNING", "Executing on the CPU", "#edf7f1", RUNNING,
            "kernel/process/process.header#L14")

    # Three arrows make one clockwise loop. Each has one action and one reason.
    f.path("M 532 340 H 1068", arrow=True)
    f.text(800, 300, "wakeup()", 34, bold=True, link=WAKEUP)
    f.text(800, 384, "Leave wait queue", 28, link=QUEUE)

    f.path("M 1260 432 C 1260 570 1108 700 992 700", arrow=True)
    f.text(1430, 540, "Scheduler selects", 26, bold=True, link=SELECT)
    f.text(1430, 582, "Dispatcher resumes", 24, link=RESTORE)

    f.path("M 608 700 C 492 700 340 570 340 432", arrow=True)
    f.text(256, 540, "sleep()", 34, bold=True, link=SLEEP)
    f.text(256, 582, "Join wait queue", 28, link=QUEUE)

    f.text(800, 526, "READY ≠ RUNNING", 32, bold=True, color=READY, link=STATE)
    f.save()


if __name__ == "__main__":
    generate()
