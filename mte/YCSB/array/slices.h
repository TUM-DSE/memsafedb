
#ifndef SLICES_H
#define SLICES_H

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>


#define panic(msg) do { \
  fprintf(stderr, "PANIC: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
  abort(); \
} while (0)

typedef struct {
  uint32_t *arr;
  size_t capacity;
  size_t size;
} uint32_slice_t;


uint32_slice_t 
slices_uint32_init(size_t cap);

void 
slices_uint32_deinit(uint32_slice_t s);

uint32_slice_t 
slices_uint32_remove(uint32_slice_t slice, size_t idx);

uint32_slice_t 
slices_uint32_add(uint32_slice_t slice, size_t idx, uint32_t e);

#endif

