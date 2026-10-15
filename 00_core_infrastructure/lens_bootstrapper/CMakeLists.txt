cmake_minimum_required(VERSION 3.16)
project(lens_bootstrapper VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Zero-dependency, ultra-low overhead compiler flags
add_compile_options(
    -O2
    -fno-rtti
    -fno-exceptions
    -Wall
    -Wextra
    -Wpedantic
)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Platform-specific telemetry sources
set(PLATFORM_TELEMETRY_SRC "")
if(APPLE)
    list(APPEND PLATFORM_TELEMETRY_SRC src/telemetry/darwin_telemetry.cpp)
elseif(UNIX AND NOT APPLE)
    list(APPEND PLATFORM_TELEMETRY_SRC src/telemetry/linux_telemetry.cpp)
endif()

# Reusable static telemetry & utility library
add_library(lens_telemetry STATIC
    src/utils/logger.cpp
    src/utils/json_writer.cpp
    src/telemetry/system_telemetry.cpp
    ${PLATFORM_TELEMETRY_SRC}
)

# Standalone Bootstrapper Daemon
add_executable(lens_bootstrapper
    src/main.cpp
    src/bootstrapper_daemon.cpp
    src/supervisor/process_supervisor.cpp
    src/ipc/unix_socket_server.cpp
)
target_link_libraries(lens_bootstrapper PRIVATE lens_telemetry)

# Companion Control CLI tool
add_executable(lens_bootstrapper_ctl
    src/ctl/lens_bootstrapper_ctl.cpp
    src/ipc/unix_socket_server.cpp
)
target_link_libraries(lens_bootstrapper_ctl PRIVATE lens_telemetry)

# Unit Tests and Testing Support
enable_testing()

add_executable(test_bootstrapper_telemetry
    tests/test_bootstrapper_telemetry.cpp
)
target_link_libraries(test_bootstrapper_telemetry PRIVATE lens_telemetry)
add_test(NAME test_bootstrapper_telemetry COMMAND test_bootstrapper_telemetry)

add_executable(test_bootstrapper_supervisor
    tests/test_bootstrapper_supervisor.cpp
    src/supervisor/process_supervisor.cpp
)
target_link_libraries(test_bootstrapper_supervisor PRIVATE lens_telemetry)
add_test(NAME test_bootstrapper_supervisor COMMAND test_bootstrapper_supervisor)

add_executable(test_bootstrapper_ipc
    tests/test_bootstrapper_ipc.cpp
    src/ipc/unix_socket_server.cpp
)
target_link_libraries(test_bootstrapper_ipc PRIVATE lens_telemetry)
add_test(NAME test_bootstrapper_ipc COMMAND test_bootstrapper_ipc)
