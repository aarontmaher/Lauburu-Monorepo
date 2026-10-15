#ifndef MOVESENSE_NUS_ECG_BRIDGE_HPP
#define MOVESENSE_NUS_ECG_BRIDGE_HPP

#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <functional>
#include <memory>
#include <vector>

// ============================================================================
// MOVESENSE IDIOMATIC API LAYER (Requirement R2 Acceptance Standard)
// ============================================================================

namespace movesense {

    enum StatusCode {
        HTTP_OK = 200,
        HTTP_CREATED = 201,
        HTTP_BAD_REQUEST = 400,
        HTTP_NOT_FOUND = 404,
        HTTP_SERVICE_UNAVAILABLE = 503
    };

    struct Result {
        int status;
        Result(int s = HTTP_OK) : status(s) {}
    };

    class Timer {
    public:
        Timer() : mId(0), mActive(false) {}
        uint32_t getId() const { return mId; }
        bool isActive() const { return mActive; }
        void start(uint32_t ms) { mId = 1; mActive = (ms > 0); }
        void stop() { mActive = false; }
    private:
        uint32_t mId;
        bool mActive;
    };

    class App {
    public:
        virtual ~App() = default;
        virtual void onInit() {}
    };

    class ValueItem {
    public:
        ValueItem() : mInt(0), mUInt(0) { mStr[0] = '\0'; }
        ValueItem(int32_t v) : mInt(v), mUInt(static_cast<uint32_t>(v)) { mStr[0] = '\0'; }
        ValueItem(uint32_t v) : mInt(static_cast<int32_t>(v)), mUInt(v) { mStr[0] = '\0'; }
        ValueItem(const char* s) : mInt(0), mUInt(0) {
            if (s) {
                size_t len = strlen(s);
                if (len >= sizeof(mStr)) len = sizeof(mStr) - 1;
                memcpy(mStr, s, len);
                mStr[len] = '\0';
            } else {
                mStr[0] = '\0';
            }
        }

        int32_t asInt() const { return mInt; }
        uint32_t asUInt() const { return mUInt; }
        std::string asString() const { return std::string(mStr); }
        const char* asCString() const { return mStr; }

    private:
        int32_t mInt;
        uint32_t mUInt;
        char mStr[32];
    };

    class ValueArray {
    public:
        static constexpr size_t MAX_SAMPLES = 64;

        ValueArray() : mCount(0) {}

        void add(int32_t v) {
            if (mCount < MAX_SAMPLES) {
                mSamples[mCount++] = v;
            }
        }

        void setSamples(const int32_t* samples, size_t count) {
            mCount = (count < MAX_SAMPLES) ? count : MAX_SAMPLES;
            for (size_t i = 0; i < mCount; ++i) {
                mSamples[i] = samples[i];
            }
        }

        size_t size() const { return mCount; }

        ValueItem operator[](size_t index) const {
            if (index < mCount) {
                return ValueItem(mSamples[index]);
            }
            return ValueItem(0);
        }

        const int32_t* data() const { return mSamples; }

    private:
        int32_t mSamples[MAX_SAMPLES];
        size_t mCount;
    };

    class Value;

    class ValueRef {
    public:
        ValueRef(Value* parent, size_t index);

        ValueRef& operator=(int32_t v);
        ValueRef& operator=(uint32_t v);
        ValueRef& operator=(const char* str);
        ValueRef& operator=(const std::string& str);
        ValueRef& operator=(std::string_view sv);
        ValueRef& operator=(const ValueArray& arr);
        ValueRef& operator=(const Value& val);

        int32_t asInt() const;
        uint32_t asUInt() const;
        const char* asCString() const;
        std::string asString() const;
        std::string_view asStringView() const;
        const ValueArray& asArray() const;

    private:
        Value* mParent;
        size_t mIndex;
    };

    class Value {
    public:
        enum Type {
            TYPE_NONE = 0,
            TYPE_INT = 1,
            TYPE_UINT = 2,
            TYPE_STRING = 3,
            TYPE_ARRAY = 4,
            TYPE_MAP = 5
        };

        static constexpr size_t MAX_MAP_ENTRIES = 8;
        static constexpr size_t MAX_KEY_LEN = 24;
        static constexpr size_t INLINE_STR_CAPACITY = 192;

        Value();
        Value(int32_t v);
        Value(uint32_t v);
        Value(const char* str);
        Value(const std::string& str);
        Value(std::string_view sv);
        Value(const ValueArray& arr);

        Value(const Value& other);
        Value& operator=(const Value& other);
        Value(Value&& other) noexcept;
        Value& operator=(Value&& other) noexcept;

        Value& operator=(int32_t v);
        Value& operator=(uint32_t v);
        Value& operator=(const char* str);
        Value& operator=(const std::string& str);
        Value& operator=(std::string_view sv);
        Value& operator=(const ValueArray& arr);

        void setInlineString(const char* str, size_t len);
        void setSamples(const int32_t* samples, size_t count);

        int32_t asInt() const;
        uint32_t asUInt() const;
        const char* asCString() const;
        std::string asString() const;
        std::string_view asStringView() const;
        const ValueArray& asArray() const;
        ValueArray& asArray();

        ValueRef operator[](const char* key);
        ValueRef operator[](const char* key) const;

        ValueRef operator[](const std::string& key) {
            return (*this)[key.c_str()];
        }
        ValueRef operator[](const std::string& key) const {
            return (*this)[key.c_str()];
        }

        bool hasKey(const char* key) const;

        struct MapEntry {
            char key[MAX_KEY_LEN];
            Type type;
            int32_t intVal;
            uint32_t uintVal;
            char strVal[INLINE_STR_CAPACITY];
            size_t strLen;
            ValueArray arrayVal;
        };

    private:
        friend class ValueRef;

        Type mType;
        int32_t mInt;
        uint32_t mUInt;
        char mInlineStr[INLINE_STR_CAPACITY];
        size_t mStrLen;
        ValueArray mArray;

        mutable MapEntry mEntries[MAX_MAP_ENTRIES];
        mutable size_t mEntryCount;

        size_t findOrCreateEntry(const char* key) const;
        size_t findEntry(const char* key) const;
    };

    namespace async {
        typedef std::function<void(const Result&, const Value&)> AsyncCallback;
        typedef std::function<void(const Result&)> AsyncPutCallback;

        void subscribe(const char* path, AsyncCallback callback);
        void unsubscribe(const char* path);
        void put(const char* path, const Value& payload, AsyncPutCallback callback = nullptr);
        void post(const char* path, const Value& payload, AsyncPutCallback callback = nullptr);
        void get(const char* path, AsyncCallback callback = nullptr);

        // Verification & mock control hooks for local/unit test runners
        bool isSubscribed(const char* path);
        size_t getSubscriberCount(const char* path);
        size_t getPutCount(const char* path);
        Value getLastPutPayload(const char* path);
        std::string getLastPutData(const char* path);
        std::string_view getLastPutDataView(const char* path);
        size_t getLastPutData(const char* path, char* out_buf, size_t buf_size);
        void simulateNotification(const char* path, const Value& val, const Result& result = Result(HTTP_OK));
        void clear();
    }

} // namespace movesense

// ============================================================================
// APPLICATION CLASS: NusEcgBridge
// ============================================================================

class NusEcgBridge : public movesense::App {
public:
    static constexpr const char* ECG_PATH = "/Meas/ECG/130";
    static constexpr const char* NUS_TX_PATH = "/Comm/Ble/Nus/Tx";
    static constexpr uint32_t DEFAULT_SAMPLE_RATE = 130;
    static constexpr size_t MAX_STACK_BUFFER_SIZE = 160; // Nordic UART NUS_MAX_DATA_LEN = 158
    static constexpr size_t MAX_LINE_BUFFER_SIZE = 32;

    explicit NusEcgBridge(bool batchMode = false);
    virtual ~NusEcgBridge() override;

    void onInit() override;
    void onClientConnected();
    void onClientDisconnected();
    bool isStreaming() const;

    // Direct ECG notification handler
    void onEcgDataReceived(const movesense::Value& val);

    // Exact sample timestamp skew correction formula:
    // Calculates: base_ts + (sample_index * 1000) / sample_rate
    // Using 64-bit intermediate arithmetic to prevent integer truncation and clock drift
    static uint32_t calculateSampleTimestamp(uint32_t base_timestamp,
                                            size_t sample_index,
                                            uint32_t sample_rate = DEFAULT_SAMPLE_RATE);

    // Zero-heap stack buffer CSV formatting:
    // Formats: "Timestamp,ECG_uV\n"
    static int formatSampleCsv(uint32_t timestamp,
                               int32_t ecg_uv,
                               char* out_buf,
                               size_t buf_size);

    // Batch CSV formatter packing multiple samples into stack buffer up to MTU bounds
    static size_t formatBatchCsv(uint32_t base_timestamp,
                                 const int32_t* samples,
                                 size_t sample_count,
                                 char* out_buf,
                                 size_t buf_size,
                                 uint32_t sample_rate = DEFAULT_SAMPLE_RATE);

    // Telemetry inspection
    size_t getPacketsSent() const;
    size_t getSamplesProcessed() const;
    uint32_t getLastTimestamp() const;
    bool isBatchMode() const;
    void resetStats();

private:
    bool mIsStreaming;
    bool mBatchMode;
    movesense::Timer mTimer;
    size_t mPacketsSent;
    size_t mSamplesProcessed;
    uint32_t mLastTimestamp;
};

// ============================================================================
// WHITEBOARD COMPONENT INTEGRATION LAYER (Bare-Metal / FreeRTOS Compatibility)
// ============================================================================

namespace whiteboard {

    typedef uint32_t ResourceId;
    typedef uint32_t LocalResourceId;
    typedef uint32_t TimerId;
    static constexpr TimerId ID_INVALID_TIMER = 0;
    static constexpr int HTTP_CODE_OK = 200;

    enum ExecutionContext {
        WB_EXEC_CTX_APPLICATION = 1
    };

    struct ParameterList {
        // Flat parameter list placeholder
    };

    template <typename T>
    class Array {
    public:
        Array() : mData(nullptr), mSize(0) {}
        Array(const T* data, size_t size) : mData(data), mSize(size) {}
        size_t size() const { return mSize; }
        const T* begin() const { return mData; }
        const T* end() const { return mData ? mData + mSize : nullptr; }
        const T& operator[](size_t idx) const { return mData[idx]; }
    private:
        const T* mData;
        size_t mSize;
    };

    template <typename T>
    inline Array<T> MakeArray(const T* data, size_t size) {
        return Array<T>(data, size);
    }

    class LaunchableModule {
    public:
        LaunchableModule(const char* name = "LaunchableModule", ExecutionContext ctx = WB_EXEC_CTX_APPLICATION);
        virtual ~LaunchableModule() = default;
        virtual bool initModule() { return true; }
        virtual void deinitModule() {}
        virtual bool startModule() { return true; }
        virtual void stopModule() {}

    protected:
        const char* mName;
        ExecutionContext mContext;
        int mModuleState;
    };

} // namespace whiteboard

namespace WB_RES {

    struct ModuleStateValues {
        static constexpr int UNINITIALIZED = 0;
        static constexpr int INITIALIZED = 1;
        static constexpr int STARTED = 2;
        static constexpr int STOPPED = 3;
    };

    struct ECGData {
        uint32_t timestamp;
        whiteboard::Array<int32_t> samples;
    };

    struct NUSData {
        whiteboard::Array<uint8_t> bytes;
    };

    namespace LOCAL {
        struct MEAS_ECG_REQUIREDSAMPLERATE {
            static constexpr whiteboard::LocalResourceId LID = 0x1001;
            static constexpr whiteboard::ExecutionContext EXECUTION_CONTEXT = whiteboard::WB_EXEC_CTX_APPLICATION;
        };

        struct COMM_BLE_NUS {
            static constexpr whiteboard::LocalResourceId LID = 0x2001;
            static constexpr whiteboard::ExecutionContext EXECUTION_CONTEXT = whiteboard::WB_EXEC_CTX_APPLICATION;
        };
    }

} // namespace WB_RES

namespace whiteboard {

    class ResourceClient {
    public:
        ResourceClient(const char* name = "ResourceClient", ExecutionContext ctx = WB_EXEC_CTX_APPLICATION);
        virtual ~ResourceClient() = default;

        bool asyncSubscribe(LocalResourceId lid, int rate = 130);
        bool asyncUnsubscribe(LocalResourceId lid, int rate = 130);
        bool asyncPost(LocalResourceId lid, const WB_RES::NUSData& data);

        bool isSubscribed(LocalResourceId lid) const;
        size_t getPostCount() const;
        const WB_RES::NUSData& getLastPostData() const;

    private:
        const char* mClientName;
        ExecutionContext mClientContext;
        bool mEcgSubscribed;
        bool mNusSubscribed;
        size_t mPostCount;
        WB_RES::NUSData mLastPostData;
    };

} // namespace whiteboard

namespace wb = whiteboard;

class NusEcgBridgeWbModule : public whiteboard::LaunchableModule, public whiteboard::ResourceClient {
public:
    static const char* const LAUNCHABLE_NAME;

    NusEcgBridgeWbModule();
    virtual ~NusEcgBridgeWbModule() override;

    bool initModule() override;
    void deinitModule() override;
    bool startModule() override;
    void stopModule() override;

    void onNotify(whiteboard::ResourceId resourceId,
                  const WB_RES::ECGData& ecgData);

    bool isSubscribed() const;
    size_t getPacketsSent() const;
    size_t getSamplesProcessed() const;
    uint32_t getLastTimestamp() const;
    const char* getLastPacketBuffer() const;
    size_t getLastPacketLength() const;

private:
    bool mIsSubscribed;
    size_t mPacketsSent;
    size_t mSamplesProcessed;
    uint32_t mLastTimestamp;
    char mLastPacketBuffer[160];
    size_t mLastPacketLength;
};

#endif // MOVESENSE_NUS_ECG_BRIDGE_HPP
