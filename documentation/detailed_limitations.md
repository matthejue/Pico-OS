# Detailed limitations

This page retains the implementation-specific limitations that were removed
from the short [`17. Limitations`](../README.md#17-limitations). It
explains the mechanisms behind them without making the overview harder to
scan.

## Blocking and child waiting

PicoOS has event-based blocking primitives, not a time-based sleep interface.
The following limitations describe the two supported waiting mechanisms.

- [`sleep()`](../library/unistd/blocking.picoc#L9) blocks the current process on
  a caller-supplied wait queue until [`wakeup()`](../library/unistd/blocking.picoc#L17)
  wakes it, it cannot wait for a specified duration.
- [`waitpid()`](../library/sys/wait/wait.picoc#L15) waits for one exact child
  PID and has no options argument or general interface for waiting on any
  child.

## Signals, job control, and terminal input

Signal delivery and terminal input use deliberately small global mechanisms.
They demonstrate the relevant operating-system concepts, but do not implement
full POSIX job control or independent terminal queues.

- Six fixed-action signals and one foreground/input owner replace full job
  control. See [`7.2 Process signals`](../README.md#72-process-signals) and
  [`12.5.1 Foreground processes, background processes, and job-control signals`](../README.md#1251-foreground-processes-background-processes-and-job-control-signals).
- One global terminal ring and wait queue serve per-process pending input
  reads, as explained in
  [`8.2 Global terminal input buffer`](../README.md#82-global-terminal-input-buffer).

## Host-backed append writes

[`O_APPEND`](../common/file.header#L15) writes first ask the host for the
current file size and then write at that offset. The positioning is therefore
not atomic if another PicoOS process or host program writes the same
host-backed file concurrently.

## Pipelines

The shell supports one sequential, file-backed pipeline per command. It has no
streaming kernel pipes. See
[`12.7 Sequential file-backed pipelines`](../README.md#127-sequential-file-backed-pipelines)
for its execution model.
