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
    # Resumable frames need two rows. The shorter exception frames fit one
    # wide row without the unused space of a second row.
    compact = len(stages) == 4
    count = 4 if compact else min(3, len(stages))
    rows = (len(stages) + count - 1) // count
    stride = 650 if compact else 880
    registers_y = 530 if compact else 754
    fig = Figure(24 + 526 * count, 60 + stride * rows, title, description)
    fig.text(24, 30, title, 23, True)
    for i, stage in enumerate(stages):
        x = 24 + (i % count) * 526
        dy = (i // count) * stride
        fig.text(x, dy + 72, stage['title'], 21, True)
        if i < len(stages)-1 and i % count < count-1:
            fig.arrow([(x + 461, dy + 64), (x + 504, dy + 64)])
        elif i < len(stages)-1:
            fig.text(24, dy + 865, 'Continue with the next numbered state in the row below ↓', 17, True)
        fig.text(x, dy + 107, 'Kernel stack · higher addresses at top', 17, True)
        cells(fig, x, dy + 122, stage['kernel'])
        fig.text(x, dy + 414, stage.get('stack', 'User-process stack') + ' · grows downward', 17, True)
        cells(fig, x, dy + 429, stage['user'])
        fig.box(x, dy + registers_y, 450, 96, 'active', stage['regs'], 17)
        for key, origin in [('pointer', 429), ('kernel_pointer', 122)]:
            if key in stage:
                row, label = stage[key]
                top = dy + origin + row * 28 + 14
                fig.text(x + 463, top - 10, label, 14, anchor='end')
                fig.arrow([(x + 460, top), (x + 451, top)], True)
        if stage.get('transfer'):
            if stage['transfer'] == 'c':
                fig.arrow([(x + 451, dy + 780), (x + 495, dy + 780),
                           (x + 495, dy + 136), (x + 451, dy + 136)])
            else:
                for top in (150, 457):
                    fig.parts.append(f'<path d="M {x+451} {dy+top} h 10 v 56 h -10" '
                                     'fill="none" stroke="#27617b" stroke-width="2"/>')
                fig.arrow([(x + 462, dy + 485), (x + 495, dy + 485),
                           (x + 495, dy + 178), (x + 463, dy + 178)])
            fig.text(x + 458, dy + 389, stage['transfer'], 16)
        if stage.get('restore') or stage.get('rti'):
            start = 443 if stage.get('rti') else 510
            fig.arrow([(x + 476, dy + start), (x + 491, dy + start),
                       (x + 491, dy + 790), (x + 451, dy + 790)])
            fig.text(x + 458, dy + 738, 'RTI' if stage.get('rti') else 'POP', 15)
    fig.text(24, 40 + stride * rows,
             'Yellow: saved   Purple: PC   Blue: active registers   Gray: discarded   Solid arrows: transfers / execution   Dashed: pointers', 17)
    fig.save(name)


def helper_kernel(return_name, saved_baf='c'):
    return [('K', return_name, 'pc'), ('K-1', f'saved caller BAF = {saved_baf}', 'saved'),
            ('K-2', 'free at helper prologue ← BAF/SP', 'free'),
            ('…', 'nested calls / temporaries below', 'unused')]


def syscall_entry():
    arguments = [('K', 'c → caller_context', 'saved'),
                 ('K-1', 'M[c+5] → argument', 'saved'),
                 ('K-2', 'M[c+6] → syscall_number', 'saved'),
                 ('K-3', 'free ← SP', 'free')]
    prepared = arguments[:3] + [('K-3', 'syscall_interrupt_return address', 'pc'),
                                ('K-4', 'free ← SP', 'free')]
    callee = prepared[:4] + [('K-4', 'saved caller BAF = c', 'saved'),
                            ('K-5', 'free at C prologue ← BAF/SP', 'free'),
                            ('…', 'expression temporaries below', 'unused')]
    columns('syscall-entry.svg', 'Syscall entry: save the process, then prepare a kernel C call', [
        dict(title='1. Save interrupted context', kernel=empty_kernel(), user=context(),
             regs='SP=c=S0−7; BAF still user BAF\nCS/DS still user; PC in syscall ISR\nM[c+7]=INT PC; six registers saved', pointer=(7, 'SP')),
        dict(title='2. Select fresh kernel stack', kernel=empty_kernel(), user=context(),
             regs='BAF=c; IN1=0 → boundary=0\nCS/DS=kernel; SP=K\nNext: activate_kernel_stack_boundary', pointer=(7, 'BAF'), kernel_pointer=(0, 'SP')),
        dict(title='3. Temporary boundary call', kernel=helper_kernel('boundary-call continuation'), user=context(),
             regs='Prologue: BAF=SP=K−2; M[K−1]=c\nNested calls then write kernel boundary\nEpilogue restores BAF=c, SP=K', kernel_pointer=(2, 'BAF')),
        dict(title='4. Copy syscall arguments', kernel=arguments, user=context(),
             regs='BAF=c; SP=K−3; CS/DS=kernel\nIN2=M[c+5] → PUSH, then M[c+6] → PUSH\nOriginal saved IN2 still at c+4', pointer=(7, 'BAF'), kernel_pointer=(3, 'SP'), transfer='args'),
        dict(title='5. Set result; prepare return', kernel=prepared, user=context('1 (default result)'),
             regs='IN2=1 → M[c+4]; BAF=c; SP=K−4\nACC=handle_syscall address → PC\nReturn continuation is at K−3', pointer=(7, 'BAF'), kernel_pointer=(4, 'SP')),
        dict(title='6. handle_syscall prologue', kernel=callee, user=context('1 (default result)'),
             regs='Prologue: BAF=SP=K−5; no C locals\nargs: BAF+3, +4, +5; saved c at +1\nExpressions use cells below this SP', kernel_pointer=(5, 'BAF'))],
        'The six process registers and interrupt PC stay on the user stack. The kernel boundary helper temporarily saves c, then restores it before argument copies. IN2 is overwritten only after argument and selector have been pushed. The C prologue saves c again at K-4.')


def syscall_restore():
    scratch = [('K', 'old caller_context argument', 'unused'),
               ('K-1', 'old syscall argument', 'unused'),
               ('K-2', 'old syscall selector', 'unused'),
               ('K-3', 'c (reschedule-check argument)', 'saved'),
               ('K-4', 'consumed restore return address', 'unused'),
               ('K-5', 'discarded C frame', 'unused'),
               ('…', 'discarded temporaries', 'unused')]
    helper = context('syscall result')[:7] + [
        ('c', 'boundary-call continuation address', 'pc'),
        ('c-1', 'saved caller BAF = c', 'saved'),
        ('c-2', 'free at helper prologue ← BAF/SP', 'free'),
        ('…', 'nested boundary calls below', 'unused')]
    columns('syscall-restore.svg', 'Normal syscall restoration: the registers come from the user stack', [
        dict(title='1. Reschedule check returned', kernel=scratch, user=context('syscall result'),
             regs='SP=K−4; BAF=c\nCS/DS and boundary still kernel\nResult is safe at M[c+4]', pointer=(7, 'BAF'), kernel_pointer=(4, 'SP')),
        dict(title='2. Select process stack', kernel=scratch, user=context('syscall result'),
             regs='MOVE BAF SP → SP=c; BAF=c\nCS/DS still kernel\nBoundary still kernel before C call', pointer=(7, 'SP/BAF')),
        dict(title='3. Temporary boundary call', kernel=scratch, user=helper,
             regs='Prologue: BAF=SP=c−2; saved c at c−1\nResult intact at c+4; CS/DS=kernel\nNested calls then write process boundary', pointer=(9, 'BAF')),
        dict(title='4. Helper epilogue returned', kernel=scratch, user=context('syscall result'),
             regs='BAF=c, SP=c; boundary=process\nCS/DS still kernel\nTemporary C cells are no longer live', pointer=(7, 'SP/BAF')),
        dict(title='5. Restore six registers', kernel=scratch, user=context('syscall result', consumed=True),
             regs='SP=c+6; BAF=saved user BAF\nIN2=result; CS/DS=saved user values\nOnly saved PC remains live at c+7', pointer=(1, 'SP'), restore=True),
        dict(title='6. RTI consumes saved PC', kernel=scratch, user=context('syscall result', returned=True),
             regs='SP=c+7=S0; PC=P+1\nBoundary remains process\nResume instruction after INT 0', pointer=(0, 'SP'), rti=True)],
        'SP first leaves the kernel call frame for c. The process-boundary C helper then changes BAF to c-2 and saves c at c-1 before restoring both pointers. POP BAF restores the original user frame pointer, and RTI consumes the PC at c+7.')


def timer_entry():
    dispatch = [('K', 'c → caller_context argument', 'saved'),
                ('K-1', '0: unreachable return address', 'pc'),
                ('K-2', 'free ← SP', 'free')]
    callee = dispatch[:2] + [('K-2', 'saved caller BAF = c', 'saved'),
                            ('K-3', 'first local ← BAF', 'active'),
                            ('…', 'locals / temporaries, then free SP', 'unused')]
    columns('timer-entry.svg', 'Timer process path: preserve the interrupted frame, then schedule', [
        dict(title='1. Save, then classify PC', kernel=empty_kernel(), user=context(),
             regs='SP=c; BAF still interrupted BAF\nCS/DS=kernel; ACC=M[c+7]−DS\nNonnegative → process branch', pointer=(7, 'SP')),
        dict(title='2. Select fresh kernel stack', kernel=empty_kernel(), user=context(),
             regs='BAF=c; IN1=0 → boundary=0\nSP=K; CS/DS already kernel\nNext: activate_kernel_stack_boundary', pointer=(7, 'BAF'), kernel_pointer=(0, 'SP')),
        dict(title='3. Temporary boundary call', kernel=helper_kernel('boundary-call continuation'), user=context(),
             regs='Prologue: BAF=SP=K−2; saved c at K−1\nNested calls then write kernel boundary\nEpilogue restores BAF=c, SP=K', kernel_pointer=(2, 'BAF')),
        dict(title='4. Record scheduling request', kernel=helper_kernel('timer after-request continuation'), user=context(),
             regs='Request-helper BAF=K−2, SP=K−2\nreschedule_requested=true\nEpilogue restores BAF=c, SP=K', kernel_pointer=(2, 'SP/BAF')),
        dict(title='5. Dispatcher call prepared', kernel=dispatch, user=context(),
             regs='SP=K−2, BAF=c; CS/DS=kernel\nPUSH c, then unreachable return 0\nNext: dispatcher_switch_from_context', pointer=(7, 'BAF'), transfer='c', kernel_pointer=(2, 'SP')),
        dict(title='6. Save activation in C', kernel=callee, user=context(),
             regs='C prologue: BAF=K−3; SP below locals\ncaller_context=c is at BAF+3\nCopy c[1..6] into current PCB activation', kernel_pointer=(3, 'BAF'))],
        'The user branch preserves c in BAF, disables checking while SP switches, and temporarily creates two helper frames on the kernel stack before dispatching. Saved register cells stay on the process stack until copied to its PCB. The kernel branch keeps its interrupted stack instead.')


def borrowed_stack():
    unused = [('K', 'not reset or selected by this ISR', 'unused'),
              ('…', 'kernel frames, if kernel interrupted', 'unused')]
    called = context()[:7] + [('c', 'uart/dma_interrupt_return address', 'pc'),
                             ('c-1', 'saved caller BAF = c', 'saved'),
                             ('c-2', 'C locals / free SP ← BAF', 'active'),
                             ('…', 'nested calls / temporaries below', 'unused')]
    columns('interrupt-borrowed-stack.svg', 'UART / DMA: keep the interrupted stack and restore the same context', [
        dict(title='1. Save interrupted registers', kernel=unused, user=context(),
             regs='SP=c=S0−7; BAF=c\nCS/DS=kernel; boundary unchanged\nNext: PUSH return address at c', pointer=(7, 'SP/BAF')),
        dict(title='2. Call device C handler', kernel=unused, user=called,
             regs='Before C: SP=c−1; BAF=c\nC frame: BAF=c−2; locals/temps below\nUART: 4 locals; DMA: 0 locals', pointer=(9, 'BAF')),
        dict(title='3. Return to saved frame', kernel=unused, user=context(),
             regs='C epilogue: BAF=c, SP=c\nMOVE BAF SP keeps SP=c\nCS/DS=kernel; saved frame still live', pointer=(7, 'SP/BAF')),
        dict(title='4. Restore six registers', kernel=unused, user=context(consumed=True),
             regs='Six POPs: SP=c+6; BAF=original BAF\nCS/DS and general registers restored\nSaved PC still live at c+7', pointer=(1, 'SP'), restore=True),
        dict(title='5. RTI resumes context', kernel=unused, user=context(returned=True),
             regs='SP=c+7=S0; PC=P+1\nBoundary unchanged throughout\nResume user code or interrupted kernel work', pointer=(0, 'SP'), rti=True)],
        'UART and DMA have identical stack mechanics. The example shows user code interrupted. For a kernel interruption, all displayed active cells belong to the live kernel stack. Separate states preserve c before POP BAF replaces it with the original frame pointer. The timer kernel return shares states 4 and 5, with SP already equal to c.')


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
    old = [('S0', 'saved PC = faulting PC − 1', 'pc'),
           ('S0−1', 'free after automatic entry', 'free')]
    helper = helper_kernel('boundary-call continuation', 'old CS')
    abandoned = [(address, value, 'unused') for address, value, _ in old]
    call = [('K', 'old CS − kernel CS (argument)', 'saved'),
            ('K-1', '0: unreachable return address', 'pc'),
            ('K-2', 'saved caller BAF = old CS', 'saved'),
            ('K-3', 'local cause ← BAF', 'active'),
            ('K-4', 'local kernel_exception', 'active'),
            ('K-5', 'free SP after reserving two locals', 'free'),
            ('…', 'expression temporaries and calls', 'unused')]
    columns('cpu-exception-entry.svg', 'CPU exception: abandon the faulting context and prepare a kernel handler', [
        dict(title='1. Preserve interrupted CS', kernel=empty_kernel(), user=old, stack='Faulting user-process stack',
             regs='SP=S0−1; BAF=old CS (a value)\nOnly PC was saved automatically\nNo six-register resumable frame', pointer=(1, 'SP')),
        dict(title='2. Select fresh kernel stack', kernel=empty_kernel(), user=abandoned, stack='Abandoned user-process stack',
             regs='IN1=0 → boundary=0; SP=K\nCS/DS=kernel; BAF still old CS\nThe old stack is no longer used', kernel_pointer=(0, 'SP')),
        dict(title='3. Temporary boundary call', kernel=helper, user=abandoned, stack='Abandoned user-process stack',
             regs='Prologue: BAF=SP=K−2; old CS at K−1\nNested calls then write kernel boundary\nEpilogue: SP=K, BAF=old CS', kernel_pointer=(2, 'BAF')),
        dict(title='4. Enter exception C handler', kernel=call, user=abandoned, stack='Abandoned user-process stack',
             regs='Difference is pushed before C uses BAF\nC prologue: BAF=K−3; SP=K−5\nKernel panic or process exit → dispatcher', kernel_pointer=(3, 'BAF'))],
        'The user-fault case is shown. BAF holds old CS, not a pointer, until a C prologue uses it. The temporary boundary helper saves and restores that value before it is used for the CS difference. No register frame or interrupt-return path is restored for the faulting context.')


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
