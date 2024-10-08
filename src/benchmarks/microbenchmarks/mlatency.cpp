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
#include <atomic>
#include <random>
#include <chrono>
#include <algorithm>

/* read functions from the shared-library */
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
std::vector<uint64_t> usedkeys;
std::mutex            g_mutex;
Barrier               tbarrier;

/* ordering parameter */
std::chrono::time_point<std::chrono::high_resolution_clock> gstart_time;

/* data extracted from the program */
LogFile logfilePerformance("");

/* workaround for perforator */
extern "C" {
    int _ds_insert(void* ds, uint64_t key, uint64_t value) { return ds_insert(ds, key, value); }
    int _ds_read(void* ds, uint64_t key) {  return ds_read(ds, key); }
    int _ds_remove(void* ds, uint64_t key) { return ds_remove(ds, key); }
}

void dataset_performfill(const size_t num_threads, const size_t thread_id, 
                         void* ds, const uint64_t capacity) {
    std::chrono::nanoseconds duration;
    std::vector<std::pair<uint64_t, uint64_t>> latencies(capacity);

    for (uint64_t i=0; i<capacity; i++) {
        const uint64_t key_num  = i * num_threads + thread_id;
        const uint64_t key      = hash_fn(key_num) % capacity;
        const uint64_t value    = hash_fn(key_num * key_num);   /* insert a random key */

        MEASURE_TIME(_ds_insert(ds, key, value), duration);

        std::chrono::nanoseconds order = std::chrono::high_resolution_clock::now() - gstart_time;
        latencies.push_back({order.count(), duration.count()});
    }
    logfilePerformance.add_log("dataset_performfill", latencies);
}

void dataset_performquery(const size_t num_threads, const size_t thread_id, void* ds,
                         const double success_factor, const uint64_t thread_capacity, const double query_factor,
                         std::vector<uint64_t> qkeys) {
    uint64_t qindex = 0;
    std::chrono::nanoseconds duration;
    std::vector<std::pair<uint64_t, uint64_t>> latencies; 
    for (uint64_t i=0; i<thread_capacity * query_factor; i++) {
        uint64_t key_num = (thread_capacity + i + 1) * num_threads + thread_id;    /* take a value outside of the generated keys */
        if (success_factor > 0 && i % static_cast<uint64_t>(thread_capacity / success_factor) == 0) {
            key_num   = qkeys[qindex++];
        }
        const uint64_t key      = hash_fn(key_num);
        MEASURE_TIME(_ds_read(ds, key),  duration);

        std::chrono::nanoseconds order = std::chrono::high_resolution_clock::now() - gstart_time;
        latencies.push_back({order.count(), duration.count()});
    }
    logfilePerformance.add_log("dataset_performquery", latencies);
}

void dataset_performdeletion(const size_t num_threads, const size_t thread_id, void* ds,
                            const double success_factor, const uint64_t thread_capacity, const double deletion_factor,
                            std::vector<uint64_t> rkeys) {
    uint64_t rorder = 0;
    std::chrono::nanoseconds duration;
    std::vector<std::pair<uint64_t, uint64_t>> latencies; 
    for (uint64_t i=0; i<thread_capacity * deletion_factor; i++) {
        uint64_t key_num = (thread_capacity + i + 1) * num_threads + thread_id;
        if (success_factor > 0 &&  i % static_cast<uint64_t>(thread_capacity / success_factor) == 0) {
            key_num  = rkeys[rorder++];
        }
        const uint64_t key      = hash_fn(key_num);
        MEASURE_TIME(_ds_remove(ds, key), duration);

        std::chrono::nanoseconds order = std::chrono::high_resolution_clock::now() - gstart_time;
        latencies.push_back({order.count(), duration.count()});
    }
    logfilePerformance.add_log("dataset_performdeletion", latencies);
}

void benchmark_threads(const uint64_t num_threads, const uint64_t threadid,
                       nlohmann::json config_data,
                       void *ds, const uint64_t capacity) {
#ifdef DIFF_CPU_EXEC
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(threadid, &cpuset);  // threadid is the desired CPU core index
#if defined(__arm__) || defined(__aarch64__)
    int result = sched_setaffinity(0, sizeof(cpuset), &cpuset);
    if (result != 0) { perror("sched_setaffinity"); }
#else
    CPU_SET(threadid, &cpuset);  // threadid is the desired CPU core index
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
#endif
#endif
    ds_thread_init(ds);
    const uint64_t thread_capacity = capacity/num_threads;
    const double filling_factor = config_data["performfill"]["filling_factor"];

    tbarrier.wait();
    dataset_performfill(num_threads, threadid, ds, static_cast<uint64_t>(thread_capacity * filling_factor));
    tbarrier.wait();


    /* query mechanism */
    const double query_factor   = config_data["performquery"]["query_factor"];
    double success_factor       = config_data["performquery"]["success_factor"];

    std::vector<uint64_t> qkey;
    /* prepare the query mechanism, gmutex or cheri */
    g_mutex.lock();
    for(int i=0; i<query_factor * thread_capacity; i++) {
        qkey.push_back(rand() % capacity);
    }
    g_mutex.unlock();

    tbarrier.wait();
    dataset_performquery(num_threads, threadid, ds,
                        success_factor, thread_capacity, query_factor, qkey);
    tbarrier.wait();


    /* deletion mechanism */
    const double deletion_factor = config_data["performdeletion"]["deletion_factor"];
    success_factor               = config_data["performdeletion"]["success_factor"];

    /* prepare the keys to remove*/
    g_mutex.lock();
    std::vector<uint64_t> rkey;
    for(int i=0; i<deletion_factor * thread_capacity; i++) {
        rkey.push_back(usedkeys[threadid * thread_capacity + i]);
    }
    g_mutex.unlock();

    tbarrier.wait();
    dataset_performdeletion(num_threads, threadid, ds,
                            success_factor, thread_capacity, deletion_factor, rkey);
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

    /* used keys filling for deletion procedure */
    std::random_device rd;
    std::mt19937 gen_rd(rd());

    for(uint64_t i=0; i<capacity; i++) { usedkeys.push_back(i); }
    std::shuffle(usedkeys.begin(), usedkeys.end(), gen_rd);
    
    EXECUTE_PARALLEL(num_threads, benchmark_threads, config_data, ds, capacity);
    logfilePerformance.save_logfile();
    return 0;
}