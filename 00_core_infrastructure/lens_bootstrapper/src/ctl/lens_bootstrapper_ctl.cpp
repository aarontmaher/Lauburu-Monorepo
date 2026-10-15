#include "ipc/unix_socket_server.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <algorithm>

static void printUsage(const char* prog) {
    std::cerr << "Usage: " << prog << " [options] <command>\n\n"
              << "Commands:\n"
              << "  status               Query bootstrapper daemon and supervisor status\n"
              << "  telemetry            Query real-time kernel memory, thermal & network telemetry\n"
              << "  restart_supervisor   Gracefully restart the child supervisor process\n"
              << "  stop                 Stop the bootstrapper daemon and supervisor\n"
              << "  ping                 Test IPC connectivity\n\n"
              << "Options:\n"
              << "  --socket <path>      Path to UNIX domain socket (default: ~/.lauburu/lens_bootstrapper.sock)\n"
              << "  --help               Display this help message\n";
}

int main(int argc, char* argv[]) {
    std::string socketPath = "~/.lauburu/lens_bootstrapper.sock";
    std::string command;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--socket" && i + 1 < argc) {
            socketPath = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 0;
        } else if (arg[0] != '-') {
            command = arg;
        } else {
            std::cerr << "Unknown option: " << arg << "\n";
            printUsage(argv[0]);
            return 1;
        }
    }

    if (command.empty()) {
        std::cerr << "Error: No command specified.\n";
        printUsage(argv[0]);
        return 1;
    }

    // Convert command to uppercase
    std::string upperCmd = command;
    std::transform(upperCmd.begin(), upperCmd.end(), upperCmd.begin(), ::toupper);

    std::string expandedPath = lauburu::UnixSocketServer::expandHomePath(socketPath);

    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock < 0) {
        std::cerr << "Error: Failed to create socket: " << strerror(errno) << "\n";
        return 1;
    }

    struct sockaddr_un addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, expandedPath.c_str(), sizeof(addr.sun_path) - 1);

    if (connect(sock, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) != 0) {
        std::cerr << "Error: Failed to connect to bootstrapper daemon at " << expandedPath
                  << ": " << strerror(errno) << "\n"
                  << "(Is lens_bootstrapper running?)\n";
        close(sock);
        return 2;
    }

    std::string request = upperCmd + "\n";
    ssize_t written = write(sock, request.c_str(), request.size());
    if (written < 0) {
        std::cerr << "Error: Failed to send command: " << strerror(errno) << "\n";
        close(sock);
        return 3;
    }

    // Read response line
    char buffer[4096];
    std::string response;
    while (true) {
        ssize_t n = read(sock, buffer, sizeof(buffer) - 1);
        if (n <= 0) break;
        buffer[n] = '\0';
        response += buffer;
        if (response.find('\n') != std::string::npos) break;
    }

    close(sock);

    if (response.empty()) {
        std::cerr << "Error: Empty response from daemon\n";
        return 4;
    }

    // Strip trailing newline for clean output
    while (!response.empty() && (response.back() == '\n' || response.back() == '\r')) {
        response.pop_back();
    }

    std::cout << response << std::endl;
    return 0;
}
