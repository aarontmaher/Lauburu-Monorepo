cmake_minimum_required(VERSION 3.10)
project(LauburuKeychainBLE)

set(CMAKE_CXX_STANDARD 11)

# Pure C Dependency - No TFLite required!
add_executable(keychain_firmware main.cpp)
target_link_libraries(keychain_firmware m)
