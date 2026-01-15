#pragma once

#ifdef MTE
#include <sys/prctl.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <arm_acle.h>

#define MTE_GRANULE_SIZE 16
#define MTE_MODE_SYNC 1
#define MTE_MODE_ASYNC 2
#define ADDR_MASK ((uintptr_t)0x00FFFFFFFFFFFFFFULL)

inline size_t round_to_tag_granule(size_t size) {
  return (size + (MTE_GRANULE_SIZE - 1)) & ~(MTE_GRANULE_SIZE - 1);
}

#define MTE_TAG_INCLUDE_MASK 0xfffe
inline void init_process(int mode){
  if (prctl(PR_SET_TAGGED_ADDR_CTRL, (1UL << 0) | PR_MTE_TCF_SYNC | (MTE_TAG_INCLUDE_MASK << 3), 0, 0, 0)){
    perror("prctl() failed");
  }
}

inline void* tag_memory_region(void* ptr, size_t size){
  assert(ptr != NULL);
  if(size % 16 != 0){
    perror("non aligned tagging");
  }
  assert(size % 16 == 0);
  __asm__ volatile("irg %0, %0" : "+r" (ptr) : );
  void *end = (char*) ptr + size;
  void *ret = ptr;
  while (ptr < end) {
    __asm__ volatile("stg %0, [%0], #16" : "+r"(ptr) : : "memory");
  }
  return ret;
}

inline void* tag_and_zero_memory_region(void* ptr, size_t size){
  assert(ptr != NULL);
  assert(size % 16 == 0);
  __asm__ volatile("irg %0, %1" : "+r" (ptr) : );
  void *end = (char*) ptr + size;
  void *ret = ptr;
  while (ptr < end) {
    __asm__ volatile("stzg %0, [%0], #16" : "+r"(ptr) : : "memory");
  }
  return ret;
}

inline void* untag_memory_region(void* ptr, size_t size){
  assert(ptr != NULL);
  assert(size % 16 == 0);

  void *ut_ptr = (void*)((uintptr_t)ptr & ADDR_MASK);
  void *end = (char*) ptr + size;
  while (ptr < end) {
    __asm__ volatile("stg %1, [%0], #16" : "+r" (ptr) : "r" (ut_ptr) : "memory");
  }
  return ut_ptr;
}

inline void* clear_tag(void *ptr){
  return (void*)((uintptr_t)ptr & ADDR_MASK);
}

inline void print_tag(void* ptr){
  int logical_tag = ((uintptr_t) ptr) >> 56;
  void* alloc_tag= __arm_mte_get_tag(ptr);
  printf("ptr: %p, logical tag: %u, allocation tag: %lu\n", ptr, logical_tag, ((uintptr_t)alloc_tag)>>56);
}
#endif
