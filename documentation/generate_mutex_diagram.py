"""Generate the horizontal mutex acquisition and unlock flows in section 7.3."""

from html import escape
from pathlib import Path

from diagram_style import FOCUS_FILL, FREE, INK, LINE, PANEL, TEAL, style_svg


OUTPUT = Path(__file__).resolve().parent / "images/mutex-lock-wakeup.svg"


def generate():
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="720" '
        'viewBox="0 0 1360 720" role="img" aria-labelledby="title desc">',
        '<title id="title">Mutex acquisition and unlock</title>',
        '<desc id="desc">Two horizontal flows show separate mutex_lock and '
        'mutex_unlock calls. Above, testset atomically sets the lock. False '
        'acquires it, while true sleeps on mutex.waiters. The waiting process '
        'resumes when scheduled and retries. Below, unlock clears the lock and '
        'checks mutex.waiters.head. An empty queue wakes nobody. Otherwise, '
        'the first PCB is removed and that process is woken. The dotted arrow '
        'connects wakeup to the waiting process above. Both unlock paths return.</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{TEAL}"/>'
        '</marker></defs>',
        '<rect width="1360" height="720" fill="#ffffff"/>',
        '<g font-family="Cantarell, sans-serif" '
        f'fill="{INK}" text-anchor="middle">',
    ]

    def arrow(identifier, path, *, dotted=False):
        dash = ' stroke-dasharray="4 7"' if dotted else ''
        parts.append(
            f'<path id="{identifier}" d="{path}" fill="none" '
            f'stroke="{TEAL}" stroke-width="2"{dash} '
            'marker-end="url(#arrow)"/>'
        )

    def text(x, y, value, *, size=21, bold=False, color=INK):
        weight = ' font-weight="600"' if bold else ''
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                     f'fill="{color}"{weight}>{escape(value)}</text>')

    def node(identifier, x, y, lines, fill=PANEL, *, diamond=False,
             height=96, link=None):
        parts.append(f'<g id="{identifier}">')
        if link:
            parts.append(f'<a href="../../{escape(link, quote=True)}">')
        if diamond:
            parts.append(
                f'<polygon points="{x - 125},{y} {x},{y - 75} '
                f'{x + 125},{y} {x},{y + 75}" '
                f'fill="{fill}" stroke="{LINE}" stroke-width="1.5"/>'
            )
        else:
            parts.append(
                f'<rect x="{x - 130}" y="{y - height / 2}" width="260" '
                f'height="{height}" fill="{fill}" stroke="{LINE}" stroke-width="1.5"/>'
            )
        for index, line in enumerate(lines):
            text(x, y + 7 - (len(lines) - 1) * 14 + index * 28,
                 line, bold=index == 0, size=21 if index == 0 else 20)
        if link:
            parts.append('</a>')
        parts.append('</g>')

    # Identical columns, box widths and branch spacing organize both calls.
    arrow('lock-test', 'M 310 160 H 355')
    arrow('acquired', 'M 605 160 H 650 V 100 H 700')
    arrow('contended', 'M 605 160 H 650 V 250 H 700')
    arrow('resume', 'M 960 250 H 1050')
    arrow('retry', 'M 1140 298 V 340 H 180 V 208')
    arrow('unlock-check', 'M 310 520 H 355')
    arrow('empty', 'M 605 520 H 650 V 460 H 700')
    arrow('wake', 'M 605 520 H 650 V 610 H 1050')
    arrow('wake-resume', 'M 1210 546 V 298', dotted=True)

    text(675, 87, 'false', size=19, color=TEAL)
    text(675, 237, 'true', size=19, color=TEAL)
    text(675, 447, 'Yes', size=19, color=TEAL)
    text(675, 597, 'No', size=19, color=TEAL)
    text(670, 329, 'retry testset', size=19, color=TEAL)
    text(1260, 420, 'wakeup', size=19, color=TEAL)

    node('lock', 180, 160, ['mutex_lock()', 'call testset(&m->lock)'], '#eaf5f5',
         link='library/mutex/mutex.picoc#L18')
    node('old-value', 480, 160, ['Old lock value?'], FOCUS_FILL, diamond=True,
         link='library/mutex/mutex.picoc#L3')
    node('critical-section', 830, 100, ['Lock acquired: 0 → 1', 'enter critical section'], FREE)
    node('sleep', 830, 250, ['sleep(&m->waiters)', 'wait for wakeup'], FOCUS_FILL,
         link='library/unistd/blocking.picoc#L9')
    node('scheduled', 1180, 250, ['Waiting process resumes', 'when scheduled'])
    node('unlock', 180, 520, ['mutex_unlock()', 'm->lock = false', 'wakeup(&m->waiters)'],
         '#eaf5f5', link='library/mutex/mutex.picoc#L25')
    node('queue-empty', 480, 520, ['Queue empty?', 'm->waiters.head', '== NULL'],
         FOCUS_FILL, diamond=True, link='common/wait_queue.header#L6')
    node('no-waiter', 830, 460, ['Wake nobody', 'mutex_unlock returns'])
    node('wake-waiter', 1180, 610,
         ['Remove first PCB', 'from m->waiters', 'wake that process', 'mutex_unlock returns'],
         FREE, height=128, link='kernel/process/process.picoc#L395')

    parts.append('</g></svg>')
    OUTPUT.write_text(style_svg('\n'.join(parts) + '\n', name=OUTPUT.stem))


if __name__ == '__main__':
    generate()
