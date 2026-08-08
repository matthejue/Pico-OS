# Unhandled user input errors

The following input errors and limitations do not currently have specific
diagnostics. They are intentionally deferred because addressing them would add
parser complexity, require a wider protocol change, or change established
command behavior.

- `run` and `unload` accept a numeric PID prefix. For example, `3oops` is
  interpreted as PID 3, and `unload 3 extra` ignores the trailing text. Fixing
  this cleanly requires a shared checked integer parser and stricter handling
  of the arguments accepted by each built-in.
- Shell input and expanded argument strings are silently limited to their
  fixed-size buffers. Reporting truncation would require propagating a distinct
  result through line reading and variable expansion.
- `export` accepts empty or unusual names, whitespace in names, and additional
  `=` characters or assignments as part of the value. The environment library
  currently permits these names, so enforcing a grammar only in the shell
  needs a deliberate definition of valid PicoOS environment names.
- Redirection is recognized only when `>` is preceded by whitespace. Thus
  `echo.bin hello>file` treats `hello>file` as an argument. Supporting compact
  redirection belongs in a more complete token parser.
- A redirection target that the emulator cannot create is not reported back to
  PicoOS. The UART output-selection protocol has no success response, so the
  kernel returns a file descriptor even when the emulator could not open the
  host file. Fixing this requires coordinated kernel and emulator changes.
- `kill.bin` checks the resulting PID and signal ranges, but `atoi()` cannot
  report nondigit input. Some malformed strings can therefore still become a
  numeric value instead of producing an "invalid number" message.
- `poweroff.bin` ignores extra arguments and still shuts down. Rejecting them
  is intentionally deferred because the command is currently defined with a
  no-argument entry point and changing it was considered low priority.
- `echo.bin -n` prints `-n` as ordinary text. PicoOS `echo` intentionally has
  no option parser, so unsupported option-like arguments are not diagnosed.
- If init starts the shell without a `PATH` variable, external command lookup
  can dereference a null pointer. Diagnosing this requires deciding whether
  `PATH` is mandatory init configuration or whether the shell should provide a
  fallback search policy.
- Init restarts the shell without interpreting its `waitpid()` status. A shell
  killed, stopped, or terminated by an error therefore disappears without an
  explanation before a new shell starts. Handling this needs a defined init
  policy for normal exit, signal termination, and stopped shells.
