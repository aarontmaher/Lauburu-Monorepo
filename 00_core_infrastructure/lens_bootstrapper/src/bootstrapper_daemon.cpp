#include "bootstrapper_daemon.hpp"
#include "utils/logger.hpp"
#include "utils/json_writer.hpp"

#include <csignal>
#include <unistd.h>
#include <fstream>
#include <chrono>

namespace lauburu {

static uint64_t currentEpochSec() {
    auto now = std::chrono::system_clock::now();
    return std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count();
}

static void signalHandler(int sig) {
    if (sig == SIGTERM || sig == SIGINT) {
        BootstrapperDaemon::instance().requestStop();
    } else if (sig == SIGHUP) {
        BootstrapperDaemon::instance().requestReload();
    }
}

BootstrapperDaemon& BootstrapperDaemon::instance() {
    static BootstrapperDaemon s_instance;
    return s_instance;
}

BootstrapperDaemon::BootstrapperDaemon()
    : m_testRun(false),
      m_running(false),
      m_reloadRequested(false),
      m_startTimeSec(0) {
}

BootstrapperDaemon::~BootstrapperDaemon() {
    requestStop();
}

void BootstrapperDaemon::setupSignalHandlers() {
    struct sigaction sa;
    sa.sa_handler = signalHandler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;

    sigaction(SIGTERM, &sa, nullptr);
    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGHUP, &sa, nullptr);
    signal(SIGPIPE, SIG_IGN); // Ignore broken pipes on IPC sockets
}

bool BootstrapperDaemon::init(const DaemonConfig& config, bool testRun) {
    m_config = config;
    m_testRun = testRun;
    m_startTimeSec = currentEpochSec();

    Logger::init(m_config.logFilePath, LogLevel::INFO);
    LOG_INFO("Initializing Sovereign Lens Bootstrapper Daemon (PID: %d)...", getpid());

    if (m_testRun) {
        LOG_INFO("Running in TEST-RUN mode (automatic exit after 3 seconds)");
    }

    if (m_config.enableSupervisor) {
        if (!m_supervisor.init(m_config.supervisorCommand,
                               m_config.healthHost,
                               m_config.healthPort,
                               m_config.healthIntervalSec)) {
            LOG_ERROR("Failed to initialize process supervisor with command: %s",
                      m_config.supervisorCommand.c_str());
            return false;
        }
    } else {
        m_supervisor.setEnabled(false);
    }

    if (!m_ipcServer.init(m_config.socketPath, this)) {
        LOG_ERROR("Failed to initialize IPC server at %s", m_config.socketPath.c_str());
        return false;
    }

    // Perform initial telemetry sample
    TelemetrySnapshot initialSnapshot;
    SystemTelemetry::instance().sample(initialSnapshot);
    LOG_INFO("Telemetry initialized: Total RAM: %llu MB, Avail: %llu MB, Thermal: %d",
             static_cast<unsigned long long>(initialSnapshot.ram_total_bytes / (1024 * 1024)),
             static_cast<unsigned long long>(initialSnapshot.ram_avail_bytes / (1024 * 1024)),
             initialSnapshot.thermal_pressure);

    return true;
}

int BootstrapperDaemon::run() {
    m_running = true;
    setupSignalHandlers();

    if (m_config.enableSupervisor && !m_testRun) {
        m_supervisor.start();
    } else if (m_testRun) {
        LOG_INFO("Test run: verifying supervisor lifecycle with dummy echo command");
        m_supervisor.init("/bin/echo lens_bootstrapper_test_supervisor_ok");
        m_supervisor.start();
    }

    uint64_t lastTelemetrySec = 0;

    LOG_INFO("Bootstrapper daemon entered main event loop");

    while (m_running) {
        // Poll IPC server for commands (200ms timeout)
        m_ipcServer.poll(200);

        // Poll child supervisor
        m_supervisor.poll();

        uint64_t now = currentEpochSec();

        // Sample telemetry periodically
        if (now - lastTelemetrySec >= static_cast<uint64_t>(m_config.telemetryIntervalSec)) {
            lastTelemetrySec = now;
            TelemetrySnapshot snapshot;
            if (SystemTelemetry::instance().sample(snapshot)) {
                checkThermalOffload(snapshot);
            }
        }

        // Handle reload request (SIGHUP)
        if (m_reloadRequested) {
            m_reloadRequested = false;
            LOG_INFO("SIGHUP received, restarting supervisor child...");
            m_supervisor.restart();
        }

        // If test-run, exit cleanly after 3 seconds
        if (m_testRun && (now - m_startTimeSec >= 3)) {
            LOG_INFO("Test run duration completed (3 seconds), cleanly shutting down");
            m_running = false;
        }
    }

    LOG_INFO("Shutting down Bootstrapper Daemon...");
    m_supervisor.stop(5);
    m_ipcServer.stop();
    Logger::close();

    return 0;
}

void BootstrapperDaemon::requestStop() {
    m_running = false;
}

void BootstrapperDaemon::requestReload() {
    m_reloadRequested = true;
}

void BootstrapperDaemon::checkThermalOffload(const TelemetrySnapshot& snapshot) {
    const char* signalPath = "/tmp/thermal_offload_signal.json";

    if (snapshot.thermal_pressure >= 2) {
        const char* stateStr = (snapshot.thermal_pressure >= 3) ? "CRITICAL" : "SERIOUS";
        JsonWriter w;
        w.startObject();
        w.addUInt64("timestamp", snapshot.timestamp);
        w.addInt64("thermal_level", snapshot.thermal_pressure);
        w.addString("thermal_state", stateStr);
        w.addBool("trigger_offload", true);
        w.endObject();

        std::string jsonStr = w.dump();

        std::ofstream ofs(signalPath, std::ios::trunc);
        if (ofs.is_open()) {
            ofs << jsonStr << "\n";
            ofs.close();
            LOG_WARN("Thermal pressure elevated (%s, level %d), wrote %s",
                     stateStr, snapshot.thermal_pressure, signalPath);
        }
    } else {
        // If file exists and thermals have recovered, clean up signal file
        if (access(signalPath, F_OK) == 0) {
            unlink(signalPath);
            LOG_INFO("Thermal pressure recovered to nominal, removed %s", signalPath);
        }
    }
}

std::string BootstrapperDaemon::handleCommand(const std::string& cmd) {
    if (cmd == "STATUS") {
        uint64_t now = currentEpochSec();
        uint64_t uptime = (now >= m_startTimeSec) ? (now - m_startTimeSec) : 0;

        JsonWriter w;
        w.startObject();
        w.addString("status", "RUNNING");
        w.addInt64("pid", static_cast<int64_t>(getpid()));
        w.addInt64("supervisor_pid", static_cast<int64_t>(m_supervisor.childPid()));
        w.addString("supervisor_status", m_supervisor.statusString());
        w.addUInt64("uptime_sec", uptime);
        w.endObject();
        return w.dump();
    }

    if (cmd == "TELEMETRY") {
        TelemetrySnapshot snapshot;
        SystemTelemetry::instance().sample(snapshot);
        return snapshot.toJson();
    }

    if (cmd == "RESTART_SUPERVISOR") {
        pid_t oldPid = m_supervisor.childPid();
        m_supervisor.restart();

        JsonWriter w;
        w.startObject();
        w.addString("result", "RESTARTING");
        w.addInt64("old_pid", static_cast<int64_t>(oldPid));
        w.endObject();
        return w.dump();
    }

    if (cmd == "STOP") {
        requestStop();

        JsonWriter w;
        w.startObject();
        w.addString("result", "STOPPING");
        w.endObject();
        return w.dump();
    }

    if (cmd == "PING") {
        JsonWriter w;
        w.startObject();
        w.addString("result", "PONG");
        w.endObject();
        return w.dump();
    }

    JsonWriter w;
    w.startObject();
    w.addString("error", "UNKNOWN_COMMAND");
    w.addString("command", cmd);
    w.endObject();
    return w.dump();
}

} // namespace lauburu
