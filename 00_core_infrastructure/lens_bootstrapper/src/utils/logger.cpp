#include "utils/logger.hpp"

#include <cstdio>
#include <cstdarg>
#include <ctime>
#include <unistd.h>
#include <fcntl.h>
#include <sys/time.h>

namespace lauburu {

LogLevel Logger::s_min_level = LogLevel::INFO;
int Logger::s_log_fd = -1;

void Logger::init(const std::string& log_file_path, LogLevel min_level) {
    s_min_level = min_level;
    if (!log_file_path.empty()) {
        if (s_log_fd >= 0) {
            close();
        }
        s_log_fd = ::open(log_file_path.c_str(), O_WRONLY | O_CREAT | O_APPEND, 0644);
    }
}

void Logger::set_level(LogLevel level) {
    s_min_level = level;
}

void Logger::log(LogLevel level, const char* fmt, ...) {
    if (level < s_min_level) {
        return;
    }

    struct timeval tv;
    gettimeofday(&tv, nullptr);
    struct tm tm_buf;
    localtime_r(&tv.tv_sec, &tm_buf);

    char time_str[32];
    snprintf(time_str, sizeof(time_str), "%04d-%02d-%02d %02d:%02d:%02d.%03d",
             tm_buf.tm_year + 1900, tm_buf.tm_mon + 1, tm_buf.tm_mday,
             tm_buf.tm_hour, tm_buf.tm_min, tm_buf.tm_sec,
             (int)(tv.tv_usec / 1000));

    const char* lvl_str = "INFO";
    switch (level) {
        case LogLevel::DEBUG: lvl_str = "DEBUG"; break;
        case LogLevel::INFO:  lvl_str = "INFO "; break;
        case LogLevel::WARN:  lvl_str = "WARN "; break;
        case LogLevel::ERROR: lvl_str = "ERROR"; break;
    }

    char msg_buf[1024];
    va_list args;
    va_start(args, fmt);
    vsnprintf(msg_buf, sizeof(msg_buf), fmt, args);
    va_end(args);

    char out_buf[1200];
    int len = snprintf(out_buf, sizeof(out_buf), "[%s] [%s] %s\n", time_str, lvl_str, msg_buf);
    if (len > 0) {
        // Output to stderr
        ::write(STDERR_FILENO, out_buf, (size_t)len);
        // Output to file if configured
        if (s_log_fd >= 0) {
            ::write(s_log_fd, out_buf, (size_t)len);
        }
    }
}

void Logger::close() {
    if (s_log_fd >= 0) {
        ::close(s_log_fd);
        s_log_fd = -1;
    }
}

} // namespace lauburu
