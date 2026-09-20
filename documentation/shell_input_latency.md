# Why typed characters can appear late

This note records the shell-delay measurement used to choose PicoOS's
5,000-instruction timer interval.

## Simple measurement method

For the character-delay check, PicoOS started a second program in the
background. That program only ran an endless empty loop (`while (1) {}`), with
no input or output, so it kept using the CPU whenever PicoOS gave it a turn.
The shell therefore had to wait for a timer interrupt before it could show a
typed character. For each timer value, the host script did the following:

1. Waited until the `PicoOS>` prompt was visible.
2. Started its clock and sent one normal letter to the emulator input.
3. Read the emulator output until the shell printed that same letter, then
   stopped the clock.

The clock therefore measures everything a user sees: sending the character,
the emulator, PicoOS, and the shell echo. The check was repeated 20 times for
each timer value. The table uses the median: after sorting the 20 delays, it is
the average of the two middle values. This stops one unusually slow or fast
result from deciding the value. The complete script is
[`measure_shell_input_delay.py`](measure_shell_input_delay.py).

The script records the start and end with Python's `time.perf_counter_ns()`.
This clock returns nanoseconds; one millisecond is 1,000,000 nanoseconds. It
therefore subtracts the two values and divides by 1,000,000 to get
milliseconds. The exact conversion is
`(finished_ns - started_ns) / 1_000_000`.

The script does not inspect the terminal window or its pixels. Before it sends
a letter, it remembers where the current emulator output ends. It then reads
new output bytes until they contain the same letter. Finding that byte is what
stops the clock, so the result is the time until PicoOS has echoed the
character.

## Reproducing the measurement

The benchmark files are kept beside this note. Copy
[`timer-set.picoc`](timer-set.picoc) and
[`timer-spin.picoc`](timer-spin.picoc) to `user/`, then build them and run the
script from the repository root:

```sh
cp documentation/timer-set.picoc user/timer-set.picoc
cp documentation/timer-spin.picoc user/timer-spin.picoc
make binary/user/timer-set.bin binary/user/timer-spin.bin
python documentation/measure_shell_input_delay.py
```

[`timer-set.picoc`](timer-set.picoc) writes its command-line value to timer
register 9. [`timer-spin.picoc`](timer-spin.picoc) is the background loop. The
script starts the emulator without artificial UART waiting (`-w 0`) and starts
the kernel directly. The timer values are counts of emulator instructions, not
milliseconds.

## Results and selected value

The table and figure show the same measurements. Smaller times are better.

| Timer interval (instructions) | Character appears after (ms) |
| ---: | ---: |
| 1,000 | 109.1 |
| 3,000 | 108.3 |
| **5,000 (selected)** | **106.6** |
| 10,000 | 106.4 |

![Measured character delay for each timer interrupt interval](images/timer_interval_measurements.png)

**PicoOS uses 5,000 instructions because it was the best balance.** The
measured character delay was practically the same as at 10,000, but a
10,000-instruction interval can make the shell wait longer before the running
program is paused.

Short intervals give programs turns more often, which can help a simple game,
but make PicoOS spend more time switching programs. Long intervals reduce that
work but make the shell and other programs wait longer. The value
[`INTERRUPT_CONTROLLER_TIMER_INTERVAL`](../kernel/interrupt_controller.header#L18)
is therefore a practical middle ground.
