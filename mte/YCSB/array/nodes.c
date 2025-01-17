//
// Created by raphael-dichler on 1/14/25.
//
#include <assert.h>
#include <malloc.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>

#include "slices.h"
#include "walking_order.h"

#ifdef MTE
#include <arm_acle.h>
#endif

void *tag_64byte(void *start) {
#ifdef MTE
  uintptr_t addr = (uintptr_t)start;
  addr = __arm_mte_create_random_tag(addr, 0);

  asm volatile("st2g %0, [%0]\n\t"      // Store tag for first 32 bytes
               "st2g %0, [%0, #32]\n\t" // Store tag for next 32 bytes
               :                        // No output operands
               : "r"(addr)              // Input operand
               : "memory"               // Clobbers memory
  );

  return addr;
#endif
  return NULL;
}

#define ARENA_SIZE 2048

#ifdef MTE
// https://developer.arm.com/documentation/101028/0012/10--Memory-tagging-intrinsics
#define __ARM_FEATURE_MEMORY_TAGGING
#endif

#define panic(msg)                                                             \
  do {                                                                         \
    fprintf(stderr, "PANIC: %s (%s:%d)\n", msg, __FILE__, __LINE__);           \
    abort();                                                                   \
  } while (0)

struct memory_arena {
  uint8_t *arena;
  uint32_t nodes_allocated;
};

struct node {
  struct node *next;
  uint8_t data[60 - sizeof(struct node *)];
  uint32_t value;
};

struct memory_arena *memory_arena_init() {
  struct memory_arena *ma = malloc(sizeof(*ma));
  if (!ma) {
    panic("OOM");
  }
  void *m = mmap(NULL, ARENA_SIZE, PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (m == MAP_FAILED) {
    panic("OOM");
  }

#ifdef MTE
  if (mprotect(a, page_sz, PROT_READ | PROT_WRITE | PROT_MTE)) {
    panic("mprotect() failed");
  }
#endif

  assert(sizeof(struct node) == 64);
  ma->nodes_allocated = 0;
  ma->arena = m;

  return ma;
}

void memory_arena_deinit(struct memory_arena *ma) {
  if (munmap(ma->arena, ARENA_SIZE) == -1) {
    panic("Failed to free memory arena");
  }
  free(ma);
}

struct node *memory_arena_node_init(struct memory_arena *ma) {
  assert(sizeof(struct node) == 64);
  if (ma->nodes_allocated >= (ARENA_SIZE / 64)) {
    panic("To many nodes inside the arena");
  }

  struct node *n = (struct node *)(&ma->arena[ma->nodes_allocated * 64]);
  ma->nodes_allocated += 1;

#ifdef MTE
  n = tag_64byte(n);
#endif

  n->value = 0;
  n->next = NULL;

  return n;
}

/*
 * What do we want to see:
 *  The difference in time between tagged and untag should be come increasingly
 * smaller because the fetching of the tags in the tagging area is much better
 * here. Assumption is that with random access via nodes the prefetching of the
 * tags get increasingly harder which results in bad performance.
 *
 *  With one node per region: 100_000 * 64 bytes are used for
 */
// 2048 / 64 = 32 --> 32 node inside 1 arena
// 100_000 / 32 = 3125 --> different cache lines for tags need to be loaded
// 100_000 nodes each in its own arena
int main(int argc, char **args) {
  if (argc != 3) {
    fprintf(stderr, "Usage: %s <num_nodes> <seed>\n", args[0]);
    exit(EXIT_FAILURE);
  }
  uint32_t num_nodes = atoi(args[1]);
  assert(num_nodes <= UINT32_MAX);
  uint32_t seed = atoi(args[2]);
  srand(seed);

  uint64_t sum1 = 0;
  uint64_t sum2 = 0;
  uint32_slice_t walking_order = walking_order_init(num_nodes);
  struct node **nodes = malloc(sizeof(*nodes) * num_nodes);
  if (!nodes) {
    panic("OOM");
  }

  struct memory_arena **arenas = NULL;
  size_t num_arenas = 0;

#ifdef MTE
  unsigned char *a;
  unsigned long page_sz = sysconf(_SC_PAGESIZE);
  unsigned long hwcap2 = getauxval(AT_HWCAP2);

  /* check if MTE is present */
  if (!(hwcap2 & HWCAP2_MTE)) {
    panic("MTE is not present");
  }

#endif

#ifdef COMPACT
  printf("mode: COMPACT\n");
  // 2048 / 64 = 32 nodes per arena
  // 100_000 nodes needed -> 100_000 / 32 = 3125
  size_t nodes_per_arena = (ARENA_SIZE / sizeof(struct node));
  num_arenas = num_nodes / nodes_per_arena + 1;

  arenas = malloc(sizeof(*arenas) * num_arenas);
  if (!arenas) {
    panic("OOM");
  }

  for (size_t i = 0; i < num_arenas; ++i) {
    arenas[i] = memory_arena_init();
  }

  // fill each arena which nodes
  size_t inserted = 0;
  size_t arena_idx = 0;
  while (inserted <= num_nodes) {
    if (arenas[arena_idx]->nodes_allocated >= nodes_per_arena) {
      arena_idx += 1;
    }

    struct node *n = memory_arena_node_init(arenas[arena_idx]);
    n->value = rand();
    nodes[inserted] = n;
    inserted += 1;
  }
#else
  printf("mode: LOOSE\n");

  num_arenas = num_nodes;
  arenas = malloc(sizeof(*arenas) * num_nodes);
  if (!arenas) {
    panic("OOM");
  }

  for (uint32_t i = 0; i < num_arenas; ++i) {
    arenas[i] = memory_arena_init();
    struct node *n = memory_arena_node_init(arenas[i]);
    n->value = rand();
    nodes[i] = n;
  }
#endif
  printf("Connecting nodes\n");

  // connect nodes
  uint32_t curr = 0;
  for (uint32_t i = 0; i < num_nodes - 1; ++i) {
    uint32_t next = walking_order.arr[curr];
    struct node *c = nodes[curr];
    struct node *n = nodes[next];
    sum1 += c->value;
    curr = next;
    c->next = n;
  }

  struct node *n = nodes[0];
  free(nodes);
  nodes = NULL;
  assert(nodes == NULL);
  printf("Connecting nodes done\n");

  // walk nodes
  while (n->next) {
    sum2 += n->value;
    n = n->next;
  }

  printf("sum1: %ld\n", sum1);
  printf("sum2: %ld\n", sum2);
  assert(sum1 == sum2);

  for (uint32_t i = 0; i < num_arenas; ++i) {
    memory_arena_deinit(arenas[i]);
  }

  free(arenas);
  walking_order_deinit(walking_order);
}
