#include "telemetry/system_telemetry.hpp"
#include "utils/logger.hpp"
#include "utils/json_writer.hpp"

#include <iostream>
#include <cassert>
#include <unistd.h>

int main() {
    std::cout << "[TEST] Running test_bootstrapper_telemetry..." << std::endl;

    lauburu::SystemTelemetry& telemetry = lauburu::SystemTelemetry::instance();
    lauburu::TelemetrySnapshot s1;

    bool ok1 = telemetry.sample(s1);
    assert(ok1 && "First telemetry sample must succeed");
    (void)ok1;

    std::cout << "  Snapshot 1:" << std::endl;
    std::cout << "    Timestamp:        " << s1.timestamp << " sec" << std::endl;
    std::cout << "    Total RAM:        " << (s1.ram_total_bytes / (1024 * 1024)) << " MB" << std::endl;
    std::cout << "    Free RAM:         " << (s1.ram_free_bytes / (1024 * 1024)) << " MB" << std::endl;
    std::cout << "    Available RAM:    " << (s1.ram_avail_bytes / (1024 * 1024)) << " MB" << std::endl;
    std::cout << "    Used RAM:         " << (s1.ram_used_bytes / (1024 * 1024)) << " MB" << std::endl;
    std::cout << "    VM Pressure:      " << s1.vm_pressure << " (1=Normal, 2=Warning, 3=Critical)" << std::endl;
    std::cout << "    Thermal Pressure: " << s1.thermal_pressure << " (0=Nominal..3=Critical)" << std::endl;
    std::cout << "    Net Cumulative:   RX=" << s1.net_rx_bytes << " bytes, TX=" << s1.net_tx_bytes << " bytes" << std::endl;

    // Zero-Mock empirical assertions
    assert(s1.timestamp > 0 && "Timestamp must be non-zero");
    assert(s1.ram_total_bytes > 0 && "Total RAM must be greater than 0");
    assert(s1.ram_free_bytes > 0 && "Free RAM must be greater than 0");
    assert(s1.ram_avail_bytes > 0 && "Available RAM must be greater than 0");
    assert(s1.vm_pressure >= 1 && s1.vm_pressure <= 3 && "VM pressure must be between 1 and 3");
    assert(s1.thermal_pressure >= 0 && s1.thermal_pressure <= 3 && "Thermal pressure must be between 0 and 3");

    // Sleep 100ms and sample again to verify rate calculation
    usleep(100000);

    lauburu::TelemetrySnapshot s2;
    bool ok2 = telemetry.sample(s2);
    assert(ok2 && "Second telemetry sample must succeed");
    (void)ok2;

    std::cout << "  Snapshot 2 (Rate Calculation):" << std::endl;
    std::cout << "    Net RX Rate:      " << s2.net_rx_bps << " B/s" << std::endl;
    std::cout << "    Net TX Rate:      " << s2.net_tx_bps << " B/s" << std::endl;

    // Verify JSON serialization
    std::string jsonStr = s2.toJson();
    std::cout << "  Serialized JSON: " << jsonStr << std::endl;
    assert(!jsonStr.empty() && "JSON serialization must not be empty");
    assert(jsonStr.find("\"ram_free_bytes\"") != std::string::npos && "JSON must contain ram_free_bytes");
    assert(jsonStr.find("\"thermal_pressure\"") != std::string::npos && "JSON must contain thermal_pressure");
    assert(jsonStr.find("\"vm_pressure\"") != std::string::npos && "JSON must contain vm_pressure");

    std::cout << "[PASS] test_bootstrapper_telemetry passed successfully." << std::endl;
    return 0;
}
