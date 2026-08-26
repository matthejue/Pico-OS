# Process loading

PicoOS has two process-loading paths in
`kernel/process/process_loader.picoc`:

- `load_process()` loads PID 1 as one continuous UART stream during boot,
  before the timer and normal scheduling are active
- `load_process_chunk()` services userspace syscall 3 in bounded steps so the
  non-preemptive kernel does not hold the CPU for a complete executable

## Userspace loading sequence

The public `load(path)` wrapper keeps its normal synchronous interface. It
repeats syscall 3 while the kernel returns the private
`SYSCALL_LOAD_PROCESS_CONTINUE` value. It requests the next chunk directly.
When a timer expires during a chunk, the timer ISR records a reschedule request
and the syscall-return path dispatches before this process resumes in
userspace.

The first syscall:

1. normalizes and copies the binary path
2. requests the host file size
3. reads the five-word binary header with one `read-range` request
4. validates the heap and stack layout
5. reserves the complete process-memory region with `pmalloc()`
6. stores a `struct ProcessLoad` pointer in the calling PCB

Later syscalls each request and copy at most 1 KiB. Every chunk is an
independent `<ESC>read-range ...<ESC>/` request and response, so host-file
operations from another scheduled process cannot become mixed with an
unfinished binary stream.

After the last chunk, `finish_process_load()` creates and appends the new
`PROCESS_STATE_NEW` PCB and returns its PID. The incomplete image is never
visible as a process. `run()` remains a separate operation that constructs the
initial stack and changes the process to `READY`.

## Ownership and failure cleanup

`struct ProcessLoad` owns the normalized host path, the original binary path,
the header values, transfer progress, loading-bar progress, and the reserved
process-memory address. The loading process owns this structure through its
`pending_load` PCB field.

`cancel_process_load()` frees the reserved image, both copied paths, and the
continuation structure after a transfer failure. `remove_process()` calls the
same helper, so killing a process between chunks cannot leak its partial image.
Once loading succeeds, the child PCB owns the completed image and the temporary
continuation state is freed without releasing that image.
