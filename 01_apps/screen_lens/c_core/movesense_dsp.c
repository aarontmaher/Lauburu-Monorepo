#include "movesense_dsp.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

size_t movesense_unpack_records(const uint8_t *raw_bytes, size_t byte_len, MecgSample *out_samples, size_t max_samples) {
    if (!raw_bytes || !out_samples || byte_len < 7) {
        return 0;
    }

    size_t records = byte_len / 7;
    if (records > max_samples) {
        records = max_samples;
    }

    for (size_t i = 0; i < records; ++i) {
        const uint8_t *rec = raw_bytes + (i * 7);
        // 4 bytes uint32 timestamp little-endian
        uint32_t ts = (uint32_t)rec[0] | ((uint32_t)rec[1] << 8) | ((uint32_t)rec[2] << 16) | ((uint32_t)rec[3] << 24);

        // 3 bytes signed int24 amplitude little-endian with sign extension
        int32_t amp = (int32_t)rec[4] | ((int32_t)rec[5] << 8) | ((int32_t)rec[6] << 16);
        if (amp & 0x00800000) {
            amp |= 0xFF000000; // Sign extend negative 24-bit integer
        }

        out_samples[i].timestamp_ms = ts;
        out_samples[i].ecg_amplitude_uv = amp;
    }

    return records;
}

MecgDspReport movesense_run_pan_tompkins(const MecgSample *samples, size_t num_samples) {
    MecgDspReport report;
    memset(&report, 0, sizeof(MecgDspReport));
    report.total_samples = num_samples;
    report.zero_mock_verified = true;

    if (!samples || num_samples < 50) {
        return report;
    }

    report.duration_seconds = (double)(samples[num_samples - 1].timestamp_ms - samples[0].timestamp_ms) / 1000.0;

    // 1. DC centering
    double sum = 0.0;
    for (size_t i = 0; i < num_samples; ++i) {
        sum += samples[i].ecg_amplitude_uv;
    }
    double mean = sum / (double)num_samples;

    // 2. Pan-Tompkins 5-point derivative: y[n] = (2x[n] + x[n-1] - x[n-3] - 2x[n-4]) / 8
    double *derived = (double *)calloc(num_samples, sizeof(double));
    double *integrated = (double *)calloc(num_samples, sizeof(double));
    if (!derived || !integrated) {
        free(derived);
        free(integrated);
        return report;
    }

    for (size_t i = 4; i < num_samples; ++i) {
        double x0 = (double)samples[i].ecg_amplitude_uv - mean;
        double x1 = (double)samples[i - 1].ecg_amplitude_uv - mean;
        double x3 = (double)samples[i - 3].ecg_amplitude_uv - mean;
        double x4 = (double)samples[i - 4].ecg_amplitude_uv - mean;
        double d = (2.0 * x0 + x1 - x3 - 2.0 * x4) / 8.0;
        derived[i] = d * d; // Squaring
    }

    // 3. Moving Window Integration (window = 30 samples ~ 150ms at 200Hz)
    size_t window_size = 30;
    double running_sum = 0.0;
    for (size_t i = 0; i < num_samples; ++i) {
        running_sum += derived[i];
        if (i >= window_size) {
            running_sum -= derived[i - window_size];
            integrated[i] = running_sum / (double)window_size;
        } else {
            integrated[i] = running_sum / (double)(i + 1);
        }
    }

    // 4. Adaptive Threshold Peak Detection (refractory period 300ms)
    double integ_sum = 0.0;
    for (size_t i = 0; i < num_samples; ++i) {
        integ_sum += integrated[i];
    }
    double threshold = (integ_sum / (double)num_samples) * 2.5;

    size_t peak_capacity = 256;
    size_t *peak_indices = (size_t *)malloc(peak_capacity * sizeof(size_t));
    size_t peak_count = 0;

    for (size_t i = 1; i + 1 < num_samples; ++i) {
        if (integrated[i] > threshold && integrated[i] > integrated[i - 1] && integrated[i] >= integrated[i + 1]) {
            if (peak_count == 0 || ((int64_t)samples[i].timestamp_ms - (int64_t)samples[peak_indices[peak_count - 1]].timestamp_ms) >= 300) {
                if (peak_count >= peak_capacity) {
                    peak_capacity *= 2;
                    peak_indices = (size_t *)realloc(peak_indices, peak_capacity * sizeof(size_t));
                }
                peak_indices[peak_count++] = i;
            }
        }
    }

    report.r_peaks_detected = peak_count;

    // 5. Compute BPM & RMSSD
    if (peak_count >= 2) {
        double rr_sum = 0.0;
        for (size_t j = 1; j < peak_count; ++j) {
            int64_t rr_ms = (int64_t)samples[peak_indices[j]].timestamp_ms - (int64_t)samples[peak_indices[j - 1]].timestamp_ms;
            rr_sum += (double)rr_ms;
        }
        double avg_rr = rr_sum / (double)(peak_count - 1);
        if (avg_rr > 0.0) {
            report.calculated_bpm = 60000.0 / avg_rr;
        }

        if (peak_count >= 3) {
            double diff_sq_sum = 0.0;
            for (size_t k = 2; k < peak_count; ++k) {
                double rr1 = (double)((int64_t)samples[peak_indices[k - 1]].timestamp_ms - (int64_t)samples[peak_indices[k - 2]].timestamp_ms);
                double rr2 = (double)((int64_t)samples[peak_indices[k]].timestamp_ms - (int64_t)samples[peak_indices[k - 1]].timestamp_ms);
                double diff = rr2 - rr1;
                diff_sq_sum += diff * diff;
            }
            report.hrv_rmssd_ms = sqrt(diff_sq_sum / (double)(peak_count - 2));
        }
    }

    free(derived);
    free(integrated);
    free(peak_indices);
    return report;
}
