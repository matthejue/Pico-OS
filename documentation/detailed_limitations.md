# Detailed limitations

This page retains the implementation-specific limitations that were removed
from the short [README limitations overview](../README.md#17-limitations). It
explains the mechanisms behind them without making the overview harder to
scan.

## Blocking and child waiting

PicoOS has event-based blocking primitives, not a time-based sleep interface.
The following limitations describe the two supported waiting mechanisms.

- [`sleep()`](../library/unistd/blocking.picoc#L9) blocks the current process on
  a caller-supplied wait queue until [`wakeup()`](../library/unistd/blocking.picoc#L19)
  wakes it, it cannot wait for a specified duration.
- [`waitpid()`](../library/sys/wait/wait.picoc#L14) waits for one exact child
  PID and has no options argument or general interface for waiting on any
  child.

## Signals, job control, and terminal input

Signal delivery and terminal input use deliberately small global mechanisms.
They demonstrate the relevant operating-system concepts, but do not implement
full POSIX job control or independent terminal queues.

- [Six fixed-action signals](../README.md#64-process-signals) and one
  [foreground/input owner](../README.md#126-foreground-processes-background-processes-and-job-control-signals)
  replace full job control.
- One [global terminal ring and wait queue](../README.md#72-global-terminal-input-buffer)
  serves per-process pending input reads.

## Host-backed append writes

[`O_APPEND`](../common/file.header#L15) writes first ask the host for the
current file size and then write at that offset. The positioning is therefore
not atomic if another PicoOS process or host program writes the same
host-backed file concurrently.

## Pipelines

The shell supports one [sequential, file-backed pipeline](../README.md#128-sequential-file-backed-pipelines)
per command. It has no streaming kernel pipes.
