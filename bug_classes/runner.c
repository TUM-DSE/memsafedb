// Runs every bug of the suite in a forked child, repeatedly, and classifies
// how each run ended. Output: one CSV row per (bug, outcome, detail, timing).
//
// Usage: runner -c <config> [-n runs] [-b bug_id] [-o out.csv] [-l]
#define _GNU_SOURCE
#include "bugs.h"

#include <errno.h>
#include <getopt.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <unistd.h>

// si_code values (Linux uapi); not all libcs define them.
#ifndef SEGV_MTEAERR
#define SEGV_MTEAERR 8 // MTE asynchronous tag check fault
#endif
#ifndef SEGV_MTESERR
#define SEGV_MTESERR 9 // MTE synchronous tag check fault
#endif
// Morello Linux reports capability faults as SIGSEGV with one si_code per
// fault type (uapi asm/siginfo.h): tag, sealed, bounds, permission, tag store.
#define SEGV_CAP_FIRST 10
#define SEGV_CAP_LAST 14
static const char *const cheri_fault_names[] = {
    "cheri_tag", "cheri_sealed", "cheri_bounds", "cheri_permission",
    "cheri_tag_store"};

#define EXIT_TRAPPED 97 // child caught a fault in its handler
#define EXIT_OBS_BASE 64
#define CHILD_TIMEOUT_S 5
#define STDERR_MAX (64 * 1024)

struct shared_state *g_state;

/* ---------------------------- child side -------------------------------- */

static void fault_handler(int sig, siginfo_t *si, void *ctx) {
  (void)ctx;
  g_state->signo = sig;
  g_state->code = si->si_code;
  g_state->addr = (uint64_t)(uintptr_t)si->si_addr;
  _exit(EXIT_TRAPPED);
}

static void child_setup(void) {
#ifdef MTE
  // Synchronous tag checks, all non-zero tags allowed (glibc does the same
  // with glibc.mem.tagging=3; repeating it is harmless).
  prctl(PR_SET_TAGGED_ADDR_CTRL,
        PR_TAGGED_ADDR_ENABLE | PR_MTE_TCF_SYNC | (0xfffeUL << PR_MTE_TAG_SHIFT),
        0, 0, 0);
#endif
  static char altstack[64 * 1024];
  stack_t ss = {.ss_sp = altstack, .ss_size = sizeof altstack, .ss_flags = 0};
  sigaltstack(&ss, NULL);

  struct sigaction sa;
  memset(&sa, 0, sizeof sa);
  sa.sa_sigaction = fault_handler;
  sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
  sigemptyset(&sa.sa_mask);
  int sigs[] = {SIGSEGV, SIGBUS, SIGILL, SIGTRAP, SIGFPE};
  for (size_t i = 0; i < sizeof sigs / sizeof sigs[0]; i++)
    sigaction(sigs[i], &sa, NULL);
  alarm(CHILD_TIMEOUT_S);
}

/* ---------------------------- parent side ------------------------------- */

struct outcome {
  char outcome[32]; // hw_trap, runtime_abort, crash, hang, silent
  char detail[96];  // mechanism (fault type, libc message) or observation
  char timing[16];  // access, later, -
};

static const char *obs_name(int obs) {
  switch (obs) {
  case OBS_NONE: return "no_effect";
  case OBS_CORRUPT: return "corruption";
  case OBS_LEAK: return "leak";
  default: return "unknown";
  }
}

static const char *timing_of(int stage) {
  switch (stage) {
  case STAGE_SETUP: return "setup";
  case STAGE_ACCESS: return "access";
  case STAGE_AFTER: return "after";
  default: return "cleanup";
  }
}

// glibc / musl allocator and libc runtime checks.
static int find_libc_message(const char *buf, char *out, size_t n) {
  static const char *patterns[] = {
      "double free", "free(): ", "malloc(): ", "realloc(): ", "munmap_chunk",
      "corrupted ", "malloc_consolidate", "unaligned tcache",
  };
  for (size_t i = 0; i < sizeof patterns / sizeof patterns[0]; i++) {
    const char *p = strstr(buf, patterns[i]);
    if (!p)
      continue;
    size_t j = 0;
    while (p[j] && p[j] != '\n' && j + 1 < n) {
      out[j] = p[j] == ',' ? ';' : p[j];
      j++;
    }
    out[j] = 0;
    return 1;
  }
  return 0;
}

static void classify(int status, const char *err, struct outcome *o) {
  strcpy(o->timing, "-");
  o->detail[0] = 0;
  int stage = g_state->stage;

  if (WIFEXITED(status)) {
    int st = WEXITSTATUS(status);
    if (st == EXIT_TRAPPED) {
      int sig = g_state->signo, code = g_state->code;
      strcpy(o->timing, timing_of(stage));
      if (sig == SIGSEGV && code == SEGV_MTESERR) {
        strcpy(o->outcome, "hw_trap");
        strcpy(o->detail, "mte_sync");
      } else if (sig == SIGSEGV && code == SEGV_MTEAERR) {
        strcpy(o->outcome, "hw_trap");
        strcpy(o->detail, "mte_async");
      } else if (sig == SIGSEGV && code >= SEGV_CAP_FIRST && code <= SEGV_CAP_LAST) {
        strcpy(o->outcome, "hw_trap");
        strcpy(o->detail, cheri_fault_names[code - SEGV_CAP_FIRST]);
#ifdef SIGPROT
      } else if (sig == SIGPROT) {
        strcpy(o->outcome, "hw_trap");
        snprintf(o->detail, sizeof o->detail, "cheri_sigprot_%d", code);
#endif
      } else if (sig == SIGILL || sig == SIGTRAP) {
        // musl's malloc aborts via __builtin_trap on detected corruption.
        strcpy(o->outcome, "runtime_abort");
        snprintf(o->detail, sizeof o->detail, "%s",
                 sig == SIGILL ? "sigill" : "sigtrap");
      } else if (sig == SIGSEGV) {
        strcpy(o->outcome, "crash");
        snprintf(o->detail, sizeof o->detail, "%s",
                 code == SEGV_MAPERR   ? "segv_maperr"
                 : code == SEGV_ACCERR ? "segv_accerr"
                                       : "segv_other");
        if (code != SEGV_MAPERR && code != SEGV_ACCERR)
          snprintf(o->detail, sizeof o->detail, "segv_code_%d", code);
      } else {
        strcpy(o->outcome, "crash");
        snprintf(o->detail, sizeof o->detail, "sig%d_code_%d", sig, code);
      }
      return;
    }
    if (st >= EXIT_OBS_BASE && st < EXIT_OBS_BASE + 8) {
      int obs = st - EXIT_OBS_BASE;
      strcpy(o->outcome, "silent");
      strcpy(o->detail, obs_name(obs));
      return;
    }
    strcpy(o->outcome, "exit");
    snprintf(o->detail, sizeof o->detail, "status_%d", st);
    return;
  }

  if (WIFSIGNALED(status)) {
    int sig = WTERMSIG(status);
    strcpy(o->timing, timing_of(stage));
    if (sig == SIGALRM) {
      strcpy(o->outcome, "hang");
    } else if (sig == SIGABRT && strstr(err, "stack smashing")) {
      strcpy(o->outcome, "runtime_abort");
      strcpy(o->detail, "stack_protector");
    } else if (sig == SIGABRT && strstr(err, "buffer overflow detected")) {
      strcpy(o->outcome, "runtime_abort");
      strcpy(o->detail, "fortify_source");
    } else if (sig == SIGABRT && find_libc_message(err, o->detail, sizeof o->detail)) {
      strcpy(o->outcome, "runtime_abort");
    } else if (sig == SIGABRT) {
      strcpy(o->outcome, "runtime_abort");
      strcpy(o->detail, "abort");
    } else {
      strcpy(o->outcome, "crash");
      snprintf(o->detail, sizeof o->detail, "sig%d", sig);
    }
    return;
  }
  strcpy(o->outcome, "unknown");
}

static void run_once(const struct bug *b, struct outcome *o) {
  memset((void *)g_state, 0, sizeof *g_state);
  g_state->obs = -1;

  int errp[2];
  if (pipe(errp) != 0) {
    perror("pipe");
    exit(1);
  }
  fflush(NULL);
  pid_t pid = fork();
  if (pid < 0) {
    perror("fork");
    exit(1);
  }
  if (pid == 0) {
    close(errp[0]);
    dup2(errp[1], STDERR_FILENO);
    close(errp[1]);
    child_setup();
    int obs = b->fn();
    _exit(EXIT_OBS_BASE + obs);
  }
  close(errp[1]);

  static char err[STDERR_MAX + 1];
  size_t len = 0;
  for (;;) {
    ssize_t r = read(errp[0], err + len, STDERR_MAX - len);
    if (r > 0) {
      len += (size_t)r;
      if (len == STDERR_MAX) {
        char sink[4096]; // keep draining so the child never blocks
        while (read(errp[0], sink, sizeof sink) > 0) {
        }
        break;
      }
    } else if (r == 0 || errno != EINTR) {
      break;
    }
  }
  err[len] = 0;
  close(errp[0]);

  int status;
  while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {
  }
  classify(status, err, o);
}

/* ----------------------------- aggregation ------------------------------ */

#define MAX_DISTINCT 16

struct tally {
  struct outcome o;
  int count;
};

static void print_csv_header(FILE *out) {
  fprintf(out, "config,bug,class,outcome,detail,timing,count,runs\n");
}

static void run_bug(FILE *out, const char *config, const struct bug *b, int runs) {
  struct tally t[MAX_DISTINCT];
  int nt = 0;
  for (int r = 0; r < runs; r++) {
    struct outcome o;
    run_once(b, &o);
    int k;
    for (k = 0; k < nt; k++)
      if (!strcmp(t[k].o.outcome, o.outcome) && !strcmp(t[k].o.detail, o.detail) &&
          !strcmp(t[k].o.timing, o.timing))
        break;
    if (k == nt) {
      if (nt == MAX_DISTINCT) {
        k = nt - 1; // fold the tail into the last bucket
      } else {
        t[nt].o = o;
        t[nt].count = 0;
        nt++;
      }
    }
    t[k].count++;
  }
  for (int k = 0; k < nt; k++) {
    fprintf(out, "%s,%s,%s,%s,%s,%s,%d,%d\n", config, b->id, b->cls,
            t[k].o.outcome, t[k].o.detail, t[k].o.timing, t[k].count, runs);
    fprintf(stderr, "  %-24s %-14s %-40s %-7s %4d/%d\n", b->id, t[k].o.outcome,
            t[k].o.detail, t[k].o.timing, t[k].count, runs);
  }
  fflush(out);
}

int main(int argc, char **argv) {
  const char *config = NULL, *only = NULL, *outpath = NULL;
  int runs = 100, list = 0, opt;
  while ((opt = getopt(argc, argv, "c:n:b:o:l")) != -1) {
    switch (opt) {
    case 'c': config = optarg; break;
    case 'n': runs = atoi(optarg); break;
    case 'b': only = optarg; break;
    case 'o': outpath = optarg; break;
    case 'l': list = 1; break;
    default:
      fprintf(stderr, "usage: %s -c config [-n runs] [-b bug] [-o out.csv] [-l]\n", argv[0]);
      return 2;
    }
  }
  if (list) {
    for (size_t i = 0; i < g_nbugs; i++)
      printf("%-24s %-30s %s\n", g_bugs[i].id, g_bugs[i].cls, g_bugs[i].desc);
    return 0;
  }
  if (!config || runs < 1) {
    fprintf(stderr, "error: -c <config> is required (and -n must be >= 1)\n");
    return 2;
  }

  g_state = mmap(NULL, sizeof *g_state, PROT_READ | PROT_WRITE,
                 MAP_SHARED | MAP_ANONYMOUS, -1, 0);
  if (g_state == MAP_FAILED) {
    perror("mmap");
    return 1;
  }

  FILE *out = stdout;
  if (outpath && !(out = fopen(outpath, "w"))) {
    perror(outpath);
    return 1;
  }
  print_csv_header(out);
  fprintf(stderr, "config=%s runs=%d\n", config, runs);
  int found = 0;
  for (size_t i = 0; i < g_nbugs; i++) {
    if (only && strcmp(only, g_bugs[i].id))
      continue;
    found = 1;
    run_bug(out, config, &g_bugs[i], runs);
  }
  if (out != stdout)
    fclose(out);
  if (only && !found) {
    fprintf(stderr, "error: unknown bug '%s'\n", only);
    return 2;
  }
  return 0;
}
