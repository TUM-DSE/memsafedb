//
// Created by t-rdichler on 17.12.2024.
//

#ifndef CHASHTABLE_CHASHTABLE_H
#define CHASHTABLE_CHASHTABLE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>



typedef struct chashtable chashtable_t;

void
chashtable_deinit(chashtable_t *ht);

chashtable_t *
chashtable_init(uint64_t capacity);

chashtable_t *
chashtable_put(chashtable_t *ht, uint8_t *key, uint8_t *val);

uint8_t *
chashtable_get(chashtable_t *ht, uint8_t *key);

void
chashtable_remove(chashtable_t *ht, uint8_t *key);

#ifdef __cplusplus
}
#endif

#endif //CHASHTABLE_CHASHTABLE_H
