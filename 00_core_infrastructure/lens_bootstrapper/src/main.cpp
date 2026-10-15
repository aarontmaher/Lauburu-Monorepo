#include "bootstrapper_daemon.hpp"
#include "utils/logger.hpp"
#include "utils/json_writer.hpp"

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>

static void printUsage(const char* prog) {
    std::cout << "Usage: " << prog << " [options]\n\n"
              << "Options:\n"
              << "  --foreground             Run in foreground (default for LaunchAgent / systemd)\n"
              << "  --daemon                 Run as background daemon (double-fork)\n"
              << "  --config <path>          Path to JSON configuration file\n"
              << "  --supervisor-cmd <cmd>   Command to execute for the child supervisor\n"
              << "  --no-supervisor          Disable child process supervision\n"
              << "  --test-run               Run for 3 seconds and cleanly exit (for verification)\n"
              << "  --socket <path>          Path to UNIX domain socket\n"
              << "  --help, -h               Show this help message\n";
}

int main(int argc, char* argv[]) {
    lauburu::DaemonConfig config;
    bool foreground = false;
    bool runDaemon = false;
    bool testRun = false;
    std::string configPath;

    // First pass: locate --config flag if specified
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--config" && i + 1 < argc) {
            configPath = argv[i + 1];
            break;
        }
    }

    // If not specified, look for default config paths
    if (configPath.empty()) {
        const char* defaultPaths[] = {
            "00_core_infrastructure/lens_bootstrapper/config/lens_bootstrapper.json",
            "config/lens_bootstrapper.json",
            "/etc/lauburu/lens_bootstrapper.json"
        };
        for (const char* path : defaultPaths) {
            if (access(path, R_OK) == 0) {
                configPath = path;
                break;
            }
        }
    }

    // Load base configuration from file if present
    if (!configPath.empty() && access(configPath.c_str(), R_OK) == 0) {
        std::ifstream ifs(configPath);
        if (ifs.is_open()) {
            std::stringstream ss;
            ss << ifs.rdbuf();
            std::string jsonContent = ss.str();

            std::string cmd = lauburu::SimpleJsonParser::getString(jsonContent, "supervisor_command");
            if (!cmd.empty()) config.supervisorCommand = cmd;

            std::string sock = lauburu::SimpleJsonParser::getString(jsonContent, "socket_path");
            if (!sock.empty()) config.socketPath = sock;

            std::string host = lauburu::SimpleJsonParser::getString(jsonContent, "health_host");
            if (!host.empty()) config.healthHost = host;

            int port = lauburu::SimpleJsonParser::getInt(jsonContent, "health_port", -1);
            if (port > 0) config.healthPort = port;

            int telInterval = lauburu::SimpleJsonParser::getInt(jsonContent, "telemetry_interval_sec", -1);
            if (telInterval > 0) config.telemetryIntervalSec = telInterval;

            int healthInterval = lauburu::SimpleJsonParser::getInt(jsonContent, "health_interval_sec", -1);
            if (healthInterval > 0) config.healthIntervalSec = healthInterval;

            std::string logFile = lauburu::SimpleJsonParser::getString(jsonContent, "log_file_path");
            if (!logFile.empty()) config.logFilePath = logFile;

            bool enableSup = lauburu::SimpleJsonParser::getBool(jsonContent, "enable_supervisor", true);
            config.enableSupervisor = enableSup;
        }
    }

    // Second pass: CLI arguments override config file values
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--foreground") {
            foreground = true;
        } else if (arg == "--daemon") {
            runDaemon = true;
        } else if (arg == "--test-run") {
            testRun = true;
        } else if (arg == "--no-supervisor") {
            config.enableSupervisor = false;
        } else if (arg == "--config" && i + 1 < argc) {
            ++i; // already handled
        } else if (arg == "--supervisor-cmd" && i + 1 < argc) {
            config.supervisorCommand = argv[++i];
        } else if (arg == "--socket" && i + 1 < argc) {
            config.socketPath = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 0;
        } else {
            std::cerr << "Unknown option: " << arg << "\n";
            printUsage(argv[0]);
            return 1;
        }
    }

    // Double-fork daemonization if requested and not in foreground or test-run mode
    if (runDaemon && !foreground && !testRun) {
        pid_t pid = fork();
        if (pid < 0) {
            std::cerr << "Failed to fork daemon parent\n";
            return 1;
        }
        if (pid > 0) {
            // Exit parent
            return 0;
        }

        if (setsid() < 0) {
            return 1;
        }

        pid = fork();
        if (pid < 0) {
            return 1;
        }
        if (pid > 0) {
            // Exit first child
            return 0;
        }

        umask(027);

        // Redirect standard descriptors
        int devnull = open("/dev/null", O_RDWR);
        if (devnull >= 0) {
            dup2(devnull, STDIN_FILENO);
            dup2(devnull, STDOUT_FILENO);
            dup2(devnull, STDERR_FILENO);
            if (devnull > 2) close(devnull);
        }
    }

    auto& daemon = lauburu::BootstrapperDaemon::instance();
    if (!daemon.init(config, testRun)) {
        std::cerr << "Failed to initialize Bootstrapper Daemon\n";
        return 1;
    }

    return daemon.run();
}
