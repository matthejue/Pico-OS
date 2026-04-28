#pragma once

#define HEAP_SIZE  (1024 * 256)     // heap size in words
#define NULL       ((void *)0)

struct BlockHeader {
    int size;                      // usable words in this block
    int free;                      // 1 = free, 0 = used
    struct BlockHeader *next;      // pointer to next block
};

void init_heap();
void *malloc(int size);
void free(void *ptr);
