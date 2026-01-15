#include <cstdint>
#include <string>

#include <profiler.h>

__attribute__((noinline)) void target_function(uint64_t i) {
  std::string s = std::to_string(i);
}

int main() {
  const long long ITERATIONS = 100000000;

  for (uint64_t i = 0; i < ITERATIONS; ++i) {
    
    PROFILER_BEGIN(func);
    target_function(i);
    PROFILER_END(func);
  }

  profiler_print_stats();

  return 0;
}
