#pragma once

#include <string>
#include <cstdint>

namespace lauburu {

enum class LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3
};

class Logger {
public:
    static void init(const std::string& log_file_path = "", LogLevel min_level = LogLevel::INFO);
    static void set_level(LogLevel level);
    static void log(LogLevel level, const char* fmt, ...);
    static void close();

private:
    static LogLevel s_min_level;
    static int s_log_fd;
};

#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wgnu-zero-variadic-macro-arguments"
#endif

#define LOG_DEBUG(fmt, ...) ::lauburu::Logger::log(::lauburu::LogLevel::DEBUG, fmt, ##__VA_ARGS__)
#define LOG_INFO(fmt, ...)  ::lauburu::Logger::log(::lauburu::LogLevel::INFO,  fmt, ##__VA_ARGS__)
#define LOG_WARN(fmt, ...)  ::lauburu::Logger::log(::lauburu::LogLevel::WARN,  fmt, ##__VA_ARGS__)
#define LOG_ERROR(fmt, ...) ::lauburu::Logger::log(::lauburu::LogLevel::ERROR, fmt, ##__VA_ARGS__)

#if defined(__clang__)
#pragma clang diagnostic pop
#endif

} // namespace lauburu
