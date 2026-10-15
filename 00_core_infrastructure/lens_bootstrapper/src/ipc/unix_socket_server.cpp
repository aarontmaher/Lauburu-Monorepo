#include "ipc/unix_socket_server.hpp"
#include "utils/logger.hpp"

#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#include <cerrno>
#include <cstring>
#include <cstdlib>
#include <algorithm>

namespace lauburu {

std::string UnixSocketServer::expandHomePath(const std::string& path) {
    if (path.empty() || path[0] != '~') {
        return path;
    }
    const char* home = std::getenv("HOME");
    if (!home) {
        return path;
    }
    if (path.size() == 1) {
        return std::string(home);
    }
    if (path[1] == '/') {
        return std::string(home) + path.substr(1);
    }
    return path;
}

UnixSocketServer::UnixSocketServer()
    : m_listenFd(-1),
      m_handler(nullptr) {
}

UnixSocketServer::~UnixSocketServer() {
    stop();
}

bool UnixSocketServer::init(const std::string& socketPath, ICommandHandler* handler) {
    m_handler = handler;
    m_socketPath = expandHomePath(socketPath);

    // Ensure parent directory exists
    size_t lastSlash = m_socketPath.find_last_of('/');
    if (lastSlash != std::string::npos && lastSlash > 0) {
        std::string dir = m_socketPath.substr(0, lastSlash);
        // Create directory recursively or simply try mkdir
        struct stat st;
        if (stat(dir.c_str(), &st) != 0) {
            mkdir(dir.c_str(), 0755);
        }
    }

    // Remove existing socket file if present
    unlink(m_socketPath.c_str());

    m_listenFd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (m_listenFd < 0) {
        LOG_ERROR("Failed to create UNIX domain socket: %s", strerror(errno));
        return false;
    }

    // Set non-blocking
    int flags = fcntl(m_listenFd, F_GETFL, 0);
    if (flags >= 0) {
        fcntl(m_listenFd, F_SETFL, flags | O_NONBLOCK);
    }

    struct sockaddr_un addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, m_socketPath.c_str(), sizeof(addr.sun_path) - 1);

    if (bind(m_listenFd, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) != 0) {
        LOG_ERROR("Failed to bind UNIX domain socket %s: %s", m_socketPath.c_str(), strerror(errno));
        close(m_listenFd);
        m_listenFd = -1;
        return false;
    }

    // Strict permissions: 0600 (owner only)
    chmod(m_socketPath.c_str(), 0600);

    if (listen(m_listenFd, 8) != 0) {
        LOG_ERROR("Failed to listen on UNIX domain socket: %s", strerror(errno));
        close(m_listenFd);
        m_listenFd = -1;
        unlink(m_socketPath.c_str());
        return false;
    }

    LOG_INFO("IPC server listening on %s (fd=%d)", m_socketPath.c_str(), m_listenFd);
    return true;
}

void UnixSocketServer::poll(int timeoutMs) {
    if (m_listenFd < 0) {
        return;
    }

    std::vector<struct pollfd> pfds;
    pfds.reserve(1 + m_clients.size());

    // Listen socket
    struct pollfd lfd;
    lfd.fd = m_listenFd;
    lfd.events = POLLIN;
    lfd.revents = 0;
    pfds.push_back(lfd);

    // Client sockets
    for (const auto& client : m_clients) {
        struct pollfd cfd;
        cfd.fd = client.fd;
        cfd.events = POLLIN;
        cfd.revents = 0;
        pfds.push_back(cfd);
    }

    int res = ::poll(pfds.data(), static_cast<nfds_t>(pfds.size()), timeoutMs);
    if (res <= 0) {
        return;
    }

    // Check listen socket
    if (pfds[0].revents & POLLIN) {
        acceptClient();
    }

    // Check client sockets in reverse order so removal does not shift unprocessed indices
    for (int i = static_cast<int>(m_clients.size()) - 1; i >= 0; --i) {
        size_t pfdIdx = static_cast<size_t>(i + 1);
        if (pfdIdx < pfds.size()) {
            if (pfds[pfdIdx].revents & (POLLERR | POLLHUP | POLLNVAL)) {
                removeClient(static_cast<size_t>(i));
            } else if (pfds[pfdIdx].revents & POLLIN) {
                handleClientData(static_cast<size_t>(i));
            }
        }
    }
}

void UnixSocketServer::acceptClient() {
    struct sockaddr_un clientAddr;
    socklen_t clientLen = sizeof(clientAddr);
    int clientFd = accept(m_listenFd, reinterpret_cast<struct sockaddr*>(&clientAddr), &clientLen);
    if (clientFd >= 0) {
        // Set non-blocking
        int flags = fcntl(clientFd, F_GETFL, 0);
        if (flags >= 0) {
            fcntl(clientFd, F_SETFL, flags | O_NONBLOCK);
        }

        ClientConnection conn;
        conn.fd = clientFd;
        m_clients.push_back(conn);
        LOG_DEBUG("IPC accepted client fd=%d (total active: %zu)", clientFd, m_clients.size());
    }
}

void UnixSocketServer::handleClientData(size_t index) {
    if (index >= m_clients.size()) return;

    char buffer[1024];
    ssize_t bytes = read(m_clients[index].fd, buffer, sizeof(buffer));
    if (bytes <= 0) {
        removeClient(index);
        return;
    }

    m_clients[index].inBuffer.append(buffer, static_cast<size_t>(bytes));

    size_t nlPos;
    while ((nlPos = m_clients[index].inBuffer.find('\n')) != std::string::npos) {
        std::string cmd = m_clients[index].inBuffer.substr(0, nlPos);
        m_clients[index].inBuffer.erase(0, nlPos + 1);

        // Trim carriage return if present
        if (!cmd.empty() && cmd.back() == '\r') {
            cmd.pop_back();
        }

        // Process command
        std::string response = "{\"error\": \"NO_HANDLER\"}";
        if (m_handler) {
            response = m_handler->handleCommand(cmd);
        }
        response += "\n";

        // Write response
        ssize_t written = write(m_clients[index].fd, response.c_str(), response.size());
        (void)written;
    }
}

void UnixSocketServer::removeClient(size_t index) {
    if (index < m_clients.size()) {
        close(m_clients[index].fd);
        m_clients.erase(m_clients.begin() + static_cast<std::ptrdiff_t>(index));
    }
}

void UnixSocketServer::stop() {
    for (auto& client : m_clients) {
        if (client.fd >= 0) {
            close(client.fd);
        }
    }
    m_clients.clear();

    if (m_listenFd >= 0) {
        close(m_listenFd);
        m_listenFd = -1;
    }

    if (!m_socketPath.empty()) {
        unlink(m_socketPath.c_str());
        m_socketPath.clear();
    }
}

} // namespace lauburu
