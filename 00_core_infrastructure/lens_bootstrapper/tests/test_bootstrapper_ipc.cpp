#include "ipc/unix_socket_server.hpp"
#include "utils/logger.hpp"
#include "utils/json_writer.hpp"

#include <iostream>
#include <cassert>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <cstring>

class TestCommandHandler : public lauburu::ICommandHandler {
public:
    std::string handleCommand(const std::string& cmd) override {
        if (cmd == "PING") {
            return "{\"result\": \"PONG\"}";
        }
        if (cmd == "STATUS") {
            return "{\"status\": \"RUNNING\", \"pid\": 9999, \"uptime_sec\": 42}";
        }
        if (cmd == "TELEMETRY") {
            return "{\"ram_free_bytes\": 1073741824, \"thermal_pressure\": 0}";
        }
        return "{\"error\": \"UNKNOWN_COMMAND\"}";
    }
};

static std::string sendCommand(const std::string& socketPath, const std::string& cmd) {
    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    assert(sock >= 0 && "Socket creation must succeed");

    struct sockaddr_un addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, socketPath.c_str(), sizeof(addr.sun_path) - 1);

    int conn = connect(sock, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr));
    assert(conn == 0 && "Socket connect must succeed");
    (void)conn;

    std::string req = cmd + "\n";
    ssize_t w = write(sock, req.c_str(), req.size());
    assert(w == static_cast<ssize_t>(req.size()) && "Write must succeed");
    (void)w;

    char buf[1024];
    ssize_t r = read(sock, buf, sizeof(buf) - 1);
    assert(r > 0 && "Read response must succeed");
    (void)r;
    buf[r] = '\0';

    close(sock);
    return std::string(buf);
}

int main() {
    std::cout << "[TEST] Running test_bootstrapper_ipc..." << std::endl;
    lauburu::Logger::init("", lauburu::LogLevel::INFO);

    const std::string testSockPath = "/tmp/test_lens_bootstrapper_ipc.sock";

    TestCommandHandler handler;
    lauburu::UnixSocketServer server;

    bool inited = server.init(testSockPath, &handler);
    assert(inited && "IPC server initialization must succeed");
    (void)inited;
    assert(access(testSockPath.c_str(), F_OK) == 0 && "Socket file must exist");

    std::cout << "  IPC server initialized at " << testSockPath << std::endl;

    // Test 1: PING command
    std::cout << "  Testing PING command..." << std::endl;
    // We send command in background or execute connect, then poll server
    // Since connect blocks until accepted or socket backlog, we can fork a client or do non-blocking
    pid_t pid = fork();
    if (pid == 0) {
        // Child client
        usleep(50000); // 50ms
        std::string respPing = sendCommand(testSockPath, "PING");
        assert(respPing.find("\"result\": \"PONG\"") != std::string::npos);

        std::string respStatus = sendCommand(testSockPath, "STATUS");
        assert(respStatus.find("\"status\": \"RUNNING\"") != std::string::npos);

        std::string respTel = sendCommand(testSockPath, "TELEMETRY");
        assert(respTel.find("\"ram_free_bytes\"") != std::string::npos);

        _exit(0);
    }

    // Parent server poll loop
    int loops = 0;
    while (loops < 30) {
        server.poll(100);
        loops++;
    }

    int clientStatus = 0;
    waitpid(pid, &clientStatus, 0);
    assert(WIFEXITED(clientStatus) && WEXITSTATUS(clientStatus) == 0 && "Client must exit cleanly with 0");

    // Clean up
    server.stop();
    assert(access(testSockPath.c_str(), F_OK) != 0 && "Socket file must be unlinked after stop");

    std::cout << "[PASS] test_bootstrapper_ipc passed successfully." << std::endl;
    return 0;
}
