#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <stdio.h>

#include "slices.h"

static void swap(uint32_t *arr, uint32_t i, uint32_t j) {
  uint32_t tmp = arr[i];
  arr[i] = arr[j];
  arr[j] = tmp;
}

uint32_slice_t slices_uint32_init(size_t cap) {
  assert(cap > 0);
  
  uint32_t *arr = malloc(cap * sizeof(*arr));
  if (!arr) {
    panic("OOM");
  }

  return (uint32_slice_t) {
    .arr = arr,
    .capacity = cap, 
    .size = 0
  };
}

void slices_uint32_deinit(uint32_slice_t s) {
  free(s.arr);
}

uint32_slice_t slices_uint32_remove(uint32_slice_t slice, size_t idx) {
  assert(idx < slice.size);
  assert(slice.size > 0);
  assert(slice.arr != NULL);

  slice.size -= 1;
  if (slice.size == 0) {
    return slice;
  }

  // [1,2,3,4] 
  // remove idx:0 -> swap idx with last one and -1 size
  swap(slice.arr, slice.size, idx);
  return slice;
}

// assumes the idx to add was not prev added
uint32_slice_t slices_uint32_add(uint32_slice_t slice, size_t idx, uint32_t e) {
  assert(idx < slice.capacity);
  assert(idx >= 0);
  assert(slice.arr != NULL);

  slice.arr[idx] = e;
  slice.size += 1;
  return slice;
}
