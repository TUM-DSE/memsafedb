/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "structure_interface.h"
#include <tbb/concurrent_hash_map.h>


extern "C" {

void*   ds_init(uint64_t size) {
    /*
    * the hash table is partitioned into an array of buckets, each of which contains SLOT_PER_BUCKET
    * slots to store items
    */
    return static_cast<void*>(new tbb::concurrent_hash_map<uint64_t, uint64_t>(size));
}

void    ds_thread_init(void* ds) {}

int     ds_insert(void* ds, uint64_t key, uint64_t value) {
    tbb::concurrent_hash_map<uint64_t, uint64_t>* dc =
        static_cast<tbb::concurrent_hash_map<uint64_t, uint64_t> *>(ds);
    tbb::concurrent_hash_map<uint64_t, uint64_t>::accessor accessor; 
    int result = dc->insert(accessor, key);
    accessor->second = value;
    return result;
}

int     ds_update(void* ds, uint64_t key, uint64_t value) {
    return ds_insert(ds, key, value);
}

int     ds_read(void* ds, uint64_t key) {
    tbb::concurrent_hash_map<uint64_t, uint64_t>* dc =
        static_cast<tbb::concurrent_hash_map<uint64_t, uint64_t> *>(ds);
    tbb::concurrent_hash_map<uint64_t, uint64_t>::accessor accessor; 
    return dc->find(accessor, key);
}

int     ds_read_range(void* ds, uint64_t key, uint64_t len) {
    for (uint64_t i=0; i<len; i++) {
        ds_read(ds, key + i);
    }
    return 0;
}

int     ds_remove(void* ds, uint64_t key) {
    tbb::concurrent_hash_map<uint64_t, uint64_t>* dc =
        static_cast<tbb::concurrent_hash_map<uint64_t, uint64_t> *>(ds);
    return dc->erase(key);
}

uint64_t ds_get_size(void* ds) {
    tbb::concurrent_hash_map<uint64_t, uint64_t>* dc =
        static_cast<tbb::concurrent_hash_map<uint64_t, uint64_t> *>(ds);
    
    using bucket = struct tbb::detail::d2::hash_map_base<tbb::detail::d1::tbb_allocator<std::pair<const long unsigned int, long unsigned int> >,
        tbb::detail::d1::spin_rw_mutex>::bucket;
    uint64_t approx_size = sizeof(tbb::concurrent_hash_map<uint64_t, uint64_t>) +   /* overhead of hashtable */
        dc->bucket_count() *  sizeof(bucket);                                       /* size of keys */
    return approx_size;
}

}