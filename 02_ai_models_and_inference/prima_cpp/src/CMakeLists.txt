# TODO: should not use this
if (WIN32)
    if (BUILD_SHARED_LIBS)
        set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    endif()
endif()

#
# libraries
#

# llama

add_library(llama
            ../include/llama.h
            ../common/profiler.cpp
            ../common/profiler.h
            ../common/log.cpp
            ../common/log.h
            network-utils.cpp
            network-utils.h
            llama.cpp
            llama-vocab.cpp
            llama-grammar.cpp
            llama-sampling.cpp
            unicode.h
            unicode.cpp
            unicode-data.cpp
            )

target_include_directories(llama
    PUBLIC  .
    PUBLIC  ../include
    PRIVATE ../common)
target_compile_features   (llama PUBLIC cxx_std_11) # don't bump

target_link_libraries(llama PUBLIC ggml)

# prima.cpp requires zeromq for PRP activation streaming
find_library(ZMQ_LIB zmq
    HINTS /opt/homebrew/lib /usr/local/lib /usr/lib "$ENV{HOME}/.local/lib"
    REQUIRED)
if (ZMQ_LIB)
    target_link_libraries(llama PUBLIC ${ZMQ_LIB})
    message(STATUS "ZeroMQ found: ${ZMQ_LIB}")
else()
    message(WARNING "ZeroMQ not found — prima.cpp PRP activation streaming will not link")
endif()


if (BUILD_SHARED_LIBS)
    set_target_properties(llama PROPERTIES POSITION_INDEPENDENT_CODE ON)
    target_compile_definitions(llama PRIVATE LLAMA_SHARED LLAMA_BUILD)
endif()
