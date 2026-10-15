cmake_minimum_required(VERSION 3.14)
project(Movesense_TinyML_HR_Forecaster)

# ------------------------------------------------------------------------------
# 🎯 Lauburu Mesh: Tri-Fork Distillation Target (Movesense HR+)
# Hardware: Nordic nRF52832 (ARM Cortex-M4F) - 64KB RAM / 512KB Flash
# ------------------------------------------------------------------------------

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# C/C++ cross-compiler flags for Cortex-M4F
set(CMAKE_C_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 -O3 -Os")
set(CMAKE_CXX_FLAGS "${CMAKE_C_FLAGS} -fno-rtti -fno-exceptions")

# Placeholder for TensorFlow Lite Micro & Movesense API Includes
# include_directories(${MOVESENSE_CORE_API})
# include_directories(${TENSORFLOW_LITE_MICRO_PATH})

add_executable(movesense_tinyml_app main.cpp)
# target_link_libraries(movesense_tinyml_app tflite_micro movesense_api)
