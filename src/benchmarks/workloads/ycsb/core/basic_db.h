/*
* @details: modified to evaluate the datastructures instead of databases.
*
* @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#ifndef YCSB_C_BASIC_DB_H_
#define YCSB_C_BASIC_DB_H_

#include "db.h"
#include "utils/properties.h"

#include <iostream>
#include <string>
#include <mutex>

namespace ycsbc {

class BasicDB : public DB {
 public:
  BasicDB() : out_(nullptr) {}

  int Init();

  Status Read  (const std::string &table, const uint64_t key);

  Status Scan  (const std::string &table, const uint64_t key, int len);

  Status Update(const std::string &table, const uint64_t key, const uint64_t value);

  Status Insert(const std::string &table, const uint64_t key, const uint64_t value);

  Status Delete(const std::string &table, const uint64_t key);

 private:
  static std::mutex mutex_;

  std::ostream *out_;
};

DB *NewBasicDB();

} // ycsbc

#endif // YCSB_C_BASIC_DB_H_

