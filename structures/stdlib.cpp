/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*   C++ standard library examples
*/

#include "structure_interface.h"
#include <unordered_map>

using STDLibtype = std::unordered_map<uint64_t, uint64_t>;

extern "C" {

void*   ds_init(uint64_t size) {
    return static_cast<void*>(new STDLibtype(size));
}

void    ds_thread_init(void* ds) {}

int     ds_insert(void* ds, uint64_t key, uint64_t value) {
    STDLibtype* dc = static_cast<STDLibtype *>(ds);
    auto result = dc->insert({key, value});
    return result.second;
}

int     ds_update(void* ds, uint64_t key, uint64_t value) {
    STDLibtype* dc = static_cast<STDLibtype *>(ds);
    auto result = dc->insert({key, value});
    return result.second;
}

int     ds_read(void* ds, uint64_t key) {
    STDLibtype* dc = static_cast<STDLibtype *>(ds);
    dc->find(key);
    return true;
}

int     ds_read_range(void* ds, uint64_t key, uint64_t len) {
    bool result = true;
    for (uint64_t i=0; i<len; i++) {
        result &= ds_read(ds, key + i);
    }
    return 0;
}

int     ds_remove(void* ds, uint64_t key) {
    STDLibtype* dc = static_cast<STDLibtype *>(ds);
    dc->erase(key);
    return 1;
}

uint64_t ds_get_size(void* ds) {
    STDLibtype* dc = static_cast<STDLibtype *>(ds);
    
    size_t totalSize = sizeof(dc);
    for (const auto& pair : *dc) {
        totalSize += sizeof(pair);
        totalSize += sizeof(pair.first);
        totalSize += sizeof(pair.second);
    }

    return totalSize;
}

}