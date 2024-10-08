/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "structure_interface.h"
#include "cuckoo_trie.h"
#include <string.h>

typedef struct {
	int key_size;
	int value_size;
	uint8_t bytes[2 * sizeof(uint64_t)];
} _ct_kv;

void*   ds_init(uint64_t size) {
    void* ds = (void*)(ct_alloc(size));
    assert(ds != NULL);
    return ds;
}

void ds_thread_init(void *ds) {
    /* no initialization needed */
}

int ds_insert(void* ds, uint64_t key, uint64_t value) {
    _ct_kv* data = (_ct_kv*)malloc(sizeof(_ct_kv));
    kv_init((ct_kv*)data, sizeof(uint64_t), sizeof(uint64_t));

    uint64_t dummy[2] = {key, value};
    memcpy(data->bytes, dummy,  sizeof(dummy));
    return ct_insert((cuckoo_trie*)(ds), (ct_kv*)data);
}

int ds_update(void* ds, uint64_t key, uint64_t value) {
    _ct_kv* data = (_ct_kv*)malloc(sizeof(_ct_kv));
    kv_init((ct_kv*)data, sizeof(uint64_t), sizeof(uint64_t));
    
    uint64_t dummy[2] = {key, value};
    memcpy(data->bytes, dummy,  sizeof(dummy));
    return ct_update((cuckoo_trie*)(ds), (ct_kv*)data);
}

int ds_read(void* ds, uint64_t key) {
    ct_kv* data = ct_lookup((cuckoo_trie*)(ds), sizeof(uint64_t), (uint8_t*)(&key));
    return data != NULL;
}

int ds_read_range(void* ds, uint64_t key, uint64_t len) {
    int status = 0;
    for(int i=key; i<key+len; i++) {
        status |= ds_read(ds, i);
    }
    return status;
}

int ds_remove(void* ds, uint64_t key) {
    return 0;       /* not supported - read documentation */
}

uint64_t ds_get_size(void* ds) {
    return 0;
}
