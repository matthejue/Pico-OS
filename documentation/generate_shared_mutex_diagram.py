"""Generate the parent, two workers, and shared counter in README 15.2.

Run with Python 3. Reuse the README's sharp-corner SVG style and colours.
Process boxes show responsibilities, not SRAM allocation order. Shared fields
show their initial values. Launch arrows carry arguments, blue arrows show
local pointers, and the green arrow shows the kernel entry's stored address.
"""

from generate_process_diagrams import Figure
from generate_memory_layout_diagrams import ADDRESS, ALLOCATED, FOCUS, MUTED, POINTER


def main():
    figure = Figure(
        "shared-mutex", "Parent and two children share one counter and mutex",
        "The launcher creates the named shared-memory region, maps and initializes "
        "SharedState, then loads and runs two copies of worker.bin with arguments "
        "1 <id> and 2 <id>. All three processes map the same ID, so their local "
        "shared_state pointers reach the same SharedState payload. The workers "
        "lock, increment workers, and unlock. Worker 1 also yields while holding "
        "the lock. The payload initially contains workers = 0, mutex.lock = false, "
        "and an empty mutex.waiters queue. One kernel SharedMemoryEntry stores "
        "the name shared-memory-mutex, the ID, and address of that payload. "
        "The parent waits for both children, reads the final count, and unlinks "
        "the name. Boxes show responsibilities, not physical memory placement.",
        width=1560, height=610, show_address_direction=False,
    )

    def arrow(path, colour=POINTER, dashed=False):
        style = ' stroke-dasharray="7 5"' if dashed else ""
        figure.parts.append(
            f'<path d="{path}" fill="none" stroke="{colour}" '
            f'stroke-width="2.5"{style} marker-end="url(#{colour[1:]})"/>'
        )

    figure.box(30, 140, 350, 290, MUTED)
    figure.label(205, 180, "Parent · launcher", size=25, bold=True,
                 link="test/shared_memory_mutex/launcher.picoc#L35")
    for y, text, link in (
        (227, "shm_open(name, size)", "library/sys/mman/mman.picoc#L15"),
        (267, "mmap(id) + initialize", "test/shared_memory_mutex/launcher.picoc#L47"),
        (307, "load + run both children", "test/shared_memory_mutex/launcher.picoc#L53"),
        (347, "waitpid for both children", "library/sys/wait/wait.picoc#L14"),
        (395, "Read count + shm_unlink", "test/shared_memory_mutex/launcher.picoc#L60"),
    ):
        figure.label(205, y, text, size=21, link=link)

    figure.box(560, 155, 390, 255, ALLOCATED, FOCUS, 2)
    figure.label(755, 195, "One shared region", size=25, bold=True)
    figure.label(755, 231, "SharedState", size=23, bold=True,
                 link="test/shared_memory_mutex/shared.header#L5")
    for y, text, link in (
        (273, "workers = 0", "test/shared_memory_mutex/shared.header#L6"),
        (321, "mutex.lock = false", "library/mutex/mutex.header#L7"),
        (369, "mutex.waiters = empty queue", "library/mutex/mutex.header#L8"),
    ):
        figure.box(575, y - 29, 360, 45, "white")
        figure.label(755, y, text, size=21, link=link)

    for number, y in ((1, 60), (2, 320)):
        figure.box(1150, y, 380, 185, MUTED)
        figure.label(1340, y + 37, f"Child {number} · worker", size=25, bold=True,
                     link="test/shared_memory_mutex/worker.picoc#L10")
        figure.label(1340, y + 74, f"argv: worker.bin, {number}, <id>", size=20,
                     link="test/shared_memory_mutex/worker.picoc#L13")
        figure.label(1340, y + 112, "mmap(id)", size=22,
                     link="library/sys/mman/mman.picoc#L23")
        figure.label(1340, y + 149, "lock → increment → unlock", size=21,
                     link="test/shared_memory_mutex/worker.picoc#L14")
        if number == 1:
            figure.label(1340, y + 174, "yield while holding the lock", size=17,
                         link="test/shared_memory_mutex/worker.picoc#L17")

    # Launch paths stay outside the shared region and its address arrow.
    arrow("M 205 140 V 25 H 1100 V 97 H 1150", FOCUS, dashed=True)
    figure.label(660, 18, "load + run · arguments: 1 <id>", size=20, color=FOCUS,
                 link="test/shared_memory_mutex/launcher.picoc#L55")
    arrow("M 205 430 V 580 H 1340 V 505", FOCUS, dashed=True)
    figure.label(660, 572, "load + run · arguments: 2 <id>", size=20, color=FOCUS,
                 link="test/shared_memory_mutex/launcher.picoc#L56")

    arrow("M 380 267 H 560")
    figure.label(470, 251, "shared_state", size=17, color=POINTER,
                 link="test/shared_memory_mutex/launcher.picoc#L39")
    arrow("M 1150 172 H 1035 V 267 H 950")
    figure.label(1045, 157, "shared_state", size=17, color=POINTER,
                 link="test/shared_memory_mutex/worker.picoc#L11")
    arrow("M 1150 432 H 1035 V 369 H 950")
    figure.label(1045, 455, "shared_state", size=17, color=POINTER,
                 link="test/shared_memory_mutex/worker.picoc#L11")

    figure.box(560, 465, 390, 80, MUTED)
    figure.label(755, 492, "Kernel · SharedMemoryEntry", size=21, bold=True,
                 link="kernel/shared_memory.header#L8")
    figure.label(755, 524, 'name: "shared-memory-mutex" · id', size=18,
                 link="kernel/shared_memory.header#L9")
    arrow("M 755 465 V 410", ADDRESS)
    figure.label(803, 445, "address", size=18, color=ADDRESS,
                 link="kernel/shared_memory.header#L11")
    figure.save()


if __name__ == "__main__":
    main()
