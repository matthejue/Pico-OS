#pragma once

struct process;

struct wait_queue {
    struct process *head;
    struct process *tail;
};

void sleep(struct wait_queue *wq);
void wakeup(struct wait_queue *wq);
