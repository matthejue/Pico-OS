"""Generate the save, state-change and restore diagrams for README 6.3–6.4.

Run with Python 3. The save diagram uses the chapter 3 SRAM grouping bands.
The restore diagram separates SRAM, CPU registers and periphery, retaining
the same region names and colors. Keep overall headings in the README.
SVGs retain accessible descriptions and links to the source definitions.
"""

from generate_memory_layout_diagrams import (
    ADDRESS, ALLOCATED, HEADER, METADATA, MUTED, POINTER,
)
from generate_process_diagrams import Figure


PCB = "kernel/process/process.header"
DISPATCHER = "kernel/dispatcher.picoc"
PC_FILL = "#eadffa"
REGISTERS = (
    ("in1", 8, 22), ("in2", 9, 23), ("acc", 10, 24),
    ("sp", 11, 25), ("baf", 12, 26), ("cs", 13, 27), ("ds", 14, 28),
)


def path(f, d, color=POINTER):
    f.parts.append(f'<path d="{d}" fill="none" stroke="{color}" '
                   f'stroke-width="2" marker-end="url(#{color[1:]})"/>')


def step_number(f, x, baseline, number, color=METADATA):
    """Draw a circled action number beside its label."""
    f.parts.append(f'<circle cx="{x}" cy="{baseline - 8}" r="16" '
                   f'fill="white" stroke="{color}" stroke-width="2"/>')
    f.label(x, baseline - 1, number, size=20, bold=True, color=color)


def sram_context(f, number, *, saving):
    """Same SRAM regions for both directions of a context switch."""
    stack_lines = ("Kernel Stack", "caller_context") if saving else (
        "Kernel Stack", "process", "stack_boundary")
    f.row(270, 150, [
        ("ivt", 60, (".ivt",), MUTED),
        ("text", 100, (".text", "kernel code"), MUTED),
        ("data", 250, (".data · kernel globals", "kernel_heap.first_block",
                       "process_list_head", "active_process"), MUTED),
        ("ha", 60, ("Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("pcb1", 170, ("Payload A", "PCB 1"), MUTED, f"{PCB}#L31"),
        ("hb", 60, ("Block", "Header B"), HEADER, "common/heap.header#L5"),
        ("pcb_before", 100, (f"PCB {number}", "cells 0–7"), MUTED, f"{PCB}#L31"),
        ("activation", 300, ("activation", "cells 8–14"), ALLOCATED, f"{PCB}#L40"),
        ("pcb_after", 100, ("cells 15+", "other fields"), MUTED, f"{PCB}#L31"),
        ("kstack", 160, stack_lines, MUTED),
        ("oh", 70, ("Outer", "Block", "Header A"), HEADER, "common/heap.header#L5"),
        ("image", 240, ("User Process Image", f"PCB {number}", ".text · .data"), MUTED),
        ("uheap", 140, ("User", "Process Heap"), MUTED),
        ("ustack", 310, ("User Process Stack", "saved interrupt frame"), ALLOCATED),
    ])
    f.band("ivt", "data", 420, "Kernel Image")
    f.band("ha", "pcb_after", 420, "Kernel Heap")
    f.band("kstack", "kstack", 420, "Kernel Stack")
    f.band("image", "image", 420, "User Process Image")
    f.band("uheap", "uheap", 420, "User Process Heap")
    f.band("ustack", "ustack", 420, "User Process Stack", ALLOCATED)
    f.band("ivt", "kstack", 450, "Kernel")
    f.band("oh", "ustack", 450, "Process and Shared Data Heap")
    f.band("pcb_before", "pcb_after", 480, f"Payload B · PCB {number}", ALLOCATED)
    f.band("image", "ustack", 480, f"Process Payload A · PCB {number}", ALLOCATED)
    f.arrow("data", "ha", "kernel_heap.first_block", 80,
            source_shift=-85, label_x=485, color=POINTER)
    f.arrow("data", "pcb1", "process_list_head", 140,
            source_shift=-15, label_x=570, color=POINTER)
    f.arrow("data", "pcb_before", "active_process", 205,
            source_shift=90, target_shift=-25, label_x=775, color=ADDRESS)
    if saving:
        f.arrow("kstack", "ustack", "caller_context", 130,
                source_shift=25, color=POINTER)
    else:
        f.arrow("kstack", "pcb_before", "BAF = process", 130,
                source_shift=25, target_shift=25, color=POINTER)
    f.focus("activation")


def save_context():
    f = Figure("dispatcher-save", "Copy the outgoing user context into PCB 3.activation",
               "SRAM contains Kernel Image, Kernel Heap, Kernel Stack and Process and Shared Data Heap. "
               "active_process and the local process point to PCB 3. caller_context is a kernel-call "
               "argument pointing to the free cell below the user process's saved interrupt frame. "
               "Stack offsets 1 through 6 hold DS, CS, BAF, IN2, IN1 and ACC. Each value is copied "
               "to its named activation field in the same PCB allocation. activation.sp receives "
               "the address caller_context + 6, not the ACC value. The saved PC at offset 7 stays "
               "on the user stack. Lower panels are an assignment view with exact PCB offsets, "
               "not the physical ordering of activation fields.",
               width=2200, height=1010, show_address_direction=False)
    sram_context(f, 3, saving=True)

    # Each row is one assignment. Activation is embedded, with actual offsets
    # printed explicitly rather than suggesting that these rows are its layout.
    offsets = {name: (offset, line) for name, offset, line in REGISTERS}
    stack = ("free cell", "DS", "CS", "BAF", "IN2", "IN1", "ACC", "PC")
    for index, value in enumerate(stack):
        y = 560 + index * 48
        f.box(1220, y, 250, 48, MUTED)
        f.box(1470, y, 650, 48, PC_FILL if index == 7 else ALLOCATED if index else MUTED)
        f.label(1345, y + 31, f"caller_context + {index}", size=18)
        f.label(1795, y + 31, value, size=21, bold=True)
        if 1 <= index <= 6:
            name = ("ds", "cs", "baf", "in2", "in1", "acc")[index - 1]
            offset, line = offsets[name]
            f.box(140, y, 480, 48, ALLOCATED)
            f.box(620, y, 220, 48, MUTED)
            f.label(380, y + 31, f"activation.{name}", size=22,
                    link=f"{PCB}#L{line}")
            f.label(730, y + 31, f"PCB 3 + {offset}", size=19)
            path(f, f"M 1216 {y + 24} H 845", METADATA)
            f.label(1030, y + 16, f"caller_context[{index}]", size=18, color=METADATA,
                    link=f"{DISPATCHER}#L{75 + index}")

    f.label(1130, 585, "caller_context", size=18, color=POINTER, anchor="end",
            link=f"{DISPATCHER}#L71")
    path(f, "M 1145 580 H 1216", POINTER)
    f.box(140, 896, 480, 48, ALLOCATED)
    f.box(620, 896, 220, 48, MUTED)
    f.label(380, 927, "activation.sp", size=22, link=f"{PCB}#L25")
    f.label(730, 927, "PCB 3 + 11", size=19)
    # SP is the address of the ACC cell. Its arrow is separate from value copies.
    path(f, "M 1220 885 H 1185 V 984 H 380 V 949", POINTER)
    f.label(1025, 970, "caller_context + 6", size=19, color=POINTER,
            link=f"{DISPATCHER}#L75")
    f.save()


def state_change():
    f = Figure("dispatcher-state", "Outgoing PCB state during dispatcher_switch_from_context",
               "After copying the context, dispatcher_switch_from_context changes only state RUNNING "
               "to READY. BLOCKED from a wait and STOPPED from signal handling remain unchanged. "
               "READY can result from a wakeup or SIGCONT before selection and also remains unchanged. "
               "NEW and ZOMBIE are left untouched by the condition but are not normal outgoing "
               "resumable contexts. A NULL current process skips activation and state writes. "
               "All branches call dispatcher_start_next_process. The save step leaves other PCB states "
               "and active_process unchanged, before selection and dispatch update them.",
               width=1840, height=250, show_address_direction=False)
    cases = (
        ("RUNNING", "READY", 14, 13, ALLOCATED),
        ("BLOCKED", "BLOCKED", 15, 15, MUTED),
        ("STOPPED", "STOPPED", 16, 16, MUTED),
        ("READY", "READY", 13, 13, ALLOCATED),
    )
    for index, (before, after, bline, aline, fill) in enumerate(cases):
        x = 32 + (index % 2) * 1000
        y = 32 + (index // 2) * 110
        f.box(x, y, 310, 75, fill)
        f.label(x + 155, y + 28, "process->state", size=20, link=f"{PCB}#L33")
        f.label(x + 155, y + 58, before, size=26, bold=True, link=f"{PCB}#L{bline}")
        path(f, f"M {x + 318} {y + 37} H {x + 462}",
             ADDRESS if before != after else METADATA)
        f.box(x + 470, y, 310, 75, ALLOCATED if after == "READY" else MUTED)
        f.label(x + 625, y + 28, "process->state", size=20, link=f"{PCB}#L33")
        f.label(x + 625, y + 58, after, size=26, bold=True, link=f"{PCB}#L{aline}")
    f.save()


def restore_context():
    f = Figure("dispatcher-restore", "Restore PCB 1.activation and return through its user stack with RTI",
               "This standalone example uses PCB 1 as the selected process. "
               "Three separate regions show PCB 1 in SRAM's Kernel Heap, the CPU, and PCB 1's "
               "user stack and code in SRAM's Process Payload A. activation is embedded in PCB 1. "
               "Its seven fields are shown in struct order and arrows copy their values into CPU "
               "registers. The PCB and stack tables each show lower addresses at the top and "
               "higher addresses at the bottom, with downward address-order arrows. The user "
               "process image is above the heap, which is above the stack, matching SRAM address order. "
               "Circled action numbers show SP restored first, the periphery stack boundary "
               "installed second, and the remaining registers restored third, with BAF last. "
               "Step 4 executes the CPU instruction RTI, meaning return from interrupt. "
               "Step numbers describe the action order, not process numbers. "
               "The SP register stores an address pointing to the saved ACC cell in the user stack. "
               "SP and SP + 1 in the stack's address column denote SRAM addresses, not registers. "
               "RTI actually reads the saved PC from the cell at SP + 1, advances SP by one, and "
               "sets the CPU PC to saved PC + 1 to resume in the selected process's .text. "
               "The stack addresses are shown before RTI. The separate memory-mapped "
               "STACK_HEAP_BOUNDARY_REGISTER detects stack growth into the user heap.",
               width=1800, height=890, show_address_direction=False)

    # Region labels establish where each object lives. These are separate
    # detail views, not neighboring cells in one physical memory rectangle.
    f.box(32, 32, 500, 590, "white", thickness=2)
    f.label(282, 70, "SRAM · Kernel Heap", size=27, bold=True)
    f.box(52, 96, 460, 506, MUTED)
    f.label(282, 132, "Payload B · PCB 1", size=27, bold=True, link=f"{PCB}#L31")
    f.label(282, 167, "state = RUNNING", size=23, link=f"{PCB}#L33")
    f.label(282, 207, "activation · saved register values", size=24,
            link=f"{PCB}#L40")

    f.box(770, 32, 330, 828, "white", thickness=2)
    f.label(935, 70, "CPU", size=29, bold=True)
    f.label(935, 111, "Live registers", size=25)

    step_number(f, 610, 161, 3)
    f.label(634, 161, "Load", size=22, color=METADATA, anchor="start")
    f.label(651, 190, "remaining registers", size=22, color=METADATA)
    roles = {"sp": "SP · stack pointer", "cs": "CS · code base",
             "ds": "DS · data base", "baf": "BAF (restored last)"}
    for index, (name, offset, line) in enumerate(REGISTERS):
        y = 224 + index * 52
        f.box(72, y, 420, 52, ALLOCATED)
        f.label(94, y + 34, f"activation.{name}", size=25, anchor="start",
                link=f"{PCB}#L{line}")
        if index in (0, len(REGISTERS) - 1):
            f.label(469, y + 23, f"PCB + {offset}", size=21, anchor="end")
            f.label(469, y + 44,
                    "Lower address" if index == 0 else "Higher address",
                    size=16, anchor="end", color=ADDRESS)
        else:
            f.label(469, y + 34, f"PCB + {offset}", size=21, anchor="end")
        f.box(800, y, 270, 52, ALLOCATED)
        f.label(935, y + 34, roles.get(name, name.upper()), size=23, bold=True)
        path(f, f"M 497 {y + 26} H 795", ADDRESS if name == "sp" else METADATA)
    path(f, "M 61 238 V 574", ADDRESS)
    f.label(282, 649, "PCB addresses increase ↓", size=22, color=ADDRESS)
    step_number(f, 584, 393, 1, ADDRESS)
    f.label(608, 393, "Load SP", size=24, color=ADDRESS, anchor="start")

    f.box(1230, 32, 538, 828, "white", thickness=2)
    f.label(1499, 70, "SRAM · Process Payload A", size=27, bold=True)
    f.label(1499, 111, "PCB 1's user process", size=25)
    f.label(1499, 149, "Lower addresses", size=22, color=ADDRESS)
    path(f, "M 1240 176 V 782", ADDRESS)
    f.label(1499, 790, "Higher addresses", size=22, color=ADDRESS)

    # Keep the process regions in physical address order: image, heap, stack.
    f.box(1270, 170, 458, 156, PC_FILL)
    f.label(1499, 206, "User Process Image · .text", size=25, bold=True)
    f.label(1499, 248, "Instruction at saved PC + 1", size=25)
    f.label(1499, 289, "Process 1 resumes here", size=26, bold=True)
    f.box(1270, 348, 458, 70, MUTED)
    f.label(1499, 392, "User Process Heap", size=25, bold=True)

    f.box(1250, 450, 498, 280, MUTED)
    f.label(1499, 486, "User Process Stack", size=27, bold=True)
    f.label(1499, 519, "Addresses shown before RTI", size=23)
    f.label(1340, 545, "Address", size=21)
    f.label(1590, 545, "Stored value", size=21)
    for y, address, value, fill in (
        (550, "SP", "saved ACC", ALLOCATED),
        (602, "SP + 1", "saved PC", PC_FILL),
    ):
        f.box(1270, y, 140, 52, MUTED)
        f.box(1410, y, 318, 52, fill)
        f.label(1340, y + 23, address, size=25, bold=True)
        f.label(1340, y + 44,
                "Lower address" if address == "SP" else "Higher address",
                size=16, color=ADDRESS)
        f.label(1569, y + 34, value, size=25, bold=True)
    path(f, "M 1259 564 V 640", ADDRESS)
    f.label(1499, 686, "Stack addresses increase ↓", size=22, color=ADDRESS)
    f.label(1499, 716, "Each row is one SRAM cell", size=21)
    path(f, "M 1075 406 H 1195 V 576 H 1265", POINTER)
    f.label(1160, 391, "points to", size=22, color=POINTER)

    # The boundary is a periphery register, not a member of the CPU register
    # bank or a divider between register rows. IN1 holds it only temporarily.
    f.box(32, 674, 680, 186, MUTED, thickness=2)
    f.label(372, 709, "Periphery · memory-mapped register", size=26, bold=True)
    step_number(f, 253, 745, 2)
    f.label(277, 745, "Install stack limit", size=24, anchor="start",
            link="common/periphery_asm.header#L2")
    f.label(372, 782, "STACK_HEAP_BOUNDARY_REGISTER ← IN1", size=24,
            link="kernel/exception.header#L5")
    f.label(372, 814, "IN1 temporarily holds stack_boundary", size=23,
            link=f"{DISPATCHER}#L24")
    f.label(372, 844, "Detects stack growth into the user heap", size=23)

    # The saved-PC read is an actual data transfer performed by RTI. The
    # outgoing arrow identifies the resumed instruction in the process code.
    f.box(800, 674, 270, 156, PC_FILL)
    step_number(f, 852, 710, 4)
    f.label(876, 710, "Execute RTI", size=24, bold=True, anchor="start",
            link=f"{DISPATCHER}#L40")
    f.label(935, 743, "Return from interrupt", size=21)
    f.label(935, 779, "PC ← saved PC + 1", size=23)
    f.label(935, 811, "SP ← SP + 1", size=24)
    path(f, "M 1733 628 H 1758 V 758 H 1160 V 702 H 1075", METADATA)
    f.label(1499, 753, "RTI reads this saved PC", size=22, color=METADATA)
    path(f, "M 1075 780 H 1115 V 844 H 1788 V 248 H 1733", POINTER)
    f.label(1499, 827, "PC points to the resumed instruction", size=22, color=POINTER)
    f.save()


def generate():
    save_context()
    state_change()
    restore_context()


if __name__ == "__main__":
    generate()
