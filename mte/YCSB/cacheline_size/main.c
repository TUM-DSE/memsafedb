#include <linux/mman.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

extern void benchmark(uint32_t *arr, size_t size, size_t stide);

static uint32_t *setup(size_t len) {
#ifdef MTE
  unsigned long hwcap2 = getauxval(AT_HWCAP2);

  /* check if MTE is present */
  if (!(hwcap2 & HWCAP2_MTE)) {
    panic("MTE is not present");
  }
#endif
  size_t size = len * sizeof(uint32_t);
  uint32_t *mem = mmap(NULL, size, PROT_READ | PROT_WRITE,
#ifdef MTE_ENABLE
                       PROT_MTE,
#endif
                       MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
  if (mem == MAP_FAILED) {
    perror("mmap");
    exit(EXIT_FAILURE);
  }

  return mem;
}

int main(int argc, char *args[]) {
  if (argc != 3) {
    fprintf(stderr, "Usage: %s <size> <stride>\n", args[0]);
    exit(EXIT_FAILURE);
  }

  size_t size = atoll(args[1]);
  size_t stride = atoll(args[2]);
  uint32_t *mem = setup(size);

  struct timespec s, e;

  clock_gettime(CLOCK_MONOTONIC_RAW, &s);
  benchmark(mem, size, stride);
  clock_gettime(CLOCK_MONOTONIC_RAW, &e);

  uint64_t duration = 1e9 * (e.tv_sec - s.tv_sec) + (e.tv_nsec - s.tv_nsec);
  // size;stride;duration
  // throughput (T):
  //    input (I) = size/stride aka how many elements we accessed
  //    --> I = T * duration (D) -> T = (size/stride)/duration
  //          = size/(stride * duration) = T
  printf("%lu;%lu;%lu\n", size, stride, duration);
}
