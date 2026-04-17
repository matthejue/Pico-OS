#pragma once

#include "../unistd/unistd.h"

struct mutex {
    int lock;
    struct wait_queue waiters;
};

int testset(int *lock_addr);
void wait_queue_init(struct wait_queue *wq);
void mutex_init(struct mutex *m);
void mutex_lock(struct mutex *m);
void mutex_unlock(struct mutex *m);
