#include <linux/mman.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

static void benchmark(uint32_t *arr, size_t len, size_t steps) {
  for (size_t i = 0; i < steps; i++) {
    arr[(i * 16) & (len - 1)] += 1;
  }
}

int main(int argc, char *args[]) {
  if (argc != 3) {
    printf("Usage: %s <len> <steps>\n", args[0]);
  }

  size_t len = atoll(args[1]);
  size_t steps = atoll(args[2]);

  size_t size = len * sizeof(uint32_t);
  void *mem = mmap((void *)0x600000000000, size, PROT_READ | PROT_WRITE,
                   MAP_ANONYMOUS | MAP_PRIVATE | MAP_FIXED, -1, 0);
  if (mem == MAP_FAILED) {
    perror("mmap");
    exit(EXIT_FAILURE);
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
