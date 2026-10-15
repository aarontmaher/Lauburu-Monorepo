#include "utils/json_writer.hpp"
#include <sstream>
#include <iomanip>
#include <cctype>

namespace lauburu {

JsonWriter::JsonWriter() : m_firstEntry(true) {
    m_buffer.reserve(256);
}

void JsonWriter::startObject() {
    m_buffer += "{";
    m_firstEntry = true;
}

void JsonWriter::endObject() {
    m_buffer += "}";
}

std::string JsonWriter::escape(const std::string& str) {
    std::string out;
    out.reserve(str.size() + 16);
    for (char c : str) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char buf[8];
                    snprintf(buf, sizeof(buf), "\\u%04x", static_cast<unsigned char>(c));
                    out += buf;
                } else {
                    out += c;
                }
                break;
        }
    }
    return out;
}

void JsonWriter::addKey(const std::string& key) {
    if (!m_firstEntry) {
        m_buffer += ", ";
    }
    m_firstEntry = false;
    m_buffer += "\"" + escape(key) + "\": ";
}

void JsonWriter::addString(const std::string& key, const std::string& value) {
    addKey(key);
    m_buffer += "\"" + escape(value) + "\"";
}

void JsonWriter::addInt64(const std::string& key, int64_t value) {
    addKey(key);
    m_buffer += std::to_string(value);
}

void JsonWriter::addUInt64(const std::string& key, uint64_t value) {
    addKey(key);
    m_buffer += std::to_string(value);
}

void JsonWriter::addDouble(const std::string& key, double value) {
    addKey(key);
    char buf[32];
    snprintf(buf, sizeof(buf), "%.4f", value);
    m_buffer += buf;
}

void JsonWriter::addBool(const std::string& key, bool value) {
    addKey(key);
    m_buffer += value ? "true" : "false";
}

void JsonWriter::addRaw(const std::string& key, const std::string& rawJson) {
    addKey(key);
    m_buffer += rawJson;
}

std::string JsonWriter::dump() const {
    return m_buffer;
}

// Simple JSON parser
std::string SimpleJsonParser::getString(const std::string& json, const std::string& key, const std::string& def) {
    std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) return def;

    pos += needle.size();
    while (pos < json.size() && (std::isspace(json[pos]) || json[pos] == ':')) {
        pos++;
    }
    if (pos >= json.size() || json[pos] != '"') return def;
    pos++; // skip open quote

    std::string val;
    bool escaped = false;
    while (pos < json.size()) {
        char c = json[pos++];
        if (escaped) {
            val += c;
            escaped = false;
        } else if (c == '\\') {
            escaped = true;
        } else if (c == '"') {
            break;
        } else {
            val += c;
        }
    }
    return val;
}

int SimpleJsonParser::getInt(const std::string& json, const std::string& key, int def) {
    int64_t val = getInt64(json, key, def);
    return static_cast<int>(val);
}

int64_t SimpleJsonParser::getInt64(const std::string& json, const std::string& key, int64_t def) {
    std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) return def;

    pos += needle.size();
    while (pos < json.size() && (std::isspace(json[pos]) || json[pos] == ':')) {
        pos++;
    }
    if (pos >= json.size()) return def;

    size_t start = pos;
    if (json[pos] == '-' || json[pos] == '+') pos++;
    while (pos < json.size() && std::isdigit(json[pos])) {
        pos++;
    }
    if (pos == start) return def;

    std::string numStr = json.substr(start, pos - start);
    return std::stoll(numStr);
}

bool SimpleJsonParser::getBool(const std::string& json, const std::string& key, bool def) {
    std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) return def;

    pos += needle.size();
    while (pos < json.size() && (std::isspace(json[pos]) || json[pos] == ':')) {
        pos++;
    }
    if (json.compare(pos, 4, "true") == 0) return true;
    if (json.compare(pos, 5, "false") == 0) return false;
    return def;
}

} // namespace lauburu
