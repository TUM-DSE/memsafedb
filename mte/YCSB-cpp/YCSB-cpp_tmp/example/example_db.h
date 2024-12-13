//
// Created by root on 12/13/24.
//

#ifndef MTE_EXAMPLE_DB_H
#define MTE_EXAMPLE_DB_H


#include "core/db.h"

namespace ycsbc {

    class ExampleDB : public DB {

    private:
        std::unordered_map<std::string, std::string> map;

    public:
        ExampleDB() = default;
        ~ExampleDB() = default;

        Status Read(const std::string &table, const std::string &key,
                    const std::vector<std::string> *fields, std::vector<Field> &result) override;

        Status Scan(const std::string &table, const std::string &key, int len,
                    const std::vector<std::string> *fields, std::vector<std::vector<Field>> &result) override;

        Status Update(const std::string &table, const std::string &key, std::vector<Field> &values) override;

        Status Insert(const std::string &table, const std::string &key, std::vector<Field> &values) override;

        Status Delete(const std::string &table, const std::string &key) override;
    };

    DB *NewExmapleDB();

}


#endif //MTE_EXAMPLE_DB_H
