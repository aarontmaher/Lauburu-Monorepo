#pragma once

#include "telemetry/system_telemetry.hpp"

#ifdef __APPLE__

namespace lauburu {

class DarwinTelemetryProvider : public ITelemetryProvider {
public:
    DarwinTelemetryProvider();
    ~DarwinTelemetryProvider() override;

    bool sample(TelemetrySnapshot& out) override;

private:
    int m_thermalToken;
    uint32_t m_pageSize;
    mach_port_t m_hostPort;

    void sampleMemory(TelemetrySnapshot& out);
    void sampleThermals(TelemetrySnapshot& out);
    void sampleNetwork(TelemetrySnapshot& out);
};

} // namespace lauburu

#endif // __APPLE__
