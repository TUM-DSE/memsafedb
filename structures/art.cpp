/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "structure_interface.h"
#include <art.hpp>
#include <string.h>

using ARTtype = art::art<uint64_t>;

void*   ds_init(uint64_t size) {
    return static_cast<void *>(new ARTtype());
}

void ds_thread_init(void *ds) {
    /* no initialization needed */
}

int ds_insert(void* ds, uint64_t key, uint64_t value) {
    ARTtype* ds_ = static_cast<ARTtype*>(ds);

    /* convert to string */
    std::string strKey = std::to_string(key);
    ds_->set(strKey.c_str(), value);
    return SUCCESS;
}

int ds_update(void* ds, uint64_t key, uint64_t value) {
    return ds_insert(ds, key, value);
}

int ds_read(void* ds, uint64_t key) {
    ARTtype* ds_ = static_cast<ARTtype*>(ds);

    /* convert to string */
    std::string strKey = std::to_string(key);
    uint64_t value = ds_->get(strKey.c_str());
    return SUCCESS;
}

int ds_read_range(void* ds, uint64_t key, uint64_t len) {
    for(int i=key; i<key+len; i++) {
        ds_read(ds, i);
    }
    return SUCCESS;
}

int ds_remove(void* ds, uint64_t key) {
    ARTtype* ds_ = static_cast<ARTtype*>(ds);

    /* convert to string */
    std::string strKey = std::to_string(key);
    ds_->del(strKey.c_str());
    return SUCCESS;
}

uint64_t ds_get_size(void* ds) {
    ARTtype* ds_ = static_cast<ARTtype*>(ds);
    return 0;
}
