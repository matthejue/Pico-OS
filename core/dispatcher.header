#pragma once

struct process;

struct dispatcher {
    struct process *from;
    struct process *to;
    int switch_requested;
};

struct dispatcher *os_dispatcher();

void dispatcher_init();
void dispatcher_save_context(
    struct process *process,
    int *stack_pointer,
    int program_counter,
    int status_word,
    int acc,
    int in1,
    int in2,
    int ds
);
void dispatcher_prepare_switch(struct process *from_process, struct process *next_process);
struct process *dispatcher_target_process();
