#ifndef MTE_UTILS_HPP
#define MTE_UTILS_HPP

#ifdef MTE
#include <sys/prctl.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <arm_acle.h>

#define MTE_GRANULE_SIZE 16
#define MTE_MODE_SYNC 1
#define MTE_MODE_ASYNC 2
const uintptr_t addr_mask = 0x00FFFFFFFFFFFFFFULL;

#define MTE_TAG_INCLUDE_MASK 0xfffe
inline void init_process(int mode){
  if (prctl(PR_SET_TAGGED_ADDR_CTRL, (1UL << 0) | PR_MTE_TCF_SYNC | (MTE_TAG_INCLUDE_MASK << 3), 0, 0, 0)){
    perror("prctl() failed");
  }
}

inline void* tag_pointer(void* ptr, size_t size){
  assert(ptr != NULL);
  if(size % 16 != 0){
    perror("non aligned tagging");
  }
  assert(size % 16 == 0);
  __asm__ volatile("irg %0, %1" : "+r" (ptr) : );
  void *end = (char*) ptr + size;
  void *ret = ptr;
  while (ptr < end) {
    __asm__ volatile("stg %0, [%1], #16" : "+r"(ptr) : : "memory");
  }
  return ret;
}

inline void* untag_pointer(void* ptr, size_t size){
  assert(ptr != NULL);
  assert(size % 16 == 0);

  void *ut_ptr = (void*)((uintptr_t)ptr & addr_mask);
  void *end = (char*) ptr + size;
  while (ptr < end) {
    __asm__ volatile("stg %0, [%1], #16" : "+r" (ptr) : "r" (ut_ptr) : "memory");
  }
  return ut_ptr;
}

inline void print_tag(void* ptr){
  int logical_tag = reinterpret_cast<uintptr_t>(ptr) >> 56;
  void* alloc_tag= __arm_mte_get_tag(ptr);
  printf("ptr: %p, logical tag: %u, allocation tag: %lu\n", ptr, logical_tag, reinterpret_cast<uintptr_t>(alloc_tag)>>56);
}
#endif
#endif
