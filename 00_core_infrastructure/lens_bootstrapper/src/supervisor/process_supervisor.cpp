#include "supervisor/process_supervisor.hpp"
#include "utils/logger.hpp"

#include <unistd.h>
#include <sys/wait.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <poll.h>
#include <csignal>
#include <cerrno>
#include <cstring>
#include <chrono>
#include <algorithm>

namespace lauburu {

static uint64_t currentEpochSec() {
    auto now = std::chrono::system_clock::now();
    return std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count();
}

ProcessSupervisor::ProcessSupervisor()
    : m_healthPort(0),
      m_healthIntervalSec(10),
      m_maxHealthFailures(3),
      m_childPid(-1),
      m_status(SupervisorStatus::STOPPED),
      m_enabled(true),
      m_startTimeSec(0),
      m_lastHealthCheckSec(0),
      m_consecutiveHealthFailures(0),
      m_backoffSec(1),
      m_maxBackoffSec(30),
      m_nextRestartSec(0),
      m_crashCount(0) {
}

ProcessSupervisor::~ProcessSupervisor() {
    stop(2);
}

bool ProcessSupervisor::parseCommand(const std::string& cmd) {
    m_argv.clear();
    std::string token;
    bool inQuotes = false;
    char quoteChar = '\0';

    for (size_t i = 0; i < cmd.size(); ++i) {
        char c = cmd[i];
        if (inQuotes) {
            if (c == quoteChar) {
                inQuotes = false;
            } else {
                token += c;
            }
        } else {
            if (c == '\'' || c == '"') {
                inQuotes = true;
                quoteChar = c;
            } else if (std::isspace(static_cast<unsigned char>(c))) {
                if (!token.empty()) {
                    m_argv.push_back(token);
                    token.clear();
                }
            } else {
                token += c;
            }
        }
    }
    if (!token.empty()) {
        m_argv.push_back(token);
    }
    return !m_argv.empty();
}

bool ProcessSupervisor::init(const std::string& command,
                            const std::string& host,
                            int port,
                            int healthCheckIntervalSec,
                            int maxConsecutiveHealthFailures) {
    m_command = command;
    m_healthHost = host.empty() ? "127.0.0.1" : host;
    m_healthPort = port;
    m_healthIntervalSec = healthCheckIntervalSec > 0 ? healthCheckIntervalSec : 10;
    m_maxHealthFailures = maxConsecutiveHealthFailures > 0 ? maxConsecutiveHealthFailures : 3;

    if (!parseCommand(m_command)) {
        LOG_ERROR("Failed to parse supervisor command: %s", command.c_str());
        return false;
    }
    return true;
}

bool ProcessSupervisor::start() {
    if (!m_enabled) {
        LOG_INFO("Supervisor is disabled, not starting child process");
        m_status = SupervisorStatus::STOPPED;
        return false;
    }

    if (m_argv.empty()) {
        LOG_ERROR("Cannot start supervisor: no command configured");
        m_status = SupervisorStatus::FAILED;
        return false;
    }

    if (m_childPid > 0) {
        LOG_WARN("Supervisor child already running with PID %d", m_childPid);
        return true;
    }

    m_status = SupervisorStatus::STARTING;

    std::vector<char*> c_argv;
    c_argv.reserve(m_argv.size() + 1);
    for (auto& s : m_argv) {
        c_argv.push_back(const_cast<char*>(s.c_str()));
    }
    c_argv.push_back(nullptr);

    pid_t pid = fork();
    if (pid < 0) {
        LOG_ERROR("fork() failed: %s", strerror(errno));
        m_status = SupervisorStatus::FAILED;
        return false;
    }

    if (pid == 0) {
        // Child process
        // Set new process group so parent can signal all children cleanly
        setpgid(0, 0);

        // Reset signal handlers to default
        signal(SIGTERM, SIG_DFL);
        signal(SIGINT, SIG_DFL);
        signal(SIGHUP, SIG_DFL);
        signal(SIGCHLD, SIG_DFL);

        execvp(c_argv[0], c_argv.data());

        // If execvp returns, execution failed
        LOG_ERROR("execvp failed for %s: %s", c_argv[0], strerror(errno));
        _exit(127);
    }

    // Parent process
    m_childPid = pid;
    m_startTimeSec = currentEpochSec();
    m_lastHealthCheckSec = m_startTimeSec;
    m_consecutiveHealthFailures = 0;
    m_status = SupervisorStatus::ALIVE;

    LOG_INFO("Supervisor spawned child PID %d: %s", m_childPid, m_command.c_str());
    return true;
}

void ProcessSupervisor::poll() {
    uint64_t now = currentEpochSec();

    if (m_status == SupervisorStatus::BACKOFF) {
        if (now >= m_nextRestartSec && m_enabled) {
            LOG_INFO("Backoff expired (%d sec), attempting restart of child process...", m_backoffSec);
            start();
        }
        return;
    }

    if (m_childPid <= 0) {
        return;
    }

    // Check process status via non-blocking waitpid
    int status = 0;
    pid_t res = waitpid(m_childPid, &status, WNOHANG);
    if (res == m_childPid) {
        // Child exited
        uint64_t lifetime = now - m_startTimeSec;
        m_crashCount++;

        if (WIFEXITED(status)) {
            LOG_WARN("Supervisor child PID %d exited with code %d (lifetime: %llu sec)",
                     m_childPid, WEXITSTATUS(status), static_cast<unsigned long long>(lifetime));
        } else if (WIFSIGNALED(status)) {
            LOG_WARN("Supervisor child PID %d killed by signal %d (lifetime: %llu sec)",
                     m_childPid, WTERMSIG(status), static_cast<unsigned long long>(lifetime));
        } else {
            LOG_WARN("Supervisor child PID %d terminated (lifetime: %llu sec)",
                     m_childPid, static_cast<unsigned long long>(lifetime));
        }

        m_childPid = -1;

        if (lifetime >= 60) {
            // Process was stable for at least 1 minute, reset backoff
            m_backoffSec = 1;
        } else {
            // Exponential backoff doubling up to max
            m_backoffSec = std::min(m_backoffSec * 2, m_maxBackoffSec);
        }

        if (m_enabled) {
            m_status = SupervisorStatus::BACKOFF;
            m_nextRestartSec = now + m_backoffSec;
            LOG_INFO("Next restart scheduled in %d seconds (total crashes: %d)",
                     m_backoffSec, m_crashCount);
        } else {
            m_status = SupervisorStatus::STOPPED;
        }
        return;
    }

    // If alive and TCP health check is configured
    if (m_status == SupervisorStatus::ALIVE && m_healthPort > 0) {
        // Wait at least 5 seconds after startup before checking health
        if (now - m_startTimeSec >= 5 && (now - m_lastHealthCheckSec) >= static_cast<uint64_t>(m_healthIntervalSec)) {
            m_lastHealthCheckSec = now;
            if (!checkTcpHealth()) {
                m_consecutiveHealthFailures++;
                LOG_WARN("Supervisor health check failed for %s:%d (consecutive: %d/%d)",
                         m_healthHost.c_str(), m_healthPort,
                         m_consecutiveHealthFailures, m_maxHealthFailures);

                if (m_consecutiveHealthFailures >= m_maxHealthFailures) {
                    LOG_ERROR("Supervisor exceeding max consecutive health failures (%d), forcing restart",
                              m_maxHealthFailures);
                    restart();
                }
            } else {
                if (m_consecutiveHealthFailures > 0) {
                    LOG_INFO("Supervisor health check recovered for %s:%d",
                             m_healthHost.c_str(), m_healthPort);
                }
                m_consecutiveHealthFailures = 0;
            }
        }
    }
}

bool ProcessSupervisor::checkTcpHealth() {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return false;

    // Set non-blocking
    int flags = fcntl(sock, F_GETFL, 0);
    if (flags >= 0) {
        fcntl(sock, F_SETFL, flags | O_NONBLOCK);
    }

    struct sockaddr_in sin;
    std::memset(&sin, 0, sizeof(sin));
    sin.sin_family = AF_INET;
    sin.sin_port = htons(static_cast<uint16_t>(m_healthPort));
    inet_pton(AF_INET, m_healthHost.c_str(), &sin.sin_addr);

    int res = connect(sock, reinterpret_cast<struct sockaddr*>(&sin), sizeof(sin));
    if (res == 0) {
        close(sock);
        return true;
    }

    if (errno == EINPROGRESS) {
        struct pollfd pfd;
        pfd.fd = sock;
        pfd.events = POLLOUT;
        pfd.revents = 0;

        int pollRes = ::poll(&pfd, 1, 500); // 500ms timeout
        if (pollRes > 0 && (pfd.revents & POLLOUT)) {
            int err = 0;
            socklen_t len = sizeof(err);
            if (getsockopt(sock, SOL_SOCKET, SO_ERROR, &err, &len) == 0 && err == 0) {
                close(sock);
                return true;
            }
        }
    }

    close(sock);
    return false;
}

bool ProcessSupervisor::stop(int timeoutSeconds) {
    if (m_childPid <= 0) {
        m_status = SupervisorStatus::STOPPED;
        return true;
    }

    pid_t targetPid = m_childPid;
    LOG_INFO("Sending SIGTERM to child PID %d (process group %d)...", targetPid, -targetPid);

    // Send SIGTERM to process group
    if (kill(-targetPid, SIGTERM) != 0) {
        kill(targetPid, SIGTERM);
    }

    int elapsedMs = 0;
    int maxMs = timeoutSeconds * 1000;
    bool reaped = false;

    while (elapsedMs < maxMs) {
        int status = 0;
        pid_t res = waitpid(targetPid, &status, WNOHANG);
        if (res == targetPid) {
            reaped = true;
            LOG_INFO("Child PID %d reaped cleanly after SIGTERM (%d ms)", targetPid, elapsedMs);
            break;
        }
        usleep(100000); // 100ms
        elapsedMs += 100;
    }

    if (!reaped) {
        LOG_WARN("Child PID %d did not exit within %d s, escalating to SIGKILL", targetPid, timeoutSeconds);
        if (kill(-targetPid, SIGKILL) != 0) {
            kill(targetPid, SIGKILL);
        }
        int status = 0;
        waitpid(targetPid, &status, 0);
        LOG_INFO("Child PID %d reaped after SIGKILL", targetPid);
    }

    m_childPid = -1;
    m_status = SupervisorStatus::STOPPED;
    return true;
}

bool ProcessSupervisor::restart() {
    LOG_INFO("Restarting supervisor child process...");
    stop(5);
    m_backoffSec = 1;
    return start();
}

std::string ProcessSupervisor::statusString() const {
    switch (m_status) {
        case SupervisorStatus::STOPPED:  return "STOPPED";
        case SupervisorStatus::STARTING: return "STARTING";
        case SupervisorStatus::ALIVE:    return "ALIVE";
        case SupervisorStatus::BACKOFF:  return "BACKOFF";
        case SupervisorStatus::FAILED:   return "FAILED";
    }
    return "UNKNOWN";
}

uint64_t ProcessSupervisor::uptimeSec() const {
    if (m_status == SupervisorStatus::ALIVE && m_startTimeSec > 0) {
        uint64_t now = currentEpochSec();
        return now >= m_startTimeSec ? (now - m_startTimeSec) : 0;
    }
    return 0;
}

} // namespace lauburu
