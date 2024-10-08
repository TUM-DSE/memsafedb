/*
*   @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "structure_interface.h"
#include "clht.h"

#define MEM_SIZE            8
#define MAXIMUM_BUCKET_NUM  131072 /* power of 2 */

void*   ds_init(uint64_t size) {
#ifdef CLHT_LB
    uint64_t buckets = size / ENTRIES_PER_BUCKET;
#elif CLHT_LF
    assert((size & (size - 1)) == 0);
    uint64_t buckets = size;
    /* check if power of 2 */
#endif

    if (buckets >= MAXIMUM_BUCKET_NUM) {
        buckets = MAXIMUM_BUCKET_NUM;
    }

    void* hashtable = clht_create(buckets);
    assert(hashtable != NULL);

    return hashtable;
}

void ds_thread_init(void *ds) {
    /* some ds require thread initialization */
    clht_gc_thread_init(ds, pthread_self());
}

int ds_insert(void* ds, uint64_t key, uint64_t value) {
    if (clht_put(ds, key, (clht_val_t) value)) {
        return SUCCESS;
    }
    return FAIL;
}

int ds_update(void* ds, uint64_t key, uint64_t value) {
    /* clht does not provide a mechanism for updating */
    if (clht_put(ds, key, value)) {
        return SUCCESS;
    }
    return FAIL;
}

int ds_read(void* ds, uint64_t key) {
    clht_t* dsh = (clht_t *)(ds);
    if (clht_get(dsh->ht, key) == 0) {
        return FAIL;
    }
    return SUCCESS;
}

int ds_read_range(void* ds, uint64_t key, uint64_t len) {
    int status = 0;
    for(int i=key; i<key+len; i++) {
        status |= clht_get(ds, i);
    }
    return status;
}

int ds_remove(void* ds, uint64_t key) {
    return clht_remove(ds, key);
}

#ifdef CLHT_LB
    uint64_t __real_num_buckets(clht_t* h) {
        /* inspired by clht_lb.c:clht_put */
        clht_hashtable_t* hashtable = h->ht;
        uint64_t bucket_num = 0;
        for (int i=0; i<h->ht->num_buckets; i++) {
            bucket_num += 1;

            bucket_t *current_bucket = hashtable->table + i;
            while(current_bucket->next != NULL) {
                bucket_num += 1;
                current_bucket = current_bucket->next;
            }
        }
        return bucket_num;
    }
#endif

uint64_t ds_get_size(void* ds) {
#ifdef CLHT_LB
    clht_t* dsh = (clht_t *)(ds);
    return __real_num_buckets(dsh) * sizeof(bucket_t);
#else
    return 0;
#endif
}
