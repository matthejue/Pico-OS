#include "simple_malloc.h"

#include<stdio.h>
int main() {
    init_heap();

    int *a = (int *)simple_malloc(10);
    int *b = (int *)simple_malloc(20);

    printf(" %d", a);
    printf(" %d", b);

    simple_free(a);
    simple_free(b);

    return 0;
}

