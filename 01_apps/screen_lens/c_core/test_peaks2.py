import sys
import subprocess

c_code = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "movesense_dsp.h"

int main() {
    const char *file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg";
    FILE *f = fopen(file_path, "rb");
    fseek(f, 381, SEEK_SET);
    size_t record_count = 5000;
    size_t byte_count = record_count * 7;
    uint8_t *raw_data = (uint8_t *)malloc(byte_count);
    fread(raw_data, 1, byte_count, f);
    fclose(f);

    MecgSample *samples = (MecgSample *)malloc(record_count * sizeof(MecgSample));
    movesense_unpack_records(raw_data, byte_count, samples, record_count);

    double sum = 0.0;
    for (size_t i = 0; i < record_count; ++i) { sum += samples[i].ecg_amplitude_uv; }
    double mean = sum / record_count;

    double *derived = (double *)calloc(record_count, sizeof(double));
    for (size_t i = 4; i < record_count; ++i) {
        double x0 = (double)samples[i].ecg_amplitude_uv - mean;
        double x1 = (double)samples[i - 1].ecg_amplitude_uv - mean;
        double x3 = (double)samples[i - 3].ecg_amplitude_uv - mean;
        double x4 = (double)samples[i - 4].ecg_amplitude_uv - mean;
        double d = (2.0 * x0 + x1 - x3 - 2.0 * x4) / 8.0;
        derived[i] = d * d;
    }

    double *integrated = (double *)calloc(record_count, sizeof(double));
    size_t window_size = 30;
    double running_sum = 0.0;
    for (size_t i = 0; i < record_count; ++i) {
        running_sum += derived[i];
        if (i >= window_size) {
            running_sum -= derived[i - window_size];
            integrated[i] = running_sum / (double)window_size;
        } else {
            integrated[i] = running_sum / (double)(i + 1);
        }
    }

    double integ_sum = 0.0;
    for (size_t i = 0; i < record_count; ++i) {
        integ_sum += integrated[i];
    }
    double threshold = (integ_sum / (double)record_count) * 2.5;

    size_t peak_capacity = 256;
    size_t *peak_indices = (size_t *)malloc(peak_capacity * sizeof(size_t));
    size_t peak_count = 0;

    for (size_t i = 1; i + 1 < record_count; ++i) {
        if (integrated[i] > threshold && integrated[i] > integrated[i - 1] && integrated[i] >= integrated[i + 1]) {
            if (peak_count < 5) {
                printf("Peak cand %zu, TS=%u. Prev TS=%u\\n", i, samples[i].timestamp_ms, peak_count > 0 ? samples[peak_indices[peak_count - 1]].timestamp_ms : 0);
            }
            if (peak_count == 0 || (samples[i].timestamp_ms - samples[peak_indices[peak_count - 1]].timestamp_ms) >= 300) {
                if (peak_count < 5) printf("Accepted peak at %zu\\n", i);
                peak_indices[peak_count++] = i;
            }
        }
    }
    printf("Total accepted C peaks: %zu\\n", peak_count);
    return 0;
}
"""
with open("c_test_peaks2.c", "w") as f:
    f.write(c_code)

subprocess.run(["clang", "-O3", "c_test_peaks2.c", "movesense_dsp.c", "-o", "c_test_peaks2"])
subprocess.run(["./c_test_peaks2"])
