#include "NusEcgBridge.hpp"
#include <algorithm>
#include <mutex>

// ============================================================================
// MOVESENSE VALUE & VALUEREF IMPLEMENTATION
// ============================================================================

namespace movesense {

    ValueRef::ValueRef(Value* parent, size_t index)
        : mParent(parent), mIndex(index) {}

    ValueRef& ValueRef::operator=(int32_t v) {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            auto& e = mParent->mEntries[mIndex];
            e.type = Value::TYPE_INT;
            e.intVal = v;
            e.uintVal = static_cast<uint32_t>(v);
            e.strLen = 0;
            e.strVal[0] = '\0';
        }
        return *this;
    }

    ValueRef& ValueRef::operator=(uint32_t v) {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            auto& e = mParent->mEntries[mIndex];
            e.type = Value::TYPE_UINT;
            e.intVal = static_cast<int32_t>(v);
            e.uintVal = v;
            e.strLen = 0;
            e.strVal[0] = '\0';
        }
        return *this;
    }

    ValueRef& ValueRef::operator=(const char* str) {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            auto& e = mParent->mEntries[mIndex];
            e.type = Value::TYPE_STRING;
            size_t len = str ? strlen(str) : 0;
            if (len >= Value::INLINE_STR_CAPACITY) {
                len = Value::INLINE_STR_CAPACITY - 1;
            }
            if (len > 0) {
                memcpy(e.strVal, str, len);
            }
            e.strVal[len] = '\0';
            e.strLen = len;
        }
        return *this;
    }

    ValueRef& ValueRef::operator=(const std::string& str) {
        return (*this = str.c_str());
    }

    ValueRef& ValueRef::operator=(std::string_view sv) {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            auto& e = mParent->mEntries[mIndex];
            e.type = Value::TYPE_STRING;
            size_t len = sv.length();
            if (len >= Value::INLINE_STR_CAPACITY) {
                len = Value::INLINE_STR_CAPACITY - 1;
            }
            if (len > 0) {
                memcpy(e.strVal, sv.data(), len);
            }
            e.strVal[len] = '\0';
            e.strLen = len;
        }
        return *this;
    }

    ValueRef& ValueRef::operator=(const ValueArray& arr) {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            auto& e = mParent->mEntries[mIndex];
            e.type = Value::TYPE_ARRAY;
            e.arrayVal = arr;
        }
        return *this;
    }

    ValueRef& ValueRef::operator=(const Value& val) {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            auto& e = mParent->mEntries[mIndex];
            e.type = val.mType;
            e.intVal = val.mInt;
            e.uintVal = val.mUInt;
            e.strLen = val.mStrLen;
            memcpy(e.strVal, val.mInlineStr, sizeof(e.strVal));
            e.arrayVal = val.mArray;
        }
        return *this;
    }

    int32_t ValueRef::asInt() const {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            const auto& e = mParent->mEntries[mIndex];
            if (e.type == Value::TYPE_INT || e.type == Value::TYPE_UINT) return e.intVal;
            if (e.type == Value::TYPE_STRING && e.strLen > 0) return std::strtol(e.strVal, nullptr, 10);
        }
        return 0;
    }

    uint32_t ValueRef::asUInt() const {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            const auto& e = mParent->mEntries[mIndex];
            if (e.type == Value::TYPE_UINT || e.type == Value::TYPE_INT) return e.uintVal;
            if (e.type == Value::TYPE_STRING && e.strLen > 0) return static_cast<uint32_t>(std::strtoul(e.strVal, nullptr, 10));
        }
        return 0;
    }

    const char* ValueRef::asCString() const {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            return mParent->mEntries[mIndex].strVal;
        }
        return "";
    }

    std::string ValueRef::asString() const {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            const auto& e = mParent->mEntries[mIndex];
            return std::string(e.strVal, e.strLen);
        }
        return std::string();
    }

    std::string_view ValueRef::asStringView() const {
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            const auto& e = mParent->mEntries[mIndex];
            return std::string_view(e.strVal, e.strLen);
        }
        return std::string_view();
    }

    const ValueArray& ValueRef::asArray() const {
        static ValueArray sEmptyArray;
        if (mParent && mIndex < Value::MAX_MAP_ENTRIES) {
            return mParent->mEntries[mIndex].arrayVal;
        }
        return sEmptyArray;
    }

    // ========================================================================
    // VALUE CONSTRUCTORS & ASSIGNMENTS
    // ========================================================================

    Value::Value()
        : mType(TYPE_NONE), mInt(0), mUInt(0), mStrLen(0), mEntryCount(0) {
        mInlineStr[0] = '\0';
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i].key[0] = '\0';
            mEntries[i].type = TYPE_NONE;
            mEntries[i].intVal = 0;
            mEntries[i].uintVal = 0;
            mEntries[i].strVal[0] = '\0';
            mEntries[i].strLen = 0;
        }
    }

    Value::Value(int32_t v)
        : mType(TYPE_INT), mInt(v), mUInt(static_cast<uint32_t>(v)), mStrLen(0), mEntryCount(0) {
        mInlineStr[0] = '\0';
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i].key[0] = '\0';
            mEntries[i].type = TYPE_NONE;
            mEntries[i].intVal = 0;
            mEntries[i].uintVal = 0;
            mEntries[i].strVal[0] = '\0';
            mEntries[i].strLen = 0;
        }
    }

    Value::Value(uint32_t v)
        : mType(TYPE_UINT), mInt(static_cast<int32_t>(v)), mUInt(v), mStrLen(0), mEntryCount(0) {
        mInlineStr[0] = '\0';
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i].key[0] = '\0';
            mEntries[i].type = TYPE_NONE;
            mEntries[i].intVal = 0;
            mEntries[i].uintVal = 0;
            mEntries[i].strVal[0] = '\0';
            mEntries[i].strLen = 0;
        }
    }

    Value::Value(const char* str)
        : mType(TYPE_STRING), mInt(0), mUInt(0), mStrLen(0), mEntryCount(0) {
        mInlineStr[0] = '\0';
        setInlineString(str, str ? strlen(str) : 0);
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i].key[0] = '\0';
            mEntries[i].type = TYPE_NONE;
            mEntries[i].intVal = 0;
            mEntries[i].uintVal = 0;
            mEntries[i].strVal[0] = '\0';
            mEntries[i].strLen = 0;
        }
    }

    Value::Value(const std::string& str)
        : Value(str.c_str()) {}

    Value::Value(std::string_view sv)
        : mType(TYPE_STRING), mInt(0), mUInt(0), mStrLen(0), mEntryCount(0) {
        mInlineStr[0] = '\0';
        setInlineString(sv.data(), sv.length());
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i].key[0] = '\0';
            mEntries[i].type = TYPE_NONE;
            mEntries[i].intVal = 0;
            mEntries[i].uintVal = 0;
            mEntries[i].strVal[0] = '\0';
            mEntries[i].strLen = 0;
        }
    }

    Value::Value(const ValueArray& arr)
        : mType(TYPE_ARRAY), mInt(0), mUInt(0), mStrLen(0), mArray(arr), mEntryCount(0) {
        mInlineStr[0] = '\0';
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i].key[0] = '\0';
            mEntries[i].type = TYPE_NONE;
            mEntries[i].intVal = 0;
            mEntries[i].uintVal = 0;
            mEntries[i].strVal[0] = '\0';
            mEntries[i].strLen = 0;
        }
    }

    Value::Value(const Value& other)
        : mType(other.mType),
          mInt(other.mInt),
          mUInt(other.mUInt),
          mStrLen(other.mStrLen),
          mArray(other.mArray),
          mEntryCount(other.mEntryCount) {
        memcpy(mInlineStr, other.mInlineStr, sizeof(mInlineStr));
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i] = other.mEntries[i];
        }
    }

    Value& Value::operator=(const Value& other) {
        if (this != &other) {
            mType = other.mType;
            mInt = other.mInt;
            mUInt = other.mUInt;
            mStrLen = other.mStrLen;
            mArray = other.mArray;
            mEntryCount = other.mEntryCount;
            memcpy(mInlineStr, other.mInlineStr, sizeof(mInlineStr));
            for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
                mEntries[i] = other.mEntries[i];
            }
        }
        return *this;
    }

    Value::Value(Value&& other) noexcept
        : mType(other.mType),
          mInt(other.mInt),
          mUInt(other.mUInt),
          mStrLen(other.mStrLen),
          mArray(other.mArray),
          mEntryCount(other.mEntryCount) {
        memcpy(mInlineStr, other.mInlineStr, sizeof(mInlineStr));
        for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
            mEntries[i] = other.mEntries[i];
        }
        other.mType = TYPE_NONE;
        other.mEntryCount = 0;
    }

    Value& Value::operator=(Value&& other) noexcept {
        if (this != &other) {
            mType = other.mType;
            mInt = other.mInt;
            mUInt = other.mUInt;
            mStrLen = other.mStrLen;
            mArray = other.mArray;
            mEntryCount = other.mEntryCount;
            memcpy(mInlineStr, other.mInlineStr, sizeof(mInlineStr));
            for (size_t i = 0; i < MAX_MAP_ENTRIES; ++i) {
                mEntries[i] = other.mEntries[i];
            }
            other.mType = TYPE_NONE;
            other.mEntryCount = 0;
        }
        return *this;
    }

    Value& Value::operator=(int32_t v) {
        mType = TYPE_INT;
        mInt = v;
        mUInt = static_cast<uint32_t>(v);
        mStrLen = 0;
        mInlineStr[0] = '\0';
        return *this;
    }

    Value& Value::operator=(uint32_t v) {
        mType = TYPE_UINT;
        mInt = static_cast<int32_t>(v);
        mUInt = v;
        mStrLen = 0;
        mInlineStr[0] = '\0';
        return *this;
    }

    Value& Value::operator=(const char* str) {
        mType = TYPE_STRING;
        setInlineString(str, str ? strlen(str) : 0);
        return *this;
    }

    Value& Value::operator=(const std::string& str) {
        return (*this = str.c_str());
    }

    Value& Value::operator=(std::string_view sv) {
        mType = TYPE_STRING;
        setInlineString(sv.data(), sv.length());
        return *this;
    }

    Value& Value::operator=(const ValueArray& arr) {
        mType = TYPE_ARRAY;
        mArray = arr;
        return *this;
    }

    void Value::setInlineString(const char* str, size_t len) {
        if (!str || len == 0) {
            mInlineStr[0] = '\0';
            mStrLen = 0;
            return;
        }
        if (len >= INLINE_STR_CAPACITY) {
            len = INLINE_STR_CAPACITY - 1;
        }
        memcpy(mInlineStr, str, len);
        mInlineStr[len] = '\0';
        mStrLen = len;
        mType = TYPE_STRING;
    }

    void Value::setSamples(const int32_t* samples, size_t count) {
        mType = TYPE_ARRAY;
        mArray.setSamples(samples, count);
    }

    int32_t Value::asInt() const {
        if (mType == TYPE_INT || mType == TYPE_UINT) return mInt;
        if (mType == TYPE_STRING && mStrLen > 0) return std::strtol(mInlineStr, nullptr, 10);
        return mInt;
    }

    uint32_t Value::asUInt() const {
        if (mType == TYPE_UINT || mType == TYPE_INT) return mUInt;
        if (mType == TYPE_STRING && mStrLen > 0) return static_cast<uint32_t>(std::strtoul(mInlineStr, nullptr, 10));
        return mUInt;
    }

    const char* Value::asCString() const {
        return mInlineStr;
    }

    std::string Value::asString() const {
        return std::string(mInlineStr, mStrLen);
    }

    std::string_view Value::asStringView() const {
        return std::string_view(mInlineStr, mStrLen);
    }

    const ValueArray& Value::asArray() const {
        return mArray;
    }

    ValueArray& Value::asArray() {
        return mArray;
    }

    size_t Value::findEntry(const char* key) const {
        if (!key) return MAX_MAP_ENTRIES;
        for (size_t i = 0; i < mEntryCount; ++i) {
            if (strncmp(mEntries[i].key, key, MAX_KEY_LEN) == 0) {
                return i;
            }
        }
        return MAX_MAP_ENTRIES;
    }

    size_t Value::findOrCreateEntry(const char* key) const {
        if (!key) return MAX_MAP_ENTRIES;
        size_t existing = findEntry(key);
        if (existing < MAX_MAP_ENTRIES) {
            return existing;
        }
        if (mEntryCount < MAX_MAP_ENTRIES) {
            size_t idx = mEntryCount++;
            size_t keyLen = strlen(key);
            if (keyLen >= MAX_KEY_LEN) keyLen = MAX_KEY_LEN - 1;
            memcpy(mEntries[idx].key, key, keyLen);
            mEntries[idx].key[keyLen] = '\0';
            mEntries[idx].type = TYPE_NONE;
            mEntries[idx].intVal = 0;
            mEntries[idx].uintVal = 0;
            mEntries[idx].strVal[0] = '\0';
            mEntries[idx].strLen = 0;
            return idx;
        }
        return MAX_MAP_ENTRIES - 1; // Fallback to last slot if capacity saturated
    }

    bool Value::hasKey(const char* key) const {
        return findEntry(key) < MAX_MAP_ENTRIES;
    }

    ValueRef Value::operator[](const char* key) {
        mType = TYPE_MAP;
        size_t idx = findOrCreateEntry(key);
        return ValueRef(this, idx);
    }

    ValueRef Value::operator[](const char* key) const {
        size_t idx = findOrCreateEntry(key);
        return ValueRef(const_cast<Value*>(this), idx);
    }

    // ========================================================================
    // MOVESENSE::ASYNC SUBSCRIPTION & DISPATCH ROUTER
    // ========================================================================

    namespace async {

        struct AsyncPathEntry {
            char path[64];
            bool inUse;
            size_t putCount;
            Value lastPutPayload;
            char lastPutData[Value::INLINE_STR_CAPACITY];
            size_t lastPutDataLen;

            static constexpr size_t MAX_CALLBACKS = 8;
            AsyncCallback callbacks[MAX_CALLBACKS];
            size_t callbackCount;
        };

        struct AsyncRegistry {
            static constexpr size_t MAX_PATHS = 16;
            std::mutex mtx;
            AsyncPathEntry entries[MAX_PATHS];

            AsyncRegistry() {
                clearInternal();
            }

            void clearInternal() {
                for (size_t i = 0; i < MAX_PATHS; ++i) {
                    entries[i].path[0] = '\0';
                    entries[i].inUse = false;
                    entries[i].putCount = 0;
                    entries[i].lastPutPayload = Value();
                    entries[i].lastPutData[0] = '\0';
                    entries[i].lastPutDataLen = 0;
                    for (size_t c = 0; c < AsyncPathEntry::MAX_CALLBACKS; ++c) {
                        entries[i].callbacks[c] = nullptr;
                    }
                    entries[i].callbackCount = 0;
                }
            }

            size_t findPath(const char* path) const {
                if (!path) return MAX_PATHS;
                for (size_t i = 0; i < MAX_PATHS; ++i) {
                    if (entries[i].inUse && strncmp(entries[i].path, path, sizeof(entries[i].path)) == 0) {
                        return i;
                    }
                }
                return MAX_PATHS;
            }

            size_t findOrCreatePath(const char* path) {
                if (!path) return MAX_PATHS;
                size_t existing = findPath(path);
                if (existing < MAX_PATHS) {
                    return existing;
                }
                for (size_t i = 0; i < MAX_PATHS; ++i) {
                    if (!entries[i].inUse) {
                        entries[i].inUse = true;
                        size_t len = strlen(path);
                        if (len >= sizeof(entries[i].path)) {
                            len = sizeof(entries[i].path) - 1;
                        }
                        memcpy(entries[i].path, path, len);
                        entries[i].path[len] = '\0';
                        entries[i].putCount = 0;
                        entries[i].lastPutPayload = Value();
                        entries[i].lastPutData[0] = '\0';
                        entries[i].lastPutDataLen = 0;
                        entries[i].callbackCount = 0;
                        return i;
                    }
                }
                return MAX_PATHS;
            }
        };

        static AsyncRegistry& getRegistry() {
            static AsyncRegistry sRegistry;
            return sRegistry;
        }

        void subscribe(const char* path, AsyncCallback callback) {
            if (!path || !callback) return;
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findOrCreatePath(path);
            if (idx < AsyncRegistry::MAX_PATHS) {
                auto& entry = reg.entries[idx];
                if (entry.callbackCount < AsyncPathEntry::MAX_CALLBACKS) {
                    entry.callbacks[entry.callbackCount++] = callback;
                }
            }
        }

        void unsubscribe(const char* path) {
            if (!path) return;
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            if (idx < AsyncRegistry::MAX_PATHS) {
                auto& entry = reg.entries[idx];
                for (size_t i = 0; i < entry.callbackCount; ++i) {
                    entry.callbacks[i] = nullptr;
                }
                entry.callbackCount = 0;
            }
        }

        void put(const char* path, const Value& payload, AsyncPutCallback callback) {
            if (!path) return;
            auto& reg = getRegistry();
            {
                std::lock_guard<std::mutex> lock(reg.mtx);
                size_t idx = reg.findOrCreatePath(path);
                if (idx < AsyncRegistry::MAX_PATHS) {
                    auto& entry = reg.entries[idx];
                    entry.putCount++;
                    entry.lastPutPayload = payload;

                    if (payload.hasKey("Data")) {
                        std::string_view sv = payload["Data"].asStringView();
                        size_t copy_len = sv.length();
                        if (copy_len >= sizeof(entry.lastPutData)) {
                            copy_len = sizeof(entry.lastPutData) - 1;
                        }
                        if (copy_len > 0) {
                            memcpy(entry.lastPutData, sv.data(), copy_len);
                        }
                        entry.lastPutData[copy_len] = '\0';
                        entry.lastPutDataLen = copy_len;
                    } else if (payload.asCString()[0] != '\0') {
                        const char* cs = payload.asCString();
                        size_t len = strlen(cs);
                        if (len >= sizeof(entry.lastPutData)) {
                            len = sizeof(entry.lastPutData) - 1;
                        }
                        if (len > 0) {
                            memcpy(entry.lastPutData, cs, len);
                        }
                        entry.lastPutData[len] = '\0';
                        entry.lastPutDataLen = len;
                    } else {
                        entry.lastPutData[0] = '\0';
                        entry.lastPutDataLen = 0;
                    }
                }
            }
            if (callback) {
                callback(Result(HTTP_OK));
            }
        }

        void post(const char* path, const Value& payload, AsyncPutCallback callback) {
            put(path, payload, callback);
        }

        void get(const char* path, AsyncCallback callback) {
            if (callback) {
                Value val;
                callback(Result(HTTP_OK), val);
            }
            (void)path;
        }

        bool isSubscribed(const char* path) {
            if (!path) return false;
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            return (idx < AsyncRegistry::MAX_PATHS && reg.entries[idx].callbackCount > 0);
        }

        size_t getSubscriberCount(const char* path) {
            if (!path) return 0;
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            return (idx < AsyncRegistry::MAX_PATHS) ? reg.entries[idx].callbackCount : 0;
        }

        size_t getPutCount(const char* path) {
            if (!path) return 0;
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            return (idx < AsyncRegistry::MAX_PATHS) ? reg.entries[idx].putCount : 0;
        }

        Value getLastPutPayload(const char* path) {
            if (!path) return Value();
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            return (idx < AsyncRegistry::MAX_PATHS) ? reg.entries[idx].lastPutPayload : Value();
        }

        std::string getLastPutData(const char* path) {
            if (!path) return "";
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            if (idx < AsyncRegistry::MAX_PATHS) {
                return std::string(reg.entries[idx].lastPutData, reg.entries[idx].lastPutDataLen);
            }
            return "";
        }

        std::string_view getLastPutDataView(const char* path) {
            if (!path) return std::string_view();
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            if (idx < AsyncRegistry::MAX_PATHS) {
                return std::string_view(reg.entries[idx].lastPutData, reg.entries[idx].lastPutDataLen);
            }
            return std::string_view();
        }

        size_t getLastPutData(const char* path, char* out_buf, size_t buf_size) {
            if (!path || !out_buf || buf_size == 0) return 0;
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            size_t idx = reg.findPath(path);
            if (idx < AsyncRegistry::MAX_PATHS) {
                size_t copy_len = reg.entries[idx].lastPutDataLen;
                if (copy_len >= buf_size) {
                    copy_len = buf_size - 1;
                }
                if (copy_len > 0) {
                    memcpy(out_buf, reg.entries[idx].lastPutData, copy_len);
                }
                out_buf[copy_len] = '\0';
                return copy_len;
            }
            out_buf[0] = '\0';
            return 0;
        }

        void simulateNotification(const char* path, const Value& val, const Result& result) {
            if (!path) return;
            AsyncCallback cbs[AsyncPathEntry::MAX_CALLBACKS];
            size_t count = 0;
            {
                auto& reg = getRegistry();
                std::lock_guard<std::mutex> lock(reg.mtx);
                size_t idx = reg.findPath(path);
                if (idx < AsyncRegistry::MAX_PATHS) {
                    count = reg.entries[idx].callbackCount;
                    for (size_t i = 0; i < count; ++i) {
                        cbs[i] = reg.entries[idx].callbacks[i];
                    }
                }
            }
            for (size_t i = 0; i < count; ++i) {
                if (cbs[i]) {
                    cbs[i](result, val);
                }
            }
        }

        void clear() {
            auto& reg = getRegistry();
            std::lock_guard<std::mutex> lock(reg.mtx);
            reg.clearInternal();
        }

    } // namespace async

} // namespace movesense

// ============================================================================
// NUSECGBRIDGE APPLICATION IMPLEMENTATION
// ============================================================================

NusEcgBridge::NusEcgBridge(bool batchMode)
    : mIsStreaming(false),
      mBatchMode(batchMode),
      mPacketsSent(0),
      mSamplesProcessed(0),
      mLastTimestamp(0) {}

NusEcgBridge::~NusEcgBridge() {
    if (mIsStreaming) {
        onClientDisconnected();
    }
}

void NusEcgBridge::onInit() {
    mIsStreaming = false;
    mPacketsSent = 0;
    mSamplesProcessed = 0;
    mLastTimestamp = 0;
}

void NusEcgBridge::onClientConnected() {
    if (!mIsStreaming) {
        // Subscribe to local ECG sensor at 130 Hz
        movesense::async::subscribe(ECG_PATH, [this](const movesense::Result& result, const movesense::Value& val) {
            if (result.status == movesense::HTTP_OK) {
                this->onEcgDataReceived(val);
            }
        });
        mIsStreaming = true;
    }
}

void NusEcgBridge::onClientDisconnected() {
    if (mIsStreaming) {
        movesense::async::unsubscribe(ECG_PATH);
        mIsStreaming = false;
    }
}

bool NusEcgBridge::isStreaming() const {
    return mIsStreaming;
}

uint32_t NusEcgBridge::calculateSampleTimestamp(uint32_t base_timestamp,
                                               size_t sample_index,
                                               uint32_t sample_rate) {
    if (sample_rate == 0) {
        sample_rate = DEFAULT_SAMPLE_RATE;
    }
    // Exact sample timestamp formula: base_ts + (i * 1000) / sample_rate
    // Using 64-bit unsigned arithmetic prevents integer overflow and completely avoids
    // the 1000/130=7 ms truncation error (preserving 0.6923 ms fractional interval).
    uint64_t offset_ms = (static_cast<uint64_t>(sample_index) * 1000ULL) / static_cast<uint64_t>(sample_rate);
    return base_timestamp + static_cast<uint32_t>(offset_ms);
}

int NusEcgBridge::formatSampleCsv(uint32_t timestamp,
                                 int32_t ecg_uv,
                                 char* out_buf,
                                 size_t buf_size) {
    if (!out_buf || buf_size == 0) {
        return -1;
    }
    // Zero-heap stack buffer formatting: "Timestamp,ECG_uV\n"
    int written = snprintf(out_buf, buf_size, "%u,%d\n", timestamp, ecg_uv);
    if (written < 0 || static_cast<size_t>(written) >= buf_size) {
        return -1; // Truncation or error
    }
    return written;
}

size_t NusEcgBridge::formatBatchCsv(uint32_t base_timestamp,
                                   const int32_t* samples,
                                   size_t sample_count,
                                   char* out_buf,
                                   size_t buf_size,
                                   uint32_t sample_rate) {
    if (!samples || !out_buf || buf_size == 0 || sample_count == 0) {
        return 0;
    }
    size_t total_written = 0;
    char line_buf[MAX_LINE_BUFFER_SIZE];

    for (size_t i = 0; i < sample_count; ++i) {
        uint32_t ts = calculateSampleTimestamp(base_timestamp, i, sample_rate);
        int line_len = formatSampleCsv(ts, samples[i], line_buf, sizeof(line_buf));
        if (line_len <= 0) {
            continue;
        }
        if (total_written + static_cast<size_t>(line_len) >= buf_size) {
            // Buffer full for this batch; stops to respect MTU bounds
            break;
        }
        memcpy(out_buf + total_written, line_buf, static_cast<size_t>(line_len));
        total_written += static_cast<size_t>(line_len);
    }
    out_buf[total_written] = '\0';
    return total_written;
}

void NusEcgBridge::onEcgDataReceived(const movesense::Value& val) {
    uint32_t base_timestamp = val["Timestamp"].asUInt();
    const auto& samples = val["Samples"].asArray();
    size_t count = samples.size();
    if (count == 0) {
        return;
    }

    if (!mBatchMode) {
        // Single sample line transmission per packet
        char line_buf[MAX_LINE_BUFFER_SIZE];

        for (size_t i = 0; i < count; ++i) {
            int32_t ecg_val = samples[i].asInt();
            uint32_t current_ts = calculateSampleTimestamp(base_timestamp, i, DEFAULT_SAMPLE_RATE);

            int line_len = formatSampleCsv(current_ts, ecg_val, line_buf, sizeof(line_buf));
            if (line_len > 0) {
                movesense::Value nus_payload;
                nus_payload["Data"] = line_buf;

                movesense::async::put(NUS_TX_PATH, nus_payload, [](const movesense::Result& result) {
                    (void)result;
                });

                mPacketsSent++;
                mSamplesProcessed++;
                mLastTimestamp = current_ts;
            }
        }
    } else {
        // Batched sample lines transmission up to MAX_STACK_BUFFER_SIZE (NUS_MAX_DATA_LEN = 158)
        char batch_buf[MAX_STACK_BUFFER_SIZE];
        size_t offset = 0;
        char line_buf[MAX_LINE_BUFFER_SIZE];

        for (size_t i = 0; i < count; ++i) {
            int32_t ecg_val = samples[i].asInt();
            uint32_t current_ts = calculateSampleTimestamp(base_timestamp, i, DEFAULT_SAMPLE_RATE);

            int line_len = formatSampleCsv(current_ts, ecg_val, line_buf, sizeof(line_buf));
            if (line_len <= 0) continue;

            if (offset + static_cast<size_t>(line_len) >= sizeof(batch_buf)) {
                // Flush batch to Nordic UART
                if (offset > 0) {
                    batch_buf[offset] = '\0';
                    movesense::Value nus_payload;
                    nus_payload["Data"] = batch_buf;

                    movesense::async::put(NUS_TX_PATH, nus_payload, [](const movesense::Result& result) {
                        (void)result;
                    });
                    mPacketsSent++;
                }
                offset = 0;
            }

            memcpy(batch_buf + offset, line_buf, static_cast<size_t>(line_len));
            offset += static_cast<size_t>(line_len);
            mSamplesProcessed++;
            mLastTimestamp = current_ts;
        }

        if (offset > 0) {
            batch_buf[offset] = '\0';
            movesense::Value nus_payload;
            nus_payload["Data"] = batch_buf;

            movesense::async::put(NUS_TX_PATH, nus_payload, [](const movesense::Result& result) {
                (void)result;
            });
            mPacketsSent++;
        }
    }
}

size_t NusEcgBridge::getPacketsSent() const {
    return mPacketsSent;
}

size_t NusEcgBridge::getSamplesProcessed() const {
    return mSamplesProcessed;
}

uint32_t NusEcgBridge::getLastTimestamp() const {
    return mLastTimestamp;
}

bool NusEcgBridge::isBatchMode() const {
    return mBatchMode;
}

void NusEcgBridge::resetStats() {
    mPacketsSent = 0;
    mSamplesProcessed = 0;
    mLastTimestamp = 0;
}

// ============================================================================
// WHITEBOARD LAYER IMPLEMENTATION
// ============================================================================

namespace whiteboard {

    LaunchableModule::LaunchableModule(const char* name, ExecutionContext ctx)
        : mName(name), mContext(ctx), mModuleState(WB_RES::ModuleStateValues::UNINITIALIZED) {}

    ResourceClient::ResourceClient(const char* name, ExecutionContext ctx)
        : mClientName(name),
          mClientContext(ctx),
          mEcgSubscribed(false),
          mNusSubscribed(false),
          mPostCount(0) {
        (void)mClientName;
        (void)mClientContext;
    }

    bool ResourceClient::asyncSubscribe(LocalResourceId lid, int rate) {
        (void)rate;
        if (lid == WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID) {
            mEcgSubscribed = true;
            return true;
        }
        if (lid == WB_RES::LOCAL::COMM_BLE_NUS::LID) {
            mNusSubscribed = true;
            return true;
        }
        return false;
    }

    bool ResourceClient::asyncUnsubscribe(LocalResourceId lid, int rate) {
        (void)rate;
        if (lid == WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID) {
            mEcgSubscribed = false;
            return true;
        }
        if (lid == WB_RES::LOCAL::COMM_BLE_NUS::LID) {
            mNusSubscribed = false;
            return true;
        }
        return false;
    }

    bool ResourceClient::asyncPost(LocalResourceId lid, const WB_RES::NUSData& data) {
        if (lid == WB_RES::LOCAL::COMM_BLE_NUS::LID) {
            mPostCount++;
            mLastPostData = data;
            return true;
        }
        return false;
    }

    bool ResourceClient::isSubscribed(LocalResourceId lid) const {
        if (lid == WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID) {
            return mEcgSubscribed;
        }
        if (lid == WB_RES::LOCAL::COMM_BLE_NUS::LID) {
            return mNusSubscribed;
        }
        return false;
    }

    size_t ResourceClient::getPostCount() const {
        return mPostCount;
    }

    const WB_RES::NUSData& ResourceClient::getLastPostData() const {
        return mLastPostData;
    }

} // namespace whiteboard

const char* const NusEcgBridgeWbModule::LAUNCHABLE_NAME = "NusEcgBridge";

NusEcgBridgeWbModule::NusEcgBridgeWbModule()
    : LaunchableModule(LAUNCHABLE_NAME, whiteboard::WB_EXEC_CTX_APPLICATION),
      ResourceClient(LAUNCHABLE_NAME, whiteboard::WB_EXEC_CTX_APPLICATION),
      mIsSubscribed(false),
      mPacketsSent(0),
      mSamplesProcessed(0),
      mLastTimestamp(0),
      mLastPacketLength(0) {
    mLastPacketBuffer[0] = '\0';
}

NusEcgBridgeWbModule::~NusEcgBridgeWbModule() {
    if (mIsSubscribed) {
        stopModule();
    }
}

bool NusEcgBridgeWbModule::initModule() {
    mModuleState = WB_RES::ModuleStateValues::INITIALIZED;
    return true;
}

void NusEcgBridgeWbModule::deinitModule() {
    mModuleState = WB_RES::ModuleStateValues::UNINITIALIZED;
}

bool NusEcgBridgeWbModule::startModule() {
    mModuleState = WB_RES::ModuleStateValues::STARTED;
    asyncSubscribe(WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID, 130);
    mIsSubscribed = true;
    return true;
}

void NusEcgBridgeWbModule::stopModule() {
    if (mIsSubscribed) {
        asyncUnsubscribe(WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID, 130);
        mIsSubscribed = false;
    }
    mModuleState = WB_RES::ModuleStateValues::STOPPED;
}

void NusEcgBridgeWbModule::onNotify(whiteboard::ResourceId resourceId,
                                   const WB_RES::ECGData& ecgData) {
    if (resourceId == WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID) {
        uint32_t base_ts = ecgData.timestamp;
        size_t count = ecgData.samples.size();
        if (count == 0) return;

        char packet_buffer[160];
        size_t offset = 0;
        char line_buffer[32];

        for (size_t i = 0; i < count; ++i) {
            uint32_t sample_ts = NusEcgBridge::calculateSampleTimestamp(base_ts, i, 130);
            int32_t sample_val = ecgData.samples[i];

            int line_len = NusEcgBridge::formatSampleCsv(sample_ts, sample_val, line_buffer, sizeof(line_buffer));
            if (line_len <= 0) continue;

            if (offset + static_cast<size_t>(line_len) >= sizeof(packet_buffer)) {
                // Flush batch to Nordic UART
                WB_RES::NUSData nusData;
                nusData.bytes = whiteboard::MakeArray<uint8_t>(reinterpret_cast<const uint8_t*>(packet_buffer), offset);
                asyncPost(WB_RES::LOCAL::COMM_BLE_NUS::LID, nusData);
                mPacketsSent++;
                mLastPacketLength = offset;
                memcpy(mLastPacketBuffer, packet_buffer, offset);
                mLastPacketBuffer[offset] = '\0';
                offset = 0;
            }

            memcpy(packet_buffer + offset, line_buffer, static_cast<size_t>(line_len));
            offset += static_cast<size_t>(line_len);
            mSamplesProcessed++;
            mLastTimestamp = sample_ts;
        }

        if (offset > 0) {
            WB_RES::NUSData nusData;
            nusData.bytes = whiteboard::MakeArray<uint8_t>(reinterpret_cast<const uint8_t*>(packet_buffer), offset);
            asyncPost(WB_RES::LOCAL::COMM_BLE_NUS::LID, nusData);
            mPacketsSent++;
            mLastPacketLength = offset;
            memcpy(mLastPacketBuffer, packet_buffer, offset);
            mLastPacketBuffer[offset] = '\0';
        }
    }
}

bool NusEcgBridgeWbModule::isSubscribed() const {
    return mIsSubscribed;
}

size_t NusEcgBridgeWbModule::getPacketsSent() const {
    return mPacketsSent;
}

size_t NusEcgBridgeWbModule::getSamplesProcessed() const {
    return mSamplesProcessed;
}

uint32_t NusEcgBridgeWbModule::getLastTimestamp() const {
    return mLastTimestamp;
}

const char* NusEcgBridgeWbModule::getLastPacketBuffer() const {
    return mLastPacketBuffer;
}

size_t NusEcgBridgeWbModule::getLastPacketLength() const {
    return mLastPacketLength;
}
