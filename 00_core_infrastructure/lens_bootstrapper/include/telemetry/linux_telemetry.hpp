#pragma once

#include "telemetry/system_telemetry.hpp"

#ifdef __linux__

namespace lauburu {

class LinuxTelemetryProvider : public ITelemetryProvider {
public:
    LinuxTelemetryProvider();
    ~LinuxTelemetryProvider() override;

    bool sample(TelemetrySnapshot& out) override;

private:
    void sampleMemory(TelemetrySnapshot& out);
    void sampleThermals(TelemetrySnapshot& out);
    void sampleNetwork(TelemetrySnapshot& out);
};

} // namespace lauburu

#endif // __linux__
