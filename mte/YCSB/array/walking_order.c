
#include <stddef.h>
#include <stdint.h>

#include "slices.h"

uint32_slice_t walking_order_init(size_t size) {
  uint32_slice_t s = slices_uint32_init(size);
  uint32_slice_t buf = slices_uint32_init(size - 1);
  
  for (size_t i = 0; i < size - 1; ++i) {
    buf = slices_uint32_add(buf, i, i + 1);
  }

  uint32_t prev = 0;
  for (uint32_t i = 0; i < size - 1; ++i) {
    uint32_t next = rand() % (size - 1 - i); 
    s = slices_uint32_add(s, prev, buf.arr[next]);
    prev = s.arr[prev];

    buf = slices_uint32_remove(buf, next);
  }
  s.arr[prev] = 0;

  slices_uint32_deinit(buf);
  return s;
}

void walking_order_deinit(uint32_slice_t s) {
  slices_uint32_deinit(s);
}
