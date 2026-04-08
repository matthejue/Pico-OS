#pragma once

#define NULL ((void*)0)

// Each block on the heap starts with a header:
struct BlockHeader {
    int size;                     // usable bytes in this block
    int free;                     // 1 = free, 0 = used
    struct BlockHeader *next;     // next block in list
};

// Initialize the heap and set start/end
void init_heap(void *heap_start, int heap_size);

// Simulated sbrk(): move the program break upward
void *simple_sbrk(int increment);

// Memory allocation interface
void *simple_malloc(int size);
void simple_free(void *ptr);
