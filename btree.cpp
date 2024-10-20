/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "structure_interface.h"
#include "google-btree/btree_map.h"


extern "C" {

void*   ds_init(uint64_t size) {
    /*
    * the size can be discarded
    */
    return static_cast<void*>(new btree::btree_map<uint64_t, uint64_t>());
}

void    ds_thread_init(void* ds) {}

int     ds_insert(void* ds, uint64_t key, uint64_t value) {
    btree::btree_map<uint64_t, uint64_t>* dc =
        static_cast<btree::btree_map<uint64_t, uint64_t> *>(ds);
    dc->insert({key, value});
    return 1;
}

int     ds_update(void* ds, uint64_t key, uint64_t value) {
    return ds_insert(ds, key, value);
}

int     ds_read(void* ds, uint64_t key) {
    btree::btree_map<uint64_t, uint64_t>* dc =
       	static_cast<btree::btree_map<uint64_t, uint64_t> *>(ds);
    return dc->find(key)->second ? 1 : 0;
}

int     ds_read_range(void* ds, uint64_t key, uint64_t len) {
    for (uint64_t i=0; i<len; i++) {
        ds_read(ds, key + i);
    }
    return 0;
}

int     ds_remove(void* ds, uint64_t key) {
    btree::btree_map<uint64_t, uint64_t>* dc =
        static_cast<btree::btree_map<uint64_t, uint64_t> *>(ds);
    return dc->erase(key);
}

uint64_t ds_get_size(void* ds) {
    return 0;
}

}
