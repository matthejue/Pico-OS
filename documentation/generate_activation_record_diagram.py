"""Generate the embedded register layout in README section 6.2.

Run with Python 3. PCB offsets are RETI memory-cell offsets, not byte offsets.
Dashed lines enlarge the same embedded fields. Only the stored pointers use
arrows. Colors and square boxes match the existing process memory diagrams.
Explanations and section headings stay in the README prose.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import ALLOCATED, FOCUS, MUTED, POINTER


HEADER = "kernel/process/process.header"


def generate():
    f = Figure(
        "activation-record",
        "Saved registers embedded in a process control block",
        "PCB 1 is one Kernel Heap allocation. Its first eight cells precede the "
        "embedded activation record at PCB offsets 8 through 14. The seven "
        "fields are in1, in2, acc, sp, baf, cs and ds. Later PCB fields start "
        "at offset 15. Dashed lines enlarge the same embedded record, not a "
        "separate allocation. active_process points to the current PCB. "
        "dispatcher_switch_from_context writes the current PCB's record, and "
        "dispatcher_jump_to_process reads the selected PCB's record. Saved sp "
        "points one cell below the saved PC on that process's stack. Stack addresses "
        "increase from left to right. RTI reads "
        "the PC at sp + 1, increments SP and advances PC.",
        width=1760, height=620, show_address_direction=False,
    )
    f.label(32, 32, "active_process", size=22, color=POINTER, anchor="start",
            link="kernel/process/process.picoc#L18")
    f.parts.append(f'<path d="M 202 25 H 250 Q 270 25 270 45 V 100" '
                   f'fill="none" stroke="{POINTER}" stroke-width="2" '
                   f'marker-end="url(#{POINTER[1:]})"/>')
    f.label(32, 75, "PCB 1", size=23, bold=True, anchor="start", link=f"{HEADER}#L31")

    # One contiguous PCB allocation, with the activation highlighted in place.
    f.box(32, 100, 520, 140, MUTED)
    f.label(292, 129, "PCB cells 0–7", size=20, bold=True)
    for column, fields in enumerate((
        (("pid", 32), ("state", 33), ("base_address", 34), ("size", 35)),
        (("heap_start", 36), ("heap_size", 37), ("binary_path", 38), ("working_directory", 39)),
    )):
        for row, (name, line) in enumerate(fields):
            f.label(52 + column * 240, 157 + row * 24, name, size=18,
                    anchor="start", link=f"{HEADER}#L{line}")
    f.box(552, 100, 760, 140, ALLOCATED)
    f.label(932, 136, "activation", size=25, bold=True, link=f"{HEADER}#L40")
    f.label(932, 171, "Embedded ActivationRecord", size=22, link=f"{HEADER}#L21")
    f.label(932, 210, "PCB cells 8–14", size=20)
    f.box(1312, 100, 416, 140, MUTED)
    f.label(1520, 129, "PCB cells 15 onward", size=20, bold=True)
    f.label(1520, 162, "file_descriptors", size=20, link=f"{HEADER}#L42")
    f.label(1520, 192, "waiting_status_ptr", size=20, link=f"{HEADER}#L44")
    f.label(1520, 223, "Other PCB attributes …", size=18, link=f"{HEADER}#L31")
    f.box(552, 100, 760, 140, "none", FOCUS, 3)

    # Enlarged cells retain their exact order and their offsets in the PCB.
    f.parts.append('<path d="M 552 240 L 272 335 M 1312 240 L 1462 335" '
                   'fill="none" stroke="#96a3ae" stroke-dasharray="5 4"/>')
    for index, name in enumerate(("in1", "in2", "acc", "sp", "baf", "cs", "ds")):
        x = 272 + index * 170
        f.box(x, 335, 170, 85, ALLOCATED)
        f.label(x + 85, 364, f"PCB + {8 + index}", size=20)
        f.label(x + 85, 397, name, size=24, bold=True, link=f"{HEADER}#L{22 + index}")
    f.box(272, 335, 1190, 85, "none", FOCUS, 3)

    f.label(1410, 482, "Process stack", size=22, bold=True)
    f.box(1100, 505, 290, 70, MUTED)
    f.box(1390, 505, 290, 70, "#eadffa")
    f.label(1245, 534, "activation.sp", size=20, link=f"{HEADER}#L25")
    f.label(1245, 560, "One cell below saved PC", size=19)
    f.label(1535, 534, "activation.sp + 1", size=20, link=f"{HEADER}#L25")
    f.label(1535, 560, "Saved PC", size=22, bold=True)
    f.label(1390, 602, "Lower addresses → higher addresses", size=18)
    f.parts.append(f'<path d="M 867 420 C 867 465 1245 455 1245 505" '
                   f'fill="none" stroke="{POINTER}" stroke-width="2" '
                   f'marker-end="url(#{POINTER[1:]})"/>')
    f.save()


if __name__ == "__main__":
    generate()
