/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#pragma once

#include <string>
#include <iostream>
#include <mutex>
#include <vector>
#include <dlfcn.h>
#include <stdlib.h>
#include <chrono>
#include <condition_variable>

#define MEASURE_TIME(func, duration) {                                              \
    std::chrono::time_point<std::chrono::high_resolution_clock> start_time;         \
    try {                                                                           \
        start_time = std::chrono::high_resolution_clock::now();                     \
        func;                                                                       \
        duration   = std::chrono::high_resolution_clock::now() - start_time;        \
    } catch (...) {                                                                 \
        duration   = std::chrono::high_resolution_clock::now() - start_time;        \
    }                                                                               \
}

#define EXECUTE_PARALLEL(threadnum, func, ...) {                    \
    std::vector<std::thread> threads;                               \
    for (size_t i = 0; i < threadnum; i++) {                        \
        threads.emplace_back(func, threadnum, i, ##__VA_ARGS__);    \
    }                                                               \
                                                                    \
    for (auto& thread : threads) {                                  \
        thread.join();                                              \
    }                                                               \
}

/* the datastructure pointer */
extern void*       libhandle;
extern void*       generic_structure;

extern void*       (*ds_init)(uint64_t);
extern void        (*ds_thread_init)(void*);
extern int         (*ds_insert)(void*, uint64_t, uint64_t);
extern int         (*ds_remove)(void*, uint64_t);
extern int         (*ds_read)(void*, uint64_t);
extern int         (*ds_read_range)(void*, uint64_t, uint64_t);
extern uint64_t    (*ds_get_size)(void*);

uint64_t initialize(std::string libpath);

class LogFile {
public:
    LogFile(std::string log_name);
    void add_log(std::string, std::vector<std::pair<uint64_t, uint64_t>>);
    void save_logfile();
    void set_name(std::string log_name) { this->log_name = log_name; }
private:
    std::string   log_name;
    std::mutex    g_mutex;
    std::vector<std::string> latency_logs;
};

class Barrier {
public:
    Barrier() : num_threads(0), count(0) {}

    void set_numthreads(const uint64_t num_threads) {
        this->num_threads = num_threads;
    }
    
    void wait() {
        std::unique_lock<std::mutex> lock(mtx);
        count += 1;
        if (count % num_threads == 0) {
            cv.notify_all();
        } else {
            cv.wait(lock);
        }
    }

private:
    std::mutex mtx;
    std::condition_variable cv;
    std::uint64_t num_threads;
    volatile std::uint64_t count;
};
