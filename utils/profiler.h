#ifndef PROFILER_H
#define PROFILER_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <time.h>
#include <stdio.h>
#include <string.h>

#ifndef PROFILER_MAX_ENTRIES
#define PROFILER_MAX_ENTRIES 256
#endif

#ifndef PROFILER_NAME_MAX_LEN
#define PROFILER_NAME_MAX_LEN 64
#endif

typedef struct {
    const char* name;
    uint64_t total_value;
    uint64_t call_count;
} ProfilerEntry;

ProfilerEntry profiler_data[PROFILER_MAX_ENTRIES] __attribute__((weak)) = {0};
int profiler_entry_count __attribute__((weak)) = 0;

static inline uint64_t profiler_get_value(void) {
#ifdef PROFILER_USE_CYCLES
    uint64_t val;
    asm volatile("mrs %0, cntvct_el0" : "=r" (val));
    return val;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

static inline ProfilerEntry* profiler_register(const char* name) {
    for (int i = 0; i < profiler_entry_count; i++) {
        if (profiler_data[i].name && strcmp(profiler_data[i].name, name) == 0) {
            return &profiler_data[i];
        }
    }
    if (profiler_entry_count < PROFILER_MAX_ENTRIES) {
        ProfilerEntry* entry = &profiler_data[profiler_entry_count++];
        entry->name = name;
        entry->total_value = 0;
        entry->call_count = 0;
        return entry;
    }
    return NULL;
}

static inline void profiler_print_stats(void) {
    // MODIFICATION: Check if anything was recorded before printing
    if (profiler_entry_count == 0) {
        return;
    }

    printf("\n");
    printf("=============================================================\n");
#ifdef PROFILER_USE_CYCLES
    printf(" Profiling Results (AArch64 Cycles)\n");
    printf("=============================================================\n");
    printf("%-20s | %-12s | %-15s | %-15s\n", "Section", "Calls", "Total (Cyc)", "Avg (Cyc)");
#else
    printf(" Profiling Results (Time)\n");
    printf("=============================================================\n");
    printf("%-20s | %-12s | %-15s | %-15s\n", "Section", "Calls", "Total (ns)", "Avg (ns)");
#endif
    printf("-------------------------------------------------------------\n");

    for (int i = 0; i < profiler_entry_count; i++) {
        ProfilerEntry* e = &profiler_data[i];
        if (!e->name) continue;

        uint64_t avg = (e->call_count > 0) ? (e->total_value / e->call_count) : 0;

        printf("%-20s | %-12llu | %-15llu | %-15llu\n",
               e->name,
               (unsigned long long)e->call_count,
               (unsigned long long)e->total_value,
               (unsigned long long)avg);
    }
    printf("=============================================================\n\n");
}

/* * MACROS 
 */

#define PROFILER_DEFINE(ID, COUNT) \
    static ProfilerEntry* _prof_entries_##ID[COUNT]; \
    static int _prof_init_##ID = 0; \
    static char _prof_names_##ID[COUNT][PROFILER_NAME_MAX_LEN]; \
    if (!_prof_init_##ID) { \
        for (int i = 0; i < COUNT; i++) { \
            snprintf(_prof_names_##ID[i], PROFILER_NAME_MAX_LEN, "%s-%d", #ID, i); \
            _prof_entries_##ID[i] = profiler_register(_prof_names_##ID[i]); \
        } \
        _prof_init_##ID = 1; \
    } \
    uint64_t _prof_ts_##ID[COUNT + 1]; \
    int _prof_idx_##ID = 0; \
    int _prof_count_##ID = COUNT; \
    _prof_ts_##ID[_prof_idx_##ID++] = profiler_get_value();

#define PROFILER_RECORD(ID) \
    if (_prof_idx_##ID <= _prof_count_##ID) { \
        _prof_ts_##ID[_prof_idx_##ID++] = profiler_get_value(); \
    }

#define PROFILER_COLLECT(ID) \
    PROFILER_RECORD(ID); \
    for (int i = 0; i < _prof_count_##ID; i++) { \
        if (_prof_entries_##ID[i]) { \
            uint64_t delta = _prof_ts_##ID[i+1] - _prof_ts_##ID[i]; \
            _prof_entries_##ID[i]->total_value += delta; \
            _prof_entries_##ID[i]->call_count++; \
        } \
    }

#ifdef __cplusplus
}
#endif

#endif
