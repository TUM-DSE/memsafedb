
#include "experiment.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

struct arena {
  uint8_t *arena;
  size_t len;
};

struct manager {
  struct arena *arenas;
  size_t arenas_len;
};

struct node_pair {
  struct node *start;
  struct node *end;
};

static uint64_t checksum1 = 0;

static struct manager *sparse_manager_init(size_t num_nodes) {
  assert(sizeof(struct node) == NODE_SIZE);

  struct manager *m = malloc(sizeof(*m));
  if (!m) {
    panic("OOM");
  }

  m->arenas_len = num_nodes;
  m->arenas = malloc(sizeof(struct arena) * num_nodes);
  if (!m->arenas) {
    panic("OOM");
  }

  for (size_t i = 0; i < num_nodes; ++i) {
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

static struct node_pair sparse_connect_nodes(struct manager *m) {
  size_t nodes_left = m->arenas_len;
  m->arenas[0].len += 1;
  struct node *n = (struct node *)m->arenas[0].arena;
  n->value = rand();
  checksum1 ^= n->value;

  struct node *start = n;
  struct node *prev = n;

  for (size_t i = 1; i < nodes_left; ++i) {
    m->arenas[i].len += 1;
    struct node *n = (struct node *)m->arenas[i].arena;
    n->value = rand();
    checksum1 ^= n->value;

    prev->next = n;
    prev = n;
  }

  return (struct node_pair){
      .start = start,
      .end = prev,
  };
}

struct result run(struct options *options) {
  assert(options != NULL);
  srand(options->seed);

  struct manager *m = sparse_manager_init(options->num_nodes);
  assert(m->arenas != NULL);
  assert(m->arenas_len == options->num_nodes);

  struct node_pair p = sparse_connect_nodes(m);
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
  // dense_manager_deinit(m);
  return (struct result){
      .name = "sparse",
      .duration = 1e9 * (e.tv_sec - s.tv_sec) + (e.tv_nsec - s.tv_nsec),
      .checksum1 = checksum1,
      .checksum2 = checksum,
  };
}
