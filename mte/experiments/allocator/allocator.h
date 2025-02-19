
#ifndef ALLOCATOR_H
#define ALLOCATOR_H

#include <stddef.h>

void *alloc(size_t num_bytes);

void alloc_free(void *ptr, size_t num_bytes);

#endif
