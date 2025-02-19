
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

#include <sys/auxv.h>
#include <sys/prctl.h>

#ifdef MTE
#include <arm_acle.h>
#endif


extern void *mtag_tag_region(void *ptr, size_t size);

void *alloc(size_t num_bytes) {
#ifdef MTE
  unsigned long hwcap2 = getauxval(AT_HWCAP2);

  /* check if MTE is present */
  if (!(hwcap2 & HWCAP2_MTE)) {
    perror("MTE is not present");
    exit(EXIT_FAILURE);
  }
#endif

#ifdef MTE
  void *mem = mmap(NULL, num_bytes, PROT_READ | PROT_WRITE | PROT_MTE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
#else
  void *mem = mmap(NULL, num_bytes, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
#endif

  if (mem == MAP_FAILED) {
    perror("mmap");
    exit(EXIT_FAILURE);
  }

#ifdef MTE
  /* Tag the mmap area */
  void *p = __arm_mte_create_random_tag(mem, 0);
  mem = mtag_tag_region(p, num_bytes);
#endif

  // ensure every page is loaded befor benchmarking
  uint8_t *pp = mem;
  for (size_t i = 0; i < num_bytes; i += 1024) {
      pp[i]++;
  }

  return mem;
}

void alloc_free(void *ptr, size_t num_bytes) {
    if (munmap(ptr, num_bytes) == -1) {
        perror("mmap");
        exit(EXIT_FAILURE);
    }
}
