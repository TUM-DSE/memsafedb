#include "utils.hpp"
#include <sstream>
#include <fstream>
#include <time.h>
#include <stdarg.h>

uint64_t initialize(std::string libpath) {
  /* initialize the datastructure */
  libhandle = dlopen(libpath.c_str(), RTLD_LAZY);
  if (libhandle == nullptr) {
    std::cerr << "unable to load the library " << libpath  << "reason: " << dlerror() << std::endl;
    return 1;
  }

  /* load the functions */
  ds_init   = (void* (*)(uint64_t))dlsym(libhandle,  "ds_init");
  if (ds_init == nullptr) {
    std::cerr << "unable to load the function ds_init from the library " << libpath << std::endl;
    return 1;
  }

  ds_thread_init  = (void (*)(void*))dlsym(libhandle,  "ds_thread_init");
  if (ds_init == nullptr) {
    std::cerr << "unable to load the function ds_thread_init from the library " << libpath << std::endl;
    return 1;
  }

  ds_insert = (int (*)(void*, uint64_t, uint64_t))dlsym(libhandle, "ds_insert");
  if (ds_insert == nullptr) {
    std::cerr << "unable to load the function ds_insert from the library " << libpath << std::endl;
    return 1;
  }

  ds_remove = (int (*)(void*, uint64_t))dlsym(libhandle, "ds_remove");
  if (ds_remove == nullptr) {
    std::cerr << "unable to load the function ds_remove from the library " << libpath << std::endl;
    return 1;
  }

  ds_read = (int (*)(void*, uint64_t))dlsym(libhandle, "ds_read");
  if (ds_remove == nullptr) {
    std::cerr << "unable to load the function ds_read from the library " << libpath << std::endl;
    return 1;
  }

  ds_read_range = (int (*)(void*, uint64_t, uint64_t))dlsym(libhandle, "ds_read_range");
  if (ds_remove == nullptr) {
    std::cerr << "unable to load the function ds_read_range from the library " << libpath << std::endl;
    return 1;
  }

  ds_get_size = (uint64_t (*)(void*))dlsym(libhandle, "ds_get_size");
  if (ds_remove == nullptr) {
    std::cerr << "unable to load the function ds_get_size from the library " << libpath << std::endl;
    return 1;
  }
  return 0;
}

LogFile::LogFile(std::string log_name) {
  this->log_name = log_name;
}

void LogFile::add_log(std::string function_name, uint64_t thread_id, uint64_t key_num,
        uint64_t key, uint64_t value, uint64_t status,
        std::chrono::time_point<std::chrono::system_clock> start_time, 
        std::chrono::time_point<std::chrono::system_clock> end_time) {
  std::ostringstream log_entry;
  
  auto dstart_time = start_time.time_since_epoch();
  auto dend_time   = end_time.time_since_epoch();

  g_mutex.lock();
  log_entry << function_name
            << " " << thread_id
            << " " << key_num
            << " " << key
            << " " << value
            << " " << status
            << " " << std::chrono::duration_cast<std::chrono::nanoseconds>(dstart_time).count()
            << " " << std::chrono::duration_cast<std::chrono::nanoseconds>(dend_time).count();
    this->latency_logs.push_back(log_entry.str());
    g_mutex.unlock();
}

void LogFile::add_log_mem(std::string function_name, uint64_t thread_id, uint64_t key_num, uint64_t memory_usage) {
  std::ostringstream log_entry;
  g_mutex.lock();
  log_entry << function_name
            << " " << thread_id
            << " " << key_num
            << " " << memory_usage;
  this->latency_logs.push_back(log_entry.str());
  g_mutex.unlock();
}

void LogFile::save_logfile() {
  std::ofstream fout(this->log_name);
  for (size_t i=0; i < this->latency_logs.size(); i++) {
    fout << this->latency_logs[i] << std::endl;
  }
}