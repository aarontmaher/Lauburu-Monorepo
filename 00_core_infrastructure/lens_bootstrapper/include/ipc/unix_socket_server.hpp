#pragma once

#include <string>
#include <vector>
#include <sys/types.h>

namespace lauburu {

class ICommandHandler {
public:
    virtual ~ICommandHandler() = default;
    virtual std::string handleCommand(const std::string& cmd) = 0;
};

struct ClientConnection {
    int fd = -1;
    std::string inBuffer;
};

class UnixSocketServer {
public:
    UnixSocketServer();
    ~UnixSocketServer();

    bool init(const std::string& socketPath, ICommandHandler* handler);
    void poll(int timeoutMs = 100);
    void stop();

    const std::string& socketPath() const { return m_socketPath; }
    static std::string expandHomePath(const std::string& path);

private:
    std::string m_socketPath;
    int m_listenFd;
    ICommandHandler* m_handler;
    std::vector<ClientConnection> m_clients;

    void acceptClient();
    void handleClientData(size_t index);
    void removeClient(size_t index);
};

} // namespace lauburu
