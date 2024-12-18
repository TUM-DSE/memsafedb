
#include "chashtable_db.h"
#include "core/db_factory.h"
#include "core/db.h"
#include "chashtable.h"
#include <cstdint>
#include <mutex>

namespace ycsbc {

  DB *NewCHashtableDB() {
    return new CHashtableDB;
  }
  const bool registered = DBFactory::RegisterDB("chashtabledb", NewCHashtableDB);
}
