// Lauburu NUS ECG Bridge - Movesense App
// Subscribes to internal /Meas/ECG/512 and forwards to standard BLE NUS (Nordic UART Service)
#include "NusEcgBridge.hpp"

static const char* ECG_PATH = "/Meas/ECG/512";
static const char* NUS_TX_PATH = "/Comm/Ble/Nus/Tx";

/**
 * @brief Movesense Application wrapper delegating to NusEcgBridge.
 *
 * Remediated to eliminate heap allocations (std::string) and clock drift (1000/512):
 * - Subscribes to /Meas/ECG/512 via movesense::async::subscribe
 * - Formats CSV lines via zero-heap stack buffer (NusEcgBridge::formatSampleCsv)
 * - Computes sample timestamps via 64-bit integer arithmetic:
 *     base_ts + (i * 1000ULL) / 512 (NusEcgBridge::calculateSampleTimestamp)
 * - Transmits to /Comm/Ble/Nus/Tx via movesense::async::put
 * - Eliminates std::string heap allocations on the 15KB RAM nRF52832 sensor
 */
class Movesense_NUS_Bridge_App : public movesense::App {
private:
    bool mIsStreaming;

public:
    Movesense_NUS_Bridge_App() : mIsStreaming(false) {}

    void onInit() override {
        mIsStreaming = false;
    }

    // Called when a Bluetooth client connects and requests data
    void onClientConnected() {
        if (!mIsStreaming) {
            // Subscribe to local ECG sensor at 512 Hz via movesense::async::subscribe
            movesense::async::subscribe(ECG_PATH, [this](const movesense::Result& result, const movesense::Value& val) {
                if (result.status == movesense::HTTP_OK) {
                    this->onEcgDataReceived(val);
                }
            });
            mIsStreaming = true;
        }
    }

    void onClientDisconnected() {
        if (mIsStreaming) {
            movesense::async::unsubscribe(ECG_PATH);
            mIsStreaming = false;
        }
    }

    // Forward raw data directly out over Nordic UART using zero-heap stack formatting
    void onEcgDataReceived(const movesense::Value& val) {
        // Zero-heap stack formatting and 64-bit timestamp math eliminating clock drift
        uint32_t base_timestamp = val["Timestamp"].asUInt();
        const auto& samples = val["Samples"].asArray();
        size_t count = samples.size();

        char line_buf[NusEcgBridge::MAX_LINE_BUFFER_SIZE];

        for (size_t i = 0; i < count; ++i) {
            int32_t ecg_val = samples[i].asInt();
            // Drift-free 64-bit timestamp math: base_ts + (i * 1000ULL) / 512
            uint32_t current_ts = NusEcgBridge::calculateSampleTimestamp(
                base_timestamp, i, NusEcgBridge::DEFAULT_SAMPLE_RATE);

            // Zero-heap stack buffer formatting: "Timestamp,ECG_uV\n"
            int line_len = NusEcgBridge::formatSampleCsv(current_ts, ecg_val, line_buf, sizeof(line_buf));
            if (line_len > 0) {
                // Push via Nordic UART Service Tx via movesense::async::put
                movesense::Value nus_payload;
                nus_payload["Data"] = line_buf;
                movesense::async::put(NUS_TX_PATH, nus_payload, [](const movesense::Result& result) {
                    (void)result;
                });
            }
        }
    }

    bool isStreaming() const { return mIsStreaming; }
};

#ifndef MOVESENSE_APPLICATION_MAIN
#define MOVESENSE_APPLICATION_MAIN(AppClass)
#endif

MOVESENSE_APPLICATION_MAIN(NusEcgBridge)
