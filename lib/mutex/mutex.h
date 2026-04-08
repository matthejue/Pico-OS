#pragma once

struct mutex {
    int lock;
    int id;
};

int testset(int *lock_addr);
void mutex_init(struct mutex *m);
void mutex_lock(struct mutex *m);
void mutex_unlock(struct mutex *m);

void sleep(int id);
void wakeup(int id);
