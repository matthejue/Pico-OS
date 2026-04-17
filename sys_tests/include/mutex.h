#pragma once

#include "./unistd.h"

struct mutex {
    int lock;
    struct wait_queue waiters;
};

int testset(int *lock_addr);
void mutex_init(struct mutex *m);
void mutex_lock(struct mutex *m);
void mutex_unlock(struct mutex *m);

int testset(int *lock_addr) {
    int old;
    asm("LOADIN BAF IN2 -2");
    asm("TSL IN2 ACC 0");
    asm("STOREIN BAF ACC -3");
    return old;
}

void mutex_init(struct mutex *m) {
    m->lock = 0;
    wait_queue_init(&(m->waiters));
    return;
}

void mutex_lock(struct mutex *m) {
    while (testset(&(m->lock))) {
        sleep(&(m->waiters));
    }
    return;
}

void mutex_unlock(struct mutex *m) {
    m->lock = 0;
    wakeup(&(m->waiters));
    return;
}
