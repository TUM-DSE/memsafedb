/*
*   @details:
*       1. Generate 64bit keys and 64bit values from an uniform random distribution to be inserted, removed or queried.
*       2. Evaluation of Insertion: from 0% -> filling_factor of the total capacity.
*       3. Evaluation of Queries: Positive and Negative queries (queries_factor) (success_factor).
*       4. Evaluation of Deletion: Remove a selections of keys until the usage reaches ~50%.
*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "utils.hpp"
#include "hash.hpp"
#include <nlohmann/json.hpp>
#include <iostream>
#include <functional>
#include <vector>
#include <time.h>
#include <fstream>
#include <thread>

void*       libhandle = nullptr;
void*       generic_structure = nullptr;

void*       (*ds_init)(uint64_t);
void        (*ds_thread_init)(void*);
int         (*ds_insert)(void*, uint64_t, uint64_t);
int         (*ds_remove)(void*, uint64_t);
int         (*ds_read)(void*, uint64_t);
int         (*ds_read_range)(void*, uint64_t, uint64_t);
uint64_t    (*ds_get_size)(void*);

/* hashing function */
uint64_t            (*hash_fn)(uint64_t);

/* parameters */
std::vector<uint64_t> used_keys;
std::mutex            g_mutex;
Barrier               tbarrier;

/* data extracted from the program */
LogFile logfilePerformance("");
LogFile logfileMemory("");

uint64_t next_value() {
    static uint64_t current_value = 0;
    g_mutex.lock();
    int result = current_value++;
    g_mutex.unlock();
    return result;
}

void dataset_performfill(const size_t thread_id, void* ds,
                         const double filling_factor, const uint64_t maximum_capacity) {
    const uint64_t capacity = filling_factor * maximum_capacity;
    uint64_t status = 0;
    std::chrono::time_point<std::chrono::system_clock> start_time, end_time;

    for (uint64_t i=0; i<capacity; i++) {
        const uint64_t key_num  = next_value();
        const uint64_t key      = hash_fn(key_num);
        const uint64_t value    = hash_fn(next_value());

        MEASURE_TIME(ds_insert(ds, key, value),  start_time, end_time, status);
        logfilePerformance.add_log("dataset_performfill", thread_id, key_num, key, value, status, start_time, end_time);

        g_mutex.lock();
        uint64_t memory_usage = ds_get_size(ds);
        logfileMemory.add_log_mem("dataset_performfill", thread_id, key_num, memory_usage);
        used_keys.push_back(key_num);
        g_mutex.unlock();
    }
}

void dataset_performqueries(const size_t thread_id, void* ds,
                         const double query_factor, const double success_factor,
                         const uint64_t maximum_capacity) {
    const uint64_t capacity = query_factor * maximum_capacity,
                   success_capacity = success_factor * capacity;
    uint64_t status = 0;
    std::chrono::time_point<std::chrono::system_clock> start_time, end_time;    
    for (uint64_t i=0; i<capacity; i++) {
        uint64_t key_num = 0;
        if (success_capacity > 0 && i % (capacity / success_capacity) == 0) {
            g_mutex.lock();
            key_num   = used_keys[rand() % used_keys.size()];
            g_mutex.unlock();
        } else {
            key_num  = next_value();
        }

        const uint64_t key      = hash_fn(key_num);
        MEASURE_TIME(ds_read(ds, key),  start_time, end_time, status);
        logfilePerformance.add_log("dataset_performqueries", thread_id, key_num, key, 0, status, start_time, end_time);
    }
}

void dataset_performdeletion(const size_t thread_id, void* ds,
                         const double deletion_factor, const double success_factor,
                         const uint64_t maximum_capacity) {
    const uint64_t capacity = deletion_factor * maximum_capacity,
                   success_capacity = success_factor * capacity;
    uint64_t status = 0, success_count = 0;
    std::chrono::time_point<std::chrono::system_clock> start_time, end_time;    
    for (uint64_t i=0; i<capacity; i++) {
        uint64_t key_num = 0;
        if (success_capacity > 0 && i % (capacity / success_capacity) == 0) {
            g_mutex.lock();
            uint64_t index_random = rand() % used_keys.size();
            while(used_keys[index_random] == -1) { index_random = rand() % used_keys.size(); }

            key_num   = used_keys[index_random];
            used_keys[index_random] = -1;
            g_mutex.unlock();
        } else {
            key_num  = next_value();
        }
        const uint64_t key      = hash_fn(key_num);

        MEASURE_TIME(ds_remove(ds, key),  start_time, end_time, status);
        logfilePerformance.add_log("dataset_performdeletion", thread_id, key_num, key, 0, status, start_time, end_time);
    }
}

void benchmark_threads(const uint64_t threadid, nlohmann::json config_data, const uint64_t num_threads,
                       void *ds, const uint64_t capacity) {
    #ifdef DIFF_CPU_EXEC
        /* each thread will be executed on a different CPU */
        pthread_t self = pthread_self();
        cpu_set_t cpuset;
        CPU_ZERO(&cpuset);
        CPU_SET(threadid, &cpuset);
    #endif
    ds_thread_init(ds);

    const double   filling_factor  = config_data["performfill"]["filling_factor"];
    const uint64_t thread_capacity = capacity/num_threads;
    dataset_performfill(threadid, ds, filling_factor, thread_capacity);
    tbarrier.wait();

    const double  query_factor   = config_data["performquery"]["query_factor"];
    double  success_factor = config_data["performquery"]["success_factor"];
    dataset_performqueries(threadid, ds, query_factor, success_factor, thread_capacity);
    tbarrier.wait();

    const double  deletion_factor = config_data["performdeletion"]["deletion_factor"];
    success_factor  = config_data["performdeletion"]["success_factor"];
    dataset_performdeletion(threadid, ds, deletion_factor, success_factor, thread_capacity);
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        std::cerr << "[error] format: <path to so> <path to config file> <log file name>" << std::endl;
        exit(1);
    }
    srand(time(NULL));      /* prepare the randomness */

    std::string libpath   = argv[1];

    std::ifstream f(argv[2]);
    nlohmann::json config_data = nlohmann::json::parse(f);
    logfilePerformance.set_name(std::string(argv[3]) + "_performance.out");
    logfileMemory.set_name(std::string(argv[3]) + "_memory.out");

    const uint64_t num_threads = config_data["threadnum"];
    if (std::thread::hardware_concurrency() < num_threads) {
        std::cerr << "[error] the CPU has only " << std::thread::hardware_concurrency()
                << " while the threads num. is " << num_threads << std::endl;
        exit(1);
    }

    if (initialize(libpath) != 0) {
        std::cerr << "[error] failed: " << std::endl;
        exit(1);
    }

    if (config_data["distribution"] == "zipfian") {
        hash_fn = hash_zipfian;
    } else if (config_data["distribution"] == "uniform") {
        hash_fn = hash_uniform;
    } else {
        throw std::runtime_error("unknown distribution type");
    }

    /* thread barrier initialization */
    tbarrier.set_numthreads(num_threads);

    /* all functions have been loaded at this point */
    const uint64_t capacity  = config_data["capacity"];
    void* ds = ds_init(capacity);
    
    const uint64_t thread_capacity = capacity/num_threads;
    EXECUTE_PARALLEL(num_threads, benchmark_threads, config_data, num_threads, ds, capacity);

    logfilePerformance.save_logfile();
    logfileMemory.save_logfile();
    return 0;
}