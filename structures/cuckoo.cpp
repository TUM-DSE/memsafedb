/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "structure_interface.h"
#include <libcuckoo/cuckoohash_map.hh>
#include <libcuckoo/cuckoohash_config.hh>
#include <libcuckoo/bucket_container.hh>

/* documentation: https://efficient.github.io/libcuckoo/ */

struct int_str_table;
struct int_str_table*  int_str_table_init(uint64_t);
int  (int_str_table_insert)(struct clht_t*, int, int);  /* returns true (0) and false (1) */
int  (int_str_table_find)(struct clht_t*, int);
int  (clht_remove)(struct clht_t*, int);

extern "C" {

void*   ds_init(uint64_t size) {
    /*
    * the hash table is partitioned into an array of buckets, each of which contains SLOT_PER_BUCKET
    * slots to store items
    */
    uint64_t buckets = size / libcuckoo::DEFAULT_SLOT_PER_BUCKET;
    return static_cast<void*>(new libcuckoo::cuckoohash_map<uint64_t, uint64_t>(buckets));
}

void    ds_thread_init(void* ds) {}

int     ds_insert(void* ds, uint64_t key, uint64_t value) {
    libcuckoo::cuckoohash_map<uint64_t, uint64_t>* dc =
        static_cast<libcuckoo::cuckoohash_map<uint64_t, uint64_t> *>(ds);
    return dc->insert(key, value);
}

int     ds_update(void* ds, uint64_t key, uint64_t value) {
    libcuckoo::cuckoohash_map<uint64_t, uint64_t>* dc =
        static_cast<libcuckoo::cuckoohash_map<uint64_t, uint64_t> *>(ds);
    return dc->update(key, value);
}

int     ds_read(void* ds, uint64_t key) {
    libcuckoo::cuckoohash_map<uint64_t, uint64_t>* dc =
        static_cast<libcuckoo::cuckoohash_map<uint64_t, uint64_t> *>(ds);
    return dc->find(key);
}

int     ds_read_range(void* ds, uint64_t key, uint64_t len) {
    for (uint64_t i=0; i<len; i++) {
        ds_read(ds, key + i);
    }
    return 0;
}

int     ds_remove(void* ds, uint64_t key) {
    libcuckoo::cuckoohash_map<uint64_t, uint64_t>* dc =
        static_cast<libcuckoo::cuckoohash_map<uint64_t, uint64_t> *>(ds);
    return dc->erase(key);
}

uint64_t ds_get_size(void* ds) {
    libcuckoo::cuckoohash_map<uint64_t, uint64_t>* dc =
        static_cast<libcuckoo::cuckoohash_map<uint64_t, uint64_t> *>(ds);
    
    uint64_t size_container = 
        sizeof(libcuckoo::bucket_container<uint64_t, uint64_t, std::allocator<std::pair<const uint64_t, uint64_t>>, uint8_t, libcuckoo::DEFAULT_SLOT_PER_BUCKET>::bucket);
    return dc->capacity() * size_container;
}

}