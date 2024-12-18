#include <stdio.h>
#include <stdint.h>
#include <assert.h>
#include <malloc.h>
#include <stdlib.h>
#include <string.h>

#include "chashtable.h"

#define panic(msg) do { \
    fprintf(stderr, "PANIC: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
    abort(); \
} while (0)



struct key_value_pair {
    struct key_value_pair *next;
    uint8_t *key;
    uint8_t *val;
};

struct chashtable {
    uint32_t size;
    uint32_t capacity;
    struct key_value_pair **items;
};

chashtable_t *chashtable_init(uint64_t capacity);

// some hash function: https://stackoverflow.com/questions/7666509/hash-function-for-string
//uint32_t jenkins_one_at_a_time_hash(uint8_t *key) {
static uint32_t hash(uint8_t *key) {
    uint32_t h = 0;

    while (*key) {
        h += *key;
        h += (h << 10);
        h ^= (h >> 6);
        ++key;
    }

    h += (h << 3);
    h ^= (h >> 11);
    h += (h << 15);

    return h;
}

/// returns the index of the key inside this hashtable
static uint32_t idx_of(chashtable_t *ht, uint8_t *key) {
    assert(ht != NULL);
    assert(key != NULL);
    assert(ht->capacity % 2 == 0);

    uint32_t h = hash(key);
    // capacity of ht is always mod 2 == 0 -> h & ht->capacity == h & (ht->capacity - 1)
    uint32_t idx = h & (ht->capacity - 1);

    assert(idx < ht->capacity);
    return idx;
}

/// init a new key-value-pair and zeros it
static struct key_value_pair *chashtable_kvp_init() {
    struct key_value_pair *kvp = malloc(sizeof(*kvp));
    if (!kvp) {
        panic("OOM");
    }

    kvp->key = NULL;
    kvp->val = NULL;
    kvp->next = NULL;

    return kvp;
}

static uint32_t chashtable_kvp_remove(struct key_value_pair *kvp, uint8_t *key) {
    if (kvp == NULL) {
        return 0;
    }
    while (kvp->next != NULL
           && strcmp((const char *) kvp->key, (const char *) key) != 0) {
        kvp = kvp->next;
    }

    if (kvp->next != NULL) {
        printf("we are gonna remove\n");
        struct key_value_pair *next = kvp->next;

        uint8_t *key_remove = kvp->key;
        uint8_t *val_remove = kvp->val;

        kvp->val = next->val;
        kvp->key = next->key;
        kvp->next = next->next;

        if(key_remove) {
            free(key_remove);
        }

        if(val_remove) {
            free(val_remove);
        }

        return 1;
    }


    return 0;
}

static uint8_t *chashtable_kvp_find(struct key_value_pair *kvp, uint8_t *key) {
    if (kvp == NULL) {
        return NULL;
    }

    while (kvp->next != NULL
           && strcmp((const char *) kvp->key, (const char *) key) != 0) {
        kvp = kvp->next;
    }

    if (kvp->next == NULL) {
        return NULL;
    }

    return kvp->val;
}

/// insert a key, value into the linked list. if the key is not inside the list, append
/// to the end. else replace value of key with new one
static uint32_t chashtable_kvp_insert(struct key_value_pair *kvp, uint8_t *key, uint8_t *val) {
    while (kvp->next != NULL
           && strcmp((const char *) kvp->key, (const char *) key) != 0) {
        kvp = kvp->next;
    }

    if (kvp->next == NULL) {
        // at the end of the linked list
        kvp->next = chashtable_kvp_init();
        kvp->key = key;
        kvp->val = val;

        return 1;
    } else {
        // we found an entry, we override the val
        // is freeing bad? - YCSB dont like to free?
        // printf("insert/update free old key (not anymore) also\n");
        //free(key);
        //free(kvp->val);
        kvp->val = val;
    }

    return 0;
}

static void chashtable_kvp_list_deinit(struct key_value_pair *kvp) {
    assert(kvp != NULL);

    while (kvp->next != NULL) {
        struct key_value_pair *next = kvp->next;

        assert(kvp->key != NULL && kvp->val != NULL);
        // the keys and values are freed by YCSB? - need to double check
        //free(kvp->key);
        //free(kvp->val);
        free(kvp);

        kvp = next;
    }

    if (kvp->key) {
        free(kvp->key);
    }
    if (kvp->val) {
        free(kvp->val);
    }
    free(kvp);
}

static chashtable_t *chashtable_capacity(chashtable_t *ht) {
    uint64_t max_size = ht->capacity / 2 + ht->capacity / 4;
    if (ht->size <= max_size) {
        return ht;
    }

    printf("increase size!\n");
    // we exceeded the fill factor
    uint64_t capacity = ht->capacity * 2;
    chashtable_t *new_ht = chashtable_init(capacity);

    for (uint32_t i = 0; i < ht->capacity; ++i) {
        struct key_value_pair *kvp = ht->items[i];
        if (kvp) {
            // some linked list found, we need to move all elements to the new ht
            while (kvp->next != NULL) {
                chashtable_put(new_ht, kvp->key, kvp->val);

                // after coping the data to the new ht
                struct key_value_pair *next = kvp->next;
                free(kvp);
                kvp = next;
            }
        }
    }

    free(ht->items);
    free(ht);

    return new_ht;
}

void chashtable_deinit(chashtable_t *ht) {
    for (uint32_t i = 0; i < ht->capacity; ++i) {
        if (ht->items[i]) {
            chashtable_kvp_list_deinit(ht->items[i]);
        }
    }

    free(ht->items);
    free(ht);
}

chashtable_t *chashtable_init(uint64_t capacity) {
    assert(capacity % 2 == 0);
    assert(capacity > 0);

    chashtable_t *ht = malloc(sizeof(*ht));
    if (!ht) {
        panic("OOM");
    }

    ht->size = 0;
    ht->capacity = capacity;
    ht->items = calloc(sizeof(*(ht->items)), capacity);
    if (!ht->items) {
        panic("OOM");
    }

    return ht;
}

/// puts the key to value into the hashmap. passing key/value into this function
/// delegates the managment of the resourcen to the hashtable
chashtable_t *chashtable_put(chashtable_t *ht, uint8_t *key, uint8_t *val) {
    assert(ht != NULL);
    assert(key != NULL);
    assert(val != NULL);

    ht = chashtable_capacity(ht);

    uint32_t idx = idx_of(ht, key);
    struct key_value_pair *kvp = *(ht->items + idx);
    if (!kvp) {
        kvp = chashtable_kvp_init();
        ht->items[idx] = kvp;
    }

    if (chashtable_kvp_insert(kvp, key, val)) {
        ht->size++;
    }

    return ht;
}

/// returns the value to the key or NULL if it doesnt exists.
/// the returned value can be after every hashtable operation be invalid and no longer valid
uint8_t *chashtable_get(chashtable_t *ht, uint8_t *key) {
    assert(ht != NULL);
    assert(key != NULL);

    uint32_t idx = idx_of(ht, key);
    return chashtable_kvp_find(ht->items[idx], key);
}

/// removes the key from the ht, if the ht contains the key
void chashtable_remove(chashtable_t *ht, uint8_t *key) {
    assert(ht != NULL);
    assert(key != NULL);

    uint32_t idx = idx_of(ht, key);
    if (chashtable_kvp_remove(ht->items[idx], key))  {
        ht->size--;
    }
}
