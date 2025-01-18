
#include "experiment.h"
#include <assert.h>
#include <malloc.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

/*
 * Dense experiment. With node size of 64 byte
 *
 * 2048 bytes
 * --------------------
 * | 64B |            |
 * |------            |
 * | 64B |    ...     |
 * |------            |
 * | 64B |            |
 * --------------------
 *
 *  Inside a 2048 Byte block we put many Nodes of a size of 64 Bytes and access
 * the nodes inside a block random. Because of the size of the nodes (64 eq.
 * cacheline) the should be no performnace win compared to the spare one.
 *
 */

#define _GNU_SOURCE
#include <fcntl.h>
#include <unistd.h>

static uint64_t checksum1 = 0;

struct arena {
  uint8_t *arena;
  size_t len;
};

struct manager {
  struct arena *arenas;
  size_t arenas_len;
  size_t num_nodes;
};

struct node_pair {
  struct node *start;
  struct node *end;
};

#define NODES_PER_ARENA (ARENA_SIZE / NODE_SIZE)

#define SWAP(arr, i1, i2)                                                      \
  do {                                                                         \
    uint32_t tmp = arr[i1];                                                    \
    arr[i1] = arr[i2];                                                         \
    arr[i2] = tmp;                                                             \
  } while (0)

static struct manager *dense_manager_init(size_t num_nodes) {
  assert(sizeof(struct node) == NODE_SIZE);

  uint64_t num_arenas = (num_nodes / NODES_PER_ARENA) + 1;

  struct manager *m = malloc(sizeof(*m));
  if (!m) {
    panic("OOM");
  }

  m->arenas_len = num_arenas;
  m->num_nodes = num_nodes;
  m->arenas = malloc(sizeof(struct arena) * num_arenas);
  if (!m->arenas) {
    panic("OOM");
  }

  for (size_t i = 0; i < num_arenas; ++i) {
    void *arr = mmap(NULL, ARENA_SIZE, PROT_READ | PROT_WRITE,
                     MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if (arr == MAP_FAILED) {
      panic("OOM arena");
    }

    struct arena *a = &m->arenas[i];
    a->arena = arr;
    a->len = 0;
  }

  return m;
}

static void dense_manager_deinit(struct manager *m) {
  assert(m != NULL);

  for (size_t i = 0; i < m->arenas_len; ++i) {
    if (munmap(m->arenas[i].arena, ARENA_SIZE) == -1) {
      panic("Failed to free memory arena");
    }
  }

  free(m->arenas);
  free(m);
}

static struct node_pair dense_connect_nodes_arena(struct arena *a,
                                                  uint32_t nodes_to_alloc) {
  assert(a != NULL);
  assert(nodes_to_alloc <= NODES_PER_ARENA);

  size_t len = NODES_PER_ARENA;
  uint32_t order[len];
  for (size_t i = 0; i < len; ++i) {
    order[i] = i;
  }

  uint32_t next = rand() % len;
  len -= 1;
  size_t idx = order[next];
  SWAP(order, next, len);

  struct node *start = (struct node *)&a->arena[NODE_SIZE * idx];
  assert(start->next == NULL);
  assert(start->value == 0);

  start->value = rand();
  checksum1 ^= start->value;

  struct node *curr = start;
  for (size_t i = 0; i < nodes_to_alloc - 1; ++i) {
    next = rand() % len;
    len -= 1;
    idx = order[next];
    SWAP(order, next, len);

    struct node *n = (struct node *)&a->arena[NODE_SIZE * idx];
    assert(n->next == NULL);
    assert(n->value == 0);

    n->value = rand();
    checksum1 ^= n->value;

    curr->next = n;
    curr = n;
  }

  return (struct node_pair){
      .start = start,
      .end = curr,
  };
}

static struct node_pair dense_connect_nodes(struct manager *m) {
  // connet the arena internally and than each other
  size_t nodes_left = m->num_nodes;
  size_t arena_idx = 0;

  size_t node_to_alloc = nodes_left >= 32 ? 32 : nodes_left;
  struct node_pair prev =
      dense_connect_nodes_arena(&m->arenas[arena_idx], node_to_alloc);
  struct node *start = prev.start;
  arena_idx += 1;
  nodes_left -= node_to_alloc;
  assert(nodes_left >= 0);

  struct node_pair curr = prev;
  while (nodes_left != 0) {
    assert(arena_idx < m->arenas_len);
    assert(nodes_left >= 0);

    node_to_alloc = nodes_left >= 32 ? 32 : nodes_left;
    curr = dense_connect_nodes_arena(&m->arenas[arena_idx], node_to_alloc);
    prev.end->next = curr.start;
    prev = curr;
    nodes_left -= node_to_alloc;
    arena_idx += 1;
  }

  return (struct node_pair){
      .start = start,
      .end = curr.end,
  };
}

struct result run(struct options *options) {
  assert(options != NULL);
  srand(options->seed);

  struct manager *m = dense_manager_init(options->num_nodes);
  assert(m->arenas != NULL);
  assert(m->arenas_len > 0);
  assert(m->arenas_len < options->num_nodes);

  struct node_pair p = dense_connect_nodes(m);
  struct node *n = p.start;

  struct timespec s, e;

  // Benchmark
  clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &s);
  struct node *prev;
  uint64_t checksum = 0;
  while (n) {
    checksum ^= n->value;
    prev = n;
    n = n->next;
  }
  clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &e);

  assert(n == NULL);
  assert(prev == p.end);
  dense_manager_deinit(m);
  return (struct result){
      .name = "dense",
      .duration = 1e9 * (e.tv_sec - s.tv_sec) + (e.tv_nsec - s.tv_nsec),
      .checksum1 = checksum1,
      .checksum2 = checksum,
  };
}
