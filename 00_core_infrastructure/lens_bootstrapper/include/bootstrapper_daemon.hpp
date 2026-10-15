#pragma once

#include "telemetry/system_telemetry.hpp"
#include "supervisor/process_supervisor.hpp"
#include "ipc/unix_socket_server.hpp"

#include <string>
#include <atomic>
#include <cstdint>

namespace lauburu {

struct DaemonConfig {
    std::string supervisorCommand = "python3 -u 00_core_infrastructure/lens_bootstrapper/supervisor/local_lens_supervisor.py --port 3037";
    std::string socketPath = "~/.lauburu/lens_bootstrapper.sock";
    std::string healthHost = "127.0.0.1";
    int healthPort = 3037;
    int healthIntervalSec = 10;
    int telemetryIntervalSec = 2;
    std::string logFilePath = "";
    bool enableSupervisor = true;
};

class BootstrapperDaemon : public ICommandHandler {
public:
    static BootstrapperDaemon& instance();

    bool init(const DaemonConfig& config, bool testRun = false);
    int run();
    void requestStop();
    void requestReload();

    // ICommandHandler implementation
    std::string handleCommand(const std::string& cmd) override;

    static void setupSignalHandlers();

private:
    BootstrapperDaemon();
    ~BootstrapperDaemon() override;

    DaemonConfig m_config;
    bool m_testRun;
    std::atomic<bool> m_running;
    std::atomic<bool> m_reloadRequested;
    uint64_t m_startTimeSec;

    ProcessSupervisor m_supervisor;
    UnixSocketServer m_ipcServer;

    void checkThermalOffload(const TelemetrySnapshot& snapshot);
    bool loadConfigFile(const std::string& configPath);
};

} // namespace lauburu
