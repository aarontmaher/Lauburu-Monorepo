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

    MecgDspReport report = movesense_run_pan_tompkins(samples, record_count);
    printf("C Peaks: %zu\\n", report.r_peaks_detected);
    return 0;
}
"""
with open("c_test_peaks.c", "w") as f:
    f.write(c_code)

subprocess.run(["clang", "-O3", "c_test_peaks.c", "movesense_dsp.c", "-o", "c_test_peaks"])
subprocess.run(["./c_test_peaks"])
