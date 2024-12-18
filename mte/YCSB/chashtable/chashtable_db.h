

#ifndef MTE_CHASHTABLE_DB_H
#define MTE_CHASHTABLE_DB_H


#include "core/db.h"
#include "chashtable.h"
#include <cstdint>
#include <mutex>
#include <iostream>

namespace ycsbc {

    class CHashtableDB : public DB {

    private:
      chashtable_t *ht;
      std::mutex mutex_;

    public:
        CHashtableDB() {
          this->ht = chashtable_init(1 << 20);
        }

        ~CHashtableDB() {
          chashtable_deinit(this->ht);
        }

        Status Read(const std::string &table, const std::string &key,
                    const std::vector<std::string> *fields, std::vector<Field> &result) override {
          std::lock_guard<std::mutex> lock(mutex_);
          assert(fields == nullptr); // fields is null, if all fields are requried?


          uint8_t *s = chashtable_get(this->ht, (uint8_t *) key.c_str());
          if (!s) {
            return DB::Status::kNotFound;
          }
          return DB::kOK;
        }

        Status Scan(const std::string &table, const std::string &key, int len,
                    const std::vector<std::string> *fields, std::vector<std::vector<Field>> &result) override {
          return DB::Status::kNotImplemented;
        }

        Status Update(const std::string &table, const std::string &key, std::vector<Field> &values) override {
          return Insert(table, key, values);
        }

        Status Insert(const std::string &table, const std::string &key, std::vector<Field> &values) override {
          // todo: currently the hashmap is not concurrent - change it?
          std::lock_guard<std::mutex> lock(mutex_);
          assert(values.size() == 1);

          this->ht = chashtable_put(this->ht, (uint8_t *)key.c_str(), (uint8_t *)values[0].value.c_str());
          return DB::kOK;

        }

        Status Delete(const std::string &table, const std::string &key) override {
          return DB::Status::kNotImplemented;
        }
    };

    DB *NewCHashtableDB();

}


#endif //MTE_EXAMPLE_DB_H
