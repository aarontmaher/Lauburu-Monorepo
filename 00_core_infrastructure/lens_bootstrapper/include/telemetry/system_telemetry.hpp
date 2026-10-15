#pragma once

#include <cstdint>
#include <string>

namespace lauburu {

struct TelemetrySnapshot {
    uint64_t timestamp = 0;       // Epoch seconds
    uint64_t ram_total_bytes = 0;
    uint64_t ram_free_bytes = 0;
    uint64_t ram_avail_bytes = 0;
    uint64_t ram_used_bytes = 0;
    int vm_pressure = 1;          // 1=Normal, 2=Warning, 3=Critical
    int thermal_pressure = 0;     // 0=Nominal, 1=Fair, 2=Serious, 3=Critical
    uint64_t net_rx_bps = 0;      // Bytes per sec
    uint64_t net_tx_bps = 0;      // Bytes per sec
    uint64_t net_rx_bytes = 0;    // Cumulative bytes
    uint64_t net_tx_bytes = 0;    // Cumulative bytes

    std::string toJson() const;
};

class ITelemetryProvider {
public:
    virtual ~ITelemetryProvider() = default;
    virtual bool sample(TelemetrySnapshot& out) = 0;
};

class SystemTelemetry {
public:
    static SystemTelemetry& instance();
    bool sample(TelemetrySnapshot& out);
    const TelemetrySnapshot& lastSnapshot() const { return m_lastSnapshot; }

private:
    SystemTelemetry();
    ~SystemTelemetry();

    ITelemetryProvider* m_provider;
    TelemetrySnapshot m_lastSnapshot;
    uint64_t m_lastSampleTimeMs;
    uint64_t m_lastRxBytes;
    uint64_t m_lastTxBytes;
};

} // namespace lauburu
