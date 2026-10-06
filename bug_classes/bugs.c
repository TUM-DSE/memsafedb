// Each bug function sets up a small scenario, performs one faulty operation
// between STAGE(STAGE_ACCESS) and STAGE(STAGE_AFTER), and returns what it
// observed (enum obs) if it was not stopped. Accesses go through volatile,
// non-inlined helpers so the compiler cannot fold or remove the bug.
//
// The cases reproduce the memory-safety classes of the bug-study classifier
// (paper, App. B); `cls` is the row of the paper's table (Sec. 6.4).
#define _GNU_SOURCE
#include "bugs.h"

#include <stdlib.h>
#include <string.h>

#ifdef __CHERI_PURE_CAPABILITY__
#include <cheriintrin.h>
#define ADDR(p) ((uint64_t)cheri_address_get(p))
#else
// Strip the top byte (MTE logical tag / TBI) to get the plain address.
#define ADDR(p) ((uint64_t)(uintptr_t)(p) & 0x00FFFFFFFFFFFFFFull)
#endif

// Defeat constant folding of sizes and indices.
static volatile size_t g_zero = 0;
#define OPAQUE(x) ((x) + g_zero)

__attribute__((noinline)) static void write_bytes(char *p, size_t off,
                                                  size_t n, char v) {
  for (size_t i = 0; i < n; i++)
    ((volatile char *)p)[off + i] = v;
}

// Returns 1 if any byte in p[off, off+n) equals `needle`.
__attribute__((noinline)) static int read_contains(const char *p, size_t off,
                                                   size_t n, char needle) {
  int found = 0;
  for (size_t i = 0; i < n; i++)
    found |= ((volatile const char *)p)[off + i] == needle;
  return found;
}

static int all_equal(const char *p, size_t n, char v) {
  for (size_t i = 0; i < n; i++)
    if (((volatile const char *)p)[i] != v)
      return 0;
  return 1;
}

static int record(int obs) {
  g_state->obs = obs;
  return obs;
}

/* ------------------------------------------------------------------------ */
/* Heap buffer overflow                                                     */
/* ------------------------------------------------------------------------ */

// Linear overflow past a heap buffer into the next allocation.
static int bug_heap_overflow(void) {
  char *a = malloc(32), *b = malloc(32);
  memset(b, 'B', 32);
  STAGE(STAGE_ACCESS);
  write_bytes(a, 32, 48, 'X');
  STAGE(STAGE_AFTER);
  int obs = record(all_equal(b, 32, 'B') ? OBS_NONE : OBS_CORRUPT);
  STAGE(STAGE_CLEANUP);
  free(a);
  free(b);
  return obs;
}

// Off-by-few overflow that stays inside the last 16-byte granule.
static int bug_heap_overflow_granule(void) {
  char *a = malloc(OPAQUE(20));
  STAGE(STAGE_ACCESS);
  write_bytes(a, 20, 4, 'X');
  STAGE(STAGE_AFTER);
  int obs = record(OBS_NONE);
  STAGE(STAGE_CLEANUP);
  free(a);
  return obs;
}

// Small overflow past a large allocation whose CHERI bounds are rounded up
// to a representable length (imprecise bounds).
static int bug_heap_overflow_large(void) {
  size_t n = OPAQUE((1u << 20) + 16);
  char *a = malloc(n);
  STAGE(STAGE_ACCESS);
  write_bytes(a, n, 16, 'X');
  STAGE(STAGE_AFTER);
  int obs = record(OBS_NONE);
  STAGE(STAGE_CLEANUP);
  free(a);
  return obs;
}

// Integer overflow in a size computation leads to an undersized buffer.
static int bug_int_overflow_alloc(void) {
  uint32_t count = (uint32_t)OPAQUE(0x40000001u);
  uint32_t bytes = count * 4u; // wraps to 4
  char *a = malloc(bytes), *b = malloc(32);
  memset(b, 'B', 32);
  STAGE(STAGE_ACCESS);
  write_bytes(a, 0, 64, 'X');
  STAGE(STAGE_AFTER);
  int obs = record(all_equal(b, 32, 'B') ? OBS_NONE : OBS_CORRUPT);
  STAGE(STAGE_CLEANUP);
  free(a);
  free(b);
  return obs;
}

// Overflow inside a libc routine (memcpy with a too-large length).
static int bug_libc_memcpy_overflow(void) {
  char src[128];
  memset(src, 'X', sizeof src);
  char *a = malloc(32), *b = malloc(32);
  memset(b, 'B', 32);
  STAGE(STAGE_ACCESS);
  memcpy(a, src, OPAQUE(96));
  STAGE(STAGE_AFTER);
  int obs = record(all_equal(b, 32, 'B') ? OBS_NONE : OBS_CORRUPT);
  STAGE(STAGE_CLEANUP);
  free(a);
  free(b);
  return obs;
}

/* ------------------------------------------------------------------------ */
/* Out-of-bounds read / write                                               */
/* ------------------------------------------------------------------------ */

// Out-of-bounds read past a heap buffer (information leak).
static int bug_oob_read(void) {
  char *a = malloc(32), *b = malloc(32);
  memset(b, 'S', 32);
  STAGE(STAGE_ACCESS);
  int leaked = read_contains(a, 32, 64, 'S');
  STAGE(STAGE_AFTER);
  int obs = record(leaked ? OBS_LEAK : OBS_NONE);
  STAGE(STAGE_CLEANUP);
  free(a);
  free(b);
  return obs;
}

// Negative index: write just before the buffer (allocator metadata).
static int bug_oob_underflow(void) {
  char *a = malloc(32);
  STAGE(STAGE_ACCESS);
  write_bytes(a - OPAQUE(8), 0, 8, 'X');
  STAGE(STAGE_AFTER);
  int obs = record(OBS_CORRUPT);
  STAGE(STAGE_CLEANUP);
  free(a);
  return obs;
}

// Wild index that skips the redzone and lands inside another live object.
static int bug_oob_nonadjacent(void) {
  char *a = malloc(64), *b = malloc(64);
  memset(b, 'S', 64);
  char *target = a + (ADDR(b) - ADDR(a));
  STAGE(STAGE_ACCESS);
  int leaked = read_contains(target, 0, 16, 'S');
  STAGE(STAGE_AFTER);
  int obs = record(leaked ? OBS_LEAK : OBS_NONE);
  STAGE(STAGE_CLEANUP);
  free(a);
  free(b);
  return obs;
}

/* ------------------------------------------------------------------------ */
/* Stack and global overflow                                                */
/* ------------------------------------------------------------------------ */

__attribute__((noinline)) static int bug_stack_overflow(void) {
  volatile char guard[16];
  char buf[16];
  for (int i = 0; i < 16; i++)
    guard[i] = 'G';
  memset(buf, 0, sizeof buf);
  STAGE(STAGE_ACCESS);
  write_bytes(buf, 16, 16, 'X');
  STAGE(STAGE_AFTER);
  return record(all_equal((const char *)guard, 16, 'G') ? OBS_NONE
                                                        : OBS_CORRUPT);
}

__attribute__((used)) static char g_buf[16];
__attribute__((used)) static char g_neighbour[16] = "NNNNNNNNNNNNNNN";

static int bug_global_overflow(void) {
  STAGE(STAGE_ACCESS);
  write_bytes(g_buf, 16, 16, 'X');
  STAGE(STAGE_AFTER);
  return record(all_equal(g_neighbour, 15, 'N') ? OBS_NONE : OBS_CORRUPT);
}

/* ------------------------------------------------------------------------ */
/* Use-after-free                                                           */
/* ------------------------------------------------------------------------ */

static int bug_uaf_read(void) {
  char *p = malloc(64);
  memset(p, 'S', 64);
  free(p);
  STAGE(STAGE_ACCESS);
  int leaked = read_contains(p, 16, 48, 'S');
  STAGE(STAGE_AFTER);
  return record(leaked ? OBS_LEAK : OBS_NONE);
}

// Write through a dangling pointer; the next allocation receives the data.
static int bug_uaf_write(void) {
  char *p = malloc(64);
  free(p);
  STAGE(STAGE_ACCESS);
  write_bytes(p, 16, 16, 'X');
  STAGE(STAGE_AFTER);
  char *q = malloc(64);
  int obs = record(read_contains(q, 16, 16, 'X') ? OBS_CORRUPT : OBS_NONE);
  STAGE(STAGE_CLEANUP);
  free(q);
  return obs;
}

// Dangling pointer used after the memory was reallocated to a new object.
static int bug_uaf_reuse(void) {
  char *p = malloc(64);
  free(p);
  char *q = malloc(64); // typically the same chunk
  memset(q, 'Q', 64);
  STAGE(STAGE_ACCESS);
  write_bytes(p, 0, 16, 'X');
  STAGE(STAGE_AFTER);
  int obs = record(all_equal(q, 64, 'Q') ? OBS_NONE : OBS_CORRUPT);
  STAGE(STAGE_CLEANUP);
  free(q);
  return obs;
}

// Stale pointer after realloc() moved the buffer.
static int bug_realloc_stale(void) {
  char *p = malloc(16);
  memset(p, 'S', 16);
  char *q = realloc(p, OPAQUE(4096));
  STAGE(STAGE_ACCESS);
  write_bytes(p, 0, 16, 'X');
  STAGE(STAGE_AFTER);
  int obs = record(OBS_CORRUPT);
  STAGE(STAGE_CLEANUP);
  free(q);
  return obs;
}

/* ------------------------------------------------------------------------ */
/* Double / invalid free                                                    */
/* ------------------------------------------------------------------------ */

static int bug_double_free(void) {
  char *p = malloc(64);
  free(p);
  STAGE(STAGE_ACCESS);
  free(p);
  STAGE(STAGE_AFTER);
  // The allocator may now hand out the same chunk twice.
  char *q = malloc(64), *r = malloc(64);
  int obs = record(q == r ? OBS_CORRUPT : OBS_NONE);
  return obs;
}

static int bug_invalid_free(void) {
  char *p = malloc(64);
  STAGE(STAGE_ACCESS);
  free(p + OPAQUE(16));
  STAGE(STAGE_AFTER);
  return record(OBS_NONE);
}

/* ------------------------------------------------------------------------ */
/* Null dereference / uninitialized memory                                  */
/* ------------------------------------------------------------------------ */

static int *volatile g_null;

static int bug_null_deref(void) {
  int *p = g_null;
  STAGE(STAGE_ACCESS);
  int v = *(volatile int *)p;
  STAGE(STAGE_AFTER);
  (void)v;
  return record(OBS_NONE);
}

// Freshly allocated memory still contains the previous owner's data.
static int bug_uninit_read(void) {
  char *p = malloc(64);
  memset(p, 'S', 64);
  free(p);
  char *q = malloc(64);
  STAGE(STAGE_ACCESS);
  int leaked = read_contains(q, 16, 48, 'S');
  STAGE(STAGE_AFTER);
  int obs = record(leaked ? OBS_LEAK : OBS_NONE);
  STAGE(STAGE_CLEANUP);
  free(q);
  return obs;
}

/* ------------------------------------------------------------------------ */

#define HEAP "Heap buffer overflow"
#define STACK "Stack/global buffer overflow"
#define OOB "Out-of-bounds read/write"
#define INTOVF "Integer overflow to corruption"
#define UAF "Use-after-free"
#define FREE "Double/invalid free"
#define NULLD "Null pointer dereference"
#define UNINIT "Uninitialized memory access"

const struct bug g_bugs[] = {
    {"heap_overflow", HEAP, "Linear write past a heap buffer into the next allocation",
     bug_heap_overflow},
    {"heap_overflow_granule", HEAP, "Overflow within the buffer's last 16-byte granule",
     bug_heap_overflow_granule},
    {"heap_overflow_large", HEAP, "Small overflow past a large (1 MiB) allocation",
     bug_heap_overflow_large},
    {"libc_memcpy_overflow", HEAP, "Overflow inside libc (memcpy with a too-large length)",
     bug_libc_memcpy_overflow},
    {"stack_overflow", STACK, "Write past a local array", bug_stack_overflow},
    {"global_overflow", STACK, "Write past a global array", bug_global_overflow},
    {"oob_read", OOB, "Read past a heap buffer (information leak)", bug_oob_read},
    {"oob_underflow", OOB, "Write before the start of a heap buffer", bug_oob_underflow},
    {"oob_nonadjacent", OOB, "Wild index landing inside another live object",
     bug_oob_nonadjacent},
    {"int_overflow_alloc", INTOVF,
     "Wrapped size computation, then overflow of the undersized buffer",
     bug_int_overflow_alloc},
    {"uaf_read", UAF, "Read through a freed pointer", bug_uaf_read},
    {"uaf_write", UAF, "Write through a freed pointer, visible in the next allocation",
     bug_uaf_write},
    {"uaf_reuse", UAF, "Freed pointer used after the memory was reallocated", bug_uaf_reuse},
    {"realloc_stale", UAF, "Stale pointer after realloc() moved the buffer",
     bug_realloc_stale},
    {"double_free", FREE, "free() called twice", bug_double_free},
    {"invalid_free", FREE, "free() of an interior pointer", bug_invalid_free},
    {"null_deref", NULLD, "Read through a NULL pointer", bug_null_deref},
    {"uninit_read", UNINIT, "New allocation still holds the previous owner's data",
     bug_uninit_read},
};

const size_t g_nbugs = sizeof g_bugs / sizeof g_bugs[0];
