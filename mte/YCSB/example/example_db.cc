
#include "example_db.h"
#include "core/db_factory.h"


namespace ycsbc {

    DB::Status ExampleDB::Read(const std::string &table, const std::string &key,
                               const std::vector<std::string> *fields, std::vector<Field> &result) {
        // for the beginning we only do one key values, ignore for the first multiple fields associated with a key
        assert(fields == nullptr);

        auto e = this->map.find(key);
        if (e == this->map.end()) {
            return DB::Status::kNotFound;
        }

        result.push_back({key, e->first});
        return DB::Status::kOK;
    }


    DB::Status ExampleDB::Scan(const std::string &table, const std::string &key, int len,
                               const std::vector<std::string> *fields, std::vector<std::vector<Field>> &result) {
        // for the beginning we only do one key values, ignore for the first multiple fields associated with a key
        assert(fields == nullptr);

        return DB::Status::kOK;
    }


    DB::Status ExampleDB::Update(const std::string &table, const std::string &key, std::vector<Field> &values) {
        return DB::Status::kOK;
    }

    DB::Status ExampleDB::Insert(const std::string &table, const std::string &key, std::vector<Field> &values) {
        return DB::Status::kOK;
    }

    DB::Status ExampleDB::Delete(const std::string &table, const std::string &key) {
        return DB::Status::kOK;
    }

    DB *NewExampleDB() {
        return new ExampleDB;
    }

    const bool registered = DBFactory::RegisterDB("exampledb", NewExampleDB);
}
