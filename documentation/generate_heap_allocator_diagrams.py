"""Draw the allocator example in README section 3.6 as editable SVG diagrams."""

from html import escape
from pathlib import Path


OUTPUT = Path(__file__).parent / "images"
HEADER_CELLS = 3
REGION_CELLS = 52
# Reserve room for every header that appears, including D′ inside the initial D
# payload. Give its two-cell payload enough space for its labels. These reserved
# widths keep the same addresses at the same positions in every frame.
HEADER_WIDTH = 102
CELL_WIDTH = 18
HEADER_OFFSETS = (0, 11, 18, 33, 47)
CELL_WIDTHS = {50: 45, 51: 45}
ORIGIN = 32
TOP = 100
HEIGHT = 116


def block(label, offset, size, free):
    return (label, offset, size, free)


A = block("A", 0, 8, False)
B = block("B", 11, 4, True)
C = block("C", 18, 12, False)
D = block("D", 33, 16, True)
USED_D = block("D", 33, 11, False)
TAIL = block("D′", 47, 2, True)

STATES = [
    ("01-initial", "Initial state: request 11 cells", [A, B, C, D], "D"),
    ("02-allocated", "Allocation: D split into 11 allocated cells and a free remainder D′",
     [A, B, C, USED_D, TAIL], "D"),
    ("03-d-marked-free", "Free D: mark its header free before the merge scan",
     [A, B, C, block("D", 33, 11, True), TAIL], "D"),
    ("04-d-merged", "Merge D + D′: D.size = 11 + 3 + 2 = 16, D.next = NULL",
     [A, B, C, D], "D"),
    ("05-c-marked-free", "Free C: B, C, and D are now consecutive free blocks",
     [A, B, block("C", 18, 12, True), D], "C"),
    ("06-b-c-merged", "First merge: B.size = 4 + 3 + 12 = 19, B.next = D",
     [A, block("B", 11, 19, True), D], "B"),
    ("07-b-d-merged", "Second merge at B: B.size = 19 + 3 + 16 = 38, B.next = NULL",
     [A, block("B", 11, 38, True)], "B"),
]

ABSORBED_HEADERS = {
    "04-d-merged": {"D": "Includes former Header D′"},
    "05-c-marked-free": {"D": "Includes former Header D′"},
    "06-b-c-merged": {"B": "Includes former Header C", "D": "Includes former Header D′"},
    "07-b-d-merged": {"B": "Includes former Headers C, D, D′"},
}


def text(x, y, value, *, size=16, weight="normal", anchor="middle", color="#172b3a"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{color}">{escape(value)}</text>')


def render(slug, title, blocks, highlighted):
    parts = []
    positions = []
    x = ORIGIN
    end = 0
    for label, offset, size, free in blocks:
        assert offset == end
        end = offset + HEADER_CELLS + size
        positions.append(x + HEADER_WIDTH / 2)
        internal_headers = sum(offset + HEADER_CELLS <= h and h + HEADER_CELLS <= end
                               for h in HEADER_OFFSETS)
        payload_width = sum(CELL_WIDTHS.get(cell, CELL_WIDTH)
                            for cell in range(offset + HEADER_CELLS, end))
        payload_width += internal_headers * (HEADER_WIDTH - 3 * CELL_WIDTH)
        fill = "#e5f3de" if free else "#deecff"
        parts.append(f'<rect x="{x}" y="{TOP}" width="{HEADER_WIDTH}" height="{HEIGHT}" '
                     'fill="#fff0cc"/>')
        for dy, value in [(24, "Block Header"), (44, label), (66, f"size = {size}"),
                          (87, f"free = {str(free).lower()}"), (106, "3 cells")]:
            parts.append(text(x + HEADER_WIDTH / 2, TOP + dy, value, size=13,
                              weight="bold" if dy <= 44 else "normal"))
        x += HEADER_WIDTH
        parts.append(f'<rect x="{x}" y="{TOP}" width="{payload_width}" height="{HEIGHT}" '
                     f'fill="{fill}"/>')
        for dy, value in [(39, f"Payload {label}"), (62, "FREE" if free else "ALLOCATED"),
                          (85, f"{size} cells")]:
            parts.append(text(x + payload_width / 2, TOP + dy, value, size=13,
                              weight="bold" if dy == 62 else "normal"))
        absorbed = ABSORBED_HEADERS.get(slug, {}).get(label)
        if absorbed:
            parts.append(text(x + payload_width / 2, TOP + 105, absorbed, size=12))
        if label == highlighted:
            parts.append(f'<rect x="{x - HEADER_WIDTH}" y="{TOP}" '
                         f'width="{HEADER_WIDTH + payload_width}" height="{HEIGHT}" '
                         'fill="none" stroke="#9c3d15" stroke-width="3"/>')
        parts.append(text(x - HEADER_WIDTH, TOP + HEIGHT + 22, f"{offset}",
                          size=13, anchor="start"))
        x += payload_width
    assert end == REGION_CELLS
    width = x + ORIGIN
    # Each physical boundary is one line shared by its neighboring regions.
    parts.append(f'<rect x="{ORIGIN}" y="{TOP}" width="{x - ORIGIN}" '
                 f'height="{HEIGHT}" fill="none" stroke="#43576a"/>')
    for position in positions:
        for boundary in (position - HEADER_WIDTH / 2, position + HEADER_WIDTH / 2):
            if boundary != ORIGIN:
                parts.append(f'<path d="M {boundary} {TOP} v {HEIGHT}" stroke="#43576a"/>')
    for left, right in zip(positions, positions[1:]):
        parts.append(f'<path d="M {left} {TOP} C {left} 46, {right} 46, {right} {TOP - 4}" '
                     'fill="none" stroke="#405ea8" stroke-width="2" marker-end="url(#arrow)"/>')
        parts.append(text((left + right) / 2, 55, "next", size=14, color="#405ea8"))
    parts.append(text(positions[-1], 76, "next = NULL", size=13, color="#405ea8"))
    parts.append(text(ORIGIN, 76, "first_block", size=12, anchor="start"))
    parts.append(f'<path d="M {ORIGIN + 6} 82 L {positions[0]} {TOP - 3}" '
                 'stroke="#405ea8" stroke-width="1.5" marker-end="url(#arrow)"/>')
    parts.append(text(ORIGIN, 273, "Header offsets in RETI cells from region start",
                      size=14, anchor="start"))
    parts.append(text(x, TOP + HEIGHT + 22, str(REGION_CELLS), size=13, anchor="end"))
    parts.append(text(x, 273, "Increasing addresses →", size=14, anchor="end"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="292" '
           f'viewBox="0 0 {width} 292" role="img" aria-labelledby="title desc">\n'
           f'<title id="title">{escape(title)}</title>\n'
           '<desc id="desc">One continuous horizontal heap region with adjacent headers and payloads sharing divider lines. '
           'Curved next arrows link headers in address order. Green payloads are free, '
           'blue payloads are allocated, and the orange outline marks the changed or selected block. '
           'Widths preserve memory positions across steps but are not to scale in cells.</desc>\n'
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
           'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
           '<path d="M 0 0 L 10 5 L 0 10 z" fill="#405ea8"/></marker></defs>\n'
           f'<rect width="{width}" height="292" fill="white"/>\n'
           '<g font-family="DejaVu Sans, sans-serif">\n'
           + "\n".join(parts) + "\n</g>\n</svg>\n")
    (OUTPUT / f"heap-{slug}.svg").write_text(svg)


def main():
    OUTPUT.mkdir(exist_ok=True)
    for state in STATES:
        render(*state)


if __name__ == "__main__":
    main()
