#include <stdio.h>
#include <stdlib.h>
#include <mach/mach.h>
#include <mach/mach_host.h>
#include <sys/sysctl.h>
#include <time.h>

typedef struct {
    uint64_t total_ram_bytes;
    uint64_t free_ram_bytes;
    uint64_t available_ram_bytes;
    uint64_t active_ram_bytes;
    uint64_t inactive_ram_bytes;
    uint64_t wired_ram_bytes;
    uint64_t compressed_ram_bytes;
    double free_gb;
    double available_gb;
    double used_gb;
    double used_pct;
    double query_latency_us;
} DarwinKernelMemoryReport;

DarwinKernelMemoryReport audit_darwin_kernel_memory() {
    DarwinKernelMemoryReport report;
    memset(&report, 0, sizeof(DarwinKernelMemoryReport));

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    // 1. Get total physical RAM via sysctl
    int mib[2] = {CTL_HW, HW_MEMSIZE};
    size_t length = sizeof(report.total_ram_bytes);
    sysctl(mib, 2, &report.total_ram_bytes, &length, NULL, 0);

    // 2. Query XNU Mach Kernel directly (0ms latency, zero process fork)
    mach_port_t host_port = mach_host_self();
    mach_msg_type_number_t host_size = sizeof(vm_statistics64_data_t) / sizeof(integer_t);
    vm_statistics64_data_t vm_stat;
    vm_size_t page_size;
    host_page_size(host_port, &page_size);

    if (host_statistics64(host_port, HOST_VM_INFO64, (host_info64_t)&vm_stat, &host_size) == KERN_SUCCESS) {
        report.free_ram_bytes = (uint64_t)(vm_stat.free_count + vm_stat.speculative_count) * page_size;
        report.available_ram_bytes = (uint64_t)(vm_stat.free_count + vm_stat.speculative_count + vm_stat.inactive_count + vm_stat.purgeable_count) * page_size;
        report.active_ram_bytes = (uint64_t)vm_stat.active_count * page_size;
        report.inactive_ram_bytes = (uint64_t)vm_stat.inactive_count * page_size;
        report.wired_ram_bytes = (uint64_t)vm_stat.wire_count * page_size;
        report.compressed_ram_bytes = (uint64_t)vm_stat.compressor_page_count * page_size;

        report.free_gb = (double)report.free_ram_bytes / (1024.0 * 1024.0 * 1024.0);
        report.available_gb = (double)report.available_ram_bytes / (1024.0 * 1024.0 * 1024.0);
        uint64_t used_bytes = report.total_ram_bytes - report.available_ram_bytes;
        report.used_gb = (double)used_bytes / (1024.0 * 1024.0 * 1024.0);
        report.used_pct = ((double)used_bytes / (double)report.total_ram_bytes) * 100.0;
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    report.query_latency_us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;

    return report;
}

int main() {
    DarwinKernelMemoryReport rep = audit_darwin_kernel_memory();
    printf("================================================================================\n");
    printf("🖥️  XNU MACH KERNEL DIRECT MEMORY AUDIT (NATIVE C)\n");
    printf("================================================================================\n");
    printf("Total Physical RAM:    %.2f GB (%llu bytes)\n", (double)rep.total_ram_bytes / (1024.0 * 1024.0 * 1024.0), rep.total_ram_bytes);
    printf("Available Headroom:    %.2f GB (Free + Inactive Cache)\n", rep.available_gb);
    printf("Uncached Free RAM:     %.2f GB (%llu bytes)\n", rep.free_gb, rep.free_ram_bytes);
    printf("Active In-Use RAM:     %.2f GB (%.1f%%)\n", rep.used_gb, rep.used_pct);
    printf("Wired Down RAM:        %.2f GB\n", (double)rep.wired_ram_bytes / (1024.0 * 1024.0 * 1024.0));
    printf("Compressed RAM:        %.2f GB\n", (double)rep.compressed_ram_bytes / (1024.0 * 1024.0 * 1024.0));
    printf("XNU Query Latency:     %.2f microseconds (%.4f ms)\n", rep.query_latency_us, rep.query_latency_us / 1000.0);
    printf("Sanctuary Headroom:    %s (Target: >= 9.6 GB Available)\n", rep.available_gb >= 9.6 ? "SATISFIED" : (rep.used_pct <= 80.0 ? "DYNAMIC_HEALTHY" : "EVACUATION_REQUIRED"));
    printf("================================================================================\n");
    return 0;
}
