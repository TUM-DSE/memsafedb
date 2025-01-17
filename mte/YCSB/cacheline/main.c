#include <assert.h>
#include <bits/time.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>
#include <x86intrin.h>

#define panic(msg)                                                             \
  do {                                                                         \
    fprintf(stderr, "PANIC: %s (%s:%d)\n", msg, __FILE__, __LINE__);           \
    abort();                                                                   \
  } while (0)

struct uint32_slice {
  uint32_t *arr;
  size_t len;
};

static struct uint32_slice uint32_slice_init(size_t size) {
  assert(size > 0);
  void *arr = mmap(NULL, sizeof(uint32_t) * size, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (arr == MAP_FAILED) {
    panic("OOM");
  }

  return (struct uint32_slice){.arr = arr, .len = size};
}

static void uint32_slice_deinit(struct uint32_slice s) {
  if (munmap(s.arr, sizeof(uint32_t) * s.len) == -1) {
    panic("Failed to free memory arena");
  }
}

static uint64_t sum_with_steps(struct uint32_slice s, size_t steps) {
  uint64_t sum = 0;

  for (size_t i = 0; i < s.len; i += steps) {
    sum += s.arr[i];
  }

  return sum;
}

__attribute__((noinline)) static void
uint32_slice_set_random(struct uint32_slice s) {
  for (size_t i = 0; i < s.len; ++i) {
    s.arr[i] = rand();
  }
}

struct timespec diff(struct timespec start, struct timespec end) {
  struct timespec temp;
  if ((end.tv_nsec - start.tv_nsec) < 0) {
    temp.tv_sec = end.tv_sec - start.tv_sec - 1;
    temp.tv_nsec = 1000000000 + end.tv_nsec - start.tv_nsec;
  } else {
    temp.tv_sec = end.tv_sec - start.tv_sec;
    temp.tv_nsec = end.tv_nsec - start.tv_nsec;
  }
  return temp;
}

int main(int argc, char **args) {
  if (argc != 4) {
    fprintf(stderr, "Usage: %s <size> <seed> <steps>\n", args[0]);
    exit(EXIT_FAILURE);
  }

  size_t size = atoll(args[1]);
  size_t seed = atoi(args[2]);
  size_t steps = atoi(args[3]);
  srand(seed);

  struct uint32_slice s = uint32_slice_init(size);
  uint32_slice_set_random(s);

  struct timespec time1, time2;

  clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &time1);
  uint64_t sum = sum_with_steps(s, steps);
  clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &time2);

  struct timespec duration = diff(time1, time2);
  uint64_t nano = duration.tv_sec * 1e9 + duration.tv_nsec;

  printf("%lu;%lu;%lu;%lu;%lu\n", size, seed, steps, sum, nano);
}
