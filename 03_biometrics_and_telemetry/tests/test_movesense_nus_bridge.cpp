#include "NusEcgBridge.hpp"
#include "Movesense_NUS_Bridge_App.cpp"
#include <iostream>
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <vector>
#include <string>
#include <sstream>

// ============================================================================
// HEAP ALLOCATION TRACKING HOOKS (Verifies Zero-Heap Formatting)
// ============================================================================

static bool g_track_allocations = false;
static size_t g_heap_alloc_count = 0;

void* operator new(size_t size) {
    if (g_track_allocations) {
        g_heap_alloc_count++;
    }
    return std::malloc(size);
}

void* operator new[](size_t size) {
    if (g_track_allocations) {
        g_heap_alloc_count++;
    }
    return std::malloc(size);
}

void operator delete(void* p) noexcept {
    std::free(p);
}

void operator delete[](void* p) noexcept {
    std::free(p);
}

void operator delete(void* p, size_t) noexcept {
    std::free(p);
}

void operator delete[](void* p, size_t) noexcept {
    std::free(p);
}

// ============================================================================
// TEST MACROS & HELPERS
// ============================================================================

static int g_tests_passed = 0;
static int g_tests_failed = 0;

#define TEST_ASSERT(cond, msg) \
    do { \
        if (!(cond)) { \
            std::cerr << "[-] ASSERTION FAILED: " << msg << " (" << __FILE__ << ":" << __LINE__ << ")" << std::endl; \
            g_tests_failed++; \
            return false; \
        } \
    } while (0)

#define RUN_TEST(test_func) \
    do { \
        std::cout << "[RUNNING] " << #test_func << " ... " << std::flush; \
        if (test_func()) { \
            std::cout << "\033[32mPASS\033[0m" << std::endl; \
            g_tests_passed++; \
        } else { \
            std::cout << "\033[31mFAIL\033[0m" << std::endl; \
        } \
    } while (0)

// ============================================================================
// TEST SUITE 1: SUBSCRIPTION & LIFECYCLE PATH
// ============================================================================

static bool test_movesense_async_subscription_lifecycle() {
    movesense::async::clear();

    NusEcgBridge bridge;
    TEST_ASSERT(!bridge.isStreaming(), "Bridge should not be streaming initially");
    TEST_ASSERT(!movesense::async::isSubscribed(NusEcgBridge::ECG_PATH), "Should not be subscribed initially");

    bridge.onInit();
    TEST_ASSERT(!bridge.isStreaming(), "Bridge should remain idle after onInit");

    // Client connects -> triggers subscription on /Meas/ECG/130
    bridge.onClientConnected();
    TEST_ASSERT(bridge.isStreaming(), "Bridge should be streaming after client connected");
    TEST_ASSERT(movesense::async::isSubscribed(NusEcgBridge::ECG_PATH), "Must be subscribed to /Meas/ECG/130");
    TEST_ASSERT(movesense::async::getSubscriberCount(NusEcgBridge::ECG_PATH) == 1, "Should have exactly 1 subscriber");

    // Redundant client connected should be idempotent
    bridge.onClientConnected();
    TEST_ASSERT(bridge.isStreaming(), "Bridge should still be streaming");
    TEST_ASSERT(movesense::async::getSubscriberCount(NusEcgBridge::ECG_PATH) == 1, "Should not duplicate subscription");

    // Client disconnects -> unsubscribes
    bridge.onClientDisconnected();
    TEST_ASSERT(!bridge.isStreaming(), "Bridge should stop streaming on disconnect");
    TEST_ASSERT(!movesense::async::isSubscribed(NusEcgBridge::ECG_PATH), "Must unsubscribe from /Meas/ECG/130");

    return true;
}

// ============================================================================
// TEST SUITE 2: TIMESTAMP SKEW CORRECTION FORMULA
// ============================================================================

static bool test_timestamp_skew_correction() {
    const uint32_t base_ts = 172800000;
    const uint32_t rate = 130;

    // 1. Verify specific index calculations
    uint32_t ts_0 = NusEcgBridge::calculateSampleTimestamp(base_ts, 0, rate);
    TEST_ASSERT(ts_0 == 172800000, "Sample 0 timestamp must equal base_ts");

    uint32_t ts_1 = NusEcgBridge::calculateSampleTimestamp(base_ts, 1, rate);
    // (1 * 1000) / 130 = 7.6923 -> 7 ms
    TEST_ASSERT(ts_1 == 172800007, "Sample 1 timestamp should be 172800007");

    uint32_t ts_2 = NusEcgBridge::calculateSampleTimestamp(base_ts, 2, rate);
    // (2 * 1000) / 130 = 15.3846 -> 15 ms
    TEST_ASSERT(ts_2 == 172800015, "Sample 2 timestamp should be 172800015");

    uint32_t ts_13 = NusEcgBridge::calculateSampleTimestamp(base_ts, 13, rate);
    // (13 * 1000) / 130 = 100.0 ms exactly
    TEST_ASSERT(ts_13 == 172800100, "Sample 13 timestamp must be exactly 100ms offset");

    uint32_t ts_130 = NusEcgBridge::calculateSampleTimestamp(base_ts, 130, rate);
    // (130 * 1000) / 130 = 1000 ms exactly (1 second)
    TEST_ASSERT(ts_130 == 172801000, "Sample 130 timestamp must be exactly 1000ms offset (1 second)");

    uint32_t ts_1300 = NusEcgBridge::calculateSampleTimestamp(base_ts, 1300, rate);
    // (1300 * 1000) / 130 = 10000 ms exactly (10 seconds)
    TEST_ASSERT(ts_1300 == 172810000, "Sample 1300 timestamp must be exactly 10000ms offset (10 seconds)");

    // 2. Contrast with broken integer division truncation: ts += (1000 / 130) = 7
    // After 130 samples, broken gives: 172800000 + 130 * 7 = 172800910 (90 ms skew!)
    uint32_t broken_130 = base_ts + (130 * (1000 / 130));
    TEST_ASSERT(broken_130 == 172800910, "Broken truncation must demonstrate 90ms clock error at 130 samples");
    TEST_ASSERT(ts_130 - broken_130 == 90, "Exact formula corrects the 90ms skew at 130 samples");

    // After 1300 samples, broken gives: 172800000 + 1300 * 7 = 172809100 (900 ms skew!)
    uint32_t broken_1300 = base_ts + (1300 * (1000 / 130));
    TEST_ASSERT(ts_1300 - broken_1300 == 900, "Exact formula corrects the 900ms cumulative drift over 10s");

    // 3. Mathematical proof of bounded error: |exact - theoretical| < 1.0 ms across 1300 samples
    uint32_t prev_ts = base_ts;
    for (size_t i = 1; i <= 1300; ++i) {
        uint32_t cur_ts = NusEcgBridge::calculateSampleTimestamp(base_ts, i, rate);
        double theoretical_ms = (static_cast<double>(i) * 1000.0) / 130.0;
        double actual_offset_ms = static_cast<double>(cur_ts - base_ts);
        double diff = std::abs(theoretical_ms - actual_offset_ms);
        TEST_ASSERT(diff < 1.0, "Timestamp skew must strictly be less than 1.0ms at all points");

        // Monotonic check: timestamp must strictly increase
        TEST_ASSERT(cur_ts > prev_ts, "Timestamp must be strictly monotonically increasing");
        uint32_t delta = cur_ts - prev_ts;
        TEST_ASSERT(delta == 7 || delta == 8, "Sample interval delta must alternate strictly between 7ms and 8ms");
        prev_ts = cur_ts;
    }

    return true;
}

// ============================================================================
// TEST SUITE 3: ZERO-HEAP CSV SAMPLE FORMATTING
// ============================================================================

static bool test_csv_sample_formatting() {
    char buf[64];

    // Standard case: 172800000, 342
    int len = NusEcgBridge::formatSampleCsv(172800000, 342, buf, sizeof(buf));
    TEST_ASSERT(len > 0, "Formatting should succeed");
    TEST_ASSERT(std::string(buf) == "172800000,342\n", "Output must be exactly '172800000,342\\n'");

    // Negative ECG microvolts: 172800007, -450
    len = NusEcgBridge::formatSampleCsv(172800007, -450, buf, sizeof(buf));
    TEST_ASSERT(len > 0, "Formatting negative value should succeed");
    TEST_ASSERT(std::string(buf) == "172800007,-450\n", "Output must be exactly '172800007,-450\\n'");

    // Zero ECG amplitude: 172800015, 0
    len = NusEcgBridge::formatSampleCsv(172800015, 0, buf, sizeof(buf));
    TEST_ASSERT(len > 0, "Formatting zero value should succeed");
    TEST_ASSERT(std::string(buf) == "172800015,0\n", "Output must be exactly '172800015,0\\n'");

    // Extreme values
    len = NusEcgBridge::formatSampleCsv(4294967000U, -32768, buf, sizeof(buf));
    TEST_ASSERT(len > 0, "Extreme value formatting should succeed");
    TEST_ASSERT(std::string(buf) == "4294967000,-32768\n", "Formatted extreme value mismatch");

    // Buffer overflow prevention
    char tiny_buf[5];
    int tiny_len = NusEcgBridge::formatSampleCsv(172800000, 342, tiny_buf, sizeof(tiny_buf));
    TEST_ASSERT(tiny_len == -1, "Should reject too small buffer and return -1 without overrun");

    return true;
}

// ============================================================================
// TEST SUITE 4: ZERO-HEAP ALLOCATION SAFETY
// ============================================================================

static bool test_zero_heap_allocation_safety() {
    char stack_buf[160];
    const int32_t sample_array[] = { 342, 355, 368, 380, 420, 550, 720, 950 };
    const size_t sample_count = sizeof(sample_array) / sizeof(sample_array[0]);

    // Enable heap tracking
    g_heap_alloc_count = 0;
    g_track_allocations = true;

    // 1. Test sample timestamp calculation in loop
    for (size_t i = 0; i < 500; ++i) {
        uint32_t ts = NusEcgBridge::calculateSampleTimestamp(172800000, i, 130);
        (void)ts;
    }

    // 2. Test individual sample formatting in loop
    for (size_t i = 0; i < 500; ++i) {
        char line[32];
        int w = NusEcgBridge::formatSampleCsv(172800000 + static_cast<uint32_t>(i * 7), 350, line, sizeof(line));
        (void)w;
    }

    // 3. Test batch formatting in loop
    for (size_t i = 0; i < 100; ++i) {
        size_t written = NusEcgBridge::formatBatchCsv(172800000, sample_array, sample_count, stack_buf, sizeof(stack_buf), 130);
        (void)written;
    }

    // 4. Test movesense::async::put transmission in loop (Mock registry zero-heap verification)
    movesense::Value put_payload;
    put_payload["Data"] = "172800000,342\n";
    for (size_t i = 0; i < 100; ++i) {
        movesense::async::put(NusEcgBridge::NUS_TX_PATH, put_payload, [](const movesense::Result& r) {
            (void)r;
        });
    }

    // 5. Test complete onEcgDataReceived dispatch pipeline with zero heap allocations
    NusEcgBridge streamingBridge(false);
    movesense::Value streamVal;
    streamVal["Timestamp"] = 172800000U;
    movesense::ValueArray streamArr;
    for (int i = 0; i < 8; ++i) {
        streamArr.add(300 + static_cast<int32_t>(i * 15));
    }
    streamVal["Samples"] = streamArr;
    streamingBridge.onEcgDataReceived(streamVal);

    // 6. Test batched onEcgDataReceived dispatch pipeline with zero heap allocations
    NusEcgBridge batchedBridge(true);
    batchedBridge.onEcgDataReceived(streamVal);

    // Disable heap tracking
    g_track_allocations = false;

    std::cout << "[Heap allocations detected: " << g_heap_alloc_count << "] " << std::flush;
    TEST_ASSERT(g_heap_alloc_count == 0, "Must have zero heap allocations in the sample formatting hot paths and mock put registry!");

    return true;
}

// ============================================================================
// TEST SUITE 5: MOVESENSE ASYNC PUT TRANSMISSION PIPELINE
// ============================================================================

static bool test_movesense_async_put_transmission() {
    movesense::async::clear();

    NusEcgBridge bridge(false); // Unbatched single-line mode
    bridge.onInit();
    bridge.onClientConnected();

    // Prepare simulated ECG notification with 4 samples
    movesense::Value ecgVal;
    ecgVal["Timestamp"] = 172800000U;

    movesense::ValueArray arr;
    arr.add(342);
    arr.add(355);
    arr.add(368);
    arr.add(380);
    ecgVal["Samples"] = arr;

    // Trigger notification
    movesense::async::simulateNotification(NusEcgBridge::ECG_PATH, ecgVal);

    // Verify statistics
    TEST_ASSERT(bridge.getSamplesProcessed() == 4, "Should have processed 4 samples");
    TEST_ASSERT(bridge.getPacketsSent() == 4, "Should have transmitted 4 NUS packets");
    TEST_ASSERT(movesense::async::getPutCount(NusEcgBridge::NUS_TX_PATH) == 4, "PUT count on /Comm/Ble/Nus/Tx must be 4");

    // Verify last transmitted payload
    std::string last_data = movesense::async::getLastPutData(NusEcgBridge::NUS_TX_PATH);
    // Sample index 3: (3 * 1000) / 130 = 23 ms -> 172800023,380\n
    TEST_ASSERT(last_data == "172800023,380\n", "Last packet payload must match exact timestamp and sample value");
    TEST_ASSERT(bridge.getLastTimestamp() == 172800023, "Last timestamp recorded must be 172800023");

    return true;
}

// ============================================================================
// TEST SUITE 6: BATCHED NUS TRANSMISSION & MTU BOUNDS
// ============================================================================

static bool test_batched_nus_transmission() {
    movesense::async::clear();

    NusEcgBridge batchedBridge(true); // Batched mode enabled
    batchedBridge.onInit();
    batchedBridge.onClientConnected();

    // Construct 16 samples
    movesense::Value ecgVal;
    ecgVal["Timestamp"] = 172800000U;

    movesense::ValueArray arr;
    for (int i = 0; i < 16; ++i) {
        arr.add(300 + i * 10);
    }
    ecgVal["Samples"] = arr;

    // Dispatch notification
    movesense::async::simulateNotification(NusEcgBridge::ECG_PATH, ecgVal);

    TEST_ASSERT(batchedBridge.getSamplesProcessed() == 16, "Must process all 16 samples");
    TEST_ASSERT(batchedBridge.getPacketsSent() > 0, "Must send at least 1 batched packet");
    TEST_ASSERT(batchedBridge.getPacketsSent() < 16, "Batched mode must send fewer packets than sample count");

    // Verify each line inside last put payload
    std::string batch_data = movesense::async::getLastPutData(NusEcgBridge::NUS_TX_PATH);
    TEST_ASSERT(batch_data.length() <= NusEcgBridge::MAX_STACK_BUFFER_SIZE, "Batched packet length must not exceed buffer size");

    // Verify CSV lines in batch
    std::istringstream stream(batch_data);
    std::string line;
    size_t lines_found = 0;
    while (std::getline(stream, line)) {
        if (line.empty()) continue;
        lines_found++;
        size_t comma = line.find(',');
        TEST_ASSERT(comma != std::string::npos, "Each line must contain comma delimiter");
        uint32_t ts = std::stoul(line.substr(0, comma));
        int val = std::stoi(line.substr(comma + 1));
        TEST_ASSERT(ts >= 172800000, "Timestamp must be >= base");
        TEST_ASSERT(val >= 300, "Sample value must be valid");
    }
    TEST_ASSERT(lines_found > 0, "Must contain parsed CSV lines");

    return true;
}

// ============================================================================
// TEST SUITE 7: WHITEBOARD COMPONENT INTEGRATION LAYER
// ============================================================================

static bool test_whiteboard_layer_compatibility() {
    NusEcgBridgeWbModule wbModule;

    TEST_ASSERT(!wbModule.isSubscribed(), "Whiteboard module should not be subscribed initially");

    // Lifecycle
    TEST_ASSERT(wbModule.initModule(), "initModule must succeed");
    TEST_ASSERT(wbModule.startModule(), "startModule must succeed");
    TEST_ASSERT(wbModule.isSubscribed(), "startModule must activate subscription");

    // Create WB_RES::ECGData notification
    const int32_t raw_samples[] = { 342, 358, 370, 395, 410, 480, 620, 750 };
    const size_t raw_count = sizeof(raw_samples) / sizeof(raw_samples[0]);

    WB_RES::ECGData ecgData;
    ecgData.timestamp = 172800000;
    ecgData.samples = whiteboard::MakeArray<int32_t>(raw_samples, raw_count);

    // Call onNotify
    wbModule.onNotify(WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID, ecgData);

    TEST_ASSERT(wbModule.getSamplesProcessed() == raw_count, "Whiteboard module must process all samples");
    TEST_ASSERT(wbModule.getPacketsSent() > 0, "Whiteboard module must post NUS packets");
    TEST_ASSERT(wbModule.getLastPacketLength() > 0, "Must record packet buffer length");
    TEST_ASSERT(wbModule.getLastPacketLength() <= 160, "Must respect packet buffer MTU size");

    // Verify stop and deinit
    wbModule.stopModule();
    TEST_ASSERT(!wbModule.isSubscribed(), "stopModule must deactivate subscription");
    wbModule.deinitModule();

    return true;
}

// ============================================================================
// TEST SUITE 8: ADVERSARIAL AND BOUNDARY HARDENING
// ============================================================================

static bool test_adversarial_and_boundary_cases() {
    movesense::async::clear();
    NusEcgBridge bridge;
    bridge.onInit();
    bridge.onClientConnected();

    // 1. Empty sample array notification
    movesense::Value emptyVal;
    emptyVal["Timestamp"] = 172800000U;
    movesense::ValueArray emptyArr;
    emptyVal["Samples"] = emptyArr;

    movesense::async::simulateNotification(NusEcgBridge::ECG_PATH, emptyVal);
    TEST_ASSERT(bridge.getSamplesProcessed() == 0, "Empty samples should not process any samples");
    TEST_ASSERT(bridge.getPacketsSent() == 0, "Empty samples should not send any packets");

    // 2. High sample rate override (e.g. 500 Hz)
    uint32_t ts_500hz_0 = NusEcgBridge::calculateSampleTimestamp(1000, 0, 500);
    uint32_t ts_500hz_1 = NusEcgBridge::calculateSampleTimestamp(1000, 1, 500);
    uint32_t ts_500hz_500 = NusEcgBridge::calculateSampleTimestamp(1000, 500, 500);
    TEST_ASSERT(ts_500hz_0 == 1000, "500Hz sample 0 must match base");
    TEST_ASSERT(ts_500hz_1 == 1002, "500Hz sample 1 must increment by 2ms (1000/500=2)");
    TEST_ASSERT(ts_500hz_500 == 2000, "500Hz sample 500 must equal exactly 1000ms offset");

    // 3. High timestamp and 32-bit modular wraparound safety
    uint32_t high_ts = 4294960000U;
    uint32_t computed_high = NusEcgBridge::calculateSampleTimestamp(high_ts, 130, 130);
    TEST_ASSERT(computed_high == 4294961000U, "Timestamp near uint32 max must compute accurately");

    // Standard uint32 modular arithmetic wrapping (4294967200 + 1000 wraps modulo 2^32 to 904)
    uint32_t wrap_base = 4294967200U;
    uint32_t wrapped_ts = NusEcgBridge::calculateSampleTimestamp(wrap_base, 130, 130);
    TEST_ASSERT(wrapped_ts == 904U, "Timestamp wrapping around uint32 boundary must produce correct modular result");

    return true;
}

// ============================================================================
// TEST SUITE 9: REMEDIATED MOVESENSE_NUS_BRIDGE_APP DELEGATION & DRIFT ELIMINATION
// ============================================================================

static bool test_movesense_nus_bridge_app_delegation_and_drift_elimination() {
    movesense::async::clear();

    Movesense_NUS_Bridge_App app;
    TEST_ASSERT(!app.isStreaming(), "Movesense_NUS_Bridge_App must not be streaming initially");
    TEST_ASSERT(!movesense::async::isSubscribed(NusEcgBridge::ECG_PATH), "Must not be subscribed initially");

    app.onInit();
    TEST_ASSERT(!app.isStreaming(), "Must remain idle after onInit");

    // Connect client -> subscribes to /Meas/ECG/130
    app.onClientConnected();
    TEST_ASSERT(app.isStreaming(), "Must be streaming after client connection");
    TEST_ASSERT(movesense::async::isSubscribed(NusEcgBridge::ECG_PATH), "Must subscribe to /Meas/ECG/130");

    // Idempotent connection call
    app.onClientConnected();
    TEST_ASSERT(movesense::async::getSubscriberCount(NusEcgBridge::ECG_PATH) == 1, "Subscription must be idempotent");

    // Construct ECG notification with 4 samples
    const uint32_t base_ts = 172800000;
    movesense::Value ecgVal;
    ecgVal["Timestamp"] = base_ts;
    movesense::ValueArray samples;
    samples.add(340);
    samples.add(360);
    samples.add(380);
    samples.add(400);
    ecgVal["Samples"] = samples;

    // Track heap allocations during app.onEcgDataReceived
    g_heap_alloc_count = 0;
    g_track_allocations = true;
    app.onEcgDataReceived(ecgVal);
    g_track_allocations = false;

    TEST_ASSERT(g_heap_alloc_count == 0, "Movesense_NUS_Bridge_App::onEcgDataReceived must have strictly zero heap allocations");

    // Verify PUT packet delivery on NUS TX path
    TEST_ASSERT(movesense::async::getPutCount(NusEcgBridge::NUS_TX_PATH) == 4, "Must transmit 4 NUS packets");

    // Verify last payload matches drift-free timestamp:
    // (3 * 1000ULL) / 130 = 23 ms offset -> 172800023,400\n
    std::string last_data = movesense::async::getLastPutData(NusEcgBridge::NUS_TX_PATH);
    TEST_ASSERT(last_data == "172800023,400\n", "Last packet must have exact 64-bit drift-free timestamp");

    // Verify zero-heap string_view inspection
    std::string_view last_sv = movesense::async::getLastPutDataView(NusEcgBridge::NUS_TX_PATH);
    TEST_ASSERT(last_sv == "172800023,400\n", "getLastPutDataView must match");

    // Verify buffer-based inspection
    char out_buf[64];
    size_t copied = movesense::async::getLastPutData(NusEcgBridge::NUS_TX_PATH, out_buf, sizeof(out_buf));
    TEST_ASSERT(copied == 14, "Buffer copied length mismatch");
    TEST_ASSERT(std::string(out_buf) == "172800023,400\n", "Buffer contents mismatch");

    // Disconnect
    app.onClientDisconnected();
    TEST_ASSERT(!app.isStreaming(), "Must stop streaming on disconnect");
    TEST_ASSERT(!movesense::async::isSubscribed(NusEcgBridge::ECG_PATH), "Must unsubscribe on disconnect");

    return true;
}

// ============================================================================
// MAIN TEST RUNNER
// ============================================================================

int main() {
    std::cout << "============================================================" << std::endl;
    std::cout << "  Movesense NUS ECG Bridge (NusEcgBridge) Test Suite" << std::endl;
    std::cout << "  Requirement R2 Verification Harness" << std::endl;
    std::cout << "============================================================" << std::endl;

    RUN_TEST(test_movesense_async_subscription_lifecycle);
    RUN_TEST(test_timestamp_skew_correction);
    RUN_TEST(test_csv_sample_formatting);
    RUN_TEST(test_zero_heap_allocation_safety);
    RUN_TEST(test_movesense_async_put_transmission);
    RUN_TEST(test_batched_nus_transmission);
    RUN_TEST(test_whiteboard_layer_compatibility);
    RUN_TEST(test_adversarial_and_boundary_cases);
    RUN_TEST(test_movesense_nus_bridge_app_delegation_and_drift_elimination);

    std::cout << "============================================================" << std::endl;
    std::cout << "  RESULTS: " << g_tests_passed << " PASSED, " << g_tests_failed << " FAILED" << std::endl;
    std::cout << "============================================================" << std::endl;

    if (g_tests_failed > 0) {
        return 1;
    }
    return 0;
}
