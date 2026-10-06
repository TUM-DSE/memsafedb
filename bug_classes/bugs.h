// Bug-class suite: small, self-contained reproductions of the memory-safety
// bug classes of the bug study (Sec. 2.1, App. B), used to check which classes
// MTE and CHERI detect (Sec. 6.4).
#pragma once

#include <stddef.h>
#include <stdint.h>

// What a bug function observed when it ran to completion (no trap/crash).
enum obs {
  OBS_NONE = 0,    // the bug executed without any observable effect
  OBS_CORRUPT = 1, // a neighbouring object/field (or a reused object) was modified
  OBS_LEAK = 2,    // data of another (live, freed, or reused) object was read
};

// Shared with the runner (mapped MAP_SHARED before fork) so the parent can
// tell where the child was when it trapped.
struct shared_state {
  volatile int stage;     // see STAGE_* below
  volatile int signo;     // signal caught by the child handler
  volatile int code;      // si_code of that signal
  volatile uint64_t addr; // si_addr (address only)
  volatile int obs;       // observation recorded before cleanup (-1: none)
};
extern struct shared_state *g_state;

enum {
  STAGE_SETUP = 0,   // allocating / preparing objects
  STAGE_ACCESS = 1,  // the faulty operation is executing
  STAGE_AFTER = 2,   // the faulty operation completed without a trap
  STAGE_CLEANUP = 3, // freeing objects after the faulty operation
};
#define STAGE(n)                                                               \
  do {                                                                         \
    g_state->stage = (n);                                                      \
    __asm__ volatile("" ::: "memory");                                         \
  } while (0)

typedef int (*bug_fn)(void);

struct bug {
  const char *id;    // short identifier, used in CSVs and the table
  const char *cls;   // bug class (row of the paper table)
  const char *desc;  // one-line description
  bug_fn fn;
};

extern const struct bug g_bugs[];
extern const size_t g_nbugs;
