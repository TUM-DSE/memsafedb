#include <assert.h>
#include <linux/mman.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

extern void benchmark(uint32_t *arr, size_t len, size_t steps);

#define MB32 (1 << 26)

int main(int argc, char *args[]) {
  if (argc != 3) {
    printf("Usage: %s <len> <steps>\n", args[0]);
    exit(EXIT_FAILURE);
  }

  size_t len = atoll(args[1]);
  size_t steps = atoll(args[2]);

  size_t size = len * sizeof(uint32_t);
  // we do at least 32MB
  if ((size / MB32) * MB32 != size) {
    size = (size / MB32 + 1) * MB32;
  }
  assert(size % MB32 == 0);
  uint32_t *mem = mmap((void *)0x600000000000, size, PROT_READ | PROT_WRITE,
                       MAP_ANONYMOUS | MAP_PRIVATE | MAP_FIXED, -1, 0);
  if (mem == MAP_FAILED) {
    perror("mmap");
    exit(EXIT_FAILURE);
  }

  // ensure every page is loaded befor benchmarking
  size_t idx = 0;
  while (idx < len) {
    mem[idx] += 1;
    idx += 1024 / sizeof(uint32_t);
  }

  struct timespec s, e;

  clock_gettime(CLOCK_MONOTONIC_RAW, &s);
  benchmark(mem, len, steps);
  clock_gettime(CLOCK_MONOTONIC_RAW, &e);

  uint64_t duration = 1e9 * (e.tv_sec - s.tv_sec) + (e.tv_nsec - s.tv_nsec);

  if (munmap(mem, size) == -1) {
    perror("Failed to clear memeory region");
    exit(EXIT_FAILURE);
  }

  // len;steps;duration
  printf("%ld;%ld;%ld\n", len, steps, duration);
}
