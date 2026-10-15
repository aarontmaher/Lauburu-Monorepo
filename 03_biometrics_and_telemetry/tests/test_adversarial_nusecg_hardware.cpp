#include "NusEcgBridge.hpp"
#include <iostream>
#include <iomanip>
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <vector>
#include <string>
#include <sstream>
#include <chrono>

// ============================================================================
// HEAP ALLOCATION INTERCEPTION HOOKS
// ============================================================================

static bool g_track_allocations = false;
static size_t g_heap_alloc_count = 0;
static size_t g_heap_bytes_allocated = 0;

void* operator new(size_t size) {
    if (g_track_allocations) {
        g_heap_alloc_count++;
        g_heap_bytes_allocated += size;
    }
    return std::malloc(size);
}

void* operator new[](size_t size) {
    if (g_track_allocations) {
        g_heap_alloc_count++;
        g_heap_bytes_allocated += size;
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
// TEST MACROS & LOGGING
// ============================================================================

static int g_tests_passed = 0;
static int g_tests_failed = 0;

#define TEST_ASSERT(cond, msg) \
    do { \
        if (!(cond)) { \
            std::cerr << "\n[-] ASSERTION FAILED: " << msg << " (" << __FILE__ << ":" << __LINE__ << ")" << std::endl; \
            g_tests_failed++; \
            return false; \
        } \
    } while (0)

#define RUN_TEST(test_func) \
    do { \
        std::cout << "[RUNNING] " << #test_func << " ... " << std::flush; \
        auto start = std::chrono::high_resolution_clock::now(); \
        if (test_func()) { \
            auto end = std::chrono::high_resolution_clock::now(); \
            auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count(); \
            std::cout << "\033[32mPASS\033[0m (" << elapsed_us << " us)" << std::endl; \
            g_tests_passed++; \
        } else { \
            std::cout << "\033[31mFAIL\033[0m" << std::endl; \
        } \
    } while (0)

// ============================================================================
// 1. ZERO-HEAP ALLOCATION INVARIANT: 10,000 SAMPLES
// ============================================================================

static bool test_zero_heap_timestamp_10k_samples() {
    const uint32_t base_ts = 172800000;
    const size_t total_samples = 10000;

    g_heap_alloc_count = 0;
    g_heap_bytes_allocated = 0;
    g_track_allocations = true;

    for (size_t i = 0; i < total_samples; ++i) {
        uint32_t ts = NusEcgBridge::calculateSampleTimestamp(base_ts, i, 130);
        (void)ts;
    }

    g_track_allocations = false;

    TEST_ASSERT(g_heap_alloc_count == 0,
        "calculateSampleTimestamp MUST have 0 heap allocations across 10,000 samples");
    TEST_ASSERT(g_heap_bytes_allocated == 0,
        "calculateSampleTimestamp MUST have 0 bytes allocated across 10,000 samples");
    return true;
}

static bool test_zero_heap_single_csv_format_10k_samples() {
    char line_buf[NusEcgBridge::MAX_LINE_BUFFER_SIZE];
    const uint32_t base_ts = 172800000;
    const size_t total_samples = 10000;

    g_heap_alloc_count = 0;
    g_heap_bytes_allocated = 0;
    g_track_allocations = true;

    for (size_t i = 0; i < total_samples; ++i) {
        uint32_t ts = base_ts + static_cast<uint32_t>(i * 7);
        // Alternate positive, negative, zero, and boundary values
        int32_t ecg_uv = static_cast<int32_t>((i % 2000) - 1000);
        int len = NusEcgBridge::formatSampleCsv(ts, ecg_uv, line_buf, sizeof(line_buf));
        if (len <= 0) {
            g_track_allocations = false;
            TEST_ASSERT(false, "formatSampleCsv failed on valid sample");
        }
    }

    g_track_allocations = false;

    TEST_ASSERT(g_heap_alloc_count == 0,
        "formatSampleCsv MUST have 0 heap allocations across 10,000 samples");
    TEST_ASSERT(g_heap_bytes_allocated == 0,
        "formatSampleCsv MUST have 0 bytes allocated across 10,000 samples");
    return true;
}

static bool test_zero_heap_batch_csv_format_10k_samples() {
    char batch_buf[NusEcgBridge::MAX_STACK_BUFFER_SIZE];
    const uint32_t base_ts = 172800000;
    const size_t total_samples = 10000;
    const size_t batch_size = 16;

    int32_t sample_batch[batch_size];
    for (size_t j = 0; j < batch_size; ++j) {
        sample_batch[j] = static_cast<int32_t>(300 + j * 25);
    }

    g_heap_alloc_count = 0;
    g_heap_bytes_allocated = 0;
    g_track_allocations = true;

    size_t samples_processed = 0;
    while (samples_processed < total_samples) {
        size_t count = std::min(batch_size, total_samples - samples_processed);
        uint32_t cur_base = NusEcgBridge::calculateSampleTimestamp(base_ts, samples_processed, 130);
        size_t written = NusEcgBridge::formatBatchCsv(cur_base, sample_batch, count, batch_buf, sizeof(batch_buf), 130);
        if (written == 0) {
            g_track_allocations = false;
            TEST_ASSERT(false, "formatBatchCsv produced 0 bytes");
        }
        samples_processed += count;
    }

    g_track_allocations = false;

    TEST_ASSERT(g_heap_alloc_count == 0,
        "formatBatchCsv MUST have 0 heap allocations across 10,000 samples");
    TEST_ASSERT(g_heap_bytes_allocated == 0,
        "formatBatchCsv MUST have 0 bytes allocated across 10,000 samples");
    TEST_ASSERT(samples_processed == total_samples, "Processed sample count mismatch");
    return true;
}

static bool test_zero_heap_whiteboard_onnotify_10k_samples() {
    NusEcgBridgeWbModule wbModule;
    wbModule.initModule();
    wbModule.startModule();

    const size_t batch_size = 16;
    const size_t num_notifications = 625; // 625 * 16 = 10,000 samples exactly
    int32_t raw_samples[batch_size];
    for (size_t j = 0; j < batch_size; ++j) {
        raw_samples[j] = static_cast<int32_t>(350 + j * 15);
    }

    WB_RES::ECGData ecgData;
    ecgData.timestamp = 172800000;
    ecgData.samples = whiteboard::MakeArray<int32_t>(raw_samples, batch_size);

    // Warm-up call before tracking to ensure module static init is settled
    wbModule.onNotify(WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID, ecgData);
    wbModule.stopModule();
    wbModule.startModule();

    g_heap_alloc_count = 0;
    g_heap_bytes_allocated = 0;
    g_track_allocations = true;

    for (size_t i = 0; i < num_notifications; ++i) {
        ecgData.timestamp = NusEcgBridge::calculateSampleTimestamp(172800000, i * batch_size, 130);
        wbModule.onNotify(WB_RES::LOCAL::MEAS_ECG_REQUIREDSAMPLERATE::LID, ecgData);
    }

    g_track_allocations = false;

    std::cout << "[WB onNotify heap allocs: " << g_heap_alloc_count << ", bytes: " << g_heap_bytes_allocated << "] " << std::flush;
    TEST_ASSERT(g_heap_alloc_count == 0,
        "NusEcgBridgeWbModule::onNotify MUST maintain strictly 0 heap allocations across 10,000 samples");
    TEST_ASSERT(wbModule.getSamplesProcessed() == (num_notifications * batch_size) + batch_size,
        "Sample count mismatch in Whiteboard module");
    return true;
}

static bool test_investigate_onEcgDataReceived_heap_10k_samples() {
    movesense::async::clear();
    NusEcgBridge bridge(true); // batched mode
    bridge.onInit();
    bridge.onClientConnected();

    const size_t batch_size = 16;
    const size_t num_notifications = 625; // 10,000 samples

    movesense::Value ecgVal;
    ecgVal["Timestamp"] = 172800000U;
    movesense::ValueArray arr;
    for (size_t j = 0; j < batch_size; ++j) {
        arr.add(static_cast<int32_t>(350 + j * 10));
    }
    ecgVal["Samples"] = arr;

    // Warm-up to pre-allocate map nodes in mock registry if any
    movesense::async::simulateNotification(NusEcgBridge::ECG_PATH, ecgVal);

    g_heap_alloc_count = 0;
    g_heap_bytes_allocated = 0;
    g_track_allocations = true;

    for (size_t i = 0; i < num_notifications; ++i) {
        ecgVal["Timestamp"] = NusEcgBridge::calculateSampleTimestamp(172800000, i * batch_size, 130);
        movesense::async::simulateNotification(NusEcgBridge::ECG_PATH, ecgVal);
    }

    g_track_allocations = false;

    std::cout << "[onEcgDataReceived mock pipeline allocs: " << g_heap_alloc_count << ", bytes: " << g_heap_bytes_allocated << "] " << std::flush;
    // Note: If g_heap_alloc_count > 0, this identifies heap allocations inside movesense::async::put mock registry (std::string / std::map)
    return true;
}

// ============================================================================
// 2. TIMESTAMP SKEW ACCURACY: 100,000 SAMPLES (verify drift <= 1ms)
// ============================================================================

static bool test_timestamp_skew_100k_samples() {
    const uint32_t base_ts = 172800000;
    const uint32_t sample_rate = 130;
    const size_t total_samples = 100000;

    double max_drift_ms = 0.0;
    size_t max_drift_index = 0;
    uint32_t prev_ts = base_ts;

    for (size_t i = 0; i <= total_samples; ++i) {
        uint32_t computed_ts = NusEcgBridge::calculateSampleTimestamp(base_ts, i, sample_rate);

        // Theoretical continuous physical time
        double theoretical_elapsed_ms = (static_cast<double>(i) * 1000.0) / static_cast<double>(sample_rate);
        double computed_elapsed_ms = static_cast<double>(computed_ts - base_ts);
        double drift_ms = std::abs(theoretical_elapsed_ms - computed_elapsed_ms);

        if (drift_ms > max_drift_ms) {
            max_drift_ms = drift_ms;
            max_drift_index = i;
        }

        // Hard assertion: drift must be <= 1.0 ms at EVERY point
        TEST_ASSERT(drift_ms <= 1.0, "Drift exceeded 1.0 ms threshold!");

        if (i > 0) {
            // Monotonicity check
            TEST_ASSERT(computed_ts > prev_ts, "Computed timestamp must be strictly monotonic");
            uint32_t step = computed_ts - prev_ts;
            TEST_ASSERT(step == 7 || step == 8, "Sample interval delta must strictly alternate between 7ms and 8ms");
        }
        prev_ts = computed_ts;
    }

    // Verify specifically at sample 100,000
    uint32_t final_ts = NusEcgBridge::calculateSampleTimestamp(base_ts, total_samples, sample_rate);
    double final_theoretical = (100000.0 * 1000.0) / 130.0; // 769230.7692307692 ms
    double final_computed = static_cast<double>(final_ts - base_ts); // 769230 ms
    double final_drift = std::abs(final_theoretical - final_computed);

    // Contrast with naive integer truncation: ts += (1000 / 130) = 7
    double naive_elapsed = static_cast<double>(total_samples * (1000 / sample_rate)); // 700000 ms
    double naive_drift = std::abs(final_theoretical - naive_elapsed); // 69230.769 ms (~69.23 seconds!)

    std::cout << "[100k samples: max_drift=" << std::fixed << std::setprecision(4)
              << max_drift_ms << " ms @ index " << max_drift_index
              << ", final_drift=" << final_drift << " ms"
              << ", naive_drift=" << std::setprecision(1) << naive_drift << " ms] " << std::flush;

    TEST_ASSERT(final_drift <= 1.0, "Cumulative drift at 100,000 samples must be <= 1.0 ms");
    TEST_ASSERT(max_drift_ms < 1.0, "Peak theoretical drift across all 100,000 samples must be strictly < 1.0 ms");
    return true;
}

static bool test_timestamp_skew_multi_rate_matrix_100k_samples() {
    const uint32_t base_ts = 1000000;
    const uint32_t test_rates[] = { 52, 128, 130, 200, 250, 256, 500, 512, 1000, 1024 };
    const size_t num_rates = sizeof(test_rates) / sizeof(test_rates[0]);
    const size_t sample_count = 100000;

    for (size_t r = 0; r < num_rates; ++r) {
        uint32_t rate = test_rates[r];
        double max_drift = 0.0;

        for (size_t i = 0; i <= sample_count; ++i) {
            uint32_t cur = NusEcgBridge::calculateSampleTimestamp(base_ts, i, rate);
            double theoretical = (static_cast<double>(i) * 1000.0) / static_cast<double>(rate);
            double actual = static_cast<double>(cur - base_ts);
            double diff = std::abs(theoretical - actual);
            if (diff > max_drift) {
                max_drift = diff;
            }
        }
        TEST_ASSERT(max_drift <= 1.0, "Max drift across multi-rate matrix must remain <= 1.0 ms");
    }
    return true;
}

static bool test_timestamp_uint32_wraparound_boundary_100k_samples() {
    // Base timestamp near uint32 max: 4,294,960,000 (wraps after ~7,295 ms)
    const uint32_t high_base_ts = 4294960000U;
    const uint32_t rate = 130;
    const size_t total_samples = 100000;

    // Verify calculated timestamp at sample 0
    uint32_t ts_0 = NusEcgBridge::calculateSampleTimestamp(high_base_ts, 0, rate);
    TEST_ASSERT(ts_0 == high_base_ts, "Sample 0 must equal high_base_ts");

    // Sample 13000: offset is (13000 * 1000) / 130 = 100,000 ms
    // 4294960000 + 100000 = 4295060000.
    // In uint32: 4295060000 - 4294967296 = 92704
    uint32_t ts_13k = NusEcgBridge::calculateSampleTimestamp(high_base_ts, 13000, rate);
    uint32_t expected_wrap = static_cast<uint32_t>(static_cast<uint64_t>(high_base_ts) + 100000ULL);
    TEST_ASSERT(ts_13k == expected_wrap, "Wraparound arithmetic must match expected uint32 modular sum");

    // Check drift calculation across wraparound using modular subtraction
    uint32_t ts_100k = NusEcgBridge::calculateSampleTimestamp(high_base_ts, total_samples, rate);
    uint32_t elapsed_modular = ts_100k - high_base_ts; // (uint32_t wrap subtraction preserves delta)
    uint32_t expected_elapsed = 769230U;
    TEST_ASSERT(elapsed_modular == expected_elapsed, "Modular difference after 100,000 samples must be exactly 769230 ms");

    return true;
}

// ============================================================================
// MAIN RUNNER
// ============================================================================

int main() {
    std::cout << "============================================================" << std::endl;
    std::cout << "  Adversarial Hardware & Concurrency Verification Suite" << std::endl;
    std::cout << "  C++ NusEcgBridge Zero-Heap & Timestamp Skew Challenger" << std::endl;
    std::cout << "============================================================" << std::endl;

    RUN_TEST(test_zero_heap_timestamp_10k_samples);
    RUN_TEST(test_zero_heap_single_csv_format_10k_samples);
    RUN_TEST(test_zero_heap_batch_csv_format_10k_samples);
    RUN_TEST(test_zero_heap_whiteboard_onnotify_10k_samples);
    RUN_TEST(test_investigate_onEcgDataReceived_heap_10k_samples);
    RUN_TEST(test_timestamp_skew_100k_samples);
    RUN_TEST(test_timestamp_skew_multi_rate_matrix_100k_samples);
    RUN_TEST(test_timestamp_uint32_wraparound_boundary_100k_samples);

    std::cout << "============================================================" << std::endl;
    std::cout << "  SUMMARY: " << g_tests_passed << " PASSED, " << g_tests_failed << " FAILED" << std::endl;
    std::cout << "============================================================" << std::endl;

    return (g_tests_failed > 0) ? 1 : 0;
}
