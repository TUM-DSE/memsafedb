#include "experiment.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *args[]) {
  if (argc != 3) {
    fprintf(stderr, "Usage: %s <num_nodes> <seed>\n", args[0]);
    exit(EXIT_FAILURE);
  }

  size_t num_nodes = atoll(args[1]);
  uint32_t seed = atoi(args[2]);

  struct options options = {
      .num_nodes = num_nodes,
      .seed = seed,
  };
  struct result r = run(&options);

  printf("%s;%ld;%u;%ld;%ld;%ld\n", r.name, num_nodes, seed, r.checksum1,
         r.checksum2, r.duration);
}
