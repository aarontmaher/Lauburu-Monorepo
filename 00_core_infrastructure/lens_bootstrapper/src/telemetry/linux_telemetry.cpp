#ifdef __linux__

#include "telemetry/linux_telemetry.hpp"
#include "utils/logger.hpp"

#include <cstdio>
#include <cstring>
#include <unistd.h>
#include <fcntl.h>

namespace lauburu {

LinuxTelemetryProvider::LinuxTelemetryProvider() = default;
LinuxTelemetryProvider::~LinuxTelemetryProvider() = default;

bool LinuxTelemetryProvider::sample(TelemetrySnapshot& out) {
    sampleMemory(out);
    sampleThermals(out);
    sampleNetwork(out);
    return true;
}

void LinuxTelemetryProvider::sampleMemory(TelemetrySnapshot& out) {
    FILE* fp = fopen("/proc/meminfo", "r");
    if (!fp) return;

    char line[256];
    uint64_t mem_total_kb = 0;
    uint64_t mem_free_kb = 0;
    uint64_t mem_avail_kb = 0;
    uint64_t buffers_kb = 0;
    uint64_t cached_kb = 0;

    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "MemTotal:", 9) == 0) {
            sscanf(line + 9, "%llu", (unsigned long long*)&mem_total_kb);
        } else if (strncmp(line, "MemFree:", 8) == 0) {
            sscanf(line + 8, "%llu", (unsigned long long*)&mem_free_kb);
        } else if (strncmp(line, "MemAvailable:", 13) == 0) {
            sscanf(line + 13, "%llu", (unsigned long long*)&mem_avail_kb);
        } else if (strncmp(line, "Buffers:", 8) == 0) {
            sscanf(line + 8, "%llu", (unsigned long long*)&buffers_kb);
        } else if (strncmp(line, "Cached:", 7) == 0) {
            sscanf(line + 7, "%llu", (unsigned long long*)&cached_kb);
        }
    }
    fclose(fp);

    out.ram_total_bytes = mem_total_kb * 1024;
    out.ram_free_bytes = mem_free_kb * 1024;
    if (mem_avail_kb > 0) {
        out.ram_avail_bytes = mem_avail_kb * 1024;
    } else {
        out.ram_avail_bytes = (mem_free_kb + buffers_kb + cached_kb) * 1024;
    }

    if (out.ram_total_bytes > out.ram_avail_bytes) {
        out.ram_used_bytes = out.ram_total_bytes - out.ram_avail_bytes;
    } else {
        out.ram_used_bytes = 0;
    }

    // VM Pressure estimation based on available RAM percentage
    if (out.ram_total_bytes > 0) {
        double avail_pct = static_cast<double>(out.ram_avail_bytes) / static_cast<double>(out.ram_total_bytes);
        if (avail_pct < 0.10) {
            out.vm_pressure = 3; // Critical
        } else if (avail_pct < 0.20) {
            out.vm_pressure = 2; // Warning
        } else {
            out.vm_pressure = 1; // Normal
        }
    } else {
        out.vm_pressure = 1;
    }
}

void LinuxTelemetryProvider::sampleThermals(TelemetrySnapshot& out) {
    int fd = open("/sys/class/thermal/thermal_zone0/temp", O_RDONLY);
    if (fd < 0) {
        out.thermal_pressure = 0;
        return;
    }

    char buf[32];
    ssize_t bytes = read(fd, buf, sizeof(buf) - 1);
    close(fd);

    if (bytes <= 0) {
        out.thermal_pressure = 0;
        return;
    }

    buf[bytes] = '\0';
    int temp_milli = 0;
    if (sscanf(buf, "%d", &temp_milli) == 1) {
        int temp_c = temp_milli / 1000;
        if (temp_c >= 85) {
            out.thermal_pressure = 3; // Critical
        } else if (temp_c >= 75) {
            out.thermal_pressure = 2; // Serious
        } else if (temp_c >= 60) {
            out.thermal_pressure = 1; // Fair
        } else {
            out.thermal_pressure = 0; // Nominal
        }
    } else {
        out.thermal_pressure = 0;
    }
}

void LinuxTelemetryProvider::sampleNetwork(TelemetrySnapshot& out) {
    FILE* fp = fopen("/proc/net/dev", "r");
    if (!fp) return;

    char line[512];
    uint64_t rx_total = 0;
    uint64_t tx_total = 0;

    // Skip first two header lines
    if (!fgets(line, sizeof(line), fp)) { fclose(fp); return; }
    if (!fgets(line, sizeof(line), fp)) { fclose(fp); return; }

    while (fgets(line, sizeof(line), fp)) {
        char ifname[64];
        unsigned long long rx_bytes = 0, tx_bytes = 0;
        unsigned long long dummy = 0;

        char* colon = strchr(line, ':');
        if (!colon) continue;

        *colon = ' ';
        int matched = sscanf(line, "%63s %llu %llu %llu %llu %llu %llu %llu %llu %llu",
                             ifname, &rx_bytes,
                             &dummy, &dummy, &dummy, &dummy, &dummy, &dummy, &dummy,
                             &tx_bytes);

        if (matched >= 10) {
            if (strcmp(ifname, "lo") != 0) {
                rx_total += rx_bytes;
                tx_total += tx_bytes;
            }
        }
    }
    fclose(fp);

    out.net_rx_bytes = rx_total;
    out.net_tx_bytes = tx_total;
}

} // namespace lauburu

#endif // __linux__
