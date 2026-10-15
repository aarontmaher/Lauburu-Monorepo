#ifdef __APPLE__

#include "telemetry/darwin_telemetry.hpp"
#include "utils/logger.hpp"

#include <mach/mach.h>
#include <mach/mach_host.h>
#include <mach/vm_statistics.h>
#include <notify.h>
#include <sys/sysctl.h>
#include <sys/types.h>
#include <ifaddrs.h>
#include <net/if.h>

namespace lauburu {

DarwinTelemetryProvider::DarwinTelemetryProvider()
    : m_thermalToken(-1),
      m_pageSize(16384),
      m_hostPort(MACH_PORT_NULL) {
    m_hostPort = mach_host_self();
    vm_size_t ps = 0;
    if (host_page_size(m_hostPort, &ps) == KERN_SUCCESS && ps > 0) {
        m_pageSize = static_cast<uint32_t>(ps);
    }
    notify_register_check("com.apple.system.thermalpressurelevel", &m_thermalToken);
}

DarwinTelemetryProvider::~DarwinTelemetryProvider() {
    if (m_thermalToken >= 0) {
        notify_cancel(m_thermalToken);
        m_thermalToken = -1;
    }
}

bool DarwinTelemetryProvider::sample(TelemetrySnapshot& out) {
    sampleMemory(out);
    sampleThermals(out);
    sampleNetwork(out);
    return true;
}

void DarwinTelemetryProvider::sampleMemory(TelemetrySnapshot& out) {
    // Total physical RAM via sysctl
    int mib[2] = {CTL_HW, HW_MEMSIZE};
    uint64_t total_mem = 0;
    size_t len = sizeof(total_mem);
    if (sysctl(mib, 2, &total_mem, &len, nullptr, 0) == 0) {
        out.ram_total_bytes = total_mem;
    }

    // Mach VM statistics
    vm_statistics64_data_t vm_stat;
    mach_msg_type_number_t count = HOST_VM_INFO64_COUNT;
    kern_return_t kr = host_statistics64(m_hostPort, HOST_VM_INFO64,
                                        reinterpret_cast<host_info64_t>(&vm_stat), &count);
    if (kr == KERN_SUCCESS) {
        uint64_t free_pages = vm_stat.free_count + vm_stat.speculative_count;
        out.ram_free_bytes = free_pages * m_pageSize;

        uint64_t avail_pages = free_pages + vm_stat.inactive_count + vm_stat.purgeable_count;
        out.ram_avail_bytes = avail_pages * m_pageSize;

        // Activity Monitor standard memory used calculation
        uint64_t internal_pages = vm_stat.internal_page_count;
        uint64_t purgeable_pages = vm_stat.purgeable_count;
        uint64_t app_pages = (internal_pages > purgeable_pages) ? (internal_pages - purgeable_pages) : 0;
        uint64_t wired_pages = vm_stat.wire_count;
        uint64_t compressed_pages = vm_stat.compressor_page_count;

        out.ram_used_bytes = (app_pages + wired_pages + compressed_pages) * m_pageSize;
    }

    // Memory pressure level (1=Normal, 2=Warning, 3=Critical)
    int pressure_level = 1;
    size_t psize = sizeof(pressure_level);
    if (sysctlbyname("kern.memorystatus_vm_pressure_level", &pressure_level, &psize, nullptr, 0) == 0) {
        out.vm_pressure = pressure_level;
    } else {
        out.vm_pressure = 1;
    }
}

void DarwinTelemetryProvider::sampleThermals(TelemetrySnapshot& out) {
    if (m_thermalToken >= 0) {
        uint64_t thermal_state = 0;
        uint32_t status = notify_get_state(m_thermalToken, &thermal_state);
        if (status == NOTIFY_STATUS_OK) {
            out.thermal_pressure = static_cast<int>(thermal_state);
        } else {
            out.thermal_pressure = 0;
        }
    } else {
        out.thermal_pressure = 0;
    }
}

void DarwinTelemetryProvider::sampleNetwork(TelemetrySnapshot& out) {
    struct ifaddrs* ifaddr = nullptr;
    if (getifaddrs(&ifaddr) != 0 || !ifaddr) {
        return;
    }

    uint64_t rx_sum = 0;
    uint64_t tx_sum = 0;

    for (struct ifaddrs* ifa = ifaddr; ifa != nullptr; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr || ifa->ifa_addr->sa_family != AF_LINK) {
            continue;
        }
        // Exclude loopback
        if (ifa->ifa_flags & IFF_LOOPBACK) {
            continue;
        }
        struct if_data* ifd = reinterpret_cast<struct if_data*>(ifa->ifa_data);
        if (ifd) {
            rx_sum += ifd->ifi_ibytes;
            tx_sum += ifd->ifi_obytes;
        }
    }

    freeifaddrs(ifaddr);

    out.net_rx_bytes = rx_sum;
    out.net_tx_bytes = tx_sum;
}

} // namespace lauburu

#endif // __APPLE__
