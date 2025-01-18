

#ifndef EXPERIMENT_H
#define EXPERIMENT_H

#include <stddef.h>
#include <stdint.h>

#define ARENA_SIZE (2048 * 4)
#define NODE_SIZE 64

#define panic(msg) do { \
  fprintf(stderr, "PANIC: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
  abort(); \
} while (0)

struct node {
  struct node *next;
  uint8_t pad[64 - sizeof(struct nodes *) - sizeof(uint64_t)];
  uint64_t value;
};

struct options {
  size_t num_nodes;
  uint32_t seed;
};

typedef uint64_t duration_ns_t;

struct result {
  char *name;
  duration_ns_t duration;
  uint64_t checksum1;
  uint64_t checksum2;
};


struct result run(struct options *options);

#endif 
