/*
* @details: modified to evaluate the datastructures instead of databases.
*
* @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#include "basic_db.h"
#include "core/db_factory.h"

namespace {
  const std::string PROP_SILENT = "basic.silent";
  const std::string PROP_SILENT_DEFAULT = "false";
}

namespace ycsbc {

std::mutex BasicDB:: mutex_;

int BasicDB::Init() {
  /* initialize the datastructure */
  std::lock_guard<std::mutex> lock(mutex_);


  return 0;
}

DB::Status BasicDB::Read(const std::string &table, const uint64_t key) {
  std::lock_guard<std::mutex> lock(mutex_);
  return kOK;
}

DB::Status BasicDB::Scan(const std::string &table, const uint64_t key, int len) {
  std::lock_guard<std::mutex> lock(mutex_);
  int result = this->ds_read_range(this->generic_structure, key, len);
  if (result == 0) {
    return kOK;
  }
  return kError;
}

DB::Status BasicDB::Update(const std::string &table, const uint64_t key,
                           const uint64_t value) {
  /* update is equivalent to insert */
  std::lock_guard<std::mutex> lock(mutex_);
  int result = this->ds_update(this->generic_structure, key, value);
  if (result == 0) {
    return kOK;
  }
  return kError;
}

DB::Status BasicDB::Insert(const std::string &table, const uint64_t key, uint64_t value) {
  std::lock_guard<std::mutex> lock(mutex_);
  int result = this->ds_insert(this->generic_structure, key, value);
  if (result == 0) {
    return kOK;
  }
  return kError;
}

DB::Status BasicDB::Delete(const std::string &table, uint64_t key) {
  std::lock_guard<std::mutex> lock(mutex_);
  int result = this->ds_remove(this->generic_structure, key);
  if (result == 0) {
    return kOK;
  }
  exit(1);
  return kError;
}

DB *NewBasicDB() {
  return new BasicDB;
}

const bool registered = DBFactory::RegisterDB("basic", NewBasicDB);

} // ycsbc
