"""Generate the README's interrupt memory diagrams from the linked constants."""

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


def cells(fig, x, y, rows, width=450):
    """Higher addresses at the top. Each row is one RETI memory cell."""
    for index, (address, value, kind) in enumerate(rows):
        top = y + index * 28
        fig.box(x, top, 103, 28, "unused")
        fig.box(x + 103, top, width - 103, 28, kind)
        fig.text(x + 9, top + 21, address, 16)
        fig.text(x + 113, top + 21, value, 14 if len(value) > 35 else 17)


def context(result="saved IN2", prefix="c", consumed=False, returned=False):
    values = ["saved PC (P)", "saved ACC", "saved IN1", result,
              "saved BAF", "saved CS", "saved DS", "free"]
    return [(f"{prefix}+{7-i}" if i < 7 else prefix, value,
             "unused" if returned or (consumed and i != 0) else "pc" if i == 0 else "free" if i == 7 else "saved")
            for i, value in enumerate(values)] + [
                ("c-1", "no live frame here", "unused"),
                ("c-2", "no live frame here", "unused")]


def empty_kernel():
    return [("K", "initial free cell", "free")] + [
        (f"K-{i}", "not used by this entry", "unused") for i in range(1, 8)]


def columns(name, title, stages, description):
    fig = Figure(24 + 526*len(stages), 850, title, description)
    fig.text(24, 30, title, 23, True)
    for i, stage in enumerate(stages):
        x = 24 + i * 526
        fig.text(x, 72, stage["title"], 21, True)
        if i < len(stages)-1:
            fig.arrow([(x + 461, 64), (x + 504, 64)])
        fig.text(x, 107, "Kernel stack · higher addresses at top", 17, True)
        cells(fig, x, 122, stage["kernel"])
        fig.text(x, 414, stage.get("stack", "User-process stack") + " · grows downward", 17, True)
        cells(fig, x, 429, stage["user"])
        fig.box(x, 710, 450, 83, "active", stage["regs"], 17)
        if "pointer" in stage:
            row, label = stage["pointer"]
            top = 429 + row * 28 + 14
            fig.text(x + 463, top - 10, label, 14, anchor="end")
            fig.arrow([(x + 460, top), (x + 451, top)], True)
        if "kernel_pointer" in stage:
            row, label = stage["kernel_pointer"]
            top = 122 + row * 28 + 14
            fig.text(x + 463, top - 10, label, 14, anchor="end")
            fig.arrow([(x + 460, top), (x + 451, top)], True)
        if "transfer" in stage:
            if stage["transfer"] == "c":
                fig.arrow([(x + 451, 740), (x + 495, 740), (x + 495, 136), (x + 451, 136)])
            else:
                # Brackets cover ACC/IN1 and their two kernel argument cells.
                for top in (150, 457):
                    fig.parts.append(f'<path d="M {x+451} {top} h 10 v 56 h -10" '
                                     'fill="none" stroke="#27617b" stroke-width="2"/>')
                fig.arrow([(x + 462, 485), (x + 495, 485), (x + 495, 178), (x + 463, 178)])
            fig.text(x + 458, 389, stage["transfer"], 16)
        if stage.get("restore"):
            fig.arrow([(x + 476, 510), (x + 491, 510), (x + 491, 744), (x + 451, 744)])
            fig.text(x + 458, 701, "POP", 15)
        if stage.get("rti"):
            fig.arrow([(x + 476, 443), (x + 491, 443), (x + 491, 744), (x + 451, 744)])
            fig.text(x + 458, 701, "RTI", 15)
    fig.text(24, 830, "Yellow: saved   Purple: PC   Blue: active registers   Gray: inactive / discarded   Solid arrows: transfers / execution   Dashed: pointers", 17)
    fig.save(name)


def syscall_entry():
    prepared = [("K", "c → caller_context", "saved"),
                ("K-1", "M[c+5] → argument", "saved"),
                ("K-2", "M[c+6] → syscall_number", "saved"),
                ("K-3", "syscall_interrupt_return address", "pc"),
                ("K-4", "free ← SP", "free")] + [
                    (f"K-{i}", "not occupied yet", "unused") for i in range(5, 8)]
    callee = prepared[:4] + [("K-4", "saved caller BAF = c", "saved"),
                            ("K-5", "first local ← BAF", "active"),
                            ("K-6", "further locals / temporaries", "unused"),
                            ("…", "free SP below allocated locals", "free")]
    columns("syscall-entry.svg", "Syscall entry: save the process, then prepare a kernel C call", [
        dict(title="1. Six registers saved", kernel=empty_kernel(), user=context(),
             regs="SP = c = S0 − 7, BAF = c\nCS/DS still user values; PC in ISR", pointer=(7, "SP/BAF")),
        dict(title="2. Kernel call prepared", kernel=prepared, user=context("1 (default result)"),
             regs="SP = K − 4, BAF = c\nCS = kernel CS, DS = kernel DS", pointer=(7, "BAF"), transfer="args", kernel_pointer=(4, "SP")),
        dict(title="3. handle_syscall prologue", kernel=callee, user=context("1 (default result)"),
             regs="BAF = K − 5; SP below locals\nargs: BAF+3, +4, +5; saved c: +1", kernel_pointer=(5, "BAF"))],
        "The six process registers remain at c+1 through c+6. Only the syscall selector, argument and context pointer enter the kernel call frame. The callee saves c and changes BAF to K-5.")


def syscall_restore():
    scratch = [("K", "old caller_context argument", "unused"),
               ("K-1", "old syscall argument", "unused"),
               ("K-2", "old syscall selector", "unused"),
               ("K-3", "c (reschedule-check argument)", "saved"),
               ("K-4", "consumed restore return address", "unused"),
               ("K-5", "discarded C frame", "unused"),
               ("…", "discarded temporaries", "unused"),
               ("", "no process register frame here", "unused")]
    columns("syscall-restore.svg", "Normal syscall restoration: the registers come from the user stack", [
        dict(title="1. Reschedule check returned", kernel=scratch, user=context("syscall result"),
             regs="SP = K − 4, BAF = c\nCS/DS = kernel; boundary = kernel", pointer=(7, "BAF"), kernel_pointer=(4, "SP")),
        dict(title="2. Select process stack", kernel=scratch, user=context("syscall result"),
             regs="MOVE BAF SP → SP=c, BAF=c\nBoundary helper returns here; CS/DS=kernel", pointer=(7, "SP/BAF")),
        dict(title="3. Six POPs restore registers", kernel=scratch, user=context("syscall result", consumed=True),
             regs="SP = c+6; BAF = saved user BAF\nIN2 = result; DS/CS = saved user values", pointer=(1, "SP"), restore=True),
        dict(title="4. RTI consumes saved PC", kernel=scratch, user=context("syscall result", returned=True),
             regs="SP = c+7 = S0; PC = P+1\nBoundary = process; execution resumes", pointer=(0, "SP"), rti=True)],
        "MOVE BAF SP discards the kernel call frame. A C helper writes the process boundary on the user stack, then six POPs restore the registers and RTI reads M[c+7].")


def timer_entry():
    kernel_call = [("K", "timer_interrupt_after_reschedule_request", "pc"),
                   ("K-1", "saved c in helper prologue", "saved"),
                   ("K-2", "helper locals / free SP", "free")] + [
                       (f"K-{i}", "not occupied by this helper", "unused") for i in range(3, 8)]
    dispatch = [("K", "c → caller_context argument", "saved"),
                ("K-1", "0: unreachable return address", "pc"),
                ("K-2", "free ← SP", "free")] + [
                    (f"K-{i}", "not occupied yet", "unused") for i in range(3, 8)]
    columns("timer-entry.svg", "Timer process path: preserve the interrupted frame, then schedule", [
        dict(title="1. Save, then classify PC", kernel=empty_kernel(), user=context(),
             regs="SP = c; BAF still interrupted BAF\nCS/DS = kernel; ACC = M[c+7] − DS", pointer=(7, "SP")),
        dict(title="2. Switch stack, request", kernel=kernel_call, user=context(),
             regs="SP first = K; BAF first = c\nC helper: BAF = K−2; request = true", kernel_pointer=(2, "BAF")),
        dict(title="3. Dispatcher call prepared", kernel=dispatch, user=context(),
             regs="SP = K−2, BAF = c\nNext C prologue: saved c at K−2; BAF=K−3", pointer=(7, "BAF"), transfer="c", kernel_pointer=(2, "SP"))],
        "On the user branch BAF preserves c while SP switches to K. The request helper returns with BAF=c, then the dispatcher copies the six saved registers into the PCB activation. The kernel branch instead retains the interrupted stack.")


def borrowed_stack():
    unused = [("K", "not reset or selected by ISR", "unused")] + [
        (f"K-{i}", "live kernel work, if interrupted", "unused") for i in range(1, 8)]
    called = context()
    called[7:] = [("c", "uart/dma_interrupt_return address", "pc"),
                  ("c-1", "saved caller BAF = c", "saved"),
                  ("c-2", "C locals / free SP ← BAF", "active")]
    columns("interrupt-borrowed-stack.svg", "UART / DMA: keep the interrupted stack and return to the same context", [
        dict(title="1. Save and call C handler", kernel=unused, user=called,
             regs="Before C: BAF=c, SP=c−1; CS/DS=kernel\nC prologue: BAF=c−2; SP below locals", pointer=(9, "BAF")),
        dict(title="2. C returns; restore frame", kernel=unused, user=context(consumed=True),
             regs="C returned: BAF=c; MOVE BAF SP → c\nSix POPs: SP → c+6; segments restored", pointer=(1, "SP"), restore=True),
        dict(title="3. RTI resumes context", kernel=unused, user=context(returned=True),
             regs="SP = c+7 = S0; PC = P+1\nBoundary unchanged throughout", pointer=(0, "SP"), rti=True)],
        "UART and DMA use identical save/call/restore sequences. Their C return address is at c and their saved caller BAF at c-1 below the displayed register frame. If kernel work was interrupted, that same frame is on the kernel stack rather than the user stack.")


def memory_map():
    f = Figure(1640, 660, "Interrupt-controller initialization in the RETI memory map",
               "EPROM, periphery and SRAM in address order. Two int[3] arrays in kernel .data write mapping cells 3-5 and priority cells 6-8. The separate function-pointer table occupies .ivt.")
    f.text(24, 32, "Interrupt-controller initialization: global arrays in SRAM → six periphery cells", 23, True)
    f.text(24, 68, "Increasing absolute addresses →   Layout widths are schematic", 18)
    f.box(24, 90, 205, 535, "unused")
    f.text(36, 120, "EPROM", 23, True)
    f.text(36, 154, "0x00000000\n… 0x3fffffff\n\nBootloader", 18)
    f.box(249, 90, 530, 535, "free")
    f.text(263, 120, "Periphery · 0x40000000 … 0x7fffffff", 20, True)
    f.text(267, 161, "… UART cells 0–2 …", 18)
    labels = ["timer mapping = 1", "DMA/custom mapping = 4", "UART mapping = 2",
              "timer priority = 1", "DMA/custom priority = 1", "UART priority = 2"]
    for i, label in enumerate(labels):
        f.box(264, 188+i*49, 480, 49, "active")
        f.text(275, 219+i*49, f"0x4000000{i+3:x}   {label}", 18)
    f.text(267, 524, "… timer, boundary, exception, DMA …", 18)
    f.text(267, 570, "255 disables a device mapping.\nInitialization writes 255/0 before assignment.", 17)
    f.box(850, 90, 766, 535, "free")
    f.text(867, 120, "SRAM · 0x80000000 … 0xffffffff", 21, True)
    f.box(868, 143, 728, 343, "kernel")
    f.text(880, 171, "Kernel region", 20, True)
    f.box(884, 185, 694, 220, "free")
    f.text(896, 213, "Kernel image", 19, True)
    f.box(896, 230, 174, 152, "pc", ".ivt\nfunction pointers\n[5]", 17)
    f.box(1070, 230, 123, 152, "unused", ".text\nISRs + C", 17)
    f.box(1193, 230, 371, 152, "saved", ".data · global int[3] arrays", 17)
    f.text(1204, 300, "interrupt_device_isrs\n[1, 4, 2]\ninterrupt_device_priorities\n[1, 1, 2]", 17)
    f.box(884, 417, 345, 52, "kernel", "Kernel heap", 18)
    f.box(1229, 417, 349, 52, "kernel", "Kernel stack", 18)
    f.box(868, 506, 728, 100, "unused", "Process and Shared Data Heap\nProcess images (each .text/.data/heap/stack) + shared data", 18)
    # Separate buses group the three writes without crossings through labels.
    f.arrow([(1193, 318), (1174, 318), (1174, 393), (820, 393), (820, 213), (746, 213)])
    for y in [262, 311]:
        f.arrow([(820, y), (746, y)])
    f.arrow([(1193, 362), (1180, 362), (1180, 410), (795, 410), (795, 360), (746, 360)])
    f.arrow([(795, 409), (746, 409)])
    f.arrow([(795, 410), (795, 458), (746, 458)])
    f.text(863, 645, "interrupt_controller_initialize writes the mapping and priority cells", 16)
    f.save("interrupt-controller-initialization.svg")


def timer_memory():
    f = Figure(1640, 340, "Why the timer compares the saved PC with kernel DS",
               "The kernel .text lies before .data and its DS boundary. User process .text lies in the Process and Shared Data Heap above the kernel region.")
    f.text(24, 32, "Timer classification: kernel code precedes kernel DS; user code follows it", 23, True)
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
    f.text(24, 323, "saved PC < kernel DS → kernel path", 19, True)
    f.text(974, 323, "saved PC ≥ kernel DS → process path", 19, True)
    f.save("timer-pc-memory-layout.svg")


def exception_entry():
    f = Figure(1300, 630, "CPU exception abandons the faulting stack",
               "Only a PC is saved automatically. BAF temporarily holds old CS, SP resets to the kernel stack, and the handler receives old CS minus kernel CS. No register restoration returns to the faulting context.")
    f.text(24, 32, "CPU exception: replace the faulting context instead of restoring it", 23, True)
    for i in range(2):
        x = 24 + i*650
        f.text(x, 75, ["1. Automatic entry, preserve CS", "2. Fresh kernel call frame"][i], 21, True)
        f.text(x, 113, "Kernel stack · higher addresses at top", 18, True)
        rows = [("K", "initial free cell", "free"), ("K-1", "unused", "unused"),
                ("K-2", "unused", "unused"), ("K-3", "unused", "unused")]
        if i:
            rows = [("K", "old CS − kernel CS (argument)", "saved"),
                    ("K-1", "0: unreachable return address", "pc"),
                    ("K-2", "saved BAF = old CS (C prologue)", "saved"),
                    ("K-3", "C locals / free SP ← BAF", "active")]
        cells(f, x, 135, rows, 560)
        if i:
            f.text(x+573, 223, "BAF", 14, anchor="end")
            f.arrow([(x+572, 233), (x+561, 233)], True)
        f.text(x, 297, "Faulting stack (user case shown)", 18, True)
        cells(f, x, 320, [("S0", "saved PC = faulting PC − 1", "pc"),
                         ("S0−1", "free after automatic entry", "free")], 560)
        f.box(x, 423, 560, 138, "active", [
            "SP = S0−1; BAF = old CS\nNo six-register frame is created.\nPC is already in exception entry.",
            "SP first = K; CS/DS = kernel\nC prologue: BAF=K−3; SP below locals\nBoundary: 0 during switch, then kernel\nKernel panic or process exit → dispatcher"
        ][i], 18)
    f.arrow([(595, 67), (650, 67)])
    f.text(24, 608, "Old CS is a segment value, saved before BAF becomes a C-frame pointer · no return to the fault PC", 18)
    f.save("cpu-exception-entry.svg")


def scheduled_return():
    f = Figure(1602, 875, "Scheduled return through a selected PCB activation",
               "The dispatcher reads the target PCB and boundary from its kernel call frame, sets the target SP before the boundary, restores six registers from the PCB, then uses RTI on the selected process stack.")
    f.text(24, 32, "Scheduled return: restore registers from the PCB, then PC from the selected stack", 22, True)
    for i, title in enumerate(["1. Read target and limit", "2. Select SP, then boundary", "3. Restore registers; RTI"]):
        x = 24 + 526*i
        f.text(x, 77, title, 21, True)
        if i < 2:
            f.arrow([(x+461, 69), (x+504, 69)])
        f.text(x, 117, "Kernel stack · naked-call frame", 18, True)
        cells(f, x, 136, [("q+3", "precomputed process boundary", "saved"),
                         ("q+2", "selected Process pointer = p", "saved"),
                         ("q+1", "unused C return address", "pc"),
                         ("q", "free at naked entry", "free")])
        f.text(x, 288, "Selected PCB · activation cells", 18, True)
        rows = [("p+14", "activation.ds", "saved"), ("p+13", "activation.cs", "saved"),
                ("p+12", "activation.baf", "saved"), ("p+11", "activation.sp = s", "saved"),
                ("p+10", "activation.acc", "saved"), ("p+9", "activation.in2", "saved"),
                ("p+8", "activation.in1", "saved"),
                ("p", "pid · p+1…7 omitted above", "saved")]
        cells(f, x, 310, rows)
        if i < 2:
            f.arrow([(x+462, 520), (x+451, 520)], True)
            f.text(x+463, 510, "BAF=p", 14, anchor="end")
        f.text(x, 568, "Selected user-process stack", 18, True)
        cells(f, x, 590, [("s+1", "saved PC (P)", "pc" if i < 2 else "unused"),
                         ("s", "free before RTI", "free")])
        if i == 1:
            f.arrow([(x+462, 632), (x+451, 632)], True)
            f.text(x+463, 622, "SP=s", 14, anchor="end")
        elif i == 2:
            f.arrow([(x+462, 604), (x+451, 604)], True)
            f.text(x+463, 594, "SP=s+1", 14, anchor="end")
        states = ["SP=q, BAF=p\nIN1 = process boundary\nCS/DS still kernel",
                  "SP=s before boundary write\nThen M[0x4000000a] = IN1\nBAF=p still reads the activation",
                  "CS/DS, IN1/IN2, ACC, BAF restored\nRTI: SP=s+1, PC=P+1\nResume selected process"]
        f.box(x, 690, 450, 110, "active", states[i], 17)
        if i == 2:
            f.parts.append(f'<path d="M {x+451} 310 h 10 v 196 h -10" '
                           'fill="none" stroke="#27617b" stroke-width="2"/>')
            f.arrow([(x+462, 408), (x+490, 408), (x+490, 740), (x+451, 740)])
            f.text(x+458, 675, "load", 15)
    f.text(24, 850, "Higher addresses at top · yellow: saved values · purple: PC · blue: active registers · dashed arrows: pointers", 17)
    f.save("dispatcher-scheduled-return.svg")


if __name__ == "__main__":
    memory_map()
    syscall_entry()
    syscall_restore()
    timer_entry()
    timer_memory()
    borrowed_stack()
    exception_entry()
    scheduled_return()
