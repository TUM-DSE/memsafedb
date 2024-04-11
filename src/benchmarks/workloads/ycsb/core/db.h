/*
* @details: modified to evaluate the datastructures instead of databases.
*
* @author: Cristian Sandu <cristian.sandu@tum.de>
*/

#ifndef YCSB_C_DB_H_
#define YCSB_C_DB_H_

#include "utils/properties.h"

#include <vector>
#include <string>

#include <dlfcn.h>
#include <iostream>

namespace ycsbc {

///
/// Database interface layer.
/// per-thread DB instance.
///
class DB {
 public:
  struct Field {
    std::string name;
    std::string value;
  };
  enum Status {
    kOK = 0,
    kError,
    kNotFound,
    kNotImplemented
  };
  ///
  /// Initializes any state for accessing this DB.
  ///
  virtual int Init() { return 0; }
  ///
  /// Clears any state for accessing this DB.
  ///
  virtual void Cleanup() { }
  ///
  /// Reads a record from the database.
  /// Field/value pairs from the result are stored in a vector.
  ///
  /// @param table The name of the table.
  /// @param key The key of the record to read.
  /// @param fields The list of fields to read, or NULL for all of them.
  /// @param result A vector of field/value pairs for the result.
  /// @return Zero on success, or a non-zero error code on error/record-miss.
  ///
  virtual Status Read(const std::string &table, const uint64_t key) = 0;
  ///
  /// Performs a range scan for a set of records in the database.
  /// Field/value pairs from the result are stored in a vector.
  ///
  /// @param table The name of the table.
  /// @param key The key of the first record to read.
  /// @param record_count The number of records to read.
  /// @param fields The list of fields to read, or NULL for all of them.
  /// @param result A vector of vector, where each vector contains field/value
  ///        pairs for one record
  /// @return Zero on success, or a non-zero error code on error.
  ///
  virtual Status Scan(const std::string &table, const uint64_t key, int len) = 0;

  ///
  /// Updates a record in the database.
  /// Field/value pairs in the specified vector are written to the record,
  /// overwriting any existing values with the same field names.
  ///
  /// @param table The name of the table.
  /// @param key The key of the record to write.
  /// @param values A vector of field/value pairs to update in the record.
  /// @return Zero on success, a non-zero error code on error.
  ///
  virtual Status Update(const std::string &table, const uint64_t key,
                     const uint64_t value) = 0;
  ///
  /// Inserts a record into the database.
  /// Field/value pairs in the specified vector are written into the record.
  ///
  /// @param table The name of the table.
  /// @param key The key of the record to insert.
  /// @param values A vector of field/value pairs to insert in the record.
  /// @return Zero on success, a non-zero error code on error.
  ///
  virtual Status Insert(const std::string &table, const uint64_t key,
                     const uint64_t values) = 0;
  ///
  /// Deletes a record from the database.
  ///
  /// @param table The name of the table.
  /// @param key The key of the record to delete.
  /// @return Zero on success, a non-zero error code on error.
  ///
  virtual Status Delete(const std::string &table, const uint64_t key) = 0;

  virtual ~DB() { }

  void SetProps(utils::Properties *props) {
    props_ = props;
  }

  /* added to evaluated datastructures */
  
  /* the datastructure pointer */
  void*       libhandle = nullptr;
  void*       generic_structure = nullptr;
  std::string libpath;

  void*       (*ds_init)();
  int         (*ds_insert)(void*, uint64_t, uint64_t);
  int         (*ds_update)(void*, uint64_t, uint64_t);
  int         (*ds_remove)(void*, uint64_t);
  int         (*ds_read)(void*, uint64_t);
  int         (*ds_read_range)(void*, uint64_t, uint64_t);

  /* initialize the datastructure */
  const std::string LIB_PATH    = "libpath";
  
  int load_functions() {
    /* load the proper functions from the library */
    this->libpath   = this->props_->GetProperty(LIB_PATH, "none");
    this->libhandle = dlopen(this->libpath.c_str(), RTLD_LAZY);
    if (this->libhandle == nullptr) {
      std::cerr << "unable to load the library " << this->libpath  << "reason: " << dlerror() << std::endl;
      return 1;
    }

    /* load the functions */
    this->ds_init   = (void* (*)())dlsym(this->libhandle,  "ds_init");
    if (this->ds_init == nullptr) {
      std::cerr << "unable to load the function ds_init from the library " << this->libpath << std::endl;
      return 1;
    }

    this->ds_insert = (int (*)(void*, uint64_t, uint64_t))dlsym(this->libhandle, "ds_insert");
    if (this->ds_insert == nullptr) {
      std::cerr << "unable to load the function ds_insert from the library " << this->libpath << std::endl;
      return 1;
    }

    this->ds_update = (int (*)(void*, uint64_t, uint64_t))dlsym(this->libhandle, "ds_update");
    if (this->ds_update == nullptr) {
      std::cerr << "unable to load the function ds_update from the library " << this->libpath << std::endl;
      return 1;
    }

    this->ds_remove = (int (*)(void*, uint64_t))dlsym(this->libhandle, "ds_remove");
    if (this->ds_remove == nullptr) {
      std::cerr << "unable to load the function ds_remove from the library " << this->libpath << std::endl;
      return 1;
    }
    this->ds_read = (int (*)(void*, uint64_t))dlsym(this->libhandle, "ds_read");
    if (this->ds_remove == nullptr) {
      std::cerr << "unable to load the function ds_read from the library " << this->libpath << std::endl;
      return 1;
    }

    this->ds_read_range = (int (*)(void*, uint64_t, uint64_t))dlsym(this->libhandle, "ds_read_range");
    if (this->ds_remove == nullptr) {
      std::cerr << "unable to load the function ds_read_range from the library " << this->libpath << std::endl;
      return 1;
    }

    /* initialize the datastructure */
    this->generic_structure = this->ds_init();
    return 0;
  }
  
 protected:
  utils::Properties *props_;
};

} // ycsbc

#endif // YCSB_C_DB_H_
