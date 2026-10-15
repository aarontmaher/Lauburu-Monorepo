#include "telemetry/system_telemetry.hpp"
#include "utils/json_writer.hpp"
#include "utils/logger.hpp"

#ifdef __APPLE__
#include "telemetry/darwin_telemetry.hpp"
#elif defined(__linux__)
#include "telemetry/linux_telemetry.hpp"
#endif

#include <chrono>
#include <ctime>

namespace lauburu {

std::string TelemetrySnapshot::toJson() const {
    JsonWriter w;
    w.startObject();
    w.addUInt64("timestamp", timestamp);
    w.addUInt64("ram_total_bytes", ram_total_bytes);
    w.addUInt64("ram_free_bytes", ram_free_bytes);
    w.addUInt64("ram_avail_bytes", ram_avail_bytes);
    w.addUInt64("ram_used_bytes", ram_used_bytes);
    w.addInt64("vm_pressure", vm_pressure);
    w.addInt64("thermal_pressure", thermal_pressure);
    w.addUInt64("net_rx_bps", net_rx_bps);
    w.addUInt64("net_tx_bps", net_tx_bps);
    w.addUInt64("net_rx_bytes", net_rx_bytes);
    w.addUInt64("net_tx_bytes", net_tx_bytes);
    w.endObject();
    return w.dump();
}

SystemTelemetry& SystemTelemetry::instance() {
    static SystemTelemetry s_instance;
    return s_instance;
}

SystemTelemetry::SystemTelemetry()
    : m_provider(nullptr),
      m_lastSampleTimeMs(0),
      m_lastRxBytes(0),
      m_lastTxBytes(0) {
#ifdef __APPLE__
    m_provider = new DarwinTelemetryProvider();
#elif defined(__linux__)
    m_provider = new LinuxTelemetryProvider();
#endif
}

SystemTelemetry::~SystemTelemetry() {
    delete m_provider;
}

bool SystemTelemetry::sample(TelemetrySnapshot& out) {
    if (!m_provider) {
        return false;
    }

    auto now = std::chrono::system_clock::now();
    uint64_t nowSec = std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count();
    uint64_t nowMs = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();

    out.timestamp = nowSec;

    if (!m_provider->sample(out)) {
        return false;
    }

    if (m_lastSampleTimeMs > 0 && nowMs > m_lastSampleTimeMs) {
        double deltaSec = static_cast<double>(nowMs - m_lastSampleTimeMs) / 1000.0;
        if (deltaSec > 0.05) { // At least 50ms to avoid divide by zero or extreme spikes
            if (out.net_rx_bytes >= m_lastRxBytes) {
                out.net_rx_bps = static_cast<uint64_t>((out.net_rx_bytes - m_lastRxBytes) / deltaSec);
            }
            if (out.net_tx_bytes >= m_lastTxBytes) {
                out.net_tx_bps = static_cast<uint64_t>((out.net_tx_bytes - m_lastTxBytes) / deltaSec);
            }
        }
    } else {
        out.net_rx_bps = 0;
        out.net_tx_bps = 0;
    }

    m_lastSampleTimeMs = nowMs;
    m_lastRxBytes = out.net_rx_bytes;
    m_lastTxBytes = out.net_tx_bytes;
    m_lastSnapshot = out;

    return true;
}

} // namespace lauburu
