#pragma once

#include <string>
#include <vector>
#include <cstdint>
#include <sys/types.h>

namespace lauburu {

enum class SupervisorStatus {
    STOPPED,
    STARTING,
    ALIVE,
    BACKOFF,
    FAILED
};

class ProcessSupervisor {
public:
    ProcessSupervisor();
    ~ProcessSupervisor();

    bool init(const std::string& command,
              const std::string& host = "127.0.0.1",
              int port = 3037,
              int healthCheckIntervalSec = 10,
              int maxConsecutiveHealthFailures = 3);

    bool start();
    void poll();
    bool stop(int timeoutSeconds = 5);
    bool restart();

    pid_t childPid() const { return m_childPid; }
    SupervisorStatus status() const { return m_status; }
    std::string statusString() const;
    uint64_t uptimeSec() const;
    int crashCount() const { return m_crashCount; }
    int currentBackoffSec() const { return m_backoffSec; }

    void setEnabled(bool enabled) { m_enabled = enabled; }
    bool isEnabled() const { return m_enabled; }

private:
    std::string m_command;
    std::vector<std::string> m_argv;
    std::string m_healthHost;
    int m_healthPort;
    int m_healthIntervalSec;
    int m_maxHealthFailures;

    pid_t m_childPid;
    SupervisorStatus m_status;
    bool m_enabled;

    uint64_t m_startTimeSec;
    uint64_t m_lastHealthCheckSec;
    int m_consecutiveHealthFailures;

    int m_backoffSec;
    int m_maxBackoffSec;
    uint64_t m_nextRestartSec;
    int m_crashCount;

    bool parseCommand(const std::string& cmd);
    bool checkTcpHealth();
};

} // namespace lauburu
