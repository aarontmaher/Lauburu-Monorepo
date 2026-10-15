#include "supervisor/process_supervisor.hpp"
#include "utils/logger.hpp"

#include <iostream>
#include <cassert>
#include <unistd.h>
#include <sys/types.h>
#include <csignal>

int main() {
    std::cout << "[TEST] Running test_bootstrapper_supervisor..." << std::endl;
    lauburu::Logger::init("", lauburu::LogLevel::INFO);

    lauburu::ProcessSupervisor sup;

    // Test 1: Command parsing and startup
    bool inited = sup.init("/bin/sh -c 'sleep 1'");
    assert(inited && "Supervisor initialization must succeed");
    (void)inited;

    bool started = sup.start();
    assert(started && "Supervisor start must succeed");
    (void)started;
    assert(sup.childPid() > 0 && "Child PID must be valid");
    assert(sup.status() == lauburu::SupervisorStatus::ALIVE && "Status must be ALIVE");
    assert(sup.statusString() == "ALIVE" && "Status string must be ALIVE");

    std::cout << "  Child started with PID: " << sup.childPid() << std::endl;

    // Verify process is actually alive via kill(pid, 0)
    int killRes = kill(sup.childPid(), 0);
    assert(killRes == 0 && "Process must exist in process table");
    (void)killRes;

    // Test 2: Process exit detection via poll
    std::cout << "  Waiting for child to finish (sleep 1)..." << std::endl;
    sleep(2); // Wait for sleep 1 to exit

    sup.poll();
    std::cout << "  After exit poll, status: " << sup.statusString()
              << ", crashes: " << sup.crashCount()
              << ", backoff: " << sup.currentBackoffSec() << "s" << std::endl;

    assert(sup.status() == lauburu::SupervisorStatus::BACKOFF && "Status must be BACKOFF after child exit");
    assert(sup.crashCount() == 1 && "Crash count must be 1");
    assert(sup.childPid() == -1 && "Child PID must be reset to -1");
    assert(sup.currentBackoffSec() >= 2 && "Backoff must have increased to at least 2 seconds");

    // Test 3: Graceful termination with SIGTERM
    std::cout << "  Testing graceful termination with SIGTERM..." << std::endl;
    sup.init("/bin/sleep 30");
    sup.start();
    pid_t longPid = sup.childPid();
    assert(longPid > 0 && "Long-running child must start");
    assert(kill(longPid, 0) == 0 && "Child must be running");

    bool stopped = sup.stop(3);
    assert(stopped && "Supervisor stop must succeed");
    (void)stopped;
    assert(sup.status() == lauburu::SupervisorStatus::STOPPED && "Status must be STOPPED");
    assert(sup.childPid() == -1 && "Child PID must be -1 after stop");

    // Verify child process was reaped and does not exist
    int deadRes = kill(longPid, 0);
    assert(deadRes != 0 && "Child process must no longer exist after stop");
    (void)deadRes;

    std::cout << "[PASS] test_bootstrapper_supervisor passed successfully." << std::endl;
    return 0;
}
