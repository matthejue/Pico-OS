"""Generate the step-by-step scheduler walkthrough in README section 6.1.1.

Run with Python 3. The SVGs use the same five PCBs in every row, sharp
corners, and separate arrows for active_process, start and candidate.
Only short step labels accompany the lists. Explanations stay in the README.
"""

from html import escape
from pathlib import Path

from diagram_style import style_svg

from generate_memory_layout_diagrams import POINTER


OUTPUT = Path(__file__).resolve().parent / "images"
INK = "#172b3a"
LINE = "#43576a"
ACTIVE = "#26715b"
CANDIDATE = "#9c3d15"
STATE = "kernel/process/process.header#L33"
NEXT = "kernel/process/process.header#L53"
CURRENT = "kernel/process/process.picoc#L18"
SCHEDULER = "kernel/scheduler.picoc#L12"
DISPATCHER = "kernel/dispatcher.picoc#L43"
BEFORE_SCAN = ("READY", "BLOCKED", "READY", "STOPPED", "READY")
AFTER_P5 = ("READY", "BLOCKED", "READY", "STOPPED", "RUNNING")
AFTER_P1 = ("RUNNING", "BLOCKED", "READY", "STOPPED", "READY")
X = 460
PITCH = 200
BOX_WIDTH = 165
BOX_HEIGHT = 78
NULL_X = 1515


class Figure:
    def __init__(self, slug, title, description, rows, *, height=None):
        self.slug = slug
        self.height = height if height is not None else 60 + rows * 230
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" '
            f'height="{self.height}" viewBox="0 0 1600 {self.height}" '
            'role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            '<defs>',
        ]
        for color in (LINE, ACTIVE, CANDIDATE, POINTER):
            self.parts.append(
                f'<marker id="{color[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                'markerWidth="6" markerHeight="6" orient="auto">'
                f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{color}"/></marker>'
            )
        self.parts += [
            '</defs>',
            f'<rect width="1600" height="{self.height}" fill="white"/>',
            '<g font-family="DejaVu Sans, sans-serif">',
        ]

    def text(self, x, y, value, size=20, *, bold=False, color=INK,
             anchor="middle", link=""):
        label = (f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
                 f'font-size="{size}" font-weight="{"bold" if bold else "normal"}" '
                 f'fill="{color}">{escape(value)}</text>')
        if link:
            label = f'<a href="../../{escape(link, quote=True)}">{label}</a>'
        self.parts.append(label)

    def box(self, x, y, w, h, fill="white", stroke=LINE, thickness=2):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{thickness}"/>'
        )

    def arrow(self, path, color=LINE):
        self.parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" '
            f'marker-end="url(#{color[1:]})"/>'
        )

    def row(self, index, title, states, active, *, candidate=None,
            candidate_label="candidate", start=None, wrap=False, link=SCHEDULER):
        y = 60 + index * 230
        self.text(32, y + 25, title, size=25, bold=True, anchor="start", link=link)

        for pcb, state in enumerate(states, 1):
            x = X + (pcb - 1) * PITCH
            fill = {"READY": "#deecff", "RUNNING": "#edf7f1"}.get(state, "#f0f3f6")
            self.box(x, y, BOX_WIDTH, BOX_HEIGHT, fill,
                     CANDIDATE if candidate == pcb else LINE,
                     3 if candidate == pcb else 2)
            self.text(x + BOX_WIDTH / 2, y + 29, f"PCB {pcb}",
                      size=22, bold=True, link="kernel/process/process.header#L31")
            self.text(x + BOX_WIDTH / 2, y + 59, f"state: {state}", size=18, link=STATE)
            end = X + pcb * PITCH if pcb < 5 else NULL_X - 34
            self.arrow(f"M {x + BOX_WIDTH + 3} {y + 40} H {end - 7}")
            self.text((x + BOX_WIDTH + end) / 2, y + 26, "next", size=14, link=NEXT)

        self.text(NULL_X, y + 47, "NULL", size=22, link=NEXT)
        active_x = X + (active - 1) * PITCH + BOX_WIDTH / 2
        self.text(active_x, y - 28, "active_process", size=21, color=ACTIVE, link=CURRENT)
        self.arrow(f"M {active_x} {y - 20} V {y - 3}", ACTIVE)

        self.text(32, y + 145, "process_list_head", size=21, color=POINTER,
                  anchor="start", link="kernel/process/process.picoc#L16")
        self.arrow(f"M 250 {y + 138} H {X + 18} V {y + BOX_HEIGHT + 3}", POINTER)

        if start is not None:
            sx = X + (start - 1) * PITCH + BOX_WIDTH / 2
            self.text(sx, y - 28, "start", size=21, color=CANDIDATE, link=SCHEDULER)
            self.arrow(f"M {sx} {y - 20} V {y - 3}", CANDIDATE)

        if candidate is not None:
            cx = NULL_X if candidate == 0 else X + (candidate - 1) * PITCH + BOX_WIDTH / 2
            self.text(cx - 20 if candidate == 0 else cx, y + 127,
                      "candidate == NULL" if candidate == 0 else candidate_label,
                      size=21, color=CANDIDATE,
                      anchor="end" if candidate == 0 else "middle", link=SCHEDULER)
            if candidate != 0:
                self.arrow(f"M {cx} {y + 107} V {y + BOX_HEIGHT + 3}", CANDIDATE)

        if wrap:
            # One arrow leaves NULL and ends at PCB 1. The label above identifies
            # the condition, rather than adding a pointer arrow back toward NULL.
            # This is a scheduler assignment, not a stored PCB next link.
            self.arrow(f"M {NULL_X} {y + 64} V {y + 163} H {X + BOX_WIDTH / 2} "
                       f"V {y + BOX_HEIGHT + 3}", CANDIDATE)
            self.text(1010, y + 152, "candidate = first_process()", size=21,
                      color=CANDIDATE, link="kernel/process/process.picoc#L28")

    def save(self):
        self.parts.append('</g></svg>')
        OUTPUT.mkdir(exist_ok=True)
        (OUTPUT / f"scheduler-{self.slug}.svg").write_text(style_svg("\n".join(self.parts) + "\n"))


def generate():
    overview = Figure(
        "overview", "PCB list with process_list_head and active_process",
        "Five PCBs are connected from left to right by ProcessControlBlock.next. "
        "PCB 5.next is NULL. The two global variables appear on the left. "
        "process_list_head points to PCB 1 and active_process points to PCB 3, "
        "whose state is RUNNING. Other state values are READY, BLOCKED, STOPPED and READY.",
        0, height=245,
    )
    y = 70
    for pcb, state in enumerate(("READY", "BLOCKED", "RUNNING", "STOPPED", "READY"), 1):
        x = X + (pcb - 1) * PITCH
        fill = {"READY": "#deecff", "RUNNING": "#edf7f1"}.get(state, "#f0f3f6")
        overview.box(x, y, BOX_WIDTH, BOX_HEIGHT, fill)
        overview.text(x + BOX_WIDTH / 2, y + 29, f"PCB {pcb}", size=22,
                      bold=True, link="kernel/process/process.header#L31")
        overview.text(x + BOX_WIDTH / 2, y + 59, f"state: {state}", size=18, link=STATE)
        end = X + pcb * PITCH if pcb < 5 else NULL_X - 34
        overview.arrow(f"M {x + BOX_WIDTH + 3} {y + 40} H {end - 7}")
        overview.text((x + BOX_WIDTH + end) / 2, y + 26, "next", size=14, link=NEXT)
    overview.text(NULL_X, y + 47, "NULL", size=22, link=NEXT)
    overview.text(32, y + 47, "process_list_head", size=21, color=POINTER,
                  anchor="start", link="kernel/process/process.picoc#L16")
    overview.arrow(f"M 250 {y + 40} H {X - 3}", POINTER)
    overview.text(32, 200, "active_process", size=21, color=ACTIVE,
                  anchor="start", link=CURRENT)
    active_x = X + 2 * PITCH + BOX_WIDTH / 2
    overview.arrow(f"M 250 193 H {active_x} V {y + BOX_HEIGHT + 3}", ACTIVE)
    overview.save()

    f = Figure("select", "Steps 1–3: skip state STOPPED, select PCB 5, then dispatch",
               "The same five linked PCBs appear in each step. PCB 3 is initially current, "
               "with its context saved and its state set to READY by the dispatcher. "
               "The scheduler starts at PCB 4, skips its STOPPED state, and returns PCB 5 with "
               "state READY. Only the dispatcher changes active_process to PCB 5 "
               "and PCB 5's state to RUNNING.", 3)
    f.row(0, "1. Skip PCB 4", BEFORE_SCAN, 3, candidate=4, start=4)
    f.row(1, "2. Select PCB 5", BEFORE_SCAN, 3, candidate=5, start=4)
    f.row(2, "3. Dispatch PCB 5", AFTER_P5, 5, link=DISPATCHER)
    f.save()

    f = Figure("next-turn", "Steps 4–5: the current process is last in the list",
               "PCB 5 is now current and PCB 5.next is NULL. After the dispatcher saves PCB 5's "
               "context and sets its state to READY, the next scheduler call sets "
               "start and candidate to the head, PCB 1, and returns it because its state "
               "is READY. The dispatcher changes active_process to PCB 1, PCB 5's state to "
               "READY, and PCB 1's state to RUNNING. PCB 5.next remains NULL.", 2)
    f.row(0, "4. Wrap to PCB 1", BEFORE_SCAN, 5, candidate=1, start=1)
    f.row(1, "5. Dispatch PCB 1", AFTER_P1, 1, link=DISPATCHER)
    f.save()

    variation = ("READY", "BLOCKED", "READY", "STOPPED", "BLOCKED")
    f = Figure("scan-end", "Variation: PCB 5's state is BLOCKED, so the scan reaches NULL",
               "This variation starts after saving PCB 3's context, with PCB 3 still current "
               "and its state READY. PCB 5's state is now BLOCKED. With start PCB 4, "
               "the scheduler skips PCB 4 and PCB 5, reaching "
               "candidate NULL. It then assigns candidate to first_process(), PCB 1. "
               "The second loop returns PCB 1 in state READY. active_process stays PCB 3 "
               "during both scheduler loops. The wrap arrow is an assignment, "
               "not a PCB next link.", 2)
    f.row(0, "A. Reach NULL", variation, 3, candidate=0, start=4, wrap=True)
    f.row(1, "B. Select PCB 1", variation, 3, candidate=1, start=4)
    f.save()


if __name__ == "__main__":
    generate()
