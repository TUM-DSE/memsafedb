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

void LogFile::add_log(std::string function_name,
        std::vector<std::pair<uint64_t, uint64_t>> durations) {

  g_mutex.lock();
  for (int i=0; i<durations.size(); i++) {
    std::ostringstream log_entry;
    log_entry << function_name << " " << durations[i].first << " " << durations[i].second;
    this->latency_logs.push_back(log_entry.str());
  }
  g_mutex.unlock();
}

void LogFile::save_logfile() {
  std::ofstream fout(this->log_name);
  for (size_t i=0; i < this->latency_logs.size(); i++) {
    fout << this->latency_logs[i] << std::endl;
  }
}