#include "movesense_dsp.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

int main(int argc, char **argv) {
    const char *file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg";
    if (argc > 1) {
        file_path = argv[1];
    }

    FILE *f = fopen(file_path, "rb");
    if (!f) {
        // Try reading extracted file or return error
        fprintf(stderr, "Could not open file: %s\n", file_path);
        return 1;
    }

    // Skip 4-byte magic + header JSON
    char magic[5] = {0};
    fread(magic, 1, 4, f);
    if (strcmp(magic, "MECG") != 0) {
        fprintf(stderr, "Invalid MECG magic: %s\n", magic);
        fclose(f);
        return 1;
    }

    // Seek past 4-byte magic
    fseek(f, 4, SEEK_SET);

    uint8_t buf[2048];
    size_t n = fread(buf, 1, sizeof(buf), f);
    long end_json_offset = -1;
    for (size_t i = 0; i + 1 < n; ++i) {
        if (buf[i] == '}' && buf[i+1] == '}') {
            end_json_offset = (long)i;
            break;
        }
    }
    if (end_json_offset < 0) {
        fprintf(stderr, "Could not find end of JSON header in binary buffer\n");
        fclose(f);
        return 1;
    }

    long data_offset = 4 + end_json_offset + 3;
    fseek(f, data_offset, SEEK_SET);

    // Read 5,000 records (35,000 bytes)
    size_t record_count = 5000;
    size_t byte_count = record_count * 7;
    uint8_t *raw_data = (uint8_t *)malloc(byte_count);
    size_t read_bytes = fread(raw_data, 1, byte_count, f);
    fclose(f);

    MecgSample *samples = (MecgSample *)malloc(record_count * sizeof(MecgSample));

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    size_t unpacked = movesense_unpack_records(raw_data, read_bytes, samples, record_count);
    MecgDspReport report = movesense_run_pan_tompkins(samples, unpacked);

    clock_gettime(CLOCK_MONOTONIC, &t1);
    double elapsed_us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;

    printf("================================================================================\n");
    printf("🫀 NATIVE C MOVESENSE PAN-TOMPKINS DSP BENCHMARK RESULT\n");
    printf("================================================================================\n");
    printf("Samples Processed:   %zu\n", report.total_samples);
    printf("Duration:            %.2f seconds\n", report.duration_seconds);
    printf("R-Peaks Detected:    %zu\n", report.r_peaks_detected);
    printf("Calculated BPM:      %.1f BPM\n", report.calculated_bpm);
    printf("HRV RMSSD:           %.2f ms\n", report.hrv_rmssd_ms);
    printf("Execution Time (C):  %.2f microseconds (%.4f ms)\n", elapsed_us, elapsed_us / 1000.0);
    printf("First 5 Timestamps:  %u, %u, %u, %u, %u ms\n", 
           samples[0].timestamp_ms, samples[1].timestamp_ms, samples[2].timestamp_ms, samples[3].timestamp_ms, samples[4].timestamp_ms);
    printf("First 5 ECG Amps:    %d, %d, %d, %d, %d uV\n",
           samples[0].ecg_amplitude_uv, samples[1].ecg_amplitude_uv, samples[2].ecg_amplitude_uv, samples[3].ecg_amplitude_uv, samples[4].ecg_amplitude_uv);
    printf("Zero-Mock Verified:  %s\n", report.zero_mock_verified ? "TRUE" : "FALSE");
    printf("================================================================================\n");

    free(raw_data);
    free(samples);
    return 0;
}
