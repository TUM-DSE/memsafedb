/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#pragma once

#include <stdlib.h>
#include <stdint.h>
#include <assert.h>
#include <pthread.h>

/* returns success - true (0) and fail - false (1) */

#define SUCCESS     0
#define FAIL        1

#define MAXIMUM_BUCKET_NUM 1000000

#ifdef __cplusplus
extern "C" {
#endif

void*    ds_init       (uint64_t size);
void     ds_thread_init(void* ds);
int      ds_insert     (void* ds, uint64_t key, uint64_t value);
int      ds_update     (void* ds, uint64_t key, uint64_t value);
int      ds_read       (void* ds, uint64_t key); 
int      ds_read_range (void *ds, uint64_t key, uint64_t len);
int      ds_remove     (void* ds, uint64_t key);
uint64_t ds_get_size   (void* ds);  /* the size in kb */

#ifdef __cplusplus
}
#endif