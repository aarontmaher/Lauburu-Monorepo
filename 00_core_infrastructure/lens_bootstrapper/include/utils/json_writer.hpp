#pragma once

#include <string>
#include <cstdint>
#include <vector>

namespace lauburu {

class JsonWriter {
public:
    JsonWriter();
    void startObject();
    void endObject();
    void addKey(const std::string& key);
    void addString(const std::string& key, const std::string& value);
    void addInt64(const std::string& key, int64_t value);
    void addUInt64(const std::string& key, uint64_t value);
    void addDouble(const std::string& key, double value);
    void addBool(const std::string& key, bool value);
    void addRaw(const std::string& key, const std::string& rawJson);

    std::string dump() const;
    static std::string escape(const std::string& str);

private:
    std::string m_buffer;
    bool m_firstEntry;
};

class SimpleJsonParser {
public:
    static std::string getString(const std::string& json, const std::string& key, const std::string& def = "");
    static int getInt(const std::string& json, const std::string& key, int def = 0);
    static int64_t getInt64(const std::string& json, const std::string& key, int64_t def = 0);
    static bool getBool(const std::string& json, const std::string& key, bool def = false);
};

} // namespace lauburu
