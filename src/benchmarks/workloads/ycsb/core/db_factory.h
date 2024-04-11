/*
* @details: modified to evaluate the datastructures instead of databases.
*
* @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#ifndef YCSB_C_DB_FACTORY_H_
#define YCSB_C_DB_FACTORY_H_

#include "db.h"
#include "measurements.h"
#include "utils/properties.h"

#include <string>
#include <map>

namespace ycsbc {

class DBFactory {
 public:
  using DBCreator = DB *(*)();
  static bool RegisterDB(std::string db_name, DBCreator db_creator);
  static DB *CreateDB(utils::Properties *props, Measurements *measurements);
 private:
  static std::map<std::string, DBCreator> &Registry();
  
};

} // ycsbc

#endif // YCSB_C_DB_FACTORY_H_

