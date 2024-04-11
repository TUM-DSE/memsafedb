#pragma once

#include <algorithm>
#include <cstdint>
#include <exception>
#include <random>
#include <locale>

#if defined(_MSC_VER)
#if _MSC_VER >= 1911
#define MAYBE_UNUSED [[maybe_unused]]
#else
#define MAYBE_UNUSED
#endif
#elif defined(__GNUC__)
#define MAYBE_UNUSED __attribute__ ((unused))
#endif


const uint64_t kFNVOffsetBasis64 = 0xCBF29CE484222325ull;
const uint64_t kFNVPrime64 = 1099511628211ull;

inline uint64_t FNVHash64(uint64_t val) {
  uint64_t hash = kFNVOffsetBasis64;

  for (int i = 0; i < 8; i++) {
    uint64_t octet = val & 0x00ff;
    val = val >> 8;

    hash = hash ^ octet;
    hash = hash * kFNVPrime64;
  }
  return hash;
}

inline uint64_t hash_zipfian(uint64_t val) { return FNVHash64(val); }

inline uint64_t hash_uniform(uint64_t val) { return val; }