"""Generate the save, state-change and restore diagrams for README 6.3–6.4.

Run with Python 3. SRAM uses the chapter 3 grouping bands and colors. Lower
panels show field assignments, labeled with exact RETI cell offsets. They are
not additional allocations. Keep headings and explanations in the README.
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
    f = Figure("dispatcher-restore", "Restore PCB 5.activation and return through its user stack with RTI",
               "The same SRAM regions as the save diagram now contain the selected PCB 5. "
               "active_process already points to PCB 5 and its state is RUNNING. The naked function "
               "reads process from kernel entry SP + 2 into BAF and stack_boundary from SP + 3 into IN1. "
               "BAF temporarily addresses the PCB. Fixed PCB offsets restore SP first, then the "
               "stack boundary, then CS, DS, IN1, IN2, ACC and BAF last. The lower panels show "
               "the loads in execution order. RTI reads the saved PC at restored SP + 1, increments "
               "SP and continues at saved PC + 1. PC is not a PCB activation field.",
               width=2200, height=1120, show_address_direction=False)
    sram_context(f, 5, saving=False)
    f.row(560, 70, [
        ("entry_sp", 180, ("entry SP + 0", "free cell"), MUTED),
        ("return", 240, ("entry SP + 1", "C return address"), MUTED),
        ("arg_process", 300, ("entry SP + 2", "process → BAF"), ALLOCATED, f"{DISPATCHER}#L23"),
        ("arg_boundary", 300, ("entry SP + 3", "stack_boundary → IN1"), ALLOCATED, f"{DISPATCHER}#L24"),
    ])
    loads = (("sp", 11, 25), ("cs", 13, 27), ("ds", 14, 28),
             ("in1", 8, 22), ("in2", 9, 23), ("acc", 10, 24), ("baf", 12, 26))
    for index, (name, offset, line) in enumerate(loads):
        # Leave one row between SP and CS for the boundary installation.
        y = 670 + index * 48 + (48 if index else 0)
        f.box(140, y, 480, 48, ALLOCATED)
        f.box(620, y, 220, 48, MUTED)
        f.label(380, y + 31, f"activation.{name}", size=22, link=f"{PCB}#L{line}")
        f.label(730, y + 31, f"PCB 5 + {offset}", size=19)
        path(f, f"M 845 {y + 24} H 996", METADATA)
        f.box(1000, y, 260, 48, ALLOCATED)
        f.label(1130, y + 31, "BAF (last)" if name == "baf" else name.upper(),
                size=24, bold=True)

    f.row(660, 75, [
        ("saved_sp", 300, ("SP",), ALLOCATED, f"{PCB}#L25"),
        ("saved_pc", 350, ("SP + 1", "PC"), PC_FILL),
    ], x=1460)
    path(f, "M 1265 694 H 1455", POINTER)
    f.box(1000, 726, 1110, 32, MUTED)
    f.label(1555, 749, "STACK_HEAP_BOUNDARY_REGISTER ← IN1", size=20,
            link="kernel/exception.header#L5")
    f.box(1460, 945, 650, 95, PC_FILL)
    f.label(1785, 972, "RTI: PC ← memory[SP + 1]", size=22,
            link=f"{DISPATCHER}#L40")
    f.label(1785, 1001, "SP ← SP + 1", size=22)
    f.label(1785, 1030, "resume at PC + 1", size=22)
    path(f, "M 1935 735 V 784 H 2140 V 992 H 2115", METADATA)
    f.save()


def generate():
    save_context()
    state_change()
    restore_context()


if __name__ == "__main__":
    generate()
