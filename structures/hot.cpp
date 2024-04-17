/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "structure_interface.h"
#include <hot/rowex/HOTRowex.hpp>
#include <idx/contenthelpers/IdentityKeyExtractor.hpp>
#include <idx/contenthelpers/OptionalValue.hpp>

extern "C" {
using TrieType = hot::rowex::HOTRowex<uint64_t, idx::contenthelpers::IdentityKeyExtractor>;

void*   ds_init(uint64_t size) {
    return static_cast<void*>(new TrieType());
}

void    ds_thread_init(void* ds) {}

int     ds_insert(void* ds, uint64_t key, uint64_t value) {
    TrieType* dc = static_cast<TrieType *>(ds);
    return dc->insert(key);
}

int     ds_update(void* ds, uint64_t key, uint64_t value) {
    return ds_insert(ds, key, value);
}

int     ds_read(void* ds, uint64_t key) {
    TrieType* dc = static_cast<TrieType *>(ds);
    idx::contenthelpers::OptionalValue<uint64_t> result = dc->lookup(key);
	return result.mIsValid & (result.mValue == key);
}

int     ds_read_range(void* ds, uint64_t key, uint64_t len) {
    for (uint64_t i=0; i<len; i++) {
        ds_read(ds, key + i);
    }
    return 0;
}

int     ds_remove(void* ds, uint64_t key) {
    /* has no remove operation implemented */
    return 0;
}

uint64_t ds_get_size(void* ds) {
    /* to be calculated, sometime */
    return 0;
}

}