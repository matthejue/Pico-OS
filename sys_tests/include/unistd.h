#pragma once

struct process;

struct wait_queue {
    struct process *head;
    struct process *tail;
};

void wait_queue_init(struct wait_queue *wq);
void sleep(struct wait_queue *wq);
void wakeup(struct wait_queue *wq);

void wait_queue_init(struct wait_queue *wq) {
    wq->head = 0;
    wq->tail = 0;
}

void sleep(struct wait_queue *wq) {
    if (wq == 0) {
        return;
    }

    asm("LOADIN BAF ACC -2");
    asm("INT 4");
}

void wakeup(struct wait_queue *wq) {
    if (wq == 0) {
        return;
    }

    asm("LOADIN BAF ACC -2");
    asm("INT 5");
}
