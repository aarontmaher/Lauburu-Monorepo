#ifndef MOVESENSE_DSP_H
#define MOVESENSE_DSP_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint32_t timestamp_ms;
    int32_t ecg_amplitude_uv;
} MecgSample;

typedef struct {
    size_t total_samples;
    size_t r_peaks_detected;
    double calculated_bpm;
    double hrv_rmssd_ms;
    double duration_seconds;
    bool zero_mock_verified;
} MecgDspReport;

/**
 * Parses raw 7-byte Movesense binary records into MecgSample array.
 * Record format: 4 bytes uint32 timestamp_ms (little-endian) + 3 bytes int24 amplitude (little-endian).
 */
size_t movesense_unpack_records(const uint8_t *raw_bytes, size_t byte_len, MecgSample *out_samples, size_t max_samples);

/**
 * Runs native Pan-Tompkins QRS peak detection and heart rate analysis on samples.
 */
MecgDspReport movesense_run_pan_tompkins(const MecgSample *samples, size_t num_samples);

#ifdef __cplusplus
}
#endif

#endif // MOVESENSE_DSP_H
