# Waiting For a Process

This diagram focuses only on how `waitpid(pid)` queues the waiting process and
how the exiting process delivers its status.

```mermaid
sequenceDiagram
    participant W as Waiting process W
    participant WS as W waitpid() stack frame
    participant WP as W Process PCB
    participant K as Kernel wait handling
    participant TP as Target process T PCB
    participant TQ as T waiters queue

    Note over WS: status is local and request.status points to it
    W->>K: wait_for_process_by_pid(request pointer)
    K->>WP: wait_for_process_by_pid stores request.status in waiting_status_ptr
    Note over WP,WS: waiting_status_ptr points to W status variable
    K->>TP: Get pointer to T waiters queue
    TP->>TQ: sleep_on_wait_queue receives T waiters queue pointer
    TQ->>WP: sleep_on_wait_queue adds W and sets queue links
    Note over TQ: T waiters queue now contains W

    Note over TP: exit_process calls remove_process with T exit status
    TP->>TQ: remove_process reads T waiters head
    TQ->>K: T waiters head supplies W Process pointer as waiting_process
    K->>WP: waiting_process identifies W PCB and its waiting_status_ptr
    WP->>WS: remove_process writes status through waiting_status_ptr
    TP->>TQ: remove_process calls wakeup_wait_queue with T waiters queue pointer
    TQ->>WP: wakeup_wait_queue removes W and clears queue links
    WP->>W: W becomes READY and waitpid() returns status
```

`status` and `request` belong to W's suspended `waitpid()` stack frame.
`waiting_status_ptr` belongs to W's PCB and points to W's `status` variable.
The waited-on process T owns the `waiters` queue in its PCB. **The same
`T->waiters` attribute is used both times:** W's user-space `waitpid(pid)` enters
the kernel function `wait_for_process_by_pid()`, which calls
`sleep_on_wait_queue(&T->waiters)` to add W to that queue. When T exits,
`exit_process()` calls `remove_process(T, status)`, which reads waiters from
that same `T->waiters`, writes T's exit status through each waiting process's
`waiting_status_ptr`, and calls `wakeup_wait_queue(&T->waiters)` on that same
queue to remove and ready each waiter.
