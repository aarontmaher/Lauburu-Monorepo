cmake_minimum_required(VERSION 3.10)
project(LauburuDSP)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(pan_tompkins STATIC pan_tompkins.cpp)
target_include_directories(pan_tompkins PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
